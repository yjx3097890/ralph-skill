"""
AI 引擎适配器单元测试

测试 AI 引擎适配器的核心功能：
- 引擎创建和初始化
- 代码生成、重构和错误修复
- 引擎切换和状态管理
- 故障转移机制
"""

import pytest
from datetime import datetime

from ralph.adapters import (
    AIEngineAdapter,
    AIEngineManager,
    CodeResult,
    EngineConfig,
    EngineStatus,
    QwenCodeAdapter,
    AiderAdapter,
    ClaudeAdapter,
    GPT4Adapter,
)
from ralph.models.enums import EngineType, ErrorCategory


class TestEngineConfig:
    """测试引擎配置"""
    
    def test_engine_config_creation(self):
        """测试引擎配置创建"""
        config = EngineConfig(
            engine_type=EngineType.QWEN_CODE,
            api_key="test-key",
            model_name="qwen-coder",
            temperature=0.7,
            max_tokens=2048
        )
        
        assert config.engine_type == EngineType.QWEN_CODE
        assert config.api_key == "test-key"
        assert config.model_name == "qwen-coder"
        assert config.temperature == 0.7
        assert config.max_tokens == 2048
    
    def test_engine_config_defaults(self):
        """测试引擎配置默认值"""
        config = EngineConfig(engine_type=EngineType.CLAUDE)
        
        assert config.temperature == 0.7
        assert config.max_tokens == 4096
        assert config.timeout == 60
        assert config.retry_count == 3


class TestCodeResult:
    """测试代码结果"""
    
    def test_code_result_creation(self):
        """测试代码结果创建"""
        result = CodeResult(
            success=True,
            code="def hello(): pass",
            explanation="生成了一个简单的函数",
            changes=["添加了 hello 函数"],
            warnings=["函数体为空"],
            execution_time=1.5,
            tokens_used=100,
            cost=0.01
        )
        
        assert result.success is True
        assert result.code == "def hello(): pass"
        assert len(result.changes) == 1
        assert len(result.warnings) == 1
        assert result.execution_time == 1.5
        assert result.tokens_used == 100
        assert result.cost == 0.01


class TestEngineStatus:
    """测试引擎状态"""
    
    def test_engine_status_creation(self):
        """测试引擎状态创建"""
        status = EngineStatus(
            engine_type=EngineType.GPT4,
            is_available=True,
            total_calls=10,
            total_tokens=5000,
            total_cost=2.5
        )
        
        assert status.engine_type == EngineType.GPT4
        assert status.is_available is True
        assert status.total_calls == 10
        assert status.total_tokens == 5000
        assert status.total_cost == 2.5


class TestAIEngineAdapter:
    """测试 AI 引擎适配器基类"""
    
    def test_adapter_factory_qwen_code(self):
        """测试创建 Qwen Code 适配器"""
        config = EngineConfig(engine_type=EngineType.QWEN_CODE)
        adapter = AIEngineAdapter.create(EngineType.QWEN_CODE, config)
        
        assert isinstance(adapter, QwenCodeAdapter)
        assert adapter.config.engine_type == EngineType.QWEN_CODE
    
    def test_adapter_factory_aider(self):
        """测试创建 Aider 适配器"""
        config = EngineConfig(engine_type=EngineType.AIDER)
        adapter = AIEngineAdapter.create(EngineType.AIDER, config)
        
        assert isinstance(adapter, AiderAdapter)
        assert adapter.config.engine_type == EngineType.AIDER
    
    def test_adapter_factory_claude(self):
        """测试创建 Claude 适配器"""
        config = EngineConfig(engine_type=EngineType.CLAUDE)
        adapter = AIEngineAdapter.create(EngineType.CLAUDE, config)
        
        assert isinstance(adapter, ClaudeAdapter)
        assert adapter.config.engine_type == EngineType.CLAUDE
    
    def test_adapter_factory_gpt4(self):
        """测试创建 GPT-4 适配器"""
        config = EngineConfig(engine_type=EngineType.GPT4)
        adapter = AIEngineAdapter.create(EngineType.GPT4, config)
        
        assert isinstance(adapter, GPT4Adapter)
        assert adapter.config.engine_type == EngineType.GPT4
    
    def test_adapter_factory_invalid_type(self):
        """测试创建不支持的引擎类型"""
        config = EngineConfig(engine_type=EngineType.QWEN_CODE)
        
        # 模拟无效的引擎类型
        with pytest.raises(ValueError, match="不支持的引擎类型"):
            # 这里需要传入一个无效的枚举值，但由于枚举限制，我们测试异常处理逻辑
            AIEngineAdapter.create("invalid_engine", config)
    
    def test_update_status(self):
        """测试更新引擎状态"""
        config = EngineConfig(engine_type=EngineType.QWEN_CODE)
        adapter = QwenCodeAdapter(config)
        
        # 初始状态
        assert adapter.status.total_calls == 0
        assert adapter.status.total_tokens == 0
        assert adapter.status.total_cost == 0.0
        
        # 更新状态
        adapter.update_status(tokens_used=100, cost=0.05)
        
        assert adapter.status.total_calls == 1
        assert adapter.status.total_tokens == 100
        assert adapter.status.total_cost == 0.05
        assert adapter.status.last_used is not None
        
        # 再次更新
        adapter.update_status(tokens_used=200, cost=0.10)
        
        assert adapter.status.total_calls == 2
        assert adapter.status.total_tokens == 300
        assert abs(adapter.status.total_cost - 0.15) < 0.001  # 使用浮点数比较
    
    def test_update_status_with_error(self):
        """测试更新引擎状态（包含错误）"""
        config = EngineConfig(engine_type=EngineType.CLAUDE)
        adapter = ClaudeAdapter(config)
        
        # 更新状态并记录错误
        adapter.update_status(error="API 调用失败")
        
        assert adapter.status.error_count == 1
        assert adapter.status.last_error == "API 调用失败"
        
        # 再次记录错误
        adapter.update_status(error="超时")
        
        assert adapter.status.error_count == 2
        assert adapter.status.last_error == "超时"


