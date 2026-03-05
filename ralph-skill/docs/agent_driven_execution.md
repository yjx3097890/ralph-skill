# Agent 驱动的动态任务执行

## 设计理念

将任务执行的控制权交给调用 Skill 的 Agent，而不是在 Skill 内部盲目重试。

## 当前问题

```python
# 当前设计：Skill 内部重试
while retry_count <= max_retries:
    code = ai_engine.generate_code()
    test_result = run_tests()
    if test_result.failed:
        retry_count += 1
        rollback()  # 盲目重试，可能重复相同错误
```

**问题**：
- AI 可能重复生成相同的错误代码
- 没有利用测试失败的具体信息
- Agent 无法参与决策和修复

## 改进设计

### 1. Skill 职责

Skill 只负责**执行单次任务**，不做重试：

```python
def execute_task(task_config):
    # 1. 创建 WIP 分支
    create_wip_branch()
    
    # 2. 调用 AI 生成代码
    code_result = ai_engine.generate_code(prompt)
    
    # 3. 运行测试
    test_result = run_tests()
    
    # 4. 返回详细结果（成功或失败）
    return TaskResult(
        success=test_result.passed,
        files_changed=[...],
        test_output=test_result.output,  # 详细的测试输出
        errors=test_result.errors,        # 错误列表
        code_diff=get_git_diff()          # 代码变更
    )
```

### 2. Agent 职责

Agent 负责**分析错误并决定如何修复**：

```python
# 在 Kiro 中
result = ralph_skill.execute_task(task_config)

if not result.success:
    # Agent 分析错误
    analysis = agent.analyze_error(
        test_output=result.test_output,
        code_diff=result.code_diff,
        errors=result.errors
    )
    
    # Agent 决定修复策略
    if analysis.can_fix:
        # 策略 1: 创建修复任务
        fix_task = TaskConfig(
            id=f"{task_config.id}-fix-1",
            name=f"修复 {task_config.name}",
            description=f"修复以下错误：\n{analysis.fix_suggestion}",
            depends_on=[task_config.id]
        )
        ralph_skill.add_task(fix_task)
        
    elif analysis.need_more_info:
        # 策略 2: 询问用户
        user_input = agent.ask_user(analysis.question)
        # 根据用户输入更新任务
        
    else:
        # 策略 3: 放弃任务
        agent.report_failure(result)
```

### 3. 执行流程

```
用户需求
   ↓
Agent 生成初始任务列表
   ↓
┌─────────────────────────────────────┐
│  主循环（由 Agent 控制）              │
│                                     │
│  while 有未完成的任务:                │
│    ├─ 选择下一个任务                  │
│    ├─ 调用 Skill 执行任务            │
│    │                                │
│    └─ 分析结果:                      │
│       ├─ 成功? → 标记完成            │
│       │                             │
│       └─ 失败?                       │
│          ├─ 分析错误原因             │
│          ├─ 生成修复任务             │
│          ├─ 或询问用户               │
│          └─ 或放弃任务               │
└─────────────────────────────────────┘
   ↓
返回最终结果
```

### 4. 新增 API

#### 4.1 添加任务

```python
def add_task(task_config: TaskConfig) -> str:
    """
    动态添加新任务到任务列表
    
    返回:
        task_id: 新任务的 ID
    """
```

#### 4.2 更新任务

```python
def update_task(task_id: str, updates: Dict) -> bool:
    """
    更新任务配置
    
    参数:
        task_id: 任务 ID
        updates: 要更新的字段
    """
```

#### 4.3 获取任务状态

```python
def get_task_status(task_id: str) -> TaskInfo:
    """
    获取任务当前状态
    """
```

#### 4.4 回滚任务

```python
def rollback_task(task_id: str) -> bool:
    """
    回滚任务的代码变更
    """
```

### 5. 实际例子

#### 场景：后端测试失败

```python
# 第 1 次执行
result = ralph_skill.execute_task({
    "id": "task-backend",
    "name": "实现后端 API",
    "description": "实现 Todo CRUD API"
})

# 结果：测试失败
# result.test_output:
#   "FAIL: TestTodoAPI.test_create_todo
#    AssertionError: Expected status 201, got 500
#    Error: database connection failed"

# Agent 分析
agent.analyze_error(result)
# → 发现：缺少数据库连接配置

# Agent 创建修复任务
ralph_skill.add_task({
    "id": "task-backend-fix-db",
    "name": "修复数据库连接",
    "description": """
    修复后端数据库连接问题：
    1. 添加数据库连接配置
    2. 确保 MongoDB 容器正在运行
    3. 更新连接字符串
    
    错误信息：{result.test_output}
    """,
    "depends_on": ["task-backend"]
})

# 第 2 次执行（修复任务）
fix_result = ralph_skill.execute_task("task-backend-fix-db")
# → 成功！
```

### 6. 优势

1. **智能修复**：Agent 可以分析具体错误，生成针对性的修复
2. **避免重复**：不会盲目重试相同的代码
3. **用户参与**：Agent 可以在需要时询问用户
4. **灵活控制**：Agent 可以动态调整任务列表
5. **更好的日志**：每次尝试都有清晰的记录

### 7. 实现步骤

1. ✅ 移除 `execute_task` 中的重试循环
2. ✅ 修改 `_run_tests` 返回详细的测试输出
3. ✅ 添加 `add_task` API
4. ✅ 添加 `update_task` API
5. ✅ 添加 `rollback_task` API
6. ✅ 更新 `TaskResult` 包含更多错误信息
7. ✅ 在 SKILL.md 中说明 Agent 如何使用这些 API

### 8. 向后兼容

为了保持兼容性，可以提供两种模式：

```yaml
# 配置文件
settings:
  execution_mode: "agent_driven"  # 或 "auto_retry"（旧模式）
```

- `agent_driven`: 新模式，由 Agent 控制
- `auto_retry`: 旧模式，Skill 内部重试（当前实现）

## 总结

这个设计将 Ralph Skill 从一个"自动重试的执行器"转变为一个"智能的任务执行工具"，让 Agent 能够更好地控制开发流程，实现真正的智能化开发。
