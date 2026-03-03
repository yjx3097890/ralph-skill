"""
配置文件解析器

提供配置文件的解析、验证和热重载功能。

## 功能特性

- **多格式支持**: 支持 JSON 和 YAML 格式的配置文件
- **数据验证**: 使用 pydantic 进行配置数据验证
- **错误处理**: 提供详细的错误信息和诊断
- **热重载**: 支持配置文件的监控和自动重载
- **往返一致性**: 确保解析和序列化的一致性

## 使用示例

```python
from ralph.core.config_parser import ConfigParser

# 创建解析器
parser = ConfigParser()

# 解析配置文件
config = parser.parse_config("prd.json")

# 验证配置
result = parser.validate_config(config)
if not result.valid:
    print(f"配置错误: {result.errors}")

# 美化打印配置
formatted = parser.pretty_print(config)
print(formatted)

# 启用热重载
parser.enable_hot_reload("prd.json", callback=on_config_change)
```

## 验证需求

- **需求 9.1**: 解析有效配置文件为 Configuration 对象
- **需求 9.2**: 返回描述性错误信息
- **需求 9.3**: 格式化配置为有效文件
- **需求 9.4**: 往返解析一致性
- **需求 9.5**: 配置文件热重载和验证
"""

import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import yaml
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from ralph.models.config import (
    BackendConfig,
    Configuration,
    DatabaseConfig,
    DockerConfig,
    EngineConfig,
    FrontendConfig,
    ProjectConfig,
    SystemSettings,
    ValidationResult,
)
from ralph.models.enums import (
    BuildTool,
    DependencyManager,
    EngineType,
    FrameworkType,
    ProjectType,
    TestRunner,
)
from ralph.models.task import TaskConfig


class ConfigParseError(Exception):
    """配置解析错误"""
    pass


class ConfigValidationError(Exception):
    """配置验证错误"""
    pass


class ConfigFileWatcher(FileSystemEventHandler):
    """配置文件监控器"""
    
    def __init__(self, config_path: str, callback: Callable[[str], None]):
        """
        初始化配置文件监控器
        
        Args:
            config_path: 配置文件路径
            callback: 文件变更时的回调函数
        """
        self.config_path = Path(config_path).resolve()
        self.callback = callback
        self.last_modified = 0.0
        
    def on_modified(self, event: FileSystemEvent) -> None:
        """
        文件修改事件处理
        
        Args:
            event: 文件系统事件
        """
        if event.is_directory:
            return
            
        event_path = Path(event.src_path).resolve()
        if event_path != self.config_path:
            return
            
        # 防止重复触发（某些编辑器会触发多次修改事件）
        current_time = time.time()
        if current_time - self.last_modified < 1.0:
            return
            
        self.last_modified = current_time
        
        try:
            self.callback(str(self.config_path))
        except Exception as e:
            print(f"配置重载回调执行失败: {e}")


