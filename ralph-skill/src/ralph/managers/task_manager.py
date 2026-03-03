"""
任务管理器

负责任务生命周期管理、状态机控制和状态变更通知。

## 核心功能
- 任务创建和管理
- 状态机转换控制
- 状态变更通知机制
- 任务依赖关系处理
- 并发安全保护

## 状态转换规则
- PENDING → IN_PROGRESS: 开始执行任务
- IN_PROGRESS → TESTING: 代码实现完成，进入测试阶段
- TESTING → COMPLETED: 测试通过
- TESTING → IN_PROGRESS: 测试失败，返回修复
- IN_PROGRESS → FAILED: 执行失败
- 任何状态 → FAILED: 取消任务（通过 cancel_task）
"""

import threading
from datetime import datetime
from typing import Callable, Dict, List, Optional, Set
from uuid import uuid4

from ..models.enums import TaskStatus, TaskType
from ..models.task import Task, TaskConfig, TaskGraph, TaskInfo


class TaskStatusTransitionError(Exception):
    """任务状态转换错误"""
    pass


class TaskNotFoundError(Exception):
    """任务未找到错误"""
    pass


class TaskDependencyError(Exception):
    """任务依赖错误"""
    pass


# 状态变更回调函数类型
StatusChangeCallback = Callable[[Task, TaskStatus, TaskStatus], None]


