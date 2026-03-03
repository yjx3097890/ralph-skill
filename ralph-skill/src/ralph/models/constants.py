"""
系统常量定义

定义系统中使用的所有常量值，包括超时时间、重试次数、默认配置等。

## 常量分类

### 任务执行相关
- 任务超时时间和重试次数
- 任务状态检查间隔

### 上下文管理相关
- 上下文大小限制
- 截断策略配置
- 错误优先级权重

### Git 管理相关
- WIP 分支命名规则
- Git 操作超时配置

### 钩子系统相关
- 钩子超时和重试配置

### AI 引擎相关
- AI 引擎超时和重试配置
- 默认引擎选择

### 安全沙箱相关
- 资源限制配置
- 网络访问白名单

### 测试执行相关
- 测试超时和重试配置
- 覆盖率阈值

### Docker 容器相关
- 容器启动和健康检查配置
- 资源限制默认值

### 数据库相关
- 数据库连接配置
- 连接池配置

### 成本控制相关
- Token 预算配置
- LLM 模型定价

### 代码索引相关
- 索引更新间隔
- 排除目录和文件

### 策略管理相关
- 策略切换阈值
- 各策略超时配置

### 事件流相关
- 事件缓冲和批处理配置

### ACP Harness 相关
- ACP 会话配置
- 资源监控配置

### 文件和路径相关
- 临时文件和日志目录
- 文件大小和保留配置

### 网络相关
- HTTP 请求配置
- WebSocket 和 SSE 配置

### 其他
- 系统版本和名称
- 编码和时间格式
"""

# ============================================================================
# 任务执行相关常量
# ============================================================================

# 默认任务超时时间（秒）
DEFAULT_TASK_TIMEOUT = 1800  # 30 分钟

# 默认全局超时时间（秒）
DEFAULT_GLOBAL_TIMEOUT = 3600  # 60 分钟

# 最大任务重试次数
MAX_TASK_RETRIES = 3

# 任务状态检查间隔（秒）
TASK_STATUS_CHECK_INTERVAL = 5

# ============================================================================
# 上下文管理相关常量
# ============================================================================

# 默认最大上下文大小（字符）
DEFAULT_MAX_CONTEXT_SIZE = 10000

# 上下文截断保留前部字符数
CONTEXT_TRUNCATE_HEAD_SIZE = 2000

# 上下文截断保留尾部字符数
CONTEXT_TRUNCATE_TAIL_SIZE = 2000

# 错误信息优先级权重
ERROR_PRIORITY_WEIGHTS = {
    "syntax_error": 10,
    "compilation_error": 9,
    "runtime_error": 8,
    "test_failure": 7,
    "network_error": 5,
    "permission_error": 6,
    "unknown_error": 1,
}

# ============================================================================
# Git 管理相关常量
# ============================================================================

# WIP 分支名称前缀
WIP_BRANCH_PREFIX = "wip"

# Git 提交消息最大长度
MAX_COMMIT_MESSAGE_LENGTH = 500

# Git 操作超时时间（秒）
GIT_OPERATION_TIMEOUT = 300  # 5 分钟

# ============================================================================
# 钩子系统相关常量
# ============================================================================

# 默认钩子超时时间（秒）
DEFAULT_HOOK_TIMEOUT = 60

# 钩子最大重试次数
MAX_HOOK_RETRIES = 2

# 钩子执行间隔（秒）
HOOK_EXECUTION_INTERVAL = 1

# ============================================================================
# AI 引擎相关常量
# ============================================================================

# AI 引擎调用超时时间（秒）
AI_ENGINE_TIMEOUT = 300  # 5 分钟

# AI 引擎最大重试次数
MAX_AI_ENGINE_RETRIES = 3

# AI 引擎重试间隔（秒）
AI_ENGINE_RETRY_INTERVAL = 5

# 默认 AI 引擎
DEFAULT_AI_ENGINE = "qwen_code"

# ============================================================================
# 安全沙箱相关常量
# ============================================================================

# 沙箱执行超时时间（秒）
SANDBOX_EXECUTION_TIMEOUT = 300  # 5 分钟

# 沙箱最大 CPU 使用率（百分比）
SANDBOX_MAX_CPU_PERCENT = 80

# 沙箱最大内存使用（MB）
SANDBOX_MAX_MEMORY_MB = 2048

# 沙箱最大磁盘使用（MB）
SANDBOX_MAX_DISK_MB = 5120

# 沙箱网络访问白名单
SANDBOX_NETWORK_WHITELIST = [
    "github.com",
    "gitlab.com",
    "pypi.org",
    "npmjs.com",
    "registry.npmjs.org",
]

# ============================================================================
# 测试执行相关常量
# ============================================================================

