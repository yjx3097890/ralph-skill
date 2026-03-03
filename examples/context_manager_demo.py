"""
上下文管理器演示

展示 ContextManager 的基本用法和功能。
"""

from ralph.managers.context_manager import ContextManager


def demo_basic_truncation():
    """演示基本的截断功能"""
    print("=" * 80)
    print("演示 1: 基本截断功能")
    print("=" * 80)
    
    # 创建上下文管理器
    manager = ContextManager(
        max_size=500,
        head_size=150,
        tail_size=150
    )
    
    # 创建一个长文本
    long_text = "这是一段很长的日志输出。\n" * 100
    
    print(f"\n原始文本长度: {len(long_text)} 字符")
    print(f"原始文本行数: {long_text.count(chr(10))} 行")
    
    # 截断文本
    truncated = manager.truncate_output(long_text)
    
    print(f"\n截断后文本长度: {len(truncated)} 字符")
    print(f"\n截断后的文本:\n{truncated}")
    
    # 获取统计信息
    stats = manager.get_truncation_stats()
    if stats:
        print(f"\n统计信息:")
        print(f"  - 原始长度: {stats.original_length:,} 字符")
        print(f"  - 截断后长度: {stats.truncated_length:,} 字符")
        print(f"  - 截断字符数: {stats.truncated_chars:,} 字符")
        print(f"  - 截断行数: {stats.truncated_lines:,} 行")
        print(f"  - 是否截断: {stats.was_truncated}")


def demo_no_truncation():
    """演示短文本不会被截断"""
    print("\n" + "=" * 80)
    print("演示 2: 短文本不会被截断")
    print("=" * 80)
    
    manager = ContextManager(max_size=1000)
    
    short_text = "这是一段短文本,不会被截断。\n" * 5
    
    print(f"\n原始文本长度: {len(short_text)} 字符")
    
    result = manager.truncate_output(short_text)
    
    print(f"截断后文本长度: {len(result)} 字符")
    print(f"文本是否被截断: {manager.get_truncation_stats().was_truncated}")
    print(f"\n文本内容:\n{result}")


def demo_error_log_truncation():
    """演示错误日志截断"""
    print("\n" + "=" * 80)
    print("演示 3: 错误日志截断")
    print("=" * 80)
    
    manager = ContextManager(
        max_size=800,
        head_size=250,
        tail_size=250
    )
    
    # 模拟一个包含错误信息的长日志
    error_log = """
[ERROR] 测试执行失败
Traceback (most recent call last):
  File "test_example.py", line 42, in test_function
    assert result == expected
AssertionError: 1 != 2

""" + ("." * 1000) + """

[ERROR] 最后的错误信息
Failed to execute test suite
Exit code: 1
"""
    
    print(f"\n原始日志长度: {len(error_log)} 字符")
    
    truncated_log = manager.truncate_output(error_log)
    
    print(f"截断后日志长度: {len(truncated_log)} 字符")
    print(f"\n截断后的日志:\n{truncated_log}")
    
    stats = manager.get_truncation_stats()
    if stats:
        print(f"\n保留了开头 {stats.head_size} 字符和结尾 {stats.tail_size} 字符")


def demo_config_update():
    """演示配置更新"""
    print("\n" + "=" * 80)
    print("演示 4: 动态配置更新")
    print("=" * 80)
    
    manager = ContextManager(max_size=500)
    
    print(f"\n初始配置: {manager.get_config()}")
    
    # 更新配置
    manager.update_config(
        max_size=1000,
        head_size=300,
        tail_size=300
    )
    
    print(f"更新后配置: {manager.get_config()}")
    
    # 使用新配置截断
    text = "A" * 1500
    result = manager.truncate_output(text)
    
    stats = manager.get_truncation_stats()
    if stats:
        print(f"\n使用新配置截断:")
        print(f"  - 原始长度: {stats.original_length}")
        print(f"  - 截断后长度: {stats.truncated_length}")
        print(f"  - 头部大小: {stats.head_size}")
        print(f"  - 尾部大小: {stats.tail_size}")


def demo_multibyte_characters():
    """演示多字节字符处理"""
    print("\n" + "=" * 80)
    print("演示 5: 多字节字符(中文)处理")
    print("=" * 80)
    
    manager = ContextManager(max_size=300, head_size=100, tail_size=100)
    
    # 创建包含中文的文本
    chinese_text = "这是中文测试内容,用于验证多字节字符的正确处理。" * 20
    
    print(f"\n原始文本长度: {len(chinese_text)} 字符")
    print(f"原始文本字节数: {len(chinese_text.encode('utf-8'))} 字节")
    
    result = manager.truncate_output(chinese_text)
    
    print(f"\n截断后文本长度: {len(result)} 字符")
    print(f"截断后文本字节数: {len(result.encode('utf-8'))} 字节")
    
    # 验证结果是有效的 UTF-8 字符串
    try:
        result.encode('utf-8')
        print("\n✓ 截断后的文本是有效的 UTF-8 字符串")
    except UnicodeEncodeError:
        print("\n✗ 截断后的文本包含无效字符")
    
    print(f"\n截断后的文本片段:\n{result[:200]}...")


def main():
    """运行所有演示"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "上下文管理器功能演示" + " " * 20 + "║")
    print("╚" + "=" * 78 + "╝")
    
    demo_basic_truncation()
    demo_no_truncation()
    demo_error_log_truncation()
    demo_config_update()
    demo_multibyte_characters()
    
    print("\n" + "=" * 80)
    print("演示完成!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
