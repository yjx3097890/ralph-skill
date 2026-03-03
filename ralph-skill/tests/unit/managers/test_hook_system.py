"""
钩子系统单元测试

测试钩子系统的核心功能：
- 钩子注册和注销
- 钩子执行和超时控制
- 钩子重试机制
- 钩子执行历史记录
- 并发安全性
"""

import os
import tempfile
import time
from datetime import datetime
from pathlib import Path

import pytest

from ralph.managers.hook_system import (
    HookExecutionError,
    HookSystem,
    HookTimeoutError,
)
from ralph.models.enums import HookType
from ralph.models.hook import HookConfig, HookContext, HookResult


class TestHookSystemBasics:
    """测试钩子系统基础功能"""
    
    def test_hook_system_initialization(self):
        """测试钩子系统初始化"""
        hook_system = HookSystem()
        
        # 验证所有钩子类型都已初始化
        for hook_type in HookType:
            hooks = hook_system.get_hooks(hook_type)
            assert hooks == []
        
        # 验证统计信息
        stats = hook_system.get_statistics()
        assert stats["total_registered_hooks"] == 0
        assert stats["total_executions"] == 0
    
    def test_register_hook(self):
        """测试钩子注册"""
        hook_system = HookSystem()
        
        config = HookConfig(
            name="test_hook",
            hook_type=HookType.PRE_TEST,
            command="echo 'test'",
            timeout=60,
        )
        
        hook_system.register_hook(config)
        
        # 验证钩子已注册
        hooks = hook_system.get_hooks(HookType.PRE_TEST)
        assert len(hooks) == 1
        assert hooks[0].name == "test_hook"
        assert hooks[0].command == "echo 'test'"
    
    def test_register_duplicate_hook_name(self):
        """测试注册重复的钩子名称"""
        hook_system = HookSystem()
        
        config1 = HookConfig(
            name="duplicate_hook",
            hook_type=HookType.PRE_TEST,
            command="echo 'first'",
        )
        
        config2 = HookConfig(
            name="duplicate_hook",
            hook_type=HookType.PRE_TEST,
            command="echo 'second'",
        )
        
        hook_system.register_hook(config1)
        
        # 应该抛出 ValueError
        with pytest.raises(ValueError, match="钩子名称已存在"):
            hook_system.register_hook(config2)
    
    def test_unregister_hook(self):
        """测试钩子注销"""
        hook_system = HookSystem()
        
        config = HookConfig(
            name="test_hook",
            hook_type=HookType.PRE_TEST,
            command="echo 'test'",
        )
        
        hook_system.register_hook(config)
        
        # 注销钩子
        result = hook_system.unregister_hook(HookType.PRE_TEST, "test_hook")
        assert result is True
        
        # 验证钩子已注销
        hooks = hook_system.get_hooks(HookType.PRE_TEST)
        assert len(hooks) == 0
    
    def test_unregister_nonexistent_hook(self):
        """测试注销不存在的钩子"""
        hook_system = HookSystem()
        
        result = hook_system.unregister_hook(HookType.PRE_TEST, "nonexistent")
        assert result is False


