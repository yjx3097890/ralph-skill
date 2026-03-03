"""
PostgreSQL 客户端

封装 PostgreSQL 数据库操作，包括查询执行、事务管理和连接管理。
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import psycopg2
import psycopg2.extras
import psycopg2.pool
from psycopg2 import sql

from ralph.models.database import (
    ConnectionInfo,
    DatabaseError,
    PostgreSQLConfig,
    QueryResult,
)

logger = logging.getLogger(__name__)


class Transaction:
    """数据库事务"""

    def __init__(self, connection: Any):
        """
        初始化事务

        Args:
            connection: 数据库连接对象
        """
        self.connection = connection
        self.started = False

    def begin(self) -> None:
        """开始事务"""
        if not self.started:
            self.started = True
            logger.debug("事务已开始")

    def commit(self) -> None:
        """提交事务"""
        if self.started:
            self.connection.commit()
            self.started = False
            logger.debug("事务已提交")

    def rollback(self) -> None:
        """回滚事务"""
        if self.started:
            self.connection.rollback()
            self.started = False
            logger.debug("事务已回滚")


class PostgreSQLClient:
    """PostgreSQL 客户端 - 封装数据库操作"""

    def __init__(self, config: PostgreSQLConfig):
        """
        初始化 PostgreSQL 客户端

        Args:
            config: PostgreSQL 配置
        """
        self.config = config
        self._connection: Optional[Any] = None
        self._pool: Optional[psycopg2.pool.SimpleConnectionPool] = None
        self._connection_time: Optional[datetime] = None
        logger.info(f"PostgreSQL 客户端初始化: {config.host}:{config.port}/{config.database}")

    def connect(self) -> None:
        """
        建立数据库连接

        Raises:
            ConnectionError: 连接失败时抛出
        """
        try:
            # 创建连接池
            self._pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=self.config.pool_size + self.config.max_overflow,
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.user,
                password=self.config.password,
                sslmode=self.config.ssl_mode,
                connect_timeout=self.config.connection_timeout,
            )

            # 获取一个连接用于测试
            self._connection = self._pool.getconn()
            self._connection_time = datetime.now()

            # 测试连接
            cursor = self._connection.cursor()
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            cursor.close()

            logger.info(f"PostgreSQL 连接成功: {version}")

        except psycopg2.OperationalError as e:
            error = self._parse_connection_error(e)
            logger.error(f"PostgreSQL 连接失败: {error.message}")
            raise ConnectionError(error.message) from e

        except Exception as e:
            logger.error(f"PostgreSQL 连接失败: {e}")
            raise ConnectionError(f"无法连接到 PostgreSQL: {e}") from e

    def execute_query(
        self, sql_query: str, params: Optional[Dict[str, Any]] = None
    ) -> QueryResult:
        """
        执行 SQL 查询

        Args:
            sql_query: SQL 查询语句
            params: 查询参数（可选）

        Returns:
            查询结果

        Raises:
            RuntimeError: 未连接到数据库时抛出
        """
        if not self._connection:
            raise RuntimeError("未连接到数据库")

        start_time = time.time()

        try:
            cursor = self._connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # 执行查询
            if params:
                cursor.execute(sql_query, params)
            else:
                cursor.execute(sql_query)

            # 获取结果
            rows_affected = cursor.rowcount
            rows = []

            # 如果是 SELECT 查询，获取结果
            if cursor.description:
                rows = [dict(row) for row in cursor.fetchall()]

            cursor.close()

            execution_time = time.time() - start_time
            logger.debug(
                f"查询执行成功: {rows_affected} 行受影响, 耗时 {execution_time:.3f}s"
            )

            return QueryResult(
                success=True,
                rows_affected=rows_affected,
                rows=rows,
                execution_time=execution_time,
            )

        except psycopg2.Error as e:
            execution_time = time.time() - start_time
            error_msg = f"查询执行失败: {e}"
            logger.error(error_msg)

            return QueryResult(
                success=False,
                rows_affected=0,
                rows=[],
                execution_time=execution_time,
                error=error_msg,
            )

    def execute_many(
        self, sql_query: str, params_list: List[Dict[str, Any]]
    ) -> QueryResult:
        """
        批量执行 SQL 查询

        Args:
            sql_query: SQL 查询语句
            params_list: 参数列表

        Returns:
            查询结果

        Raises:
            RuntimeError: 未连接到数据库时抛出
        """
        if not self._connection:
            raise RuntimeError("未连接到数据库")

        start_time = time.time()

        try:
            cursor = self._connection.cursor()

            # 批量执行
            cursor.executemany(sql_query, params_list)

            rows_affected = cursor.rowcount
            cursor.close()

            execution_time = time.time() - start_time
            logger.debug(
                f"批量查询执行成功: {rows_affected} 行受影响, 耗时 {execution_time:.3f}s"
            )

            return QueryResult(
                success=True,
                rows_affected=rows_affected,
                rows=[],
                execution_time=execution_time,
            )

        except psycopg2.Error as e:
            execution_time = time.time() - start_time
            error_msg = f"批量查询执行失败: {e}"
            logger.error(error_msg)

            return QueryResult(
                success=False,
                rows_affected=0,
                rows=[],
                execution_time=execution_time,
                error=error_msg,
            )

    def begin_transaction(self) -> Transaction:
        """
        开始事务

        Returns:
            事务对象

        Raises:
            RuntimeError: 未连接到数据库时抛出
        """
        if not self._connection:
            raise RuntimeError("未连接到数据库")

        transaction = Transaction(self._connection)
        transaction.begin()
        return transaction

    def commit_transaction(self, transaction: Transaction) -> bool:
        """
        提交事务

        Args:
            transaction: 事务对象

        Returns:
            是否成功提交
        """
        try:
            transaction.commit()
            return True
        except Exception as e:
            logger.error(f"事务提交失败: {e}")
            return False

    def rollback_transaction(self, transaction: Transaction) -> bool:
        """
        回滚事务

        Args:
            transaction: 事务对象

        Returns:
            是否成功回滚
        """
        try:
            transaction.rollback()
            return True
        except Exception as e:
            logger.error(f"事务回滚失败: {e}")
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
            database=self.config.database,
            user=self.config.user,
            connected=self._connection is not None,
            connection_time=self._connection_time,
        )

    def close(self) -> None:
        """关闭数据库连接"""
        if self._connection:
            try:
                # 归还连接到连接池
                if self._pool:
                    self._pool.putconn(self._connection)
                self._connection = None
                logger.info("PostgreSQL 连接已关闭")
            except Exception as e:
                logger.error(f"关闭连接失败: {e}")

        if self._pool:
            try:
                self._pool.closeall()
                self._pool = None
                logger.info("PostgreSQL 连接池已关闭")
            except Exception as e:
                logger.error(f"关闭连接池失败: {e}")

    def _parse_connection_error(self, error: Exception) -> DatabaseError:
        """
        解析连接错误

        Args:
            error: 异常对象

        Returns:
            数据库错误信息
        """
        error_msg = str(error).lower()

        if "authentication failed" in error_msg or "password" in error_msg:
            return DatabaseError(
                type="authentication_failed",
                message=f"数据库认证失败：密码错误",
                details={"host": self.config.host, "user": self.config.user},
            )
        elif "database" in error_msg and "does not exist" in error_msg:
            return DatabaseError(
                type="database_not_found",
                message=f"数据库不存在：{self.config.database}",
                details={"database": self.config.database},
            )
        elif "connection" in error_msg and ("refused" in error_msg or "failed" in error_msg):
            return DatabaseError(
                type="connection_failed",
                message=f"无法连接到数据库服务器：{self.config.host}:{self.config.port}",
                details={"host": self.config.host, "port": self.config.port},
            )
        elif "timeout" in error_msg:
            return DatabaseError(
                type="timeout",
                message=f"连接超时：{self.config.connection_timeout}秒",
                details={"timeout": self.config.connection_timeout},
            )
        else:
            return DatabaseError(
                type="unknown_error",
                message=str(error),
                details={},
            )

    def __enter__(self) -> "PostgreSQLClient":
        """上下文管理器入口"""
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """上下文管理器出口"""
        self.close()
