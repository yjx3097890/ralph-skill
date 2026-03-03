"""
动态策略管理器

管理失败模式识别和策略切换。
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class StrategyType(Enum):
    """策略类型"""
    DIRECT_CODING = "direct_coding"  # 直接编码
    DIAGNOSTIC_MODE = "diagnostic_mode"  # 诊断模式
    WEB_SEARCH_MODE = "web_search_mode"  # Web 搜索模式
    INCREMENTAL_FIX = "incremental_fix"  # 增量修复


@dataclass
class FailurePattern:
    """失败模式"""
    pattern_type: str
    occurrences: int
    first_seen: datetime
    last_seen: datetime
    error_messages: List[str] = field(default_factory=list)
    suggested_strategy: Optional[StrategyType] = None


@dataclass
class StrategyExecution:
    """策略执行记录"""
    strategy: StrategyType
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None
    execution_time: float = 0.0


class StrategyManager:
    """
    动态策略管理器
    
    功能:
    1. 记录失败模式
    2. 自动切换策略
    3. 策略学习和推荐
    4. 人工介入请求
    """
    
    def __init__(self, max_retries_per_strategy: int = 3):
        """
        初始化策略管理器
        
        Args:
            max_retries_per_strategy: 每个策略的最大重试次数
        """
        self.max_retries_per_strategy = max_retries_per_strategy
        self.current_strategy = StrategyType.DIRECT_CODING
        self.failure_patterns: List[FailurePattern] = []
        self.execution_history: List[StrategyExecution] = []
        self.strategy_success_rate: Dict[StrategyType, float] = {}
    
    def record_failure(
        self,
        error_message: str,
        error_type: str = "unknown"
    ) -> None:
        """
        记录失败
        
        Args:
            error_message: 错误信息
            error_type: 错误类型
        """
        # 查找现有模式
        pattern = self._find_or_create_pattern(error_type)
        pattern.occurrences += 1
        pattern.last_seen = datetime.now()
        pattern.error_messages.append(error_message)
        
        logger.warning(f"记录失败: {error_type}, 累计 {pattern.occurrences} 次")
    
    def should_switch_strategy(self) -> bool:
        """
        判断是否应该切换策略
        
        Returns:
            True 如果应该切换
        """
        # 检查当前策略的连续失败次数
        recent_executions = self._get_recent_executions(self.current_strategy)
        consecutive_failures = sum(1 for e in recent_executions if not e.success)
        
        return consecutive_failures >= self.max_retries_per_strategy
    
    def get_next_strategy(self) -> StrategyType:
        """
        获取下一个策略
        
        Returns:
            推荐的策略类型
        """
        # 策略切换顺序
        strategy_order = [
            StrategyType.DIRECT_CODING,
            StrategyType.DIAGNOSTIC_MODE,
            StrategyType.WEB_SEARCH_MODE,
            StrategyType.INCREMENTAL_FIX
        ]
        
        current_index = strategy_order.index(self.current_strategy)
        next_index = (current_index + 1) % len(strategy_order)
        
        return strategy_order[next_index]
    
    def switch_strategy(self) -> StrategyType:
        """
        切换到下一个策略
        
        Returns:
            新的策略类型
        """
        old_strategy = self.current_strategy
        self.current_strategy = self.get_next_strategy()
        
        logger.info(f"策略切换: {old_strategy.value} -> {self.current_strategy.value}")
        
        return self.current_strategy
    
    def record_execution(
        self,
        strategy: StrategyType,
        success: bool,
        error_message: Optional[str] = None,
        execution_time: float = 0.0
    ) -> None:
        """
        记录策略执行
        
        Args:
            strategy: 策略类型
            success: 是否成功
            error_message: 错误信息
            execution_time: 执行时间
        """
        execution = StrategyExecution(
            strategy=strategy,
            timestamp=datetime.now(),
            success=success,
            error_message=error_message,
            execution_time=execution_time
        )
        
        self.execution_history.append(execution)
        self._update_success_rate(strategy)
    
    def _find_or_create_pattern(self, pattern_type: str) -> FailurePattern:
        """查找或创建失败模式"""
        for pattern in self.failure_patterns:
            if pattern.pattern_type == pattern_type:
                return pattern
        
        pattern = FailurePattern(
            pattern_type=pattern_type,
            occurrences=0,
            first_seen=datetime.now(),
            last_seen=datetime.now()
        )
        self.failure_patterns.append(pattern)
        return pattern
    
    def _get_recent_executions(
        self,
        strategy: StrategyType,
        limit: int = 5
    ) -> List[StrategyExecution]:
        """获取最近的策略执行记录"""
        executions = [e for e in self.execution_history if e.strategy == strategy]
        return executions[-limit:]
    
    def _update_success_rate(self, strategy: StrategyType) -> None:
        """更新策略成功率"""
        executions = [e for e in self.execution_history if e.strategy == strategy]
        if executions:
            success_count = sum(1 for e in executions if e.success)
            self.strategy_success_rate[strategy] = success_count / len(executions)
    
    def get_statistics(self) -> Dict[str, any]:
        """获取统计信息"""
        return {
            "current_strategy": self.current_strategy.value,
            "total_executions": len(self.execution_history),
            "failure_patterns": len(self.failure_patterns),
            "success_rates": {
                k.value: v for k, v in self.strategy_success_rate.items()
            }
        }