class TestHookExecution:
    """测试钩子执行功能"""
    
    def test_execute_simple_hook(self):
        """测试执行简单钩子"""
        hook_system = HookSystem()
        
        config = HookConfig(
            name="echo_hook",
            hook_type=HookType.PRE_TEST,
            command="echo 'Hello, World!'",
            timeout=10,
        )
        
        hook_system.register_hook(config)
        
        context = HookContext(
            hook_type=HookType.PRE_TEST,
            task_id="task_1",
            task_name="测试任务",
            timestamp=datetime.now(),
            working_directory=os.getcwd(),
        )
        
        results = hook_system.execute_hooks(HookType.PRE_TEST, context)
        
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].hook_name == "echo_hook"
        assert "Hello, World!" in results[0].output
        assert results[0].exit_code == 0
    
    def test_execute_failing_hook(self):
        """测试执行失败的钩子"""
        hook_system = HookSystem()
        
        config = HookConfig(
            name="failing_hook",
            hook_type=HookType.PRE_TEST,
            command="exit 1",  # 故意失败
            timeout=10,
            continue_on_failure=False,
        )
        
        hook_system.register_hook(config)
        
        context = HookContext(
            hook_type=HookType.PRE_TEST,
            task_id="task_1",
            task_name="测试任务",
            timestamp=datetime.now(),
            working_directory=os.getcwd(),
        )
        
        # 应该抛出 HookExecutionError
        with pytest.raises(HookExecutionError, match="钩子执行失败"):
            hook_system.execute_hooks(HookType.PRE_TEST, context)
    
    def test_execute_failing_hook_with_continue(self):
        """测试执行失败但允许继续的钩子"""
        hook_system = HookSystem()
        
        config = HookConfig(
            name="failing_hook",
            hook_type=HookType.PRE_TEST,
            command="exit 1",
            timeout=10,
            continue_on_failure=True,  # 允许继续
        )
        
        hook_system.register_hook(config)
        
        context = HookContext(
            hook_type=HookType.PRE_TEST,
            task_id="task_1",
            task_name="测试任务",
            timestamp=datetime.now(),
            working_directory=os.getcwd(),
        )
        
        # 不应该抛出异常
        results = hook_system.execute_hooks(HookType.PRE_TEST, context)
        
        assert len(results) == 1
        assert results[0].success is False
        assert results[0].exit_code == 1
    
    def test_execute_multiple_hooks(self):
        """测试执行多个钩子"""
        hook_system = HookSystem()
        
        # 注册多个钩子
        for i in range(3):
            config = HookConfig(
                name=f"hook_{i}",
                hook_type=HookType.PRE_TEST,
                command=f"echo 'Hook {i}'",
                timeout=10,
            )
            hook_system.register_hook(config)
        
        context = HookContext(
            hook_type=HookType.PRE_TEST,
            task_id="task_1",
            task_name="测试任务",
            timestamp=datetime.now(),
            working_directory=os.getcwd(),
        )
        
        results = hook_system.execute_hooks(HookType.PRE_TEST, context)
        
        assert len(results) == 3
        assert all(r.success for r in results)
        assert [r.hook_name for r in results] == ["hook_0", "hook_1", "hook_2"]
    
    def test_execute_no_hooks(self):
        """测试执行没有注册钩子的类型"""
        hook_system = HookSystem()
        
        context = HookContext(
            hook_type=HookType.PRE_TEST,
            task_id="task_1",
            task_name="测试任务",
            timestamp=datetime.now(),
            working_directory=os.getcwd(),
        )
        
        results = hook_system.execute_hooks(HookType.PRE_TEST, context)
        
        assert results == []


class TestHookTimeout:
    """测试钩子超时功能"""
    
    def test_hook_timeout(self):
        """测试钩子超时"""
        hook_system = HookSystem()
        
        config = HookConfig(
            name="slow_hook",
            hook_type=HookType.PRE_TEST,
            command="sleep 5",  # 睡眠 5 秒
            timeout=1,  # 超时 1 秒
            continue_on_failure=True,
        )
        
        hook_system.register_hook(config)
        
        context = HookContext(
            hook_type=HookType.PRE_TEST,
            task_id="task_1",
            task_name="测试任务",
            timestamp=datetime.now(),
            working_directory=os.getcwd(),
        )
        
        results = hook_system.execute_hooks(HookType.PRE_TEST, context)
        
        assert len(results) == 1
        assert results[0].success is False
        assert "超时" in results[0].error
        assert results[0].execution_time >= 1.0


