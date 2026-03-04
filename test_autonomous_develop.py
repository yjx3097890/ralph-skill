#!/usr/bin/env python3
"""
测试 autonomous_develop 函数
"""

import sys
from pathlib import Path

# 添加 Ralph Skill 到路径
skill_path = Path.home() / ".kiro" / "skills" / "ralph-skill"
sys.path.insert(0, str(skill_path / "src"))

from ralph import autonomous_develop


def test_simple_project():
    """测试创建简单项目"""
    print("=" * 60)
    print("测试：创建简单的 Hello World API")
    print("=" * 60)
    
    result = autonomous_develop(
        task_description="创建一个简单的 Hello World API",
        tech_stack={
            "backend": {
                "language": "go",
                "framework": "gin"
            }
        },
        requirements=[
            "实现 GET /hello 端点",
            "返回 JSON 格式",
            "包含单元测试"
        ],
        project_root="./test-hello-api"
    )
    
    print("\n结果:")
    print(f"  成功: {result['success']}")
    print(f"  完成任务: {result['tasks_completed']}/{result['tasks_total']}")
    print(f"  消息: {result['message']}")
    
    if "config_file" in result:
        print(f"  配置文件: {result['config_file']}")
    
    if not result['success']:
        print("\n失败的任务:")
        for task_id, task_result in result['results'].items():
            if not task_result['success']:
                print(f"    - {task_id}: {task_result['message']}")
    
    return result['success']


def test_with_config():
    """测试使用配置文件"""
    print("\n" + "=" * 60)
    print("测试：使用配置文件")
    print("=" * 60)
    
    # 首先创建一个配置文件
    config_content = """
project:
  name: "test-app"
  type: "backend"
  backend:
    language: "go"
    framework: "gin"

tasks:
  - id: "task-1"
    name: "初始化项目"
    type: "feature"
    ai_engine: "qwen_code"
    config:
      description: "创建基础项目结构"

ai_engines:
  qwen_code:
    type: "qwen_code"
    model: "qwen3-coder-plus"
    timeout: 60
"""
    
    config_path = Path("./test-with-config/ralph-config.yaml")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(config_content)
    
    print(f"✅ 已创建配置文件: {config_path}")
    
    result = autonomous_develop(
        task_description="执行配置文件中的任务",
        config_file="ralph-config.yaml",
        project_root="./test-with-config"
    )
    
    print("\n结果:")
    print(f"  成功: {result['success']}")
    print(f"  完成任务: {result['tasks_completed']}/{result['tasks_total']}")
    print(f"  消息: {result['message']}")
    
    return result['success']


def main():
    """运行所有测试"""
    print("开始测试 autonomous_develop 函数\n")
    
    tests = [
        ("简单项目", test_simple_project),
        ("使用配置文件", test_with_config),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # 打印总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{status} - {name}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\n总计: {passed}/{total} 通过")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
