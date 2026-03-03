# 钩子系统使用指南

## 概述

钩子系统（Hook System）是 Ralph Engine 的核心组件之一，用于在任务执行的不同阶段自动运行自定义脚本或命令。通过钩子系统，您可以实现代码格式化、环境清理、测试前准备等自动化操作。

## 核心功能

- **钩子注册和管理**：注册、注销和查询钩子
- **钩子执行**：按类型执行钩子，支持超时控制
- **重试机制**：自动重试失败的钩子
- **执行历史**：记录和查询钩子执行历史
- **统计信息**：查看钩子系统的统计数据
- **并发安全**：线程安全的钩子管理

## 钩子类型

系统支持以下四种钩子类型：

| 钩子类型 | 说明 | 典型用途 |
|---------|------|---------|
| `PRE_TASK` | 任务开始前执行 | 环境准备、依赖检查 |
| `PRE_TEST` | 测试前执行 | 代码格式化、Lint 检查 |
| `POST_TEST` | 测试后执行 | 清理临时文件、生成报告 |
| `POST_TASK` | 任务完成后执行 | 部署、通知、清理 |

## 快速开始

### 1. 创建钩子系统实例

```python
from ralph.managers.hook_system import HookSystem

hook_system = HookSystem()
```

### 2. 注册钩子

```python
from ralph.models.enums import HookType
from ralph.models.hook import HookConfig

# 注册代码格式化钩子
format_hook = HookConfig(
    name="format_python_code",
    hook_type=HookType.PRE_TEST,
    command="black .",
    timeout=60,
    max_retries=1,
    continue_on_failure=False,
)

hook_system.register_hook(format_hook)
```

### 3. 执行钩子

```python
from datetime import datetime
from ralph.models.hook import HookContext

# 创建执行上下文
context = HookContext(
    hook_type=HookType.PRE_TEST,
    task_id="task_001",
    task_name="实现用户认证",
    timestamp=datetime.now(),
    working_directory="/path/to/project",
)

# 执行钩子
results = hook_system.execute_hooks(HookType.PRE_TEST, context)

# 检查结果
for result in results:
    if result.success:
        print(f"✓ {result.hook_name} 成功")
    else:
        print(f"✗ {result.hook_name} 失败: {result.error}")
```

## 钩子配置详解

### HookConfig 参数

```python
HookConfig(
    name="hook_name",              # 钩子名称（必需，唯一）
    hook_type=HookType.PRE_TEST,   # 钩子类型（必需）
    command="echo 'test'",         # 要执行的命令（必需）
    timeout=300,                   # 超时时间（秒），默认 300
    max_retries=0,                 # 最大重试次数，默认 0
    retry_delay=1,                 # 重试延迟（秒），默认 1
    continue_on_failure=False,     # 失败时是否继续，默认 False
    working_directory=None,        # 工作目录，默认使用上下文目录
    environment={},                # 环境变量字典
)
```

### 关键参数说明

- **timeout**: 钩子执行的最大时间。超时后进程会被终止。
- **max_retries**: 失败后的重试次数。0 表示不重试。
- **retry_delay**: 重试之间的等待时间（秒）。
- **continue_on_failure**: 
  - `False`: 钩子失败时抛出异常，中止任务
  - `True`: 钩子失败时记录错误但继续执行

## 常见使用场景

### 场景 1: 代码格式化

```python
# 注册 Python 代码格式化钩子
black_hook = HookConfig(
    name="format_with_black",
    hook_type=HookType.PRE_TEST,
    command="black . --check",
    timeout=60,
    continue_on_failure=False,
)

# 注册 import 排序钩子
isort_hook = HookConfig(
    name="sort_imports",
    hook_type=HookType.PRE_TEST,
    command="isort . --check-only",
    timeout=60,
    continue_on_failure=False,
)

hook_system.register_hook(black_hook)
hook_system.register_hook(isort_hook)
```

### 场景 2: 清理临时文件

```python
cleanup_hook = HookConfig(
    name="cleanup_temp",
    hook_type=HookType.POST_TEST,
    command="rm -rf tmp/ __pycache__/ .pytest_cache/",
    timeout=30,
    continue_on_failure=True,  # 清理失败不影响任务
)

hook_system.register_hook(cleanup_hook)
```

### 场景 3: 环境检查

```python
env_check_hook = HookConfig(
    name="check_dependencies",
    hook_type=HookType.PRE_TASK,
    command="poetry check && poetry install --no-root",
    timeout=120,
    max_retries=2,
    retry_delay=5,
    continue_on_failure=False,
)

hook_system.register_hook(env_check_hook)
```

### 场景 4: 带环境变量的钩子

