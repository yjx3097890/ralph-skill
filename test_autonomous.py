#!/usr/bin/env python3
"""
测试 Ralph Skill 的自治开发功能
"""

import sys
from pathlib import Path

# 添加 Ralph Skill 到 Python 路径
skill_path = Path.home() / ".kiro" / "skills" / "ralph-skill"
sys.path.insert(0, str(skill_path / "src"))

from ralph import autonomous_develop


def test_simple_task():
    """测试简单的任务"""
    print("\n" + "=" * 60)
    print("测试：创建一个简单的 Hello World 应用")
    print("=" * 60 + "\n")
    
    result = autonomous_develop(
        task_description="创建一个简单的 Hello World 应用",
        tech_stack={
            "backend": {
                "language": "go",
                "framework": "gin"
            }
        },
        requirements=[
            "实现一个 GET /hello 端点",
            "返回 JSON 格式的问候消息",
            "包含基础的单元测试"
        ],
        project_root="./test-project"
    )
    
    print("\n" + "=" * 60)
    print("执行结果")
    print("=" * 60)
    print(f"成功: {result['success']}")
    print(f"完成任务: {result['tasks_completed']}/{result['tasks_total']}")
    print(f"修改文件: {len(result['files_changed'])} 个")
    print(f"消息: {result['message']}")
    
    if result['results']:
        print("\n任务详情:")
        for task_id, task_result in result['results'].items():
            status = "✅" if task_result['success'] else "❌"
            print(f"  {status} {task_id}: {task_result['message']}")
            print(f"     执行时间: {task_result['execution_time']:.2f}s")
    
    return result['success']


def main():
    """主函数"""
    print("\n🚀 Ralph Skill 自治开发测试\n")
    
    try:
        success = test_simple_task()
        
        if success:
            print("\n✅ 测试通过！")
            return 0
        else:
            print("\n❌ 测试失败")
            return 1
            
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
