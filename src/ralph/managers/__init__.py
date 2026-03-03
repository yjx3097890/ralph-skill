"""
管理器模块

提供各种管理器类:
- GitManager: Git 版本控制管理
- ContextManager: 上下文管理和日志截断
- TaskManager: 任务生命周期管理和状态机控制
- HookSystem: 钩子注册和执行管理
- DatabaseManager: 数据库连接生命周期管理
- PostgreSQLClient: PostgreSQL 数据库客户端
- RedisClient: Redis 缓存客户端
- ACPHarnessManager: ACP Harness 会话管理
- ACPSessionManager: ACP 会话配置和监控管理
- ACPDockerClient: ACP Docker-in-Docker 客户端
- ACPGitClient: ACP Git 客户端
- ACPBuildkitClient: ACP Buildkit 客户端
- ACPSecurityManager: ACP 安全管理器
- CostControlManager: 成本控制和预算管理
- BudgetEnforcer: 预算熔断器
- TimeoutController: 全局超时控制器
- DeadLoopDetector: 死循环检测器
"""

from ralph.managers.acp_buildkit_client import ACPBuildkitClient
from ralph.managers.acp_docker_client import ACPDockerClient
from ralph.managers.acp_git_client import ACPGitClient
from ralph.managers.acp_harness_manager import ACPHarnessManager
from ralph.managers.acp_security_manager import ACPSecurityManager
from ralph.managers.acp_session_manager import ACPSessionManager
from ralph.managers.budget_enforcer import BudgetEnforcer, BudgetEvent, CostReport
from ralph.managers.context_manager import ContextManager, TruncationStats
from ralph.managers.cost_control_manager import (
    BudgetConfig,
    BudgetStatus,
    CostControlManager,
    CostRecord,
    LLMPricing,
)
from ralph.managers.database_manager import DatabaseManager
from ralph.managers.dead_loop_detector import (
    CodeChange,
    DeadLoopConfig,
    DeadLoopDetector,
    DeadLoopPattern,
    ErrorOccurrence,
)
from ralph.managers.git_manager import (
    BranchOperationError,
    CommitOperationError,
    GitManager,
    GitManagerError,
    MergeConflictError,
    RepositoryNotFoundError,
)
from ralph.managers.hook_system import (
    HookExecutionError,
    HookSystem,
    HookTimeoutError,
)
from ralph.managers.postgresql_client import PostgreSQLClient, Transaction
from ralph.managers.redis_client import RedisClient
from ralph.managers.task_manager import (
    TaskDependencyError,
    TaskManager,
    TaskNotFoundError,
    TaskStatusTransitionError,
)
from ralph.managers.timeout_controller import (
    TimeoutConfig,
    TimeoutController,
    TimeoutEvent,
)
from ralph.managers.code_index_manager import (
    CodeIndexManager,
    FileIndex,
    IndexStats,
    SymbolInfo,
)
from ralph.managers.call_relationship_analyzer import (
    CallRelationship,
    CallRelationshipAnalyzer,
)
from ralph.managers.context_builder import ContextBuilder
from ralph.managers.module_analyzer import ModuleAnalyzer, ModuleInfo
from ralph.managers.strategy_manager import (
    FailurePattern,
    StrategyExecution,
    StrategyManager,
    StrategyType,
)
from ralph.managers.event_stream_manager import (
    EventStreamManager,
    EventType,
    TaskStartEvent,
    StepUpdateEvent,
    GitCommitEvent,
    TestRunEvent,
    AICallEvent,
    ErrorEvent,
    TaskCompleteEvent,
)

__all__ = [
    "GitManager",
    "GitManagerError",
    "RepositoryNotFoundError",
    "BranchOperationError",
    "CommitOperationError",
    "MergeConflictError",
    "ContextManager",
    "TruncationStats",
    "TaskManager",
    "TaskNotFoundError",
    "TaskStatusTransitionError",
    "TaskDependencyError",
    "HookSystem",
    "HookExecutionError",
    "HookTimeoutError",
    "DatabaseManager",
    "PostgreSQLClient",
    "RedisClient",
    "Transaction",
    "ACPHarnessManager",
    "ACPSessionManager",
    "ACPDockerClient",
    "ACPGitClient",
    "ACPBuildkitClient",
    "ACPSecurityManager",
    "CostControlManager",
    "BudgetConfig",
    "BudgetStatus",
    "CostRecord",
    "LLMPricing",
    "BudgetEnforcer",
    "BudgetEvent",
    "CostReport",
    "TimeoutController",
    "TimeoutConfig",
    "TimeoutEvent",
    "DeadLoopDetector",
    "DeadLoopConfig",
    "DeadLoopPattern",
    "CodeChange",
    "ErrorOccurrence",
    "CodeIndexManager",
    "FileIndex",
    "IndexStats",
    "SymbolInfo",
    "CallRelationshipAnalyzer",
    "CallRelationship",
    "ContextBuilder",
    "ModuleAnalyzer",
    "ModuleInfo",
    "StrategyManager",
    "StrategyType",
    "FailurePattern",
    "StrategyExecution",
    "EventStreamManager",
    "EventType",
    "TaskStartEvent",
    "StepUpdateEvent",
    "GitCommitEvent",
    "TestRunEvent",
    "AICallEvent",
    "ErrorEvent",
    "TaskCompleteEvent",
]
