"""
测试数据库管理器

管理测试数据库的生命周期，包括创建、初始化、事务管理和清理。
"""

import logging
import uuid
from datetime import datetime
from typing import Optional

from ralph.managers.database_manager import DatabaseManager
from ralph.managers.postgresql_client import PostgreSQLClient, Transaction
from ralph.models.database import PostgreSQLConfig, TestDatabase

logger = logging.getLogger(__name__)


class TestDatabaseManager:
    """测试数据库管理器 - 管理测试数据库生命周期"""

    def __init__(self, base_config: PostgreSQLConfig):
        """
        初始化测试数据库管理器

        Args:
            base_config: 基础 PostgreSQL 配置
        """
        self.base_config = base_config
        self.database_manager = DatabaseManager(
            config=type("Config", (), {"postgresql": base_config, "redis": None})()
        )
        self._active_test_databases: dict[str, TestDatabase] = {}
        logger.info("测试数据库管理器初始化完成")

    def create_test_database(
        self, template_db: Optional[str] = None
    ) -> TestDatabase:
        """
        创建测试数据库

        Args:
            template_db: 模板数据库名称（可选）

        Returns:
            测试数据库对象

        Raises:
            RuntimeError: 创建失败时抛出
        """
        # 生成唯一的测试数据库名称
        test_db_name = f"test_{self.base_config.database}_{uuid.uuid4().hex[:8]}"
        logger.info(f"正在创建测试数据库: {test_db_name}")

        try:
            # 连接到默认数据库（postgres）创建测试数据库
            admin_config = self._create_admin_config()
            admin_client = self.database_manager.connect_postgresql(admin_config)

            # 创建测试数据库
            if template_db:
                create_sql = f'CREATE DATABASE "{test_db_name}" TEMPLATE "{template_db}"'
            else:
                create_sql = f'CREATE DATABASE "{test_db_name}"'

            result = admin_client.execute_query(create_sql)

            if not result.success:
                raise RuntimeError(f"创建测试数据库失败: {result.error}")

            logger.info(f"测试数据库创建成功: {test_db_name}")

            # 关闭管理员连接
            admin_client.close()

            # 创建测试数据库配置
            test_config = self._create_test_config(test_db_name)

            # 连接到测试数据库
            test_client = self.database_manager.connect_postgresql(test_config)

            # 开始事务
            transaction = test_client.begin_transaction()

            # 构建连接字符串
            connection_string = self._build_connection_string(test_config)

            # 创建测试数据库对象
            test_db = TestDatabase(
                name=test_db_name,
                connection_string=connection_string,
                created_at=datetime.now(),
                transaction=transaction,
            )

            # 记录活跃的测试数据库
            self._active_test_databases[test_db_name] = test_db

            logger.info(f"测试数据库初始化完成: {test_db_name}")
            return test_db

        except Exception as e:
            logger.error(f"创建测试数据库失败: {e}")
            # 尝试清理
            try:
                self._force_drop_database(test_db_name)
            except Exception:
                pass
            raise RuntimeError(f"创建测试数据库失败: {e}") from e

    def cleanup_test_database(self, test_db: TestDatabase) -> None:
        """
        清理测试数据库

        Args:
            test_db: 测试数据库对象
        """
        logger.info(f"正在清理测试数据库: {test_db.name}")

        try:
            # 回滚事务
            if test_db.transaction:
                logger.debug("回滚测试事务")
                test_db.transaction.rollback()

            # 获取 PostgreSQL 客户端
            pg_client = self.database_manager.get_postgresql_client()
            if pg_client:
                logger.debug("关闭测试数据库连接")
                pg_client.close()

            # 终止所有连接到测试数据库的会话
            self._terminate_database_connections(test_db.name)

            # 删除测试数据库
            self._drop_database(test_db.name)

            # 从活跃列表中移除
            if test_db.name in self._active_test_databases:
                del self._active_test_databases[test_db.name]

            logger.info(f"测试数据库清理完成: {test_db.name}")

        except Exception as e:
            logger.error(f"清理测试数据库失败: {e}")
            # 尝试强制删除
            try:
                self._force_drop_database(test_db.name)
            except Exception as force_error:
                logger.error(f"强制删除测试数据库失败: {force_error}")

    def create_test_database_template(
        self, template_name: str, init_sql: Optional[str] = None
    ) -> None:
        """
        创建测试数据库模板

        Args:
            template_name: 模板名称
            init_sql: 初始化 SQL 脚本（可选）

        Raises:
            RuntimeError: 创建失败时抛出
        """
        logger.info(f"正在创建测试数据库模板: {template_name}")

        try:
            # 连接到默认数据库
            admin_config = self._create_admin_config()
            admin_client = self.database_manager.connect_postgresql(admin_config)

            # 创建模板数据库
            create_sql = f'CREATE DATABASE "{template_name}" IS_TEMPLATE = TRUE'
            result = admin_client.execute_query(create_sql)

            if not result.success:
                raise RuntimeError(f"创建模板数据库失败: {result.error}")

            # 如果提供了初始化 SQL，执行它
            if init_sql:
                # 连接到模板数据库
                template_config = self._create_test_config(template_name)
                template_client = self.database_manager.connect_postgresql(
                    template_config
                )

                # 执行初始化 SQL
                result = template_client.execute_query(init_sql)
                if not result.success:
                    logger.error(f"初始化模板数据库失败: {result.error}")

                template_client.close()

            admin_client.close()
            logger.info(f"测试数据库模板创建成功: {template_name}")

        except Exception as e:
            logger.error(f"创建测试数据库模板失败: {e}")
            raise RuntimeError(f"创建测试数据库模板失败: {e}") from e

    def cleanup_all_test_databases(self) -> None:
        """清理所有活跃的测试数据库"""
        logger.info(f"正在清理所有测试数据库（共 {len(self._active_test_databases)} 个）")

        for test_db in list(self._active_test_databases.values()):
            try:
                self.cleanup_test_database(test_db)
            except Exception as e:
                logger.error(f"清理测试数据库失败: {test_db.name}, 错误: {e}")

        logger.info("所有测试数据库清理完成")

    def _create_admin_config(self) -> PostgreSQLConfig:
        """
        创建管理员配置（连接到 postgres 数据库）

        Returns:
            管理员配置
        """
        admin_config = PostgreSQLConfig(
            host=self.base_config.host,
            port=self.base_config.port,
            database="postgres",  # 连接到默认数据库
            user=self.base_config.user,
            password=self.base_config.password,
            ssl_mode=self.base_config.ssl_mode,
            connection_timeout=self.base_config.connection_timeout,
            pool_size=1,  # 管理操作只需要一个连接
            max_overflow=0,
        )
        return admin_config

    def _create_test_config(self, test_db_name: str) -> PostgreSQLConfig:
        """
        创建测试数据库配置

        Args:
            test_db_name: 测试数据库名称

        Returns:
            测试数据库配置
        """
        test_config = PostgreSQLConfig(
            host=self.base_config.host,
            port=self.base_config.port,
            database=test_db_name,
            user=self.base_config.user,
            password=self.base_config.password,
            ssl_mode=self.base_config.ssl_mode,
            connection_timeout=self.base_config.connection_timeout,
            pool_size=self.base_config.pool_size,
            max_overflow=self.base_config.max_overflow,
        )
        return test_config

    def _build_connection_string(self, config: PostgreSQLConfig) -> str:
        """
        构建数据库连接字符串

        Args:
            config: PostgreSQL 配置

        Returns:
            连接字符串
        """
        return (
            f"postgresql://{config.user}:{config.password}@"
            f"{config.host}:{config.port}/{config.database}"
        )

    def _terminate_database_connections(self, database_name: str) -> None:
        """
        终止所有连接到指定数据库的会话

        Args:
            database_name: 数据库名称
        """
        logger.debug(f"正在终止数据库连接: {database_name}")

        try:
            admin_config = self._create_admin_config()
            admin_client = self.database_manager.connect_postgresql(admin_config)

            # 终止所有连接（排除当前连接）
            terminate_sql = f"""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = '{database_name}'
                AND pid <> pg_backend_pid()
            """

            result = admin_client.execute_query(terminate_sql)
            if result.success:
                logger.debug(f"已终止 {result.rows_affected} 个数据库连接")

            admin_client.close()

        except Exception as e:
            logger.warning(f"终止数据库连接失败: {e}")

    def _drop_database(self, database_name: str) -> None:
        """
        删除数据库

        Args:
            database_name: 数据库名称

        Raises:
            RuntimeError: 删除失败时抛出
        """
        logger.debug(f"正在删除数据库: {database_name}")

        try:
            admin_config = self._create_admin_config()
            admin_client = self.database_manager.connect_postgresql(admin_config)

            # 删除数据库
            drop_sql = f'DROP DATABASE IF EXISTS "{database_name}"'
            result = admin_client.execute_query(drop_sql)

            if not result.success:
                raise RuntimeError(f"删除数据库失败: {result.error}")

            admin_client.close()
            logger.debug(f"数据库删除成功: {database_name}")

        except Exception as e:
            logger.error(f"删除数据库失败: {e}")
            raise RuntimeError(f"删除数据库失败: {e}") from e

    def _force_drop_database(self, database_name: str) -> None:
        """
        强制删除数据库（先终止所有连接）

        Args:
            database_name: 数据库名称
        """
        logger.debug(f"正在强制删除数据库: {database_name}")

        try:
            # 先终止所有连接
            self._terminate_database_connections(database_name)

            # 等待一小段时间确保连接已终止
            import time

            time.sleep(0.5)

            # 删除数据库
            self._drop_database(database_name)

        except Exception as e:
            logger.error(f"强制删除数据库失败: {e}")

    def __enter__(self) -> "TestDatabaseManager":
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """上下文管理器出口 - 自动清理所有测试数据库"""
        self.cleanup_all_test_databases()
