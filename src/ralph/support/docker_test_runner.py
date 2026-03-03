"""
Docker 容器化测试执行器

在 Docker 容器中运行测试套件，收集结果和日志。
"""

import docker
from docker.errors import DockerException
from typing import List, Optional
import logging
import time

from ralph.models.docker import (
    ContainerConfig,
    ContainerTestResult,
    Artifact,
    ResourceUsage,
)
from ralph.support.docker_container_manager import DockerContainerManager

logger = logging.getLogger(__name__)


class DockerTestRunner:
    """Docker 测试运行器"""

    def __init__(
        self,
        docker_client: docker.DockerClient,
        container_manager: DockerContainerManager,
    ):
        """
        初始化测试运行器

        Args:
            docker_client: Docker 客户端实例
            container_manager: 容器管理器
        """
        self.client = docker_client
        self.container_manager = container_manager

    def run_tests_in_container(
        self,
        container_config: ContainerConfig,
        test_command: str,
        timeout: int = 300,
    ) -> ContainerTestResult:
        """
        在容器中运行测试

        Args:
            container_config: 容器配置
            test_command: 测试命令
            timeout: 超时时间（秒）

        Returns:
            ContainerTestResult: 测试结果
        """
        start_time = time.time()
        container_id = None

        try:
            # 创建容器
            container = self.container_manager.create_container(container_config)
            container_id = container.id

            # 启动容器
            if not self.container_manager.start_container(container_id):
                return ContainerTestResult(
                    success=False,
                    container_id=container_id,
                    exit_code=-1,
                    stdout="",
                    stderr="容器启动失败",
                    execution_time=time.time() - start_time,
                )

            # 执行测试命令
            exec_result = self.container_manager.execute_command(
                container_id, test_command
            )

            # 获取资源使用情况
            resource_usage = self.container_manager.get_container_stats(container_id)

            execution_time = time.time() - start_time

            return ContainerTestResult(
                success=exec_result.exit_code == 0,
                container_id=container_id,
                exit_code=exec_result.exit_code,
                stdout=exec_result.stdout,
                stderr=exec_result.stderr,
                execution_time=execution_time,
                resource_usage=resource_usage,
            )

        except DockerException as e:
            logger.error(f"容器化测试执行失败: {e}")
            return ContainerTestResult(
                success=False,
                container_id=container_id or "",
                exit_code=-1,
                stdout="",
                stderr=str(e),
                execution_time=time.time() - start_time,
            )

    def collect_test_artifacts(
        self, container_id: str, artifact_paths: List[str]
    ) -> List[Artifact]:
        """
        从容器中收集测试产物

        Args:
            container_id: 容器 ID
            artifact_paths: 产物路径列表

        Returns:
            List[Artifact]: 产物列表
        """
        artifacts = []

        try:
            container = self.client.containers.get(container_id)

            for artifact_path in artifact_paths:
                try:
                    # 从容器中获取文件
                    bits, stat = container.get_archive(artifact_path)
                    
                    # 确定产物类型
                    artifact_type = self._determine_artifact_type(artifact_path)
                    
                    # 保存产物（简化实现，实际应该保存到文件系统）
                    artifact = Artifact(
                        name=artifact_path.split("/")[-1],
                        path=artifact_path,
                        size_bytes=stat.get("size", 0),
                        artifact_type=artifact_type,
                    )
                    artifacts.append(artifact)
                    logger.info(f"收集产物成功: {artifact_path}")

                except Exception as e:
                    logger.warning(f"收集产物失败 {artifact_path}: {e}")

        except DockerException as e:
            logger.error(f"收集测试产物失败: {e}")

        return artifacts

    def _determine_artifact_type(self, path: str) -> str:
        """
        根据路径确定产物类型

        Args:
            path: 文件路径

        Returns:
            str: 产物类型
        """
        path_lower = path.lower()
        
        if path_lower.endswith((".log", ".txt")):
            return "log"
        elif path_lower.endswith((".html", ".xml", ".json")):
            return "report"
        elif path_lower.endswith((".png", ".jpg", ".jpeg")):
            return "screenshot"
        elif path_lower.endswith((".mp4", ".webm")):
            return "video"
        elif path_lower.endswith(".zip"):
            return "archive"
        else:
            return "unknown"

    def cleanup_test_containers(self, container_ids: List[str]) -> bool:
        """
        清理测试容器

        Args:
            container_ids: 容器 ID 列表

        Returns:
            bool: 是否全部成功
        """
        success = True

        for container_id in container_ids:
            try:
                # 停止容器
                self.container_manager.stop_container(container_id, timeout=5)
                
                # 删除容器
                if not self.container_manager.remove_container(container_id, force=True):
                    success = False
                    logger.error(f"删除测试容器失败: {container_id[:12]}")
                else:
                    logger.info(f"测试容器清理成功: {container_id[:12]}")

            except Exception as e:
                logger.error(f"清理测试容器失败 {container_id[:12]}: {e}")
                success = False

        return success

    def run_test_suite_with_cleanup(
        self,
        container_config: ContainerConfig,
        test_command: str,
        artifact_paths: Optional[List[str]] = None,
        timeout: int = 300,
    ) -> ContainerTestResult:
        """
        运行测试套件并自动清理

        Args:
            container_config: 容器配置
            test_command: 测试命令
            artifact_paths: 产物路径列表
            timeout: 超时时间（秒）

        Returns:
            ContainerTestResult: 测试结果
        """
        result = None
        container_id = None

        try:
            # 运行测试
            result = self.run_tests_in_container(
                container_config, test_command, timeout
            )
            container_id = result.container_id

            # 收集产物
            if artifact_paths and container_id:
                artifacts = self.collect_test_artifacts(container_id, artifact_paths)
                result.artifacts = artifacts

            return result

        finally:
            # 清理容器
            if container_id:
                self.cleanup_test_containers([container_id])
