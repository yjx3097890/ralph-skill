"""
钩子相关数据模型

定义钩子配置、钩子上下文、钩子结果等核心数据类。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .enums import HookType


@dataclass
class HookContext:
    """
    钩子执行上下文
    
    包含钩子执行时需要的所有上下文信息。
    """
    hook_type: HookType
    task_id: str
    task_name: str
    timestamp: datetime
    working_directory: str
    environment: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HookResult:
    """
    钩子执行结果
    
    包含钩子执行的结果信息，包括成功状态、输出、错误等。
    """
    success: bool
    hook_type: HookType
    hook_name: str
    execution_time: float  # 执行时间（秒）
    output: str = ""
    error: Optional[str] = None
    exit_code: int = 0
    modified_files: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        """字符串表示"""
        status = "成功" if self.success else "失败"
        return f"HookResult({self.hook_name}, {status}, {self.execution_time:.2f}s)"


@dataclass
class HookConfig:
    """
    钩子配置
    
    定义单个钩子的配置信息。
    """
    name: str
    hook_type: HookType
    command: str  # 要执行的命令或脚本
    timeout: int = 300  # 超时时间（秒），默认 5 分钟
    max_retries: int = 0  # 最大重试次数，默认不重试
    retry_delay: int = 1  # 重试延迟（秒）
    continue_on_failure: bool = False  # 失败时是否继续执行任务
    working_directory: Optional[str] = None  # 工作目录，None 表示使用项目根目录
    environment: Dict[str, str] = field(default_factory=dict)  # 环境变量
    
    def __post_init__(self):
        """验证配置"""
        if self.timeout <= 0:
            raise ValueError(f"超时时间必须大于 0: {self.timeout}")
        if self.max_retries < 0:
            raise ValueError(f"最大重试次数不能为负数: {self.max_retries}")
        if self.retry_delay < 0:
            raise ValueError(f"重试延迟不能为负数: {self.retry_delay}")


@dataclass
class HookExecutionRecord:
    """
    钩子执行记录
    
    记录钩子的执行历史。
    """
    hook_name: str
    hook_type: HookType
    task_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[HookResult] = None
    retry_count: int = 0
    
    @property
    def duration(self) -> Optional[float]:
        """执行时长（秒）"""
        if self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds()
    
    @property
    def is_completed(self) -> bool:
        """是否已完成"""
        return self.completed_at is not None
    
    @property
    def is_successful(self) -> bool:
        """是否成功"""
        return self.result is not None and self.result.success


# 钩子函数类型定义
HookFunction = Callable[[HookContext], HookResult]

