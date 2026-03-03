"""
执行相关数据模型

定义执行结果、错误信息、资源使用等数据结构。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .enums import ErrorCategory, ErrorPriority


@dataclass
class ErrorInfo:
    """
    错误信息
    
    存储从日志输出中提取的错误信息,包括错误类型、消息、位置、
    堆栈跟踪和优先级等。
    
    验证需求 2.2: 实现错误信息识别和提取
    验证需求 2.4: 支持多种编程语言的错误格式
    验证需求 2.5: 提供错误优先级排序
    """
    type: ErrorCategory
    message: str
    priority: ErrorPriority = ErrorPriority.ERROR
    file: Optional[str] = None
    line: Optional[int] = None
    column: Optional[int] = None
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __str__(self) -> str:
        """格式化错误信息"""
        location = ""
        if self.file:
            location = f" at {self.file}"
            if self.line:
                location += f":{self.line}"
                if self.column:
                    location += f":{self.column}"
        return f"[{self.priority.value.upper()}] [{self.type.value}] {self.message}{location}"
    
    def get_priority_value(self) -> int:
        """
        获取优先级数值(用于排序)
        
        Returns:
            int: 优先级数值,数值越大优先级越高
        """
        priority_map = {
            ErrorPriority.FATAL: 5,
            ErrorPriority.CRITICAL: 5,
            ErrorPriority.ERROR: 4,
            ErrorPriority.WARNING: 3,
            ErrorPriority.INFO: 2,
        }
        return priority_map.get(self.priority, 0)


@dataclass
class ResourceUsage:
    """资源使用情况"""
    cpu_percent: float = 0.0
    memory_usage_mb: float = 0.0
    memory_limit_mb: float = 0.0
    disk_usage_mb: float = 0.0
    network_rx_bytes: int = 0
    network_tx_bytes: int = 0
    execution_time: float = 0.0
    
    def get_memory_percent(self) -> float:
        """获取内存使用百分比"""
        if self.memory_limit_mb > 0:
            return (self.memory_usage_mb / self.memory_limit_mb) * 100
        return 0.0


@dataclass
class SecurityViolation:
    """安全违规"""
    type: str  # file_access, network_access, system_call, etc.
    message: str  # 违规描述信息
    severity: str  # low, medium, high, critical
    timestamp: datetime = field(default_factory=datetime.now)
    blocked: bool = True
    details: Dict[str, Any] = field(default_factory=dict)  # 额外的详细信息


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    output: str
    errors: List[ErrorInfo] = field(default_factory=list)
    execution_time: float = 0.0
    resource_usage: Optional[ResourceUsage] = None
    security_violations: List[SecurityViolation] = field(default_factory=list)
    exit_code: int = 0
    
    def add_error(self, error: ErrorInfo) -> None:
        """添加错误信息"""
        self.errors.append(error)
        self.success = False
    
    def has_errors(self) -> bool:
        """是否有错误"""
        return len(self.errors) > 0
    
    def get_error_summary(self) -> str:
        """获取错误摘要"""
        if not self.errors:
            return "无错误"
        
        error_counts = {}
        for error in self.errors:
            error_type = error.type.value
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        summary_parts = [f"{count} 个 {error_type}" for error_type, count in error_counts.items()]
        return ", ".join(summary_parts)


@dataclass
class TestResult:
    """测试结果"""
    success: bool
    test_type: str  # unit, integration, e2e
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    execution_time: float
    coverage: Optional[float] = None
    failed_test_details: List[Dict[str, Any]] = field(default_factory=list)
    output: str = ""
    
    def get_pass_rate(self) -> float:
        """获取测试通过率"""
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100


@dataclass
class BuildResult:
    """构建结果"""
    success: bool
    build_time: float
    output: str
    errors: List[ErrorInfo] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)
    
    def has_warnings(self) -> bool:
        """是否有警告"""
        return len(self.warnings) > 0


@dataclass
class GitCommit:
    """Git 提交信息"""
    hash: str
    message: str
    author: str
    timestamp: datetime
    files_changed: List[str] = field(default_factory=list)
    
    def __str__(self) -> str:
        """格式化提交信息"""
        return f"{self.hash[:7]} - {self.message}"


@dataclass
class BranchStatus:
    """分支状态"""
    name: str
    current: bool
    commits_ahead: int = 0
    commits_behind: int = 0
    has_uncommitted_changes: bool = False
    last_commit: Optional[GitCommit] = None


@dataclass
class ContextStats:
    """上下文统计信息"""
    total_size: int
    truncated: bool
    truncated_size: int = 0
    error_count: int = 0
    warning_count: int = 0
    preserved_errors: int = 0
