# TaskManager 使用指南

## 概述

TaskManager 是 Ralph Skill 企业级自治编程引擎的核心组件之一，负责管理任务的完整生命周期，包括创建、状态转换、依赖管理和状态变更通知。

## 核心功能

- **任务创建和管理**: 创建、获取、列出和删除任务
- **状态机控制**: 严格的状态转换规则，确保任务状态的一致性
- **状态变更通知**: 支持注册回调函数，在状态变更时接收通知
- **依赖管理**: 构建任务依赖图，验证依赖关系，获取可执行任务
- **并发安全**: 使用线程锁保护共享状态，支持多线程环境

## 状态转换规则

TaskManager 实现了严格的状态机，只允许以下状态转换：

```
PENDING → IN_PROGRESS: 开始执行任务
IN_PROGRESS → TESTING: 代码实现完成，进入测试阶段
IN_PROGRESS → FAILED: 执行失败
TESTING → COMPLETED: 测试通过
TESTING → IN_PROGRESS: 测试失败，返回修复
TESTING → FAILED: 测试失败且无法修复
```

任何其他状态转换都会抛出 `TaskStatusTransitionError` 异常。

## 基本使用

### 1. 创建任务管理器

```python
from ralph.managers import TaskManager
from ralph.models.task import TaskConfig
from ralph.models.enums import TaskType, TaskStatus

# 创建任务管理器实例
manager = TaskManager()
```

### 2. 创建任务

```python
# 定义任务配置
config = TaskConfig(
    id="task_1",
    name="实现用户认证功能",
    type=TaskType.FEATURE,
    ai_engine="qwen_code",
    depends_on=[],  # 无依赖
    max_retries=3,
)

# 创建任务
task = manager.create_task(config)
print(f"任务已创建: {task.id}, 状态: {task.status.value}")
# 输出: 任务已创建: task_1, 状态: pending
```

### 3. 更新任务状态

```python
# 开始执行任务
task = manager.update_task_status("task_1", TaskStatus.IN_PROGRESS)
print(f"任务状态: {task.status.value}")
# 输出: 任务状态: in_progress

# 代码实现完成，进入测试
task = manager.update_task_status("task_1", TaskStatus.TESTING)

# 测试通过，任务完成
task = manager.update_task_status("task_1", TaskStatus.COMPLETED)
print(f"任务状态: {task.status.value}")
# 输出: 任务状态: completed
```

### 4. 获取和列出任务

```python
# 获取单个任务
task = manager.get_task("task_1")
print(f"任务: {task.name}, 状态: {task.status.value}")

# 列出所有任务
all_tasks = manager.list_tasks()
print(f"总任务数: {len(all_tasks)}")

# 按状态过滤任务
pending_tasks = manager.list_tasks(status=TaskStatus.PENDING)
print(f"待执行任务数: {len(pending_tasks)}")
```

### 5. 取消任务

```python
# 取消正在执行的任务
task = manager.cancel_task("task_1", reason="用户取消")
print(f"任务状态: {task.status.value}")
# 输出: 任务状态: failed
```

## 状态变更通知

### 注册回调函数

```python
def on_status_change(task, old_status, new_status):
    """状态变更回调函数"""
    print(f"任务 {task.id} 状态变更: {old_status.value} -> {new_status.value}")
    
    # 可以在这里执行自定义逻辑
    if new_status == TaskStatus.COMPLETED:
        print(f"✅ 任务 {task.name} 已完成！")
    elif new_status == TaskStatus.FAILED:
        print(f"❌ 任务 {task.name} 失败")

# 注册回调
manager.register_status_change_callback(on_status_change)

# 现在每次状态变更都会触发回调
task = manager.update_task_status("task_1", TaskStatus.IN_PROGRESS)
# 输出: 任务 task_1 状态变更: pending -> in_progress
```

### 注销回调函数

```python
# 注销回调
manager.unregister_status_change_callback(on_status_change)
```

## 任务依赖管理

### 创建有依赖的任务

```python
# 创建任务 1（无依赖）
config1 = TaskConfig(
    id="task_1",
    name="实现数据模型",
    type=TaskType.FEATURE,
)
manager.create_task(config1)

# 创建任务 2（依赖任务 1）
config2 = TaskConfig(
    id="task_2",
    name="实现业务逻辑",
    type=TaskType.FEATURE,
    depends_on=["task_1"],  # 依赖任务 1
)
manager.create_task(config2)

# 创建任务 3（依赖任务 2）
config3 = TaskConfig(
    id="task_3",
    name="实现 API 接口",
    type=TaskType.FEATURE,
    depends_on=["task_2"],  # 依赖任务 2
)
manager.create_task(config3)
```

### 获取可执行任务

```python
# 获取当前可执行的任务（状态为 PENDING 且依赖已满足）
executable_tasks = manager.get_executable_tasks()
print(f"可执行任务: {[t.id for t in executable_tasks]}")
# 输出: 可执行任务: ['task_1']

# 完成任务 1
manager.update_task_status("task_1", TaskStatus.IN_PROGRESS)
manager.update_task_status("task_1", TaskStatus.TESTING)
manager.update_task_status("task_1", TaskStatus.COMPLETED)

# 现在任务 2 可以执行了
executable_tasks = manager.get_executable_tasks()
print(f"可执行任务: {[t.id for t in executable_tasks]}")
# 输出: 可执行任务: ['task_2']
```

