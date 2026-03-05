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
from typing import Dict, List, Optional

from ralph.adapters.ai_engine import AIEngineManager, CodeResult, EngineConfig
from ralph.managers.context_manager import ContextManager
from ralph.managers.git_manager import GitManager, MergeConflictError
from ralph.managers.hook_system import HookSystem
from ralph.managers.task_manager import TaskManager
from ralph.models.config import Configuration
from ralph.models.enums import EngineType, HookType, TaskStatus
from ralph.models.execution import ExecutionResult
from ralph.models.hook import HookConfig, HookContext
from ralph.models.task import Task, TaskConfig, TaskResult
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
        执行单个任务

        完整的任务执行工作流:
        1. 创建 WIP 分支
        2. 执行任务（调用 AI 引擎生成代码）
        3. 运行测试
        4. 处理错误和重试
        5. 提交代码或回滚

        验证需求 1, 2, 3, 4
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

            # 执行任务的核心循环
            retry_count = 0
            max_retries = task_config.max_retries
            success = False
            error_message = ""
            files_changed = []
            
            while retry_count <= max_retries and not success:
                try:
                    logger.info(f"执行任务 {task.name}，尝试 {retry_count + 1}/{max_retries + 1}")
                    
                    # 1. 调用 AI 引擎生成代码
                    code_result = self._execute_with_ai(task_config)
                    files_changed = code_result.changes or []
                    
                    # 2. 运行测试验证
                    test_passed = self._run_tests(task_config)
                    
                    if test_passed:
                        success = True
                        logger.info(f"任务 {task.name} 执行成功")
                    else:
                        error_message = "测试未通过"
                        retry_count += 1
                        if retry_count <= max_retries:
                            logger.warning(f"测试失败，准备重试 ({retry_count}/{max_retries})")
                            # 回滚代码
                            self.git_manager.rollback_to_branch(wip_branch)
                        
                except Exception as e:
                    error_message = str(e)
                    retry_count += 1
                    logger.error(f"任务执行出错: {e}")
                    if retry_count <= max_retries:
                        logger.warning(f"准备重试 ({retry_count}/{max_retries})")
                        # 回滚代码
                        try:
                            self.git_manager.rollback_to_branch(wip_branch)
                        except Exception:
                            pass

            if success:
                # 提交代码
                commit_hash = self.git_manager.commit_changes(
                    f"feat: {task.name}",
                    files=files_changed
                )
                
                # 更新状态为 COMPLETED
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
                )
            else:
                # 任务失败
                self.task_manager.update_task_status(
                    task.id, TaskStatus.FAILED
                )
                
                execution_time = time.time() - start_time
                return TaskResult(
                    task_id=task.id,
                    success=False,
                    message=f"任务失败: {error_message}",
                    execution_time=execution_time,
                )

        except Exception as e:
            logger.error(f"任务执行失败: {e}")
            self.task_manager.update_task_status(
                task.id, TaskStatus.FAILED
            )
            return TaskResult(
                task_id=task.id,
                success=False,
                message=str(e),
                execution_time=time.time() - start_time,
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
    
    def _run_tests(self, task_config: TaskConfig) -> bool:
        """
        运行测试验证代码
        
        参数:
            task_config: 任务配置
        
        返回:
            bool: 测试是否通过
        """
        logger.info("运行测试验证...")
        
        try:
            # 在沙箱中运行测试
            test_command = self._get_test_command()
            if not test_command:
                logger.warning("未配置测试命令，跳过测试")
                return True
            
            result = self.sandbox.execute_command(
                test_command,
                timeout=task_config.timeout,
            )
            
            if result.exit_code == 0:
                logger.info("✅ 测试通过")
                return True
            else:
                logger.warning(f"❌ 测试失败: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"运行测试时出错: {e}")
            return False
    
    def _get_test_command(self) -> Optional[str]:
        """获取测试命令"""
        # 根据项目类型返回测试命令
        if self.config.project.backend:
            language = self.config.project.backend.language
            if language == "go":
                return "go test ./..."
            elif language == "python":
                return "pytest"
            elif language == "node":
                return "npm test"
        
        if self.config.project.frontend:
            return "npm test"
        
        return None
    
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

