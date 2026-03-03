"""
数据库管理器

管理数据库连接生命周期、连接池配置和健康检查。
"""

import logging
import time
from typing import Optional

from ralph.models.database import (
    ConnectionInfo,
    ConnectionStatus,
    DatabaseConfig,
    PostgreSQLConfig,
    RedisConfig,
)

logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理器 - 管理数据库连接生命周期"""

    def __init__(self, config: DatabaseConfig):
        """
        初始化数据库管理器

        Args:
            config: 数据库配置
        """
        self.config = config
        self._postgresql_client: Optional["PostgreSQLClient"] = None
        self._redis_client: Optional["RedisClient"] = None
        logger.info("数据库管理器初始化完成")

    def connect_postgresql(
        self, config: Optional[PostgreSQLConfig] = None
    ) -> "PostgreSQLClient":
        """
        连接 PostgreSQL 数据库

        Args:
            config: PostgreSQL 配置，如果为 None 则使用默认配置

        Returns:
            PostgreSQL 客户端实例

        Raises:
            ConnectionError: 连接失败时抛出
        """
        from ralph.managers.postgresql_client import PostgreSQLClient

        pg_config = config or self.config.postgresql
        if not pg_config:
            raise ValueError("PostgreSQL 配置未提供")

        logger.info(f"正在连接 PostgreSQL: {pg_config.host}:{pg_config.port}/{pg_config.database}")

        try:
            client = PostgreSQLClient(pg_config)
            client.connect()
            self._postgresql_client = client
            logger.info("PostgreSQL 连接成功")
            return client
        except Exception as e:
            logger.error(f"PostgreSQL 连接失败: {e}")
            raise ConnectionError(f"无法连接到 PostgreSQL: {e}") from e

    def connect_redis(self, config: Optional[RedisConfig] = None) -> "RedisClient":
        """
        连接 Redis 缓存

        Args:
            config: Redis 配置，如果为 None 则使用默认配置

        Returns:
            Redis 客户端实例

        Raises:
            ConnectionError: 连接失败时抛出
        """
        from ralph.managers.redis_client import RedisClient

        redis_config = config or self.config.redis
        if not redis_config:
            raise ValueError("Redis 配置未提供")

        logger.info(f"正在连接 Redis: {redis_config.host}:{redis_config.port}")

        try:
            client = RedisClient(redis_config)
            client.connect()
            self._redis_client = client
            logger.info("Redis 连接成功")
            return client
        except Exception as e:
            logger.error(f"Redis 连接失败: {e}")
            raise ConnectionError(f"无法连接到 Redis: {e}") from e

    def verify_connection(self, client: object) -> ConnectionStatus:
        """
        验证数据库连接状态

        Args:
            client: 数据库客户端（PostgreSQLClient 或 RedisClient）

        Returns:
            连接状态信息
        """
        from ralph.managers.postgresql_client import PostgreSQLClient
        from ralph.managers.redis_client import RedisClient

        start_time = time.time()

        try:
            if isinstance(client, PostgreSQLClient):
                # 验证 PostgreSQL 连接
                result = client.execute_query("SELECT 1")
                latency_ms = (time.time() - start_time) * 1000

                return ConnectionStatus(
                    connected=result.success,
                    host=client.config.host,
                    port=client.config.port,
                    database=client.config.database,
                    latency_ms=latency_ms,
                    error=result.error if not result.success else None,
                )

            elif isinstance(client, RedisClient):
                # 验证 Redis 连接
                success = client.ping()
                latency_ms = (time.time() - start_time) * 1000

                return ConnectionStatus(
                    connected=success,
                    host=client.config.host,
                    port=client.config.port,
                    database=None,
                    latency_ms=latency_ms,
                    error=None if success else "Ping 失败",
                )

            else:
                raise ValueError(f"不支持的客户端类型: {type(client)}")

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"连接验证失败: {e}")

            return ConnectionStatus(
                connected=False,
                host="unknown",
                port=0,
                database=None,
                latency_ms=latency_ms,
                error=str(e),
                error_details={"exception_type": type(e).__name__},
            )

    def get_postgresql_client(self) -> Optional["PostgreSQLClient"]:
        """获取 PostgreSQL 客户端实例"""
        return self._postgresql_client

    def get_redis_client(self) -> Optional["RedisClient"]:
        """获取 Redis 客户端实例"""
        return self._redis_client

    def close_all(self) -> None:
        """关闭所有数据库连接"""
        if self._postgresql_client:
            logger.info("关闭 PostgreSQL 连接")
            self._postgresql_client.close()
            self._postgresql_client = None

        if self._redis_client:
            logger.info("关闭 Redis 连接")
            self._redis_client.close()
            self._redis_client = None

        logger.info("所有数据库连接已关闭")
