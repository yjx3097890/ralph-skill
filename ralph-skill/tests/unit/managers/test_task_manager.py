"""
任务管理器单元测试

测试 TaskManager 的核心功能：
- 任务创建和管理
- 状态机转换
- 状态变更通知
- 依赖关系处理
- 并发安全性
"""

import pytest
import threading
import time
from datetime import datetime

from src.ralph.managers.task_manager import (
    TaskManager,
    TaskStatusTransitionError,
    TaskNotFoundError,
    TaskDependencyError,
)
from src.ralph.models.enums import TaskStatus, TaskType
from src.ralph.models.task import Task, TaskConfig


class TestTaskManagerBasics:
    """测试任务管理器基础功能"""
    
    def test_create_task(self):
        """测试创建任务"""
        manager = TaskManager()
        config = TaskConfig(
            id="task_1",
            name="测试任务",
            type=TaskType.FEATURE,
            ai_engine="qwen_code",
        )
        
        task = manager.create_task(config)
        
        assert task.id == "task_1"
        assert task.name == "测试任务"
        assert task.type == TaskType.FEATURE
        assert task.status == TaskStatus.PENDING
        assert task.ai_engine == "qwen_code"
        assert len(task.execution_log) == 1  # 创建日志
    
    def test_create_duplicate_task(self):
        """测试创建重复 ID 的任务应该失败"""
        manager = TaskManager()
        config = TaskConfig(
            id="task_1",
            name="测试任务",
            type=TaskType.FEATURE,
        )
        
        manager.create_task(config)
        
        with pytest.raises(ValueError, match="任务 ID 已存在"):
            manager.create_task(config)
    
    def test_get_task(self):
        """测试获取任务"""
        manager = TaskManager()
        config = TaskConfig(
            id="task_1",
            name="测试任务",
            type=TaskType.FEATURE,
        )
        
        created_task = manager.create_task(config)
        retrieved_task = manager.get_task("task_1")
        
        assert retrieved_task.id == created_task.id
        assert retrieved_task.name == created_task.name
    
    def test_get_nonexistent_task(self):
        """测试获取不存在的任务应该失败"""
        manager = TaskManager()
        
        with pytest.raises(TaskNotFoundError, match="任务不存在"):
            manager.get_task("nonexistent")
    
    def test_list_tasks(self):
        """测试列出所有任务"""
        manager = TaskManager()
        
        # 创建多个任务
        for i in range(3):
            config = TaskConfig(
                id=f"task_{i}",
                name=f"任务 {i}",
                type=TaskType.FEATURE,
            )
            manager.create_task(config)
        
        tasks = manager.list_tasks()
        
        assert len(tasks) == 3
        assert all(isinstance(t, Task) for t in tasks)
    
    def test_list_tasks_by_status(self):
        """测试按状态过滤任务"""
        manager = TaskManager()
        
        # 创建不同状态的任务
        config1 = TaskConfig(id="task_1", name="任务 1", type=TaskType.FEATURE)
        config2 = TaskConfig(id="task_2", name="任务 2", type=TaskType.FEATURE)
        
        task1 = manager.create_task(config1)
        task2 = manager.create_task(config2)
        
        # 更新一个任务的状态
        manager.update_task_status("task_1", TaskStatus.IN_PROGRESS)
        
        # 测试过滤
        pending_tasks = manager.list_tasks(status=TaskStatus.PENDING)
        in_progress_tasks = manager.list_tasks(status=TaskStatus.IN_PROGRESS)
        
        assert len(pending_tasks) == 1
        assert pending_tasks[0].id == "task_2"
        assert len(in_progress_tasks) == 1
        assert in_progress_tasks[0].id == "task_1"
    
    def test_delete_task(self):
        """测试删除任务"""
        manager = TaskManager()
        config = TaskConfig(
            id="task_1",
            name="测试任务",
            type=TaskType.FEATURE,
        )
        
        manager.create_task(config)
        manager.delete_task("task_1")
        
        with pytest.raises(TaskNotFoundError):
            manager.get_task("task_1")
    
    def test_delete_nonexistent_task(self):
        """测试删除不存在的任务应该失败"""
        manager = TaskManager()
        
        with pytest.raises(TaskNotFoundError, match="任务不存在"):
            manager.delete_task("nonexistent")