class TestQwenCodeAdapter:
    """测试 Qwen Code 适配器"""
    
    def test_initialization(self):
        """测试 Qwen Code 适配器初始化"""
        config = EngineConfig(engine_type=EngineType.QWEN_CODE)
        adapter = QwenCodeAdapter(config)
        
        # 初始化（占位符实现应该返回 True）
        result = adapter.initialize()
        
        assert result is True
        assert adapter.is_available() is True
    
    def test_generate_code(self):
        """测试代码生成"""
        config = EngineConfig(engine_type=EngineType.QWEN_CODE)
        adapter = QwenCodeAdapter(config)
        adapter.initialize()
        
        result = adapter.generate_code(
            prompt="实现快速排序",
            language="python"
        )
        
        assert isinstance(result, CodeResult)
        assert result.success is True
        assert result.code is not None
    
    def test_refactor_code(self):
        """测试代码重构"""
        config = EngineConfig(engine_type=EngineType.QWEN_CODE)
        adapter = QwenCodeAdapter(config)
        adapter.initialize()
        
        code = "def add(a, b): return a + b"
        result = adapter.refactor_code(
            code=code,
            requirements="添加类型注解"
        )
        
        assert isinstance(result, CodeResult)
        assert result.success is True
    
    def test_fix_errors(self):
        """测试错误修复"""
        config = EngineConfig(engine_type=EngineType.QWEN_CODE)
        adapter = QwenCodeAdapter(config)
        adapter.initialize()
        
        code = "def hello():\n    print('Hello'"
        errors = ["SyntaxError: unexpected EOF while parsing"]
        
        result = adapter.fix_errors(
            code=code,
            errors=errors,
            error_category=ErrorCategory.SYNTAX_ERROR
        )
        
        assert isinstance(result, CodeResult)
        assert result.success is True


