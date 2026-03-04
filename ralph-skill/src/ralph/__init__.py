"""
Ralph Skill 企业级自治编程引擎

这是一个企业级的自治编程引擎，提供 Git 级别的安全回滚、
上下文防爆机制、多 AI 引擎兼容等核心功能。
"""

__version__ = "1.0.0"
__author__ = "Ralph Team"

# 导出主要函数供外部调用
from ralph.__main__ import autonomous_develop

__all__ = ["autonomous_develop"]
