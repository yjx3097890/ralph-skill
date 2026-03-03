"""
枚举类型定义

定义系统中使用的所有枚举类型，包括：

## 核心枚举
- TaskType: 任务类型（功能开发、Bug修复、重构等）
- TaskStatus: 任务状态（等待、执行中、测试中、完成、失败）
- EngineType: AI 引擎类型（Qwen Code、Aider、Claude、GPT-4）
- HookType: 钩子类型（任务前、测试前、测试后、任务后）
- ErrorCategory: 错误类别（语法错误、编译错误、运行时错误等）

## 项目和框架
- ProjectType: 项目类型（前端、后端、全栈）
- FrameworkType: 框架类型（Vue3、React、Django、Flask、FastAPI、Go等）
- TestRunner: 测试运行器（Vitest、Jest、pytest、Go test、Playwright）
- BuildTool: 构建工具（Vite、Webpack、Rollup、Make）
- DependencyManager: 依赖管理工具（npm、yarn、pnpm、pip、poetry等）

## Python 开发
- VirtualEnvType: Python 虚拟环境类型（venv、virtualenv、conda）
- CodeFormatter: 代码格式化工具（Black、isort、autopep8、Ruff等）

## 数据库
- DatabaseType: 数据库类型（PostgreSQL、MySQL、Redis、MongoDB、SQLite）
- MigrationTool: 数据库迁移工具（Alembic、golang-migrate、Flyway等）
- SSLMode: SSL 连接模式（禁用、允许、优先、必需等）

## Docker 容器
- ContainerStatus: 容器状态（创建、运行、暂停、停止、退出、死亡）
- HealthStatus: 健康状态（健康、不健康、启动中、未知）
- RestartPolicy: 重启策略（不重启、总是、失败时、除非停止）
- NetworkMode: 网络模式（桥接、主机、无网络、容器）
- VolumeMode: 卷挂载模式（读写、只读）

## 策略和事件
- StrategyType: 策略类型（直接编码、诊断模式、Web搜索、增量修复）
- EventType: 事件类型（任务开始、完成、步骤更新、Git提交、测试运行等）
- RecoveryStrategy: 恢复策略（重试、重新创建、跳过、失败）

## ACP Harness
- ACPSessionStatus: ACP 会话状态（创建中、就绪、活跃、空闲、终止中等）
- Architecture: CPU 架构（AMD64、ARM64、ARMv7、i386）
- PlatformType: 平台类型（Linux/AMD64、Linux/ARM64、Windows/AMD64等）
- GitAuthType: Git 认证类型（SSH、HTTPS、Token）
- OperationType: 操作类型（构建、运行、执行、Git、测试、部署）

## 前端测试
- BrowserType: 浏览器类型（Chromium、Firefox、WebKit）
- ScreenshotMode: 截图模式（关闭、开启、仅失败时）
- VideoMode: 视频录制模式（关闭、开启、失败时保留、首次重试时）
- TraceMode: 追踪模式（关闭、开启、失败时保留、首次重试时）

## 其他
- BudgetStatus: 预算状态（安全、警告、危急、超出）
- LogLevel: 日志级别（调试、信息、警告、错误、严重错误）
- LogFormat: 日志格式（JSON、文本、结构化）
- CaptureOutput: 输出捕获模式（不捕获、系统级、文件描述符级）
"""

from enum import Enum


class TaskType(str, Enum):
    """任务类型枚举"""
    FEATURE = "feature"  # 功能开发
    BUGFIX = "bugfix"  # Bug 修复
    REFACTOR = "refactor"  # 代码重构
    TEST = "test"  # 测试编写
    DOCS = "docs"  # 文档编写


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"  # 等待执行
    IN_PROGRESS = "in_progress"  # 执行中
    TESTING = "testing"  # 测试中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败


class EngineType(str, Enum):
    """AI 引擎类型枚举"""
    QWEN_CODE = "qwen_code"  # Qwen Code 引擎
    AIDER = "aider"  # Aider 引擎
    CLAUDE = "claude"  # Claude 引擎
    GPT4 = "gpt4"  # GPT-4 引擎


class HookType(str, Enum):
    """钩子类型枚举"""
    PRE_TASK = "pre-task"  # 任务开始前
    PRE_TEST = "pre-test"  # 测试前
    POST_TEST = "post-test"  # 测试后
    POST_TASK = "post-task"  # 任务完成后


class ErrorCategory(str, Enum):
    """错误类别枚举"""
    SYNTAX_ERROR = "syntax_error"  # 语法错误
    COMPILATION_ERROR = "compilation_error"  # 编译错误
    RUNTIME_ERROR = "runtime_error"  # 运行时错误
    TEST_FAILURE = "test_failure"  # 测试失败
    NETWORK_ERROR = "network_error"  # 网络错误
    PERMISSION_ERROR = "permission_error"  # 权限错误
    UNKNOWN_ERROR = "unknown_error"  # 未知错误


