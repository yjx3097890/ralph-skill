"""
Docker Compose 编排器

管理多服务编排、依赖关系解析和启动顺序控制。
"""

import docker
from docker.errors import DockerException
from typing import Dict, List, Optional
import logging
import time

from ralph.models.docker import (
    ComposeConfig,
    Service,
    ServiceStatus,
    OrchestrateResult,
    ContainerConfig,
    HealthCheck,
    ResourceLimits,
)
from ralph.support.docker_container_manager import DockerContainerManager
from ralph.support.docker_health_checker import DockerHealthChecker

logger = logging.getLogger(__name__)


class ContainerOrchestrator:
    """容器编排器"""

    def __init__(
        self,
        docker_client: docker.DockerClient,
        container_manager: DockerContainerManager,
        health_checker: DockerHealthChecker,
    ):
        """
        初始化编排器

        Args:
            docker_client: Docker 客户端实例
            container_manager: 容器管理器
            health_checker: 健康检查器
        """
        self.client = docker_client
        self.container_manager = container_manager
        self.health_checker = health_checker
        self.service_containers: Dict[str, str] = {}  # service_name -> container_id

    def resolve_service_dependencies(self, services: Dict[str, Service]) -> List[Service]:
        """
        解析服务依赖关系并返回启动顺序

        Args:
            services: 服务配置字典

        Returns:
            List[Service]: 按依赖顺序排列的服务列表

        Raises:
            ValueError: 如果存在循环依赖
        """
        # 拓扑排序
        visited = set()
        temp_mark = set()
        result = []

        def visit(service_name: str):
            if service_name in temp_mark:
                raise ValueError(f"检测到循环依赖: {service_name}")
            
            if service_name in visited:
                return
            
            temp_mark.add(service_name)
            
            service = services.get(service_name)
            if service:
                for dep in service.depends_on:
                    if dep in services:
                        visit(dep)
            
            temp_mark.remove(service_name)
            visited.add(service_name)
            
            if service:
                result.append(service)

        for service_name in services.keys():
            if service_name not in visited:
                visit(service_name)

        return result

    def start_services(
        self,
        compose_config: ComposeConfig,
        parallel: bool = False,
        timeout: int = 300,
    ) -> OrchestrateResult:
        """
        启动服务

        Args:
            compose_config: Compose 配置
            parallel: 是否并行启动（忽略依赖关系）
            timeout: 总超时时间（秒）

        Returns:
            OrchestrateResult: 编排结果
        """
        start_time = time.time()
        services_started = []
        services_failed = []
        errors = []

        try:
            # 解析服务依赖顺序
            if parallel:
                ordered_services = list(compose_config.services.values())
            else:
                ordered_services = self.resolve_service_dependencies(compose_config.services)

            logger.info(f"启动顺序: {[s.name for s in ordered_services]}")

            # 创建网络
            self._ensure_networks(compose_config.networks)

            # 按顺序启动服务
            for service in ordered_services:
                if time.time() - start_time > timeout:
                    errors.append(f"启动超时: {timeout}秒")
                    break

                try:
                    container_id = self._start_service(service, compose_config)
                    self.service_containers[service.name] = container_id
                    services_started.append(service.name)
                    logger.info(f"服务启动成功: {service.name}")

                except Exception as e:
                    error_msg = f"服务启动失败 {service.name}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    services_failed.append(service.name)

            total_time = time.time() - start_time
            success = len(services_failed) == 0

            return OrchestrateResult(
                success=success,
                services_started=services_started,
                services_failed=services_failed,
                total_time=total_time,
                errors=errors,
            )

        except ValueError as e:
            # 循环依赖错误
            return OrchestrateResult(
                success=False,
                services_started=services_started,
                services_failed=services_failed,
                total_time=time.time() - start_time,
                errors=[str(e)],
            )

    def _start_service(self, service: Service, compose_config: ComposeConfig) -> str:
        """
        启动单个服务

        Args:
            service: 服务配置
            compose_config: Compose 配置

        Returns:
            str: 容器 ID
        """
        # 确定镜像
        image = service.image
        if not image and service.build:
            # 需要构建镜像
            image = f"{service.name}:latest"
            # 这里简化处理，实际应该调用 build_image
            logger.warning(f"服务 {service.name} 需要构建镜像，跳过构建步骤")

        if not image:
            raise ValueError(f"服务 {service.name} 没有指定镜像或构建配置")

        # 解析端口映射
        ports = {}
        for port_mapping in service.ports:
            if ":" in port_mapping:
                host_port, container_port = port_mapping.split(":")
                ports[int(host_port)] = int(container_port.split("/")[0])
            else:
                port = int(port_mapping.split("/")[0])
                ports[port] = port

        # 解析数据卷
        from ralph.models.docker import VolumeMount
        volumes = []
        for volume_str in service.volumes:
            if ":" in volume_str:
                parts = volume_str.split(":")
                host_path = parts[0]
                container_path = parts[1]
                mode = parts[2] if len(parts) > 2 else "rw"
                volumes.append(VolumeMount(host_path, container_path, mode))

        # 创建容器配置
        container_config = ContainerConfig(
            image=image,
            name=service.name,
            command=service.command,
            environment=service.environment,
            ports=ports,
            volumes=volumes,
            network=service.networks[0] if service.networks else None,
            health_check=service.health_check,
            restart_policy=service.restart,
        )

        # 创建并启动容器
        container = self.container_manager.create_container(container_config)
        self.container_manager.start_container(container.id)

        # 等待容器健康（如果配置了健康检查）
        if service.health_check:
            if not self.health_checker.wait_for_healthy(container.id, timeout=60):
                raise RuntimeError(f"服务 {service.name} 健康检查失败")

        return container.id

    def stop_services(self, service_names: Optional[List[str]] = None) -> bool:
        """
        停止服务

        Args:
            service_names: 要停止的服务名称列表，None 表示停止所有服务

        Returns:
            bool: 是否全部成功
        """
        if service_names is None:
            service_names = list(self.service_containers.keys())

        success = True
        for service_name in reversed(service_names):  # 反向停止
            container_id = self.service_containers.get(service_name)
            if container_id:
                if not self.container_manager.stop_container(container_id):
                    success = False
                    logger.error(f"停止服务失败: {service_name}")
                else:
                    logger.info(f"服务停止成功: {service_name}")

        return success

    def scale_service(self, service_name: str, replicas: int) -> bool:
        """
        扩缩容服务

        Args:
            service_name: 服务名称
            replicas: 副本数量

        Returns:
            bool: 是否成功
        """
        # 简化实现，实际需要更复杂的逻辑
        logger.warning(f"扩缩容功能尚未完全实现: {service_name} -> {replicas} 副本")
        return False

    def get_service_status(self, service_name: str) -> Optional[ServiceStatus]:
        """
        获取服务状态

        Args:
            service_name: 服务名称

        Returns:
            Optional[ServiceStatus]: 服务状态
        """
        container_id = self.service_containers.get(service_name)
        if not container_id:
            return ServiceStatus(
                name=service_name,
                status="stopped",
                health_status="unknown",
            )

        try:
            container_info = self.container_manager.inspect_container(container_id)
            if not container_info:
                return ServiceStatus(
                    name=service_name,
                    status="unknown",
                    container_id=container_id,
                    health_status="unknown",
                )

            # 获取健康状态
            health_status_obj = self.health_checker.check_container_health(container_id)

            return ServiceStatus(
                name=service_name,
                status=container_info.state.status,
                container_id=container_id,
                health_status=health_status_obj.status,
                replicas=1,
                error=container_info.state.error,
            )

        except Exception as e:
            logger.error(f"获取服务状态失败: {e}")
            return ServiceStatus(
                name=service_name,
                status="error",
                container_id=container_id,
                health_status="unknown",
                error=str(e),
            )

    def _ensure_networks(self, networks: Dict[str, any]):
        """
        确保网络存在

        Args:
            networks: 网络配置
        """
        for network_name, network_config in networks.items():
            try:
                # 检查网络是否存在
                self.client.networks.list(names=[network_name])
            except DockerException:
                # 创建网络
                try:
                    driver = network_config.driver if network_config else "bridge"
                    self.client.networks.create(network_name, driver=driver)
                    logger.info(f"网络创建成功: {network_name}")
                except DockerException as e:
                    logger.error(f"网络创建失败: {e}")

    def cleanup_services(self, remove_volumes: bool = False) -> bool:
        """
        清理所有服务容器

        Args:
            remove_volumes: 是否删除数据卷

        Returns:
            bool: 是否成功
        """
        success = True

        # 停止并删除所有容器
        for service_name, container_id in self.service_containers.items():
            try:
                self.container_manager.stop_container(container_id, timeout=5)
                self.container_manager.remove_container(container_id, force=True)
                logger.info(f"服务清理成功: {service_name}")
            except Exception as e:
                logger.error(f"服务清理失败 {service_name}: {e}")
                success = False

        self.service_containers.clear()
        return success