# 默认测试超时时间（秒）
DEFAULT_TEST_TIMEOUT = 300  # 5 分钟

# 测试最大重试次数
MAX_TEST_RETRIES = 2

# 测试覆盖率阈值（百分比）
DEFAULT_COVERAGE_THRESHOLD = 80.0

# Pytest 默认并行工作进程数
DEFAULT_PYTEST_WORKERS = 4

# ============================================================================
# Docker 容器相关常量
# ============================================================================

# 容器启动超时时间（秒）
CONTAINER_START_TIMEOUT = 60

# 容器健康检查超时时间（秒）
CONTAINER_HEALTH_CHECK_TIMEOUT = 60

# 容器健康检查间隔（秒）
CONTAINER_HEALTH_CHECK_INTERVAL = 5

# 容器健康检查重试次数
CONTAINER_HEALTH_CHECK_RETRIES = 12

# 容器停止超时时间（秒）
CONTAINER_STOP_TIMEOUT = 10

# 默认容器 CPU 限制（核心数）
DEFAULT_CONTAINER_CPU_LIMIT = 2.0

# 默认容器内存限制（MB）
DEFAULT_CONTAINER_MEMORY_LIMIT = 1024

# Docker 构建超时时间（秒）
DOCKER_BUILD_TIMEOUT = 600  # 10 分钟

# ============================================================================
# 数据库相关常量
# ============================================================================

# PostgreSQL 默认端口
POSTGRESQL_DEFAULT_PORT = 5432

# Redis 默认端口
REDIS_DEFAULT_PORT = 6379

# 数据库连接超时时间（秒）
DATABASE_CONNECTION_TIMEOUT = 30

# 数据库查询超时时间（秒）
DATABASE_QUERY_TIMEOUT = 60

# 数据库连接池大小
DATABASE_POOL_SIZE = 10

# 数据库连接池最大溢出
DATABASE_MAX_OVERFLOW = 20

# Redis 最大连接数
REDIS_MAX_CONNECTIONS = 50

# 数据库健康检查间隔（秒）
DATABASE_HEALTH_CHECK_INTERVAL = 30

# ============================================================================
# 成本控制相关常量
# ============================================================================

# 默认最大 Token 预算（美元）
DEFAULT_MAX_TOKENS_BUDGET = 5.0

# 预算警告阈值（百分比）
BUDGET_WARNING_THRESHOLD = 90

# 预算熔断阈值（百分比）
BUDGET_CIRCUIT_BREAKER_THRESHOLD = 100

# 死循环检测阈值（连续相同操作次数）
DEAD_LOOP_DETECTION_THRESHOLD = 3

# LLM 模型定价（美元/1000 tokens）
LLM_MODEL_PRICING = {
    "qwen_code": {"input": 0.0002, "output": 0.0006},
    "gpt4": {"input": 0.03, "output": 0.06},
    "claude": {"input": 0.008, "output": 0.024},
    "aider": {"input": 0.0002, "output": 0.0006},
}

# ============================================================================
# 代码索引相关常量
# ============================================================================

# 符号表更新间隔（秒）
SYMBOL_TABLE_UPDATE_INTERVAL = 60

# 最大索引文件数量
MAX_INDEXED_FILES = 10000

# 索引排除目录
INDEX_EXCLUDE_DIRS = [
    ".git",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "venv",
    "env",
    ".venv",
    "dist",
    "build",
    "target",
]

# 索引排除文件扩展名
INDEX_EXCLUDE_EXTENSIONS = [
    ".pyc",
    ".pyo",
    ".so",
    ".dll",
    ".exe",
    ".bin",
    ".log",
    ".tmp",
]

# 调用关系分析最大深度
MAX_CALL_DEPTH = 5

# ============================================================================
# 策略管理相关常量
# ============================================================================

# 策略切换失败阈值（连续失败次数）
STRATEGY_SWITCH_THRESHOLD = 3

# 最大策略尝试次数
MAX_STRATEGY_ATTEMPTS = 3

# 诊断模式超时时间（秒）
DIAGNOSTIC_MODE_TIMEOUT = 600  # 10 分钟

# Web 搜索最大结果数
WEB_SEARCH_MAX_RESULTS = 5

# 增量修复最大步骤数
INCREMENTAL_FIX_MAX_STEPS = 10

# ============================================================================
# 事件流相关常量
# ============================================================================

# 事件缓冲区大小
EVENT_BUFFER_SIZE = 100

# 事件批处理大小
EVENT_BATCH_SIZE = 10

# 事件流刷新间隔（秒）
EVENT_STREAM_FLUSH_INTERVAL = 1

# 进度估算窗口大小（任务数）
PROGRESS_ESTIMATION_WINDOW = 10

