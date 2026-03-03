"""
配置模型单元测试
"""

import pytest

from ralph.models import (
    BackendConfig,
    BuildTool,
    Configuration,
    DatabaseConfig,
    DependencyManager,
    DockerConfig,
    EngineConfig,
    EngineType,
    FrameworkType,
    FrontendConfig,
    ProjectConfig,
    ProjectType,
    SystemSettings,
    TaskConfig,
    TaskType,
    TestRunner,
    ValidationResult,
)


class TestFrontendConfig:
    """测试前端配置"""

    def test_create_frontend_config(self):
        """测试创建前端配置"""
        config = FrontendConfig(
            framework=FrameworkType.VUE3,
            test_runner=TestRunner.VITEST,
            e2e_runner=TestRunner.PLAYWRIGHT,
            build_tool=BuildTool.VITE,
            package_manager=DependencyManager.NPM
        )
        
        assert config.framework == FrameworkType.VUE3
        assert config.test_runner == TestRunner.VITEST
        assert config.e2e_runner == TestRunner.PLAYWRIGHT
        assert config.build_tool == BuildTool.VITE


class TestBackendConfig:
    """测试后端配置"""

    def test_create_backend_config(self):
        """测试创建后端配置"""
        config = BackendConfig(
            language="go",
            framework=FrameworkType.NONE,
            build_system=BuildTool.MAKE,
            test_runner=TestRunner.GO_TEST
        )
        
        assert config.language == "go"
        assert config.framework == FrameworkType.NONE
        assert config.build_system == BuildTool.MAKE


class TestDatabaseConfig:
    """测试数据库配置"""

    def test_create_database_config(self):
        """测试创建数据库配置"""
        config = DatabaseConfig(
            type="postgresql",
            host="localhost",
            port=5432,
            database="testdb",
            user="testuser",
            password="testpass"
        )
        
        assert config.type == "postgresql"
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.ssl_mode == "prefer"
        assert config.pool_size == 10


class TestDockerConfig:
    """测试 Docker 配置"""

    def test_create_docker_config(self):
        """测试创建 Docker 配置"""
        config = DockerConfig(
            has_dockerfile=True,
            has_compose=True,
            dockerfile_path="./Dockerfile",
            compose_path="./docker-compose.yml",
            base_image="python:3.9",
            exposed_ports=[8000, 8001],
            environment={"ENV": "production"}
        )
        
        assert config.has_dockerfile is True
        assert config.has_compose is True
        assert config.base_image == "python:3.9"
        assert 8000 in config.exposed_ports


class TestProjectConfig:
    """测试项目配置"""

    def test_create_frontend_project(self):
        """测试创建前端项目配置"""
        frontend = FrontendConfig(
            framework=FrameworkType.VUE3,
            test_runner=TestRunner.VITEST,
            build_tool=BuildTool.VITE
        )
        
        config = ProjectConfig(
            name="test-project",
            type=ProjectType.FRONTEND,
            frontend=frontend
        )
        
        assert config.name == "test-project"
        assert config.type == ProjectType.FRONTEND
        assert config.frontend is not None
        assert config.backend is None

    def test_create_fullstack_project(self):
        """测试创建全栈项目配置"""
        frontend = FrontendConfig(
            framework=FrameworkType.VUE3,
            test_runner=TestRunner.VITEST,
            build_tool=BuildTool.VITE
        )
        
        backend = BackendConfig(
            language="go",
            build_system=BuildTool.MAKE
        )
        
        config = ProjectConfig(
            name="fullstack-project",
            type=ProjectType.FULLSTACK,
            frontend=frontend,
            backend=backend
        )
        
        assert config.type == ProjectType.FULLSTACK
        assert config.frontend is not None
        assert config.backend is not None


class TestSystemSettings:
    """测试系统设置"""

    def test_create_system_settings(self):
        """测试创建系统设置"""
        settings = SystemSettings(
            max_context_size=10000,
            git_auto_commit=True,
            sandbox_timeout=300,
            max_retries=3,
            log_level="info"
        )
        
        assert settings.max_context_size == 10000
        assert settings.git_auto_commit is True
        assert settings.sandbox_timeout == 300

    def test_system_settings_defaults(self):
        """测试系统设置默认值"""
        settings = SystemSettings()
        
        assert settings.max_context_size == 10000
        assert settings.git_auto_commit is True
        assert settings.sandbox_timeout == 300
        assert settings.max_retries == 3
        assert settings.log_level == "info"
        assert settings.enable_hooks is True


class TestEngineConfig:
    """测试 AI 引擎配置"""

    def test_create_engine_config(self):
        """测试创建引擎配置"""
        config = EngineConfig(
            type=EngineType.QWEN_CODE,
            api_key="test-key",
            api_base="https://api.example.com",
            model="qwen-coder-plus",
            temperature=0.7,
            max_tokens=4096
        )
        
        assert config.type == EngineType.QWEN_CODE
        assert config.api_key == "test-key"
        assert config.temperature == 0.7