class TestAIEngineManager:
    """测试 AI 引擎管理器"""
    
    def test_manager_creation(self):
        """测试管理器创建"""
        manager = AIEngineManager(
            primary_engine=EngineType.QWEN_CODE,
            fallback_engines=[EngineType.CLAUDE, EngineType.GPT4]
        )
        
        assert manager.primary_engine == EngineType.QWEN_CODE
        assert len(manager.fallback_engines) == 2
        assert manager.current_engine is None
    
    def test_register_engine(self):
        """测试注册引擎"""
        manager = AIEngineManager(primary_engine=EngineType.QWEN_CODE)
        
        config = EngineConfig(engine_type=EngineType.QWEN_CODE)
        manager.register_engine(EngineType.QWEN_CODE, config)
        
        assert EngineType.QWEN_CODE in manager.engines
        assert manager.current_engine is not None
        assert isinstance(manager.current_engine, QwenCodeAdapter)
    
    def test_switch_engine(self):
        """测试引擎切换"""
        manager = AIEngineManager(
            primary_engine=EngineType.QWEN_CODE,
            fallback_engines=[EngineType.CLAUDE]
        )
        
        # 注册两个引擎
        qwen_config = EngineConfig(engine_type=EngineType.QWEN_CODE)
        claude_config = EngineConfig(engine_type=EngineType.CLAUDE)
        
        manager.register_engine(EngineType.QWEN_CODE, qwen_config)
        manager.register_engine(EngineType.CLAUDE, claude_config)
        
        # 初始应该是主引擎
        assert isinstance(manager.current_engine, QwenCodeAdapter)
        
        # 切换到 Claude
        result = manager.switch_engine(EngineType.CLAUDE)
        
        assert result is True
        assert isinstance(manager.current_engine, ClaudeAdapter)
    
    def test_switch_to_unregistered_engine(self):
        """测试切换到未注册的引擎"""
        manager = AIEngineManager(primary_engine=EngineType.QWEN_CODE)
        
        config = EngineConfig(engine_type=EngineType.QWEN_CODE)
        manager.register_engine(EngineType.QWEN_CODE, config)
        
        # 尝试切换到未注册的引擎
        result = manager.switch_engine(EngineType.GPT4)
        
        assert result is False
        assert isinstance(manager.current_engine, QwenCodeAdapter)
    
    def test_get_current_engine(self):
        """测试获取当前引擎"""
        manager = AIEngineManager(primary_engine=EngineType.AIDER)
        
        # 未注册引擎时
        assert manager.get_current_engine() is None
        
        # 注册引擎后
        config = EngineConfig(engine_type=EngineType.AIDER)
        manager.register_engine(EngineType.AIDER, config)
        
        current = manager.get_current_engine()
        assert current is not None
        assert isinstance(current, AiderAdapter)
    
    def test_generate_code_with_manager(self):
        """测试通过管理器生成代码"""
        manager = AIEngineManager(primary_engine=EngineType.QWEN_CODE)
        
        config = EngineConfig(engine_type=EngineType.QWEN_CODE)
        manager.register_engine(EngineType.QWEN_CODE, config)
        
        result = manager.generate_code(
            prompt="实现二分查找",
            language="python"
        )
        
        assert isinstance(result, CodeResult)
        assert result.success is True
    
    def test_generate_code_without_engine(self):
        """测试没有引擎时生成代码"""
        manager = AIEngineManager(primary_engine=EngineType.QWEN_CODE)
        
        with pytest.raises(RuntimeError, match="没有可用的 AI 引擎"):
            manager.generate_code(prompt="测试")
    
    def test_get_all_statuses(self):
        """测试获取所有引擎状态"""
        manager = AIEngineManager(
            primary_engine=EngineType.QWEN_CODE,
            fallback_engines=[EngineType.CLAUDE]
        )
        
        # 注册两个引擎
        qwen_config = EngineConfig(engine_type=EngineType.QWEN_CODE)
        claude_config = EngineConfig(engine_type=EngineType.CLAUDE)
        
        manager.register_engine(EngineType.QWEN_CODE, qwen_config)
        manager.register_engine(EngineType.CLAUDE, claude_config)
        
        # 获取所有状态
        statuses = manager.get_all_statuses()
        
        assert len(statuses) == 2
        assert EngineType.QWEN_CODE in statuses
        assert EngineType.CLAUDE in statuses
        assert isinstance(statuses[EngineType.QWEN_CODE], EngineStatus)
        assert isinstance(statuses[EngineType.CLAUDE], EngineStatus)


class TestEngineFallback:
    """测试引擎故障转移"""
    
    def test_try_fallback_success(self):
        """测试成功切换到备用引擎"""
        manager = AIEngineManager(
            primary_engine=EngineType.QWEN_CODE,
            fallback_engines=[EngineType.CLAUDE, EngineType.GPT4]
        )
        
        # 只注册备用引擎
        claude_config = EngineConfig(engine_type=EngineType.CLAUDE)
        manager.register_engine(EngineType.CLAUDE, claude_config)
        
        # 尝试故障转移
        result = manager.try_fallback()
        
        assert result is True
        assert isinstance(manager.current_engine, ClaudeAdapter)
    
    def test_try_fallback_no_available_engines(self):
        """测试没有可用备用引擎"""
        manager = AIEngineManager(
            primary_engine=EngineType.QWEN_CODE,
            fallback_engines=[EngineType.CLAUDE, EngineType.GPT4]
        )
        
        # 不注册任何备用引擎
        result = manager.try_fallback()
        
        assert result is False
        assert manager.current_engine is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
