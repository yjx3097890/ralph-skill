"""
Ralph Engine 核心协调器

负责协调所有管理器组件，实现完整的任务执行工作流。

验证需求:
- 需求 1: Git 级别安全与回滚机制
- 需求 2: 上下文截断与防爆机制
- 需求 3: 高级任务状态机与依赖管理
- 需求 4: 前置和后置钩子系统
- 需求 5: OpenClaw 标准化接口
"""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from ralph.adapters.ai_engine import AIEngineManager, CodeResult, EngineConfig
from ralph.managers.context_manager import ContextManager
from ralph.managers.git_manager import GitManager, MergeConflictError
from ralph.managers.hook_system import HookSystem
from ralph.managers.task_manager import TaskManager
from ralph.models.config import Configuration
from ralph.models.enums import EngineType, HookType, TaskStatus
from ralph.models.execution import ExecutionResult
from ralph.models.hook import HookConfig, HookContext
from ralph.models.task import Task, TaskConfig, TaskResult, TaskInfo
from ralph.sandbox.safety_sandbox import (
    FileSystemPolicy,
    NetworkPolicy,
    ResourceLimits,
    SafetySandbox,
    SandboxConfig,
)

logger = logging.getLogger(__name__)


class RalphEngineError(Exception):
    """Ralph Engine 错误基类"""
    pass