class ProjectType(str, Enum):
    """项目类型枚举"""
    FRONTEND = "frontend"  # 前端项目
    BACKEND = "backend"  # 后端项目
    FULLSTACK = "fullstack"  # 全栈项目


class FrameworkType(str, Enum):
    """框架类型枚举"""
    VUE3 = "vue3"  # Vue 3
    REACT = "react"  # React
    ANGULAR = "angular"  # Angular
    DJANGO = "django"  # Django
    FLASK = "flask"  # Flask
    FASTAPI = "fastapi"  # FastAPI
    GO = "go"  # Go
    NONE = "none"  # 无框架


class TestRunner(str, Enum):
    """测试运行器枚举"""
    VITEST = "vitest"  # Vitest
    JEST = "jest"  # Jest
    PYTEST = "pytest"  # pytest
    GO_TEST = "go_test"  # Go testing
    PLAYWRIGHT = "playwright"  # Playwright E2E


class BuildTool(str, Enum):
    """构建工具枚举"""
    VITE = "vite"  # Vite
    WEBPACK = "webpack"  # Webpack
    ROLLUP = "rollup"  # Rollup
    MAKE = "make"  # Make
    NONE = "none"  # 无构建工具


class DependencyManager(str, Enum):
    """依赖管理工具枚举"""
    NPM = "npm"  # npm
    YARN = "yarn"  # Yarn
    PNPM = "pnpm"  # pnpm
    PIP = "pip"  # pip
    POETRY = "poetry"  # Poetry
    PIPENV = "pipenv"  # Pipenv
    GO_MOD = "go_mod"  # Go modules


class VirtualEnvType(str, Enum):
    """Python 虚拟环境类型枚举"""
    VENV = "venv"  # venv
    VIRTUALENV = "virtualenv"  # virtualenv
    CONDA = "conda"  # conda


class CodeFormatter(str, Enum):
    """代码格式化工具枚举"""
    BLACK = "black"  # Black
    ISORT = "isort"  # isort
    AUTOPEP8 = "autopep8"  # autopep8
    RUFF = "ruff"  # Ruff
    GOFMT = "gofmt"  # gofmt
    PRETTIER = "prettier"  # Prettier
    ESLINT = "eslint"  # ESLint


class DatabaseType(str, Enum):
    """数据库类型枚举"""
    POSTGRESQL = "postgresql"  # PostgreSQL
    MYSQL = "mysql"  # MySQL
    REDIS = "redis"  # Redis
    MONGODB = "mongodb"  # MongoDB
    SQLITE = "sqlite"  # SQLite


class MigrationTool(str, Enum):
    """数据库迁移工具枚举"""
    ALEMBIC = "alembic"  # Alembic (Python)
    GOLANG_MIGRATE = "golang-migrate"  # golang-migrate (Go)
    FLYWAY = "flyway"  # Flyway
    LIQUIBASE = "liquibase"  # Liquibase


class ContainerStatus(str, Enum):
    """容器状态枚举"""
    CREATED = "created"  # 已创建
    RUNNING = "running"  # 运行中
    PAUSED = "paused"  # 已暂停
    STOPPED = "stopped"  # 已停止
    EXITED = "exited"  # 已退出
    DEAD = "dead"  # 已死亡


