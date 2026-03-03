"""
数据库迁移运行器

管理数据库迁移脚本的执行，支持 Alembic 和 golang-migrate 工具。
"""

import logging
import os
import re
import subprocess
from pathlib import Path
from typing import List, Optional

from ralph.models.database import MigrationError, MigrationResult

logger = logging.getLogger(__name__)


class Migration:
    """迁移脚本信息"""

    def __init__(
        self,
        version: str,
        file_path: str,
        description: str = "",
        tool: str = "unknown",
    ):
        """
        初始化迁移信息

        Args:
            version: 迁移版本号
            file_path: 迁移文件路径
            description: 迁移描述
            tool: 迁移工具（alembic 或 golang-migrate）
        """
        self.version = version
        self.file_path = file_path
        self.description = description
        self.tool = tool

    def __repr__(self) -> str:
        return f"Migration(version={self.version}, tool={self.tool}, file={self.file_path})"


class MigrationRunner:
    """数据库迁移运行器 - 管理迁移执行"""

    def __init__(self, project_path: str):
        """
        初始化迁移运行器

        Args:
            project_path: 项目根目录路径
        """
        self.project_path = Path(project_path)
        self.migration_tool: Optional[str] = None
        self.migration_dir: Optional[Path] = None
        logger.info(f"迁移运行器初始化: {project_path}")

    def detect_migration_tool(self) -> Optional[str]:
        """
        检测项目使用的迁移工具

        Returns:
            迁移工具名称（alembic 或 golang-migrate），如果未检测到返回 None
        """
        # 检测 Alembic
        alembic_ini = self.project_path / "alembic.ini"
        alembic_dir = self.project_path / "alembic"

        if alembic_ini.exists() and alembic_dir.exists():
            logger.info("检测到 Alembic 迁移工具")
            self.migration_tool = "alembic"
            self.migration_dir = alembic_dir / "versions"
            return "alembic"

        # 检测 golang-migrate
        migrations_dir = self.project_path / "migrations"
        if migrations_dir.exists():
            # 检查是否有 .up.sql 或 .down.sql 文件
            sql_files = list(migrations_dir.glob("*.up.sql")) + list(
                migrations_dir.glob("*.down.sql")
            )
            if sql_files:
                logger.info("检测到 golang-migrate 迁移工具")
                self.migration_tool = "golang-migrate"
                self.migration_dir = migrations_dir
                return "golang-migrate"

        # 检查 db/migrations 目录（另一个常见位置）
        db_migrations_dir = self.project_path / "db" / "migrations"
        if db_migrations_dir.exists():
            sql_files = list(db_migrations_dir.glob("*.up.sql")) + list(
                db_migrations_dir.glob("*.down.sql")
            )
            if sql_files:
                logger.info("检测到 golang-migrate 迁移工具（db/migrations）")
                self.migration_tool = "golang-migrate"
                self.migration_dir = db_migrations_dir
                return "golang-migrate"

        logger.warning("未检测到迁移工具")
        return None

    def scan_migrations(self, migration_dir: Optional[Path] = None) -> List[Migration]:
        """
        扫描迁移文件

        Args:
            migration_dir: 迁移目录路径，如果为 None 则使用检测到的目录

        Returns:
            迁移列表，按版本号排序
        """
        if migration_dir is None:
            if self.migration_dir is None:
                self.detect_migration_tool()
            migration_dir = self.migration_dir

        if migration_dir is None or not migration_dir.exists():
            logger.warning(f"迁移目录不存在: {migration_dir}")
            return []

        migrations: List[Migration] = []

        if self.migration_tool == "alembic":
            # 扫描 Alembic 迁移文件（*.py）
            for file_path in sorted(migration_dir.glob("*.py")):
                if file_path.name == "__init__.py":
                    continue

                # Alembic 文件名格式: {revision}_{description}.py
                match = re.match(r"([a-f0-9]+)_(.+)\.py", file_path.name)
                if match:
                    version = match.group(1)
                    description = match.group(2).replace("_", " ")
                    migrations.append(
                        Migration(
                            version=version,
                            file_path=str(file_path),
                            description=description,
                            tool="alembic",
                        )
                    )

        elif self.migration_tool == "golang-migrate":
            # 扫描 golang-migrate 迁移文件（*.up.sql）
            for file_path in sorted(migration_dir.glob("*.up.sql")):
                # golang-migrate 文件名格式: {version}_{description}.up.sql
                match = re.match(r"(\d+)_(.+)\.up\.sql", file_path.name)
                if match:
                    version = match.group(1)
                    description = match.group(2).replace("_", " ")
                    migrations.append(
                        Migration(
                            version=version,
                            file_path=str(file_path),
                            description=description,
                            tool="golang-migrate",
                        )
                    )

        logger.info(f"扫描到 {len(migrations)} 个迁移文件")
        return migrations

    def get_current_version(self) -> str:
        """
        获取当前数据库迁移版本

        Returns:
            当前版本号，如果无法获取返回 "unknown"
        """
        if self.migration_tool is None:
            self.detect_migration_tool()

        if self.migration_tool == "alembic":
            return self._get_alembic_current_version()
        elif self.migration_tool == "golang-migrate":
            return self._get_golang_migrate_current_version()
        else:
            logger.warning("未检测到迁移工具，无法获取当前版本")
            return "unknown"

    def _get_alembic_current_version(self) -> str:
        """
        获取 Alembic 当前版本

        Returns:
            当前版本号
        """
        try:
            result = subprocess.run(
                ["alembic", "current"],
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                # 解析输出: "INFO  [alembic.runtime.migration] Context impl PostgresqlImpl."
                # "INFO  [alembic.runtime.migration] Will assume transactional DDL."
                # "abc123 (head)"
                output = result.stdout.strip()
                match = re.search(r"([a-f0-9]+)\s+\(head\)", output)
                if match:
                    version = match.group(1)
                    logger.info(f"Alembic 当前版本: {version}")
                    return version

            logger.warning("无法解析 Alembic 当前版本")
            return "unknown"

        except subprocess.TimeoutExpired:
            logger.error("获取 Alembic 版本超时")
            return "unknown"
        except FileNotFoundError:
            logger.error("Alembic 命令未找到")
            return "unknown"
        except Exception as e:
            logger.error(f"获取 Alembic 版本失败: {e}")
            return "unknown"

    def _get_golang_migrate_current_version(self) -> str:
        """
        获取 golang-migrate 当前版本

        Returns:
            当前版本号
        """
        try:
            # golang-migrate 需要数据库连接字符串
            # 这里我们只能通过查看迁移文件来推断
            # 实际应用中需要连接数据库查询 schema_migrations 表
            logger.warning("golang-migrate 版本查询需要数据库连接")
            return "unknown"

        except Exception as e:
            logger.error(f"获取 golang-migrate 版本失败: {e}")
            return "unknown"

    def execute_migration(
        self, migration: Migration, database_url: Optional[str] = None
    ) -> MigrationResult:
        """
        执行单个迁移

        Args:
            migration: 迁移对象
            database_url: 数据库连接字符串（golang-migrate 需要）

        Returns:
            迁移结果
        """
        logger.info(f"执行迁移: {migration}")

        if migration.tool == "alembic":
            return self._execute_alembic_migration(migration)
        elif migration.tool == "golang-migrate":
            if database_url is None:
                return MigrationResult(
                    success=False,
                    migrations_applied=[],
                    current_version="unknown",
                    execution_time=0.0,
                    errors=[
                        MigrationError(
                            migration_version=migration.version,
                            migration_file=migration.file_path,
                            error_type="missing_database_url",
                            error_message="golang-migrate 需要数据库连接字符串",
                        )
                    ],
                )
            return self._execute_golang_migrate_migration(migration, database_url)
        else:
            return MigrationResult(
                success=False,
                migrations_applied=[],
                current_version="unknown",
                execution_time=0.0,
                errors=[
                    MigrationError(
                        migration_version=migration.version,
                        migration_file=migration.file_path,
                        error_type="unknown_tool",
                        error_message=f"不支持的迁移工具: {migration.tool}",
                    )
                ],
            )

    def _execute_alembic_migration(self, migration: Migration) -> MigrationResult:
        """
        执行 Alembic 迁移

        Args:
            migration: 迁移对象

        Returns:
            迁移结果
        """
        import time

        start_time = time.time()

        try:
            # 执行 alembic upgrade
            result = subprocess.run(
                ["alembic", "upgrade", migration.version],
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                timeout=300,  # 5 分钟超时
            )

            execution_time = time.time() - start_time

            if result.returncode == 0:
                logger.info(f"Alembic 迁移成功: {migration.version}")
                return MigrationResult(
                    success=True,
                    migrations_applied=[migration.version],
                    current_version=migration.version,
                    execution_time=execution_time,
                )
            else:
                # 解析错误
                error = self._parse_alembic_error(result.stderr, migration)
                logger.error(f"Alembic 迁移失败: {error.error_message}")
                return MigrationResult(
                    success=False,
                    migrations_applied=[],
                    current_version=self.get_current_version(),
                    execution_time=execution_time,
                    errors=[error],
                )

        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            logger.error("Alembic 迁移超时")
            return MigrationResult(
                success=False,
                migrations_applied=[],
                current_version=self.get_current_version(),
                execution_time=execution_time,
                errors=[
                    MigrationError(
                        migration_version=migration.version,
                        migration_file=migration.file_path,
                        error_type="timeout",
                        error_message="迁移执行超时（5分钟）",
                    )
                ],
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Alembic 迁移失败: {e}")
            return MigrationResult(
                success=False,
                migrations_applied=[],
                current_version=self.get_current_version(),
                execution_time=execution_time,
                errors=[
                    MigrationError(
                        migration_version=migration.version,
                        migration_file=migration.file_path,
                        error_type="execution_error",
                        error_message=str(e),
                    )
                ],
            )

    def _execute_golang_migrate_migration(
        self, migration: Migration, database_url: str
    ) -> MigrationResult:
        """
        执行 golang-migrate 迁移

        Args:
            migration: 迁移对象
            database_url: 数据库连接字符串

        Returns:
            迁移结果
        """
        import time

        start_time = time.time()

        try:
            # 执行 migrate up
            result = subprocess.run(
                [
                    "migrate",
                    "-path",
                    str(self.migration_dir),
                    "-database",
                    database_url,
                    "up",
                    "1",  # 执行一个迁移
                ],
                capture_output=True,
                text=True,
                timeout=300,  # 5 分钟超时
            )

            execution_time = time.time() - start_time

            if result.returncode == 0:
                logger.info(f"golang-migrate 迁移成功: {migration.version}")
                return MigrationResult(
                    success=True,
                    migrations_applied=[migration.version],
                    current_version=migration.version,
                    execution_time=execution_time,
                )
            else:
                # 解析错误
                error = self._parse_golang_migrate_error(result.stderr, migration)
                logger.error(f"golang-migrate 迁移失败: {error.error_message}")
                return MigrationResult(
                    success=False,
                    migrations_applied=[],
                    current_version=self.get_current_version(),
                    execution_time=execution_time,
                    errors=[error],
                )

        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            logger.error("golang-migrate 迁移超时")
            return MigrationResult(
                success=False,
                migrations_applied=[],
                current_version=self.get_current_version(),
                execution_time=execution_time,
                errors=[
                    MigrationError(
                        migration_version=migration.version,
                        migration_file=migration.file_path,
                        error_type="timeout",
                        error_message="迁移执行超时（5分钟）",
                    )
                ],
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"golang-migrate 迁移失败: {e}")
            return MigrationResult(
                success=False,
                migrations_applied=[],
                current_version=self.get_current_version(),
                execution_time=execution_time,
                errors=[
                    MigrationError(
                        migration_version=migration.version,
                        migration_file=migration.file_path,
                        error_type="execution_error",
                        error_message=str(e),
                    )
                ],
            )

    def _parse_alembic_error(
        self, error_output: str, migration: Migration
    ) -> MigrationError:
        """
        解析 Alembic 错误输出

        Args:
            error_output: 错误输出
            migration: 迁移对象

        Returns:
            迁移错误对象
        """
        # 解析 sqlalchemy.exc.* 错误
        if "sqlalchemy.exc" in error_output:
            # 提取错误类型
            match = re.search(r"sqlalchemy\.exc\.(\w+)", error_output)
            error_type = match.group(1) if match else "unknown"

            # 提取 SQL 语句
            sql_match = re.search(r"\[SQL: (.+?)\]", error_output, re.DOTALL)
            sql_statement = sql_match.group(1) if sql_match else None

            return MigrationError(
                migration_version=migration.version,
                migration_file=migration.file_path,
                error_type=error_type,
                error_message=error_output,
                sql_statement=sql_statement,
            )

        return MigrationError(
            migration_version=migration.version,
            migration_file=migration.file_path,
            error_type="unknown",
            error_message=error_output,
        )

    def _parse_golang_migrate_error(
        self, error_output: str, migration: Migration
    ) -> MigrationError:
        """
        解析 golang-migrate 错误输出

        Args:
            error_output: 错误输出
            migration: 迁移对象

        Returns:
            迁移错误对象
        """
        # 解析 "error: ... in line X" 格式
        match = re.search(r"error: (.+?) in line (\d+)", error_output)
        if match:
            error_message = match.group(1)
            line_number = int(match.group(2))

            return MigrationError(
                migration_version=migration.version,
                migration_file=migration.file_path,
                error_type="migration_error",
                error_message=error_message,
                line_number=line_number,
            )

        return MigrationError(
            migration_version=migration.version,
            migration_file=migration.file_path,
            error_type="unknown",
            error_message=error_output,
        )
