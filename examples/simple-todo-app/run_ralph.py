#!/usr/bin/env python3
"""
Ralph Skill 运行脚本

使用方法：
1. 将此文件复制到你的项目目录
2. 确保项目目录中有 ralph-config.yaml
3. 在 Ralph Skill 的虚拟环境中运行：
   cd ~/.kiro/skills/ralph-skill
   poetry run python /path/to/your/project/run_ralph.py
"""

import sys
from pathlib import Path

# 添加 Ralph Skill 到 Python 路径
skill_path = Path.home() / ".kiro" / "skills" / "ralph-skill"
sys.path.insert(0, str(skill_path / "src"))

from ralph.core.config_parser import ConfigParser
from ralph.core.ralph_engine import RalphEngine


def print_banner():
    """打印欢迎横幅"""
    print("\n" + "=" * 60)
    print("🚀 Ralph Skill - 自治编程引擎")
    print("=" * 60 + "\n")


def print_config_summary(config):
    """打印配置摘要"""
    print("📋 项目配置")
    print("-" * 60)
    print(f"项目名称: {config.project.name}")
    print(f"项目类型: {config.project.type.value}")
    
    if config.project.frontend:
        print(f"前端框架: {config.project.frontend.framework.value}")
    
    if config.project.backend:
        print(f"后端语言: {config.project.backend.language}")
        print(f"后端框架: {config.project.backend.framework.value}")
    
    print(f"\n📦 任务数量: {len(config.tasks)}")
    print("-" * 60)
    
    for i, task in enumerate(config.tasks, 1):
        deps = f" (依赖: {', '.join(task.depends_on)})" if task.depends_on else ""
        print(f"{i}. [{task.type.value}] {task.name}{deps}")
    
    print()


def print_results(results):
    """打印执行结果"""
    print("\n" + "=" * 60)
    print("📊 执行结果")
    print("=" * 60 + "\n")
    
    success_count = sum(1 for r in results.values() if r.success)
    total_count = len(results)
    
    for task_id, result in results.items():
        status = "✅" if result.success else "❌"
        print(f"{status} {task_id}")
        if result.message:
            print(f"   {result.message}")
        print()
    
    print("-" * 60)
    print(f"总计: {success_count}/{total_count} 任务成功")
    
    if success_count == total_count:
        print("\n🎉 所有任务执行成功！")
    else:
        print(f"\n⚠️  有 {total_count - success_count} 个任务失败")
    
    print()


def main():
    """主函数"""
    print_banner()
    
    # 检查配置文件
    config_file = Path("ralph-config.yaml")
    if not config_file.exists():
        print("❌ 错误: 找不到配置文件 ralph-config.yaml")
        print("\n请确保：")
        print("1. 当前目录是你的项目目录")
        print("2. 项目目录中有 ralph-config.yaml 文件")
        print("\n示例配置文件位于：")
        print("~/.kiro/skills/ralph-skill/examples/simple-todo-app/ralph-config.yaml")
        return 1
    
    try:
        # 解析配置文件
        print("📖 正在解析配置文件...")
        parser = ConfigParser()
        config = parser.parse_config(str(config_file))
        print("✅ 配置文件解析成功\n")
        
        # 打印配置摘要
        print_config_summary(config)
        
        # 确认执行
        response = input("是否开始执行任务？(y/n): ")
        if response.lower() != 'y':
            print("已取消执行")
            return 0
        
        print("\n🚀 开始执行任务...\n")
        
        # 创建 Ralph 引擎并执行任务
        engine = RalphEngine(config)
        results = engine.run_all_tasks()
        
        # 打印结果
        print_results(results)
        
        # 返回状态码
        return 0 if all(r.success for r in results.values()) else 1
        
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