# ============================================================================
# ACP Harness 相关常量
# ============================================================================

# ACP 会话创建超时时间（秒）
ACP_SESSION_CREATE_TIMEOUT = 120

# ACP 会话空闲超时时间（秒）
ACP_SESSION_IDLE_TIMEOUT = 1800  # 30 分钟

# ACP 会话最大生命周期（秒）
ACP_SESSION_MAX_LIFETIME = 7200  # 2 小时

# ACP 会话最大并发数
ACP_MAX_CONCURRENT_SESSIONS = 10

# ACP Docker-in-Docker 超时时间（秒）
ACP_DIND_TIMEOUT = 600  # 10 分钟

# ACP Buildkit 构建超时时间（秒）
ACP_BUILDKIT_TIMEOUT = 1200  # 20 分钟

# ACP Git 操作超时时间（秒）
ACP_GIT_TIMEOUT = 300  # 5 分钟

# ACP 资源监控间隔（秒）
ACP_RESOURCE_MONITOR_INTERVAL = 10

# ACP 日志保留时间（秒）
ACP_LOG_RETENTION_TIME = 86400  # 24 小时

# ============================================================================
# 文件和路径相关常量
# ============================================================================

# 临时文件目录
TEMP_DIR = "/tmp/ralph"

# 日志文件目录
LOG_DIR = "/var/log/ralph"

# 配置文件默认路径
DEFAULT_CONFIG_PATH = "prd.json"

# 最大日志文件大小（MB）
MAX_LOG_FILE_SIZE = 100

# 日志文件保留数量
LOG_FILE_RETENTION_COUNT = 10

# ============================================================================
# 网络相关常量
# ============================================================================

# HTTP 请求超时时间（秒）
HTTP_REQUEST_TIMEOUT = 30

# HTTP 最大重试次数
HTTP_MAX_RETRIES = 3

# HTTP 重试间隔（秒）
HTTP_RETRY_INTERVAL = 2

# WebSocket 心跳间隔（秒）
WEBSOCKET_HEARTBEAT_INTERVAL = 30

# Server-Sent Events 重连间隔（秒）
SSE_RECONNECT_INTERVAL = 5

# ============================================================================
# Playwright E2E 测试相关常量
# ============================================================================

# Playwright 默认超时时间（毫秒）
PLAYWRIGHT_DEFAULT_TIMEOUT = 30000

# Playwright 默认重试次数
PLAYWRIGHT_DEFAULT_RETRIES = 2

# Playwright 默认浏览器
PLAYWRIGHT_DEFAULT_BROWSERS = ["chromium", "firefox", "webkit"]

# Playwright 默认截图模式
PLAYWRIGHT_DEFAULT_SCREENSHOT_MODE = "only-on-failure"

# Playwright 默认视频模式
PLAYWRIGHT_DEFAULT_VIDEO_MODE = "retain-on-failure"

# Playwright 默认追踪模式
PLAYWRIGHT_DEFAULT_TRACE_MODE = "on-first-retry"

# Playwright 测试结果目录
PLAYWRIGHT_OUTPUT_DIR = "test-results"

# Playwright 测试目录
PLAYWRIGHT_TEST_DIR = "tests/e2e"

# ============================================================================
# 前端开发相关常量
# ============================================================================

# 前端开发服务器默认端口
FRONTEND_DEV_SERVER_PORT = 3000

# 前端构建超时时间（秒）
FRONTEND_BUILD_TIMEOUT = 600  # 10 分钟

# 前端热重载延迟（毫秒）
FRONTEND_HMR_DELAY = 200

# ============================================================================
# 后端开发相关常量
# ============================================================================

# Go 测试超时时间（秒）
GO_TEST_TIMEOUT = 300  # 5 分钟

# Go 构建超时时间（秒）
GO_BUILD_TIMEOUT = 300  # 5 分钟

# Python 虚拟环境创建超时时间（秒）
PYTHON_VENV_CREATE_TIMEOUT = 120  # 2 分钟

# Python 依赖安装超时时间（秒）
PYTHON_DEPENDENCY_INSTALL_TIMEOUT = 600  # 10 分钟

# ============================================================================
# 代码格式化相关常量
# ============================================================================

# Black 行长度限制
BLACK_LINE_LENGTH = 88

# isort 行长度限制
ISORT_LINE_LENGTH = 88

# Prettier 行长度限制
PRETTIER_PRINT_WIDTH = 80

# ESLint 最大行长度
ESLINT_MAX_LINE_LENGTH = 100

# ============================================================================
# 符号表和索引相关常量
# ============================================================================

# 符号表缓存过期时间（秒）
SYMBOL_TABLE_CACHE_EXPIRY = 300  # 5 分钟

