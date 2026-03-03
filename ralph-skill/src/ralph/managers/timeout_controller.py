"""
全局超时控制器

实现任务执行时间监控和超时优雅退出机制。
"""

import logging
import signal
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class TimeoutConfig:
    """超时配置"""
    global_timeout: int  # 全局超时时间（秒）
    warning_threshold: float = 0.9  # 警告阈值（90%）
    check_interval: int = 10  # 检查间隔（秒）


@dataclass
class TimeoutEvent:
    """超时事件"""
    timestamp: datetime
    event_type: str  # started, warning, exceeded
    elapsed_time: float  # 已用时间（秒）
    remaining_time: float  # 剩余时间（秒）
    message: str


class TimeoutController:
    """
    全局超时控制器
    
    功能：
    1. 监控任务执行时间
    2. 发出超时警告
    3. 执行超时优雅退出
    4. 触发 Cleanup Hook
    5. 收集超时诊断信息
    """
    
    def __init__(
        self,
        timeout_config: TimeoutConfig,
        on_warning: Optional[Callable[[TimeoutEvent], None]] = None,
        on_timeout: Optional[Callable[[TimeoutEvent], None]] = None,
        cleanup_hook: Optional[Callable[[], None]] = None
    ):
        """
        初始化超时控制器
        
        Args:
            timeout_config: 超时配置
            on_warning: 警告回调函数
            on_timeout: 超时回调函数
            cleanup_hook: 清理钩子函数
        """
        self.config = timeout_config
        self.on_warning = on_warning
        self.on_timeout = on_timeout
        self.cleanup_hook = cleanup_hook
        
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.events: list[TimeoutEvent] = []
        self._warning_triggered = False
        self._timeout_triggered = False
        self._is_running = False
    
    def start(self) -> None:
        """开始计时"""
        self.start_time = datetime.now()
        self._is_running = True
        self._warning_triggered = False
        self._timeout_triggered = False
        
        event = TimeoutEvent(
            timestamp=self.start_time,
            event_type="started",
            elapsed_time=0.0,
            remaining_time=float(self.config.global_timeout),
            message=f"任务开始，全局超时时间: {self.config.global_timeout} 秒"
        )
        self.events.append(event)
        logger.info(event.message)
    
    def stop(self) -> None:
        """停止计时"""
        if self._is_running:
            self.end_time = datetime.now()
            self._is_running = False
            
            elapsed = self.get_elapsed_time()
            logger.info(f"任务结束，总用时: {elapsed:.2f} 秒")
    
    def check(self) -> bool:
        """
        检查是否超时
        
        Returns:
            True 如果可以继续，False 如果已超时
        """
        if not self._is_running or not self.start_time:
            return True
        
        elapsed = self.get_elapsed_time()
        remaining = self.config.global_timeout - elapsed
        
        # 检查是否超时
        if elapsed >= self.config.global_timeout:
            if not self._timeout_triggered:
                self._trigger_timeout(elapsed, remaining)
                self._timeout_triggered = True
            return False
        
        # 检查是否需要警告
        warning_time = self.config.global_timeout * self.config.warning_threshold
        if elapsed >= warning_time and not self._warning_triggered:
            self._trigger_warning(elapsed, remaining)
            self._warning_triggered = True
        
        return True
    
    def get_elapsed_time(self) -> float:
        """
        获取已用时间
        
        Returns:
            已用时间（秒）
        """
        if not self.start_time:
            return 0.0
        
        end = self.end_time if self.end_time else datetime.now()
        delta = end - self.start_time
        return delta.total_seconds()
    
    def get_remaining_time(self) -> float:
        """
        获取剩余时间
        
        Returns:
            剩余时间（秒），如果已超时则返回 0
        """
        if not self._is_running or not self.start_time:
            return float(self.config.global_timeout)
        
        elapsed = self.get_elapsed_time()
        remaining = self.config.global_timeout - elapsed
        return max(0.0, remaining)
    
    def get_time_usage(self) -> dict:
        """
        获取时间使用情况
        
        Returns:
            时间使用信息字典
        """
        elapsed = self.get_elapsed_time()
        remaining = self.get_remaining_time()
        usage_ratio = elapsed / self.config.global_timeout if self.config.global_timeout > 0 else 0.0
        
        return {
            "elapsed_time": elapsed,
            "remaining_time": remaining,
            "total_time": self.config.global_timeout,
            "usage_ratio": usage_ratio,
            "usage_percentage": usage_ratio * 100,
            "is_running": self._is_running,
            "warning_triggered": self._warning_triggered,
            "timeout_triggered": self._timeout_triggered
        }
    
    def _trigger_warning(self, elapsed: float, remaining: float) -> None:
        """
        触发超时警告
        
        Args:
            elapsed: 已用时间
            remaining: 剩余时间
        """
        event = TimeoutEvent(
            timestamp=datetime.now(),
            event_type="warning",
            elapsed_time=elapsed,
            remaining_time=remaining,
            message=f"超时警告: 已用时 {elapsed:.1f} 秒，剩余 {remaining:.1f} 秒"
        )
        
        self.events.append(event)
        logger.warning(event.message)
        
        # 调用警告回调
        if self.on_warning:
            try:
                self.on_warning(event)
            except Exception as e:
                logger.error(f"警告回调执行失败: {e}")
    
    def _trigger_timeout(self, elapsed: float, remaining: float) -> None:
        """
        触发超时
        
        Args:
            elapsed: 已用时间
            remaining: 剩余时间
        """
        event = TimeoutEvent(
            timestamp=datetime.now(),
            event_type="exceeded",
            elapsed_time=elapsed,
            remaining_time=remaining,
            message=f"任务超时: 已用时 {elapsed:.1f} 秒，超过限制 {self.config.global_timeout} 秒"
        )
        
        self.events.append(event)
        logger.error(event.message)
        
        # 调用超时回调
        if self.on_timeout:
            try:
                self.on_timeout(event)
            except Exception as e:
                logger.error(f"超时回调执行失败: {e}")
        
        # 执行清理钩子
        if self.cleanup_hook:
            try:
                logger.info("执行清理钩子...")
                self.cleanup_hook()
                logger.info("清理钩子执行完成")
            except Exception as e:
                logger.error(f"清理钩子执行失败: {e}")
    
    def collect_diagnostics(self) -> dict:
        """
        收集超时诊断信息
        
        Returns:
            诊断信息字典
        """
        time_usage = self.get_time_usage()
        
        diagnostics = {
            "timeout_config": {
                "global_timeout": self.config.global_timeout,
                "warning_threshold": self.config.warning_threshold,
                "check_interval": self.config.check_interval
            },
            "time_usage": time_usage,
            "events": [
                {
                    "timestamp": event.timestamp.isoformat(),
                    "type": event.event_type,
                    "elapsed_time": event.elapsed_time,
                    "remaining_time": event.remaining_time,
                    "message": event.message
                }
                for event in self.events
            ],
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None
        }
        
        return diagnostics
    
    def format_diagnostics(self, diagnostics: dict) -> str:
        """
        格式化诊断信息为可读文本
        
        Args:
            diagnostics: 诊断信息字典
        
        Returns:
            格式化的诊断文本
        """
        lines = [
            "=" * 60,
            "超时诊断信息",
            "=" * 60,
            "",
            "配置:",
            f"  全局超时: {diagnostics['timeout_config']['global_timeout']} 秒",
            f"  警告阈值: {diagnostics['timeout_config']['warning_threshold'] * 100:.0f}%",
            "",
            "时间使用:",
            f"  已用时间: {diagnostics['time_usage']['elapsed_time']:.2f} 秒",
            f"  剩余时间: {diagnostics['time_usage']['remaining_time']:.2f} 秒",
            f"  使用率: {diagnostics['time_usage']['usage_percentage']:.1f}%",
            f"  状态: {'运行中' if diagnostics['time_usage']['is_running'] else '已停止'}",
        ]
        
        if diagnostics['time_usage']['warning_triggered']:
            lines.append("  警告: 已触发")
        
        if diagnostics['time_usage']['timeout_triggered']:
            lines.append("  超时: 已触发")
        
        # 事件历史
        if diagnostics['events']:
            lines.extend([
                "",
                "事件历史:"
            ])
            for event in diagnostics['events']:
                lines.append(
                    f"  [{event['timestamp']}] {event['type']}: {event['message']}"
                )
        
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def reset(self) -> None:
        """重置控制器状态"""
        self.start_time = None
        self.end_time = None
        self.events.clear()
        self._warning_triggered = False
        self._timeout_triggered = False
        self._is_running = False
