"""
Docker 容器生命周期管理

管理容器的创建、启动、停止、删除等操作。
"""

import docker
from docker.errors import DockerException, NotFound, APIError
from datetime import datetime
from typing import Optional, Dict, List
import logging

from ralph.models.docker import (
    ContainerConfig,
    Container,
    ContainerInfo,
    ContainerState,
    ExecResult,
    ResourceUsage,
)

logger = logging.getLogger(__name__)


class DockerContainerManager:
    """Docker 容器管理器"""

    def __init__(self, docker_client: docker.DockerClient):
        """
        初始化容器管理器

        Args:
            docker_client: Docker 客户端实例
        """
        self.client = docker_client

    def create_container(self, config: ContainerConfig) -> Container:
        """
        创建容器

        Args:
            config: 容器配置

        Returns:
            Container: 容器实例

        Raises:
            DockerException: 创建失败时抛出
        """
        try:
            # 准备端口映射
            ports = {}
            if config.ports:
                for host_port, container_port in config.ports.items():
                    ports[f"{container_port}/tcp"] = host_port

            # 准备数据卷挂载
            volumes = {}
            binds = []
            if config.volumes:
                for vol in config.volumes:
                    volumes[vol.container_path] = {}
                    binds.append(f"{vol.host_path}:{vol.container_path}:{vol.mode}")

            # 准备资源限制
            host_config_params = {}
            if config.resource_limits:
                if config.resource_limits.cpu_limit:
                    # Docker API 使用纳秒，1 核心 = 1e9 纳秒
                    host_config_params["nano_cpus"] = int(
                        config.resource_limits.cpu_limit * 1e9
                    )
                if config.resource_limits.memory_limit:
                    host_config_params["mem_limit"] = config.resource_limits.memory_limit
                if config.resource_limits.memory_reservation:
                    host_config_params["mem_reservation"] = (
                        config.resource_limits.memory_reservation
                    )
                if config.resource_limits.pids_limit:
                    host_config_params["pids_limit"] = config.resource_limits.pids_limit

            # 准备健康检查
            healthcheck = None
            if config.health_check:
                healthcheck = {
                    "test": ["CMD-SHELL", config.health_check.test],
                    "interval": config.health_check.interval * 1_000_000_000,  # 转换为纳秒
                    "timeout": config.health_check.timeout * 1_000_000_000,
                    "retries": config.health_check.retries,
                    "start_period": config.health_check.start_period * 1_000_000_000,
                }

            # 创建容器
            container = self.client.containers.create(
                image=config.image,
                name=config.name,
                command=config.command,
                environment=config.environment,
                ports=ports,
                volumes=volumes,
                network=config.network,
                restart_policy={"Name": config.restart_policy},
                healthcheck=healthcheck,
                **host_config_params,
            )

            logger.info(f"容器创建成功: {container.id[:12]} ({config.name})")

            return Container(
                id=container.id,
                name=config.name,
                image=config.image,
                status="created",
                created_at=datetime.now(),
                ports=config.ports,
            )

        except DockerException as e:
            logger.error(f"容器创建失败: {e}")
            raise

    def start_container(self, container_id: str) -> bool:
        """
        启动容器

        Args:
            container_id: 容器 ID

        Returns:
            bool: 是否成功
        """
        try:
            container = self.client.containers.get(container_id)
            container.start()
            logger.info(f"容器启动成功: {container_id[:12]}")
            return True
        except DockerException as e:
            logger.error(f"容器启动失败: {e}")
            return False

    def stop_container(self, container_id: str, timeout: int = 10) -> bool:
        """
        停止容器

        Args:
            container_id: 容器 ID
            timeout: 超时时间（秒）

        Returns:
            bool: 是否成功
        """
        try:
            container = self.client.containers.get(container_id)
            container.stop(timeout=timeout)
            logger.info(f"容器停止成功: {container_id[:12]}")
            return True
        except DockerException as e:
            logger.error(f"容器停止失败: {e}")
            return False

    def restart_container(self, container_id: str, timeout: int = 10) -> bool:
        """
        重启容器

        Args:
            container_id: 容器 ID
            timeout: 超时时间（秒）

        Returns:
            bool: 是否成功
        """
        try:
            container = self.client.containers.get(container_id)
            container.restart(timeout=timeout)
            logger.info(f"容器重启成功: {container_id[:12]}")
            return True
        except DockerException as e:
            logger.error(f"容器重启失败: {e}")
            return False

    def remove_container(self, container_id: str, force: bool = False) -> bool:
        """
        删除容器

        Args:
            container_id: 容器 ID
            force: 是否强制删除（即使容器正在运行）

        Returns:
            bool: 是否成功
        """
        try:
            container = self.client.containers.get(container_id)
            container.remove(force=force)
            logger.info(f"容器删除成功: {container_id[:12]}")
            return True
        except DockerException as e:
            logger.error(f"容器删除失败: {e}")
            return False

    def get_container_logs(
        self, container_id: str, tail: int = 100, timestamps: bool = False
    ) -> str:
        """
        获取容器日志

        Args:
            container_id: 容器 ID
            tail: 返回最后 N 行日志
            timestamps: 是否包含时间戳

        Returns:
            str: 容器日志
        """
        try:
            container = self.client.containers.get(container_id)
            logs = container.logs(tail=tail, timestamps=timestamps)
            return logs.decode("utf-8", errors="replace")
        except DockerException as e:
            logger.error(f"获取容器日志失败: {e}")
            return f"ERROR: {e}"

    def inspect_container(self, container_id: str) -> Optional[ContainerInfo]:
        """
        检查容器详细信息

        Args:
            container_id: 容器 ID

        Returns:
            Optional[ContainerInfo]: 容器信息，失败时返回 None
        """
        try:
            container = self.client.containers.get(container_id)
            attrs = container.attrs

            # 解析容器状态
            state_data = attrs.get("State", {})
            state = ContainerState(
                status=state_data.get("Status", "unknown"),
                running=state_data.get("Running", False),
                paused=state_data.get("Paused", False),
                restarting=state_data.get("Restarting", False),
                oom_killed=state_data.get("OOMKilled", False),
                dead=state_data.get("Dead", False),
                pid=state_data.get("Pid", 0),
                exit_code=state_data.get("ExitCode", 0),
                error=state_data.get("Error", ""),
                started_at=state_data.get("StartedAt"),
                finished_at=state_data.get("FinishedAt"),
            )

            # 解析容器配置
            config_data = attrs.get("Config", {})
            
            # 创建 Container 对象
            container_obj = Container(
                id=container.id,
                name=attrs.get("Name", "").lstrip("/"),
                image=config_data.get("Image", ""),
                status=state.status,
                created_at=datetime.fromisoformat(
                    attrs.get("Created", "").replace("Z", "+00:00")
                ),
            )

            # 创建 ContainerConfig（简化版）
            from ralph.models.docker import ContainerConfig
            container_config = ContainerConfig(
                image=config_data.get("Image", ""),
                name=container_obj.name,
                command=config_data.get("Cmd"),
                environment={},  # 简化处理
            )

            return ContainerInfo(
                container=container_obj,
                config=container_config,
                state=state,
                network_settings=attrs.get("NetworkSettings", {}),
                mounts=attrs.get("Mounts", []),
            )

        except DockerException as e:
            logger.error(f"检查容器信息失败: {e}")
            return None

    def execute_command(
        self, container_id: str, command: str, workdir: Optional[str] = None
    ) -> ExecResult:
        """
        在容器中执行命令

        Args:
            container_id: 容器 ID
            command: 要执行的命令
            workdir: 工作目录

        Returns:
            ExecResult: 执行结果
        """
        import time
        start_time = time.time()

        try:
            container = self.client.containers.get(container_id)
            
            # 执行命令
            exec_result = container.exec_run(
                cmd=command, workdir=workdir, demux=True
            )

            execution_time = time.time() - start_time

            # 解析输出
            stdout = ""
            stderr = ""
            if exec_result.output:
                if isinstance(exec_result.output, tuple):
                    stdout_bytes, stderr_bytes = exec_result.output
                    if stdout_bytes:
                        stdout = stdout_bytes.decode("utf-8", errors="replace")
                    if stderr_bytes:
                        stderr = stderr_bytes.decode("utf-8", errors="replace")
                else:
                    stdout = exec_result.output.decode("utf-8", errors="replace")

            return ExecResult(
                exit_code=exec_result.exit_code,
                stdout=stdout,
                stderr=stderr,
                execution_time=execution_time,
            )

        except DockerException as e:
            execution_time = time.time() - start_time
            logger.error(f"容器命令执行失败: {e}")
            return ExecResult(
                exit_code=-1,
                stdout="",
                stderr=str(e),
                execution_time=execution_time,
            )

    def get_container_stats(self, container_id: str) -> Optional[ResourceUsage]:
        """
        获取容器资源使用统计

        Args:
            container_id: 容器 ID

        Returns:
            Optional[ResourceUsage]: 资源使用情况，失败时返回 None
        """
        try:
            container = self.client.containers.get(container_id)
            stats = container.stats(stream=False)

            # 计算 CPU 使用率
            cpu_delta = (
                stats["cpu_stats"]["cpu_usage"]["total_usage"]
                - stats["precpu_stats"]["cpu_usage"]["total_usage"]
            )
            system_delta = (
                stats["cpu_stats"]["system_cpu_usage"]
                - stats["precpu_stats"]["system_cpu_usage"]
            )
            cpu_count = stats["cpu_stats"]["online_cpus"]
            cpu_percent = 0.0
            if system_delta > 0 and cpu_delta > 0:
                cpu_percent = (cpu_delta / system_delta) * cpu_count * 100.0

            # 内存使用
            memory_usage = stats["memory_stats"]["usage"]
            memory_limit = stats["memory_stats"]["limit"]

            # 网络 I/O
            network_rx = 0
            network_tx = 0
            if "networks" in stats:
                for net_stats in stats["networks"].values():
                    network_rx += net_stats.get("rx_bytes", 0)
                    network_tx += net_stats.get("tx_bytes", 0)

            # 磁盘 I/O
            block_read = 0
            block_write = 0
            if "blkio_stats" in stats and "io_service_bytes_recursive" in stats["blkio_stats"]:
                for io_stat in stats["blkio_stats"]["io_service_bytes_recursive"]:
                    if io_stat["op"] == "Read":
                        block_read += io_stat["value"]
                    elif io_stat["op"] == "Write":
                        block_write += io_stat["value"]

            return ResourceUsage(
                cpu_percent=cpu_percent,
                memory_usage_mb=memory_usage / (1024 * 1024),
                memory_limit_mb=memory_limit / (1024 * 1024),
                network_rx_bytes=network_rx,
                network_tx_bytes=network_tx,
                block_io_read_bytes=block_read,
                block_io_write_bytes=block_write,
            )

        except DockerException as e:
            logger.error(f"获取容器统计信息失败: {e}")
            return None

    def list_containers(self, all: bool = False) -> List[Container]:
        """
        列出容器

        Args:
            all: 是否包含已停止的容器

        Returns:
            List[Container]: 容器列表
        """
        try:
            containers = self.client.containers.list(all=all)
            result = []
            
            for container in containers:
                result.append(
                    Container(
                        id=container.id,
                        name=container.name,
                        image=container.image.tags[0] if container.image.tags else container.image.id,
                        status=container.status,
                        created_at=datetime.fromisoformat(
                            container.attrs.get("Created", "").replace("Z", "+00:00")
                        ),
                    )
                )
            
            return result

        except DockerException as e:
            logger.error(f"列出容器失败: {e}")
            return []