class TestTaskStatusMachine:
    """测试任务状态机"""
    
    def test_valid_transition_pending_to_in_progress(self):
        """测试合法转换: PENDING -> IN_PROGRESS"""
        manager = TaskManager()
        config = TaskConfig(id="task_1", name="任务", type=TaskType.FEATURE)
        
        task = manager.create_task(config)
        updated_task = manager.update_task_status("task_1", TaskStatus.IN_PROGRESS)
        
        assert updated_task.status == TaskStatus.IN_PROGRESS
        assert len(updated_task.execution_log) == 2  # 创建 + 状态变更
    
    def test_valid_transition_in_progress_to_testing(self):
        """测试合法转换: IN_PROGRESS -> TESTING"""
        manager = TaskManager()
        config = TaskConfig(id="task_1", name="任务", type=TaskType.FEATURE)
        
        manager.create_task(config)
        manager.update_task_status("task_1", TaskStatus.IN_PROGRESS)
        updated_task = manager.update_task_status("task_1", TaskStatus.TESTING)
        
        assert updated_task.status == TaskStatus.TESTING
    
    def test_valid_transition_testing_to_completed(self):
        """测试合法转换: TESTING -> COMPLETED"""
        manager = TaskManager()
        config = TaskConfig(id="task_1", name="任务", type=TaskType.FEATURE)
        
        manager.create_task(config)
        manager.update_task_status("task_1", TaskStatus.IN_PROGRESS)
        manager.update_task_status("task_1", TaskStatus.TESTING)
        updated_task = manager.update_task_status("task_1", TaskStatus.COMPLETED)
        
        assert updated_task.status == TaskStatus.COMPLETED
    
    def test_valid_transition_testing_to_in_progress(self):
        """测试合法转换: TESTING -> IN_PROGRESS (测试失败，返回修复)"""
        manager = TaskManager()
        config = TaskConfig(id="task_1", name="任务", type=TaskType.FEATURE)
        
        manager.create_task(config)
        manager.update_task_status("task_1", TaskStatus.IN_PROGRESS)
        manager.update_task_status("task_1", TaskStatus.TESTING)
        updated_task = manager.update_task_status("task_1", TaskStatus.IN_PROGRESS, "测试失败，需要修复")
        
        assert updated_task.status == TaskStatus.IN_PROGRESS
    
    def test_valid_transition_in_progress_to_failed(self):
        """测试合法转换: IN_PROGRESS -> FAILED"""
        manager = TaskManager()
        config = TaskConfig(id="task_1", name="任务", type=TaskType.FEATURE)
        
        manager.create_task(config)
        manager.update_task_status("task_1", TaskStatus.IN_PROGRESS)
        updated_task = manager.update_task_status("task_1", TaskStatus.FAILED, "执行失败")
        
        assert updated_task.status == TaskStatus.FAILED
    
    def test_invalid_transition_pending_to_testing(self):
        """测试非法转换: PENDING -> TESTING"""
        manager = TaskManager()
        config = TaskConfig(id="task_1", name="任务", type=TaskType.FEATURE)
        
        manager.create_task(config)
        
        with pytest.raises(TaskStatusTransitionError, match="不合法的状态转换"):
            manager.update_task_status("task_1", TaskStatus.TESTING)
    
    def test_invalid_transition_completed_to_in_progress(self):
        """测试非法转换: COMPLETED -> IN_PROGRESS"""
        manager = TaskManager()
        config = TaskConfig(id="task_1", name="任务", type=TaskType.FEATURE)
        
        manager.create_task(config)
        manager.update_task_status("task_1", TaskStatus.IN_PROGRESS)
        manager.update_task_status("task_1", TaskStatus.TESTING)
        manager.update_task_status("task_1", TaskStatus.COMPLETED)
        
        with pytest.raises(TaskStatusTransitionError, match="不合法的状态转换"):
            manager.update_task_status("task_1", TaskStatus.IN_PROGRESS)
    
    def test_invalid_transition_failed_to_in_progress(self):
        """测试非法转换: FAILED -> IN_PROGRESS"""
        manager = TaskManager()
        config = TaskConfig(id="task_1", name="任务", type=TaskType.FEATURE)
        
        manager.create_task(config)
        manager.update_task_status("task_1", TaskStatus.IN_PROGRESS)
        manager.update_task_status("task_1", TaskStatus.FAILED)
        
        with pytest.raises(TaskStatusTransitionError, match="不合法的状态转换"):
            manager.update_task_status("task_1", TaskStatus.IN_PROGRESS)
    
    def test_idempotent_status_update(self):
        """测试幂等的状态更新（设置为相同状态）"""
        manager = TaskManager()
        config = TaskConfig(id="task_1", name="任务", type=TaskType.FEATURE)
        
        manager.create_task(config)
        manager.update_task_status("task_1", TaskStatus.IN_PROGRESS)
        
        # 再次设置为相同状态应该成功
        updated_task = manager.update_task_status("task_1", TaskStatus.IN_PROGRESS)
        assert updated_task.status == TaskStatus.IN_PROGRESS


