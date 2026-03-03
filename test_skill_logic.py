#!/usr/bin/env python3
"""
测试 Ralph Skill 的逻辑（不调用真实 AI）
"""

import sys
from pathlib import Path

# 添加 Ralph Skill 到 Python 路径
skill_path = Path.home() / ".kiro" / "skills" / "ralph-skill"
sys.path.insert(0, str(skill_path / "src"))


def test_task_planner():
    """测试任务规划器"""
    print("\n" + "=" * 60)
    print("测试 1: 任务规划器")
    print("=" * 60 + "\n")
    
    from ralph.managers.task_planner import TaskPlanner
    
    planner = TaskPlanner()
    config = planner.plan_tasks(
        task_description="创建一个 Todo 应用",
        tech_stack={
            "frontend": {"framework": "vue3"},
            "backend": {"language": "go", "framework": "gin"}
        },
        requirements=[
            "支持添加、删除、完成待办事项",
            "前端使用 Vue3",
            "后端使用 Go + Gin"
        ]
    )
    
    print(f"✅ 项目名称: {config.project.name}")
    print(f"✅ 项目类型: {config.project.type.value}")
    print(f"✅ 生成任务数: {len(config.tasks)}")
    
    print("\n任务列表:")
    for i, task in enumerate(config.tasks, 1):
        deps = f" (依赖: {', '.join(task.depends_on)})" if task.depends_on else ""
        print(f"  {i}. [{task.type.value}] {task.name}{deps}")
    
    # 验证任务依赖关系
    assert len(config.tasks) > 0, "应该生成至少一个任务"
    assert config.project.frontend is not None, "应该有前端配置"
    assert config.project.backend is not None, "应该有后端配置"
    
    print("\n✅ 任务规划器测试通过")
    return True


def test_config_generation():
    """测试配置生成"""
    print("\n" + "=" * 60)
    print("测试 2: 配置生成")
    print("=" * 60 + "\n")
    
    from ralph.managers.task_planner import TaskPlanner
    from ralph.core.config_parser import ConfigParser
    
    planner = TaskPlanner()
    config = planner.plan_tasks(
        task_description="创建一个博客系统",
        tech_stack={
            "backend": {"language": "python", "framework": "fastapi"}
        }
    )
    
    # 生成 YAML
    parser = ConfigParser()
    yaml_content = parser.pretty_print(config, format="yaml")
    
    print("生成的配置文件:")
    print("-" * 60)
    print(yaml_content[:500] + "...")  # 只显示前 500 字符
    print("-" * 60)
    
    # 验证可以重新解析
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        temp_path = f.name
    
    try:
        parsed_config = parser.parse_config(temp_path)
        assert parsed_config.project.name == config.project.name
        assert len(parsed_config.tasks) == len(config.tasks)
        print("\n✅ 配置可以正确序列化和反序列化")
    finally:
        Path(temp_path).unlink()
    
    print("✅ 配置生成测试通过")
    return True


def test_project_type_inference():
    """测试项目类型推断"""
    print("\n" + "=" * 60)
    print("测试 3: 项目类型推断")
    print("=" * 60 + "\n")
    
    from ralph.managers.task_planner import TaskPlanner
    from ralph.models.enums import ProjectType
    
    planner = TaskPlanner()
    
    # 测试全栈项目
    config1 = planner.plan_tasks(
        "创建一个全栈应用",
        tech_stack={"frontend": {}, "backend": {}}
    )
    assert config1.project.type == ProjectType.FULLSTACK
    print("✅ 全栈项目识别正确")
    
    # 测试前端项目
    config2 = planner.plan_tasks(
        "创建一个前端界面",
        tech_stack={"frontend": {}}
    )
    assert config2.project.type == ProjectType.FRONTEND
    print("✅ 前端项目识别正确")
    
    # 测试后端项目
    config3 = planner.plan_tasks(
        "创建一个 API 服务",
        tech_stack={"backend": {}}
    )
    assert config3.project.type == ProjectType.BACKEND
    print("✅ 后端项目识别正确")
    
    print("\n✅ 项目类型推断测试通过")
    return True


def test_task_dependencies():
    """测试任务依赖关系"""
    print("\n" + "=" * 60)
    print("测试 4: 任务依赖关系")
    print("=" * 60 + "\n")
    
    from ralph.managers.task_planner import TaskPlanner
    
    planner = TaskPlanner()
    config = planner.plan_tasks(
        "创建一个完整的应用",
        tech_stack={"frontend": {}, "backend": {}}
    )
    
    # 验证依赖关系
    task_ids = {task.id for task in config.tasks}
    
    for task in config.tasks:
        for dep in task.depends_on:
            assert dep in task_ids, f"任务 {task.id} 依赖不存在的任务 {dep}"
    
    print(f"✅ 所有任务依赖关系有效")
    
    # 验证没有循环依赖
    def has_cycle(tasks):
        visited = set()
        rec_stack = set()
        
        def visit(task_id):
            if task_id in rec_stack:
                return True
            if task_id in visited:
                return False
            
            visited.add(task_id)
            rec_stack.add(task_id)
            
            task = next((t for t in tasks if t.id == task_id), None)
            if task:
                for dep in task.depends_on:
                    if visit(dep):
                        return True
            
            rec_stack.remove(task_id)
            return False
        
        for task in tasks:
            if task.id not in visited:
                if visit(task.id):
                    return True
        return False
    
    assert not has_cycle(config.tasks), "存在循环依赖"
    print("✅ 没有循环依赖")
    
    print("\n✅ 任务依赖关系测试通过")
    return True


def main():
    """主函数"""
    print("\n🧪 Ralph Skill 逻辑测试\n")
    
    tests = [
        ("任务规划器", test_task_planner),
        ("配置生成", test_config_generation),
        ("项目类型推断", test_project_type_inference),
        ("任务依赖关系", test_task_dependencies),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"\n❌ 测试 '{name}' 失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    if failed == 0:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️  有 {failed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
