"""
AI 引擎适配器抽象基类

提供统一的 AI 引擎接口，支持多种 AI 引擎（Qwen Code、Aider、Claude、GPT-4）。
使用适配器模式封装不同的 AI 引擎实现，提供一致的代码生成、重构和错误修复接口。

## 核心功能
- 代码生成：根据提示和上下文生成代码
- 代码重构：优化和重构现有代码
- 错误修复：根据错误信息修复代码
- 引擎切换：动态切换不同的 AI 引擎
- 状态管理：跟踪引擎状态和使用情况

## 支持的引擎
- Qwen Code: 代码生成和修改
- Aider: 代码重构和优化
- Claude: 通用代码任务
- GPT-4: 复杂逻辑实现

## 使用示例
```python
# 创建引擎适配器
adapter = AIEngineAdapter.create(EngineType.QWEN_CODE, config)

# 生成代码
result = adapter.generate_code(
    prompt="实现用户认证功能",
    context="现有的用户模型和数据库配置"
)

# 修复错误
result = adapter.fix_errors(
    code="def hello():\n    print('Hello'",
    errors=["SyntaxError: unexpected EOF while parsing"]
)

# 切换引擎
adapter.switch_engine(EngineType.AIDER)
```
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any

from ralph.models.enums import EngineType, ErrorCategory


@dataclass
class CodeResult:
    """代码生成/修改结果"""
    success: bool
    code: str
    explanation: str
    changes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    tokens_used: int = 0
    cost: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EngineConfig:
    """AI 引擎配置"""
    engine_type: EngineType
    model_name: Optional[str] = None
    timeout: int = 60
    api_key: Optional[str] = None  # 保留用于向后兼容，但不在配置文件中使用
    api_endpoint: Optional[str] = None  # 保留用于向后兼容，但不在配置文件中使用
    temperature: float = 0.7  # 保留用于向后兼容，但不在配置文件中使用
    max_tokens: int = 4096  # 保留用于向后兼容，但不在配置文件中使用
    retry_count: int = 3
    extra_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EngineStatus:
    """引擎状态信息"""
    engine_type: EngineType
    is_available: bool
    last_used: Optional[datetime] = None
    total_calls: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    error_count: int = 0
    last_error: Optional[str] = None


class AIEngineAdapter(ABC):
    """
    AI 引擎适配器抽象基类
    
    定义统一的 AI 引擎接口，所有具体的引擎实现都必须继承此类。
    """
    
    def __init__(self, config: EngineConfig):
        """
        初始化 AI 引擎适配器
        
        Args:
            config: 引擎配置
        """
        self.config = config
        self.status = EngineStatus(
            engine_type=config.engine_type,
            is_available=False
        )
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        初始化引擎
        
        Returns:
            bool: 初始化是否成功
        """
        pass
    
    @abstractmethod
    def generate_code(
        self,
        prompt: str,
        context: str = "",
        language: Optional[str] = None,
        **kwargs
    ) -> CodeResult:
        """
        生成代码
        
        Args:
            prompt: 代码生成提示
            context: 上下文信息（现有代码、项目结构等）
            language: 目标编程语言
            **kwargs: 其他参数
            
        Returns:
            CodeResult: 代码生成结果
        """
        pass
    
    @abstractmethod
    def refactor_code(
        self,
        code: str,
        requirements: str,
        **kwargs
    ) -> CodeResult:
        """
        重构代码
        
        Args:
            code: 待重构的代码
            requirements: 重构需求描述
            **kwargs: 其他参数
            
        Returns:
            CodeResult: 重构结果
        """
        pass
    
    @abstractmethod
    def fix_errors(
        self,
        code: str,
        errors: List[str],
        error_category: Optional[ErrorCategory] = None,
        **kwargs
    ) -> CodeResult:
        """
        修复代码错误
        
        Args:
            code: 包含错误的代码
            errors: 错误信息列表
            error_category: 错误类别
            **kwargs: 其他参数
            
        Returns:
            CodeResult: 修复结果
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        检查引擎是否可用
        
        Returns:
            bool: 引擎是否可用
        """
        pass
    
    def get_status(self) -> EngineStatus:
        """
        获取引擎状态
        
        Returns:
            EngineStatus: 引擎状态信息
        """
        return self.status
    
    def update_status(
        self,
        tokens_used: int = 0,
        cost: float = 0.0,
        error: Optional[str] = None
    ) -> None:
        """
        更新引擎状态
        
        Args:
            tokens_used: 使用的 token 数量
            cost: 本次调用成本
            error: 错误信息（如果有）
        """
        self.status.last_used = datetime.now()
        self.status.total_calls += 1
        self.status.total_tokens += tokens_used
        self.status.total_cost += cost
        
        if error:
            self.status.error_count += 1
            self.status.last_error = error
    
    @staticmethod
    def create(engine_type: EngineType, config: EngineConfig) -> 'AIEngineAdapter':
        """
        工厂方法：创建具体的引擎适配器实例
        
        Args:
            engine_type: 引擎类型
            config: 引擎配置
            
        Returns:
            AIEngineAdapter: 具体的引擎适配器实例
            
        Raises:
            ValueError: 不支持的引擎类型
        """
        # 导入具体的引擎实现（延迟导入避免循环依赖）
        if engine_type == EngineType.QWEN_CODE:
            from ralph.adapters.qwen_code_adapter import QwenCodeAdapter
            return QwenCodeAdapter(config)
        elif engine_type == EngineType.AIDER:
            from ralph.adapters.aider_adapter import AiderAdapter
            return AiderAdapter(config)
        elif engine_type == EngineType.CLAUDE:
            from ralph.adapters.claude_adapter import ClaudeAdapter
            return ClaudeAdapter(config)
        elif engine_type == EngineType.GPT4:
            from ralph.adapters.gpt4_adapter import GPT4Adapter
            return GPT4Adapter(config)
        else:
            raise ValueError(f"不支持的引擎类型: {engine_type}")


