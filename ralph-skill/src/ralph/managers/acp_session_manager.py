"""
ACP Session Manager

管理 ACP 会话的超时、自动销毁和资源监控
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from ralph.models.acp import ACPSession, ACPSessionConfig, NetworkPolicy, ResourceLimits

logger = logging.getLogger(__name__)


class ACPSessionManager:
    """
    ACP Session Manager

    管理会话超时、自动销毁和资源监控
    """

    def __init__(self, harness_manager):
        """
        初始化 ACP Session Manager

        Args:
            harness_manager: ACP Harness Manager 实例
        """
        self.harness_manager = harness_manager
        self._monitoring_thread: Optional[threading.Thread] = None
        self._stop_monitoring = threading.Event()
        self._monitoring_interval = 30  # 监控间隔（秒）

        logger.info("ACP Session Manager 初始化完成")

    def start_monitoring(self):
        """启动会话监控"""
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            logger.warning("会话监控已在运行")
            return

        self._stop_monitoring.clear()
        self._monitoring_thread = threading.Thread(target=self._monitor_sessions, daemon=True)
        self._monitoring_thread.start()

        logger.info("会话监控已启动")

    def stop_monitoring(self):
        """停止会话监控"""
        if not self._monitoring_thread or not self._monitoring_thread.is_alive():
            logger.warning("会话监控未运行")
            return

        self._stop_monitoring.set()
        self._monitoring_thread.join(timeout=5)

        logger.info("会话监控已停止")

    def _monitor_sessions(self):
        """监控会话（后台线程）"""
        logger.info("会话监控线程启动")

        while not self._stop_monitoring.is_set():
            try:
                self._check_session_timeouts()
                self._check_idle_sessions()
                self._update_resource_usage()
            except Exception as e:
                logger.error(f"会话监控错误: {e}", exc_info=True)

            # 等待下一次检查
            self._stop_monitoring.wait(self._monitoring_interval)

        logger.info("会话监控线程停止")

    def _check_session_timeouts(self):
        """检查会话超时"""
        sessions = self.harness_manager.list_sessions()
        now = datetime.now()

        for session_info in sessions:
            try:
                session = self.harness_manager._sessions.get(session_info.session_id)
                if not session:
                    continue

                # 检查会话是否超时
                timeout_seconds = session.config.timeout
                elapsed = (now - session.created_at).total_seconds()

                if elapsed > timeout_seconds:
                    logger.warning(
                        f"会话超时: session_id={session.session_id}, "
                        f"elapsed={elapsed}s, timeout={timeout_seconds}s"
                    )

                    # 如果配置了自动销毁，则销毁会话
                    if session.config.auto_destroy:
                        logger.info(f"自动销毁超时会话: {session.session_id}")
                        self.harness_manager.destroy_session(session.session_id, force=True)

            except Exception as e:
                logger.error(f"检查会话超时失败: session_id={session_info.session_id}, error={e}")

    def _check_idle_sessions(self):
        """检查空闲会话"""
        sessions = self.harness_manager.list_sessions()
        now = datetime.now()
        idle_threshold = 300  # 5 分钟无操作视为空闲

        for session_info in sessions:
            try:
                session = self.harness_manager._sessions.get(session_info.session_id)
                if not session or session.status != "active":
                    continue

                # 检查会话是否空闲
                idle_seconds = (now - session.last_used_at).total_seconds()

                if idle_seconds > idle_threshold:
                    logger.debug(f"会话空闲: session_id={session.session_id}, idle={idle_seconds}s")
                    session.status = "idle"

            except Exception as e:
                logger.error(f"检查会话空闲失败: session_id={session_info.session_id}, error={e}")

    def _update_resource_usage(self):
        """更新资源使用情况"""
        sessions = self.harness_manager.list_sessions()

        for session_info in sessions:
            try:
                session = self.harness_manager._sessions.get(session_info.session_id)
                if not session:
                    continue

                # 模拟资源使用更新（实际应该从 ACP Harness API 获取）
                # 这里只是示例，实际实现需要调用真实的监控 API
                session.resource_usage.timestamp = datetime.now()

                # 检查资源使用是否超限
                self._check_resource_limits(session)

            except Exception as e:
                logger.error(f"更新资源使用失败: session_id={session_info.session_id}, error={e}")

    def _check_resource_limits(self, session: ACPSession):
        """检查资源限制"""
        usage = session.resource_usage
        limits = session.config.resource_limits

        # 检查 CPU 使用
        if limits.cpu_limit and usage.cpu_percent > usage.cpu_limit_cores * 100:
            logger.warning(
                f"会话 CPU 使用超限: session_id={session.session_id}, "
                f"usage={usage.cpu_percent}%, limit={usage.cpu_limit_cores * 100}%"
            )

        # 检查内存使用
        if limits.memory_limit and usage.memory_usage_mb > usage.memory_limit_mb:
            logger.warning(
                f"会话内存使用超限: session_id={session.session_id}, "
                f"usage={usage.memory_usage_mb}MB, limit={usage.memory_limit_mb}MB"
            )

        # 检查磁盘使用
        if limits.disk_limit and usage.disk_usage_mb > usage.disk_limit_mb:
            logger.warning(
                f"会话磁盘使用超限: session_id={session.session_id}, "
                f"usage={usage.disk_usage_mb}MB, limit={usage.disk_limit_mb}MB"
            )

    def validate_session_config(self, config: ACPSessionConfig) -> List[str]:
        """
        验证会话配置

        Args:
            config: 会话配置

        Returns:
            List[str]: 验证错误列表（空列表表示验证通过）
        """
        errors = []

        # 验证会话名称
        if not config.name or not config.name.strip():
            errors.append("会话名称不能为空")

        # 验证超时时间
        if config.timeout <= 0:
            errors.append("超时时间必须大于 0")
        elif config.timeout > 86400:  # 24 小时
            errors.append("超时时间不能超过 24 小时")

        # 验证资源限制
        if config.resource_limits.cpu_limit and config.resource_limits.cpu_limit <= 0:
            errors.append("CPU 限制必须大于 0")

        if config.resource_limits.memory_limit:
            try:
                mem_mb = self.harness_manager._parse_memory_limit(config.resource_limits.memory_limit)
                if mem_mb <= 0:
                    errors.append("内存限制必须大于 0")
            except Exception as e:
                errors.append(f"内存限制格式错误: {e}")

        if config.resource_limits.disk_limit:
            try:
                disk_mb = self.harness_manager._parse_memory_limit(config.resource_limits.disk_limit)
                if disk_mb <= 0:
                    errors.append("磁盘限制必须大于 0")
            except Exception as e:
                errors.append(f"磁盘限制格式错误: {e}")

        # 验证网络策略
        if config.network_policy.allow_privileged:
            logger.warning("会话配置允许特权模式，存在安全风险")

        if config.network_policy.allow_host_network:
            logger.warning("会话配置允许主机网络，存在安全风险")

        if config.network_policy.allow_host_pid:
            logger.warning("会话配置允许主机 PID 命名空间，存在安全风险")

        # 验证平台列表
        if not config.platforms:
            errors.append("至少需要指定一个平台")

        supported_platforms = ["linux/amd64", "linux/arm64", "linux/arm/v7"]
        for platform in config.platforms:
            if platform not in supported_platforms:
                errors.append(f"不支持的平台: {platform}")

        return errors

    def create_default_config(self, name: str) -> ACPSessionConfig:
        """
        创建默认会话配置

        Args:
            name: 会话名称

        Returns:
            ACPSessionConfig: 默认配置
        """
        return ACPSessionConfig(
            name=name,
            resource_limits=ResourceLimits(
                cpu_limit=2.0,
                memory_limit="2g",
                disk_limit="10g",
            ),
            network_policy=NetworkPolicy(
                allow_internet=False,
                allowed_hosts=[],
                blocked_ports=[],
                use_proxy=False,
                allow_privileged=False,
                allow_host_network=False,
                allow_host_pid=False,
            ),
            timeout=3600,  # 1 小时
            auto_destroy=True,
            enable_qemu=True,
            enable_buildkit=True,
            platforms=["linux/amd64"],
        )

    def create_secure_config(self, name: str) -> ACPSessionConfig:
        """
        创建安全的会话配置（最小权限）

        Args:
            name: 会话名称

        Returns:
            ACPSessionConfig: 安全配置
        """
        return ACPSessionConfig(
            name=name,
            resource_limits=ResourceLimits(
                cpu_limit=1.0,
                memory_limit="1g",
                disk_limit="5g",
            ),
            network_policy=NetworkPolicy(
                allow_internet=False,
                allowed_hosts=[],
                blocked_ports=list(range(1, 1024)),  # 阻止所有特权端口
                use_proxy=False,
                allow_privileged=False,
                allow_host_network=False,
                allow_host_pid=False,
                max_file_size_mb=512,
            ),
            timeout=1800,  # 30 分钟
            auto_destroy=True,
            enable_qemu=False,  # 禁用 QEMU 以提高安全性
            enable_buildkit=True,
            platforms=["linux/amd64"],
        )

    def get_session_statistics(self) -> Dict:
        """
        获取会话统计信息

        Returns:
            Dict: 统计信息
        """
        sessions = self.harness_manager.list_sessions()

        stats = {
            "total_sessions": len(sessions),
            "active_sessions": 0,
            "idle_sessions": 0,
            "creating_sessions": 0,
            "destroying_sessions": 0,
            "failed_sessions": 0,
            "total_operations": 0,
            "average_uptime_seconds": 0,
            "average_resource_usage_percent": 0,
        }

        if not sessions:
            return stats

        total_uptime = 0
        total_resource_usage = 0

        for session_info in sessions:
            # 统计状态
            if session_info.status == "active":
                stats["active_sessions"] += 1
            elif session_info.status == "idle":
                stats["idle_sessions"] += 1
            elif session_info.status == "creating":
                stats["creating_sessions"] += 1
            elif session_info.status == "destroying":
                stats["destroying_sessions"] += 1
            elif session_info.status == "failed":
                stats["failed_sessions"] += 1

            # 累计统计
            stats["total_operations"] += session_info.operations_count
            total_uptime += session_info.uptime_seconds
            total_resource_usage += session_info.resource_usage_percent

        # 计算平均值
        stats["average_uptime_seconds"] = total_uptime / len(sessions)
        stats["average_resource_usage_percent"] = total_resource_usage / len(sessions)

        return stats