class TestConfiguration:
    """测试系统配置"""

    def test_create_configuration(self):
        """测试创建系统配置"""
        project = ProjectConfig(
            name="test-project",
            type=ProjectType.BACKEND
        )
        
        task = TaskConfig(
            id="task_1",
            name="测试任务",
            type=TaskType.FEATURE
        )
        
        settings = SystemSettings()
        
        config = Configuration(
            project=project,
            tasks=[task],
            settings=settings
        )
        
        assert config.project.name == "test-project"
        assert len(config.tasks) == 1
        assert config.settings.max_context_size == 10000

    def test_get_task_by_id(self):
        """测试根据 ID 获取任务"""
        project = ProjectConfig(
            name="test-project",
            type=ProjectType.BACKEND
        )
        
        task1 = TaskConfig(id="task_1", name="任务1", type=TaskType.FEATURE)
        task2 = TaskConfig(id="task_2", name="任务2", type=TaskType.BUGFIX)
        
        config = Configuration(
            project=project,
            tasks=[task1, task2],
            settings=SystemSettings()
        )
        
        found = config.get_task_by_id("task_1")
        assert found is not None
        assert found.name == "任务1"
        
        not_found = config.get_task_by_id("task_999")
        assert not_found is None

    def test_get_engine_config(self):
        """测试获取引擎配置"""
        project = ProjectConfig(
            name="test-project",
            type=ProjectType.BACKEND
        )
        
        engine_config = EngineConfig(
            type=EngineType.QWEN_CODE,
            api_key="test-key"
        )
        
        config = Configuration(
            project=project,
            tasks=[],
            settings=SystemSettings(),
            ai_engines={"qwen_code": engine_config}
        )
        
        found = config.get_engine_config("qwen_code")
        assert found is not None
        assert found.api_key == "test-key"
        
        not_found = config.get_engine_config("unknown")
        assert not_found is None

    def test_validate_empty_project_name(self):
        """测试验证空项目名称"""
        project = ProjectConfig(
            name="",
            type=ProjectType.BACKEND
        )
        
        config = Configuration(
            project=project,
            tasks=[],
            settings=SystemSettings()
        )
        
        errors = config.validate()
        assert len(errors) > 0
        assert any("项目名称不能为空" in error for error in errors)

    def test_validate_duplicate_task_ids(self):
        """测试验证重复的任务 ID"""
        project = ProjectConfig(
            name="test-project",
            type=ProjectType.BACKEND
        )
        
        task1 = TaskConfig(id="task_1", name="任务1", type=TaskType.FEATURE)
        task2 = TaskConfig(id="task_1", name="任务2", type=TaskType.BUGFIX)
        
        config = Configuration(
            project=project,
            tasks=[task1, task2],
            settings=SystemSettings()
        )
        
        errors = config.validate()
        assert len(errors) > 0
        assert any("重复的任务 ID" in error for error in errors)

    def test_validate_missing_dependency(self):
        """测试验证缺失的依赖"""
        project = ProjectConfig(
            name="test-project",
            type=ProjectType.BACKEND
        )
        
        task = TaskConfig(
            id="task_1",
            name="任务1",
            type=TaskType.FEATURE,
            depends_on=["task_999"]
        )
        
        config = Configuration(
            project=project,
            tasks=[task],
            settings=SystemSettings()
        )
        
        errors = config.validate()
        assert len(errors) > 0
        assert any("依赖不存在的任务" in error for error in errors)

    def test_validate_missing_engine(self):
        """测试验证缺失的引擎配置"""
        project = ProjectConfig(
            name="test-project",
            type=ProjectType.BACKEND
        )
        
        task = TaskConfig(
            id="task_1",
            name="任务1",
            type=TaskType.FEATURE,
            ai_engine="unknown_engine"
        )
        
        config = Configuration(
            project=project,
            tasks=[task],
            settings=SystemSettings(),
            ai_engines={}
        )
        
        errors = config.validate()
        assert len(errors) > 0
        assert any("引擎" in error and "未配置" in error for error in errors)

    def test_validate_valid_configuration(self):
        """测试验证有效配置"""
        project = ProjectConfig(
            name="test-project",
            type=ProjectType.BACKEND
        )
        
        engine_config = EngineConfig(
            type=EngineType.QWEN_CODE,
            api_key="test-key"
        )
        
        task = TaskConfig(
            id="task_1",
            name="任务1",
            type=TaskType.FEATURE,
            ai_engine="qwen_code"
        )
        
        config = Configuration(
            project=project,
            tasks=[task],
            settings=SystemSettings(),
            ai_engines={"qwen_code": engine_config}
        )
        
        errors = config.validate()
        assert len(errors) == 0