class TestTaskCancellation:
    """测试任务取消功能"""
    
    def test_cancel_pending_task(self):
        """测试取消 PENDING 状态的任务"""
        manager = TaskManager()
        config = TaskConfig(id="task_1", name="任务", type=TaskType.FEATURE)
        
        manager.create_task(config)
        cancelled_task = manager.cancel_task("task_1", "用户取消")
        
        assert cancelled_task.status == TaskStatus.FAILED
    
    def test_cancel_in_progress_task(self):
        """测试取消 IN_PROGRESS 状态的任务"""
        manager = TaskManager()
        config = TaskConfig(id="task_1", name="任务", type=TaskType.FEATURE)
        
        manager.create_task(config)
        manager.update_task_status("task_1", TaskStatus.IN_PROGRESS)
        cancelled_task = manager.cancel_task("task_1", "超时")
        
        assert cancelled_task.status == TaskStatus.FAILED
    
    def test_cannot_cancel_completed_task(self):
        """测试不能取消已完成的任务"""
        manager = TaskManager()
        config = TaskConfig(id="task_1", name="任务", type=TaskType.FEATURE)
        
        manager.create_task(config)
        manager.update_task_status("task_1", TaskStatus.IN_PROGRESS)
        manager.update_task_status("task_1", TaskStatus.TESTING)
        manager.update_task_status("task_1", TaskStatus.COMPLETED)
        
        with pytest.raises(TaskStatusTransitionError, match="无法取消已完成或已失败的任务"):
            manager.cancel_task("task_1")
    
    def test_cannot_cancel_failed_task(self):
        """测试不能取消已失败的任务"""
        manager = TaskManager()
        config = TaskConfig(id="task_1", name="任务", type=TaskType.FEATURE)
        
        manager.create_task(config)
        manager.update_task_status("task_1", TaskStatus.IN_PROGRESS)
        manager.update_task_status("task_1", TaskStatus.FAILED)
        
        with pytest.raises(TaskStatusTransitionError, match="无法取消已完成或已失败的任务"):
            manager.cancel_task("task_1")


class TestStatusChangeNotification:
    """测试状态变更通知机制"""
    
    def test_register_callback(self):
        """测试注册回调函数"""
        manager = TaskManager()
        callback_called = []
        
        def callback(task, old_status, new_status):
            callback_called.append((task.id, old_status, new_status))
        
        manager.register_status_change_callback(callback)
        
        config = TaskConfig(id="task_1", name="任务", type=TaskType.FEATURE)
        manager.create_task(config)
        manager.update_task_status("task_1", TaskStatus.IN_PROGRESS)
        
        assert len(callback_called) == 1
        assert callback_called[0] == ("task_1", TaskStatus.PENDING, TaskStatus.IN_PROGRESS)
    
    def test_multiple_callbacks(self):
        """测试注册多个回调函数"""
        manager = TaskManager()
        callback1_called = []
        callback2_called = []
        
        def callback1(task, old_status, new_status):
            callback1_called.append(task.id)
        
        def callback2(task, old_status, new_status):
            callback2_called.append(task.id)
        
        manager.register_status_change_callback(callback1)
        manager.register_status_change_callback(callback2)
        
        config = TaskConfig(id="task_1", name="任务", type=TaskType.FEATURE)
        manager.create_task(config)
        manager.update_task_status("task_1", TaskStatus.IN_PROGRESS)
        
        assert len(callback1_called) == 1
        assert len(callback2_called) == 1
    
    def test_unregister_callback(self):
        """测试注销回调函数"""
        manager = TaskManager()
        callback_called = []
        
        def callback(task, old_status, new_status):
            callback_called.append(task.id)
        
        manager.register_status_change_callback(callback)
        manager.unregister_status_change_callback(callback)
        
        config = TaskConfig(id="task_1", name="任务", type=TaskType.FEATURE)
        manager.create_task(config)
        manager.update_task_status("task_1", TaskStatus.IN_PROGRESS)
        
        assert len(callback_called) == 0
    
    def test_callback_exception_handling(self):
        """测试回调函数异常处理（不应中断执行）"""
        manager = TaskManager()
        
        def failing_callback(task, old_status, new_status):
            raise Exception("回调失败")
        
        manager.register_status_change_callback(failing_callback)
        
        config = TaskConfig(id="task_1", name="任务", type=TaskType.FEATURE)
        manager.create_task(config)
        
        # 即使回调失败，状态更新也应该成功
        updated_task = manager.update_task_status("task_1", TaskStatus.IN_PROGRESS)
        assert updated_task.status == TaskStatus.IN_PROGRESS


