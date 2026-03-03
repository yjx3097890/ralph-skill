"""
Docker 检测器单元测试
"""

import os
import tempfile
from pathlib import Path
import pytest

from ralph.support.docker_detector import DockerDetector
from ralph.models.docker import (
    DockerProjectInfo,
    ComposeConfig,
    Service,
    VolumeMount,
)


class TestDockerDetector:
    """Docker 检测器测试类"""

    def test_detect_no_docker_config(self, tmp_path: Path) -> None:
        """测试：项目中没有 Docker 配置"""
        detector = DockerDetector(str(tmp_path))
        config = detector.detect_docker_config()

        assert config.has_dockerfile is False
        assert config.has_compose is False
        assert config.dockerfile_path is None
        assert config.compose_path is None

    def test_detect_dockerfile_only(self, tmp_path: Path) -> None:
        """测试：只有 Dockerfile"""
        # 创建 Dockerfile
        dockerfile = tmp_path / "Dockerfile"
        dockerfile.write_text(
            """FROM python:3.9
EXPOSE 8000
VOLUME /data
ENV APP_ENV=production
"""
        )

        detector = DockerDetector(str(tmp_path))
        config = detector.detect_docker_config()

        assert config.has_dockerfile is True
        assert config.has_compose is False
        assert config.dockerfile_path == str(dockerfile)
        assert config.base_image == "python:3.9"
        assert 8000 in config.exposed_ports
        assert len(config.volumes) == 1
        assert config.volumes[0].container_path == "/data"
        assert config.environment.get("APP_ENV") == "production"

    def test_detect_compose_only(self, tmp_path: Path) -> None:
        """测试：只有 docker-compose.yml"""
        # 创建 docker-compose.yml
        compose_file = tmp_path / "docker-compose.yml"
        compose_file.write_text(
            """version: '3.8'
services:
  web:
    image: nginx:latest
    ports:
      - "80:80"
"""
        )

        detector = DockerDetector(str(tmp_path))
        config = detector.detect_docker_config()

        assert config.has_dockerfile is False
        assert config.has_compose is True
        assert config.compose_path == str(compose_file)

    def test_detect_both_dockerfile_and_compose(self, tmp_path: Path) -> None:
        """测试：同时存在 Dockerfile 和 docker-compose.yml"""
        # 创建 Dockerfile
        dockerfile = tmp_path / "Dockerfile"
        dockerfile.write_text("FROM node:16\nEXPOSE 3000\n")

        # 创建 docker-compose.yml
        compose_file = tmp_path / "docker-compose.yml"
        compose_file.write_text(
            """version: '3.8'
services:
  app:
    build: .
    ports:
      - "3000:3000"
"""
        )

        detector = DockerDetector(str(tmp_path))
        config = detector.detect_docker_config()

        assert config.has_dockerfile is True
        assert config.has_compose is True
        assert config.dockerfile_path == str(dockerfile)
        assert config.compose_path == str(compose_file)

    def test_parse_dockerfile_multiple_ports(self, tmp_path: Path) -> None:
        """测试：解析多个暴露端口"""
        dockerfile = tmp_path / "Dockerfile"
        dockerfile.write_text(
            """FROM nginx:latest
EXPOSE 80 443
EXPOSE 8080/tcp
"""
        )

        detector = DockerDetector(str(tmp_path))
        config = detector.detect_docker_config()

        assert 80 in config.exposed_ports
        assert 443 in config.exposed_ports
        assert 8080 in config.exposed_ports

    def test_parse_dockerfile_multiple_volumes(self, tmp_path: Path) -> None:
        """测试：解析多个数据卷"""
        dockerfile = tmp_path / "Dockerfile"
        dockerfile.write_text(
            """FROM postgres:13
VOLUME /var/lib/postgresql/data
VOLUME ["/var/log/postgresql"]
"""
        )

        detector = DockerDetector(str(tmp_path))
        config = detector.detect_docker_config()

        assert len(config.volumes) == 2
        volume_paths = [v.container_path for v in config.volumes]
        assert "/var/lib/postgresql/data" in volume_paths
        assert "/var/log/postgresql" in volume_paths

    def test_parse_dockerfile_environment_variables(self, tmp_path: Path) -> None:
        """测试：解析环境变量"""
        dockerfile = tmp_path / "Dockerfile"
        dockerfile.write_text(
            """FROM python:3.9
ENV DEBUG=false
ENV DATABASE_URL="postgresql://localhost/mydb"
ENV PORT 8000
"""
        )

        detector = DockerDetector(str(tmp_path))
        config = detector.detect_docker_config()

        assert config.environment["DEBUG"] == "false"
        assert config.environment["DATABASE_URL"] == "postgresql://localhost/mydb"
        assert config.environment["PORT"] == "8000"

    def test_parse_compose_file_basic(self, tmp_path: Path) -> None:
        """测试：解析基本的 docker-compose 文件"""
        compose_file = tmp_path / "docker-compose.yml"
        compose_file.write_text(
            """version: '3.8'
services:
  web:
    image: nginx:latest
    ports:
      - "80:80"
      - "443:443"
    environment:
      - NGINX_HOST=example.com
      - NGINX_PORT=80
"""
        )

        detector = DockerDetector(str(tmp_path))
        compose_config = detector.parse_compose_file(str(compose_file))

        assert compose_config.version == "3.8"
        assert "web" in compose_config.services
        
        web_service = compose_config.services["web"]
        assert web_service.image == "nginx:latest"
        assert len(web_service.ports) == 2
        assert web_service.environment["NGINX_HOST"] == "example.com"
        assert web_service.environment["NGINX_PORT"] == "80"

    def test_parse_compose_file_with_build(self, tmp_path: Path) -> None:
        """测试：解析包含构建配置的 compose 文件"""
        compose_file = tmp_path / "docker-compose.yml"
        compose_file.write_text(
            """version: '3.8'
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.dev
      args:
        - NODE_ENV=development
    ports:
      - "3000:3000"
"""
        )

        detector = DockerDetector(str(tmp_path))
        compose_config = detector.parse_compose_file(str(compose_file))

        app_service = compose_config.services["app"]
        assert app_service.build is not None
        assert app_service.build.context == "."
        assert app_service.build.dockerfile == "Dockerfile.dev"
        assert app_service.build.args["NODE_ENV"] == "development"

    def test_parse_compose_file_with_depends_on(self, tmp_path: Path) -> None:
        """测试：解析服务依赖关系"""
        compose_file = tmp_path / "docker-compose.yml"
        compose_file.write_text(
            """version: '3.8'
services:
  db:
    image: postgres:13
  web:
    image: nginx:latest
    depends_on:
      - db
"""
        )

        detector = DockerDetector(str(tmp_path))
        compose_config = detector.parse_compose_file(str(compose_file))

        web_service = compose_config.services["web"]
        assert "db" in web_service.depends_on

    def test_parse_compose_file_with_healthcheck(self, tmp_path: Path) -> None:
        """测试：解析健康检查配置"""
        compose_file = tmp_path / "docker-compose.yml"
        compose_file.write_text(
            """version: '3.8'
services:
  db:
    image: postgres:13
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
"""
        )

        detector = DockerDetector(str(tmp_path))
        compose_config = detector.parse_compose_file(str(compose_file))

        db_service = compose_config.services["db"]
        assert db_service.health_check is not None
        assert "pg_isready" in db_service.health_check.test
        assert db_service.health_check.interval == 10
        assert db_service.health_check.timeout == 5
        assert db_service.health_check.retries == 5
        assert db_service.health_check.start_period == 10

    def test_parse_compose_file_with_networks(self, tmp_path: Path) -> None:
        """测试：解析网络配置"""
        compose_file = tmp_path / "docker-compose.yml"
        compose_file.write_text(
            """version: '3.8'
services:
  web:
    image: nginx:latest
    networks:
      - frontend
networks:
  frontend:
    driver: bridge
"""
        )

        detector = DockerDetector(str(tmp_path))
        compose_config = detector.parse_compose_file(str(compose_file))

        assert "frontend" in compose_config.networks
        assert compose_config.networks["frontend"].driver == "bridge"
        
        web_service = compose_config.services["web"]
        assert "frontend" in web_service.networks

    def test_parse_compose_file_with_volumes(self, tmp_path: Path) -> None:
        """测试：解析数据卷配置"""
        compose_file = tmp_path / "docker-compose.yml"
        compose_file.write_text(
            """version: '3.8'
services:
  db:
    image: postgres:13
    volumes:
      - db_data:/var/lib/postgresql/data
volumes:
  db_data:
    driver: local
"""
        )

        detector = DockerDetector(str(tmp_path))
        compose_config = detector.parse_compose_file(str(compose_file))

        assert "db_data" in compose_config.volumes
        assert compose_config.volumes["db_data"].driver == "local"

    def test_validate_docker_config_no_files(self, tmp_path: Path) -> None:
        """测试：验证没有 Docker 文件的配置"""
        detector = DockerDetector(str(tmp_path))
        config = detector.detect_docker_config()
        errors = detector.validate_docker_config(config)

        assert len(errors) > 0
        assert any("未找到" in error for error in errors)

    def test_validate_docker_config_valid(self, tmp_path: Path) -> None:
        """测试：验证有效的 Docker 配置"""
        # 创建 Dockerfile
        dockerfile = tmp_path / "Dockerfile"
        dockerfile.write_text("FROM python:3.9\n")

        detector = DockerDetector(str(tmp_path))
        config = detector.detect_docker_config()
        errors = detector.validate_docker_config(config)

        assert len(errors) == 0

    def test_validate_compose_config_no_services(self, tmp_path: Path) -> None:
        """测试：验证没有服务的 compose 配置"""
        compose_file = tmp_path / "docker-compose.yml"
        compose_file.write_text(
            """version: '3.8'
services: {}
"""
        )

        detector = DockerDetector(str(tmp_path))
        compose_config = detector.parse_compose_file(str(compose_file))
        errors = detector.validate_compose_config(compose_config)

        assert len(errors) > 0
        assert any("未定义任何服务" in error for error in errors)

    def test_validate_compose_config_invalid_dependency(self, tmp_path: Path) -> None:
        """测试：验证无效的服务依赖"""
        compose_file = tmp_path / "docker-compose.yml"
        compose_file.write_text(
            """version: '3.8'
services:
  web:
    image: nginx:latest
    depends_on:
      - nonexistent_service
"""
        )

        detector = DockerDetector(str(tmp_path))
        compose_config = detector.parse_compose_file(str(compose_file))
        errors = detector.validate_compose_config(compose_config)

        assert len(errors) > 0
        assert any("不存在" in error for error in errors)

    def test_validate_compose_config_invalid_network(self, tmp_path: Path) -> None:
        """测试：验证无效的网络引用"""
        compose_file = tmp_path / "docker-compose.yml"
        compose_file.write_text(
            """version: '3.8'
services:
  web:
    image: nginx:latest
    networks:
      - nonexistent_network
"""
        )

        detector = DockerDetector(str(tmp_path))
        compose_config = detector.parse_compose_file(str(compose_file))
        errors = detector.validate_compose_config(compose_config)

        assert len(errors) > 0
        assert any("未定义" in error for error in errors)

    def test_parse_duration_seconds(self) -> None:
        """测试：解析秒数"""
        detector = DockerDetector(".")
        assert detector._parse_duration("30s") == 30
        assert detector._parse_duration("5s") == 5

    def test_parse_duration_minutes(self) -> None:
        """测试：解析分钟"""
        detector = DockerDetector(".")
        assert detector._parse_duration("2m") == 120
        assert detector._parse_duration("1m") == 60

    def test_parse_duration_hours(self) -> None:
        """测试：解析小时"""
        detector = DockerDetector(".")
        assert detector._parse_duration("1h") == 3600
        assert detector._parse_duration("2h") == 7200

    def test_parse_duration_no_unit(self) -> None:
        """测试：解析没有单位的时间（默认为秒）"""
        detector = DockerDetector(".")
        assert detector._parse_duration("30") == 30

    def test_find_dockerfile_variants(self, tmp_path: Path) -> None:
        """测试：查找不同命名的 Dockerfile"""
        # 测试 Dockerfile.dev
        dockerfile_dev = tmp_path / "Dockerfile.dev"
        dockerfile_dev.write_text("FROM python:3.9\n")

        detector = DockerDetector(str(tmp_path))
        found = detector._find_dockerfile()
        assert found is not None
        assert found.name == "Dockerfile.dev"

    def test_find_compose_file_variants(self, tmp_path: Path) -> None:
        """测试：查找不同命名的 compose 文件"""
        # 测试 compose.yml
        compose_file = tmp_path / "compose.yml"
        compose_file.write_text("version: '3.8'\nservices: {}\n")

        detector = DockerDetector(str(tmp_path))
        found = detector._find_compose_file()
        assert found is not None
        assert found.name == "compose.yml"

    def test_parse_compose_file_not_found(self, tmp_path: Path) -> None:
        """测试：解析不存在的 compose 文件"""
        detector = DockerDetector(str(tmp_path))
        
        with pytest.raises(FileNotFoundError):
            detector.parse_compose_file()

    def test_parse_compose_file_invalid_yaml(self, tmp_path: Path) -> None:
        """测试：解析无效的 YAML 文件"""
        compose_file = tmp_path / "docker-compose.yml"
        compose_file.write_text("invalid: yaml: content: [")

        detector = DockerDetector(str(tmp_path))
        
        with pytest.raises(ValueError):
            detector.parse_compose_file(str(compose_file))
