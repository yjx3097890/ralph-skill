"""
任务模型单元测试
"""

from datetime import datetime

import pytest

from ralph.models import (
    LogEntry,
    Task,
    TaskConfig,
    TaskGraph,
    TaskInfo,
    TaskResult,
    TaskStatus,
    TaskType,
)


class TestLogEntry:
    """测试日志条目"""

    def test_create_log_entry(self):
        """测试创建日志条目"""
        entry = LogEntry(
            timestamp=datetime.now(),
            level="info",
            message="测试消息",
            context={"key": "value"}
        )
        
        assert entry.level == "info"
        assert entry.message == "测试消息"
        assert entry.context["key"] == "value"


class TestTaskConfig:
    """测试任务配置"""

    def test_create_task_config(self):
        """测试创建任务配置"""
        config = TaskConfig(
            id="task_1",
            name="测试任务",
            type=TaskType.FEATURE,
            depends_on=["task_0"],
            ai_engine="qwen_code",
            hooks={"pre-test": ["gofmt"]},
            config={"timeout": 300}
        )
        
        assert config.id == "task_1"
        assert config.name == "测试任务"
        assert config.type == TaskType.FEATURE
        assert "task_0" in config.depends_on
        assert config.ai_engine == "qwen_code"
        assert config.max_retries == 3

    def test_task_config_defaults(self):
        """测试任务配置默认值"""
        config = TaskConfig(
            id="task_1",
            name="测试任务",
            type=TaskType.FEATURE
        )
        
        assert config.depends_on == []
        assert config.ai_engine == "qwen_code"
        assert config.hooks == {}
        assert config.config == {}
        assert config.max_retries == 3
        assert config.timeout == 1800


