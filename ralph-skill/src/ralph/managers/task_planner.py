"""
任务规划器

负责将用户需求分解为具体的任务列表。
"""

import logging
from typing import Any, Dict, List, Optional

from ralph.models.config import Configuration, EngineConfig, ProjectConfig, SystemSettings
from ralph.models.enums import EngineType, ProjectType, TaskType
from ralph.models.task import TaskConfig

logger = logging.getLogger(__name__)


class TaskPlanner:
    """
    任务规划器
    
    将高层需求分解为可执行的任务列表。
    """
    
    def __init__(self, ai_engine_client=None):
        """
        初始化任务规划器
        
        参数:
            ai_engine_client: AI 引擎客户端（用于智能任务分解）
        """
        self.ai_engine_client = ai_engine_client
    
    def plan_tasks(
        self,
        task_description: str,
        tech_stack: Optional[Dict[str, Any]] = None,
        requirements: Optional[List[str]] = None,
    ) -> Configuration:
        """
        规划任务列表
        
        根据用户描述生成完整的配置和任务列表。
        
        参数:
            task_description: 任务描述
            tech_stack: 技术栈配置
            requirements: 具体需求列表
        
        返回:
            Configuration: 完整的配置对象
        """
        logger.info(f"开始规划任务: {task_description}")
        
        # 1. 分析项目类型
        project_type = self._infer_project_type(task_description, tech_stack)
        
        # 2. 创建项目配置
        project_config = self._create_project_config(
            task_description, project_type, tech_stack
        )
        
        # 3. 分解任务
        tasks = self._decompose_tasks(
            task_description, project_type, tech_stack, requirements
        )
        
        # 4. 创建 AI 引擎配置
        ai_engines = self._create_ai_engine_config()
        
        # 5. 创建完整配置
        config = Configuration(
            project=project_config,
            tasks=tasks,
            settings=SystemSettings(
                log_level="info",
                enable_hooks=True,
                max_retries=3,
            ),
            ai_engines=ai_engines,
        )
        
        logger.info(f"任务规划完成，共 {len(tasks)} 个任务")
        return config
    
    def _infer_project_type(
        self,
        description: str,
        tech_stack: Optional[Dict[str, Any]]
    ) -> ProjectType:
        """推断项目类型"""
        desc_lower = description.lower()
        
        # 检查技术栈
        if tech_stack:
            has_frontend = "frontend" in tech_stack
            has_backend = "backend" in tech_stack
            
            if has_frontend and has_backend:
                return ProjectType.FULLSTACK
            elif has_frontend:
                return ProjectType.FRONTEND
            elif has_backend:
                return ProjectType.BACKEND
        
        # 根据描述推断
        frontend_keywords = ["前端", "界面", "ui", "页面", "vue", "react", "angular"]
        backend_keywords = ["后端", "api", "服务", "server", "go", "python", "node"]
        
        has_frontend_keyword = any(kw in desc_lower for kw in frontend_keywords)
        has_backend_keyword = any(kw in desc_lower for kw in backend_keywords)
        
        if has_frontend_keyword and has_backend_keyword:
            return ProjectType.FULLSTACK
        elif has_frontend_keyword:
            return ProjectType.FRONTEND
        elif has_backend_keyword:
            return ProjectType.BACKEND
        
        # 默认全栈
        return ProjectType.FULLSTACK
    
    def _create_project_config(
        self,
        description: str,
        project_type: ProjectType,
        tech_stack: Optional[Dict[str, Any]]
    ) -> ProjectConfig:
        """创建项目配置"""
        from ralph.models.config import BackendConfig, FrontendConfig
        from ralph.models.enums import (
            BuildTool, DependencyManager, FrameworkType, TestRunner
        )
        
        # 提取项目名称
        project_name = self._extract_project_name(description)
        
        # 创建前端配置
        frontend_config = None
        if project_type in [ProjectType.FRONTEND, ProjectType.FULLSTACK]:
            frontend_framework = FrameworkType.VUE3
            if tech_stack and "frontend" in tech_stack:
                framework_str = tech_stack["frontend"].get("framework", "vue3")
                try:
                    frontend_framework = FrameworkType(framework_str)
                except ValueError:
                    pass
            
            frontend_config = FrontendConfig(
                framework=frontend_framework,
                test_runner=TestRunner.VITEST,
                e2e_runner=TestRunner.PLAYWRIGHT,
                build_tool=BuildTool.VITE,
                package_manager=DependencyManager.NPM,
            )
        
        # 创建后端配置
        backend_config = None
        if project_type in [ProjectType.BACKEND, ProjectType.FULLSTACK]:
            backend_language = "go"
            backend_framework = FrameworkType.GIN
            
            if tech_stack and "backend" in tech_stack:
                backend_language = tech_stack["backend"].get("language", "go")
                framework_str = tech_stack["backend"].get("framework", "gin")
                try:
                    backend_framework = FrameworkType(framework_str)
                except ValueError:
                    pass
            
            backend_config = BackendConfig(
                language=backend_language,
                framework=backend_framework,
                build_system=BuildTool.GO if backend_language == "go" else BuildTool.MAKE,
                dependency_manager=DependencyManager.GO_MOD if backend_language == "go" else DependencyManager.PIP,
                test_runner=TestRunner.TESTING if backend_language == "go" else TestRunner.PYTEST,
            )
        
        return ProjectConfig(
            name=project_name,
            type=project_type,
            frontend=frontend_config,
            backend=backend_config,
        )
    
    def _extract_project_name(self, description: str) -> str:
        """从描述中提取项目名称"""
        # 简单实现：取前几个词
        words = description.split()[:3]
        name = "-".join(words).lower()
        
        # 清理特殊字符
        import re
        name = re.sub(r'[^a-z0-9-]', '', name)
        
        return name or "my-project"
    
    def _decompose_tasks(
        self,
        description: str,
        project_type: ProjectType,
        tech_stack: Optional[Dict[str, Any]],
        requirements: Optional[List[str]]
    ) -> List[TaskConfig]:
        """分解任务"""
        tasks = []
        
        # 任务 1: 初始化项目结构
        tasks.append(TaskConfig(
            id="task-init",
            name="初始化项目结构",
            type=TaskType.FEATURE,
            depends_on=[],
            ai_engine="qwen_code",
            max_retries=3,
            timeout=1800,
            config={
                "description": self._generate_init_task_description(project_type, tech_stack),
            }
        ))
        
        # 任务 2: 实现核心功能
        if project_type in [ProjectType.BACKEND, ProjectType.FULLSTACK]:
            tasks.append(TaskConfig(
                id="task-backend",
                name="实现后端功能",
                type=TaskType.FEATURE,
                depends_on=["task-init"],
                ai_engine="qwen_code",
                max_retries=3,
                timeout=1800,
                config={
                    "description": self._generate_backend_task_description(description, requirements),
                }
            ))
        
        if project_type in [ProjectType.FRONTEND, ProjectType.FULLSTACK]:
            depends = ["task-backend"] if project_type == ProjectType.FULLSTACK else ["task-init"]
            tasks.append(TaskConfig(
                id="task-frontend",
                name="实现前端功能",
                type=TaskType.FEATURE,
                depends_on=depends,
                ai_engine="qwen_code",
                max_retries=3,
                timeout=1800,
                config={
                    "description": self._generate_frontend_task_description(description, requirements),
                }
            ))
        
        # 任务 3: 添加测试
        last_task = tasks[-1].id
        tasks.append(TaskConfig(
            id="task-tests",
            name="添加测试",
            type=TaskType.TEST,
            depends_on=[last_task],
            ai_engine="qwen_code",
            max_retries=3,
            timeout=1800,
            config={
                "description": "为实现的功能添加单元测试和集成测试，目标覆盖率 > 80%",
            }
        ))
        
        return tasks
    
    def _generate_init_task_description(
        self,
        project_type: ProjectType,
        tech_stack: Optional[Dict[str, Any]]
    ) -> str:
        """生成初始化任务描述"""
        desc = "创建项目基础结构：\n\n"
        
        if project_type in [ProjectType.FRONTEND, ProjectType.FULLSTACK]:
            framework = "Vue3"
            if tech_stack and "frontend" in tech_stack:
                framework = tech_stack["frontend"].get("framework", "vue3").title()
            desc += f"1. 前端目录（frontend/）\n"
            desc += f"   - 使用 Vite 创建 {framework} 项目\n"
            desc += f"   - 配置 Vitest 测试\n"
            desc += f"   - 配置 ESLint 和 Prettier\n\n"
        
        if project_type in [ProjectType.BACKEND, ProjectType.FULLSTACK]:
            language = "Go"
            if tech_stack and "backend" in tech_stack:
                language = tech_stack["backend"].get("language", "go").title()
            desc += f"2. 后端目录（backend/）\n"
            desc += f"   - 初始化 {language} 项目\n"
            desc += f"   - 创建基础目录结构\n"
            desc += f"   - 配置依赖管理\n\n"
        
        desc += "3. 配置文件\n"
        desc += "   - .gitignore\n"
        desc += "   - README.md\n"
        desc += "   - .env.example\n"
        
        return desc
    
    def _generate_backend_task_description(
        self,
        description: str,
        requirements: Optional[List[str]]
    ) -> str:
        """生成后端任务描述"""
        desc = f"实现后端功能：{description}\n\n"
        desc += "要求：\n"
        desc += "- 实现 RESTful API\n"
        desc += "- 添加错误处理和日志\n"
        desc += "- 使用合适的数据结构\n"
        
        if requirements:
            desc += "\n具体需求：\n"
            for req in requirements:
                desc += f"- {req}\n"
        
        return desc
    
    def _generate_frontend_task_description(
        self,
        description: str,
        requirements: Optional[List[str]]
    ) -> str:
        """生成前端任务描述"""
        desc = f"实现前端界面：{description}\n\n"
        desc += "要求：\n"
        desc += "- 使用 Composition API\n"
        desc += "- 实现响应式设计\n"
        desc += "- 添加适当的用户反馈\n"
        desc += "- 调用后端 API\n"
        
        if requirements:
            desc += "\n具体需求：\n"
            for req in requirements:
                desc += f"- {req}\n"
        
        return desc
    
    def _create_ai_engine_config(self) -> Dict[str, EngineConfig]:
        """创建 AI 引擎配置"""
        return {
            "qwen_code": EngineConfig(
                type=EngineType.QWEN_CODE,
                model="qwen3-coder-plus",
                timeout=60,
            )
        }