# 调用图缓存大小
CALL_GRAPH_CACHE_SIZE = 1000

# 文件树缓存过期时间（秒）
FILE_TREE_CACHE_EXPIRY = 60

# 模块依赖图最大节点数
MAX_MODULE_GRAPH_NODES = 5000

# ============================================================================
# 策略执行相关常量
# ============================================================================

# 直接编码模式超时时间（秒）
DIRECT_CODING_TIMEOUT = 300  # 5 分钟

# Web 搜索超时时间（秒）
WEB_SEARCH_TIMEOUT = 30

# Web 搜索结果缓存时间（秒）
WEB_SEARCH_CACHE_EXPIRY = 3600  # 1 小时

# 增量修复步骤间隔（秒）
INCREMENTAL_FIX_STEP_INTERVAL = 5

# ============================================================================
# 进度估算相关常量
# ============================================================================

# 进度更新间隔（秒）
PROGRESS_UPDATE_INTERVAL = 5

# 平均耗时计算窗口大小
AVERAGE_TIME_WINDOW_SIZE = 10

# 进度估算最小样本数
MIN_PROGRESS_SAMPLES = 3

# ============================================================================
# 审计和日志相关常量
# ============================================================================

# 审计日志保留时间（天）
AUDIT_LOG_RETENTION_DAYS = 90

# 操作日志保留时间（天）
OPERATION_LOG_RETENTION_DAYS = 30

# 性能指标采样间隔（秒）
PERFORMANCE_METRICS_SAMPLE_INTERVAL = 10

# 性能指标聚合窗口（秒）
PERFORMANCE_METRICS_AGGREGATION_WINDOW = 60

# ============================================================================
# 安全策略相关常量
# ============================================================================

# 允许的最大文件上传大小（MB）
MAX_FILE_UPLOAD_SIZE = 100

# 允许的最大请求体大小（MB）
MAX_REQUEST_BODY_SIZE = 10

# API 速率限制（请求/分钟）
API_RATE_LIMIT = 60

# 会话超时时间（秒）
SESSION_TIMEOUT = 3600  # 1 小时

# 密码最小长度
MIN_PASSWORD_LENGTH = 8

# ============================================================================
# 缓存相关常量
# ============================================================================

# 默认缓存过期时间（秒）
DEFAULT_CACHE_EXPIRY = 300  # 5 分钟

# 构建缓存过期时间（秒）
BUILD_CACHE_EXPIRY = 86400  # 24 小时

# 测试结果缓存过期时间（秒）
TEST_RESULT_CACHE_EXPIRY = 3600  # 1 小时

# 符号表缓存最大条目数
SYMBOL_TABLE_CACHE_MAX_ENTRIES = 10000

# ============================================================================
# 并发和并行相关常量
# ============================================================================

# 默认工作线程数
DEFAULT_WORKER_THREADS = 4

# 最大并发任务数
MAX_CONCURRENT_TASKS = 10

# 任务队列最大长度
TASK_QUEUE_MAX_LENGTH = 100

# 线程池空闲超时时间（秒）
THREAD_POOL_IDLE_TIMEOUT = 60

# ============================================================================
# 资源监控相关常量
# ============================================================================

# CPU 使用率警告阈值（百分比）
CPU_USAGE_WARNING_THRESHOLD = 80

# 内存使用率警告阈值（百分比）
MEMORY_USAGE_WARNING_THRESHOLD = 85

# 磁盘使用率警告阈值（百分比）
DISK_USAGE_WARNING_THRESHOLD = 90

# 资源监控采样间隔（秒）
RESOURCE_MONITOR_SAMPLE_INTERVAL = 5

# ============================================================================
# 错误处理相关常量
# ============================================================================

# 错误重试最大延迟（秒）
MAX_RETRY_DELAY = 60

# 错误重试指数退避基数
RETRY_BACKOFF_BASE = 2

# 错误重试抖动范围（百分比）
RETRY_JITTER_RANGE = 10

# 错误堆栈跟踪最大深度
MAX_STACK_TRACE_DEPTH = 20

# ============================================================================
# 其他常量
# ============================================================================

# 系统版本
RALPH_VERSION = "1.0.0"

# 系统名称
RALPH_NAME = "Ralph Skill Enterprise Autonomous Engine"

# 默认编码
DEFAULT_ENCODING = "utf-8"

# 时间戳格式
TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"

# 日期时间格式
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# ISO 8601 日期时间格式
ISO_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

# UUID 版本
UUID_VERSION = 4

# 默认语言
DEFAULT_LANGUAGE = "zh-CN"

# 支持的语言列表
SUPPORTED_LANGUAGES = ["zh-CN", "en-US"]

# 默认时区
DEFAULT_TIMEZONE = "Asia/Shanghai"
