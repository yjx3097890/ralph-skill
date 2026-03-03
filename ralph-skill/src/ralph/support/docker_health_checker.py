"""
Docker 容器健康检查和诊断

实现容器健康检查机制、服务就绪状态验证和诊断信息收集。
"""

import docker
from docker.errors import DockerException
import time
from typing import Optional, Dict, List
import logging

from ralph.models.docker import HealthStatus, Container

logger = logging.getLogger(__name__)


class DockerHealthChecker:
    """Docker 健康检查器"""

    def __init__(self, docker_client: docker.DockerClient):
        """
        初始化健康检查器

        Args:
            docker_client: Docker 客户端实例
        """
        self.client = docker_client

    def check_container_health(self, container_id: str) -> HealthStatus:
        """
        检查容器健康状态

        Args:
            container_id: 容器 ID

        Returns:
            HealthStatus: 健康状态
        """
        try:
            container = self.client.containers.get(container_id)
            attrs = container.attrs

            # 获取健康检查状态
            state = attrs.get("State", {})
            health = state.get("Health", {})

            if not health:
                # 没有配置健康检查
                return HealthStatus(
                    healthy=state.get("Running", False),
                    status="none",
                    failing_streak=0,
                    log=[],
                )

            health_status = health.get("Status", "none")
            failing_streak = health.get("FailingStreak", 0)
            
            # 提取健康检查日志
            log_entries = []
            for log_entry in health.get("Log", []):
                output = log_entry.get("Output", "").strip()
                if output:
                    log_entries.append(output)

            is_healthy = health_status == "healthy"

            return HealthStatus(
                healthy=is_healthy,
                status=health_status,
                failing_streak=failing_streak,
                log=log_entries,
            )

        except DockerException as e:
            logger.error(f"检查容器健康状态失败: {e}")
            return HealthStatus(
                healthy=False,
                status="unknown",
                failing_streak=0,
                log=[f"ERROR: {e}"],
            )

    def wait_for_healthy(
        self, container_id: str, timeout: int = 60, check_interval: int = 2
    ) -> bool:
        """
        等待容器变为健康状态

        Args:
            container_id: 容器 ID
            timeout: 超时时间（秒）
            check_interval: 检查间隔（秒）

        Returns:
            bool: 是否在超时前变为健康状态
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            health_status = self.check_container_health(container_id)
            
            if health_status.healthy:
                logger.info(f"容器健康检查通过: {container_id[:12]}")
                return True
            
            if health_status.status == "unhealthy":
                logger.warning(
                    f"容器健康检查失败 (尝试 {health_status.failing_streak}): {container_id[:12]}"
                )
                # 如果连续失败次数过多，提前退出
                if health_status.failing_streak >= 5:
                    logger.error(f"容器健康检查连续失败，放弃等待: {container_id[:12]}")
                    return False
            
            time.sleep(check_interval)
        
        logger.error(f"容器健康检查超时: {container_id[:12]}")
        return False

    def check_service_ready(
        self, container_id: str, port: int, timeout: int = 30
    ) -> bool:
        """
        检查服务是否就绪（通过端口检查）

        Args:
            container_id: 容器 ID
            port: 服务端口
            timeout: 超时时间（秒）

        Returns:
            bool: 服务是否就绪
        """
        import socket
        
        try:
            container = self.client.containers.get(container_id)
            attrs = container.attrs
            
            # 获取容器 IP 地址
            networks = attrs.get("NetworkSettings", {}).get("Networks", {})
            if not networks:
                logger.error(f"容器没有网络配置: {container_id[:12]}")
                return False
            
            # 获取第一个网络的 IP 地址
            network_name = list(networks.keys())[0]
            ip_address = networks[network_name].get("IPAddress")
            
            if not ip_address:
                logger.error(f"无法获取容器 IP 地址: {container_id[:12]}")
                return False
            
            # 尝试连接端口
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    result = sock.connect_ex((ip_address, port))
                    sock.close()
                    
                    if result == 0:
                        logger.info(f"服务就绪: {container_id[:12]}:{port}")
                        return True
                    
                except socket.error:
                    pass
                
                time.sleep(1)
            
            logger.error(f"服务就绪检查超时: {container_id[:12]}:{port}")
            return False
            
        except DockerException as e:
            logger.error(f"服务就绪检查失败: {e}")
            return False

    def collect_diagnostic_info(self, container_id: str) -> Dict[str, any]:
        """
        收集容器诊断信息

        Args:
            container_id: 容器 ID

        Returns:
            Dict[str, any]: 诊断信息
        """
        diagnostic_info = {
            "container_id": container_id,
            "status": "unknown",
            "health_status": None,
            "logs": "",
            "resource_usage": None,
            "network_info": {},
            "errors": [],
        }

        try:
            container = self.client.containers.get(container_id)
            attrs = container.attrs

            # 基本状态
            state = attrs.get("State", {})
            diagnostic_info["status"] = state.get("Status", "unknown")
            diagnostic_info["running"] = state.get("Running", False)
            diagnostic_info["exit_code"] = state.get("ExitCode", 0)
            diagnostic_info["error"] = state.get("Error", "")

            # 健康检查状态
            health_status = self.check_container_health(container_id)
            diagnostic_info["health_status"] = {
                "healthy": health_status.healthy,
                "status": health_status.status,
                "failing_streak": health_status.failing_streak,
                "log": health_status.log,
            }

            # 容器日志（最后 100 行）
            logs = container.logs(tail=100)
            diagnostic_info["logs"] = logs.decode("utf-8", errors="replace")

            # 网络信息
            networks = attrs.get("NetworkSettings", {}).get("Networks", {})
            diagnostic_info["network_info"] = {
                name: {
                    "ip_address": net.get("IPAddress"),
                    "gateway": net.get("Gateway"),
                    "mac_address": net.get("MacAddress"),
                }
                for name, net in networks.items()
            }

            # 资源使用情况
            try:
                stats = container.stats(stream=False)
                memory_usage = stats["memory_stats"]["usage"]
                memory_limit = stats["memory_stats"]["limit"]
                
                diagnostic_info["resource_usage"] = {
                    "memory_usage_mb": memory_usage / (1024 * 1024),
                    "memory_limit_mb": memory_limit / (1024 * 1024),
                    "memory_percent": (memory_usage / memory_limit) * 100,
                }
            except Exception as e:
                diagnostic_info["errors"].append(f"获取资源使用情况失败: {e}")

        except DockerException as e:
            diagnostic_info["errors"].append(f"收集诊断信息失败: {e}")
            logger.error(f"收集容器诊断信息失败: {e}")

        return diagnostic_info

    def detect_startup_timeout(
        self, container_id: str, expected_timeout: int = 60
    ) -> bool:
        """
        检测容器启动超时

        Args:
            container_id: 容器 ID
            expected_timeout: 预期超时时间（秒）

        Returns:
            bool: 是否超时
        """
        try:
            container = self.client.containers.get(container_id)
            attrs = container.attrs
            
            # 获取容器创建时间和启动时间
            created_at = attrs.get("Created", "")
            state = attrs.get("State", {})
            started_at = state.get("StartedAt", "")
            
            if not created_at or not started_at:
                return False
            
            from datetime import datetime
            created_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            started_time = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            
            startup_duration = (started_time - created_time).total_seconds()
            
            if startup_duration > expected_timeout:
                logger.warning(
                    f"容器启动超时: {container_id[:12]} "
                    f"(耗时 {startup_duration:.1f}秒, 预期 {expected_timeout}秒)"
                )
                return True
            
            return False
            
        except DockerException as e:
            logger.error(f"检测启动超时失败: {e}")
            return False

    def verify_container_running(self, container_id: str) -> bool:
        """
        验证容器是否正在运行

        Args:
            container_id: 容器 ID

        Returns:
            bool: 是否正在运行
        """
        try:
            container = self.client.containers.get(container_id)
            return container.status == "running"
        except DockerException as e:
            logger.error(f"验证容器运行状态失败: {e}")
            return False
