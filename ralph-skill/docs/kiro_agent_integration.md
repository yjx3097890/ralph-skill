# Kiro Agent 集成指南

## Agent 驱动模式

Ralph Skill 提供两种执行模式：

1. **自动模式**（默认）：Skill 自动执行所有任务，内部处理重试
2. **Agent 驱动模式**（推荐）：Agent 控制任务执行，智能处理失败

## 为什么使用 Agent 驱动模式？

### 自动模式的问题

```python
# 自动模式：盲目重试
result = autonomous_develop(
    task_description="创建 Todo 应用",
    tech_stack={"backend": {"language": "go"}}
)
# 如果失败，只能看到最终结果，无法干预
```

**问题**：
- ❌ AI 可能重复生成相同的错误代码
- ❌ 无法利用测试失败的具体信息
- ❌ Agent 无法参与决策和修复
- ❌ 用户无法在中途调整策略

### Agent 驱动模式的优势

```python
# Agent 驱动模式：智能控制
result = autonomous_develop(
    task_description="创建 Todo 应用",
    tech_stack={"backend": {"language": "go"}},
    agent_driven=True  # 启用 Agent 驱动模式
)

engine = result["engine"]
config = result["config"]

# Agent 逐个执行任务，智能处理失败
for task_config in config.tasks:
    task_result = engine.execute_task(task_config)
    
    if not task_result.success:
        # Agent 分析错误并决定修复策略
        fix_strategy = analyze_error(task_result)
        
        if fix_strategy == "add_fix_task":
            # 动态添加修复任务
            fix_task = create_fix_task(task_result)
            engine.add_task(fix_task)
        elif fix_strategy == "ask_user":
            # 询问用户
            user_input = ask_user(task_result.errors)
            # 根据用户输入更新任务
```

**优势**：
- ✅ 智能分析错误原因
- ✅ 动态生成针对性的修复任务
- ✅ 用户可以参与决策
- ✅ 避免重复相同错误
- ✅ 更好的日志和可观察性

## 在 Kiro 中使用

### 方式 1：简单的 Agent 驱动执行

```python
import sys
from pathlib import Path

# 添加 Ralph Skill 到路径
skill_path = Path.home() / ".kiro" / "skills" / "ralph-skill"
sys.path.insert(0, str(skill_path / "src"))

from ralph import autonomous_develop

# 启用 Agent 驱动模式
result = autonomous_develop(
    task_description="创建一个 Todo 应用",
    tech_stack={
        "frontend": {"framework": "vue3"},
        "backend": {"language": "go", "framework": "gin"}
    },
    requirements=[
        "支持添加、删除、完成待办事项",
        "包含单元测试"
    ],
    project_root=".",
    agent_driven=True  # 启用 Agent 驱动模式
)

if not result["success"]:
    print(f"❌ 初始化失败: {result['message']}")
    exit(1)

engine = result["engine"]
config = result["config"]

print(f"✅ 引擎已初始化")
print(f"📋 任务列表: {len(config.tasks)} 个任务")

# Agent 控制任务执行
completed_tasks = set()
failed_tasks = []

while len(completed_tasks) < len(config.tasks):
    # 找到可以执行的任务
    ready_tasks = [
        task for task in config.tasks
        if task.id not in completed_tasks
        and all(dep in completed_tasks for dep in task.depends_on)
    ]
    
    if not ready_tasks:
        print("❌ 无法继续执行，可能存在循环依赖")
        break
    
    # 执行就绪的任务
    for task_config in ready_tasks:
        print(f"\n{'='*60}")
        print(f"执行任务: {task_config.name}")
        print(f"{'='*60}")
        
        task_result = engine.execute_task(task_config)
        
        if task_result.success:
            completed_tasks.add(task_config.id)
            print(f"✅ 任务完成: {task_config.name}")
        else:
            print(f"❌ 任务失败: {task_config.name}")
            print(f"错误信息: {task_result.message}")
            failed_tasks.append((task_config, task_result))
            # 停止执行
            break
    
    if failed_tasks:
        break

# 输出结果
print(f"\n{'='*60}")
print(f"执行完成")
print(f"{'='*60}")
print(f"成功: {len(completed_tasks)}/{len(config.tasks)}")
if failed_tasks:
    print(f"失败: {len(failed_tasks)} 个任务")
```

### 方式 2：智能错误处理

