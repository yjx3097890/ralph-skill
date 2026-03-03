"""
Ralph Skill 主入口

提供标准化的函数接口供 Kiro 和其他工具调用。
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ralph.core.config_parser import ConfigParser
from ralph.core.ralph_engine import RalphEngineCore
from ralph.models.config import Configuration, ProjectConfig
from ralph.models.enums import ProjectType, TaskType
from ralph.models.task import TaskConfig

logger = logging.getLogger(__name__)


def autonomous_develop(
    task_description: str,
    tech_stack: Optional[Dict[str, Any]] = None,
    requirements: Optional[List[str]] = None,
    constraints: Optional[List[str]] = None,
    project_root: str = ".",
    config_file: Optional[str] = None,
) -> Dict[str, Any]:
    """
    自治开发功能
    
    根据任务描述自动生成代码。
    
    参数:
        task_description: 任务描述
        tech_stack: 技术栈配置（可选）
        requirements: 具体需求列表（可选）
        constraints: 约束条件（可选）
        project_root: 项目根目录（默认当前目录）
        config_file: 配置文件路径（可选，如果不提供则使用默认配置）
    
    返回:
        {
            "success": bool,
            "files_changed": List[str],
            "commit_hash": str,
            "message": str
        }
    """
    try:
        # 加载或创建配置
        if config_file and Path(config_file).exists():
            parser = ConfigParser()
            config = parser.parse_config(config_file)
        else:
            # 使用默认配置
            config = _create_default_config(task_description, tech_stack)
        
        # 创建任务配置
        task_config = TaskConfig(
            id="auto-dev-task",
            name=task_description,
            type=TaskType.FEATURE,
            depends_on=[],
            ai_engine=list(config.ai_engines.keys())[0] if config.ai_engines else "qwen_code",
            max_retries=3,
            timeout=1800,
            config={
                "description": task_description,
                "requirements": requirements or [],
                "constraints": constraints or [],
            }
        )
        
        # 执行任务
        engine = RalphEngineCore(config, project_root)
        result = engine.execute_task(task_config)
        
        return {
            "success": result.success,
            "files_changed": result.files_changed or [],
            "commit_hash": result.commit_hash or "",
            "message": result.message,
        }
        
    except Exception as e:
        logger.error(f"自治开发失败: {e}")
        return {
            "success": False,
            "files_changed": [],
            "commit_hash": "",
            "message": f"执行失败: {str(e)}",
        }


def generate_tests(
    target_files: List[str],
    test_type: str = "unit",
    coverage_target: int = 80,
    project_root: str = ".",
    config_file: Optional[str] = None,
) -> Dict[str, Any]:
    """
    生成测试代码
    
    为指定文件生成测试。
    
    参数:
        target_files: 目标文件列表
        test_type: 测试类型（unit, integration, e2e）
        coverage_target: 覆盖率目标（默认 80）
        project_root: 项目根目录
        config_file: 配置文件路径（可选）
    
    返回:
        {
            "success": bool,
            "test_files": List[str],
            "coverage": float,
            "message": str
        }
    """
    try:
        # 加载配置
        if config_file and Path(config_file).exists():
            parser = ConfigParser()
            config = parser.parse_config(config_file)
        else:
            config = _create_default_config("生成测试", None)
        
        # 创建测试任务
        task_description = f"为以下文件生成 {test_type} 测试：\n" + "\n".join(f"- {f}" for f in target_files)
        task_description += f"\n目标覆盖率：{coverage_target}%"
        
        task_config = TaskConfig(
            id="test-gen-task",
            name="生成测试",
            type=TaskType.TEST,
            depends_on=[],
            ai_engine=list(config.ai_engines.keys())[0] if config.ai_engines else "qwen_code",
            max_retries=3,
            timeout=1800,
            config={
                "description": task_description,
                "target_files": target_files,
                "test_type": test_type,
                "coverage_target": coverage_target,
            }
        )
        
        # 执行任务
        engine = RalphEngineCore(config, project_root)
        result = engine.execute_task(task_config)
        
        return {
            "success": result.success,
            "test_files": result.files_changed or [],
            "coverage": 0.0,  # TODO: 实际计算覆盖率
            "message": result.message,
        }
        
    except Exception as e:
        logger.error(f"生成测试失败: {e}")
        return {
            "success": False,
            "test_files": [],
            "coverage": 0.0,
            "message": f"执行失败: {str(e)}",
        }


def refactor_code(
    target_files: List[str],
    refactor_goals: List[str],
    preserve_behavior: bool = True,
    project_root: str = ".",
    config_file: Optional[str] = None,
) -> Dict[str, Any]:
    """
    重构代码
    
    对指定文件进行重构。
    
    参数:
        target_files: 目标文件列表
        refactor_goals: 重构目标列表
        preserve_behavior: 是否保持行为不变（默认 True）
        project_root: 项目根目录
        config_file: 配置文件路径（可选）
    
    返回:
        {
            "success": bool,
            "files_changed": List[str],
            "improvements": List[str],
            "message": str
        }
    """
    try:
        # 加载配置
        if config_file and Path(config_file).exists():
            parser = ConfigParser()
            config = parser.parse_config(config_file)
        else:
            config = _create_default_config("重构代码", None)
        
        # 创建重构任务
        task_description = "重构以下文件：\n" + "\n".join(f"- {f}" for f in target_files)
        task_description += "\n\n重构目标：\n" + "\n".join(f"- {g}" for g in refactor_goals)
        if preserve_behavior:
            task_description += "\n\n要求：保持原有行为不变"
        
        task_config = TaskConfig(
            id="refactor-task",
            name="重构代码",
            type=TaskType.REFACTOR,
            depends_on=[],
            ai_engine=list(config.ai_engines.keys())[0] if config.ai_engines else "qwen_code",
            max_retries=3,
            timeout=1800,
            config={
                "description": task_description,
                "target_files": target_files,
                "refactor_goals": refactor_goals,
                "preserve_behavior": preserve_behavior,
            }
        )
        
        # 执行任务
        engine = RalphEngineCore(config, project_root)
        result = engine.execute_task(task_config)
        
        return {
            "success": result.success,
            "files_changed": result.files_changed or [],
            "improvements": refactor_goals,
            "message": result.message,
        }
        
    except Exception as e:
        logger.error(f"重构代码失败: {e}")
        return {
            "success": False,
            "files_changed": [],
            "improvements": [],
            "message": f"执行失败: {str(e)}",
        }


def fix_bug(
    bug_description: str,
    error_message: Optional[str] = None,
    affected_files: Optional[List[str]] = None,
    project_root: str = ".",
    config_file: Optional[str] = None,
) -> Dict[str, Any]:
    """
    修复 Bug
    
    根据 Bug 描述自动修复问题。
    
    参数:
        bug_description: Bug 描述
        error_message: 错误信息（可选）
        affected_files: 受影响的文件列表（可选）
        project_root: 项目根目录
        config_file: 配置文件路径（可选）
    
    返回:
        {
            "success": bool,
            "fix_description": str,
            "files_changed": List[str],
            "message": str
        }
    """
    try:
        # 加载配置
        if config_file and Path(config_file).exists():
            parser = ConfigParser()
            config = parser.parse_config(config_file)
        else:
            config = _create_default_config("修复 Bug", None)
        
        # 创建 Bug 修复任务
        task_description = f"修复 Bug：{bug_description}"
        if error_message:
            task_description += f"\n\n错误信息：\n{error_message}"
        if affected_files:
            task_description += "\n\n受影响的文件：\n" + "\n".join(f"- {f}" for f in affected_files)
        
        task_config = TaskConfig(
            id="bugfix-task",
            name="修复 Bug",
            type=TaskType.BUGFIX,
            depends_on=[],
            ai_engine=list(config.ai_engines.keys())[0] if config.ai_engines else "qwen_code",
            max_retries=3,
            timeout=1800,
            config={
                "description": task_description,
                "bug_description": bug_description,
                "error_message": error_message,
                "affected_files": affected_files or [],
            }
        )
        
        # 执行任务
        engine = RalphEngineCore(config, project_root)
        result = engine.execute_task(task_config)
        
        return {
            "success": result.success,
            "fix_description": result.message,
            "files_changed": result.files_changed or [],
            "message": result.message,
        }
        
    except Exception as e:
        logger.error(f"修复 Bug 失败: {e}")
        return {
            "success": False,
            "fix_description": "",
            "files_changed": [],
            "message": f"执行失败: {str(e)}",
        }


def generate_docs(
    doc_type: str,
    target_files: Optional[List[str]] = None,
    format: str = "markdown",
    project_root: str = ".",
    config_file: Optional[str] = None,
) -> Dict[str, Any]:
    """
    生成文档
    
    为项目或指定文件生成文档。
    
    参数:
        doc_type: 文档类型（api, readme, comments）
        target_files: 目标文件列表（可选）
        format: 文档格式（markdown, openapi, jsdoc）
        project_root: 项目根目录
        config_file: 配置文件路径（可选）
    
    返回:
        {
            "success": bool,
            "doc_files": List[str],
            "message": str
        }
    """
    try:
        # 加载配置
        if config_file and Path(config_file).exists():
            parser = ConfigParser()
            config = parser.parse_config(config_file)
        else:
            config = _create_default_config("生成文档", None)
        
        # 创建文档生成任务
        task_description = f"生成 {doc_type} 文档（格式：{format}）"
        if target_files:
            task_description += "\n\n目标文件：\n" + "\n".join(f"- {f}" for f in target_files)
        
        task_config = TaskConfig(
            id="docs-gen-task",
            name="生成文档",
            type=TaskType.DOCS,
            depends_on=[],
            ai_engine=list(config.ai_engines.keys())[0] if config.ai_engines else "qwen_code",
            max_retries=3,
            timeout=1800,
            config={
                "description": task_description,
                "doc_type": doc_type,
                "target_files": target_files or [],
                "format": format,
            }
        )
        
        # 执行任务
        engine = RalphEngineCore(config, project_root)
        result = engine.execute_task(task_config)
        
        return {
            "success": result.success,
            "doc_files": result.files_changed or [],
            "message": result.message,
        }
        
    except Exception as e:
        logger.error(f"生成文档失败: {e}")
        return {
            "success": False,
            "doc_files": [],
            "message": f"执行失败: {str(e)}",
        }


def _create_default_config(task_name: str, tech_stack: Optional[Dict[str, Any]]) -> Configuration:
    """
    创建默认配置
    
    当用户没有提供配置文件时使用。
    """
    from ralph.models.config import Configuration, EngineConfig, SystemSettings
    from ralph.models.enums import EngineType
    
    # 创建默认 AI 引擎配置
    default_engine = EngineConfig(
        type=EngineType.QWEN_CODE,
        model="qwen3-coder-plus",
        timeout=60,
    )
    
    # 创建默认项目配置
    project_config = ProjectConfig(
        name=task_name,
        type=ProjectType.FULLSTACK,
    )
    
    # 创建配置对象
    config = Configuration(
        project=project_config,
        tasks=[],
        settings=SystemSettings(),
        ai_engines={"qwen_code": default_engine},
    )
    
    return config


# 导出所有公共函数
__all__ = [
    "autonomous_develop",
    "generate_tests",
    "refactor_code",
    "fix_bug",
    "generate_docs",
]
