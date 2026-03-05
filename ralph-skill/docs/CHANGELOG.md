# Ralph Skill 更新日志

## v1.1.0 (2024-03-06) - Agent 驱动模式

### 新增功能

#### 1. Agent 驱动的动态任务执行模式

**核心改进**：将任务执行的控制权交给调用 Skill 的 Agent，而不是在 Skill 内部盲目重试。

**主要变更**：

- **移除内部重试循环**：`execute_task()` 不再在内部重试，只执行单次任务
- **详细的测试输出**：`_run_tests()` 返回 `tuple[bool, str]`，包含完整的测试输出
- **保留代码现场**：测试失败时不自动回滚，保留代码供 Agent 分析
- **新增 API 方法**：
  - `add_task(task_config)`: 动态添加新任务
  - `update_task(task_id, updates)`: 更新任务配置
  - `get_task_status(task_id)`: 获取任务状态
  - `rollback_task(task_id)`: 回滚任务代码
  - `get_code_diff(task_id)`: 获取代码差异

**优势**：

- ✅ Agent 可以分析具体错误原因
- ✅ 动态生成针对性的修复任务
- ✅ 避免盲目重复相同错误
- ✅ 用户可以参与决策过程
- ✅ 更好的可观察性和控制力

#### 2. autonomous_develop() 支持 Agent 驱动模式

**新增参数**：

```python
def autonomous_develop(
    task_description: str,
    tech_stack: Optional[Dict] = None,
    requirements: Optional[List[str]] = None,
    config_file: Optional[str] = None,
    project_root: str = ".",
    agent_driven: bool = False  # 新增参数
) -> Dict
```

**使用方式**：

```python
# 启用 Agent 驱动模式
result = autonomous_develop(
    task_description="创建 Todo 应用",
    tech_stack={"backend": {"language": "go"}},
    agent_driven=True  # 返回引擎实例供 Agent 控制
)

engine = result["engine"]
config = result["config"]

# Agent 控制任务执行
for task_config in config.tasks:
    task_result = engine.execute_task(task_config)
    if not task_result.success:
        # Agent 分析错误并创建修复任务
        fix_task = create_fix_task(task_result)
        engine.add_task(fix_task)
```

#### 3. 导出核心类供外部使用

**更新 `__init__.py`**：

```python
from ralph import autonomous_develop, RalphEngineCore, TaskConfig

__all__ = ["autonomous_develop", "RalphEngineCore", "TaskConfig"]
```

现在外部可以直接导入和使用这些类。

#### 4. GitManager 新增 get_diff() 方法

**功能**：获取代码差异

```python
def get_diff(self, ref1: str = "HEAD", ref2: Optional[str] = None) -> str:
    """
    获取代码差异
    
    参数:
        ref1: 第一个引用（默认为 HEAD）
        ref2: 第二个引用（可选，如果为 None 则显示工作区差异）
    
    返回:
        str: Git diff 输出
    """
```

### 文档更新

#### 1. 设计文档

**新增**：`docs/agent_driven_execution.md`

详细说明了 Agent 驱动模式的设计理念、工作流程和实现细节。

**内容包括**：
- 当前问题分析
- 改进设计方案
- 执行流程图
- 新增 API 说明
- 实际使用示例
- 优势总结

#### 2. 集成指南

**新增**：`docs/kiro_agent_integration.md`

完整的 Kiro Agent 集成指南，包含多个实用示例。

**内容包括**：
- Agent 驱动模式介绍
- 为什么使用 Agent 驱动模式
- 在 Kiro 中的使用方法（3 种方式）
- API 参考文档
- 最佳实践
- 错误分析示例
- 动态任务生成示例
- 用户交互示例
- 日志和监控示例

#### 3. 示例代码

**新增**：`examples/agent_driven_example.py`

包含 3 个完整的示例：
1. 简单的 Agent 驱动执行
2. 智能错误处理
3. API 使用示例

#### 4. SKILL.md 更新

更新了使用说明，添加了 Agent 驱动模式的介绍和使用方法。

**新增章节**：
- 方式 1：Agent 驱动模式（推荐）
- 核心能力 - Agent 驱动的智能执行

### 技术细节

#### 修改的文件

1. **ralph-skill/src/ralph/core/ralph_engine.py**
   - 移除 `execute_task()` 中的重试循环
   - 修改 `_run_tests()` 返回详细输出
   - 新增 5 个 API 方法

2. **ralph-skill/src/ralph/managers/git_manager.py**
   - 新增 `get_diff()` 方法
   - 新增 `rollback_to_branch()` 方法

3. **ralph-skill/src/ralph/__main__.py**
   - 添加 `agent_driven` 参数支持
   - 返回引擎实例供 Agent 控制

4. **ralph-skill/src/ralph/__init__.py**
   - 导出 `RalphEngineCore` 和 `TaskConfig`

#### 新增的文件

1. `docs/agent_driven_execution.md` - 设计文档
2. `docs/kiro_agent_integration.md` - 集成指南
3. `examples/agent_driven_example.py` - 示例代码
4. `docs/CHANGELOG.md` - 更新日志

### 向后兼容性

所有更改都是向后兼容的：

- 默认情况下，`autonomous_develop()` 仍然使用自动模式
- 只有显式设置 `agent_driven=True` 才会启用新模式
- 现有的 API 和功能保持不变

### 使用建议

#### 何时使用 Agent 驱动模式

**推荐使用**：
- 复杂的项目开发
- 需要智能错误处理
- 用户希望参与决策
- 需要详细的执行日志

**不推荐使用**：
- 简单的一次性任务
- 完全自动化的场景
- 不需要错误分析的情况

#### 最佳实践

1. **错误分析**：使用正则表达式或 AI 分析测试输出
2. **动态任务生成**：根据错误类型创建针对性的修复任务
3. **用户交互**：在关键决策点询问用户意见
4. **日志记录**：记录所有任务执行和错误信息

### 下一步计划

1. 添加更多错误分析模式
2. 实现任务优先级调度
3. 支持并行任务执行
4. 添加任务执行统计和报告
5. 集成更多 AI 引擎

### 贡献者

- Ralph Team

### 许可证

MIT License

---

**注意**：这是一个重大功能更新，建议在使用前阅读完整的文档和示例。