```python
from ralph import autonomous_develop, TaskConfig

# 初始化引擎
result = autonomous_develop(
    task_description="创建 Todo 应用",
    tech_stack={"backend": {"language": "go"}},
    agent_driven=True
)

engine = result["engine"]
config = result["config"]

def analyze_error(task_result):
    """分析错误并返回修复策略"""
    test_output = task_result.test_output or ""
    errors = task_result.errors or []
    
    # 检查常见错误模式
    if "database connection" in test_output.lower():
        return "fix_database"
    elif "import" in test_output.lower() or "module not found" in test_output.lower():
        return "fix_imports"
    elif "syntax error" in test_output.lower():
        return "fix_syntax"
    elif "timeout" in test_output.lower():
        return "increase_timeout"
    else:
        return "ask_user"

def create_fix_task(task_config, task_result, fix_type):
    """根据错误类型创建修复任务"""
    fix_descriptions = {
        "fix_database": f"""
修复数据库连接问题：
1. 检查数据库配置
2. 确保数据库服务正在运行
3. 更新连接字符串

原始错误：
{task_result.test_output}
""",
        "fix_imports": f"""
修复导入错误：
1. 检查缺失的依赖
2. 更新 import 语句
3. 确保包路径正确

原始错误：
{task_result.test_output}
""",
        "fix_syntax": f"""
修复语法错误：
1. 检查语法错误位置
2. 修正语法问题
3. 确保代码符合语言规范

原始错误：
{task_result.test_output}
""",
        "increase_timeout": f"""
增加超时时间：
1. 检查慢查询
2. 优化性能
3. 或增加超时配置

原始错误：
{task_result.test_output}
"""
    }
    
    return TaskConfig(
        id=f"{task_config.id}-fix-{fix_type}",
        name=f"修复 {task_config.name} - {fix_type}",
        description=fix_descriptions.get(fix_type, f"修复错误：\n{task_result.test_output}"),
        depends_on=[task_config.id],
        timeout=task_config.timeout,
        config=task_config.config
    )

# 执行任务并智能处理失败
completed_tasks = set()
max_retries = 3

for task_config in config.tasks:
    retry_count = 0
    
    while retry_count <= max_retries:
        print(f"\n执行任务: {task_config.name} (尝试 {retry_count + 1}/{max_retries + 1})")
        
        task_result = engine.execute_task(task_config)
        
        if task_result.success:
            completed_tasks.add(task_config.id)
            print(f"✅ 任务完成")
            break
        else:
            print(f"❌ 任务失败: {task_result.message}")
            
            # 分析错误
            fix_type = analyze_error(task_result)
            
            if fix_type == "ask_user":
                print("\n需要用户输入：")
                print(f"错误信息: {task_result.test_output}")
                print("请提供修复建议或输入 'skip' 跳过此任务")
                # 在实际使用中，这里应该通过 Kiro 的 UI 获取用户输入
                break
            else:
                # 创建修复任务
                fix_task = create_fix_task(task_config, task_result, fix_type)
                print(f"🔧 创建修复任务: {fix_task.name}")
                
                # 执行修复任务
                fix_result = engine.execute_task(fix_task)
                
                if fix_result.success:
                    print(f"✅ 修复成功，重试原任务")
                    retry_count += 1
                else:
                    print(f"❌ 修复失败: {fix_result.message}")
                    retry_count += 1
    
    if task_config.id not in completed_tasks:
        print(f"⚠️ 任务 {task_config.name} 最终失败")
        break

print(f"\n完成 {len(completed_tasks)}/{len(config.tasks)} 个任务")
```

### 方式 3：使用新的 API

```python
from ralph import autonomous_develop, TaskConfig

# 初始化引擎
result = autonomous_develop(
    task_description="创建 Todo 应用",
    config_file="ralph-config.yaml",
    agent_driven=True
)

engine = result["engine"]

# 1. 获取任务状态
task_status = engine.get_task_status("task-backend")
print(f"任务状态: {task_status.status}")

# 2. 执行任务
task_result = engine.execute_task(task_config)

if not task_result.success:
    # 3. 获取代码差异
    diff = engine.get_code_diff(task_config.id)
    print(f"代码变更:\n{diff}")
    
    # 4. 分析错误并创建修复任务
    fix_task = TaskConfig(
        id=f"{task_config.id}-fix",
        name=f"修复 {task_config.name}",
        description=f"修复以下错误:\n{task_result.test_output}",
        depends_on=[task_config.id]
    )
    
    # 5. 添加修复任务
    engine.add_task(fix_task)
    
    # 6. 执行修复任务
    fix_result = engine.execute_task(fix_task)
    
    if not fix_result.success:
        # 7. 如果修复失败，回滚代码
        engine.rollback_task(task_config.id)
        print("已回滚代码变更")

# 8. 更新任务配置
engine.update_task("task-backend", {
    "timeout": 3600,  # 增加超时时间
    "description": "更新后的描述"
})
```

## API 参考

### autonomous_develop()

```python
def autonomous_develop(
    task_description: str,
    tech_stack: Optional[Dict] = None,
    requirements: Optional[List[str]] = None,
    config_file: Optional[str] = None,
    project_root: str = ".",
    agent_driven: bool = False
) -> Dict
```

