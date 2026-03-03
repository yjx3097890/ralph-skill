"""
配置相关数据模型

定义系统配置、项目配置、系统设置等模型。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .enums import (
    BuildTool,
    DependencyManager,
    EngineType,
    FrameworkType,
    ProjectType,
    TestRunner,
)
from .task import TaskConfig


@dataclass
class FrontendConfig:
    """前端配置"""
    framework: FrameworkType
    test_runner: TestRunner
    e2e_runner: Optional[TestRunner] = None
    build_tool: BuildTool = BuildTool.VITE
    package_manager: DependencyManager = DependencyManager.NPM


@dataclass
class BackendConfig:
    """后端配置"""
    language: str  # go, python, etc.
    framework: FrameworkType = FrameworkType.NONE
    build_system: Optional[BuildTool] = None
    dependency_manager: Optional[DependencyManager] = None
    test_runner: Optional[TestRunner] = None


@dataclass
class DatabaseConfig:
    """数据库配置"""
    type: str  # postgresql, mysql, redis, etc.
    host: str
    port: int
    database: str
    user: str
    password: str
    ssl_mode: str = "prefer"
    connection_timeout: int = 30
    pool_size: int = 10
    max_overflow: int = 20


@dataclass
class DockerConfig:
    """Docker 配置"""
    has_dockerfile: bool = False
    has_compose: bool = False
    dockerfile_path: Optional[str] = None
    compose_path: Optional[str] = None
    base_image: Optional[str] = None
    exposed_ports: List[int] = field(default_factory=list)
    environment: Dict[str, str] = field(default_factory=dict)


@dataclass
class ProjectConfig:
    """项目配置"""
    name: str
    type: ProjectType
    frontend: Optional[FrontendConfig] = None
    backend: Optional[BackendConfig] = None
    database: Optional[DatabaseConfig] = None
    docker: Optional[DockerConfig] = None


@dataclass
class SystemSettings:
    """系统设置"""
    max_context_size: int = 10000
    git_auto_commit: bool = True
    sandbox_timeout: int = 300
    max_retries: int = 3
    log_level: str = "info"
    enable_hooks: bool = True


@dataclass
class EngineConfig:
    """AI 引擎配置"""
    type: EngineType
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 60


@dataclass
class Configuration:
    """系统配置"""
    project: ProjectConfig
    tasks: List[TaskConfig]
    settings: SystemSettings
    hooks: Dict[str, List[str]] = field(default_factory=dict)
    ai_engines: Dict[str, EngineConfig] = field(default_factory=dict)
    
    def get_task_by_id(self, task_id: str) -> Optional[TaskConfig]:
        """根据 ID 获取任务配置"""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None
    
    def get_engine_config(self, engine_name: str) -> Optional[EngineConfig]:
        """获取 AI 引擎配置"""
        return self.ai_engines.get(engine_name)
    
    def validate(self) -> List[str]:
        """验证配置有效性，返回错误列表"""
        errors = []
        
        # 验证项目配置
        if not self.project.name:
            errors.append("项目名称不能为空")
        
        # 验证任务配置
        task_ids = set()
        for task in self.tasks:
            if not task.id:
                errors.append("任务 ID 不能为空")
            elif task.id in task_ids:
                errors.append(f"重复的任务 ID: {task.id}")
            else:
                task_ids.add(task.id)
            
            # 验证依赖关系
            for dep in task.depends_on:
                if dep not in task_ids and dep not in [t.id for t in self.tasks]:
                    errors.append(f"任务 {task.id} 依赖不存在的任务: {dep}")
        
        # 验证 AI 引擎配置
        for task in self.tasks:
            if task.ai_engine not in self.ai_engines:
                errors.append(f"任务 {task.id} 使用的引擎 {task.ai_engine} 未配置")
        
        return errors


@dataclass
class ValidationResult:
    """配置验证结果"""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
