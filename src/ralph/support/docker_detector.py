"""
Docker 项目检测器

检测项目中的 Docker 配置文件（Dockerfile、docker-compose.yml）并解析配置信息。
"""

import os
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
import yaml

from ralph.models.docker import (
    DockerProjectInfo,
    ComposeConfig,
    Service,
    Network,
    Volume,
    BuildConfig,
    VolumeMount,
    HealthCheck,
)


class DockerDetector:
    """Docker 项目检测器"""

    def __init__(self, project_path: str):
        """
        初始化 Docker 检测器

        Args:
            project_path: 项目根目录路径
        """
        self.project_path = Path(project_path)

    def detect_docker_config(self) -> DockerProjectInfo:
        """
        检测 Docker 配置

        Returns:
            DockerProjectInfo: Docker 配置信息
        """
        has_dockerfile = self._has_dockerfile()
        has_compose = self._has_compose_file()

        dockerfile_path = self._find_dockerfile() if has_dockerfile else None
        compose_path = self._find_compose_file() if has_compose else None

        base_image = None
        exposed_ports: List[int] = []
        volumes: List[VolumeMount] = []
        environment: Dict[str, str] = {}

        if dockerfile_path:
            dockerfile_info = self._parse_dockerfile(dockerfile_path)
            base_image = dockerfile_info.get("base_image")
            exposed_ports = dockerfile_info.get("exposed_ports", [])
            volumes = dockerfile_info.get("volumes", [])
            environment = dockerfile_info.get("environment", {})

        return DockerProjectInfo(
            has_dockerfile=has_dockerfile,
            has_compose=has_compose,
            dockerfile_path=str(dockerfile_path) if dockerfile_path else None,
            compose_path=str(compose_path) if compose_path else None,
            base_image=base_image,
            exposed_ports=exposed_ports,
            volumes=volumes,
            environment=environment,
        )

    def _has_dockerfile(self) -> bool:
        """检查是否存在 Dockerfile"""
        return self._find_dockerfile() is not None

    def _has_compose_file(self) -> bool:
        """检查是否存在 docker-compose 文件"""
        return self._find_compose_file() is not None

    def _find_dockerfile(self) -> Optional[Path]:
        """
        查找 Dockerfile

        Returns:
            Optional[Path]: Dockerfile 路径，如果不存在则返回 None
        """
        # 常见的 Dockerfile 命名
        dockerfile_names = [
            "Dockerfile",
            "dockerfile",
            "Dockerfile.dev",
            "Dockerfile.prod",
        ]

        for name in dockerfile_names:
            dockerfile_path = self.project_path / name
            if dockerfile_path.exists() and dockerfile_path.is_file():
                return dockerfile_path

        return None

    def _find_compose_file(self) -> Optional[Path]:
        """
        查找 docker-compose 文件

        Returns:
            Optional[Path]: docker-compose 文件路径，如果不存在则返回 None
        """
        # 常见的 docker-compose 文件命名
        compose_names = [
            "docker-compose.yml",
            "docker-compose.yaml",
            "compose.yml",
            "compose.yaml",
            "docker-compose.dev.yml",
            "docker-compose.prod.yml",
        ]

        for name in compose_names:
            compose_path = self.project_path / name
            if compose_path.exists() and compose_path.is_file():
                return compose_path

        return None

    def _parse_dockerfile(self, dockerfile_path: Path) -> Dict[str, Any]:
        """
        解析 Dockerfile

        Args:
            dockerfile_path: Dockerfile 路径

        Returns:
            Dict[str, Any]: 解析结果
        """
        result: Dict[str, Any] = {
            "base_image": None,
            "exposed_ports": [],
            "volumes": [],
            "environment": {},
        }

        try:
            with open(dockerfile_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 解析 FROM 指令获取基础镜像
            from_match = re.search(r"^FROM\s+(\S+)", content, re.MULTILINE)
            if from_match:
                result["base_image"] = from_match.group(1)

            # 解析 EXPOSE 指令获取暴露端口
            expose_matches = re.finditer(r"^EXPOSE\s+(.+)$", content, re.MULTILINE)
            for match in expose_matches:
                ports_str = match.group(1).strip()
                # 处理多个端口，例如: EXPOSE 80 443
                for port_str in ports_str.split():
                    # 移除协议后缀，例如: 80/tcp -> 80
                    port = port_str.split("/")[0]
                    try:
                        result["exposed_ports"].append(int(port))
                    except ValueError:
                        pass

            # 解析 VOLUME 指令
            volume_matches = re.finditer(r"^VOLUME\s+(.+)$", content, re.MULTILINE)
            for match in volume_matches:
                volume_str = match.group(1).strip()
                # 处理 JSON 数组格式: VOLUME ["/data"]
                if volume_str.startswith("["):
                    try:
                        import json

                        volumes_list = json.loads(volume_str)
                        for vol in volumes_list:
                            result["volumes"].append(
                                VolumeMount(host_path="", container_path=vol, mode="rw")
                            )
                    except json.JSONDecodeError:
                        pass
                else:
                    # 处理空格分隔格式: VOLUME /data /logs
                    for vol in volume_str.split():
                        result["volumes"].append(
                            VolumeMount(host_path="", container_path=vol, mode="rw")
                        )

            # 解析 ENV 指令
            # 支持两种格式: ENV KEY=value 和 ENV KEY value
            env_matches = re.finditer(r"^ENV\s+(\S+?)(?:=|\s+)(.+)$", content, re.MULTILINE)
            for match in env_matches:
                key = match.group(1)
                value = match.group(2).strip()
                # 移除引号
                value = value.strip('"').strip("'")
                result["environment"][key] = value

        except Exception as e:
            # 解析失败时返回空结果
            pass

        return result

    def parse_compose_file(self, compose_path: Optional[str] = None) -> ComposeConfig:
        """
        解析 docker-compose 文件

        Args:
            compose_path: docker-compose 文件路径，如果为 None 则自动查找

        Returns:
            ComposeConfig: Compose 配置

        Raises:
            FileNotFoundError: 如果文件不存在
            ValueError: 如果文件格式无效
        """
        if compose_path is None:
            compose_file = self._find_compose_file()
            if compose_file is None:
                raise FileNotFoundError("未找到 docker-compose 文件")
            compose_path = str(compose_file)

        try:
            with open(compose_path, "r", encoding="utf-8") as f:
                compose_data = yaml.safe_load(f)

            if not isinstance(compose_data, dict):
                raise ValueError("docker-compose 文件格式无效")

            version = compose_data.get("version", "3")
            services = self._parse_services(compose_data.get("services", {}))
            networks = self._parse_networks(compose_data.get("networks", {}))
            volumes = self._parse_volumes(compose_data.get("volumes", {}))

            return ComposeConfig(
                version=version, services=services, networks=networks, volumes=volumes
            )

        except yaml.YAMLError as e:
            raise ValueError(f"解析 docker-compose 文件失败: {e}")

    def _parse_services(self, services_data: Dict[str, Any]) -> Dict[str, Service]:
        """解析服务配置"""
        services: Dict[str, Service] = {}

        for service_name, service_config in services_data.items():
            if not isinstance(service_config, dict):
                continue

            # 解析构建配置
            build_config = None
            if "build" in service_config:
                build_data = service_config["build"]
                if isinstance(build_data, str):
                    build_config = BuildConfig(context=build_data, dockerfile="Dockerfile")
                elif isinstance(build_data, dict):
                    # 解析 args
                    args_dict = {}
                    args_data = build_data.get("args", {})
                    if isinstance(args_data, dict):
                        args_dict = args_data
                    elif isinstance(args_data, list):
                        # 将列表格式转换为字典: ["KEY=value"] -> {"KEY": "value"}
                        for arg in args_data:
                            if "=" in str(arg):
                                key, value = str(arg).split("=", 1)
                                args_dict[key] = value
                    
                    build_config = BuildConfig(
                        context=build_data.get("context", "."),
                        dockerfile=build_data.get("dockerfile", "Dockerfile"),
                        args=args_dict,
                        target=build_data.get("target"),
                    )

            # 解析健康检查
            health_check = None
            if "healthcheck" in service_config:
                hc_data = service_config["healthcheck"]
                if isinstance(hc_data, dict):
                    test = hc_data.get("test", "")
                    if isinstance(test, list):
                        test = " ".join(test)
                    health_check = HealthCheck(
                        test=test,
                        interval=self._parse_duration(hc_data.get("interval", "30s")),
                        timeout=self._parse_duration(hc_data.get("timeout", "10s")),
                        retries=hc_data.get("retries", 3),
                        start_period=self._parse_duration(hc_data.get("start_period", "0s")),
                    )

            # 解析环境变量
            environment = {}
            if "environment" in service_config:
                env_data = service_config["environment"]
                if isinstance(env_data, dict):
                    environment = env_data
                elif isinstance(env_data, list):
                    for item in env_data:
                        if "=" in item:
                            key, value = item.split("=", 1)
                            environment[key] = value

            # 解析端口映射
            ports = []
            if "ports" in service_config:
                ports_data = service_config["ports"]
                if isinstance(ports_data, list):
                    ports = [str(p) for p in ports_data]

            # 解析数据卷
            volumes = []
            if "volumes" in service_config:
                volumes_data = service_config["volumes"]
                if isinstance(volumes_data, list):
                    volumes = [str(v) for v in volumes_data]

            # 解析依赖关系
            depends_on = []
            if "depends_on" in service_config:
                depends_data = service_config["depends_on"]
                if isinstance(depends_data, list):
                    depends_on = depends_data
                elif isinstance(depends_data, dict):
                    depends_on = list(depends_data.keys())

            # 解析网络
            networks_list = []
            if "networks" in service_config:
                networks_data = service_config["networks"]
                if isinstance(networks_data, list):
                    networks_list = networks_data
                elif isinstance(networks_data, dict):
                    networks_list = list(networks_data.keys())

            service = Service(
                name=service_name,
                image=service_config.get("image"),
                build=build_config,
                command=service_config.get("command"),
                environment=environment,
                ports=ports,
                volumes=volumes,
                depends_on=depends_on,
                networks=networks_list,
                health_check=health_check,
                restart=service_config.get("restart", "no"),
            )

            services[service_name] = service

        return services

    def _parse_networks(self, networks_data: Dict[str, Any]) -> Dict[str, Network]:
        """解析网络配置"""
        networks: Dict[str, Network] = {}

        for network_name, network_config in networks_data.items():
            if network_config is None:
                network_config = {}

            network = Network(
                name=network_name,
                driver=network_config.get("driver", "bridge"),
                external=network_config.get("external", False),
                options=network_config.get("driver_opts", {}),
            )

            networks[network_name] = network

        return networks

    def _parse_volumes(self, volumes_data: Dict[str, Any]) -> Dict[str, Volume]:
        """解析数据卷配置"""
        volumes: Dict[str, Volume] = {}

        for volume_name, volume_config in volumes_data.items():
            if volume_config is None:
                volume_config = {}

            volume = Volume(
                name=volume_name,
                driver=volume_config.get("driver", "local"),
                external=volume_config.get("external", False),
                options=volume_config.get("driver_opts", {}),
            )

            volumes[volume_name] = volume

        return volumes

    def _parse_duration(self, duration_str: str) -> int:
        """
        解析时间字符串为秒数

        Args:
            duration_str: 时间字符串，例如: "30s", "1m", "2h"

        Returns:
            int: 秒数
        """
        if not duration_str:
            return 0

        duration_str = duration_str.strip().lower()

        # 匹配数字和单位
        match = re.match(r"(\d+)([smh]?)", duration_str)
        if not match:
            return 0

        value = int(match.group(1))
        unit = match.group(2) or "s"

        if unit == "s":
            return value
        elif unit == "m":
            return value * 60
        elif unit == "h":
            return value * 3600

        return value

    def validate_docker_config(self, config: DockerProjectInfo) -> List[str]:
        """
        验证 Docker 配置

        Args:
            config: Docker 配置

        Returns:
            List[str]: 验证错误列表，如果为空则表示验证通过
        """
        errors: List[str] = []

        if not config.has_dockerfile and not config.has_compose:
            errors.append("项目中未找到 Dockerfile 或 docker-compose 文件")

        if config.has_dockerfile and config.dockerfile_path:
            if not Path(config.dockerfile_path).exists():
                errors.append(f"Dockerfile 不存在: {config.dockerfile_path}")

        if config.has_compose and config.compose_path:
            if not Path(config.compose_path).exists():
                errors.append(f"docker-compose 文件不存在: {config.compose_path}")

        return errors

    def validate_compose_config(self, config: ComposeConfig) -> List[str]:
        """
        验证 Compose 配置

        Args:
            config: Compose 配置

        Returns:
            List[str]: 验证错误列表，如果为空则表示验证通过
        """
        errors: List[str] = []

        if not config.services:
            errors.append("docker-compose 文件中未定义任何服务")

        # 验证服务依赖关系
        service_names = set(config.services.keys())
        for service_name, service in config.services.items():
            for dep in service.depends_on:
                if dep not in service_names:
                    errors.append(f"服务 '{service_name}' 依赖的服务 '{dep}' 不存在")

        # 验证网络引用
        network_names = set(config.networks.keys())
        for service_name, service in config.services.items():
            for network in service.networks:
                if network not in network_names and network != "default":
                    errors.append(f"服务 '{service_name}' 引用的网络 '{network}' 未定义")

        return errors
