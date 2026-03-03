"""
数据库容器错误解析器

解析 PostgreSQL 和 Redis 容器的错误日志，提供诊断信息和修复建议。
"""

import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class DatabaseContainerError:
    """数据库容器错误"""

    def __init__(
        self,
        error_type: str,
        message: str,
        details: Optional[Dict[str, str]] = None,
        suggestions: Optional[List[str]] = None,
    ):
        """
        初始化数据库容器错误

        Args:
            error_type: 错误类型
            message: 错误消息
            details: 错误详情
            suggestions: 修复建议
        """
        self.error_type = error_type
        self.message = message
        self.details = details or {}
        self.suggestions = suggestions or []

    def __repr__(self) -> str:
        return f"DatabaseContainerError(type={self.error_type}, message={self.message})"


class DatabaseContainerErrorParser:
    """数据库容器错误解析器"""

    def __init__(self):
        """初始化错误解析器"""
        logger.info("数据库容器错误解析器初始化完成")

    def parse_postgresql_logs(self, logs: str) -> List[DatabaseContainerError]:
        """
        解析 PostgreSQL 容器日志

        Args:
            logs: 容器日志

        Returns:
            错误列表
        """
        errors: List[DatabaseContainerError] = []

        # 检查认证错误
        if "FATAL:  password authentication failed" in logs:
            errors.append(
                DatabaseContainerError(
                    error_type="authentication_failed",
                    message="PostgreSQL 认证失败：密码错误",
                    suggestions=[
                        "检查 POSTGRES_PASSWORD 环境变量是否正确",
                        "确认客户端使用的密码与容器配置一致",
                    ],
                )
            )

        # 检查数据库不存在错误
        if 'FATAL:  database "' in logs and '" does not exist' in logs:
            match = re.search(r'FATAL:  database "([^"]+)" does not exist', logs)
            db_name = match.group(1) if match else "unknown"
            errors.append(
                DatabaseContainerError(
                    error_type="database_not_found",
                    message=f"数据库不存在: {db_name}",
                    details={"database": db_name},
                    suggestions=[
                        f"检查 POSTGRES_DB 环境变量是否设置为 {db_name}",
                        "确认数据库已正确创建",
                    ],
                )
            )

        # 检查端口占用错误
        if "could not bind IPv4 address" in logs or "Address already in use" in logs:
            errors.append(
                DatabaseContainerError(
                    error_type="port_in_use",
                    message="PostgreSQL 端口已被占用",
                    suggestions=[
                        "检查是否有其他 PostgreSQL 实例正在运行",
                        "更改容器的主机端口映射",
                        "停止占用端口的进程",
                    ],
                )
            )

        # 检查数据目录权限错误
        if "FATAL:  data directory" in logs and "has wrong ownership" in logs:
            errors.append(
                DatabaseContainerError(
                    error_type="permission_denied",
                    message="数据目录权限错误",
                    suggestions=[
                        "检查数据目录的所有者和权限",
                        "使用 chown 修改目录所有者为 postgres 用户",
                        "确保容器有读写数据目录的权限",
                    ],
                )
            )

        # 检查磁盘空间不足错误
        if "No space left on device" in logs:
            errors.append(
                DatabaseContainerError(
                    error_type="disk_full",
                    message="磁盘空间不足",
                    suggestions=[
                        "清理磁盘空间",
                        "增加数据卷的大小",
                        "检查是否有大量日志文件占用空间",
                    ],
                )
            )

        # 检查配置错误
        if "FATAL:  invalid value for parameter" in logs:
            match = re.search(
                r'FATAL:  invalid value for parameter "([^"]+)"', logs
            )
            param_name = match.group(1) if match else "unknown"
            errors.append(
                DatabaseContainerError(
                    error_type="config_error",
                    message=f"配置参数错误: {param_name}",
                    details={"parameter": param_name},
                    suggestions=[
                        f"检查 {param_name} 参数的值是否正确",
                        "参考 PostgreSQL 文档确认参数的有效值",
                    ],
                )
            )

        # 检查网络错误
        if "could not receive data from client" in logs:
            errors.append(
                DatabaseContainerError(
                    error_type="network_error",
                    message="网络连接错误",
                    suggestions=[
                        "检查容器网络配置",
                        "确认客户端和容器在同一网络中",
                        "检查防火墙设置",
                    ],
                )
            )

        return errors

    def parse_redis_logs(self, logs: str) -> List[DatabaseContainerError]:
        """
        解析 Redis 容器日志

        Args:
            logs: 容器日志

        Returns:
            错误列表
        """
        errors: List[DatabaseContainerError] = []

        # 检查认证错误
        if "NOAUTH Authentication required" in logs or "invalid password" in logs:
            errors.append(
                DatabaseContainerError(
                    error_type="authentication_failed",
                    message="Redis 认证失败",
                    suggestions=[
                        "检查 --requirepass 参数是否正确设置",
                        "确认客户端使用了正确的密码",
                    ],
                )
            )

        # 检查端口占用错误
        if "Address already in use" in logs or "bind: Address already in use" in logs:
            errors.append(
                DatabaseContainerError(
                    error_type="port_in_use",
                    message="Redis 端口已被占用",
                    suggestions=[
                        "检查是否有其他 Redis 实例正在运行",
                        "更改容器的主机端口映射",
                        "停止占用端口的进程",
                    ],
                )
            )

        # 检查配置文件错误
        if "Bad directive or wrong number of arguments" in logs:
            errors.append(
                DatabaseContainerError(
                    error_type="config_error",
                    message="Redis 配置文件错误",
                    suggestions=[
                        "检查 redis.conf 配置文件语法",
                        "确认配置指令和参数数量正确",
                        "参考 Redis 文档验证配置",
                    ],
                )
            )

        # 检查内存不足错误
        if "Out of memory" in logs or "OOM" in logs:
            errors.append(
                DatabaseContainerError(
                    error_type="out_of_memory",
                    message="Redis 内存不足",
                    suggestions=[
                        "增加容器的内存限制",
                        "配置 maxmemory 参数限制 Redis 内存使用",
                        "配置内存淘汰策略（maxmemory-policy）",
                        "清理不需要的数据",
                    ],
                )
            )

        # 检查持久化错误
        if "Can't save in background: fork" in logs:
            errors.append(
                DatabaseContainerError(
                    error_type="persistence_error",
                    message="Redis 后台保存失败",
                    suggestions=[
                        "增加系统内存",
                        "禁用 RDB 持久化或使用 AOF",
                        "调整 vm.overcommit_memory 内核参数",
                    ],
                )
            )

        # 检查 AOF 错误
        if "Bad file format reading the append only file" in logs:
            errors.append(
                DatabaseContainerError(
                    error_type="aof_corrupted",
                    message="AOF 文件损坏",
                    suggestions=[
                        "使用 redis-check-aof 工具修复 AOF 文件",
                        "备份并删除损坏的 AOF 文件",
                        "从 RDB 快照恢复数据",
                    ],
                )
            )

        # 检查磁盘空间不足错误
        if "No space left on device" in logs:
            errors.append(
                DatabaseContainerError(
                    error_type="disk_full",
                    message="磁盘空间不足",
                    suggestions=[
                        "清理磁盘空间",
                        "增加数据卷的大小",
                        "检查 RDB 和 AOF 文件大小",
                    ],
                )
            )

        # 检查网络错误
        if "Error accepting a client connection" in logs:
            errors.append(
                DatabaseContainerError(
                    error_type="network_error",
                    message="Redis 网络连接错误",
                    suggestions=[
                        "检查容器网络配置",
                        "确认客户端和容器在同一网络中",
                        "检查防火墙设置",
                        "检查 Redis 的 bind 配置",
                    ],
                )
            )

        return errors

    def diagnose_container_startup_failure(
        self, container_name: str, logs: str, database_type: str
    ) -> Dict[str, any]:
        """
        诊断容器启动失败

        Args:
            container_name: 容器名称
            logs: 容器日志
            database_type: 数据库类型（postgresql 或 redis）

        Returns:
            诊断信息字典
        """
        logger.info(f"诊断容器启动失败: {container_name} ({database_type})")

        # 解析错误
        if database_type.lower() == "postgresql":
            errors = self.parse_postgresql_logs(logs)
        elif database_type.lower() == "redis":
            errors = self.parse_redis_logs(logs)
        else:
            errors = []

        # 构建诊断信息
        diagnosis = {
            "container_name": container_name,
            "database_type": database_type,
            "errors_found": len(errors),
            "errors": [
                {
                    "type": error.error_type,
                    "message": error.message,
                    "details": error.details,
                    "suggestions": error.suggestions,
                }
                for error in errors
            ],
            "log_summary": self._summarize_logs(logs),
        }

        return diagnosis

    def diagnose_network_error(
        self, container_name: str, host: str, port: int
    ) -> Dict[str, any]:
        """
        诊断网络配置错误

        Args:
            container_name: 容器名称
            host: 主机地址
            port: 端口号

        Returns:
            诊断信息字典
        """
        logger.info(f"诊断网络配置错误: {container_name}")

        diagnosis = {
            "container_name": container_name,
            "host": host,
            "port": port,
            "possible_causes": [
                "容器未正确启动",
                "端口映射配置错误",
                "容器和客户端不在同一网络中",
                "防火墙阻止了连接",
                "容器内服务未监听正确的地址",
            ],
            "suggestions": [
                f"检查容器是否正在运行: docker ps | grep {container_name}",
                f"检查端口映射: docker port {container_name}",
                f"检查容器网络: docker inspect {container_name}",
                f"尝试从容器内部连接: docker exec {container_name} <connection_command>",
                "检查防火墙规则",
                "确认服务绑定到 0.0.0.0 而不是 127.0.0.1",
            ],
        }

        return diagnosis

    def _summarize_logs(self, logs: str, max_lines: int = 20) -> str:
        """
        总结日志（提取关键信息）

        Args:
            logs: 完整日志
            max_lines: 最大行数

        Returns:
            日志摘要
        """
        lines = logs.split("\n")

        # 提取包含错误、警告或重要信息的行
        important_lines = []
        keywords = ["ERROR", "FATAL", "WARNING", "failed", "error", "cannot", "unable"]

        for line in lines:
            if any(keyword in line for keyword in keywords):
                important_lines.append(line)

        # 如果重要行太少，添加最后几行
        if len(important_lines) < 5:
            important_lines.extend(lines[-10:])

        # 限制行数
        summary_lines = important_lines[-max_lines:]

        return "\n".join(summary_lines)