### 构建任务依赖图

```python
# 构建任务依赖图
graph = manager.build_task_graph()

# 获取执行顺序（拓扑排序）
execution_order = graph.get_execution_order()
print(f"执行顺序: {execution_order}")
# 输出: 执行顺序: ['task_1', 'task_2', 'task_3']

# 检测循环依赖
has_cycle = graph.has_cycle()
print(f"存在循环依赖: {has_cycle}")
# 输出: 存在循环依赖: False
```

### 验证依赖关系

```python
# 验证所有任务的依赖关系是否有效
is_valid = manager.validate_dependencies()
print(f"依赖关系有效: {is_valid}")
# 输出: 依赖关系有效: True
```

## 统计信息

```python
# 获取任务统计信息
stats = manager.get_statistics()
print(f"总任务数: {stats['total']}")
print(f"待执行: {stats['pending']}")
print(f"执行中: {stats['in_progress']}")
print(f"测试中: {stats['testing']}")
print(f"已完成: {stats['completed']}")
print(f"已失败: {stats['failed']}")
```

## 完整示例

```python
from ralph.managers import TaskManager
from ralph.models.task import TaskConfig
from ralph.models.enums import TaskType, TaskStatus

# 创建任务管理器
manager = TaskManager()

# 注册状态变更回调
def log_status_change(task, old_status, new_status):
    print(f"📝 [{task.id}] {old_status.value} → {new_status.value}")

manager.register_status_change_callback(log_status_change)

# 创建任务
config = TaskConfig(
    id="auth_feature",
    name="实现用户认证功能",
    type=TaskType.FEATURE,
    ai_engine="qwen_code",
)
task = manager.create_task(config)

# 执行任务流程
try:
    # 开始执行
    manager.update_task_status("auth_feature", TaskStatus.IN_PROGRESS)
    
    # 代码实现完成，进入测试
    manager.update_task_status("auth_feature", TaskStatus.TESTING)
    
    # 测试通过
    manager.update_task_status("auth_feature", TaskStatus.COMPLETED)
    
    print("✅ 任务执行成功！")
    
except Exception as e:
    print(f"❌ 任务执行失败: {e}")
    manager.cancel_task("auth_feature", reason=str(e))

# 查看最终统计
stats = manager.get_statistics()
print(f"\n统计信息: {stats}")
```

## 错误处理

### TaskNotFoundError

当尝试操作不存在的任务时抛出：

```python
try:
    task = manager.get_task("nonexistent")
except TaskNotFoundError as e:
    print(f"错误: {e}")
    # 输出: 错误: 任务不存在: nonexistent
```

### TaskStatusTransitionError

当尝试非法的状态转换时抛出：

```python
try:
    # 尝试从 PENDING 直接跳到 COMPLETED（非法）
    manager.update_task_status("task_1", TaskStatus.COMPLETED)
except TaskStatusTransitionError as e:
    print(f"错误: {e}")
    # 输出: 错误: 不合法的状态转换: pending -> completed
```

## 并发安全

TaskManager 使用可重入锁（RLock）保护所有共享状态，可以安全地在多线程环境中使用：

```python
import threading

manager = TaskManager()

# 创建任务
config = TaskConfig(id="task_1", name="任务", type=TaskType.FEATURE)
manager.create_task(config)

# 多个线程并发更新状态
def update_status():
    try:
        manager.update_task_status("task_1", TaskStatus.IN_PROGRESS)
    except Exception as e:
        print(f"错误: {e}")

threads = [threading.Thread(target=update_status) for _ in range(5)]
for t in threads:
    t.start()
for t in threads:
    t.join()

# 最终状态正确
task = manager.get_task("task_1")
print(f"最终状态: {task.status.value}")
# 输出: 最终状态: in_progress
```

## 最佳实践

1. **使用状态变更回调**: 注册回调函数来监控任务状态变化，便于日志记录和通知
2. **验证依赖关系**: 在开始执行任务前，使用 `validate_dependencies()` 验证依赖关系
3. **使用 get_executable_tasks()**: 获取当前可执行的任务，而不是手动检查依赖
4. **错误处理**: 始终捕获并处理 `TaskNotFoundError` 和 `TaskStatusTransitionError`
5. **任务取消**: 使用 `cancel_task()` 而不是直接设置状态为 FAILED
6. **并发安全**: TaskManager 是线程安全的，可以在多线程环境中使用

## 参考

- [需求文档](../.kiro/specs/ralph-autonomous-engine/requirements.md) - 需求 3
- [设计文档](../.kiro/specs/ralph-autonomous-engine/design.md) - TaskManager 设计
- [任务模型](../src/ralph/models/task.py) - Task 和 TaskConfig 数据模型
- [枚举类型](../src/ralph/models/enums.py) - TaskStatus 和 TaskType 枚举
