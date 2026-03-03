"""
预算熔断器

实现预算警告、强制中止和进度保存功能。
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, List, Optional

from .cost_control_manager import BudgetStatus, CostControlManager

logger = logging.getLogger(__name__)


@dataclass
class BudgetEvent:
    """预算事件"""
    timestamp: datetime
    event_type: str  # warning, exceeded, report
    status: BudgetStatus
    total_cost: float
    budget_usage: float
    message: str


@dataclass
class CostReport:
    """成本报告"""
    generated_at: datetime
    reason: str  # budget_exceeded, timeout, manual
    total_cost: float
    total_calls: int
    budget_usage: Optional[float] = None
    cost_breakdown: Dict[str, any] = field(default_factory=dict)
    events: List[BudgetEvent] = field(default_factory=list)
    wip_branch_saved: bool = False
    wip_branch_name: Optional[str] = None


class BudgetEnforcer:
    """
    预算熔断器
    
    功能：
    1. 监控预算使用情况
    2. 发出预算警告（90% 阈值）
    3. 强制中止任务（100% 阈值）
    4. 保存进度和 WIP 分支
    5. 生成成本报告
    """
    
    def __init__(
        self,
        cost_manager: CostControlManager,
        on_warning: Optional[Callable[[BudgetEvent], None]] = None,
        on_exceeded: Optional[Callable[[BudgetEvent], None]] = None
    ):
        """
        初始化预算熔断器
        
        Args:
            cost_manager: 成本控制管理器
            on_warning: 警告回调函数
            on_exceeded: 超出预算回调函数
        """
        self.cost_manager = cost_manager
        self.on_warning = on_warning
        self.on_exceeded = on_exceeded
        self.events: List[BudgetEvent] = []
        self._last_status = BudgetStatus.NORMAL
        self._warning_triggered = False
        self._exceeded_triggered = False
    
    def check_and_enforce(self) -> bool:
        """
        检查并执行预算控制
        
        Returns:
            True 如果可以继续，False 如果应该停止
        """
        current_status = self.cost_manager.check_budget()
        
        # 状态变化时触发事件
        if current_status != self._last_status:
            self._handle_status_change(current_status)
            self._last_status = current_status
        
        # 返回是否可以继续
        return current_status != BudgetStatus.EXCEEDED
    
    def _handle_status_change(self, new_status: BudgetStatus) -> None:
        """
        处理预算状态变化
        
        Args:
            new_status: 新的预算状态
        """
        budget_usage = self.cost_manager.get_budget_usage()
        
        if new_status == BudgetStatus.WARNING and not self._warning_triggered:
            self._trigger_warning(budget_usage)
            self._warning_triggered = True
        
        elif new_status == BudgetStatus.EXCEEDED and not self._exceeded_triggered:
            self._trigger_exceeded(budget_usage)
            self._exceeded_triggered = True
    
    def _trigger_warning(self, budget_usage: Dict[str, any]) -> None:
        """
        触发预算警告
        
        Args:
            budget_usage: 预算使用情况
        """
        event = BudgetEvent(
            timestamp=datetime.now(),
            event_type="warning",
            status=BudgetStatus.WARNING,
            total_cost=budget_usage["total_cost"],
            budget_usage=budget_usage["usage_percentage"],
            message=f"预算警告: 已使用 {budget_usage['usage_percentage']:.1f}% 的预算"
        )
        
        self.events.append(event)
        logger.warning(event.message)
        
        # 调用警告回调
        if self.on_warning:
            try:
                self.on_warning(event)
            except Exception as e:
                logger.error(f"警告回调执行失败: {e}")
    
    def _trigger_exceeded(self, budget_usage: Dict[str, any]) -> None:
        """
        触发预算超出
        
        Args:
            budget_usage: 预算使用情况
        """
        event = BudgetEvent(
            timestamp=datetime.now(),
            event_type="exceeded",
            status=BudgetStatus.EXCEEDED,
            total_cost=budget_usage["total_cost"],
            budget_usage=budget_usage["usage_percentage"],
            message=f"预算超出: 已使用 {budget_usage['usage_percentage']:.1f}% 的预算，强制中止任务"
        )
        
        self.events.append(event)
        logger.error(event.message)
        
        # 调用超出回调
        if self.on_exceeded:
            try:
                self.on_exceeded(event)
            except Exception as e:
                logger.error(f"超出回调执行失败: {e}")
    
    def generate_report(
        self,
        reason: str = "manual",
        wip_branch_saved: bool = False,
        wip_branch_name: Optional[str] = None
    ) -> CostReport:
        """
        生成成本报告
        
        Args:
            reason: 报告原因（budget_exceeded, timeout, manual）
            wip_branch_saved: 是否保存了 WIP 分支
            wip_branch_name: WIP 分支名称
        
        Returns:
            成本报告
        """
        budget_usage = self.cost_manager.get_budget_usage()
        cost_breakdown = self.cost_manager.get_cost_breakdown()
        
        report = CostReport(
            generated_at=datetime.now(),
            reason=reason,
            total_cost=budget_usage["total_cost"],
            total_calls=cost_breakdown["total_calls"],
            budget_usage=budget_usage.get("usage_percentage"),
            cost_breakdown=cost_breakdown,
            events=self.events.copy(),
            wip_branch_saved=wip_branch_saved,
            wip_branch_name=wip_branch_name
        )
        
        logger.info(f"成本报告已生成: 原因={reason}, 总成本=${report.total_cost:.4f}")
        
        return report
    
    def format_report(self, report: CostReport) -> str:
        """
        格式化成本报告为可读文本
        
        Args:
            report: 成本报告
        
        Returns:
            格式化的报告文本
        """
        lines = [
            "=" * 60,
            "成本报告",
            "=" * 60,
            f"生成时间: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"报告原因: {report.reason}",
            "",
            "总体统计:",
            f"  总成本: ${report.total_cost:.4f}",
            f"  总调用次数: {report.total_calls}",
        ]
        
        if report.budget_usage is not None:
            lines.append(f"  预算使用率: {report.budget_usage:.1f}%")
        
        if report.wip_branch_saved:
            lines.extend([
                "",
                "进度保存:",
                f"  WIP 分支已保存: {report.wip_branch_name}"
            ])
        
        # 按模型分解
        if report.cost_breakdown.get("by_model"):
            lines.extend([
                "",
                "按模型分解:"
            ])
            for model, stats in report.cost_breakdown["by_model"].items():
                lines.append(
                    f"  {model}: ${stats['cost']:.4f} "
                    f"({stats['calls']} 次调用, "
                    f"{stats['input_tokens']} 输入 tokens, "
                    f"{stats['output_tokens']} 输出 tokens)"
                )
        
        # 按任务分解
        if report.cost_breakdown.get("by_task"):
            lines.extend([
                "",
                "按任务分解:"
            ])
            for task_id, stats in report.cost_breakdown["by_task"].items():
                lines.append(
                    f"  {task_id}: ${stats['cost']:.4f} ({stats['calls']} 次调用)"
                )
        
        # 事件历史
        if report.events:
            lines.extend([
                "",
                "事件历史:"
            ])
            for event in report.events:
                lines.append(
                    f"  [{event.timestamp.strftime('%H:%M:%S')}] "
                    f"{event.event_type}: {event.message}"
                )
        
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def reset(self) -> None:
        """重置熔断器状态"""
        self.events.clear()
        self._last_status = BudgetStatus.NORMAL
        self._warning_triggered = False
        self._exceeded_triggered = False