class TestTaskDependencies:
    """测试任务依赖管理"""
    
    def test_build_task_graph(self):
        """测试构建任务依赖图"""
        manager = TaskManager()
        
        config1 = TaskConfig(id="task_1", name="任务 1", type=TaskType.FEATURE)
        config2 = TaskConfig(id="task_2", name="任务 2", type=TaskType.FEATURE, depends_on=["task_1"])
        
        manager.create_task(config1)
        manager.create_task(config2)
        
        graph = manager.build_task_graph()
        
        assert len(graph.tasks) == 2
        assert "task_1" in graph.tasks
        assert "task_2" in graph.tasks
        assert graph.dependencies["task_2"] == ["task_1"]
    
    def test_validate_dependencies_no_cycle(self):
        """测试验证无循环依赖"""
        manager = TaskManager()
        
        config1 = TaskConfig(id="task_1", name="任务 1", type=TaskType.FEATURE)
        config2 = TaskConfig(id="task_2", name="任务 2", type=TaskType.FEATURE, depends_on=["task_1"])
        config3 = TaskConfig(id="task_3", name="任务 3", type=TaskType.FEATURE, depends_on=["task_2"])
        
        manager.create_task(config1)
        manager.create_task(config2)
        manager.create_task(config3)
        
        assert manager.validate_dependencies() is True
    
    def test_get_executable_tasks(self):
        """测试获取可执行任务"""
        manager = TaskManager()
        
        config1 = TaskConfig(id="task_1", name="任务 1", type=TaskType.FEATURE)
        config2 = TaskConfig(id="task_2", name="任务 2", type=TaskType.FEATURE, depends_on=["task_1"])
        config3 = TaskConfig(id="task_3", name="任务 3", type=TaskType.FEATURE)
        
        manager.create_task(config1)
        manager.create_task(config2)
        manager.create_task(config3)
        
        # 初始状态：task_1 和 task_3 可执行（无依赖）
        executable = manager.get_executable_tasks()
        executable_ids = [t.id for t in executable]
        
        assert len(executable) == 2
        assert "task_1" in executable_ids
        assert "task_3" in executable_ids
        assert "task_2" not in executable_ids
        
        # 完成 task_1 后，task_2 变为可执行
        manager.update_task_status("task_1", TaskStatus.IN_PROGRESS)
        manager.update_task_status("task_1", TaskStatus.TESTING)
        manager.update_task_status("task_1", TaskStatus.COMPLETED)
        
        executable = manager.get_executable_tasks()
        executable_ids = [t.id for t in executable]
        
        assert "task_2" in executable_ids


class TestConcurrency:
    """测试并发安全性"""
    
    def test_concurrent_task_creation(self):
        """测试并发创建任务"""
        manager = TaskManager()
        errors = []
        
        def create_task(task_id):
            try:
                config = TaskConfig(
                    id=task_id,
                    name=f"任务 {task_id}",
                    type=TaskType.FEATURE,
                )
                manager.create_task(config)
            except Exception as e:
                errors.append(e)
        
        # 创建多个线程并发创建任务
        threads = []
        for i in range(10):
            thread = threading.Thread(target=create_task, args=(f"task_{i}",))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证所有任务都创建成功
        assert len(errors) == 0
        assert len(manager.list_tasks()) == 10
    
    def test_concurrent_status_updates(self):
        """测试并发更新任务状态"""
        manager = TaskManager()
        config = TaskConfig(id="task_1", name="任务", type=TaskType.FEATURE)
        manager.create_task(config)
        
        results = []
        
        def update_status():
            try:
                manager.update_task_status("task_1", TaskStatus.IN_PROGRESS)
                results.append("success")
            except Exception as e:
                results.append(f"error: {e}")
        
        # 创建多个线程并发更新状态
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=update_status)
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证最终状态正确
        task = manager.get_task("task_1")
        assert task.status == TaskStatus.IN_PROGRESS


class TestStatistics:
    """测试统计功能"""
    
    def test_get_statistics(self):
        """测试获取任务统计信息"""
        manager = TaskManager()
        
        # 创建不同状态的任务
        for i in range(5):
            config = TaskConfig(
                id=f"task_{i}",
                name=f"任务 {i}",
                type=TaskType.FEATURE,
            )
            manager.create_task(config)
        
        # 更新部分任务状态
        manager.update_task_status("task_0", TaskStatus.IN_PROGRESS)
        manager.update_task_status("task_1", TaskStatus.IN_PROGRESS)
        manager.update_task_status("task_1", TaskStatus.TESTING)
        manager.update_task_status("task_2", TaskStatus.IN_PROGRESS)
        manager.update_task_status("task_2", TaskStatus.TESTING)
        manager.update_task_status("task_2", TaskStatus.COMPLETED)
        manager.update_task_status("task_3", TaskStatus.IN_PROGRESS)
        manager.update_task_status("task_3", TaskStatus.FAILED)
        
        stats = manager.get_statistics()
        
        assert stats["total"] == 5
        assert stats["pending"] == 1  # task_4
        assert stats["in_progress"] == 1  # task_0
        assert stats["testing"] == 1  # task_1
        assert stats["completed"] == 1  # task_2
        assert stats["failed"] == 1  # task_3
