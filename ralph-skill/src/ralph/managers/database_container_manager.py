"""
数据库容器管理器

管理 PostgreSQL 和 Redis 容器的启动、健康检查和初始化。
"""

import logging
import time
from pathlib import Path
from typing import List, Optional

from ralph.models.docker import (
    Container,
    ContainerConfig,
    HealthCheck,
    VolumeMount,
)
from ralph.support.docker_manager import DockerManager

logger = logging.getLogger(__name__)


class DatabaseContainerConfig:
    """数据库容器配置基类"""

    def __init__(
        self,
        container_name: str,
        version: str,
        host_port: int,
        data_dir: str,
    ):
        """
        初始化数据库容器配置

        Args:
            container_name: 容器名称
            version: 数据库版本
            host_port: 主机端口
            data_dir: 数据目录
        """
        self.container_name = container_name
        self.version = version
        self.host_port = host_port
        self.data_dir = data_dir


class PostgreSQLContainerConfig(DatabaseContainerConfig):
    """PostgreSQL 容器配置"""

    def __init__(
        self,
        container_name: str = "ralph_postgres",
        version: str = "14",
        host_port: int = 5432,
        data_dir: str = "./data/postgres",
        database: str = "ralph",
        user: str = "ralph",
        password: str = "ralph_password",
        init_scripts: Optional[List[str]] = None,
    ):
        """
        初始化 PostgreSQL 容器配置

        Args:
            container_name: 容器名称
            version: PostgreSQL 版本
            host_port: 主机端口
            data_dir: 数据目录
            database: 数据库名称
            user: 用户名
            password: 密码
            init_scripts: 初始化脚本路径列表
        """
        super().__init__(container_name, version, host_port, data_dir)
        self.database = database
        self.user = user
        self.password = password
        self.init_scripts = init_scripts or []


class RedisContainerConfig(DatabaseContainerConfig):
    """Redis 容器配置"""

    def __init__(
        self,
        container_name: str = "ralph_redis",
        version: str = "7",
        host_port: int = 6379,
        data_dir: str = "./data/redis",
        password: Optional[str] = None,
        persistence: str = "rdb",  # rdb, aof, both
        config_file: Optional[str] = None,
    ):
        """
        初始化 Redis 容器配置

        Args:
            container_name: 容器名称
            version: Redis 版本
            host_port: 主机端口
            data_dir: 数据目录
            password: 密码（可选）
            persistence: 持久化方式（rdb, aof, both）
            config_file: 配置文件路径（可选）
        """
        super().__init__(container_name, version, host_port, data_dir)
        self.password = password
        self.persistence = persistence
        self.config_file = config_file