class ConfigParser:
    """
    配置文件解析器
    
    提供配置文件的解析、验证、格式化和热重载功能。
    """
    
    def __init__(self):
        """初始化配置解析器"""
        self._observer: Optional[Observer] = None
        self._watchers: Dict[str, ConfigFileWatcher] = {}
        
    def parse_config(self, config_path: str) -> Configuration:
        """
        解析配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            Configuration: 解析后的配置对象
            
        Raises:
            ConfigParseError: 配置解析失败
            
        验证需求 9.1: 解析有效配置文件为 Configuration 对象
        """
        if not os.path.exists(config_path):
            raise ConfigParseError(f"配置文件不存在: {config_path}")
            
        try:
            # 根据文件扩展名选择解析器
            file_ext = Path(config_path).suffix.lower()
            
            with open(config_path, 'r', encoding='utf-8') as f:
                if file_ext == '.json':
                    data = json.load(f)
                elif file_ext in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                else:
                    raise ConfigParseError(
                        f"不支持的配置文件格式: {file_ext}。"
                        f"支持的格式: .json, .yaml, .yml"
                    )
                    
            # 将字典数据转换为配置对象
            config = self._dict_to_config(data)
            
            # 验证配置
            validation_result = self.validate_config(config)
            if not validation_result.valid:
                error_msg = "配置验证失败:\n" + "\n".join(
                    f"  - {error}" for error in validation_result.errors
                )
                raise ConfigParseError(error_msg)
                
            return config
            
        except json.JSONDecodeError as e:
            raise ConfigParseError(
                f"JSON 解析错误: {e.msg} (行 {e.lineno}, 列 {e.colno})"
            )
        except yaml.YAMLError as e:
            raise ConfigParseError(f"YAML 解析错误: {e}")
        except Exception as e:
            if isinstance(e, ConfigParseError):
                raise
            raise ConfigParseError(f"配置解析失败: {e}")
            
    def validate_config(self, config: Configuration) -> ValidationResult:
        """
        验证配置有效性
        
        Args:
            config: 配置对象
            
        Returns:
            ValidationResult: 验证结果
            
        验证需求 9.2: 返回描述性错误信息
        """
        errors = config.validate()
        warnings = []
        
        # 额外的验证逻辑
        
        # 检查前端配置
        if config.project.frontend:
            frontend = config.project.frontend
            if frontend.e2e_runner and frontend.e2e_runner != TestRunner.PLAYWRIGHT:
                warnings.append(
                    f"E2E 测试运行器 {frontend.e2e_runner} 可能不被完全支持，"
                    f"推荐使用 Playwright"
                )
                
        # 检查后端配置
        if config.project.backend:
            backend = config.project.backend
            if backend.language == "python" and not backend.dependency_manager:
                warnings.append(
                    "Python 项目未指定依赖管理工具，将使用默认的 pip"
                )
            elif backend.language == "go" and not backend.build_system:
                warnings.append(
                    "Go 项目未指定构建系统，将使用默认的 go build"
                )
                
        # 检查数据库配置
        if config.project.database:
            db = config.project.database
            if db.ssl_mode == "disable":
                warnings.append(
                    "数据库连接未启用 SSL，这可能存在安全风险"
                )
                
        # 检查系统设置
        if config.settings.max_context_size < 5000:
            warnings.append(
                f"最大上下文大小 {config.settings.max_context_size} 可能过小，"
                f"推荐至少 10000"
            )
            
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
        
    def pretty_print(self, config: Configuration, format: str = "json") -> str:
        """
        格式化配置对象为字符串
        
        Args:
            config: 配置对象
            format: 输出格式 ("json" 或 "yaml")
            
        Returns:
            str: 格式化后的配置字符串
            
        验证需求 9.3: 格式化配置为有效文件
        """
        # 将配置对象转换为字典
        data = self._config_to_dict(config)
        
        if format.lower() == "json":
            return json.dumps(data, indent=2, ensure_ascii=False)
        elif format.lower() in ["yaml", "yml"]:
            return yaml.dump(
                data,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False
            )
        else:
            raise ValueError(f"不支持的格式: {format}")
            
    def reload_config(self, config_path: str) -> Configuration:
        """
        重新加载配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            Configuration: 重新加载的配置对象
            
        验证需求 9.5: 配置文件热重载
        """
        return self.parse_config(config_path)
        
    def enable_hot_reload(
        self,
        config_path: str,
        callback: Callable[[Configuration], None]
    ) -> None:
        """
        启用配置文件热重载
        
        Args:
            config_path: 配置文件路径
            callback: 配置变更时的回调函数，接收新的配置对象
            
        验证需求 9.5: 配置文件热重载
        """
        config_path = str(Path(config_path).resolve())
        
        # 如果已经在监控，先停止
        if config_path in self._watchers:
            self.disable_hot_reload(config_path)
            
        # 创建回调包装器
        def on_file_change(path: str) -> None:
            try:
                new_config = self.reload_config(path)
                callback(new_config)
            except Exception as e:
                print(f"配置重载失败: {e}")
                
        # 创建文件监控器
        watcher = ConfigFileWatcher(config_path, on_file_change)
        self._watchers[config_path] = watcher
        
        # 启动观察者
        if self._observer is None:
            self._observer = Observer()
            self._observer.start()
            
        # 监控配置文件所在目录
        watch_dir = str(Path(config_path).parent)
        self._observer.schedule(watcher, watch_dir, recursive=False)
        
    def disable_hot_reload(self, config_path: str) -> None:
        """
        禁用配置文件热重载
        
        Args:
            config_path: 配置文件路径
        """
        config_path = str(Path(config_path).resolve())
        
        if config_path in self._watchers:
            del self._watchers[config_path]
            
        # 如果没有监控器了，停止观察者
        if not self._watchers and self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
            
    def stop_all_watchers(self) -> None:
        """停止所有配置文件监控"""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
        self._watchers.clear()
        
    def _dict_to_config(self, data: Dict[str, Any]) -> Configuration:
        """
        将字典转换为配置对象
        
        Args:
            data: 配置字典
            
        Returns:
            Configuration: 配置对象
        """
        # 解析项目配置
        project_data = data.get("project", {})
        project = self._parse_project_config(project_data)
        
        # 解析任务配置
        tasks_data = data.get("tasks", [])
        tasks = [self._parse_task_config(task) for task in tasks_data]
        
        # 解析系统设置
        settings_data = data.get("settings", {})
        settings = self._parse_system_settings(settings_data)
        
        # 解析钩子配置
        hooks = data.get("hooks", {})
        
        # 解析 AI 引擎配置
        engines_data = data.get("ai_engines", {})
        ai_engines = {
            name: self._parse_engine_config(engine_data)
            for name, engine_data in engines_data.items()
        }
        
        return Configuration(
            project=project,
            tasks=tasks,
            settings=settings,
            hooks=hooks,
            ai_engines=ai_engines
        )
        
    def _parse_project_config(self, data: Dict[str, Any]) -> ProjectConfig:
        """解析项目配置"""
        name = data.get("name", "")
        project_type = ProjectType(data.get("type", "fullstack"))
        
        # 解析前端配置
        frontend = None
        if "frontend" in data:
            frontend_data = data["frontend"]
            frontend = FrontendConfig(
                framework=FrameworkType(frontend_data.get("framework", "vue3")),
                test_runner=TestRunner(frontend_data.get("test_runner", "vitest")),
                e2e_runner=TestRunner(frontend_data["e2e_runner"]) 
                    if "e2e_runner" in frontend_data else None,
                build_tool=BuildTool(frontend_data.get("build_tool", "vite")),
                package_manager=DependencyManager(
                    frontend_data.get("package_manager", "npm")
                )
            )
            
        # 解析后端配置
        backend = None
        if "backend" in data:
            backend_data = data["backend"]
            backend = BackendConfig(
                language=backend_data.get("language", "python"),
                framework=FrameworkType(backend_data.get("framework", "none")),
                build_system=BuildTool(backend_data["build_system"]) 
                    if "build_system" in backend_data else None,
                dependency_manager=DependencyManager(backend_data["dependency_manager"])
                    if "dependency_manager" in backend_data else None,
                test_runner=TestRunner(backend_data["test_runner"])
                    if "test_runner" in backend_data else None
            )
            
        # 解析数据库配置
        database = None
        if "database" in data:
            db_data = data["database"]
            database = DatabaseConfig(
                type=db_data.get("type", "postgresql"),
                host=db_data.get("host", "localhost"),
                port=db_data.get("port", 5432),
                database=db_data.get("database", ""),
                user=db_data.get("user", ""),
                password=db_data.get("password", ""),
                ssl_mode=db_data.get("ssl_mode", "prefer"),
                connection_timeout=db_data.get("connection_timeout", 30),
                pool_size=db_data.get("pool_size", 10),
                max_overflow=db_data.get("max_overflow", 20)
            )
            
        # 解析 Docker 配置
        docker = None
        if "docker" in data:
            docker_data = data["docker"]
            docker = DockerConfig(
                has_dockerfile=docker_data.get("has_dockerfile", False),
                has_compose=docker_data.get("has_compose", False),
                dockerfile_path=docker_data.get("dockerfile_path"),
                compose_path=docker_data.get("compose_path"),
                base_image=docker_data.get("base_image"),
                exposed_ports=docker_data.get("exposed_ports", []),
                environment=docker_data.get("environment", {})
            )
            
        return ProjectConfig(
            name=name,
            type=project_type,
            frontend=frontend,
            backend=backend,
            database=database,
            docker=docker
        )
        
    def _parse_task_config(self, data: Dict[str, Any]) -> TaskConfig:
        """解析任务配置"""
        from ralph.models.enums import TaskType
        
        return TaskConfig(
            id=data.get("id", ""),
            name=data.get("name", ""),
            type=TaskType(data.get("type", "feature")),
            depends_on=data.get("depends_on", []),
            ai_engine=data.get("ai_engine", "qwen_code"),
            hooks=data.get("hooks", {}),
            config=data.get("config", {}),
            max_retries=data.get("max_retries", 3),
            timeout=data.get("timeout", 1800)
        )
        
    def _parse_system_settings(self, data: Dict[str, Any]) -> SystemSettings:
        """解析系统设置"""
        return SystemSettings(
            max_context_size=data.get("max_context_size", 10000),
            git_auto_commit=data.get("git_auto_commit", True),
            sandbox_timeout=data.get("sandbox_timeout", 300),
            max_retries=data.get("max_retries", 3),
            log_level=data.get("log_level", "info"),
            enable_hooks=data.get("enable_hooks", True)
        )
        
    def _parse_engine_config(self, data: Dict[str, Any]) -> EngineConfig:
        """解析 AI 引擎配置"""
        # 提取 CLI 相关参数到 extra_params
        extra_params = {}
        if "cli_path" in data:
            extra_params["cli_path"] = data["cli_path"]
        
        return EngineConfig(
            engine_type=EngineType(data.get("type", "qwen_code")),
            model_name=data.get("model"),  # 配置文件中的 model 映射到 model_name
            timeout=data.get("timeout", 60),
            extra_params=extra_params
        )
        
    def _config_to_dict(self, config: Configuration) -> Dict[str, Any]:
        """
        将配置对象转换为字典
        
        Args:
            config: 配置对象
            
        Returns:
            Dict[str, Any]: 配置字典
        """
        result: Dict[str, Any] = {}
        
        # 项目配置
        project_dict: Dict[str, Any] = {
            "name": config.project.name,
            "type": config.project.type.value
        }
        
        if config.project.frontend:
            frontend = config.project.frontend
            project_dict["frontend"] = {
                "framework": frontend.framework.value,
                "test_runner": frontend.test_runner.value,
                "build_tool": frontend.build_tool.value,
                "package_manager": frontend.package_manager.value
            }
            if frontend.e2e_runner:
                project_dict["frontend"]["e2e_runner"] = frontend.e2e_runner.value
                
        if config.project.backend:
            backend = config.project.backend
            backend_dict: Dict[str, Any] = {
                "language": backend.language,
                "framework": backend.framework.value
            }
            if backend.build_system:
                backend_dict["build_system"] = backend.build_system.value
            if backend.dependency_manager:
                backend_dict["dependency_manager"] = backend.dependency_manager.value
            if backend.test_runner:
                backend_dict["test_runner"] = backend.test_runner.value
            project_dict["backend"] = backend_dict
            
        if config.project.database:
            db = config.project.database
            project_dict["database"] = {
                "type": db.type,
                "host": db.host,
                "port": db.port,
                "database": db.database,
                "user": db.user,
                "password": db.password,
                "ssl_mode": db.ssl_mode,
                "connection_timeout": db.connection_timeout,
                "pool_size": db.pool_size,
                "max_overflow": db.max_overflow
            }
            
        if config.project.docker:
            docker = config.project.docker
            project_dict["docker"] = {
                "has_dockerfile": docker.has_dockerfile,
                "has_compose": docker.has_compose,
                "dockerfile_path": docker.dockerfile_path,
                "compose_path": docker.compose_path,
                "base_image": docker.base_image,
                "exposed_ports": docker.exposed_ports,
                "environment": docker.environment
            }
            
        result["project"] = project_dict
        
        # 任务配置
        result["tasks"] = [
            {
                "id": task.id,
                "name": task.name,
                "type": task.type.value,
                "depends_on": task.depends_on,
                "ai_engine": task.ai_engine,
                "hooks": task.hooks,
                "config": task.config,
                "max_retries": task.max_retries,
                "timeout": task.timeout
            }
            for task in config.tasks
        ]
        
        # 系统设置
        result["settings"] = {
            "max_context_size": config.settings.max_context_size,
            "git_auto_commit": config.settings.git_auto_commit,
            "sandbox_timeout": config.settings.sandbox_timeout,
            "max_retries": config.settings.max_retries,
            "log_level": config.settings.log_level,
            "enable_hooks": config.settings.enable_hooks
        }
        
        # 钩子配置
        if config.hooks:
            result["hooks"] = config.hooks
            
        # AI 引擎配置
        if config.ai_engines:
            result["ai_engines"] = {}
            for name, engine in config.ai_engines.items():
                engine_dict = {
                    "type": engine.engine_type.value,
                    "model": engine.model_name,
                    "timeout": engine.timeout
                }
                # 添加 extra_params 中的参数
                if "cli_path" in engine.extra_params:
                    engine_dict["cli_path"] = engine.extra_params["cli_path"]
                result["ai_engines"][name] = engine_dict
            
        return result