class AIEngineManager:
    """
    AI 引擎管理器
    
    管理多个 AI 引擎实例，支持引擎切换和故障转移。
    """
    
    def __init__(self, primary_engine: EngineType, fallback_engines: Optional[List[EngineType]] = None):
        """
        初始化引擎管理器
        
        Args:
            primary_engine: 主引擎类型
            fallback_engines: 备用引擎列表
        """
        self.primary_engine = primary_engine
        self.fallback_engines = fallback_engines or []
        self.engines: Dict[EngineType, AIEngineAdapter] = {}
        self.current_engine: Optional[AIEngineAdapter] = None
    
    def register_engine(self, engine_type: EngineType, config: EngineConfig) -> None:
        """
        注册引擎
        
        Args:
            engine_type: 引擎类型
            config: 引擎配置
        """
        adapter = AIEngineAdapter.create(engine_type, config)
        if adapter.initialize():
            self.engines[engine_type] = adapter
            adapter.status.is_available = True
            
            # 如果是主引擎，设置为当前引擎
            if engine_type == self.primary_engine:
                self.current_engine = adapter
    
    def switch_engine(self, engine_type: EngineType) -> bool:
        """
        切换引擎
        
        Args:
            engine_type: 目标引擎类型
            
        Returns:
            bool: 切换是否成功
        """
        if engine_type not in self.engines:
            return False
        
        adapter = self.engines[engine_type]
        if not adapter.is_available():
            return False
        
        self.current_engine = adapter
        return True
    
    def get_current_engine(self) -> Optional[AIEngineAdapter]:
        """
        获取当前引擎
        
        Returns:
            Optional[AIEngineAdapter]: 当前引擎适配器
        """
        return self.current_engine
    
    def try_fallback(self) -> bool:
        """
        尝试切换到备用引擎
        
        Returns:
            bool: 是否成功切换到可用的备用引擎
        """
        for engine_type in self.fallback_engines:
            if self.switch_engine(engine_type):
                return True
        return False
    
    def generate_code(
        self,
        prompt: str,
        context: str = "",
        language: Optional[str] = None,
        **kwargs
    ) -> CodeResult:
        """
        使用当前引擎生成代码，失败时自动尝试备用引擎
        
        Args:
            prompt: 代码生成提示
            context: 上下文信息
            language: 目标编程语言
            **kwargs: 其他参数
            
        Returns:
            CodeResult: 代码生成结果
            
        Raises:
            RuntimeError: 所有引擎都不可用
        """
        if not self.current_engine:
            raise RuntimeError("没有可用的 AI 引擎")
        
        try:
            return self.current_engine.generate_code(prompt, context, language, **kwargs)
        except Exception as e:
            # 尝试备用引擎
            if self.try_fallback():
                return self.current_engine.generate_code(prompt, context, language, **kwargs)
            raise RuntimeError(f"所有 AI 引擎都不可用: {e}")
    
    def refactor_code(
        self,
        code: str,
        requirements: str,
        **kwargs
    ) -> CodeResult:
        """
        使用当前引擎重构代码，失败时自动尝试备用引擎
        
        Args:
            code: 待重构的代码
            requirements: 重构需求描述
            **kwargs: 其他参数
            
        Returns:
            CodeResult: 重构结果
            
        Raises:
            RuntimeError: 所有引擎都不可用
        """
        if not self.current_engine:
            raise RuntimeError("没有可用的 AI 引擎")
        
        try:
            return self.current_engine.refactor_code(code, requirements, **kwargs)
        except Exception as e:
            # 尝试备用引擎
            if self.try_fallback():
                return self.current_engine.refactor_code(code, requirements, **kwargs)
            raise RuntimeError(f"所有 AI 引擎都不可用: {e}")
    
    def fix_errors(
        self,
        code: str,
        errors: List[str],
        error_category: Optional[ErrorCategory] = None,
        **kwargs
    ) -> CodeResult:
        """
        使用当前引擎修复错误，失败时自动尝试备用引擎
        
        Args:
            code: 包含错误的代码
            errors: 错误信息列表
            error_category: 错误类别
            **kwargs: 其他参数
            
        Returns:
            CodeResult: 修复结果
            
        Raises:
            RuntimeError: 所有引擎都不可用
        """
        if not self.current_engine:
            raise RuntimeError("没有可用的 AI 引擎")
        
        try:
            return self.current_engine.fix_errors(code, errors, error_category, **kwargs)
        except Exception as e:
            # 尝试备用引擎
            if self.try_fallback():
                return self.current_engine.fix_errors(code, errors, error_category, **kwargs)
            raise RuntimeError(f"所有 AI 引擎都不可用: {e}")
    
    def get_all_statuses(self) -> Dict[EngineType, EngineStatus]:
        """
        获取所有引擎的状态
        
        Returns:
            Dict[EngineType, EngineStatus]: 引擎类型到状态的映射
        """
        return {
            engine_type: adapter.get_status()
            for engine_type, adapter in self.engines.items()
        }
