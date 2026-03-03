"""
Redis 客户端

封装 Redis 缓存操作，包括基本操作、健康检查和连接管理。
"""

import logging
from datetime import datetime
from typing import Optional

import redis

from ralph.models.database import ConnectionInfo, DatabaseError, RedisConfig

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis 客户端 - 封装缓存操作"""

    def __init__(self, config: RedisConfig):
        """
        初始化 Redis 客户端

        Args:
            config: Redis 配置
        """
        self.config = config
        self._client: Optional[redis.Redis] = None
        self._connection_time: Optional[datetime] = None
        logger.info(f"Redis 客户端初始化: {config.host}:{config.port}")

    def connect(self) -> None:
        """
        建立 Redis 连接

        Raises:
            ConnectionError: 连接失败时抛出
        """
        try:
            # 创建 Redis 连接池
            pool = redis.ConnectionPool(
                host=self.config.host,
                port=self.config.port,
                password=self.config.password,
                db=self.config.db,
                ssl=self.config.ssl,
                socket_connect_timeout=self.config.connection_timeout,
                socket_timeout=self.config.socket_timeout,
                max_connections=self.config.max_connections,
                decode_responses=True,  # 自动解码响应为字符串
            )

            # 创建 Redis 客户端
            self._client = redis.Redis(connection_pool=pool)
            self._connection_time = datetime.now()

            # 测试连接
            self._client.ping()

            # 获取服务器信息
            info = self._client.info("server")
            redis_version = info.get("redis_version", "unknown")

            logger.info(f"Redis 连接成功: version {redis_version}")

        except redis.ConnectionError as e:
            error = self._parse_connection_error(e)
            logger.error(f"Redis 连接失败: {error.message}")
            raise ConnectionError(error.message) from e

        except redis.AuthenticationError as e:
            error = DatabaseError(
                type="authentication_failed",
                message="Redis 认证失败：密码错误或未提供密码",
                details={"host": self.config.host},
            )
            logger.error(f"Redis 连接失败: {error.message}")
            raise ConnectionError(error.message) from e

        except Exception as e:
            logger.error(f"Redis 连接失败: {e}")
            raise ConnectionError(f"无法连接到 Redis: {e}") from e

    def get(self, key: str) -> Optional[str]:
        """
        获取键值

        Args:
            key: 键名

        Returns:
            键值，如果不存在返回 None

        Raises:
            RuntimeError: 未连接到 Redis 时抛出
        """
        if not self._client:
            raise RuntimeError("未连接到 Redis")

        try:
            value = self._client.get(key)
            logger.debug(f"GET {key}: {value}")
            return value
        except redis.TimeoutError as e:
            logger.error(f"GET 操作超时: {key}")
            raise TimeoutError(f"Redis GET 操作超时: {e}") from e
        except Exception as e:
            logger.error(f"GET 操作失败: {e}")
            raise

    def set(
        self, key: str, value: str, expire: Optional[int] = None
    ) -> bool:
        """
        设置键值

        Args:
            key: 键名
            value: 键值
            expire: 过期时间（秒），可选

        Returns:
            是否设置成功

        Raises:
            RuntimeError: 未连接到 Redis 时抛出
        """
        if not self._client:
            raise RuntimeError("未连接到 Redis")

        try:
            if expire:
                result = self._client.setex(key, expire, value)
            else:
                result = self._client.set(key, value)

            logger.debug(f"SET {key}: {value} (expire={expire})")
            return bool(result)

        except redis.TimeoutError as e:
            logger.error(f"SET 操作超时: {key}")
            raise TimeoutError(f"Redis SET 操作超时: {e}") from e
        except Exception as e:
            logger.error(f"SET 操作失败: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        删除键

        Args:
            key: 键名

        Returns:
            是否删除成功

        Raises:
            RuntimeError: 未连接到 Redis 时抛出
        """
        if not self._client:
            raise RuntimeError("未连接到 Redis")

        try:
            result = self._client.delete(key)
            logger.debug(f"DELETE {key}: {result}")
            return result > 0
        except redis.TimeoutError as e:
            logger.error(f"DELETE 操作超时: {key}")
            raise TimeoutError(f"Redis DELETE 操作超时: {e}") from e
        except Exception as e:
            logger.error(f"DELETE 操作失败: {e}")
            return False

    def expire(self, key: str, seconds: int) -> bool:
        """
        设置键的过期时间

        Args:
            key: 键名
            seconds: 过期时间（秒）

        Returns:
            是否设置成功

        Raises:
            RuntimeError: 未连接到 Redis 时抛出
        """
        if not self._client:
            raise RuntimeError("未连接到 Redis")

        try:
            result = self._client.expire(key, seconds)
            logger.debug(f"EXPIRE {key}: {seconds}s")
            return bool(result)
        except redis.TimeoutError as e:
            logger.error(f"EXPIRE 操作超时: {key}")
            raise TimeoutError(f"Redis EXPIRE 操作超时: {e}") from e
        except Exception as e:
            logger.error(f"EXPIRE 操作失败: {e}")
            return False

    def exists(self, key: str) -> bool:
        """
        检查键是否存在

        Args:
            key: 键名

        Returns:
            键是否存在

        Raises:
            RuntimeError: 未连接到 Redis 时抛出
        """
        if not self._client:
            raise RuntimeError("未连接到 Redis")

        try:
            result = self._client.exists(key)
            logger.debug(f"EXISTS {key}: {result}")
            return result > 0
        except redis.TimeoutError as e:
            logger.error(f"EXISTS 操作超时: {key}")
            raise TimeoutError(f"Redis EXISTS 操作超时: {e}") from e
        except Exception as e:
            logger.error(f"EXISTS 操作失败: {e}")
            return False

    def ping(self) -> bool:
        """
        健康检查

        Returns:
            Redis 是否可用

        Raises:
            RuntimeError: 未连接到 Redis 时抛出
        """
        if not self._client:
            raise RuntimeError("未连接到 Redis")

        try:
            result = self._client.ping()
            logger.debug(f"PING: {result}")
            return result
        except redis.TimeoutError as e:
            logger.error(f"PING 操作超时")
            return False
        except Exception as e:
            logger.error(f"PING 操作失败: {e}")
            return False

    def get_connection_info(self) -> ConnectionInfo:
        """
        获取连接信息

        Returns:
            连接信息
        """
        return ConnectionInfo(
            host=self.config.host,
            port=self.config.port,
            database=None,
            user=None,
            connected=self._client is not None,
            connection_time=self._connection_time,
        )

    def close(self) -> None:
        """关闭 Redis 连接"""
        if self._client:
            try:
                self._client.close()
                self._client = None
                logger.info("Redis 连接已关闭")
            except Exception as e:
                logger.error(f"关闭连接失败: {e}")

    def _parse_connection_error(self, error: Exception) -> DatabaseError:
        """
        解析连接错误

        Args:
            error: 异常对象

        Returns:
            数据库错误信息
        """
        error_msg = str(error).lower()

        if "connection refused" in error_msg:
            return DatabaseError(
                type="connection_refused",
                message=f"Redis 服务器拒绝连接：{self.config.host}:{self.config.port}",
                details={"host": self.config.host, "port": self.config.port},
            )
        elif "timeout" in error_msg:
            return DatabaseError(
                type="timeout",
                message=f"Redis 操作超时：{self.config.connection_timeout}秒",
                details={"timeout": self.config.connection_timeout},
            )
        else:
            return DatabaseError(
                type="unknown_error",
                message=str(error),
                details={},
            )

    def __enter__(self) -> "RedisClient":
        """上下文管理器入口"""
        self.connect()
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """上下文管理器出口"""
        self.close()