class TaskManager:
    """
    任务管理器
    
    管理任务的完整生命周期，包括创建、状态转换、依赖管理和通知机制。
    使用线程锁保证并发安全。
    """
    
    # 定义合法的状态转换
    VALID_TRANSITIONS = {
        TaskStatus.PENDING: {TaskStatus.IN_PROGRESS},
        TaskStatus.IN_PROGRESS: {TaskStatus.TESTING, TaskStatus.FAILED},
        TaskStatus.TESTING: {TaskStatus.COMPLETED, TaskStatus.IN_PROGRESS, TaskStatus.FAILED},
        TaskStatus.COMPLETED: set(),  # 完成状态不能转换到其他状态
        TaskStatus.FAILED: set(),  # 失败状态不能转换到其他状态
    }
    
    def __init__(self):
        """初始化任务管理器"""
        self._tasks: Dict[str, Task] = {}
        self._callbacks: List[StatusChangeCallback] = []
        self._lock = threading.RLock()  # 使用可重入锁保护共享状态
    
    def create_task(self, config: TaskConfig) -> Task:
        """
        创建新任务
        
        Args:
            config: 任务配置
            
        Returns:
            创建的任务对象
            
        Raises:
            ValueError: 如果任务 ID 已存在
        """
        with self._lock:
            if config.id in self._tasks:
                raise ValueError(f"任务 ID 已存在: {config.id}")
            
            # 创建任务实例
            task = Task(
                id=config.id,
                name=config.name,
                type=config.type,
                status=TaskStatus.PENDING,
                depends_on=config.depends_on,
                ai_engine=config.ai_engine,
                config=config.config,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                max_retries=config.max_retries,
            )
            
            # 添加创建日志
            task.add_log("info", f"任务已创建: {task.name}", {
                "type": task.type.value,
                "ai_engine": task.ai_engine,
                "depends_on": task.depends_on,
            })
            
            # 保存任务
            self._tasks[task.id] = task
            
            return task
    
    def get_task(self, task_id: str) -> Task:
        """
        获取任务
        
        Args:
            task_id: 任务 ID
            
        Returns:
            任务对象
            
        Raises:
            TaskNotFoundError: 如果任务不存在
        """
        with self._lock:
            if task_id not in self._tasks:
                raise TaskNotFoundError(f"任务不存在: {task_id}")
            return self._tasks[task_id]
    
    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[Task]:
        """
        列出任务
        
        Args:
            status: 可选的状态过滤器，如果为 None 则返回所有任务
            
        Returns:
            任务列表
        """
        with self._lock:
            tasks = list(self._tasks.values())
            
            if status is not None:
                tasks = [t for t in tasks if t.status == status]
            
            # 按创建时间排序
            tasks.sort(key=lambda t: t.created_at)
            
            return tasks
    
    def update_task_status(
        self, 
        task_id: str, 
        new_status: TaskStatus,
        reason: Optional[str] = None
    ) -> Task:
        """
        更新任务状态
        
        Args:
            task_id: 任务 ID
            new_status: 新状态
            reason: 可选的状态变更原因
            
        Returns:
            更新后的任务对象
            
        Raises:
            TaskNotFoundError: 如果任务不存在
            TaskStatusTransitionError: 如果状态转换不合法
        """
        with self._lock:
            task = self.get_task(task_id)
            old_status = task.status
            
            # 验证状态转换是否合法
            if not self._is_valid_transition(old_status, new_status):
                raise TaskStatusTransitionError(
                    f"不合法的状态转换: {old_status.value} -> {new_status.value}"
                )
            
            # 更新状态
            task.status = new_status
            task.updated_at = datetime.now()
            
            # 添加日志
            log_context = {"old_status": old_status.value, "new_status": new_status.value}
            if reason:
                log_context["reason"] = reason
            
            task.add_log("info", f"状态变更: {old_status.value} -> {new_status.value}", log_context)
            
            # 触发状态变更回调
            self._notify_status_change(task, old_status, new_status)
            
            return task
    
    def delete_task(self, task_id: str) -> None:
        """
        删除任务
        
        Args:
            task_id: 任务 ID
            
        Raises:
            TaskNotFoundError: 如果任务不存在
        """
        with self._lock:
            if task_id not in self._tasks:
                raise TaskNotFoundError(f"任务不存在: {task_id}")
            
            del self._tasks[task_id]
    
    def cancel_task(self, task_id: str, reason: str = "任务被取消") -> Task:
        """
        取消任务（将任务状态设置为 FAILED）
        
        Args:
            task_id: 任务 ID
            reason: 取消原因
            
        Returns:
            更新后的任务对象
            
        Raises:
            TaskNotFoundError: 如果任务不存在
        """
        with self._lock:
            task = self.get_task(task_id)
            
            # 只有未完成的任务才能取消
            if task.status in {TaskStatus.COMPLETED, TaskStatus.FAILED}:
                raise TaskStatusTransitionError(
                    f"无法取消已完成或已失败的任务: {task.status.value}"
                )
            
            old_status = task.status
            task.status = TaskStatus.FAILED
            task.updated_at = datetime.now()
            task.add_log("warning", f"任务被取消: {reason}")
            
            # 触发状态变更回调
            self._notify_status_change(task, old_status, TaskStatus.FAILED)
            
            return task
    
    def register_status_change_callback(self, callback: StatusChangeCallback) -> None:
        """
        注册状态变更回调函数
        
        回调函数签名: callback(task: Task, old_status: TaskStatus, new_status: TaskStatus) -> None
        
        Args:
            callback: 回调函数
        """
        with self._lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)
    
    def unregister_status_change_callback(self, callback: StatusChangeCallback) -> None:
        """
        注销状态变更回调函数
        
        Args:
            callback: 回调函数
        """
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)
    
    def get_task_info(self, task_id: str) -> TaskInfo:
        """
        获取任务信息（简化版）
        
        Args:
            task_id: 任务 ID
            
        Returns:
            任务信息对象
            
        Raises:
            TaskNotFoundError: 如果任务不存在
        """
        with self._lock:
            task = self.get_task(task_id)
            return TaskInfo(
                id=task.id,
                name=task.name,
                type=task.type,
                status=task.status,
                created_at=task.created_at,
                updated_at=task.updated_at,
                retry_count=task.retry_count,
                git_branch=task.git_branch,
            )
    
    def build_task_graph(self, task_ids: Optional[List[str]] = None) -> TaskGraph:
        """
        构建任务依赖图
        
        Args:
            task_ids: 可选的任务 ID 列表，如果为 None 则包含所有任务
            
        Returns:
            任务依赖图
            
        Raises:
            TaskNotFoundError: 如果某个任务不存在
        """
        with self._lock:
            if task_ids is None:
                task_ids = list(self._tasks.keys())
            
            # 验证所有任务都存在
            for task_id in task_ids:
                if task_id not in self._tasks:
                    raise TaskNotFoundError(f"任务不存在: {task_id}")
            
            # 构建任务字典和依赖关系
            tasks = {task_id: self._tasks[task_id] for task_id in task_ids}
            dependencies = {task_id: self._tasks[task_id].depends_on for task_id in task_ids}
            
            return TaskGraph(tasks=tasks, dependencies=dependencies)
    
    def validate_dependencies(self, task_ids: Optional[List[str]] = None) -> bool:
        """
        验证任务依赖关系是否有效（无循环依赖）
        
        Args:
            task_ids: 可选的任务 ID 列表，如果为 None 则验证所有任务
            
        Returns:
            如果依赖关系有效返回 True，否则返回 False
        """
        try:
            graph = self.build_task_graph(task_ids)
            return not graph.has_cycle()
        except (TaskNotFoundError, ValueError):
            return False
    
    def get_executable_tasks(self) -> List[Task]:
        """
        获取可执行的任务列表（状态为 PENDING 且依赖已满足）
        
        Returns:
            可执行的任务列表
        """
        with self._lock:
            # 获取所有已完成的任务 ID
            completed_task_ids = [
                task.id for task in self._tasks.values()
                if task.status == TaskStatus.COMPLETED
            ]
            
            # 找出所有 PENDING 状态且依赖已满足的任务
            executable_tasks = [
                task for task in self._tasks.values()
                if task.status == TaskStatus.PENDING and task.can_execute(completed_task_ids)
            ]
            
            return executable_tasks
    
    def _is_valid_transition(self, old_status: TaskStatus, new_status: TaskStatus) -> bool:
        """
        检查状态转换是否合法
        
        Args:
            old_status: 旧状态
            new_status: 新状态
            
        Returns:
            如果转换合法返回 True，否则返回 False
        """
        if old_status == new_status:
            return True  # 允许设置为相同状态（幂等操作）
        
        return new_status in self.VALID_TRANSITIONS.get(old_status, set())
    
    def _notify_status_change(
        self, 
        task: Task, 
        old_status: TaskStatus, 
        new_status: TaskStatus
    ) -> None:
        """
        通知所有注册的回调函数状态已变更
        
        Args:
            task: 任务对象
            old_status: 旧状态
            new_status: 新状态
        """
        # 注意：这里不需要加锁，因为调用者已经持有锁
        for callback in self._callbacks:
            try:
                callback(task, old_status, new_status)
            except Exception as e:
                # 记录回调错误但不中断执行
                task.add_log("error", f"状态变更回调执行失败: {str(e)}", {
                    "callback": callback.__name__,
                    "error": str(e),
                })
    
    def get_statistics(self) -> Dict[str, int]:
        """
        获取任务统计信息
        
        Returns:
            包含各状态任务数量的字典
        """
        with self._lock:
            stats = {
                "total": len(self._tasks),
                "pending": 0,
                "in_progress": 0,
                "testing": 0,
                "completed": 0,
                "failed": 0,
            }
            
            for task in self._tasks.values():
                if task.status == TaskStatus.PENDING:
                    stats["pending"] += 1
                elif task.status == TaskStatus.IN_PROGRESS:
                    stats["in_progress"] += 1
                elif task.status == TaskStatus.TESTING:
                    stats["testing"] += 1
                elif task.status == TaskStatus.COMPLETED:
                    stats["completed"] += 1
                elif task.status == TaskStatus.FAILED:
                    stats["failed"] += 1
            
            return stats