class DatabaseContainerManager:
    """数据库容器管理器 - 管理数据库容器生命周期"""

    def __init__(self, docker_manager: DockerManager):
        """
        初始化数据库容器管理器

        Args:
            docker_manager: Docker 管理器实例
        """
        self.docker_manager = docker_manager
        logger.info("数据库容器管理器初始化完成")

    def start_postgresql_container(
        self, config: PostgreSQLContainerConfig
    ) -> Container:
        """
        启动 PostgreSQL 容器

        Args:
            config: PostgreSQL 容器配置

        Returns:
            容器对象

        Raises:
            RuntimeError: 启动失败时抛出
        """
        logger.info(f"正在启动 PostgreSQL 容器: {config.container_name}")

        # 确保数据目录存在
        data_path = Path(config.data_dir)
        data_path.mkdir(parents=True, exist_ok=True)

        # 构建容器配置
        container_config = ContainerConfig(
            image=f"postgres:{config.version}",
            name=config.container_name,
            environment={
                "POSTGRES_DB": config.database,
                "POSTGRES_USER": config.user,
                "POSTGRES_PASSWORD": config.password,
                "PGDATA": "/var/lib/postgresql/data/pgdata",
            },
            ports={config.host_port: 5432},
            volumes=[
                VolumeMount(
                    host_path=str(data_path.absolute()),
                    container_path="/var/lib/postgresql/data",
                    mode="rw",
                )
            ],
            health_check=HealthCheck(
                test=f"pg_isready -U {config.user} -d {config.database}",
                interval=5,
                timeout=3,
                retries=5,
                start_period=10,
            ),
        )

        try:
            # 创建并启动容器
            container = self.docker_manager.create_container(
                image=container_config.image, config=container_config
            )
            self.docker_manager.start_container(container.id)

            logger.info(f"PostgreSQL 容器已启动: {container.id}")

            # 等待容器健康
            if not self._wait_for_healthy(container.id, timeout=60):
                logs = self.docker_manager.get_container_logs(container.id, tail=50)
                raise RuntimeError(
                    f"PostgreSQL 容器启动失败，健康检查超时\n日志:\n{logs}"
                )

            logger.info(f"PostgreSQL 容器健康检查通过: {config.container_name}")

            # 执行初始化脚本
            if config.init_scripts:
                self._execute_init_scripts(container, config)

            return container

        except Exception as e:
            logger.error(f"启动 PostgreSQL 容器失败: {e}")
            # 尝试清理
            try:
                self.docker_manager.remove_container(config.container_name, force=True)
            except Exception:
                pass
            raise RuntimeError(f"启动 PostgreSQL 容器失败: {e}") from e

    def start_redis_container(self, config: RedisContainerConfig) -> Container:
        """
        启动 Redis 容器

        Args:
            config: Redis 容器配置

        Returns:
            容器对象

        Raises:
            RuntimeError: 启动失败时抛出
        """
        logger.info(f"正在启动 Redis 容器: {config.container_name}")

        # 确保数据目录存在
        data_path = Path(config.data_dir)
        data_path.mkdir(parents=True, exist_ok=True)

        # 构建 Redis 命令
        redis_command = self._build_redis_command(config)

        # 构建卷挂载
        volumes = [
            VolumeMount(
                host_path=str(data_path.absolute()),
                container_path="/data",
                mode="rw",
            )
        ]

        # 如果有配置文件，挂载配置文件
        if config.config_file:
            config_path = Path(config.config_file)
            if config_path.exists():
                volumes.append(
                    VolumeMount(
                        host_path=str(config_path.absolute()),
                        container_path="/usr/local/etc/redis/redis.conf",
                        mode="ro",
                    )
                )

        # 构建容器配置
        container_config = ContainerConfig(
            image=f"redis:{config.version}",
            name=config.container_name,
            command=redis_command,
            ports={config.host_port: 6379},
            volumes=volumes,
            health_check=HealthCheck(
                test="redis-cli ping",
                interval=5,
                timeout=3,
                retries=5,
                start_period=5,
            ),
        )

        try:
            # 创建并启动容器
            container = self.docker_manager.create_container(
                image=container_config.image, config=container_config
            )
            self.docker_manager.start_container(container.id)

            logger.info(f"Redis 容器已启动: {container.id}")

            # 等待容器健康
            if not self._wait_for_healthy(container.id, timeout=30):
                logs = self.docker_manager.get_container_logs(container.id, tail=50)
                raise RuntimeError(
                    f"Redis 容器启动失败，健康检查超时\n日志:\n{logs}"
                )

            logger.info(f"Redis 容器健康检查通过: {config.container_name}")

            return container

        except Exception as e:
            logger.error(f"启动 Redis 容器失败: {e}")
            # 尝试清理
            try:
                self.docker_manager.remove_container(config.container_name, force=True)
            except Exception:
                pass
            raise RuntimeError(f"启动 Redis 容器失败: {e}") from e

    def stop_database_container(self, container_id: str, timeout: int = 10) -> bool:
        """
        停止数据库容器

        Args:
            container_id: 容器 ID
            timeout: 超时时间（秒）

        Returns:
            是否成功停止
        """
        logger.info(f"正在停止数据库容器: {container_id}")
        return self.docker_manager.stop_container(container_id, timeout=timeout)

    def remove_database_container(
        self, container_id: str, force: bool = False
    ) -> bool:
        """
        删除数据库容器

        Args:
            container_id: 容器 ID
            force: 是否强制删除

        Returns:
            是否成功删除
        """
        logger.info(f"正在删除数据库容器: {container_id}")
        return self.docker_manager.remove_container(container_id, force=force)

    def _wait_for_healthy(self, container_id: str, timeout: int = 60) -> bool:
        """
        等待容器健康

        Args:
            container_id: 容器 ID
            timeout: 超时时间（秒）

        Returns:
            容器是否健康
        """
        logger.debug(f"等待容器健康: {container_id}")
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                container_info = self.docker_manager.inspect_container(container_id)

                # 检查容器状态
                if container_info.status == "exited":
                    logger.error("容器已退出")
                    return False

                # 检查健康状态
                health_status = container_info.health_status
                if health_status == "healthy":
                    logger.debug("容器健康检查通过")
                    return True
                elif health_status == "unhealthy":
                    logger.error("容器健康检查失败")
                    return False

                # 等待一段时间后重试
                time.sleep(2)

            except Exception as e:
                logger.warning(f"检查容器健康状态失败: {e}")
                time.sleep(2)

        logger.error(f"等待容器健康超时: {timeout}秒")
        return False

    def _build_redis_command(self, config: RedisContainerConfig) -> str:
        """
        构建 Redis 启动命令

        Args:
            config: Redis 容器配置

        Returns:
            Redis 启动命令
        """
        command_parts = ["redis-server"]

        # 如果有配置文件，使用配置文件
        if config.config_file:
            command_parts.append("/usr/local/etc/redis/redis.conf")
        else:
            # 否则使用命令行参数
            # 设置持久化
            if config.persistence in ["rdb", "both"]:
                command_parts.extend(["--save", "60", "1"])
            if config.persistence in ["aof", "both"]:
                command_parts.extend(["--appendonly", "yes"])

            # 设置密码
            if config.password:
                command_parts.extend(["--requirepass", config.password])

        return " ".join(command_parts)

    def _execute_init_scripts(
        self, container: Container, config: PostgreSQLContainerConfig
    ) -> None:
        """
        执行 PostgreSQL 初始化脚本

        Args:
            container: 容器对象
            config: PostgreSQL 容器配置

        Raises:
            RuntimeError: 执行失败时抛出
        """
        logger.info(f"正在执行初始化脚本（共 {len(config.init_scripts)} 个）")

        for script_path in config.init_scripts:
            script_file = Path(script_path)
            if not script_file.exists():
                logger.warning(f"初始化脚本不存在: {script_path}")
                continue

            logger.debug(f"执行初始化脚本: {script_path}")

            try:
                # 读取脚本内容
                with open(script_file, "r", encoding="utf-8") as f:
                    sql_content = f.read()

                # 将脚本复制到容器
                container_script_path = f"/tmp/init_{script_file.name}"
                # 注意：这里需要 docker_manager 支持文件复制功能
                # 暂时使用 execute_command 直接执行

                # 构建 psql 命令
                psql_command = (
                    f"psql -U {config.user} -d {config.database} "
                    f"-c \"{sql_content.replace(chr(34), chr(92) + chr(34))}\""
                )

                # 执行命令
                result = self.docker_manager.execute_command(
                    container.id, psql_command
                )

                if result.exit_code != 0:
                    raise RuntimeError(
                        f"初始化脚本执行失败: {script_path}\n"
                        f"错误输出: {result.stderr}"
                    )

                logger.debug(f"初始化脚本执行成功: {script_path}")

            except Exception as e:
                logger.error(f"执行初始化脚本失败: {script_path}, 错误: {e}")
                raise RuntimeError(f"执行初始化脚本失败: {e}") from e

        logger.info("所有初始化脚本执行完成")
