"""
数据库错误处理器

统一处理数据库错误，提供错误分类、恢复策略和修复建议。
"""

import logging
import time
from typing import Callable, List, Optional

from ralph.models.database import DatabaseError

logger = logging.getLogger(__name__)


class ErrorRecoveryStrategy:
    """错误恢复策略"""

    def __init__(
        self,
        strategy_name: str,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        backoff_factor: float = 2.0,
    ):
        """
        初始化恢复策略

        Args:
            strategy_name: 策略名称
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            backoff_factor: 退避因子
        """
        self.strategy_name = strategy_name
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.backoff_factor = backoff_factor

    def execute_with_retry(
        self, operation: Callable, error_types: List[str]
    ) -> tuple[bool, Optional[Exception]]:
        """
        执行操作并在失败时重试

        Args:
            operation: 要执行的操作
            error_types: 可重试的错误类型列表

        Returns:
            (是否成功, 最后的异常)
        """
        last_exception = None
        delay = self.retry_delay

        for attempt in range(self.max_retries + 1):
            try:
                operation()
                logger.info(f"操作成功（尝试 {attempt + 1}/{self.max_retries + 1}）")
                return True, None

            except Exception as e:
                last_exception = e
                error_type = type(e).__name__

                # 检查是否是可重试的错误
                if error_type not in error_types:
                    logger.error(f"不可重试的错误: {error_type}")
                    return False, e

                if attempt < self.max_retries:
                    logger.warning(
                        f"操作失败（尝试 {attempt + 1}/{self.max_retries + 1}），"
                        f"{delay}秒后重试: {e}"
                    )
                    time.sleep(delay)
                    delay *= self.backoff_factor
                else:
                    logger.error(f"操作失败，已达到最大重试次数: {e}")

        return False, last_exception


