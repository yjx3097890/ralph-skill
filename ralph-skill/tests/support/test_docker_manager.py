"""
Docker Manager 单元测试
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from ralph.support.docker_manager import DockerManager
from ralph.models.docker import BuildResult


class TestDockerManager:
    """Docker Manager 测试类"""

    @pytest.fixture
    def mock_docker_client(self):
        """创建 mock Docker 客户端"""
        with patch("docker.from_env") as mock_from_env:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_from_env.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def docker_manager(self, mock_docker_client):
        """创建 Docker Manager 实例"""
        return DockerManager()

    def test_init_success(self, mock_docker_client):
        """测试初始化成功"""
        manager = DockerManager()
        assert manager.client is not None
        mock_docker_client.ping.assert_called_once()

    def test_init_with_base_url(self):
        """测试使用自定义 base_url 初始化"""
        with patch("docker.DockerClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_client_class.return_value = mock_client
            
            manager = DockerManager(base_url="tcp://localhost:2375")
            
            mock_client_class.assert_called_once_with(base_url="tcp://localhost:2375")
            assert manager.client is not None

    def test_build_image_dockerfile_not_found(self, docker_manager, tmp_path):
        """测试 Dockerfile 不存在的情况"""
        dockerfile_path = str(tmp_path / "Dockerfile")
        
        result = docker_manager.build_image(dockerfile_path, "test:latest")
        
        assert not result.success
        assert result.image_id == ""
        assert len(result.errors) > 0
        assert result.errors[0].error_type == "file_not_found"

    def test_build_image_success(self, docker_manager, tmp_path):
        """测试镜像构建成功"""
        # 创建临时 Dockerfile
        dockerfile_path = tmp_path / "Dockerfile"
        dockerfile_path.write_text("FROM alpine:latest\nRUN echo 'test'")
        
        # Mock 构建过程
        mock_image = MagicMock()
        mock_image.id = "sha256:abc123"
        mock_image.attrs = {"Size": 1024}
        mock_image.history.return_value = []
        
        docker_manager.client.images.build.return_value = (
            mock_image,
            [{"stream": "Step 1/2 : FROM alpine:latest\n"}],
        )
        docker_manager.client.images.get.return_value = mock_image
        
        result = docker_manager.build_image(str(dockerfile_path), "test:latest")
        
        assert result.success
        assert result.image_id == "sha256:abc123"
        assert result.image_tag == "test:latest"
        assert result.build_time > 0

    def test_tag_image_success(self, docker_manager):
        """测试镜像标签添加成功"""
        mock_image = MagicMock()
        docker_manager.client.images.get.return_value = mock_image
        
        result = docker_manager.tag_image("image123", "myrepo", "v1.0")
        
        assert result is True
        mock_image.tag.assert_called_once_with("myrepo", "v1.0")

    def test_push_image_success(self, docker_manager):
        """测试镜像推送成功"""
        docker_manager.client.images.push.return_value = None
        
        result = docker_manager.push_image("myrepo", "v1.0")
        
        assert result is True
        docker_manager.client.images.push.assert_called_once_with("myrepo", "v1.0")

    def test_pull_image_success(self, docker_manager):
        """测试镜像拉取成功"""
        docker_manager.client.images.pull.return_value = None
        
        result = docker_manager.pull_image("alpine", "latest")
        
        assert result is True
        docker_manager.client.images.pull.assert_called_once_with("alpine", "latest")

    def test_remove_image_success(self, docker_manager):
        """测试镜像删除成功"""
        docker_manager.client.images.remove.return_value = None
        
        result = docker_manager.remove_image("image123", force=True)
        
        assert result is True
        docker_manager.client.images.remove.assert_called_once_with("image123", force=True)

    def test_list_images(self, docker_manager):
        """测试列出镜像"""
        mock_image1 = MagicMock()
        mock_image1.id = "img1"
        mock_image1.tags = ["alpine:latest"]
        mock_image1.attrs = {"Size": 1024, "Created": "2024-01-01"}
        
        mock_image2 = MagicMock()
        mock_image2.id = "img2"
        mock_image2.tags = ["ubuntu:20.04"]
        mock_image2.attrs = {"Size": 2048, "Created": "2024-01-02"}
        
        docker_manager.client.images.list.return_value = [mock_image1, mock_image2]
        
        images = docker_manager.list_images()
        
        assert len(images) == 2
        assert images[0]["id"] == "img1"
        assert images[0]["tags"] == ["alpine:latest"]
        assert images[1]["id"] == "img2"

    def test_close(self, docker_manager):
        """测试关闭连接"""
        docker_manager.close()
        docker_manager.client.close.assert_called_once()
