#!/usr/bin/env python3
"""
Ralph Skill 测试脚本

测试 Ralph Skill 的基本功能是否正常工作
"""

import os
import sys
from pathlib import Path

# 添加 ralph-skill 到 Python 路径
skill_path = Path.home() / ".kiro" / "skills" / "ralph-skill"
sys.path.insert(0, str(skill_path / "src"))

def test_skill_installation():
    """测试 Skill 是否正确安装"""
    print("=" * 60)
    print("测试 1: 检查 Skill 安装")
    print("=" * 60)
    
    # 检查目录是否存在
    if not skill_path.exists():
        print(f"❌ Skill 目录不存在: {skill_path}")
        return False
    
    print(f"✅ Skill 目录存在: {skill_path}")
    
    # 检查关键文件
    required_files = [
        "SKILL.md",
        "config.yaml",
        "src/ralph/__init__.py",
        "src/ralph/core/ralph_engine.py",
    ]
    
    for file in required_files:
        file_path = skill_path / file
        if file_path.exists():
            print(f"✅ {file} 存在")
        else:
            print(f"❌ {file} 不存在")
            return False
    
    return True


def test_imports():
    """测试模块导入"""
    print("\n" + "=" * 60)
    print("测试 2: 检查模块导入")
    print("=" * 60)
    
    try:
        # 测试核心模块导入
        import ralph
        print(f"✅ ralph 模块导入成功")
        
        from ralph.models.enums import EngineType, TaskType
        print(f"✅ ralph.models.enums 导入成功")
        print(f"   - 可用引擎: {[e.value for e in EngineType]}")
        print(f"   - 任务类型: {[t.value for t in TaskType]}")
        
        from ralph.adapters.ai_engine import AIEngineAdapter, EngineConfig
        print(f"✅ ralph.adapters.ai_engine 导入成功")
        
        from ralph.managers.task_manager import TaskManager
        print(f"✅ ralph.managers.task_manager 导入成功")
        
        return True
        
    except ImportError as e:
        print(f"❌ 模块导入失败: {e}")
        return False


def test_config_parsing():
    """测试配置文件解析"""
    print("\n" + "=" * 60)
    print("测试 3: 检查配置文件解析")
    print("=" * 60)
    
    try:
        from ralph.core.config_parser import ConfigParser
        
        config_file = skill_path / "config.yaml"
        if not config_file.exists():
            print(f"❌ 配置文件不存在: {config_file}")
            return False
        
        parser = ConfigParser()
        config = parser.parse_config(str(config_file))
        
        print(f"✅ 配置文件解析成功")
        print(f"   - 项目名称: {config.project.name}")
        print(f"   - 项目类型: {config.project.type.value}")
        print(f"   - AI 引擎数量: {len(config.ai_engines)}")
        
        if config.ai_engines:
            for name, engine in config.ai_engines.items():
                print(f"   - 引擎 '{name}': {engine.type.value} (模型: {engine.model})")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置解析失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ai_engine_creation():
    """测试 AI 引擎创建"""
    print("\n" + "=" * 60)
    print("测试 4: 检查 AI 引擎创建")
    print("=" * 60)
    
    try:
        from ralph.adapters.ai_engine import AIEngineAdapter, EngineConfig
        from ralph.models.enums import EngineType
        
        # 创建测试配置
        config = EngineConfig(
            engine_type=EngineType.QWEN_CODE,
            model_name="qwen3-coder-plus",
            timeout=60,
            extra_params={"cli_path": "qwen"}
        )
        
        print(f"✅ EngineConfig 创建成功")
        print(f"   - 引擎类型: {config.engine_type.value}")
        print(f"   - 模型名称: {config.model_name}")
        print(f"   - 超时时间: {config.timeout}s")
        print(f"   - CLI 路径: {config.extra_params.get('cli_path')}")
        
        # 尝试创建适配器（不初始化，因为可能没有 CLI 工具）
        try:
            adapter = AIEngineAdapter.create(EngineType.QWEN_CODE, config)
            print(f"✅ AI 引擎适配器创建成功")
            print(f"   - 适配器类型: {type(adapter).__name__}")
        except Exception as e:
            print(f"⚠️  AI 引擎适配器创建失败（可能缺少 CLI 工具）: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ AI 引擎创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_task_manager():
    """测试任务管理器"""
    print("\n" + "=" * 60)
    print("测试 5: 检查任务管理器")
    print("=" * 60)
    
    try:
        from ralph.managers.task_manager import TaskManager
        from ralph.models.task import TaskConfig
        from ralph.models.enums import TaskType
        
        # 创建测试任务配置
        task_config = TaskConfig(
            id="test-task-1",
            name="测试任务",
            type=TaskType.FEATURE,
            depends_on=[],
            ai_engine="qwen_code",
            max_retries=3,
            timeout=1800
        )
        
        print(f"✅ TaskConfig 创建成功")
        print(f"   - 任务 ID: {task_config.id}")
        print(f"   - 任务名称: {task_config.name}")
        print(f"   - 任务类型: {task_config.type.value}")
        print(f"   - AI 引擎: {task_config.ai_engine}")
        
        # 创建任务管理器
        manager = TaskManager()
        print(f"✅ TaskManager 创建成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 任务管理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "🚀 " * 20)
    print("Ralph Skill 功能测试")
    print("🚀 " * 20 + "\n")
    
    tests = [
        ("Skill 安装检查", test_skill_installation),
        ("模块导入测试", test_imports),
        ("配置文件解析", test_config_parsing),
        ("AI 引擎创建", test_ai_engine_creation),
        ("任务管理器测试", test_task_manager),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ 测试 '{name}' 发生异常: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # 打印总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status}: {name}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！Ralph Skill 工作正常。")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败，请检查配置。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
