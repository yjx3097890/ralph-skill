"""
数据库管理器测试

测试 DatabaseManager、PostgreSQLClient 和 RedisClient 的基本功能。
"""

import pytest

from ralph.managers import DatabaseManager, PostgreSQLClient, RedisClient
from ralph.models.database import (
    DatabaseConfig,
    PostgreSQLConfig,
    RedisConfig,
)


class TestDatabaseManager:
    """数据库管理器测试"""

    def test_database_manager_initialization(self) -> None:
        """测试数据库管理器初始化"""
        config = DatabaseConfig()
        manager = DatabaseManager(config)

        assert manager.config == config
        assert manager.get_postgresql_client() is None
        assert manager.get_redis_client() is None

    def test_database_manager_with_postgresql_config(self) -> None:
        """测试带 PostgreSQL 配置的数据库管理器"""
        pg_config = PostgreSQLConfig(
            host="localhost",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_password",
        )
        config = DatabaseConfig(postgresql=pg_config)
        manager = DatabaseManager(config)

        assert manager.config.postgresql == pg_config

    def test_database_manager_with_redis_config(self) -> None:
        """测试带 Redis 配置的数据库管理器"""
        redis_config = RedisConfig(
            host="localhost",
            port=6379,
            password="test_password",
        )
        config = DatabaseConfig(redis=redis_config)
        manager = DatabaseManager(config)

        assert manager.config.redis == redis_config

    def test_connect_postgresql_without_config(self) -> None:
        """测试没有配置时连接 PostgreSQL 应该失败"""
        config = DatabaseConfig()
        manager = DatabaseManager(config)

        with pytest.raises(ValueError, match="PostgreSQL 配置未提供"):
            manager.connect_postgresql()

    def test_connect_redis_without_config(self) -> None:
        """测试没有配置时连接 Redis 应该失败"""
        config = DatabaseConfig()
        manager = DatabaseManager(config)

        with pytest.raises(ValueError, match="Redis 配置未提供"):
            manager.connect_redis()


class TestPostgreSQLClient:
    """PostgreSQL 客户端测试"""

    def test_postgresql_client_initialization(self) -> None:
        """测试 PostgreSQL 客户端初始化"""
        config = PostgreSQLConfig(
            host="localhost",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_password",
        )
        client = PostgreSQLClient(config)

        assert client.config == config
        assert client._connection is None
        assert client._pool is None

    def test_postgresql_client_get_connection_info(self) -> None:
        """测试获取连接信息"""
        config = PostgreSQLConfig(
            host="localhost",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_password",
        )
        client = PostgreSQLClient(config)
        info = client.get_connection_info()

        assert info.host == "localhost"
        assert info.port == 5432
        assert info.database == "test_db"
        assert info.user == "test_user"
        assert info.connected is False

    def test_execute_query_without_connection(self) -> None:
        """测试未连接时执行查询应该失败"""
        config = PostgreSQLConfig(
            host="localhost",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_password",
        )
        client = PostgreSQLClient(config)

        with pytest.raises(RuntimeError, match="未连接到数据库"):
            client.execute_query("SELECT 1")


class TestRedisClient:
    """Redis 客户端测试"""

    def test_redis_client_initialization(self) -> None:
        """测试 Redis 客户端初始化"""
        config = RedisConfig(
            host="localhost",
            port=6379,
            password="test_password",
        )
        client = RedisClient(config)

        assert client.config == config
        assert client._client is None

    def test_redis_client_get_connection_info(self) -> None:
        """测试获取连接信息"""
        config = RedisConfig(
            host="localhost",
            port=6379,
            password="test_password",
        )
        client = RedisClient(config)
        info = client.get_connection_info()

        assert info.host == "localhost"
        assert info.port == 6379
        assert info.database is None
        assert info.connected is False

    def test_redis_operations_without_connection(self) -> None:
        """测试未连接时执行操作应该失败"""
        config = RedisConfig(
            host="localhost",
            port=6379,
        )
        client = RedisClient(config)

        with pytest.raises(RuntimeError, match="未连接到 Redis"):
            client.get("test_key")

        with pytest.raises(RuntimeError, match="未连接到 Redis"):
            client.set("test_key", "test_value")

        with pytest.raises(RuntimeError, match="未连接到 Redis"):
            client.delete("test_key")

        with pytest.raises(RuntimeError, match="未连接到 Redis"):
            client.ping()
