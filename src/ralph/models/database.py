"""
数据库相关数据模型

定义数据库配置、连接状态、查询结果等数据结构。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class PostgreSQLConfig:
    """PostgreSQL 数据库配置"""

    host: str
    port: int = 5432
    database: str = "postgres"
    user: str = "postgres"
    password: str = ""
    ssl_mode: str = "prefer"  # disable, allow, prefer, require
    connection_timeout: int = 30
    pool_size: int = 10
    max_overflow: int = 20


@dataclass
class RedisConfig:
    """Redis 缓存配置"""

    host: str
    port: int = 6379
    password: Optional[str] = None
    db: int = 0
    ssl: bool = False
    connection_timeout: int = 10
    socket_timeout: int = 5
    max_connections: int = 50


@dataclass
class DatabaseConfig:
    """数据库配置"""

    postgresql: Optional[PostgreSQLConfig] = None
    redis: Optional[RedisConfig] = None
    migration_dir: Optional[str] = None
    migration_tool: Optional[str] = None  # alembic, golang-migrate


@dataclass
class ConnectionStatus:
    """数据库连接状态"""

    connected: bool
    host: str
    port: int
    database: Optional[str]
    latency_ms: float
    error: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None


@dataclass
class QueryResult:
    """数据库查询结果"""

    success: bool
    rows_affected: int
    rows: List[Dict[str, Any]]
    execution_time: float
    error: Optional[str] = None


@dataclass
class ConnectionInfo:
    """数据库连接信息"""

    host: str
    port: int
    database: Optional[str]
    user: Optional[str]
    connected: bool
    connection_time: Optional[datetime] = None


@dataclass
class DatabaseError:
    """数据库错误信息"""

    type: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class MigrationResult:
    """数据库迁移结果"""

    success: bool
    migrations_applied: List[str]
    current_version: str
    execution_time: float
    errors: List["MigrationError"] = field(default_factory=list)


@dataclass
class MigrationError:
    """数据库迁移错误"""

    migration_version: str
    migration_file: str
    error_type: str  # syntax_error, constraint_violation, etc.
    error_message: str
    sql_statement: Optional[str] = None
    line_number: Optional[int] = None


@dataclass
class TestDatabase:
    """测试数据库"""

    name: str
    connection_string: str
    created_at: datetime
    transaction: Optional[Any] = None  # Transaction 对象
