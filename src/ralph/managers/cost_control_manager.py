"""
成本控制管理器

管理 LLM 调用成本、预算控制和资源熔断机制。
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional

from ..models.enums import EngineType


class BudgetStatus(Enum):
    """预算状态"""
    NORMAL = "normal"  # 正常状态
    WARNING = "warning"  # 警告状态（90%）
    EXCEEDED = "exceeded"  # 超出预算（100%）


@dataclass
class LLMPricing:
    """LLM 定价信息"""
    model_name: str
    input_price_per_1k: Decimal  # 输入 token 价格（每 1000 tokens）
    output_price_per_1k: Decimal  # 输出 token 价格（每 1000 tokens）


@dataclass
class CostRecord:
    """成本记录"""
    timestamp: datetime
    engine_type: EngineType
    model_name: str
    input_tokens: int
    output_tokens: int
    cost: Decimal
    task_id: Optional[str] = None
    operation: Optional[str] = None


@dataclass
class BudgetConfig:
    """预算配置"""
    max_budget: Decimal  # 最大预算（美元）
    warning_threshold: float = 0.9  # 警告阈值（90%）
    currency: str = "USD"


class CostControlManager:
    """
    成本控制管理器
    
    功能：
    1. 实时估算 LLM 调用成本
    2. 累计总消耗
    3. 预算阈值检查
    4. 预算警告和熔断
    """
    
    # LLM 定价表（示例价格，实际使用时应从配置文件读取）
    PRICING_TABLE: Dict[str, LLMPricing] = {
        # OpenAI GPT-4
        "gpt-4": LLMPricing(
            model_name="gpt-4",
            input_price_per_1k=Decimal("0.03"),
            output_price_per_1k=Decimal("0.06")
        ),
        "gpt-4-turbo": LLMPricing(
            model_name="gpt-4-turbo",
            input_price_per_1k=Decimal("0.01"),
            output_price_per_1k=Decimal("0.03")
        ),
        # OpenAI GPT-3.5
        "gpt-3.5-turbo": LLMPricing(
            model_name="gpt-3.5-turbo",
            input_price_per_1k=Decimal("0.0015"),
            output_price_per_1k=Decimal("0.002")
        ),
        # Claude
        "claude-3-opus": LLMPricing(
            model_name="claude-3-opus",
            input_price_per_1k=Decimal("0.015"),
            output_price_per_1k=Decimal("0.075")
        ),
        "claude-3-sonnet": LLMPricing(
            model_name="claude-3-sonnet",
            input_price_per_1k=Decimal("0.003"),
            output_price_per_1k=Decimal("0.015")
        ),
        # Qwen Code
        "qwen-coder-plus": LLMPricing(
            model_name="qwen-coder-plus",
            input_price_per_1k=Decimal("0.002"),
            output_price_per_1k=Decimal("0.006")
        ),
        "qwen-coder-turbo": LLMPricing(
            model_name="qwen-coder-turbo",
            input_price_per_1k=Decimal("0.0002"),
            output_price_per_1k=Decimal("0.0006")
        ),
    }
    
    def __init__(self, budget_config: Optional[BudgetConfig] = None):
        """
        初始化成本控制管理器
        
        Args:
            budget_config: 预算配置，如果为 None 则不启用预算控制
        """
        self.budget_config = budget_config
        self.cost_records: List[CostRecord] = []
        self.total_cost = Decimal("0")
        self._budget_status = BudgetStatus.NORMAL
    
    def estimate_cost(
        self,
        model_name: str,
        input_tokens: int,
        output_tokens: int
    ) -> Decimal:
        """
        估算 LLM 调用成本
        
        Args:
            model_name: 模型名称
            input_tokens: 输入 token 数量
            output_tokens: 输出 token 数量
        
        Returns:
            估算的成本（美元）
        
        Raises:
            ValueError: 如果模型名称不在定价表中
        """
        if model_name not in self.PRICING_TABLE:
            raise ValueError(f"未知的模型名称: {model_name}")
        
        pricing = self.PRICING_TABLE[model_name]
        
        # 计算输入和输出成本
        input_cost = (Decimal(input_tokens) / Decimal("1000")) * pricing.input_price_per_1k
        output_cost = (Decimal(output_tokens) / Decimal("1000")) * pricing.output_price_per_1k
        
        total_cost = input_cost + output_cost
        return total_cost.quantize(Decimal("0.0001"))  # 保留 4 位小数
    
    def record_cost(
        self,
        engine_type: EngineType,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        task_id: Optional[str] = None,
        operation: Optional[str] = None
    ) -> CostRecord:
        """
        记录 LLM 调用成本
        
        Args:
            engine_type: AI 引擎类型
            model_name: 模型名称
            input_tokens: 输入 token 数量
            output_tokens: 输出 token 数量
            task_id: 任务 ID
            operation: 操作描述
        
        Returns:
            成本记录
        """
        cost = self.estimate_cost(model_name, input_tokens, output_tokens)
        
        record = CostRecord(
            timestamp=datetime.now(),
            engine_type=engine_type,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            task_id=task_id,
            operation=operation
        )
        
        self.cost_records.append(record)
        self.total_cost += cost
        
        # 检查预算状态
        if self.budget_config:
            self._update_budget_status()
        
        return record
    
    def _update_budget_status(self) -> None:
        """更新预算状态"""
        if not self.budget_config:
            return
        
        usage_ratio = float(self.total_cost / self.budget_config.max_budget)
        
        if usage_ratio >= 1.0:
            self._budget_status = BudgetStatus.EXCEEDED
        elif usage_ratio >= self.budget_config.warning_threshold:
            self._budget_status = BudgetStatus.WARNING
        else:
            self._budget_status = BudgetStatus.NORMAL
    
    def check_budget(self) -> BudgetStatus:
        """
        检查预算状态
        
        Returns:
            当前预算状态
        """
        if not self.budget_config:
            return BudgetStatus.NORMAL
        
        return self._budget_status
    
    def get_budget_usage(self) -> Dict[str, any]:
        """
        获取预算使用情况
        
        Returns:
            预算使用信息字典
        """
        if not self.budget_config:
            return {
                "enabled": False,
                "total_cost": float(self.total_cost),
                "currency": "USD"
            }
        
        usage_ratio = float(self.total_cost / self.budget_config.max_budget)
        remaining = self.budget_config.max_budget - self.total_cost
        
        return {
            "enabled": True,
            "max_budget": float(self.budget_config.max_budget),
            "total_cost": float(self.total_cost),
            "remaining": float(remaining),
            "usage_ratio": usage_ratio,
            "usage_percentage": usage_ratio * 100,
            "status": self._budget_status.value,
            "currency": self.budget_config.currency
        }
    
    def get_cost_breakdown(self) -> Dict[str, any]:
        """
        获取成本分解信息
        
        Returns:
            成本分解字典
        """
        breakdown = {
            "total_cost": float(self.total_cost),
            "total_calls": len(self.cost_records),
            "by_model": {},
            "by_task": {},
            "by_engine": {}
        }
        
        # 按模型统计
        for record in self.cost_records:
            model = record.model_name
            if model not in breakdown["by_model"]:
                breakdown["by_model"][model] = {
                    "cost": 0.0,
                    "calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0
                }
            
            breakdown["by_model"][model]["cost"] += float(record.cost)
            breakdown["by_model"][model]["calls"] += 1
            breakdown["by_model"][model]["input_tokens"] += record.input_tokens
            breakdown["by_model"][model]["output_tokens"] += record.output_tokens
        
        # 按任务统计
        for record in self.cost_records:
            if record.task_id:
                task_id = record.task_id
                if task_id not in breakdown["by_task"]:
                    breakdown["by_task"][task_id] = {
                        "cost": 0.0,
                        "calls": 0
                    }
                
                breakdown["by_task"][task_id]["cost"] += float(record.cost)
                breakdown["by_task"][task_id]["calls"] += 1
        
        # 按引擎统计
        for record in self.cost_records:
            engine = record.engine_type.value
            if engine not in breakdown["by_engine"]:
                breakdown["by_engine"][engine] = {
                    "cost": 0.0,
                    "calls": 0
                }
            
            breakdown["by_engine"][engine]["cost"] += float(record.cost)
            breakdown["by_engine"][engine]["calls"] += 1
        
        return breakdown
    
    def should_continue(self) -> bool:
        """
        判断是否应该继续执行（未超出预算）
        
        Returns:
            True 如果可以继续，False 如果应该停止
        """
        return self.check_budget() != BudgetStatus.EXCEEDED
    
    def reset(self) -> None:
        """重置成本记录"""
        self.cost_records.clear()
        self.total_cost = Decimal("0")
        self._budget_status = BudgetStatus.NORMAL
    
    def add_custom_pricing(self, model_name: str, pricing: LLMPricing) -> None:
        """
        添加自定义模型定价
        
        Args:
            model_name: 模型名称
            pricing: 定价信息
        """
        self.PRICING_TABLE[model_name] = pricing
