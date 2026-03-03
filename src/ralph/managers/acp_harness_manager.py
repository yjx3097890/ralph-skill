"""
ACP Harness Manager

管理 ACP (Agent Coding Platform) Harness 会话的生命周期，
提供 hardened 的 Docker-in-Docker 环境，支持安全隔离的容器操作、
多架构构建和 Git 集成。
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from ralph.models.acp import (
    ACPAuditLog,
    ACPError,
    ACPPerformanceMetrics,
    ACPResourceUsage,
    ACPSession,
    ACPSessionConfig,
    ACPSessionInfo,
    ACPSessionStatus,
    LogEntry,
    LogFilter,
    NetworkPolicy,
    ResourceLimits,
)

logger = logging.getLogger(__name__)


class ACPHarnessManager:
    """
    ACP Harness Manager

    管理 ACP 会话的创建、使用、销毁和监控。
    提供安全隔离的 Docker-in-Docker 环境。
    """

    def __init__(self, harness_endpoint: str, api_key: str, max_concurrent_sessions: int = 5):
        """
        初始化 ACP Harness Manager

        Args:
            harness_endpoint: ACP Harness 服务端点
            api_key: API 认证密钥
            max_concurrent_sessions: 最大并发会话数
        """
        self.harness_endpoint = harness_endpoint
        self.api_key = api_key
        self.max_concurrent_sessions = max_concurrent_sessions

        # 会话存储
        self._sessions: Dict[str, ACPSession] = {}
        # 审计日志存储
        self._audit_logs: List[ACPAuditLog] = []
        # 日志存储
        self._logs: Dict[str, List[LogEntry]] = {}

        logger.info(
            f"ACP Harness Manager 初始化完成: endpoint={harness_endpoint}, "
            f"max_sessions={max_concurrent_sessions}"
        )

    def create_session(self, config: ACPSessionConfig) -> ACPSession:
        """
        创建 ACP 会话

        Args:
            config: 会话配置

        Returns:
            ACPSession: 创建的会话实例

        Raises:
            ACPError: 会话创建失败
        """
        # 检查并发会话数限制
        active_sessions = [s for s in self._sessions.values() if s.status in ["creating", "active", "idle"]]
        if len(active_sessions) >= self.max_concurrent_sessions:
            raise ACPError(
                type="resource_exhausted",
                message=f"ACP 会话数量已达上限: {self.max_concurrent_sessions}",
                details={"active_sessions": len(active_sessions)},
                recoverable=True,
            )

        # 生成唯一会话 ID
        session_id = f"acp-{uuid.uuid4().hex[:12]}"

        logger.info(f"创建 ACP 会话: session_id={session_id}, name={config.name}")

        try:
            # 创建会话实例
            now = datetime.now()
            session = ACPSession(
                session_id=session_id,
                name=config.name,
                status="creating",
                created_at=now,
                last_used_at=now,
                docker_endpoint=f"{self.harness_endpoint}/sessions/{session_id}/docker",
                git_endpoint=f"{self.harness_endpoint}/sessions/{session_id}/git",
                buildkit_endpoint=f"{self.harness_endpoint}/sessions/{session_id}/buildkit",
                resource_usage=ACPResourceUsage(
                    session_id=session_id,
                    timestamp=now,
                    cpu_percent=0.0,
                    cpu_limit_cores=config.resource_limits.cpu_limit or 2.0,
                    memory_usage_mb=0.0,
                    memory_limit_mb=self._parse_memory_limit(config.resource_limits.memory_limit or "2g"),
                    disk_usage_mb=0.0,
                    disk_limit_mb=self._parse_memory_limit(config.resource_limits.disk_limit or "10g"),
                    network_rx_bytes=0,
                    network_tx_bytes=0,
                    container_count=0,
                ),
                config=config,
                health_status="healthy",
                operations_count=0,
            )

            # 存储会话
            self._sessions[session_id] = session

            # 初始化日志存储
            self._logs[session_id] = []

            # 记录审计日志
            self._record_audit_log(
                session_id=session_id,
                operation_type="create_session",
                operation_details={"name": config.name, "config": config.__dict__},
                user="system",
                success=True,
            )

            # 模拟会话创建过程（实际应该调用 ACP Harness API）
            self._log(session_id, "info", f"会话创建中: {session_id}")
            self._log(session_id, "info", "初始化 Docker-in-Docker 环境...")
            self._log(session_id, "info", "配置网络策略...")
            self._log(session_id, "info", "启用 QEMU 多架构支持..." if config.enable_qemu else "跳过 QEMU 配置")
            self._log(session_id, "info", "启用 Buildkit 引擎..." if config.enable_buildkit else "跳过 Buildkit 配置")

            # 更新会话状态为 active
            session.status = "active"
            self._log(session_id, "info", f"会话创建成功: {session_id}")

            logger.info(f"ACP 会话创建成功: session_id={session_id}")
            return session

        except Exception as e:
            logger.error(f"ACP 会话创建失败: session_id={session_id}, error={e}")

            # 记录失败的审计日志
            self._record_audit_log(
                session_id=session_id,
                operation_type="create_session",
                operation_details={"name": config.name},
                user="system",
                success=False,
                error_message=str(e),
            )

            # 清理失败的会话
            if session_id in self._sessions:
                self._sessions[session_id].status = "failed"

            raise ACPError(
                type="session_creation_failed",
                message=f"ACP 会话创建失败: {e}",
                details={"session_id": session_id, "error": str(e)},
                recoverable=True,
                session_id=session_id,
            )

    def use_session(self, session_id: str) -> ACPSession:
        """
        使用 ACP 会话

        Args:
            session_id: 会话 ID

        Returns:
            ACPSession: 会话实例

        Raises:
            ACPError: 会话不存在或不可用
        """
        if session_id not in self._sessions:
            raise ACPError(
                type="session_not_found",
                message=f"ACP 会话不存在: {session_id}",
                details={"session_id": session_id},
                recoverable=False,
                session_id=session_id,
            )

        session = self._sessions[session_id]

        # 检查会话状态
        if session.status not in ["active", "idle"]:
            raise ACPError(
                type="session_unavailable",
                message=f"ACP 会话不可用: {session_id}, status={session.status}",
                details={"session_id": session_id, "status": session.status},
                recoverable=False,
                session_id=session_id,
            )

        # 更新最后使用时间
        session.last_used_at = datetime.now()
        session.status = "active"
        session.operations_count += 1

        logger.debug(f"使用 ACP 会话: session_id={session_id}, operations={session.operations_count}")

        return session

    def destroy_session(self, session_id: str, force: bool = False) -> bool:
        """
        销毁 ACP 会话

        Args:
            session_id: 会话 ID
            force: 是否强制销毁

        Returns:
            bool: 是否成功销毁

        Raises:
            ACPError: 会话销毁失败
        """
        if session_id not in self._sessions:
            logger.warning(f"尝试销毁不存在的会话: {session_id}")
            return False

        session = self._sessions[session_id]

        logger.info(f"销毁 ACP 会话: session_id={session_id}, force={force}")

        try:
            # 更新会话状态
            session.status = "destroying"
            self._log(session_id, "info", f"开始销毁会话: {session_id}")

            # 模拟销毁过程
            self._log(session_id, "info", "停止所有容器...")
            self._log(session_id, "info", "清理网络资源...")
            self._log(session_id, "info", "清理卷资源...")
            self._log(session_id, "info", "导出日志...")

            # 记录审计日志
            self._record_audit_log(
                session_id=session_id,
                operation_type="destroy_session",
                operation_details={"force": force},
                user="system",
                success=True,
            )

            # 从存储中移除会话
            del self._sessions[session_id]

            self._log(session_id, "info", f"会话销毁成功: {session_id}")
            logger.info(f"ACP 会话销毁成功: session_id={session_id}")

            return True

        except Exception as e:
            logger.error(f"ACP 会话销毁失败: session_id={session_id}, error={e}")

            # 记录失败的审计日志
            self._record_audit_log(
                session_id=session_id,
                operation_type="destroy_session",
                operation_details={"force": force},
                user="system",
                success=False,
                error_message=str(e),
            )

            if force:
                # 强制删除
                if session_id in self._sessions:
                    del self._sessions[session_id]
                logger.warning(f"强制销毁会话: {session_id}")
                return True

            raise ACPError(
                type="session_destruction_failed",
                message=f"ACP 会话销毁失败: {e}",
                details={"session_id": session_id, "error": str(e)},
                recoverable=True,
                session_id=session_id,
            )

    def list_sessions(self) -> List[ACPSessionInfo]:
        """
        列出所有会话

        Returns:
            List[ACPSessionInfo]: 会话信息列表
        """
        session_infos = []

        for session in self._sessions.values():
            uptime = (datetime.now() - session.created_at).total_seconds()
            resource_usage_percent = self._calculate_resource_usage_percent(session)

            session_infos.append(
                ACPSessionInfo(
                    session_id=session.session_id,
                    name=session.name,
                    status=session.status,
                    created_at=session.created_at,
                    uptime_seconds=int(uptime),
                    operations_count=session.operations_count,
                    resource_usage_percent=resource_usage_percent,
                )
            )

        return session_infos

    def get_session_status(self, session_id: str) -> ACPSessionStatus:
        """
        获取会话状态

        Args:
            session_id: 会话 ID

        Returns:
            ACPSessionStatus: 会话状态

        Raises:
            ACPError: 会话不存在
        """
        if session_id not in self._sessions:
            raise ACPError(
                type="session_not_found",
                message=f"ACP 会话不存在: {session_id}",
                details={"session_id": session_id},
                recoverable=False,
                session_id=session_id,
            )

        session = self._sessions[session_id]
        uptime = (datetime.now() - session.created_at).total_seconds()

        return ACPSessionStatus(
            session_id=session.session_id,
            status=session.status,
            uptime_seconds=int(uptime),
            operations_count=session.operations_count,
            resource_usage=session.resource_usage,
            health_status=session.health_status,
            last_error=None,  # TODO: 实现错误跟踪
        )

    def set_resource_limits(self, session_id: str, limits: ResourceLimits) -> bool:
        """
        设置资源限制

        Args:
            session_id: 会话 ID
            limits: 资源限制

        Returns:
            bool: 是否成功设置

        Raises:
            ACPError: 会话不存在
        """
        if session_id not in self._sessions:
            raise ACPError(
                type="session_not_found",
                message=f"ACP 会话不存在: {session_id}",
                details={"session_id": session_id},
                recoverable=False,
                session_id=session_id,
            )

        session = self._sessions[session_id]
        session.config.resource_limits = limits

        # 更新资源使用情况的限制
        if limits.cpu_limit:
            session.resource_usage.cpu_limit_cores = limits.cpu_limit
        if limits.memory_limit:
            session.resource_usage.memory_limit_mb = self._parse_memory_limit(limits.memory_limit)
        if limits.disk_limit:
            session.resource_usage.disk_limit_mb = self._parse_memory_limit(limits.disk_limit)

        self._log(session_id, "info", f"更新资源限制: {limits}")
        logger.info(f"更新会话资源限制: session_id={session_id}, limits={limits}")

        return True

    def get_session_logs(self, session_id: str, filter: Optional[LogFilter] = None) -> List[LogEntry]:
        """
        获取会话日志

        Args:
            session_id: 会话 ID
            filter: 日志过滤器

        Returns:
            List[LogEntry]: 日志条目列表

        Raises:
            ACPError: 会话不存在
        """
        if session_id not in self._logs:
            raise ACPError(
                type="session_not_found",
                message=f"ACP 会话不存在: {session_id}",
                details={"session_id": session_id},
                recoverable=False,
                session_id=session_id,
            )

        logs = self._logs[session_id]

        # 应用过滤器
        if filter:
            logs = self._apply_log_filter(logs, filter)

        return logs

    def export_session_logs(self, session_id: str, format: str = "json") -> str:
        """
        导出会话日志

        Args:
            session_id: 会话 ID
            format: 导出格式（json, text）

        Returns:
            str: 导出的日志内容

        Raises:
            ACPError: 会话不存在或格式不支持
        """
        logs = self.get_session_logs(session_id)

        if format == "json":
            import json

            return json.dumps([log.__dict__ for log in logs], default=str, indent=2)
        elif format == "text":
            lines = []
            for log in logs:
                lines.append(f"[{log.timestamp}] [{log.level.upper()}] {log.message}")
            return "\n".join(lines)
        else:
            raise ACPError(
                type="invalid_format",
                message=f"不支持的日志格式: {format}",
                details={"format": format, "supported": ["json", "text"]},
                recoverable=False,
            )

    def monitor_session_performance(self, session_id: str) -> ACPPerformanceMetrics:
        """
        监控会话性能

        Args:
            session_id: 会话 ID

        Returns:
            ACPPerformanceMetrics: 性能指标

        Raises:
            ACPError: 会话不存在
        """
        if session_id not in self._sessions:
            raise ACPError(
                type="session_not_found",
                message=f"ACP 会话不存在: {session_id}",
                details={"session_id": session_id},
                recoverable=False,
                session_id=session_id,
            )

        session = self._sessions[session_id]
        uptime_minutes = (datetime.now() - session.created_at).total_seconds() / 60

        # 计算性能指标
        operations_per_minute = session.operations_count / uptime_minutes if uptime_minutes > 0 else 0
        average_operation_time = uptime_minutes * 60 / session.operations_count if session.operations_count > 0 else 0

        # TODO: 实现真实的成功率和错误率计算
        success_rate = 0.95
        error_rate = 0.05

        return ACPPerformanceMetrics(
            session_id=session.session_id,
            timestamp=datetime.now(),
            operations_per_minute=operations_per_minute,
            average_operation_time=average_operation_time,
            success_rate=success_rate,
            error_rate=error_rate,
            resource_usage=session.resource_usage,
        )

    def configure_network_policy(self, session_id: str, policy: NetworkPolicy) -> bool:
        """
        配置网络策略

        Args:
            session_id: 会话 ID
            policy: 网络策略

        Returns:
            bool: 是否成功配置

        Raises:
            ACPError: 会话不存在
        """
        if session_id not in self._sessions:
            raise ACPError(
                type="session_not_found",
                message=f"ACP 会话不存在: {session_id}",
                details={"session_id": session_id},
                recoverable=False,
                session_id=session_id,
            )

        session = self._sessions[session_id]
        session.config.network_policy = policy

        self._log(session_id, "info", f"更新网络策略: {policy}")
        logger.info(f"更新会话网络策略: session_id={session_id}, policy={policy}")

        return True

    # 辅助方法

    def _parse_memory_limit(self, limit: str) -> float:
        """解析内存限制字符串为 MB"""
        if not limit:
            return 0.0

        limit = limit.lower().strip()
        if limit.endswith("g"):
            return float(limit[:-1]) * 1024
        elif limit.endswith("m"):
            return float(limit[:-1])
        elif limit.endswith("k"):
            return float(limit[:-1]) / 1024
        else:
            # 假设是字节
            return float(limit) / (1024 * 1024)

    def _calculate_resource_usage_percent(self, session: ACPSession) -> float:
        """计算资源使用百分比"""
        cpu_percent = (
            session.resource_usage.cpu_percent / session.resource_usage.cpu_limit_cores * 100
            if session.resource_usage.cpu_limit_cores > 0
            else 0
        )
        memory_percent = (
            session.resource_usage.memory_usage_mb / session.resource_usage.memory_limit_mb * 100
            if session.resource_usage.memory_limit_mb > 0
            else 0
        )

        # 返回平均值
        return (cpu_percent + memory_percent) / 2

    def _log(self, session_id: str, level: str, message: str, **details):
        """记录日志"""
        if session_id not in self._logs:
            self._logs[session_id] = []

        log_entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            message=message,
            session_id=session_id,
            details=details,
        )

        self._logs[session_id].append(log_entry)

    def _record_audit_log(
        self,
        session_id: str,
        operation_type: str,
        operation_details: Dict,
        user: str,
        success: bool,
        error_message: Optional[str] = None,
    ):
        """记录审计日志"""
        audit_log = ACPAuditLog(
            session_id=session_id,
            timestamp=datetime.now(),
            operation_type=operation_type,
            operation_details=operation_details,
            user=user,
            success=success,
            error_message=error_message,
        )

        self._audit_logs.append(audit_log)

    def _apply_log_filter(self, logs: List[LogEntry], filter: LogFilter) -> List[LogEntry]:
        """应用日志过滤器"""
        filtered_logs = logs

        # 时间范围过滤
        if filter.start_time:
            filtered_logs = [log for log in filtered_logs if log.timestamp >= filter.start_time]
        if filter.end_time:
            filtered_logs = [log for log in filtered_logs if log.timestamp <= filter.end_time]

        # 日志级别过滤
        if filter.log_level:
            filtered_logs = [log for log in filtered_logs if log.level == filter.log_level]

        # 关键字过滤
        if filter.keywords:
            filtered_logs = [
                log for log in filtered_logs if any(keyword in log.message for keyword in filter.keywords)
            ]

        # 限制数量
        if filter.limit:
            filtered_logs = filtered_logs[: filter.limit]

        return filtered_logs
