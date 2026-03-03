"""
Docker 容器化管理相关数据模型

包含 Docker 配置、容器信息、构建结果、编排配置等数据结构。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any


# ============================================================================
# Docker 配置相关模型
# ============================================================================

@dataclass
class DockerProjectInfo:
    """Docker 项目配置信息（详细版本）"""
    has_dockerfile: bool
    has_compose: bool
    dockerfile_path: Optional[str] = None
    compose_path: Optional[str] = None
    base_image: Optional[str] = None
    exposed_ports: List[int] = field(default_factory=list)
    volumes: List['VolumeMount'] = field(default_factory=list)
    environment: Dict[str, str] = field(default_factory=dict)


@dataclass
class VolumeMount:
    """数据卷挂载配置"""
    host_path: str
    container_path: str
    mode: str = "rw"  # rw, ro


@dataclass
class ResourceLimits:
    """资源限制配置"""
    cpu_limit: Optional[float] = None  # CPU 核心数
    memory_limit: Optional[str] = None  # 例如: "512m", "2g"
    memory_reservation: Optional[str] = None
    pids_limit: Optional[int] = None


@dataclass
class HealthCheck:
    """健康检查配置"""
    test: str  # 健康检查命令
    interval: int = 30  # 检查间隔（秒）
    timeout: int = 10  # 超时时间（秒）
    retries: int = 3  # 重试次数
    start_period: int = 0  # 启动等待时间（秒）


@dataclass
class ContainerConfig:
    """容器配置"""
    image: str
    name: str
    command: Optional[str] = None
    environment: Dict[str, str] = field(default_factory=dict)
    ports: Dict[int, int] = field(default_factory=dict)  # host_port: container_port
    volumes: List[VolumeMount] = field(default_factory=list)
    network: Optional[str] = None
    resource_limits: Optional[ResourceLimits] = None
    health_check: Optional[HealthCheck] = None
    restart_policy: str = "no"  # no, always, on-failure, unless-stopped


# ============================================================================
# 容器信息相关模型
# ============================================================================

@dataclass
class Container:
    """容器实例"""
    id: str
    name: str
    image: str
    status: str  # created, running, paused, stopped, exited
    created_at: datetime
    ports: Dict[int, int] = field(default_factory=dict)
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class ContainerInfo:
    """容器详细信息"""
    container: Container
    config: ContainerConfig
    state: 'ContainerState'
    network_settings: Dict[str, Any] = field(default_factory=dict)
    mounts: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ContainerState:
    """容器状态"""
    status: str
    running: bool
    paused: bool
    restarting: bool
    oom_killed: bool
    dead: bool
    pid: int
    exit_code: int
    error: str = ""
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


# ============================================================================
# Docker 构建相关模型
# ============================================================================

@dataclass
class BuildConfig:
    """构建配置"""
    context: str
    dockerfile: str
    args: Dict[str, str] = field(default_factory=dict)
    target: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    cache_from: List[str] = field(default_factory=list)
    pull: bool = False
    no_cache: bool = False


@dataclass
class LayerInfo:
    """镜像层信息"""
    id: str
    size_bytes: int
    command: str
    created: datetime


@dataclass
class BuildResult:
    """构建结果"""
    success: bool
    image_id: str
    image_tag: str
    build_time: float
    build_logs: str
    layers: List[LayerInfo] = field(default_factory=list)
    size_bytes: int = 0
    errors: List['BuildError'] = field(default_factory=list)


@dataclass
class BuildError:
    """构建错误"""
    step_number: int
    command: str
    error_message: str
    error_type: str  # syntax, file_not_found, network, etc.


# ============================================================================
# Docker Compose 相关模型
# ============================================================================

@dataclass
class ComposeConfig:
    """Docker Compose 配置"""
    version: str
    services: Dict[str, 'Service'] = field(default_factory=dict)
    networks: Dict[str, 'Network'] = field(default_factory=dict)
    volumes: Dict[str, 'Volume'] = field(default_factory=dict)


@dataclass
class Service:
    """服务配置"""
    name: str
    image: Optional[str] = None
    build: Optional[BuildConfig] = None
    command: Optional[str] = None
    environment: Dict[str, str] = field(default_factory=dict)
    ports: List[str] = field(default_factory=list)
    volumes: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    networks: List[str] = field(default_factory=list)
    health_check: Optional[HealthCheck] = None
    restart: str = "no"


@dataclass
class Network:
    """网络配置"""
    name: str
    driver: str = "bridge"
    external: bool = False
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Volume:
    """数据卷配置"""
    name: str
    driver: str = "local"
    external: bool = False
    options: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# 容器执行相关模型
# ============================================================================

@dataclass
class ExecResult:
    """容器命令执行结果"""
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float


@dataclass
class ResourceUsage:
    """资源使用情况"""
    cpu_percent: float
    memory_usage_mb: float
    memory_limit_mb: float
    network_rx_bytes: int
    network_tx_bytes: int
    block_io_read_bytes: int
    block_io_write_bytes: int


@dataclass
class ContainerTestResult:
    """容器化测试结果"""
    success: bool
    container_id: str
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    resource_usage: Optional[ResourceUsage] = None
    artifacts: List['Artifact'] = field(default_factory=list)


@dataclass
class Artifact:
    """测试产物"""
    name: str
    path: str
    size_bytes: int
    artifact_type: str  # log, report, screenshot, etc.


# ============================================================================
# 容器编排相关模型
# ============================================================================

@dataclass
class ServiceStatus:
    """服务状态"""
    name: str
    status: str  # starting, running, stopping, stopped, failed
    container_id: Optional[str] = None
    health_status: str = "unknown"  # healthy, unhealthy, starting, unknown
    replicas: int = 1
    error: Optional[str] = None


@dataclass
class OrchestrateResult:
    """编排结果"""
    success: bool
    services_started: List[str] = field(default_factory=list)
    services_failed: List[str] = field(default_factory=list)
    total_time: float = 0.0
    errors: List[str] = field(default_factory=list)


@dataclass
class HealthStatus:
    """健康状态"""
    healthy: bool
    status: str  # healthy, unhealthy, starting, none
    failing_streak: int = 0
    log: List[str] = field(default_factory=list)


# ============================================================================
# Docker 错误相关模型
# ============================================================================

@dataclass
class DockerError:
    """Docker 错误"""
    error_type: str
    error_message: str
    container_id: Optional[str] = None
    image: Optional[str] = None
    command: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ContainerError(DockerError):
    """容器错误"""
    exit_code: Optional[int] = None
    logs: str = ""


@dataclass
class NetworkError(DockerError):
    """网络错误"""
    network_name: Optional[str] = None


@dataclass
class ErrorContext:
    """错误上下文"""
    error: DockerError
    related_logs: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class FixSuggestion:
    """修复建议"""
    description: str
    command: Optional[str] = None
    priority: int = 0  # 优先级，数字越大优先级越高