class RalphEngineCore:
    """
    Ralph Engine 核心协调器
    
    协调所有管理器组件，实现完整的任务执行工作流。
    """
    
    def __init__(self, config: Configuration, project_root: str):
        """初始化 Ralph Engine 核心"""
        self.config = config
        self.project_root = Path(project_root)
        self._initialize_managers()
        logger.info(f"Ralph Engine 已初始化，项目: {project_root}")


    def _initialize_managers(self) -> None:
        """初始化所有管理器组件"""
        self.task_manager = TaskManager()
        self.git_manager = GitManager(str(self.project_root))
        self.context_manager = ContextManager()
        self.hook_system = HookSystem()
        
        # 初始化 AI 引擎管理器
        self.ai_engine_manager = AIEngineManager(
            EngineType.QWEN_CODE, [EngineType.AIDER]
        )
        
        # 从配置中注册 AI 引擎
        if self.config.ai_engines:
            for engine_name, engine_config in self.config.ai_engines.items():
                try:
                    self.ai_engine_manager.register_engine(
                        engine_config.type, engine_config
                    )
                    logger.info(f"已注册 AI 引擎: {engine_name} ({engine_config.type.value})")
                except Exception as e:
                    logger.warning(f"注册 AI 引擎 {engine_name} 失败: {e}")
        
        self.sandbox = SafetySandbox(
            SandboxConfig(project_root=str(self.project_root))
        )
        logger.info("所有管理器组件已初始化")

    def execute_task(self, task_config: TaskConfig) -> TaskResult:
            """
            执行单个任务（不重试，由 Agent 控制）

            工作流:
            1. 创建 WIP 分支
            2. 调用 AI 引擎生成代码
            3. 运行测试验证
            4. 返回详细结果（成功或失败）

            注意：不再在内部重试，失败时返回详细错误信息供 Agent 分析
            """
            start_time = time.time()
            task = self.task_manager.create_task(task_config)
            logger.info(f"开始执行任务: {task.name}")

            try:
                # 创建 WIP 分支
                wip_branch = self.git_manager.create_wip_branch(task.id)
                task.git_branch = wip_branch

                # 更新状态为 IN_PROGRESS
                self.task_manager.update_task_status(
                    task.id, TaskStatus.IN_PROGRESS
                )

                # 1. 调用 AI 引擎生成代码
                logger.info(f"执行任务 {task.name}")
                code_result = self._execute_with_ai(task_config)

                if not code_result.success:
                    error_message = f"AI 引擎执行失败: {code_result.explanation}"
                    logger.error(error_message)

                    # 更新状态为 FAILED
                    self.task_manager.update_task_status(
                        task.id, TaskStatus.FAILED
                    )

                    execution_time = time.time() - start_time
                    return TaskResult(
                        task_id=task.id,
                        success=False,
                        message=error_message,
                        execution_time=execution_time,
                        output=code_result.explanation,
                        errors=[error_message]
                    )

                files_changed = code_result.changes or []
                logger.info(f"AI 引擎执行成功，修改了 {len(files_changed)} 个文件")

                # 2. 运行测试验证
                test_passed, test_output = self._run_tests(task_config)

                if test_passed:
                    # 测试通过，提交代码
                    commit_hash = self.git_manager.commit_changes(
                        f"feat: {task.name}",
                        files=files_changed
                    )

                    # 更新状态为 TESTING → COMPLETED
                    self.task_manager.update_task_status(
                        task.id, TaskStatus.TESTING
                    )
                    self.task_manager.update_task_status(
                        task.id, TaskStatus.COMPLETED
                    )

                    execution_time = time.time() - start_time
                    return TaskResult(
                        task_id=task.id,
                        success=True,
                        message="任务执行成功",
                        execution_time=execution_time,
                        files_changed=files_changed,
                        commit_hash=commit_hash,
                        tests_passed=True,
                        test_output=test_output
                    )
                else:
                    # 测试失败，返回详细错误信息供 Agent 分析
                    # 不回滚代码，保留现场
                    error_message = "测试未通过"
                    logger.error(f"❌ {error_message}")
                    logger.info("保留代码现场供 Agent 分析")

                    # 更新状态为 FAILED
                    self.task_manager.update_task_status(
                        task.id, TaskStatus.FAILED
                    )

                    execution_time = time.time() - start_time
                    return TaskResult(
                        task_id=task.id,
                        success=False,
                        message=error_message,
                        execution_time=execution_time,
                        files_changed=files_changed,
                        output=test_output,
                        errors=[error_message],
                        tests_passed=False,
                        test_output=test_output
                    )

            except Exception as e:
                logger.error(f"任务执行失败: {e}", exc_info=True)

                # 更新状态为 FAILED
                try:
                    if task.status == TaskStatus.PENDING:
                        self.task_manager.update_task_status(
                            task.id, TaskStatus.IN_PROGRESS
                        )
                except Exception:
                    pass

                self.task_manager.update_task_status(
                    task.id, TaskStatus.FAILED
                )

                return TaskResult(
                    task_id=task.id,
                    success=False,
                    message=str(e),
                    execution_time=time.time() - start_time,
                    errors=[str(e)]
                )
    
    def _execute_with_ai(self, task_config: TaskConfig) -> CodeResult:
        """
        使用 AI 引擎执行任务
        
        参数:
            task_config: 任务配置
        
        返回:
            CodeResult: 代码生成结果
        """
        # 获取任务描述
        description = task_config.config.get("description", task_config.name)
        
        # 构建上下文
        context = self.context_manager.build_context(
            project_root=str(self.project_root),
            task_description=description,
        )
        
        # 调用 AI 引擎
        logger.info(f"调用 AI 引擎生成代码...")
        result = self.ai_engine_manager.generate_code(
            prompt=description,
            context=context,
            project_root=str(self.project_root),
        )
        
        logger.info(f"代码生成完成，修改了 {len(result.changes or [])} 个文件")
        return result
    
    def _run_tests(self, task_config: TaskConfig) -> tuple[bool, str]:
            """
            运行测试验证代码（包括单元测试和 E2E 测试）

            参数:
                task_config: 任务配置

            返回:
                tuple[bool, str]: (测试是否通过, 详细的测试输出)
            """
            logger.info("运行测试验证...")

            # 对于初始化任务，跳过测试（因为项目还没有完全初始化）
            if "init" in task_config.id.lower() or "初始化" in task_config.name:
                logger.info("初始化任务，跳过测试验证")
                return True, "初始化任务，跳过测试"

            try:
                # 检查项目是否已初始化
                if not self._is_project_initialized():
                    logger.warning("项目尚未初始化，跳过测试")
                    return True, "项目尚未初始化"

                # 检查并启动必要的服务（如数据库）
                self._ensure_services_running()

                # 获取所有测试命令（单元测试 + E2E 测试）
                test_commands = self._get_test_commands()
                if not test_commands:
                    logger.warning("未配置测试命令，跳过测试")
                    return True, "未配置测试命令"

                all_outputs = []
                all_passed = True

                # 依次执行所有测试
                for test_type, test_command in test_commands.items():
                    logger.info(f"\n{'='*50}")
                    logger.info(f"执行 {test_type} 测试")
                    logger.info(f"命令: {test_command}")
                    logger.info(f"{'='*50}\n")

                    result = self.sandbox.execute_command(
                        test_command,
                        timeout=task_config.timeout,
                    )

                    output_header = f"\n{'='*50}\n{test_type} 测试结果\n{'='*50}\n"
                    all_outputs.append(output_header + result.output)

                    if result.exit_code == 0:
                        logger.info(f"✅ {test_type} 测试通过")
                    else:
                        logger.error(f"❌ {test_type} 测试失败 (退出码: {result.exit_code})")
                        logger.error(f"测试输出:\n{result.output}")
                        all_passed = False
                        # 如果单元测试失败，不再执行 E2E 测试
                        if test_type == "单元测试":
                            logger.warning("单元测试失败，跳过 E2E 测试")
                            break

                combined_output = "\n".join(all_outputs)

                if all_passed:
                    logger.info("✅ 所有测试通过")
                    return True, combined_output
                else:
                    logger.error("❌ 测试失败")
                    return False, combined_output

            except Exception as e:
                error_msg = f"运行测试时出错: {str(e)}"
                logger.error(error_msg, exc_info=True)
                return False, error_msg
    
    def _ensure_services_running(self) -> None:
        """
        确保必要的服务正在运行
        
        检查项目依赖的服务（如数据库），如果未运行则自动启动 Docker 容器
        """
        try:
            import subprocess
            import re
            
            # 检查项目中是否使用了数据库
            # 通过扫描代码文件来检测
            project_files = list(self.project_root.rglob("*.go")) + \
                           list(self.project_root.rglob("*.js")) + \
                           list(self.project_root.rglob("*.py"))
            
            needs_mongodb = False
            needs_postgres = False
            needs_redis = False
            
            for file_path in project_files:
                try:
                    content = file_path.read_text()
                    if "mongo" in content.lower():
                        needs_mongodb = True
                    if "postgres" in content.lower() or "postgresql" in content.lower():
                        needs_postgres = True
                    if "redis" in content.lower():
                        needs_redis = True
                except Exception:
                    continue
            
            # 启动需要的服务
            if needs_mongodb:
                self._ensure_mongodb_running()
            if needs_postgres:
                self._ensure_postgres_running()
            if needs_redis:
                self._ensure_redis_running()
                
        except Exception as e:
            logger.warning(f"检查服务状态时出错: {e}")
    
    def _ensure_mongodb_running(self) -> None:
        """确保 MongoDB 容器正在运行"""
        try:
            import subprocess
            
            logger.info("检查 MongoDB 容器...")
            
            # 检查是否已有运行中的 MongoDB 容器
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=ralph-mongodb", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if "ralph-mongodb" in result.stdout:
                logger.info("MongoDB 容器已在运行")
                return
            
            # 检查是否有停止的容器
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", "name=ralph-mongodb", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if "ralph-mongodb" in result.stdout:
                # 启动已存在的容器
                logger.info("启动已存在的 MongoDB 容器...")
                subprocess.run(
                    ["docker", "start", "ralph-mongodb"],
                    capture_output=True,
                    timeout=30
                )
            else:
                # 创建新容器
                logger.info("创建并启动 MongoDB 容器...")
                subprocess.run(
                    [
                        "docker", "run", "-d",
                        "--name", "ralph-mongodb",
                        "-p", "27017:27017",
                        "-e", "MONGO_INITDB_DATABASE=todoapp",
                        "mongo:latest"
                    ],
                    capture_output=True,
                    timeout=60
                )
            
            # 等待 MongoDB 启动
            logger.info("等待 MongoDB 启动...")
            import time
            time.sleep(5)
            
            logger.info("✅ MongoDB 容器已启动")
            
        except Exception as e:
            logger.warning(f"启动 MongoDB 容器失败: {e}")
    
    def _ensure_postgres_running(self) -> None:
        """确保 PostgreSQL 容器正在运行"""
        try:
            import subprocess
            
            logger.info("检查 PostgreSQL 容器...")
            
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=ralph-postgres", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if "ralph-postgres" in result.stdout:
                logger.info("PostgreSQL 容器已在运行")
                return
            
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", "name=ralph-postgres", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if "ralph-postgres" in result.stdout:
                logger.info("启动已存在的 PostgreSQL 容器...")
                subprocess.run(
                    ["docker", "start", "ralph-postgres"],
                    capture_output=True,
                    timeout=30
                )
            else:
                logger.info("创建并启动 PostgreSQL 容器...")
                subprocess.run(
                    [
                        "docker", "run", "-d",
                        "--name", "ralph-postgres",
                        "-p", "5432:5432",
                        "-e", "POSTGRES_PASSWORD=postgres",
                        "-e", "POSTGRES_DB=todoapp",
                        "postgres:latest"
                    ],
                    capture_output=True,
                    timeout=60
                )
            
            import time
            time.sleep(5)
            logger.info("✅ PostgreSQL 容器已启动")
            
        except Exception as e:
            logger.warning(f"启动 PostgreSQL 容器失败: {e}")
    
    def _ensure_redis_running(self) -> None:
        """确保 Redis 容器正在运行"""
        try:
            import subprocess
            
            logger.info("检查 Redis 容器...")
            
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=ralph-redis", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if "ralph-redis" in result.stdout:
                logger.info("Redis 容器已在运行")
                return
            
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", "name=ralph-redis", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if "ralph-redis" in result.stdout:
                logger.info("启动已存在的 Redis 容器...")
                subprocess.run(
                    ["docker", "start", "ralph-redis"],
                    capture_output=True,
                    timeout=30
                )
            else:
                logger.info("创建并启动 Redis 容器...")
                subprocess.run(
                    [
                        "docker", "run", "-d",
                        "--name", "ralph-redis",
                        "-p", "6379:6379",
                        "redis:latest"
                    ],
                    capture_output=True,
                    timeout=60
                )
            
            import time
            time.sleep(3)
            logger.info("✅ Redis 容器已启动")
            
        except Exception as e:
            logger.warning(f"启动 Redis 容器失败: {e}")
    
    def _get_test_commands(self) -> Dict[str, str]:
            """
            获取所有测试命令（单元测试 + E2E 测试）

            返回:
                Dict[str, str]: 测试类型到命令的映射，例如 {"单元测试": "npm test", "E2E测试": "npm run test:e2e"}
            """
            commands = {}

            # 后端单元测试
            if self.config.project.backend:
                language = self.config.project.backend.language
                if language == "go":
                    # 检查是否在 backend 子目录
                    backend_dir = self.project_root / "backend"
                    if backend_dir.exists() and (backend_dir / "go.mod").exists():
                        commands["单元测试"] = "cd backend && go test ./..."
                    else:
                        commands["单元测试"] = "go test ./..."
                elif language == "python":
                    backend_dir = self.project_root / "backend"
                    if backend_dir.exists():
                        commands["单元测试"] = "cd backend && pytest"
                    else:
                        commands["单元测试"] = "pytest"
                elif language == "node":
                    backend_dir = self.project_root / "backend"
                    if backend_dir.exists():
                        commands["单元测试"] = "cd backend && npm test"
                    else:
                        commands["单元测试"] = "npm test"

            # 前端单元测试和 E2E 测试
            if self.config.project.frontend:
                frontend_dir = self.project_root / "frontend"

                # 检查前端目录是否存在
                if frontend_dir.exists():
                    package_json = frontend_dir / "package.json"

                    # 如果后端没有配置单元测试，添加前端单元测试
                    if "单元测试" not in commands:
                        commands["单元测试"] = "cd frontend && npm test"

                    # 检查是否配置了 E2E 测试
                    if self.config.project.frontend.e2e_runner:
                        e2e_runner = self.config.project.frontend.e2e_runner.value

                        # 检查 package.json 中是否有 E2E 测试脚本
                        if package_json.exists():
                            try:
                                import json
                                with open(package_json, 'r') as f:
                                    pkg_data = json.load(f)
                                    scripts = pkg_data.get("scripts", {})

                                    # 查找 E2E 测试脚本
                                    if "test:e2e" in scripts:
                                        commands["E2E测试"] = "cd frontend && npm run test:e2e"
                                    elif "e2e" in scripts:
                                        commands["E2E测试"] = "cd frontend && npm run e2e"
                                    elif e2e_runner == "playwright":
                                        # 使用默认的 Playwright 命令
                                        commands["E2E测试"] = "cd frontend && npx playwright test"
                                    elif e2e_runner == "cypress":
                                        commands["E2E测试"] = "cd frontend && npx cypress run"
                            except Exception as e:
                                logger.warning(f"解析 package.json 失败: {e}")
                                # 使用默认命令
                                if e2e_runner == "playwright":
                                    commands["E2E测试"] = "cd frontend && npx playwright test"
                                elif e2e_runner == "cypress":
                                    commands["E2E测试"] = "cd frontend && npx cypress run"
                else:
                    # 前端在根目录
                    if "单元测试" not in commands:
                        commands["单元测试"] = "npm test"

                    if self.config.project.frontend.e2e_runner:
                        e2e_runner = self.config.project.frontend.e2e_runner.value
                        package_json = self.project_root / "package.json"

                        if package_json.exists():
                            try:
                                import json
                                with open(package_json, 'r') as f:
                                    pkg_data = json.load(f)
                                    scripts = pkg_data.get("scripts", {})

                                    if "test:e2e" in scripts:
                                        commands["E2E测试"] = "npm run test:e2e"
                                    elif "e2e" in scripts:
                                        commands["E2E测试"] = "npm run e2e"
                                    elif e2e_runner == "playwright":
                                        commands["E2E测试"] = "npx playwright test"
                                    elif e2e_runner == "cypress":
                                        commands["E2E测试"] = "npx cypress run"
                            except Exception as e:
                                logger.warning(f"解析 package.json 失败: {e}")
                                if e2e_runner == "playwright":
                                    commands["E2E测试"] = "npx playwright test"
                                elif e2e_runner == "cypress":
                                    commands["E2E测试"] = "npx cypress run"

            return commands

        def _get_test_command(self) -> Optional[str]:
            """
            获取测试命令（保留用于向后兼容）

            返回:
                Optional[str]: 单元测试命令
            """
            commands = self._get_test_commands()
            return commands.get("单元测试")
    
    def _is_project_initialized(self) -> bool:
        """
        检查项目是否已初始化
        
        返回:
            bool: 项目是否已初始化
        """
        # 检查后端项目初始化
        if self.config.project.backend:
            language = self.config.project.backend.language
            if language == "go":
                # 检查 go.mod 是否存在（可能在根目录或 backend 目录）
                go_mod_root = self.project_root / "go.mod"
                go_mod_backend = self.project_root / "backend" / "go.mod"
                if not go_mod_root.exists() and not go_mod_backend.exists():
                    logger.debug("Go 项目未初始化：go.mod 不存在")
                    return False
            elif language == "python":
                # 检查 requirements.txt 或 pyproject.toml
                backend_dir = self.project_root / "backend"
                root_dir = self.project_root
                if not (backend_dir / "requirements.txt").exists() and \
                   not (backend_dir / "pyproject.toml").exists() and \
                   not (root_dir / "requirements.txt").exists() and \
                   not (root_dir / "pyproject.toml").exists():
                    logger.debug("Python 项目未初始化：requirements.txt 或 pyproject.toml 不存在")
                    return False
            elif language == "node":
                # 检查 package.json
                package_json_backend = self.project_root / "backend" / "package.json"
                package_json_root = self.project_root / "package.json"
                if not package_json_backend.exists() and not package_json_root.exists():
                    logger.debug("Node.js 项目未初始化：package.json 不存在")
                    return False
        
        # 检查前端项目初始化
        if self.config.project.frontend:
            frontend_dir = self.project_root / "frontend"
            root_dir = self.project_root
            package_json_frontend = frontend_dir / "package.json"
            package_json_root = root_dir / "package.json"
            
            # 如果有 frontend 目录，检查其中的 package.json
            if frontend_dir.exists():
                if not package_json_frontend.exists():
                    logger.debug("前端项目未初始化：frontend/package.json 不存在")
                    return False
            # 否则检查根目录的 package.json
            elif not package_json_root.exists():
                logger.debug("前端项目未初始化：package.json 不存在")
                return False
        
        logger.debug("项目已初始化")
        return True
    
    def run_all_tasks(self) -> Dict[str, TaskResult]:
        """
        执行所有任务
        
        按依赖顺序执行配置中的所有任务。
        
        返回:
            Dict[str, TaskResult]: 任务 ID 到结果的映射
        """
        logger.info(f"开始执行所有任务，共 {len(self.config.tasks)} 个")
        
        results = {}
        completed_tasks = set()
        
        # 按依赖顺序执行任务
        while len(completed_tasks) < len(self.config.tasks):
            # 找到可以执行的任务（依赖都已完成）
            ready_tasks = [
                task for task in self.config.tasks
                if task.id not in completed_tasks
                and all(dep in completed_tasks for dep in task.depends_on)
            ]
            
            if not ready_tasks:
                # 没有可执行的任务，可能存在循环依赖
                remaining = [t.id for t in self.config.tasks if t.id not in completed_tasks]
                logger.error(f"无法继续执行，剩余任务: {remaining}")
                break
            
            # 执行就绪的任务
            for task_config in ready_tasks:
                logger.info(f"\n{'='*60}")
                logger.info(f"执行任务: {task_config.name} ({task_config.id})")
                logger.info(f"{'='*60}\n")
                
                result = self.execute_task(task_config)
                results[task_config.id] = result
                
                if result.success:
                    completed_tasks.add(task_config.id)
                    logger.info(f"✅ 任务 {task_config.name} 完成")
                else:
                    logger.error(f"❌ 任务 {task_config.name} 失败: {result.message}")
                    # 任务失败，停止执行
                    logger.error("任务失败，停止执行后续任务")
                    return results
        
        logger.info(f"\n所有任务执行完成，成功 {len(completed_tasks)}/{len(self.config.tasks)}")
        return results


    def add_task(self, task_config: TaskConfig) -> str:
        """
        动态添加新任务到任务列表

        参数:
            task_config: 任务配置

        返回:
            str: 新任务的 ID
        """
        logger.info(f"添加新任务: {task_config.name} ({task_config.id})")

        # 添加到配置的任务列表
        self.config.tasks.append(task_config)

        return task_config.id

    def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """
        更新任务配置

        参数:
            task_id: 任务 ID
            updates: 要更新的字段字典

        返回:
            bool: 是否更新成功
        """
        logger.info(f"更新任务: {task_id}")

        # 查找任务
        for task in self.config.tasks:
            if task.id == task_id:
                # 更新字段
                for key, value in updates.items():
                    if hasattr(task, key):
                        setattr(task, key, value)
                        logger.info(f"  更新 {key} = {value}")
                return True

        logger.warning(f"任务不存在: {task_id}")
        return False

    def get_task_status(self, task_id: str) -> Optional[TaskInfo]:
        """
        获取任务当前状态

        参数:
            task_id: 任务 ID

        返回:
            TaskInfo: 任务信息，如果任务不存在则返回 None
        """
        try:
            task = self.task_manager.get_task(task_id)
            return self.task_manager.get_task_info(task_id)
        except Exception as e:
            logger.warning(f"获取任务状态失败: {e}")
            return None

    def rollback_task(self, task_id: str) -> bool:
        """
        回滚任务的代码变更

        参数:
            task_id: 任务 ID

        返回:
            bool: 是否回滚成功
        """
        logger.info(f"回滚任务: {task_id}")

        try:
            task = self.task_manager.get_task(task_id)
            if task.git_branch:
                # 回滚到任务开始前的状态
                self.git_manager.rollback_to_branch(task.git_branch)
                logger.info(f"✅ 已回滚任务 {task_id}")
                return True
            else:
                logger.warning(f"任务 {task_id} 没有关联的 Git 分支")
                return False
        except Exception as e:
            logger.error(f"回滚任务失败: {e}")
            return False

    def get_code_diff(self, task_id: str) -> str:
        """
        获取任务的代码变更差异

        参数:
            task_id: 任务 ID

        返回:
            str: Git diff 输出
        """
        try:
            task = self.task_manager.get_task(task_id)
            if task.git_branch:
                # 获取当前分支与主分支的差异
                return self.git_manager.get_diff()
            else:
                return ""
        except Exception as e:
            logger.error(f"获取代码差异失败: {e}")
            return ""