class TestHookRetry:
    """测试钩子重试功能"""
    
    def test_hook_retry_success(self):
        """测试钩子重试成功"""
        hook_system = HookSystem()
        
        # 创建一个临时文件来跟踪重试次数
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            counter_file = f.name
            f.write("0")
        
        try:
            # 创建一个脚本，前两次失败，第三次成功
            script = f"""
import sys
with open('{counter_file}', 'r') as f:
    count = int(f.read())
count += 1
with open('{counter_file}', 'w') as f:
    f.write(str(count))
if count < 3:
    sys.exit(1)
else:
    print('Success on attempt', count)
    sys.exit(0)
"""
            
            config = HookConfig(
                name="retry_hook",
                hook_type=HookType.PRE_TEST,
                command=f"python -c \"{script}\"",
                timeout=10,
                max_retries=3,
                retry_delay=0,  # 不延迟以加快测试
            )
            
            hook_system.register_hook(config)
            
            context = HookContext(
                hook_type=HookType.PRE_TEST,
                task_id="task_1",
                task_name="测试任务",
                timestamp=datetime.now(),
                working_directory=os.getcwd(),
            )
            
            results = hook_system.execute_hooks(HookType.PRE_TEST, context)
            
            assert len(results) == 1
            assert results[0].success is True
            
            # 验证执行历史中的重试次数
            history = hook_system.get_execution_history()
            assert len(history) == 1
            assert history[0].retry_count == 2  # 重试了 2 次（第 3 次成功）
        
        finally:
            # 清理临时文件
            if os.path.exists(counter_file):
                os.unlink(counter_file)
    
    def test_hook_retry_exhausted(self):
        """测试钩子重试次数用尽"""
        hook_system = HookSystem()
        
        config = HookConfig(
            name="always_fail_hook",
            hook_type=HookType.PRE_TEST,
            command="exit 1",  # 总是失败
            timeout=10,
            max_retries=2,
            retry_delay=0,
            continue_on_failure=True,
        )
        
        hook_system.register_hook(config)
        
        context = HookContext(
            hook_type=HookType.PRE_TEST,
            task_id="task_1",
            task_name="测试任务",
            timestamp=datetime.now(),
            working_directory=os.getcwd(),
        )
        
        results = hook_system.execute_hooks(HookType.PRE_TEST, context)
        
        assert len(results) == 1
        assert results[0].success is False
        
        # 验证执行历史中的重试次数
        history = hook_system.get_execution_history()
        assert len(history) == 1
        assert history[0].retry_count == 2  # 重试了 2 次


class TestHookExecutionHistory:
    """测试钩子执行历史功能"""
    
    def test_execution_history_recording(self):
        """测试执行历史记录"""
        hook_system = HookSystem()
        
        config = HookConfig(
            name="test_hook",
            hook_type=HookType.PRE_TEST,
            command="echo 'test'",
            timeout=10,
        )
        
        hook_system.register_hook(config)
        
        context = HookContext(
            hook_type=HookType.PRE_TEST,
            task_id="task_1",
            task_name="测试任务",
            timestamp=datetime.now(),
            working_directory=os.getcwd(),
        )
        
        hook_system.execute_hooks(HookType.PRE_TEST, context)
        
        # 获取执行历史
        history = hook_system.get_execution_history()
        
        assert len(history) == 1
        assert history[0].hook_name == "test_hook"
        assert history[0].hook_type == HookType.PRE_TEST
        assert history[0].task_id == "task_1"
        assert history[0].is_completed is True
        assert history[0].is_successful is True
    
    def test_execution_history_filtering(self):
        """测试执行历史过滤"""
        hook_system = HookSystem()
        
        # 注册多个钩子
        for hook_type in [HookType.PRE_TEST, HookType.POST_TEST]:
            config = HookConfig(
                name=f"{hook_type.value}_hook",
                hook_type=hook_type,
                command="echo 'test'",
                timeout=10,
            )
            hook_system.register_hook(config)
        
        # 执行不同类型的钩子
        for hook_type in [HookType.PRE_TEST, HookType.POST_TEST]:
            context = HookContext(
                hook_type=hook_type,
                task_id=f"task_{hook_type.value}",
                task_name="测试任务",
                timestamp=datetime.now(),
                working_directory=os.getcwd(),
            )
            hook_system.execute_hooks(hook_type, context)
        
        # 按任务 ID 过滤
        history = hook_system.get_execution_history(task_id="task_pre-test")
        assert len(history) == 1
        assert history[0].task_id == "task_pre-test"
        
        # 按钩子类型过滤
        history = hook_system.get_execution_history(hook_type=HookType.POST_TEST)
        assert len(history) == 1
        assert history[0].hook_type == HookType.POST_TEST
        
        # 限制结果数量
        history = hook_system.get_execution_history(limit=1)
        assert len(history) == 1
    
    def test_clear_execution_history(self):
        """测试清空执行历史"""
        hook_system = HookSystem()
        
        config = HookConfig(
            name="test_hook",
            hook_type=HookType.PRE_TEST,
            command="echo 'test'",
            timeout=10,
        )
        
        hook_system.register_hook(config)
        
        context = HookContext(
            hook_type=HookType.PRE_TEST,
            task_id="task_1",
            task_name="测试任务",
            timestamp=datetime.now(),
            working_directory=os.getcwd(),
        )
        
        hook_system.execute_hooks(HookType.PRE_TEST, context)
        
        # 验证历史存在
        assert len(hook_system.get_execution_history()) == 1
        
        # 清空历史
        hook_system.clear_execution_history()
        
        # 验证历史已清空
        assert len(hook_system.get_execution_history()) == 0