class TestTask:
    """测试任务实体"""

    def test_create_task(self):
        """测试创建任务"""
        now = datetime.now()
        task = Task(
            id="task_1",
            name="测试任务",
            type=TaskType.FEATURE,
            status=TaskStatus.PENDING,
            depends_on=[],
            ai_engine="qwen_code",
            config={},
            created_at=now,
            updated_at=now
        )
        
        assert task.id == "task_1"
        assert task.status == TaskStatus.PENDING
        assert task.retry_count == 0

    def test_add_log(self):
        """测试添加日志"""
        task = Task(
            id="task_1",
            name="测试任务",
            type=TaskType.FEATURE,
            status=TaskStatus.PENDING,
            depends_on=[],
            ai_engine="qwen_code",
            config={},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        task.add_log("info", "测试日志", {"key": "value"})
        
        assert len(task.execution_log) == 1
        assert task.execution_log[0].message == "测试日志"
        assert task.execution_log[0].level == "info"

    def test_update_status(self):
        """测试更新状态"""
        task = Task(
            id="task_1",
            name="测试任务",
            type=TaskType.FEATURE,
            status=TaskStatus.PENDING,
            depends_on=[],
            ai_engine="qwen_code",
            config={},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        old_updated_at = task.updated_at
        task.update_status(TaskStatus.IN_PROGRESS)
        
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.updated_at > old_updated_at
        assert len(task.execution_log) == 1

    def test_increment_retry(self):
        """测试增加重试计数"""
        task = Task(
            id="task_1",
            name="测试任务",
            type=TaskType.FEATURE,
            status=TaskStatus.PENDING,
            depends_on=[],
            ai_engine="qwen_code",
            config={},
            created_at=datetime.now(),
            updated_at=datetime.now(),
            max_retries=3
        )
        
        # 第一次重试
        assert task.increment_retry() is True
        assert task.retry_count == 1
        
        # 第二次重试
        assert task.increment_retry() is True
        assert task.retry_count == 2
        
        # 第三次重试（达到最大值）
        assert task.increment_retry() is False
        assert task.retry_count == 3

    def test_can_execute_no_dependencies(self):
        """测试无依赖任务可以执行"""
        task = Task(
            id="task_1",
            name="测试任务",
            type=TaskType.FEATURE,
            status=TaskStatus.PENDING,
            depends_on=[],
            ai_engine="qwen_code",
            config={},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        assert task.can_execute([]) is True

    def test_can_execute_with_dependencies(self):
        """测试有依赖任务的执行条件"""
        task = Task(
            id="task_2",
            name="测试任务",
            type=TaskType.FEATURE,
            status=TaskStatus.PENDING,
            depends_on=["task_1"],
            ai_engine="qwen_code",
            config={},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # 依赖未完成
        assert task.can_execute([]) is False
        
        # 依赖已完成
        assert task.can_execute(["task_1"]) is True


class TestTaskGraph:
    """测试任务依赖图"""

    def test_get_execution_order_no_dependencies(self):
        """测试无依赖的执行顺序"""
        now = datetime.now()
        tasks = {
            "task_1": Task(
                id="task_1", name="任务1", type=TaskType.FEATURE,
                status=TaskStatus.PENDING, depends_on=[],
                ai_engine="qwen_code", config={},
                created_at=now, updated_at=now
            ),
            "task_2": Task(
                id="task_2", name="任务2", type=TaskType.FEATURE,
                status=TaskStatus.PENDING, depends_on=[],
                ai_engine="qwen_code", config={},
                created_at=now, updated_at=now
            )
        }
        
        graph = TaskGraph(
            tasks=tasks,
            dependencies={"task_1": [], "task_2": []}
        )
        
        order = graph.get_execution_order()
        assert len(order) == 2
        assert set(order) == {"task_1", "task_2"}

    def test_get_execution_order_with_dependencies(self):
        """测试有依赖的执行顺序"""
        now = datetime.now()
        tasks = {
            "task_1": Task(
                id="task_1", name="任务1", type=TaskType.FEATURE,
                status=TaskStatus.PENDING, depends_on=[],
                ai_engine="qwen_code", config={},
                created_at=now, updated_at=now
            ),
            "task_2": Task(
                id="task_2", name="任务2", type=TaskType.FEATURE,
                status=TaskStatus.PENDING, depends_on=["task_1"],
                ai_engine="qwen_code", config={},
                created_at=now, updated_at=now
            ),
            "task_3": Task(
                id="task_3", name="任务3", type=TaskType.FEATURE,
                status=TaskStatus.PENDING, depends_on=["task_2"],
                ai_engine="qwen_code", config={},
                created_at=now, updated_at=now
            )
        }
        
        graph = TaskGraph(
            tasks=tasks,
            dependencies={
                "task_1": [],
                "task_2": ["task_1"],
                "task_3": ["task_2"]
            }
        )
        
        order = graph.get_execution_order()
        assert order == ["task_1", "task_2", "task_3"]

    def test_detect_cycle(self):
        """测试检测循环依赖"""
        now = datetime.now()
        tasks = {
            "task_1": Task(
                id="task_1", name="任务1", type=TaskType.FEATURE,
                status=TaskStatus.PENDING, depends_on=["task_2"],
                ai_engine="qwen_code", config={},
                created_at=now, updated_at=now
            ),
            "task_2": Task(
                id="task_2", name="任务2", type=TaskType.FEATURE,
                status=TaskStatus.PENDING, depends_on=["task_1"],
                ai_engine="qwen_code", config={},
                created_at=now, updated_at=now
            )
        }
        
        graph = TaskGraph(
            tasks=tasks,
            dependencies={
                "task_1": ["task_2"],
                "task_2": ["task_1"]
            }
        )
        
        assert graph.has_cycle() is True
        
        with pytest.raises(ValueError, match="检测到循环依赖"):
            graph.get_execution_order()


class TestTaskResult:
    """测试任务执行结果"""

    def test_create_task_result(self):
        """测试创建任务结果"""
        result = TaskResult(
            task_id="task_1",
            success=True,
            execution_time=10.5,
            output="执行成功",
            errors=[],
            git_commits=["abc123"],
            tests_passed=True
        )
        
        assert result.task_id == "task_1"
        assert result.success is True
        assert result.execution_time == 10.5
        assert result.tests_passed is True
        assert len(result.git_commits) == 1
