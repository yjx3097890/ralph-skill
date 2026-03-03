"""
ACP (Agent Coding Platform) Harness 数据模型

定义 ACP 会话、配置、结果等核心数据结构
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ResourceLimits:
    """资源限制配置"""
    cpu_limit: Optional[float] = None  # CPU 核心数
    memory_limit: Optional[str] = None  # 内存限制，如 "512m", "2g"
    memory_reservation: Optional[str] = None  # 内存预留
    disk_limit: Optional[str] = None  # 磁盘限制
    pids_limit: Optional[int] = None  # 进程数限制


@dataclass
class NetworkPolicy:
    """网络策略配置"""
    allow_internet: bool = False  # 是否允许访问互联网
    allowed_hosts: List[str] = field(default_factory=list)  # 允许访问的主机白名单
    blocked_ports: List[int] = field(default_factory=list)  # 禁止访问的端口黑名单
    use_proxy: bool = False  # 是否使用代理
    allow_privileged: bool = False  # 是否允许特权模式
    allow_host_network: bool = False  # 是否允许主机网络
    allow_host_pid: bool = False  # 是否允许主机 PID 命名空间
    max_file_size_mb: int = 1024  # 最大文件大小（MB）


@dataclass
class GitAuth:
    """Git 认证配置"""
    auth_type: str  # ssh, https, token
    username: Optional[str] = None
    password: Optional[str] = None
    ssh_key: Optional[str] = None
    ssh_key_passphrase: Optional[str] = None
    token: Optional[str] = None


@dataclass
class ProxyConfig:
    """代理配置"""
    http_proxy: Optional[str] = None
    https_proxy: Optional[str] = None
    no_proxy: List[str] = field(default_factory=list)
    proxy_auth: Optional[str] = None


@dataclass
class ACPSessionConfig:
    """ACP 会话配置"""
    name: str  # 会话名称
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)  # 资源限制
    network_policy: NetworkPolicy = field(default_factory=NetworkPolicy)  # 网络策略
    timeout: int = 3600  # 会话超时时间（秒），默认 1 小时
    auto_destroy: bool = True  # 任务完成后自动销毁
    enable_qemu: bool = True  # 启用 QEMU 多架构支持
    enable_buildkit: bool = True  # 启用 Buildkit
    git_auth: Optional[GitAuth] = None  # Git 认证配置
    proxy_config: Optional[ProxyConfig] = None  # 代理配置
    platforms: List[str] = field(default_factory=lambda: ["linux/amd64"])  # 支持的平台


@dataclass
class ACPResourceUsage:
    """ACP 资源使用情况"""
    session_id: str
    timestamp: datetime
    cpu_percent: float  # CPU 使用率
    cpu_limit_cores: float  # CPU 限制（核心数）
    memory_usage_mb: float  # 内存使用（MB）
    memory_limit_mb: float  # 内存限制（MB）
    disk_usage_mb: float  # 磁盘使用（MB）
    disk_limit_mb: float  # 磁盘限制（MB）
    network_rx_bytes: int  # 网络接收字节数
    network_tx_bytes: int  # 网络发送字节数
    container_count: int  # 容器数量


@dataclass
class ACPSession:
    """ACP 会话实例"""
    session_id: str  # 会话唯一 ID
    name: str  # 会话名称
    status: str  # 会话状态：creating, active, idle, destroying, failed
    created_at: datetime  # 创建时间
    last_used_at: datetime  # 最后使用时间
    docker_endpoint: str  # Docker API 端点
    git_endpoint: str  # Git 服务端点
    buildkit_endpoint: str  # Buildkit 端点
    resource_usage: ACPResourceUsage  # 资源使用情况
    config: ACPSessionConfig  # 会话配置
    health_status: str = "healthy"  # 健康状态：healthy, degraded, unhealthy
    operations_count: int = 0  # 操作计数


@dataclass
class ACPSessionStatus:
    """ACP 会话状态"""
    session_id: str
    status: str  # 会话状态
    uptime_seconds: int  # 运行时间（秒）
    operations_count: int  # 操作次数
    resource_usage: ACPResourceUsage  # 资源使用情况
    health_status: str  # 健康状态
    last_error: Optional[str] = None  # 最后错误信息


@dataclass
class ACPSessionInfo:
    """ACP 会话信息（简化版）"""
    session_id: str
    name: str
    status: str
    created_at: datetime
    uptime_seconds: int
    operations_count: int
    resource_usage_percent: float  # 资源使用百分比


@dataclass
class ACPResult:
    """ACP 操作结果基类"""
    success: bool
    session_id: str
    operation_type: str  # build, run, execute, git
    result_data: Dict[str, Any]
    execution_time: float
    resource_usage: ACPResourceUsage
    logs: str
    errors: List[str] = field(default_factory=list)


@dataclass
class LayerInfo:
    """Docker 镜像层信息"""
    layer_id: str
    size_bytes: int
    created_at: datetime
    command: str


@dataclass
class ACPBuildResult(ACPResult):
    """ACP 构建结果"""
    image_id: str = ""
    image_tag: str = ""
    platforms: List[str] = field(default_factory=list)
    build_logs: str = ""
    cache_hits: int = 0
    cache_misses: int = 0
    layers: List[LayerInfo] = field(default_factory=list)


@dataclass
class ACPExecutionResult(ACPResult):
    """ACP 执行结果"""
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    container_id: Optional[str] = None


@dataclass
class ACPGitResult(ACPResult):
    """ACP Git 操作结果"""
    repo_path: str = ""
    branch: str = ""
    commit_hash: Optional[str] = None
    changes: List[str] = field(default_factory=list)


@dataclass
class ACPPerformanceMetrics:
    """ACP 性能指标"""
    session_id: str
    timestamp: datetime
    operations_per_minute: float  # 每分钟操作数
    average_operation_time: float  # 平均操作时间（秒）
    success_rate: float  # 成功率
    error_rate: float  # 错误率
    resource_usage: ACPResourceUsage  # 资源使用情况


@dataclass
class ACPSecurityPolicy:
    """ACP 安全策略"""
    session_id: str
    allow_internet: bool
    allowed_hosts: List[str]
    blocked_ports: List[int]
    allow_privileged: bool = False
    allow_host_network: bool = False
    allow_host_pid: bool = False
    max_file_size_mb: int = 1024


@dataclass
class ACPAuditLog:
    """ACP 审计日志"""
    session_id: str
    timestamp: datetime
    operation_type: str  # 操作类型
    operation_details: Dict[str, Any]  # 操作详情
    user: str  # 执行用户
    success: bool  # 是否成功
    error_message: Optional[str] = None  # 错误信息
    resource_changes: Dict[str, Any] = field(default_factory=dict)  # 资源变更


@dataclass
class ACPError(Exception):
    """ACP 错误异常"""
    type: str  # 错误类型：connection_failed, resource_exhausted, timeout, etc.
    message: str  # 错误消息
    details: Dict[str, Any]  # 错误详情
    recoverable: bool  # 是否可恢复
    session_id: Optional[str] = None  # 会话 ID
    timestamp: datetime = field(default_factory=datetime.now)  # 时间戳

    def __str__(self):
        return f"ACPError({self.type}): {self.message}"


@dataclass
class LogFilter:
    """日志过滤器"""
    start_time: Optional[datetime] = None  # 开始时间
    end_time: Optional[datetime] = None  # 结束时间
    log_level: Optional[str] = None  # 日志级别：debug, info, warning, error
    keywords: List[str] = field(default_factory=list)  # 关键字
    limit: int = 1000  # 限制数量


@dataclass
class LogEntry:
    """日志条目"""
    timestamp: datetime
    level: str  # 日志级别
    message: str  # 日志消息
    session_id: str  # 会话 ID
    operation_type: Optional[str] = None  # 操作类型
    details: Dict[str, Any] = field(default_factory=dict)  # 详情


@dataclass
class CacheConfig:
    """缓存配置"""
    enable_cache: bool = True  # 启用缓存
    cache_from: List[str] = field(default_factory=list)  # 缓存来源
    cache_to: Optional[str] = None  # 缓存目标
    inline_cache: bool = False  # 内联缓存