**参数**：
- `task_description`: 任务描述
- `tech_stack`: 技术栈配置
- `requirements`: 需求列表
- `config_file`: 配置文件路径
- `project_root`: 项目根目录
- `agent_driven`: 是否启用 Agent 驱动模式

**返回**（agent_driven=True）：
```python
{
    "success": True,
    "engine": RalphEngineCore,  # 引擎实例
    "config": Configuration,     # 配置对象
    "config_file": str,          # 配置文件路径
    "message": str               # 消息
}
```

### RalphEngineCore API

#### execute_task(task_config)

执行单个任务（不重试）。

**返回**：
```python
TaskResult(
    task_id=str,
    success=bool,
    message=str,
    execution_time=float,
    files_changed=List[str],
    commit_hash=str,
    tests_passed=bool,
    test_output=str,  # 详细的测试输出
    errors=List[str],  # 错误列表
    output=str
)
```

#### add_task(task_config)

动态添加新任务。

**参数**：
- `task_config`: TaskConfig 对象

**返回**：
- `str`: 新任务的 ID

#### update_task(task_id, updates)

更新任务配置。

**参数**：
- `task_id`: 任务 ID
- `updates`: 要更新的字段字典

**返回**：
- `bool`: 是否更新成功

#### get_task_status(task_id)

获取任务状态。

**参数**：
- `task_id`: 任务 ID

**返回**：
- `TaskInfo`: 任务信息对象

#### rollback_task(task_id)

回滚任务的代码变更。

**参数**：
- `task_id`: 任务 ID

**返回**：
- `bool`: 是否回滚成功

#### get_code_diff(task_id)

获取任务的代码差异。

**参数**：
- `task_id`: 任务 ID

**返回**：
- `str`: Git diff 输出

## 最佳实践

### 1. 错误分析

```python
def analyze_error(task_result):
    """分析错误并返回修复建议"""
    test_output = task_result.test_output or ""
    
    # 使用正则表达式或 AI 分析错误
    patterns = {
        r"database.*connection": "数据库连接问题",
        r"import.*not found": "导入错误",
        r"syntax error": "语法错误",
        r"timeout": "超时",
    }
    
    for pattern, description in patterns.items():
        if re.search(pattern, test_output, re.IGNORECASE):
            return description
    
    return "未知错误"
```

### 2. 动态任务生成

```python
def create_fix_task(original_task, error_analysis):
    """根据错误分析创建修复任务"""
    return TaskConfig(
        id=f"{original_task.id}-fix",
        name=f"修复 {original_task.name}",
        description=f"""
修复任务: {original_task.name}

错误分析: {error_analysis}

原始错误输出:
{task_result.test_output}

修复建议:
1. 检查错误位置
2. 修正问题
3. 重新运行测试
""",
        depends_on=[original_task.id],
        timeout=original_task.timeout,
        config=original_task.config
    )
```

### 3. 用户交互

```python
def handle_task_failure(task_config, task_result):
    """处理任务失败"""
    print(f"\n任务失败: {task_config.name}")
    print(f"错误信息:\n{task_result.test_output}")
    
    # 提供选项
    print("\n请选择:")
    print("1. 自动修复")
    print("2. 手动修复")
    print("3. 跳过此任务")
    print("4. 回滚并退出")
    
    # 在 Kiro 中，可以通过 UI 获取用户选择
    choice = input("选择 (1-4): ")
    
    if choice == "1":
        # 自动修复
        fix_task = create_fix_task(task_config, task_result)
        return engine.execute_task(fix_task)
    elif choice == "2":
        # 等待用户手动修复
        input("请手动修复代码，完成后按回车继续...")
        return engine.execute_task(task_config)
    elif choice == "3":
        # 跳过
        return None
    else:
        # 回滚并退出
        engine.rollback_task(task_config.id)
        exit(1)
```

### 4. 日志和监控

```python
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ralph-execution.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 记录任务执行
for task_config in config.tasks:
    logger.info(f"开始执行任务: {task_config.name}")
    
    task_result = engine.execute_task(task_config)
    
    if task_result.success:
        logger.info(f"任务成功: {task_config.name}")
        logger.info(f"  - 修改文件: {len(task_result.files_changed)}")
        logger.info(f"  - 执行时间: {task_result.execution_time:.2f}s")
    else:
        logger.error(f"任务失败: {task_config.name}")
        logger.error(f"  - 错误: {task_result.message}")
        logger.error(f"  - 测试输出:\n{task_result.test_output}")
```

## 总结

Agent 驱动模式让 Ralph Skill 从一个"自动执行器"变成了一个"智能工具"，Agent 可以：

1. ✅ 逐个执行任务，完全控制流程
2. ✅ 分析错误原因，生成针对性修复
3. ✅ 动态添加和更新任务
4. ✅ 在需要时询问用户
5. ✅ 回滚失败的任务
6. ✅ 查看代码差异和详细日志

这使得开发过程更加智能、可控和高效。
