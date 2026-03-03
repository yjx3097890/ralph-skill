"""
钩子系统使用示例

演示如何使用钩子系统进行代码格式化、测试前后的自动化操作。
"""

import os
from datetime import datetime

from ralph.managers.hook_system import HookSystem
from ralph.models.enums import HookType
from ralph.models.hook import HookConfig, HookContext


def main():
    """主函数"""
    print("=" * 60)
    print("钩子系统使用示例")
    print("=" * 60)
    print()
    
    # 创建钩子系统实例
    hook_system = HookSystem()
    
    # 1. 注册 pre-test 钩子（代码格式化）
    print("1. 注册 pre-test 钩子（代码格式化）")
    print("-" * 60)
    
    format_hook = HookConfig(
        name="format_python_code",
        hook_type=HookType.PRE_TEST,
        command="echo '运行代码格式化工具: black .'",
        timeout=60,
        max_retries=1,
        continue_on_failure=False,
    )
    
    hook_system.register_hook(format_hook)
    print(f"✓ 已注册钩子: {format_hook.name}")
    print()
    
    # 2. 注册 post-test 钩子（清理临时文件）
    print("2. 注册 post-test 钩子（清理临时文件）")
    print("-" * 60)
    
    cleanup_hook = HookConfig(
        name="cleanup_temp_files",
        hook_type=HookType.POST_TEST,
        command="echo '清理临时文件: rm -rf tmp/'",
        timeout=30,
        continue_on_failure=True,  # 清理失败不影响任务
    )
    
    hook_system.register_hook(cleanup_hook)
    print(f"✓ 已注册钩子: {cleanup_hook.name}")
    print()
    
    # 3. 注册多个 pre-test 钩子
    print("3. 注册多个 pre-test 钩子")
    print("-" * 60)
    
    lint_hook = HookConfig(
        name="lint_code",
        hook_type=HookType.PRE_TEST,
        command="echo '运行代码检查工具: flake8 .'",
        timeout=60,
        continue_on_failure=True,  # Lint 失败不阻止测试
    )
    
    hook_system.register_hook(lint_hook)
    print(f"✓ 已注册钩子: {lint_hook.name}")
    print()
    
    # 4. 查看已注册的钩子
    print("4. 查看已注册的钩子")
    print("-" * 60)
    
    for hook_type in HookType:
        hooks = hook_system.get_hooks(hook_type)
        if hooks:
            print(f"{hook_type.value}: {len(hooks)} 个钩子")
            for hook in hooks:
                print(f"  - {hook.name}: {hook.command}")
    print()
    
    # 5. 执行 pre-test 钩子
    print("5. 执行 pre-test 钩子")
    print("-" * 60)
    
    context = HookContext(
        hook_type=HookType.PRE_TEST,
        task_id="task_001",
        task_name="实现用户认证功能",
        timestamp=datetime.now(),
        working_directory=os.getcwd(),
        environment={"PYTHONPATH": os.getcwd()},
    )
    
    try:
        results = hook_system.execute_hooks(HookType.PRE_TEST, context)
        
        print(f"执行了 {len(results)} 个钩子:")
        for result in results:
            status = "✓ 成功" if result.success else "✗ 失败"
            print(f"  {status} {result.hook_name} ({result.execution_time:.2f}秒)")
            if result.output:
                print(f"    输出: {result.output.strip()}")
            if result.error:
                print(f"    错误: {result.error}")
    except Exception as e:
        print(f"✗ 钩子执行失败: {e}")
    print()
    
    # 6. 执行 post-test 钩子
    print("6. 执行 post-test 钩子")
    print("-" * 60)
    
    context = HookContext(
        hook_type=HookType.POST_TEST,
        task_id="task_001",
        task_name="实现用户认证功能",
        timestamp=datetime.now(),
        working_directory=os.getcwd(),
    )
    
    try:
        results = hook_system.execute_hooks(HookType.POST_TEST, context)
        
        print(f"执行了 {len(results)} 个钩子:")
        for result in results:
            status = "✓ 成功" if result.success else "✗ 失败"
            print(f"  {status} {result.hook_name} ({result.execution_time:.2f}秒)")
            if result.output:
                print(f"    输出: {result.output.strip()}")
    except Exception as e:
        print(f"✗ 钩子执行失败: {e}")
    print()
    
    # 7. 查看执行历史
    print("7. 查看执行历史")
    print("-" * 60)
    
    history = hook_system.get_execution_history(limit=10)
    print(f"最近 {len(history)} 次钩子执行:")
    
    for record in history:
        status = "✓" if record.is_successful else "✗"
        duration = f"{record.duration:.2f}s" if record.duration else "N/A"
        print(f"  {status} {record.hook_name} ({record.hook_type.value}) - {duration}")
        if record.retry_count > 0:
            print(f"    重试次数: {record.retry_count}")
    print()
    
    # 8. 查看统计信息
    print("8. 查看统计信息")
    print("-" * 60)
    
    stats = hook_system.get_statistics()
    print(f"已注册钩子总数: {stats['total_registered_hooks']}")
    print(f"执行次数: {stats['total_executions']}")
    print(f"成功次数: {stats['successful_executions']}")
    print(f"失败次数: {stats['failed_executions']}")
    print(f"成功率: {stats['success_rate']:.1f}%")
    print()
    
    print("各类型钩子数量:")
    for hook_type, count in stats['hooks_by_type'].items():
        if count > 0:
            print(f"  {hook_type}: {count}")
    print()
    
    # 9. 演示钩子重试机制
    print("9. 演示钩子重试机制")
    print("-" * 60)
    
    retry_hook = HookConfig(
        name="flaky_operation",
        hook_type=HookType.PRE_TASK,
        command="echo '模拟不稳定的操作' && exit 0",  # 这里简化为成功
        timeout=10,
        max_retries=3,
        retry_delay=1,
        continue_on_failure=True,
    )
    
    hook_system.register_hook(retry_hook)
    print(f"✓ 已注册带重试的钩子: {retry_hook.name}")
    print(f"  最大重试次数: {retry_hook.max_retries}")
    print(f"  重试延迟: {retry_hook.retry_delay}秒")
    print()
    
    context = HookContext(
        hook_type=HookType.PRE_TASK,
        task_id="task_002",
        task_name="测试重试机制",
        timestamp=datetime.now(),
        working_directory=os.getcwd(),
    )
    
    results = hook_system.execute_hooks(HookType.PRE_TASK, context)
    
    for result in results:
        status = "✓ 成功" if result.success else "✗ 失败"
        print(f"{status} {result.hook_name}")
    
    # 查看重试记录
    history = hook_system.get_execution_history(hook_type=HookType.PRE_TASK, limit=1)
    if history:
        print(f"重试次数: {history[0].retry_count}")
    print()
    
    # 10. 注销钩子
    print("10. 注销钩子")
    print("-" * 60)
    
    result = hook_system.unregister_hook(HookType.PRE_TEST, "lint_code")
    if result:
        print("✓ 已注销钩子: lint_code")
    else:
        print("✗ 钩子不存在: lint_code")
    
    # 验证钩子已注销
    hooks = hook_system.get_hooks(HookType.PRE_TEST)
    print(f"剩余 pre-test 钩子: {len(hooks)} 个")
    print()
    
    print("=" * 60)
    print("示例完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()