class TestHookStatistics:
    """测试钩子统计功能"""
    
    def test_statistics(self):
        """测试统计信息"""
        hook_system = HookSystem()
        
        # 注册多个钩子
        for i in range(2):
            config = HookConfig(
                name=f"pre_test_hook_{i}",
                hook_type=HookType.PRE_TEST,
                command="echo 'test'",
                timeout=10,
            )
            hook_system.register_hook(config)
        
        config = HookConfig(
            name="post_test_hook",
            hook_type=HookType.POST_TEST,
            command="echo 'test'",
            timeout=10,
        )
        hook_system.register_hook(config)
        
        # 执行钩子
        context = HookContext(
            hook_type=HookType.PRE_TEST,
            task_id="task_1",
            task_name="测试任务",
            timestamp=datetime.now(),
            working_directory=os.getcwd(),
        )
        hook_system.execute_hooks(HookType.PRE_TEST, context)
        
        # 获取统计信息
        stats = hook_system.get_statistics()
        
        assert stats["total_registered_hooks"] == 3
        assert stats["hooks_by_type"]["pre-test"] == 2
        assert stats["hooks_by_type"]["post-test"] == 1
        assert stats["total_executions"] == 2
        assert stats["successful_executions"] == 2
        assert stats["failed_executions"] == 0
        assert stats["success_rate"] == 100.0


class TestHookConfig:
    """测试钩子配置验证"""
    
    def test_invalid_timeout(self):
        """测试无效的超时配置"""
        with pytest.raises(ValueError, match="超时时间必须大于 0"):
            HookConfig(
                name="test_hook",
                hook_type=HookType.PRE_TEST,
                command="echo 'test'",
                timeout=0,
            )
    
    def test_invalid_max_retries(self):
        """测试无效的最大重试次数"""
        with pytest.raises(ValueError, match="最大重试次数不能为负数"):
            HookConfig(
                name="test_hook",
                hook_type=HookType.PRE_TEST,
                command="echo 'test'",
                max_retries=-1,
            )
    
    def test_invalid_retry_delay(self):
        """测试无效的重试延迟"""
        with pytest.raises(ValueError, match="重试延迟不能为负数"):
            HookConfig(
                name="test_hook",
                hook_type=HookType.PRE_TEST,
                command="echo 'test'",
                retry_delay=-1,
            )


class TestHookEnvironment:
    """测试钩子环境变量"""
    
    def test_hook_with_environment_variables(self):
        """测试带环境变量的钩子"""
        hook_system = HookSystem()
        
        config = HookConfig(
            name="env_hook",
            hook_type=HookType.PRE_TEST,
            command="echo $TEST_VAR",
            timeout=10,
            environment={"TEST_VAR": "test_value"},
        )
        
        hook_system.register_hook(config)
        
        context = HookContext(
            hook_type=HookType.PRE_TEST,
            task_id="task_1",
            task_name="测试任务",
            timestamp=datetime.now(),
            working_directory=os.getcwd(),
        )
        
        results = hook_system.execute_hooks(HookType.PRE_TEST, context)
        
        assert len(results) == 1
        assert results[0].success is True
        assert "test_value" in results[0].output

