"""
Docker Manager 核心类

管理 Docker 操作，包括镜像构建、容器管理、网络配置等。
"""

import docker
from docker.errors import DockerException, ImageNotFound, APIError
from pathlib import Path
from typing import Optional, Dict, List, Any
import logging

from ralph.models.docker import (
    DockerProjectInfo,
    ContainerConfig,
    Container,
    ContainerInfo,
    BuildResult,
    BuildError,
    ExecResult,
    ResourceUsage,
    LayerInfo,
)

logger = logging.getLogger(__name__)


class DockerManager:
    """Docker Manager 核心类"""

    def __init__(self, base_url: Optional[str] = None):
        """
        初始化 Docker Manager

        Args:
            base_url: Docker daemon URL，默认使用环境变量或 unix socket
        """
        try:
            if base_url:
                self.client = docker.DockerClient(base_url=base_url)
            else:
                self.client = docker.from_env()
            
            # 测试连接
            self.client.ping()
            logger.info("Docker 连接成功")
        except DockerException as e:
            logger.error(f"Docker 连接失败: {e}")
            raise

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
            context_path: 构建上下文路径，默认为 Dockerfile 所在目录
            no_cache: 是否禁用缓存

        Returns:
            BuildResult: 构建结果
        """
        import time
        start_time = time.time()
        
        dockerfile_path_obj = Path(dockerfile_path)
        if not dockerfile_path_obj.exists():
            return BuildResult(
                success=False,
                image_id="",
                image_tag=tag,
                build_time=0.0,
                build_logs=f"Dockerfile 不存在: {dockerfile_path}",
                errors=[
                    BuildError(
                        step_number=0,
                        command="",
                        error_message=f"Dockerfile 不存在: {dockerfile_path}",
                        error_type="file_not_found",
                    )
                ],
            )

        # 确定构建上下文
        if context_path is None:
            context_path = str(dockerfile_path_obj.parent)

        build_logs = []
        errors: List[BuildError] = []

        try:
            # 构建镜像
            image, build_log = self.client.images.build(
                path=context_path,
                dockerfile=str(dockerfile_path_obj.name),
                tag=tag,
                buildargs=build_args or {},
                nocache=no_cache,
                rm=True,  # 删除中间容器
            )

            # 收集构建日志
            for log_entry in build_log:
                if "stream" in log_entry:
                    build_logs.append(log_entry["stream"])
                elif "error" in log_entry:
                    build_logs.append(f"ERROR: {log_entry['error']}")
                    errors.append(
                        BuildError(
                            step_number=0,
                            command="",
                            error_message=log_entry["error"],
                            error_type="build_error",
                        )
                    )

            build_time = time.time() - start_time
            build_logs_str = "".join(build_logs)

            # 获取镜像信息
            image_info = self.client.images.get(image.id)
            
            # 提取层信息
            layers = []
            if hasattr(image_info, 'history'):
                for idx, layer in enumerate(image_info.history()):
                    layers.append(
                        LayerInfo(
                            id=layer.get('Id', f'layer_{idx}'),
                            size_bytes=layer.get('Size', 0),
                            command=layer.get('CreatedBy', ''),
                            created=layer.get('Created', None),
                        )
                    )

            return BuildResult(
                success=len(errors) == 0,
                image_id=image.id,
                image_tag=tag,
                build_time=build_time,
                build_logs=build_logs_str,
                layers=layers,
                size_bytes=image_info.attrs.get('Size', 0),
                errors=errors,
            )

        except DockerException as e:
            build_time = time.time() - start_time
            error_message = str(e)
            
            return BuildResult(
                success=False,
                image_id="",
                image_tag=tag,
                build_time=build_time,
                build_logs="".join(build_logs) + f"\n\nERROR: {error_message}",
                errors=[
                    BuildError(
                        step_number=0,
                        command="",
                        error_message=error_message,
                        error_type="docker_error",
                    )
                ],
            )

    def tag_image(self, image_id: str, repository: str, tag: str) -> bool:
        """
        为镜像添加标签

        Args:
            image_id: 镜像 ID
            repository: 仓库名称
            tag: 标签

        Returns:
            bool: 是否成功
        """
        try:
            image = self.client.images.get(image_id)
            image.tag(repository, tag)
            logger.info(f"镜像标签添加成功: {repository}:{tag}")
            return True
        except DockerException as e:
            logger.error(f"镜像标签添加失败: {e}")
            return False

    def push_image(self, repository: str, tag: str) -> bool:
        """
        推送镜像到仓库

        Args:
            repository: 仓库名称
            tag: 标签

        Returns:
            bool: 是否成功
        """
        try:
            self.client.images.push(repository, tag)
            logger.info(f"镜像推送成功: {repository}:{tag}")
            return True
        except DockerException as e:
            logger.error(f"镜像推送失败: {e}")
            return False

    def pull_image(self, repository: str, tag: str = "latest") -> bool:
        """
        从仓库拉取镜像

        Args:
            repository: 仓库名称
            tag: 标签

        Returns:
            bool: 是否成功
        """
        try:
            self.client.images.pull(repository, tag)
            logger.info(f"镜像拉取成功: {repository}:{tag}")
            return True
        except DockerException as e:
            logger.error(f"镜像拉取失败: {e}")
            return False

    def remove_image(self, image_id: str, force: bool = False) -> bool:
        """
        删除镜像

        Args:
            image_id: 镜像 ID
            force: 是否强制删除

        Returns:
            bool: 是否成功
        """
        try:
            self.client.images.remove(image_id, force=force)
            logger.info(f"镜像删除成功: {image_id}")
            return True
        except DockerException as e:
            logger.error(f"镜像删除失败: {e}")
            return False

    def list_images(self) -> List[Dict[str, Any]]:
        """
        列出所有镜像

        Returns:
            List[Dict[str, Any]]: 镜像列表
        """
        try:
            images = self.client.images.list()
            return [
                {
                    "id": img.id,
                    "tags": img.tags,
                    "size": img.attrs.get("Size", 0),
                    "created": img.attrs.get("Created", ""),
                }
                for img in images
            ]
        except DockerException as e:
            logger.error(f"列出镜像失败: {e}")
            return []

    def close(self):
        """关闭 Docker 客户端连接"""
        if self.client:
            self.client.close()
            logger.info("Docker 连接已关闭")
