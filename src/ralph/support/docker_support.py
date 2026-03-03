"""
Docker 支持模块 - 集成接口

提供统一的 Docker 管理接口，整合镜像管理、容器管理、健康检查、编排和测试执行。
"""

import docker
from docker.errors import DockerException
from typing import Optional, List, Dict
import logging

from ralph.models.docker import (
    DockerProjectInfo,
    ComposeConfig,
    ContainerConfig,
    BuildResult,
    ContainerTestResult,
    OrchestrateResult,
    ServiceStatus,
)
from ralph.support.docker_detector import DockerDetector
from ralph.support.docker_manager import DockerManager
from ralph.support.docker_container_manager import DockerContainerManager
from ralph.support.docker_health_checker import DockerHealthChecker
from ralph.support.docker_orchestrator import ContainerOrchestrator
from ralph.support.docker_test_runner import DockerTestRunner
from ralph.support.docker_error_parser import DockerErrorParser

logger = logging.getLogger(__name__)


class DockerSupport:
    """Docker 支持统一接口"""

    def __init__(self, project_path: str, base_url: Optional[str] = None):
        """
        初始化 Docker 支持

        Args:
            project_path: 项目根目录路径
            base_url: Docker daemon URL，默认使用环境变量
        """
        self.project_path = project_path
        
        # 初始化 Docker 客户端
        try:
            if base_url:
                self.docker_client = docker.DockerClient(base_url=base_url)
            else:
                self.docker_client = docker.from_env()
            
            self.docker_client.ping()
            logger.info("Docker 客户端初始化成功")
        except DockerException as e:
            logger.error(f"Docker 客户端初始化失败: {e}")
            raise

        # 初始化各个管理器
        self.detector = DockerDetector(project_path)
        self.manager = DockerManager(base_url)
        self.container_manager = DockerContainerManager(self.docker_client)
        self.health_checker = DockerHealthChecker(self.docker_client)
        self.orchestrator = ContainerOrchestrator(
            self.docker_client,
            self.container_manager,
            self.health_checker,
        )
        self.test_runner = DockerTestRunner(
            self.docker_client,
            self.container_manager,
        )
        self.error_parser = DockerErrorParser()

    def detect_docker_config(self) -> DockerProjectInfo:
        """
        检测项目的 Docker 配置

        Returns:
            DockerProjectInfo: Docker 配置信息
        """
        return self.detector.detect_docker_config()

    def parse_compose_file(self, compose_path: Optional[str] = None) -> ComposeConfig:
        """
        解析 docker-compose 文件

        Args:
            compose_path: compose 文件路径，None 则自动查找

        Returns:
            ComposeConfig: Compose 配置
        """
        return self.detector.parse_compose_file(compose_path)

    def build_image(
        self,
        dockerfile_path: str,
        tag: str,
        build_args: Optional[Dict[str, str]] = None,
        context_path: Optional[str] = None,
        no_cache: bool = False,
    ) -> BuildResult:
        """
        构建 Docker 镜像

        Args:
            dockerfile_path: Dockerfile 路径
            tag: 镜像标签
            build_args: 构建参数
            context_path: 构建上下文路径
            no_cache: 是否禁用缓存

        Returns:
            BuildResult: 构建结果
        """
        result = self.manager.build_image(
            dockerfile_path, tag, build_args, context_path, no_cache
        )
        
        # 如果构建失败，解析错误
        if not result.success and result.build_logs:
            errors = self.error_parser.parse_build_errors(result.build_logs)
            if errors:
                result.errors = errors
        
        return result

    def create_and_start_container(self, config: ContainerConfig) -> str:
        """
        创建并启动容器

        Args:
            config: 容器配置

        Returns:
            str: 容器 ID

        Raises:
            RuntimeError: 创建或启动失败
        """
        container = self.container_manager.create_container(config)
        
        if not self.container_manager.start_container(container.id):
            raise RuntimeError(f"容器启动失败: {container.id}")
        
        return container.id

    def run_tests_in_container(
        self,
        container_config: ContainerConfig,
        test_command: str,
        artifact_paths: Optional[List[str]] = None,
        timeout: int = 300,
    ) -> ContainerTestResult:
        """
        在容器中运行测试并自动清理

        Args:
            container_config: 容器配置
            test_command: 测试命令
            artifact_paths: 产物路径列表
            timeout: 超时时间（秒）

        Returns:
            ContainerTestResult: 测试结果
        """
        return self.test_runner.run_test_suite_with_cleanup(
            container_config, test_command, artifact_paths, timeout
        )

    def start_compose_services(
        self,
        compose_config: ComposeConfig,
        parallel: bool = False,
        timeout: int = 300,
    ) -> OrchestrateResult:
        """
        启动 Compose 服务

        Args:
            compose_config: Compose 配置
            parallel: 是否并行启动
            timeout: 超时时间（秒）

        Returns:
            OrchestrateResult: 编排结果
        """
        return self.orchestrator.start_services(compose_config, parallel, timeout)

    def stop_compose_services(self, service_names: Optional[List[str]] = None) -> bool:
        """
        停止 Compose 服务

        Args:
            service_names: 服务名称列表，None 表示停止所有

        Returns:
            bool: 是否成功
        """
        return self.orchestrator.stop_services(service_names)

    def get_service_status(self, service_name: str) -> Optional[ServiceStatus]:
        """
        获取服务状态

        Args:
            service_name: 服务名称

        Returns:
            Optional[ServiceStatus]: 服务状态
        """
        return self.orchestrator.get_service_status(service_name)

    def cleanup_all(self, remove_volumes: bool = False) -> bool:
        """
        清理所有 Docker 资源

        Args:
            remove_volumes: 是否删除数据卷

        Returns:
            bool: 是否成功
        """
        return self.orchestrator.cleanup_services(remove_volumes)

    def close(self):
        """关闭 Docker 客户端连接"""
        if self.manager:
            self.manager.close()
        if self.docker_client:
            self.docker_client.close()
        logger.info("Docker 支持已关闭")

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.close()
