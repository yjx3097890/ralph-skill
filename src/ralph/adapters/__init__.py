"""
AI 引擎适配器模块

提供统一的 AI 引擎接口和多种引擎实现。

## 可用的适配器
- AIEngineAdapter: 抽象基类
- QwenCodeAdapter: Qwen Code 引擎实现
- AiderAdapter: Aider 引擎实现
- ClaudeAdapter: Claude 引擎实现
- GPT4Adapter: GPT-4 引擎实现

## 管理器
- AIEngineManager: 引擎管理器，支持引擎切换和故障转移

## 使用示例
```python
from ralph.adapters import AIEngineManager, EngineConfig
from ralph.models.enums import EngineType

# 创建引擎管理器
manager = AIEngineManager(
    primary_engine=EngineType.QWEN_CODE,
    fallback_engines=[EngineType.CLAUDE, EngineType.GPT4]
)

# 注册引擎
config = EngineConfig(
    engine_type=EngineType.QWEN_CODE,
    api_key="your-api-key"
)
manager.register_engine(EngineType.QWEN_CODE, config)

# 使用引擎
result = manager.generate_code(
    prompt="实现用户认证功能",
    context="使用 JWT 和 bcrypt"
)
```
"""

from ralph.adapters.ai_engine import (
    AIEngineAdapter,
    AIEngineManager,
    CodeResult,
    EngineConfig,
    EngineStatus,
)
from ralph.adapters.aider_adapter import AiderAdapter
from ralph.adapters.claude_adapter import ClaudeAdapter
from ralph.adapters.gpt4_adapter import GPT4Adapter
from ralph.adapters.qwen_code_adapter import QwenCodeAdapter

__all__ = [
    # 抽象基类和数据模型
    "AIEngineAdapter",
    "CodeResult",
    "EngineConfig",
    "EngineStatus",
    # 管理器
    "AIEngineManager",
    # 具体实现
    "QwenCodeAdapter",
    "AiderAdapter",
    "ClaudeAdapter",
    "GPT4Adapter",
]
