#!/usr/bin/env python3
"""
Agent 驱动模式示例

展示如何在 Kiro 中使用 Ralph Skill 的 Agent 驱动模式。
"""

import sys
from pathlib import Path

# 添加 Ralph Skill 到路径
skill_path = Path.home() / ".kiro" / "skills" / "ralph-skill"
sys.path.insert(0, str(skill_path / "src"))

from ralph import autonomous_develop, TaskConfig


def simple_agent_driven_example():
    """简单的 Agent 驱动示例"""
    print("=" * 60)
    print("示例 1: 简单的 Agent 驱动执行")
    print("=" * 60)
    
    # 启用 Agent 驱动模式
    result = autonomous_develop(
        task_description="创建一个简单的 Todo 应用",
        tech_stack={
            "backend": {"language": "go", "framework": "gin"}
        },
        requirements=[
            "支持添加、删除待办事项",
            "包含单元测试"
        ],
        project_root="./example-project",
        agent_driven=True  # 启用 Agent 驱动模式
    )
    
    if not result["success"]:
        print(f"❌ 初始化失败: {result['message']}")
        return
    
    engine = result["engine"]
    config = result["config"]
    
    print(f"✅ 引擎已初始化")
    print(f"📋 任务列表: {len(config.tasks)} 个任务")
    
    # Agent 控制任务执行
    completed_tasks = set()
    
    for task_config in config.tasks:
        # 检查依赖
        if not all(dep in completed_tasks for dep in task_config.depends_on):
            print(f"⏭️  跳过任务 {task_config.name}（依赖未满足）")
            continue
        
        print(f"\n{'='*60}")
        print(f"执行任务: {task_config.name}")
        print(f"{'='*60}")
        
        task_result = engine.execute_task(task_config)
        
        if task_result.success:
            completed_tasks.add(task_config.id)
            print(f"✅ 任务完成")
            print(f"   - 修改文件: {len(task_result.files_changed)}")
            print(f"   - 执行时间: {task_result.execution_time:.2f}s")
        else:
            print(f"❌ 任务失败: {task_result.message}")
            print(f"   - 错误信息: {task_result.errors}")
            break
    
    print(f"\n完成 {len(completed_tasks)}/{len(config.tasks)} 个任务")


def intelligent_error_handling_example():
    """智能错误处理示例"""
    print("\n" + "=" * 60)
    print("示例 2: 智能错误处理")
    print("=" * 60)
    
    # 初始化引擎
    result = autonomous_develop(
        task_description="创建 Todo 应用",
        tech_stack={"backend": {"language": "go"}},
        project_root="./example-project",
        agent_driven=True
    )
    
    if not result["success"]:
        print(f"❌ 初始化失败: {result['message']}")
        return
    
    engine = result["engine"]
    config = result["config"]
    
    def analyze_error(task_result):
        """分析错误并返回修复策略"""
        test_output = task_result.test_output or ""
        
        if "database connection" in test_output.lower():
            return "fix_database"
        elif "import" in test_output.lower():
            return "fix_imports"
        elif "syntax error" in test_output.lower():
            return "fix_syntax"
        else:
            return "unknown"
    
    def create_fix_task(task_config, task_result, fix_type):
        """创建修复任务"""
        fix_descriptions = {
            "fix_database": f"修复数据库连接问题:\n{task_result.test_output}",
            "fix_imports": f"修复导入错误:\n{task_result.test_output}",
            "fix_syntax": f"修复语法错误:\n{task_result.test_output}",
        }
        
        return TaskConfig(
            id=f"{task_config.id}-fix-{fix_type}",
            name=f"修复 {task_config.name}",
            description=fix_descriptions.get(fix_type, f"修复错误:\n{task_result.test_output}"),
            depends_on=[task_config.id],
            timeout=task_config.timeout,
            config=task_config.config
        )
    
    # 执行任务并智能处理失败
    completed_tasks = set()
    
    for task_config in config.tasks:
        print(f"\n执行任务: {task_config.name}")
        
        task_result = engine.execute_task(task_config)
        
        if task_result.success:
            completed_tasks.add(task_config.id)
            print(f"✅ 任务完成")
        else:
            print(f"❌ 任务失败: {task_result.message}")
            
            # 分析错误
            fix_type = analyze_error(task_result)
            
            if fix_type != "unknown":
                # 创建并执行修复任务
                fix_task = create_fix_task(task_config, task_result, fix_type)
                print(f"🔧 创建修复任务: {fix_task.name}")
                
                fix_result = engine.execute_task(fix_task)
                
                if fix_result.success:
                    print(f"✅ 修复成功")
                    completed_tasks.add(task_config.id)
                else:
                    print(f"❌ 修复失败")
                    break
            else:
                print(f"⚠️ 无法自动修复，需要人工介入")
                break
    
    print(f"\n完成 {len(completed_tasks)}/{len(config.tasks)} 个任务")


def api_usage_example():
    """API 使用示例"""
    print("\n" + "=" * 60)
    print("示例 3: 使用新的 API")
    print("=" * 60)
    
    # 初始化引擎
    result = autonomous_develop(
        task_description="创建 Todo 应用",
        config_file="ralph-config.yaml",
        project_root="./example-project",
        agent_driven=True
    )
    
    if not result["success"]:
        print(f"❌ 初始化失败: {result['message']}")
        return
    
    engine = result["engine"]
    config = result["config"]
    
    # 假设我们要执行第一个任务
    task_config = config.tasks[0]
    
    print(f"\n1. 获取任务状态")
    task_status = engine.get_task_status(task_config.id)
    if task_status:
        print(f"   任务状态: {task_status.status}")
    
    print(f"\n2. 执行任务")
    task_result = engine.execute_task(task_config)
    
    if not task_result.success:
        print(f"   ❌ 任务失败")
        
        print(f"\n3. 获取代码差异")
        diff = engine.get_code_diff(task_config.id)
        print(f"   代码变更:\n{diff[:200]}...")  # 只显示前 200 字符
        
        print(f"\n4. 创建修复任务")
        fix_task = TaskConfig(
            id=f"{task_config.id}-fix",
            name=f"修复 {task_config.name}",
            description=f"修复以下错误:\n{task_result.test_output}",
            depends_on=[task_config.id]
        )
        
        print(f"\n5. 添加修复任务")
        task_id = engine.add_task(fix_task)
        print(f"   新任务 ID: {task_id}")
        
        print(f"\n6. 执行修复任务")
        fix_result = engine.execute_task(fix_task)
        
        if not fix_result.success:
            print(f"\n7. 回滚代码")
            success = engine.rollback_task(task_config.id)
            print(f"   回滚{'成功' if success else '失败'}")
    else:
        print(f"   ✅ 任务成功")
    
    print(f"\n8. 更新任务配置")
    success = engine.update_task(task_config.id, {
        "timeout": 3600,  # 增加超时时间
    })
    print(f"   更新{'成功' if success else '失败'}")


if __name__ == "__main__":
    # 运行示例
    try:
        simple_agent_driven_example()
        # intelligent_error_handling_example()
        # api_usage_example()
    except Exception as e:
        print(f"\n❌ 示例执行失败: {e}")
        import traceback
        traceback.print_exc()