class DatabaseErrorHandler:
    """数据库错误处理器 - 统一处理数据库错误"""

    def __init__(self):
        """初始化错误处理器"""
        self.error_history: List[DatabaseError] = []
        logger.info("数据库错误处理器初始化完成")

    def handle_error(self, error: Exception, context: str = "") -> DatabaseError:
        """
        处理数据库错误

        Args:
            error: 异常对象
            context: 错误上下文

        Returns:
            数据库错误对象
        """
        logger.error(f"处理数据库错误: {context}, 错误: {error}")

        # 分类错误
        db_error = self._classify_error(error, context)

        # 记录错误历史
        self.error_history.append(db_error)

        # 生成修复建议
        db_error.details["suggestions"] = self._generate_suggestions(db_error)

        return db_error

    def get_recovery_strategy(self, error: DatabaseError) -> ErrorRecoveryStrategy:
        """
        获取错误恢复策略

        Args:
            error: 数据库错误

        Returns:
            恢复策略
        """
        if error.type == "connection_failed":
            return ErrorRecoveryStrategy(
                strategy_name="connection_retry",
                max_retries=3,
                retry_delay=2.0,
                backoff_factor=2.0,
            )
        elif error.type == "timeout":
            return ErrorRecoveryStrategy(
                strategy_name="timeout_retry",
                max_retries=2,
                retry_delay=5.0,
                backoff_factor=1.5,
            )
        elif error.type == "deadlock":
            return ErrorRecoveryStrategy(
                strategy_name="deadlock_retry",
                max_retries=5,
                retry_delay=0.5,
                backoff_factor=1.5,
            )
        else:
            return ErrorRecoveryStrategy(
                strategy_name="default_retry",
                max_retries=1,
                retry_delay=1.0,
                backoff_factor=1.0,
            )

    def _classify_error(self, error: Exception, context: str) -> DatabaseError:
        """
        分类错误

        Args:
            error: 异常对象
            context: 错误上下文

        Returns:
            数据库错误对象
        """
        error_msg = str(error).lower()
        error_type_name = type(error).__name__

        # 连接错误
        if "connection" in error_msg and (
            "refused" in error_msg or "failed" in error_msg
        ):
            return DatabaseError(
                type="connection_failed",
                message=f"数据库连接失败: {error}",
                details={"context": context, "error_type": error_type_name},
            )

        # 认证错误
        if "authentication" in error_msg or "password" in error_msg:
            return DatabaseError(
                type="authentication_failed",
                message=f"数据库认证失败: {error}",
                details={"context": context, "error_type": error_type_name},
            )

        # 超时错误
        if "timeout" in error_msg:
            return DatabaseError(
                type="timeout",
                message=f"数据库操作超时: {error}",
                details={"context": context, "error_type": error_type_name},
            )

        # 查询错误
        if "syntax" in error_msg or "sql" in error_msg:
            return DatabaseError(
                type="query_error",
                message=f"SQL 查询错误: {error}",
                details={"context": context, "error_type": error_type_name},
            )

        # 约束违反错误
        if "constraint" in error_msg or "unique" in error_msg or "foreign key" in error_msg:
            return DatabaseError(
                type="constraint_violation",
                message=f"数据库约束违反: {error}",
                details={"context": context, "error_type": error_type_name},
            )

        # 死锁错误
        if "deadlock" in error_msg:
            return DatabaseError(
                type="deadlock",
                message=f"数据库死锁: {error}",
                details={"context": context, "error_type": error_type_name},
            )

        # 迁移错误
        if "migration" in error_msg or "alembic" in error_msg:
            return DatabaseError(
                type="migration_error",
                message=f"数据库迁移错误: {error}",
                details={"context": context, "error_type": error_type_name},
            )

        # 未知错误
        return DatabaseError(
            type="unknown_error",
            message=f"未知数据库错误: {error}",
            details={"context": context, "error_type": error_type_name},
        )

    def _generate_suggestions(self, error: DatabaseError) -> List[str]:
        """
        生成修复建议

        Args:
            error: 数据库错误

        Returns:
            修复建议列表
        """
        suggestions = []

        if error.type == "connection_failed":
            suggestions.extend(
                [
                    "检查数据库服务是否正在运行",
                    "验证数据库主机地址和端口是否正确",
                    "检查网络连接和防火墙设置",
                    "确认数据库配置文件中的连接参数",
                ]
            )

        elif error.type == "authentication_failed":
            suggestions.extend(
                [
                    "验证数据库用户名和密码是否正确",
                    "检查用户是否有访问数据库的权限",
                    "确认数据库认证方式配置正确",
                    "检查 pg_hba.conf（PostgreSQL）或认证配置",
                ]
            )

        elif error.type == "timeout":
            suggestions.extend(
                [
                    "增加数据库连接超时时间",
                    "优化查询性能，减少执行时间",
                    "检查数据库服务器负载",
                    "考虑添加数据库索引",
                    "检查是否有长时间运行的事务阻塞",
                ]
            )

        elif error.type == "query_error":
            suggestions.extend(
                [
                    "检查 SQL 语法是否正确",
                    "验证表名和列名是否存在",
                    "确认数据类型匹配",
                    "检查 SQL 注入防护是否影响查询",
                ]
            )

        elif error.type == "constraint_violation":
            suggestions.extend(
                [
                    "检查唯一约束冲突",
                    "验证外键引用的数据是否存在",
                    "确认非空约束的字段有值",
                    "检查数据完整性规则",
                ]
            )

        elif error.type == "deadlock":
            suggestions.extend(
                [
                    "重试操作（死锁通常是暂时的）",
                    "优化事务顺序，减少锁竞争",
                    "缩短事务持续时间",
                    "考虑使用乐观锁代替悲观锁",
                ]
            )

        elif error.type == "migration_error":
            suggestions.extend(
                [
                    "检查迁移脚本的 SQL 语法",
                    "验证迁移依赖关系",
                    "确认数据库版本兼容性",
                    "回滚到上一个稳定版本",
                    "手动修复数据库状态",
                ]
            )

        else:
            suggestions.extend(
                [
                    "查看完整的错误日志",
                    "检查数据库服务器日志",
                    "联系数据库管理员",
                    "参考数据库官方文档",
                ]
            )

        return suggestions

    def get_error_statistics(self) -> dict:
        """
        获取错误统计信息

        Returns:
            错误统计字典
        """
        if not self.error_history:
            return {"total_errors": 0, "error_types": {}}

        # 统计错误类型
        error_types = {}
        for error in self.error_history:
            error_types[error.type] = error_types.get(error.type, 0) + 1

        return {
            "total_errors": len(self.error_history),
            "error_types": error_types,
            "most_common_error": max(error_types, key=error_types.get)
            if error_types
            else None,
        }

    def clear_error_history(self) -> None:
        """清除错误历史"""
        self.error_history.clear()
        logger.info("错误历史已清除")