class HealthStatus(str, Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"  # 健康
    UNHEALTHY = "unhealthy"  # 不健康
    STARTING = "starting"  # 启动中
    UNKNOWN = "unknown"  # 未知


class RestartPolicy(str, Enum):
    """容器重启策略枚举"""
    NO = "no"  # 不重启
    ALWAYS = "always"  # 总是重启
    ON_FAILURE = "on-failure"  # 失败时重启
    UNLESS_STOPPED = "unless-stopped"  # 除非停止


class NetworkMode(str, Enum):
    """网络模式枚举"""
    BRIDGE = "bridge"  # 桥接模式
    HOST = "host"  # 主机模式
    NONE = "none"  # 无网络
    CONTAINER = "container"  # 容器模式


class StrategyType(str, Enum):
    """策略类型枚举"""
    DIRECT_CODING = "direct_coding"  # 直接编码
    DIAGNOSTIC_MODE = "diagnostic_mode"  # 诊断模式
    WEB_SEARCH_MODE = "web_search_mode"  # Web 搜索模式
    INCREMENTAL_FIX = "incremental_fix"  # 增量修复


class EventType(str, Enum):
    """事件类型枚举"""
    TASK_START = "task_start"  # 任务开始
    TASK_COMPLETE = "task_complete"  # 任务完成
    STEP_UPDATE = "step_update"  # 步骤更新
    GIT_COMMIT = "git_commit"  # Git 提交
    TEST_RUN = "test_run"  # 测试运行
    AI_CALL = "ai_call"  # AI 调用
    ERROR = "error"  # 错误
    WARNING = "warning"  # 警告
    INFO = "info"  # 信息


class ACPSessionStatus(str, Enum):
    """ACP 会话状态枚举"""
    CREATING = "creating"  # 创建中
    READY = "ready"  # 就绪
    ACTIVE = "active"  # 活跃
    IDLE = "idle"  # 空闲
    TERMINATING = "terminating"  # 终止中
    TERMINATED = "terminated"  # 已终止
    FAILED = "failed"  # 失败


class Architecture(str, Enum):
    """CPU 架构枚举"""
    AMD64 = "amd64"  # x86_64
    ARM64 = "arm64"  # ARM 64-bit
    ARMV7 = "armv7"  # ARM 32-bit
    I386 = "i386"  # x86 32-bit


class BudgetStatus(str, Enum):
    """预算状态枚举"""
    SAFE = "safe"  # 安全
    WARNING = "warning"  # 警告
    CRITICAL = "critical"  # 危急
    EXCEEDED = "exceeded"  # 超出


class LogLevel(str, Enum):
    """日志级别枚举"""
    DEBUG = "debug"  # 调试
    INFO = "info"  # 信息
    WARNING = "warning"  # 警告
    ERROR = "error"  # 错误
    CRITICAL = "critical"  # 严重错误


class GitAuthType(str, Enum):
    """Git 认证类型枚举"""
    SSH = "ssh"  # SSH 密钥
    HTTPS = "https"  # HTTPS 用户名密码
    TOKEN = "token"  # 访问令牌


class ScreenshotMode(str, Enum):
    """截图模式枚举"""
    OFF = "off"  # 关闭
    ON = "on"  # 开启
    ONLY_ON_FAILURE = "only-on-failure"  # 仅失败时


class VideoMode(str, Enum):
    """视频录制模式枚举"""
    OFF = "off"  # 关闭
    ON = "on"  # 开启
    RETAIN_ON_FAILURE = "retain-on-failure"  # 失败时保留
    ON_FIRST_RETRY = "on-first-retry"  # 首次重试时


class TraceMode(str, Enum):
    """追踪模式枚举"""
    OFF = "off"  # 关闭
    ON = "on"  # 开启
    RETAIN_ON_FAILURE = "retain-on-failure"  # 失败时保留
    ON_FIRST_RETRY = "on-first-retry"  # 首次重试时


class BrowserType(str, Enum):
    """浏览器类型枚举"""
    CHROMIUM = "chromium"  # Chromium
    FIREFOX = "firefox"  # Firefox
    WEBKIT = "webkit"  # WebKit (Safari)


class SSLMode(str, Enum):
    """SSL 模式枚举"""
    DISABLE = "disable"  # 禁用
    ALLOW = "allow"  # 允许
    PREFER = "prefer"  # 优先
    REQUIRE = "require"  # 必需
    VERIFY_CA = "verify-ca"  # 验证 CA
    VERIFY_FULL = "verify-full"  # 完全验证


class CaptureOutput(str, Enum):
    """输出捕获模式枚举"""
    NO = "no"  # 不捕获
    SYS = "sys"  # 系统级捕获
    FD = "fd"  # 文件描述符级捕获


class VolumeMode(str, Enum):
    """卷挂载模式枚举"""
    RW = "rw"  # 读写
    RO = "ro"  # 只读


class LogFormat(str, Enum):
    """日志格式枚举"""
    JSON = "json"  # JSON 格式
    TEXT = "text"  # 文本格式
    STRUCTURED = "structured"  # 结构化格式


class OperationType(str, Enum):
    """操作类型枚举"""
    BUILD = "build"  # 构建
    RUN = "run"  # 运行
    EXECUTE = "execute"  # 执行
    GIT = "git"  # Git 操作
    TEST = "test"  # 测试
    DEPLOY = "deploy"  # 部署


class RecoveryStrategy(str, Enum):
    """恢复策略枚举"""
    RETRY = "retry"  # 重试
    RECREATE = "recreate"  # 重新创建
    SKIP = "skip"  # 跳过
    FAIL = "fail"  # 失败


class PlatformType(str, Enum):
    """平台类型枚举"""
    LINUX_AMD64 = "linux/amd64"  # Linux AMD64
    LINUX_ARM64 = "linux/arm64"  # Linux ARM64
    LINUX_ARMV7 = "linux/arm/v7"  # Linux ARMv7
    WINDOWS_AMD64 = "windows/amd64"  # Windows AMD64
    DARWIN_AMD64 = "darwin/amd64"  # macOS AMD64
    DARWIN_ARM64 = "darwin/arm64"  # macOS ARM64


class ErrorPriority(str, Enum):
    """错误优先级枚举"""
    FATAL = "fatal"  # 致命错误 - 最高优先级
    CRITICAL = "critical"  # 严重错误 - 最高优先级
    ERROR = "error"  # 错误 - 高优先级
    WARNING = "warning"  # 警告 - 中优先级
    INFO = "info"  # 信息 - 低优先级
