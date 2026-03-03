"""
AI 引擎适配器使用示例

演示如何使用 AI 引擎适配器进行代码生成、重构和错误修复。
"""

from ralph.adapters import AIEngineManager, EngineConfig
from ralph.models.enums import EngineType, ErrorCategory


def example_basic_usage():
    """基础使用示例"""
    print("=== 基础使用示例 ===\n")
    
    # 创建引擎配置
    config = EngineConfig(
        engine_type=EngineType.QWEN_CODE,
        api_key="your-api-key-here",
        model_name="qwen-coder-plus",
        temperature=0.7,
        max_tokens=2048
    )
    
    # 创建引擎管理器
    manager = AIEngineManager(
        primary_engine=EngineType.QWEN_CODE,
        fallback_engines=[EngineType.CLAUDE, EngineType.GPT4]
    )
    
    # 注册主引擎
    manager.register_engine(EngineType.QWEN_CODE, config)
    
    # 生成代码
    result = manager.generate_code(
        prompt="实现一个快速排序算法",
        language="python",
        context="需要支持自定义比较函数"
    )
    
    print(f"生成成功: {result.success}")
    print(f"生成的代码:\n{result.code}")
    print(f"说明: {result.explanation}")
    if result.warnings:
        print(f"警告: {', '.join(result.warnings)}")
    print()


def example_code_refactoring():
    """代码重构示例"""
    print("=== 代码重构示例 ===\n")
    
    # 创建 Aider 引擎配置（擅长重构）
    config = EngineConfig(
        engine_type=EngineType.AIDER,
        model_name="aider-refactor"
    )
    
    manager = AIEngineManager(primary_engine=EngineType.AIDER)
    manager.register_engine(EngineType.AIDER, config)
    
    # 待重构的代码
    legacy_code = """
def process_data(data):
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result
"""
    
    # 重构代码
    result = manager.refactor_code(
        code=legacy_code,
        requirements="使用列表推导式简化代码，添加类型注解"
    )
    
    print(f"重构成功: {result.success}")
    print(f"重构后的代码:\n{result.code}")
    print(f"变更说明: {', '.join(result.changes)}")
    print()


def example_error_fixing():
    """错误修复示例"""
    print("=== 错误修复示例 ===\n")
    
    config = EngineConfig(
        engine_type=EngineType.CLAUDE,
        api_key="your-api-key-here"
    )
    
    manager = AIEngineManager(primary_engine=EngineType.CLAUDE)
    manager.register_engine(EngineType.CLAUDE, config)
    
    # 包含错误的代码
    buggy_code = """
def calculate_average(numbers):
    total = sum(numbers)
    return total / len(numbers)

# 调用函数
result = calculate_average([])
print(result)
"""
    
    # 错误信息
    errors = [
        "ZeroDivisionError: division by zero",
        "Line 3: len(numbers) is 0"
    ]
    
    # 修复错误
    result = manager.fix_errors(
        code=buggy_code,
        errors=errors,
        error_category=ErrorCategory.RUNTIME_ERROR
    )
    
    print(f"修复成功: {result.success}")
    print(f"修复后的代码:\n{result.code}")
    print(f"说明: {result.explanation}")
    print()


def example_engine_switching():
    """引擎切换示例"""
    print("=== 引擎切换示例 ===\n")
    
    # 创建管理器并注册多个引擎
    manager = AIEngineManager(
        primary_engine=EngineType.QWEN_CODE,
        fallback_engines=[EngineType.CLAUDE, EngineType.GPT4]
    )
    
    # 注册 Qwen Code
    qwen_config = EngineConfig(
        engine_type=EngineType.QWEN_CODE,
        api_key="qwen-key"
    )
    manager.register_engine(EngineType.QWEN_CODE, qwen_config)
    
    # 注册 Claude
    claude_config = EngineConfig(
        engine_type=EngineType.CLAUDE,
        api_key="claude-key"
    )
    manager.register_engine(EngineType.CLAUDE, claude_config)
    
    # 使用主引擎
    print(f"当前引擎: {manager.current_engine.__class__.__name__}")
    
    # 切换到 Claude
    if manager.switch_engine(EngineType.CLAUDE):
        print(f"切换后引擎: {manager.current_engine.__class__.__name__}")
    
    # 查看所有引擎状态
    statuses = manager.get_all_statuses()
    print("\n所有引擎状态:")
    for engine_type, status in statuses.items():
        print(f"  {engine_type.value}:")
        print(f"    可用: {status.is_available}")
        print(f"    调用次数: {status.total_calls}")
        print(f"    总 Token: {status.total_tokens}")
        print(f"    总成本: ${status.total_cost:.4f}")
    print()


def example_fallback_mechanism():
    """故障转移示例"""
    print("=== 故障转移示例 ===\n")
    
    manager = AIEngineManager(
        primary_engine=EngineType.QWEN_CODE,
        fallback_engines=[EngineType.CLAUDE, EngineType.GPT4]
    )
    
    # 只注册备用引擎（模拟主引擎不可用）
    claude_config = EngineConfig(
        engine_type=EngineType.CLAUDE,
        api_key="claude-key"
    )
    manager.register_engine(EngineType.CLAUDE, claude_config)
    
    # 尝试故障转移
    if manager.try_fallback():
        print(f"成功切换到备用引擎: {manager.current_engine.__class__.__name__}")
        
        # 使用备用引擎生成代码
        result = manager.generate_code(
            prompt="实现二分查找算法",
            language="python"
        )
        print(f"使用备用引擎生成代码成功: {result.success}")
    else:
        print("没有可用的备用引擎")
    print()


def example_status_tracking():
    """状态跟踪示例"""
    print("=== 状态跟踪示例 ===\n")
    
    config = EngineConfig(engine_type=EngineType.GPT4)
    manager = AIEngineManager(primary_engine=EngineType.GPT4)
    manager.register_engine(EngineType.GPT4, config)
    
    # 获取当前引擎
    engine = manager.get_current_engine()
    
    # 模拟多次调用
    for i in range(3):
        engine.update_status(
            tokens_used=100 * (i + 1),
            cost=0.01 * (i + 1)
        )
    
    # 查看状态
    status = engine.get_status()
    print(f"引擎类型: {status.engine_type.value}")
    print(f"总调用次数: {status.total_calls}")
    print(f"总 Token 使用: {status.total_tokens}")
    print(f"总成本: ${status.total_cost:.4f}")
    print(f"最后使用时间: {status.last_used}")
    print()


def main():
    """运行所有示例"""
    print("AI 引擎适配器使用示例\n")
    print("=" * 60)
    print()
    
    try:
        example_basic_usage()
        example_code_refactoring()
        example_error_fixing()
        example_engine_switching()
        example_fallback_mechanism()
        example_status_tracking()
        
        print("=" * 60)
        print("\n所有示例运行完成！")
        print("\n注意: 这些是占位符实现，实际使用时需要配置真实的 API 密钥。")
        
    except Exception as e:
        print(f"运行示例时出错: {e}")


if __name__ == "__main__":
    main()
