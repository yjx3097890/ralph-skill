"""
任务相关数据模型

定义任务实体、任务配置、任务状态等核心数据类。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .enums import TaskStatus, TaskType


@dataclass
class LogEntry:
    """日志条目"""
    timestamp: datetime
    level: str  # debug, info, warning, error
    message: str
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskConfig:
    """任务配置"""
    id: str
    name: str
    type: TaskType
    depends_on: List[str] = field(default_factory=list)
    ai_engine: str = "qwen_code"
    hooks: Dict[str, List[str]] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    max_retries: int = 3
    timeout: int = 1800  # 默认 30 分钟超时


@dataclass
class Task:
    """任务实体"""
    id: str
    name: str
    type: TaskType
    status: TaskStatus
    depends_on: List[str]
    ai_engine: str
    config: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    execution_log: List[LogEntry] = field(default_factory=list)
    git_branch: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def add_log(self, level: str, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """添加日志条目"""
        entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            message=message,
            context=context or {}
        )
        self.execution_log.append(entry)
    
    def update_status(self, new_status: TaskStatus) -> None:
        """更新任务状态"""
        self.status = new_status
        self.updated_at = datetime.now()
        self.add_log("info", f"任务状态更新: {new_status.value}")
    
    def increment_retry(self) -> bool:
        """增加重试计数，返回是否还可以重试"""
        self.retry_count += 1
        return self.retry_count < self.max_retries
    
    def can_execute(self, completed_tasks: List[str]) -> bool:
        """检查任务是否可以执行（依赖是否满足）"""
        return all(dep in completed_tasks for dep in self.depends_on)


@dataclass
class TaskInfo:
    """任务信息（简化版，用于列表展示）"""
    id: str
    name: str
    type: TaskType
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    retry_count: int
    git_branch: Optional[str] = None


@dataclass
class TaskResult:
    """任务执行结果"""
    task_id: str
    success: bool
    execution_time: float
    message: str = ""
    output: str = ""
    errors: List[str] = field(default_factory=list)
    files_changed: List[str] = field(default_factory=list)
    commit_hash: Optional[str] = None
    tests_passed: bool = False
    test_output: Optional[str] = None


@dataclass
class TaskGraph:
    """任务依赖图"""
    tasks: Dict[str, Task]
    dependencies: Dict[str, List[str]]  # task_id -> [依赖的 task_id]
    
    def get_execution_order(self) -> List[str]:
        """获取任务执行顺序（拓扑排序）"""
        # 计算每个任务的入度（有多少任务依赖它）
        in_degree = {task_id: len(deps) for task_id, deps in self.dependencies.items()}
        
        # 找出所有入度为 0 的任务（没有依赖的任务）
        queue = [task_id for task_id, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            # 取出一个入度为 0 的任务
            task_id = queue.pop(0)
            result.append(task_id)
            
            # 找出所有依赖当前任务的其他任务，减少它们的入度
            for other_id, deps in self.dependencies.items():
                if task_id in deps:
                    in_degree[other_id] -= 1
                    if in_degree[other_id] == 0:
                        queue.append(other_id)
        
        # 如果结果数量不等于任务数量，说明存在循环依赖
        if len(result) != len(self.tasks):
            raise ValueError("检测到循环依赖")
        
        return result
    
    def has_cycle(self) -> bool:
        """检测是否存在循环依赖"""
        try:
            self.get_execution_order()
            return False
        except ValueError:
            return True