```python
deploy_hook = HookConfig(
    name="deploy_to_staging",
    hook_type=HookType.POST_TASK,
    command="./deploy.sh",
    timeout=300,
    environment={
        "DEPLOY_ENV": "staging",
        "API_KEY": "your-api-key",
    },
    continue_on_failure=True,
)

hook_system.register_hook(deploy_hook)
```

## 高级功能

### 查询钩子

```python
# 获取指定类型的所有钩子
pre_test_hooks = hook_system.get_hooks(HookType.PRE_TEST)

for hook in pre_test_hooks:
    print(f"{hook.name}: {hook.command}")
```

### 注销钩子

```python
# 注销指定钩子
success = hook_system.unregister_hook(HookType.PRE_TEST, "format_with_black")

if success:
    print("钩子已注销")
else:
    print("钩子不存在")
```

### 查看执行历史

```python
# 获取所有执行历史
history = hook_system.get_execution_history()

# 按任务 ID 过滤
history = hook_system.get_execution_history(task_id="task_001")

# 按钩子类型过滤
history = hook_system.get_execution_history(hook_type=HookType.PRE_TEST)

# 限制结果数量
history = hook_system.get_execution_history(limit=10)

# 查看执行记录
for record in history:
    print(f"{record.hook_name}: {record.is_successful}")
    print(f"  执行时间: {record.duration:.2f}秒")
    print(f"  重试次数: {record.retry_count}")
```

### 查看统计信息

```python
stats = hook_system.get_statistics()

print(f"已注册钩子: {stats['total_registered_hooks']}")
print(f"执行次数: {stats['total_executions']}")
print(f"成功率: {stats['success_rate']:.1f}%")

# 各类型钩子数量
for hook_type, count in stats['hooks_by_type'].items():
    print(f"{hook_type}: {count}")
```

### 清空执行历史

```python
hook_system.clear_execution_history()
```

## 错误处理

### 捕获钩子执行错误

```python
from ralph.managers.hook_system import HookExecutionError

try:
    results = hook_system.execute_hooks(HookType.PRE_TEST, context)
except HookExecutionError as e:
    print(f"钩子执行失败: {e}")
    # 处理错误...
```

### 检查执行结果

```python
results = hook_system.execute_hooks(HookType.PRE_TEST, context)

for result in results:
    if not result.success:
        print(f"钩子失败: {result.hook_name}")
        print(f"  退出码: {result.exit_code}")
        print(f"  错误信息: {result.error}")
        print(f"  输出: {result.output}")
```

## 最佳实践

### 1. 合理设置超时时间

```python
# ✓ 好的做法：根据操作类型设置合理的超时
format_hook = HookConfig(
    name="format_code",
    hook_type=HookType.PRE_TEST,
    command="black .",
    timeout=60,  # 代码格式化通常很快
)

build_hook = HookConfig(
    name="build_project",
    hook_type=HookType.PRE_TASK,
    command="make build",
    timeout=600,  # 构建可能需要更长时间
)
```

### 2. 使用 continue_on_failure

```python
# ✓ 关键操作：失败时中止
format_hook = HookConfig(
    name="format_code",
    hook_type=HookType.PRE_TEST,
    command="black . --check",
    continue_on_failure=False,  # 格式化失败应该中止
)

# ✓ 非关键操作：失败时继续
cleanup_hook = HookConfig(
    name="cleanup",
    hook_type=HookType.POST_TEST,
    command="rm -rf tmp/",
    continue_on_failure=True,  # 清理失败不影响任务
)
```

### 3. 合理使用重试机制

```python
# ✓ 网络操作：使用重试
deploy_hook = HookConfig(
    name="deploy",
    hook_type=HookType.POST_TASK,
    command="./deploy.sh",
    max_retries=3,
    retry_delay=5,
)

# ✓ 确定性操作：不需要重试
format_hook = HookConfig(
    name="format",
    hook_type=HookType.PRE_TEST,
    command="black .",
    max_retries=0,  # 格式化失败重试无意义
)
```

### 4. 钩子命名规范

```python
# ✓ 好的命名：清晰描述功能
HookConfig(name="format_python_code", ...)
HookConfig(name="lint_with_flake8", ...)
HookConfig(name="cleanup_temp_files", ...)

# ✗ 不好的命名：模糊不清
HookConfig(name="hook1", ...)
HookConfig(name="test", ...)
```

## 示例代码

完整的使用示例请参考：`examples/hook_system_demo.py`

运行示例：

```bash
poetry run python examples/hook_system_demo.py
```

## 相关文档

- [任务管理器使用指南](task_manager_usage.md)
- [Git 管理器使用指南](git_manager_usage.md)
- [上下文管理器使用指南](context_manager_usage.md)

