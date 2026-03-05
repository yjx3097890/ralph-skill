#!/usr/bin/env python3
"""
Ralph Skill 命令行入口

用法：
    python -m ralph develop "创建一个 Todo 应用" --tech-stack frontend=vue3 backend=go
    python -m ralph develop "实现用户登录" --config ralph-config.yaml
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

from ralph.core.config_parser import ConfigParser
from ralph.core.ralph_engine import RalphEngineCore
from ralph.managers.task_planner import TaskPlanner
from ralph.models.config import ProjectConfig, EngineConfig

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger(__name__)


def autonomous_develop(
    task_description: str,
    tech_stack: Optional[Dict] = None,
    requirements: Optional[List[str]] = None,
    config_file: Optional[str] = None,
    project_root: str = ".",
    agent_driven: bool = False
) -> Dict:
    """
    自治开发主函数
    
    参数：
        task_description: 任务描述
        tech_stack: 技术栈配置，例如 {"frontend": {"framework": "vue3"}, "backend": {"language": "go"}}
        requirements: 需求列表
        config_file: 配置文件路径（可选，如果提供则使用配置文件）
        project_root: 项目根目录
        agent_driven: 是否使用 Agent 驱动模式（返回引擎实例供 Agent 控制）
    
    返回：
        执行结果字典，如果 agent_driven=True，则返回引擎实例
    """
    project_path = Path(project_root).resolve()
    
    # 如果提供了配置文件，直接使用
    if config_file:
        config_path = project_path / config_file
        if not config_path.exists():
            return {
                "success": False,
                "message": f"配置文件不存在: {config_file}"
            }
        
        parser = ConfigParser()
        config = parser.parse_config(str(config_path))
        
        # 创建引擎
        engine = RalphEngineCore(config, project_root=str(project_path))
        
        # Agent 驱动模式：返回引擎实例
        if agent_driven:
            return {
                "success": True,
                "engine": engine,
                "config": config,
                "message": "引擎已初始化，请使用 engine 对象控制任务执行"
            }
        
        # 自动模式：执行所有任务
        results = engine.run_all_tasks()
        
        success_count = sum(1 for r in results.values() if r.success)
        total_count = len(results)
        
        return {
            "success": success_count == total_count,
            "tasks_completed": success_count,
            "tasks_total": total_count,
            "results": {tid: {"success": r.success, "message": r.message} for tid, r in results.items()},
            "message": f"完成 {success_count}/{total_count} 个任务"
        }
    
    # 否则，自动生成配置
    planner = TaskPlanner()
    
    # 使用 plan_tasks 方法生成完整配置
    config = planner.plan_tasks(
        task_description=task_description,
        tech_stack=tech_stack,
        requirements=requirements
    )
    
    # 保存配置文件
    config_path = project_path / "ralph-config.yaml"
    parser = ConfigParser()
    parser.save_config(config, str(config_path))
    
    print(f"✅ 已生成配置文件: {config_path}")
    print(f"📋 任务数量: {len(config.tasks)}")
    
    # 创建引擎
    engine = RalphEngineCore(config, project_root=str(project_path))
    
    # Agent 驱动模式：返回引擎实例
    if agent_driven:
        return {
            "success": True,
            "engine": engine,
            "config": config,
            "config_file": str(config_path),
            "message": "引擎已初始化，请使用 engine 对象控制任务执行"
        }
    
    # 自动模式：执行所有任务
    results = engine.run_all_tasks()
    
    success_count = sum(1 for r in results.values() if r.success)
    total_count = len(results)
    
    return {
        "success": success_count == total_count,
        "tasks_completed": success_count,
        "tasks_total": total_count,
        "config_file": str(config_path),
        "results": {tid: {"success": r.success, "message": r.message} for tid, r in results.items()},
        "message": f"完成 {success_count}/{total_count} 个任务"
    }


def main():
    """命令行主函数"""
    parser = argparse.ArgumentParser(
        description="Ralph Skill - 企业级自治编程引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 自动生成配置并执行
  python -m ralph develop "创建一个 Todo 应用" \\
      --tech-stack '{"frontend": {"framework": "vue3"}, "backend": {"language": "go"}}' \\
      --requirements "支持添加、删除待办事项" "包含单元测试"
  
  # 使用配置文件
  python -m ralph develop "初始化项目" --config ralph-config.yaml
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # develop 命令
    develop_parser = subparsers.add_parser("develop", help="自治开发")
    develop_parser.add_argument("description", help="任务描述")
    develop_parser.add_argument("--tech-stack", type=str, help="技术栈配置（JSON 格式）")
    develop_parser.add_argument("--requirements", nargs="+", help="需求列表")
    develop_parser.add_argument("--config", help="配置文件路径")
    develop_parser.add_argument("--project-root", default=".", help="项目根目录")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    if args.command == "develop":
        # 解析技术栈
        tech_stack = None
        if args.tech_stack:
            try:
                tech_stack = json.loads(args.tech_stack)
            except json.JSONDecodeError:
                print(f"❌ 技术栈 JSON 格式错误: {args.tech_stack}", file=sys.stderr)
                return 1
        
        # 执行开发
        try:
            result = autonomous_develop(
                task_description=args.description,
                tech_stack=tech_stack,
                requirements=args.requirements,
                config_file=args.config,
                project_root=args.project_root
            )
            
            # 打印结果
            print("\n" + "=" * 60)
            print("执行结果")
            print("=" * 60)
            print(f"状态: {'✅ 成功' if result['success'] else '❌ 失败'}")
            print(f"完成任务: {result['tasks_completed']}/{result['tasks_total']}")
            if "config_file" in result:
                print(f"配置文件: {result['config_file']}")
            print(f"消息: {result['message']}")
            
            if not result['success']:
                print("\n失败的任务:")
                for task_id, task_result in result['results'].items():
                    if not task_result['success']:
                        print(f"  - {task_id}: {task_result['message']}")
            
            return 0 if result['success'] else 1
            
        except Exception as e:
            print(f"❌ 执行失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
