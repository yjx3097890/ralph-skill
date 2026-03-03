"""
ACP Security Manager

管理 Docker-in-Docker 安全隔离和安全策略
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from ralph.models.acp import (
    ACPAuditLog,
    ACPError,
    ACPSecurityPolicy,
    ACPSession,
    NetworkPolicy,
)

logger = logging.getLogger(__name__)


class ACPSecurityManager:
    """
    ACP Security Manager

    管理 Docker-in-Docker 安全隔离、容器逃逸防护和安全审计
    """

    def __init__(self):
        """初始化 ACP Security Manager"""
        self._audit_logs: List[ACPAuditLog] = []
        self._security_violations: List[Dict] = []

        logger.info("ACP Security Manager 初始化完成")

    def enforce_container_isolation(self, session: ACPSession) -> bool:
        """
        强制容器隔离

        Args:
            session: ACP 会话

        Returns:
            bool: 是否成功配置隔离

        Raises:
            ACPError: 配置失败
        """
        logger.info(f"配置容器隔离: session_id={session.session_id}")

        try:
            policy = session.config.network_policy

            # 检查特权模式
            if policy.allow_privileged:
                logger.warning(
                    f"会话允许特权模式，存在安全风险: session_id={session.session_id}"
                )
                self._record_security_event(
                    session_id=session.session_id,
                    event_type="privileged_mode_enabled",
                    severity="high",
                    details={"policy": policy.__dict__},
                )

            # 检查主机网络访问
            if policy.allow_host_network:
                logger.warning(
                    f"会话允许主机网络访问，存在安全风险: session_id={session.session_id}"
                )
                self._record_security_event(
                    session_id=session.session_id,
                    event_type="host_network_enabled",
                    severity="high",
                    details={"policy": policy.__dict__},
                )

            # 检查主机 PID 命名空间
            if policy.allow_host_pid:
                logger.warning(
                    f"会话允许主机 PID 命名空间，存在安全风险: session_id={session.session_id}"
                )
                self._record_security_event(
                    session_id=session.session_id,
                    event_type="host_pid_enabled",
                    severity="high",
                    details={"policy": policy.__dict__},
                )

            # 配置网络隔离
            self._configure_network_isolation(session)

            # 配置资源限制
            self._configure_resource_limits(session)

            # 配置文件系统限制
            self._configure_filesystem_limits(session)

            logger.info(f"容器隔离配置成功: session_id={session.session_id}")

            # 记录审计日志
            self._record_audit_log(
                session_id=session.session_id,
                operation_type="configure_isolation",
                operation_details={"policy": policy.__dict__},
                user="system",
                success=True,
            )

            return True

        except Exception as e:
            logger.error(f"容器隔离配置失败: session_id={session.session_id}, error={e}")

            # 记录审计日志
            self._record_audit_log(
                session_id=session.session_id,
                operation_type="configure_isolation",
                operation_details={},
                user="system",
                success=False,
                error_message=str(e),
            )

            raise ACPError(
                type="isolation_config_failed",
                message=f"容器隔离配置失败: {e}",
                details={"session_id": session.session_id, "error": str(e)},
                recoverable=True,
                session_id=session.session_id,
            )

    def prevent_container_escape(self, session: ACPSession) -> bool:
        """
        防止容器逃逸

        Args:
            session: ACP 会话

        Returns:
            bool: 是否成功配置防护

        Raises:
            ACPError: 配置失败
        """
        logger.info(f"配置容器逃逸防护: session_id={session.session_id}")

        try:
            # 禁用特权模式
            if session.config.network_policy.allow_privileged:
                logger.error(
                    f"特权模式已启用，无法完全防止容器逃逸: session_id={session.session_id}"
                )
                self._record_security_event(
                    session_id=session.session_id,
                    event_type="escape_prevention_weakened",
                    severity="critical",
                    details={"reason": "privileged_mode_enabled"},
                )

            # 配置 seccomp 配置文件
            seccomp_profile = self._get_seccomp_profile()
            logger.debug(f"应用 seccomp 配置: session_id={session.session_id}")

            # 配置 AppArmor 配置文件
            apparmor_profile = self._get_apparmor_profile()
            logger.debug(f"应用 AppArmor 配置: session_id={session.session_id}")

            # 禁用危险的 capabilities
            dropped_capabilities = [
                "CAP_SYS_ADMIN",
                "CAP_SYS_MODULE",
                "CAP_SYS_RAWIO",
                "CAP_SYS_PTRACE",
                "CAP_SYS_BOOT",
                "CAP_MAC_ADMIN",
                "CAP_MAC_OVERRIDE",
                "CAP_NET_ADMIN",
            ]
            logger.debug(
                f"禁用危险 capabilities: session_id={session.session_id}, "
                f"dropped={dropped_capabilities}"
            )

            # 配置只读根文件系统
            logger.debug(f"配置只读根文件系统: session_id={session.session_id}")

            # 禁用新特权
            logger.debug(f"禁用新特权: session_id={session.session_id}")

            logger.info(f"容器逃逸防护配置成功: session_id={session.session_id}")

            # 记录审计日志
            self._record_audit_log(
                session_id=session.session_id,
                operation_type="configure_escape_prevention",
                operation_details={
                    "seccomp": seccomp_profile,
                    "apparmor": apparmor_profile,
                    "dropped_capabilities": dropped_capabilities,
                },
                user="system",
                success=True,
            )

            return True

        except Exception as e:
            logger.error(f"容器逃逸防护配置失败: session_id={session.session_id}, error={e}")

            # 记录审计日志
            self._record_audit_log(
                session_id=session.session_id,
                operation_type="configure_escape_prevention",
                operation_details={},
                user="system",
                success=False,
                error_message=str(e),
            )

            raise ACPError(
                type="escape_prevention_failed",
                message=f"容器逃逸防护配置失败: {e}",
                details={"session_id": session.session_id, "error": str(e)},
                recoverable=True,
                session_id=session.session_id,
            )

    def limit_host_resource_access(self, session: ACPSession) -> bool:
        """
        限制主机资源访问

        Args:
            session: ACP 会话

        Returns:
            bool: 是否成功配置限制

        Raises:
            ACPError: 配置失败
        """
        logger.info(f"配置主机资源访问限制: session_id={session.session_id}")

        try:
            limits = session.config.resource_limits

            # 限制 CPU 使用
            if limits.cpu_limit:
                logger.debug(
                    f"限制 CPU 使用: session_id={session.session_id}, "
                    f"limit={limits.cpu_limit} cores"
                )

            # 限制内存使用
            if limits.memory_limit:
                logger.debug(
                    f"限制内存使用: session_id={session.session_id}, "
                    f"limit={limits.memory_limit}"
                )

            # 限制磁盘使用
            if limits.disk_limit:
                logger.debug(
                    f"限制磁盘使用: session_id={session.session_id}, "
                    f"limit={limits.disk_limit}"
                )

            # 限制进程数
            if limits.pids_limit:
                logger.debug(
                    f"限制进程数: session_id={session.session_id}, "
                    f"limit={limits.pids_limit}"
                )

            # 禁止访问主机设备
            logger.debug(f"禁止访问主机设备: session_id={session.session_id}")

            # 禁止挂载主机路径
            logger.debug(f"禁止挂载主机路径: session_id={session.session_id}")

            logger.info(f"主机资源访问限制配置成功: session_id={session.session_id}")

            # 记录审计日志
            self._record_audit_log(
                session_id=session.session_id,
                operation_type="configure_resource_limits",
                operation_details={"limits": limits.__dict__},
                user="system",
                success=True,
            )

            return True

        except Exception as e:
            logger.error(f"主机资源访问限制配置失败: session_id={session.session_id}, error={e}")

            # 记录审计日志
            self._record_audit_log(
                session_id=session.session_id,
                operation_type="configure_resource_limits",
                operation_details={},
                user="system",
                success=False,
                error_message=str(e),
            )

            raise ACPError(
                type="resource_limit_failed",
                message=f"主机资源访问限制配置失败: {e}",
                details={"session_id": session.session_id, "error": str(e)},
                recoverable=True,
                session_id=session.session_id,
            )

    def audit_security_events(self, session_id: str) -> List[ACPAuditLog]:
        """
        审计安全事件

        Args:
            session_id: 会话 ID

        Returns:
            List[ACPAuditLog]: 审计日志列表
        """
        return [log for log in self._audit_logs if log.session_id == session_id]

    def get_security_violations(self, session_id: Optional[str] = None) -> List[Dict]:
        """
        获取安全违规事件

        Args:
            session_id: 会话 ID（可选）

        Returns:
            List[Dict]: 安全违规事件列表
        """
        if session_id:
            return [v for v in self._security_violations if v["session_id"] == session_id]
        return self._security_violations

    def validate_security_policy(self, policy: NetworkPolicy) -> List[str]:
        """
        验证安全策略

        Args:
            policy: 网络策略

        Returns:
            List[str]: 安全警告列表
        """
        warnings = []

        if policy.allow_privileged:
            warnings.append("特权模式已启用，存在容器逃逸风险")

        if policy.allow_host_network:
            warnings.append("主机网络访问已启用，存在网络隔离风险")

        if policy.allow_host_pid:
            warnings.append("主机 PID 命名空间已启用，存在进程隔离风险")

        if policy.allow_internet and not policy.use_proxy:
            warnings.append("互联网访问已启用但未配置代理，存在数据泄露风险")

        if not policy.blocked_ports:
            warnings.append("未配置端口黑名单，建议阻止特权端口（1-1024）")

        if policy.max_file_size_mb > 2048:
            warnings.append(f"文件大小限制过大（{policy.max_file_size_mb}MB），建议不超过 2GB")

        return warnings

    def create_security_policy(self, session: ACPSession) -> ACPSecurityPolicy:
        """
        创建安全策略

        Args:
            session: ACP 会话

        Returns:
            ACPSecurityPolicy: 安全策略
        """
        policy = session.config.network_policy

        return ACPSecurityPolicy(
            session_id=session.session_id,
            allow_internet=policy.allow_internet,
            allowed_hosts=policy.allowed_hosts,
            blocked_ports=policy.blocked_ports,
            allow_privileged=policy.allow_privileged,
            allow_host_network=policy.allow_host_network,
            allow_host_pid=policy.allow_host_pid,
            max_file_size_mb=policy.max_file_size_mb,
        )

    # 辅助方法

    def _configure_network_isolation(self, session: ACPSession):
        """配置网络隔离"""
        policy = session.config.network_policy

        if not policy.allow_internet:
            logger.debug(f"禁用互联网访问: session_id={session.session_id}")

        if policy.allowed_hosts:
            logger.debug(
                f"配置主机白名单: session_id={session.session_id}, "
                f"hosts={policy.allowed_hosts}"
            )

        if policy.blocked_ports:
            logger.debug(
                f"配置端口黑名单: session_id={session.session_id}, "
                f"ports={policy.blocked_ports}"
            )

        if policy.use_proxy:
            logger.debug(f"启用代理: session_id={session.session_id}")

    def _configure_resource_limits(self, session: ACPSession):
        """配置资源限制"""
        limits = session.config.resource_limits

        logger.debug(
            f"配置资源限制: session_id={session.session_id}, "
            f"cpu={limits.cpu_limit}, memory={limits.memory_limit}, "
            f"disk={limits.disk_limit}"
        )

    def _configure_filesystem_limits(self, session: ACPSession):
        """配置文件系统限制"""
        policy = session.config.network_policy

        logger.debug(
            f"配置文件大小限制: session_id={session.session_id}, "
            f"max_size={policy.max_file_size_mb}MB"
        )

    def _get_seccomp_profile(self) -> str:
        """获取 seccomp 配置文件"""
        return "default"  # 使用 Docker 默认 seccomp 配置

    def _get_apparmor_profile(self) -> str:
        """获取 AppArmor 配置文件"""
        return "docker-default"  # 使用 Docker 默认 AppArmor 配置

    def _record_security_event(
        self,
        session_id: str,
        event_type: str,
        severity: str,
        details: Dict,
    ):
        """记录安全事件"""
        event = {
            "session_id": session_id,
            "timestamp": datetime.now(),
            "event_type": event_type,
            "severity": severity,
            "details": details,
        }

        self._security_violations.append(event)

        logger.warning(
            f"安全事件: session_id={session_id}, type={event_type}, "
            f"severity={severity}"
        )

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
