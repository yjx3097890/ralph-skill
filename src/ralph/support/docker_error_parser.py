"""
Docker 错误解析器

解析 Docker 构建错误、容器运行时错误和 Compose 错误。
"""

import re
from typing import List, Optional, Dict, Any
import logging

from ralph.models.docker import (
    BuildError,
    DockerError,
    ContainerError,
    NetworkError,
    ErrorContext,
    FixSuggestion,
)

logger = logging.getLogger(__name__)


class DockerErrorParser:
    """Docker 错误解析器"""

    def parse_build_errors(self, output: str) -> List[BuildError]:
        """
        解析构建错误

        Args:
            output: 构建输出

        Returns:
            List[BuildError]: 构建错误列表
        """
        errors = []
        
        # 匹配 Dockerfile 语法错误
        syntax_pattern = r"Dockerfile parse error line (\d+): (.+)"
        for match in re.finditer(syntax_pattern, output, re.MULTILINE):
            line_number = int(match.group(1))
            error_message = match.group(2)
            errors.append(
                BuildError(
                    step_number=line_number,
                    command="",
                    error_message=error_message,
                    error_type="syntax",
                )
            )

        # 匹配构建步骤错误
        step_pattern = r"Step (\d+)/\d+ : (.+)"
        error_pattern = r"ERROR: (.+)"
        
        current_step = 0
        current_command = ""
        
        for line in output.split("\n"):
            step_match = re.match(step_pattern, line)
            if step_match:
                current_step = int(step_match.group(1))
                current_command = step_match.group(2)
            
            error_match = re.match(error_pattern, line)
            if error_match:
                error_message = error_match.group(1)
                error_type = self._classify_build_error(error_message)
                errors.append(
                    BuildError(
                        step_number=current_step,
                        command=current_command,
                        error_message=error_message,
                        error_type=error_type,
                    )
                )

        # 匹配文件未找到错误
        file_not_found_pattern = r"COPY failed: .+: no such file or directory"
        for match in re.finditer(file_not_found_pattern, output, re.MULTILINE):
            errors.append(
                BuildError(
                    step_number=0,
                    command="COPY",
                    error_message=match.group(0),
                    error_type="file_not_found",
                )
            )

        return errors

    def _classify_build_error(self, error_message: str) -> str:
        """
        分类构建错误

        Args:
            error_message: 错误消息

        Returns:
            str: 错误类型
        """
        error_lower = error_message.lower()
        
        if "no such file" in error_lower or "not found" in error_lower:
            return "file_not_found"
        elif "network" in error_lower or "connection" in error_lower:
            return "network"
        elif "permission denied" in error_lower:
            return "permission"
        elif "syntax" in error_lower:
            return "syntax"
        elif "invalid" in error_lower:
            return "invalid_argument"
        else:
            return "unknown"

    def parse_container_errors(self, logs: str) -> List[ContainerError]:
        """
        解析容器运行时错误

        Args:
            logs: 容器日志

        Returns:
            List[ContainerError]: 容器错误列表
        """
        errors = []
        
        # 匹配常见错误模式
        error_patterns = [
            (r"Error: (.+)", "runtime_error"),
            (r"Exception: (.+)", "exception"),
            (r"FATAL: (.+)", "fatal"),
            (r"panic: (.+)", "panic"),
            (r"Segmentation fault", "segfault"),
        ]
        
        for pattern, error_type in error_patterns:
            for match in re.finditer(pattern, logs, re.MULTILINE):
                error_message = match.group(0)
                errors.append(
                    ContainerError(
                        error_type=error_type,
                        error_message=error_message,
                        logs=logs,
                    )
                )

        return errors

    def parse_network_errors(self, output: str) -> List[NetworkError]:
        """
        解析网络错误

        Args:
            output: 错误输出

        Returns:
            List[NetworkError]: 网络错误列表
        """
        errors = []
        
        # 匹配网络相关错误
        network_patterns = [
            (r"network (.+) not found", "network_not_found"),
            (r"endpoint (.+) already exists", "endpoint_exists"),
            (r"address already in use", "address_in_use"),
            (r"could not find an available.*IP address", "no_available_ip"),
        ]
        
        for pattern, error_type in network_patterns:
            for match in re.finditer(pattern, output, re.MULTILINE | re.IGNORECASE):
                error_message = match.group(0)
                network_name = match.group(1) if match.lastindex >= 1 else None
                
                errors.append(
                    NetworkError(
                        error_type=error_type,
                        error_message=error_message,
                        network_name=network_name,
                    )
                )

        return errors

    def identify_failed_step(self, build_output: str) -> int:
        """
        识别失败的构建步骤

        Args:
            build_output: 构建输出

        Returns:
            int: 失败的步骤编号，0 表示未找到
        """
        # 查找最后一个执行的步骤
        step_pattern = r"Step (\d+)/\d+ :"
        matches = list(re.finditer(step_pattern, build_output))
        
        if matches:
            last_step = int(matches[-1].group(1))
            return last_step
        
        return 0

    def extract_error_context(self, error: DockerError, full_output: str) -> ErrorContext:
        """
        提取错误上下文

        Args:
            error: Docker 错误
            full_output: 完整输出

        Returns:
            ErrorContext: 错误上下文
        """
        # 提取相关日志（错误前后各 5 行）
        related_logs = []
        lines = full_output.split("\n")
        
        for i, line in enumerate(lines):
            if error.error_message in line:
                start = max(0, i - 5)
                end = min(len(lines), i + 6)
                related_logs = lines[start:end]
                break

        # 生成修复建议
        suggestions = self.suggest_fix(error)

        return ErrorContext(
            error=error,
            related_logs=related_logs,
            suggestions=suggestions,
        )

    def suggest_fix(self, error: DockerError) -> List[FixSuggestion]:
        """
        生成修复建议

        Args:
            error: Docker 错误

        Returns:
            List[FixSuggestion]: 修复建议列表
        """
        suggestions = []
        error_lower = error.error_message.lower()

        # 文件未找到
        if "no such file" in error_lower or "not found" in error_lower:
            suggestions.append(
                FixSuggestion(
                    description="检查文件路径是否正确，确保文件存在于构建上下文中",
                    priority=10,
                )
            )
            suggestions.append(
                FixSuggestion(
                    description="检查 .dockerignore 文件，确保需要的文件没有被忽略",
                    priority=8,
                )
            )

        # 网络错误
        elif "network" in error_lower or "connection" in error_lower:
            suggestions.append(
                FixSuggestion(
                    description="检查网络连接，确保可以访问外部资源",
                    priority=10,
                )
            )
            suggestions.append(
                FixSuggestion(
                    description="如果在代理环境中，配置 HTTP_PROXY 和 HTTPS_PROXY",
                    command="docker build --build-arg HTTP_PROXY=http://proxy:port ...",
                    priority=8,
                )
            )

        # 权限错误
        elif "permission denied" in error_lower:
            suggestions.append(
                FixSuggestion(
                    description="检查文件权限，确保 Docker 有权限访问",
                    command="chmod +x <file>",
                    priority=10,
                )
            )
            suggestions.append(
                FixSuggestion(
                    description="检查 Docker daemon 是否有足够的权限",
                    priority=8,
                )
            )

        # 端口占用
        elif "address already in use" in error_lower:
            suggestions.append(
                FixSuggestion(
                    description="检查端口是否被其他进程占用",
                    command="lsof -i :<port> 或 netstat -tulpn | grep <port>",
                    priority=10,
                )
            )
            suggestions.append(
                FixSuggestion(
                    description="更改容器使用的端口映射",
                    priority=8,
                )
            )

        # 镜像未找到
        elif "image not found" in error_lower or "pull access denied" in error_lower:
            suggestions.append(
                FixSuggestion(
                    description="检查镜像名称和标签是否正确",
                    priority=10,
                )
            )
            suggestions.append(
                FixSuggestion(
                    description="如果是私有镜像，确保已登录到镜像仓库",
                    command="docker login <registry>",
                    priority=9,
                )
            )

        # 磁盘空间不足
        elif "no space left" in error_lower:
            suggestions.append(
                FixSuggestion(
                    description="清理未使用的 Docker 资源",
                    command="docker system prune -a",
                    priority=10,
                )
            )

        # 默认建议
        if not suggestions:
            suggestions.append(
                FixSuggestion(
                    description="查看完整的错误日志以获取更多信息",
                    priority=5,
                )
            )

        return suggestions

    def prioritize_errors(self, errors: List[DockerError]) -> List[DockerError]:
        """
        对错误按优先级排序

        Args:
            errors: 错误列表

        Returns:
            List[DockerError]: 排序后的错误列表
        """
        # 定义错误类型优先级
        priority_map = {
            "syntax": 10,
            "file_not_found": 9,
            "permission": 8,
            "network": 7,
            "invalid_argument": 6,
            "unknown": 1,
        }

        def get_priority(error: DockerError) -> int:
            return priority_map.get(error.error_type, 0)

        return sorted(errors, key=get_priority, reverse=True)
