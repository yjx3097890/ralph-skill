# 在 Kiro 中使用 Ralph Skill

## 问题诊断

如果 Kiro 激活了 Ralph Skill 但没有调用 `autonomous_develop` 函数，而是手动创建项目结构，说明 Kiro 不知道该如何调用 Ralph。

## 正确的使用方式

### 方式 1：让 Kiro 执行 Python 代码（推荐）

当用户说"使用 Ralph 创建..."时，Kiro 应该执行以下 Python 代码：

```python
import sys
from pathlib import Path

# 添加 Ralph Skill 到路径
skill_path = Path.home() / ".kiro" / "skills" / "ralph-skill"
sys.path.insert(0, str(skill_path / "src"))

from ralph import autonomous_develop

# 调用自治开发函数
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
    project_root="."
)

# 输出结果
if result["success"]:
    print(f"✅ 成功完成 {result['tasks_completed']}/{result['tasks_total']} 个任务")
    print(f"📁 配置文件: {result.get('config_file', 'N/A')}")
else:
    print(f"❌ 部分任务失败: {result['tasks_completed']}/{result['tasks_total']}")
    print("失败的任务:")
    for task_id, task_result in result['results'].items():
        if not task_result['success']:
            print(f"  - {task_id}: {task_result['message']}")
```

### 方式 2：使用命令行

Kiro 也可以执行命令行：

```bash
cd ~/.kiro/skills/ralph-skill
poetry run python -m ralph develop "创建一个 Todo 应用" \
    --tech-stack '{"frontend": {"framework": "vue3"}, "backend": {"language": "go"}}' \
    --requirements "支持添加、删除待办事项" "包含单元测试" \
    --project-root /path/to/project
```

### 方式 3：使用包装脚本

```bash
cd ~/.kiro/skills/ralph-skill
poetry run python ralph_cli.py '{
  "task_description": "创建一个 Todo 应用",
  "tech_stack": {
    "frontend": {"framework": "vue3"},
    "backend": {"language": "go", "framework": "gin"}
  },
  "requirements": [
    "支持添加、删除待办事项",
    "包含单元测试"
  ],
  "project_root": "."
}'
```

## 关键点

1. **不要手动创建项目结构** - Ralph 会自动创建
2. **不要手动创建配置文件** - Ralph 会自动生成 `ralph-config.yaml`
3. **直接调用 `autonomous_develop()` 函数** - 这是唯一的入口点
4. **Ralph 会自动调用 Qwen/Claude/GPT-4** - 不需要手动调用 AI 引擎

## 工作流程

```
用户需求
    ↓
Kiro 调用 autonomous_develop()
    ↓
Ralph 自动生成配置文件
    ↓
Ralph 按顺序执行任务
    ↓
每个任务：AI 生成代码 → 测试 → 重试（如果失败）
    ↓
返回结果给 Kiro
```

## 示例对话

**用户**: 使用 Ralph 创建一个 Todo 应用，前端用 Vue3，后端用 Go

**Kiro 应该做的**:
```python
# 执行 Python 代码
from ralph import autonomous_develop
result = autonomous_develop(
    task_description="创建一个 Todo 应用",
    tech_stack={
        "frontend": {"framework": "vue3"},
        "backend": {"language": "go"}
    }
)
```

**Kiro 不应该做的**:
- ❌ 手动创建 `frontend/` 目录
- ❌ 手动创建 `backend/` 目录
- ❌ 手动创建 `ralph-config.yaml`
- ❌ 手动写代码

## 技术栈配置格式

```python
tech_stack = {
    "frontend": {
        "framework": "vue3",      # vue3, react, angular
        "test_runner": "vitest",  # vitest, jest
        "build_tool": "vite",     # vite, webpack
        "package_manager": "npm"  # npm, yarn, pnpm
    },
    "backend": {
        "language": "go",         # go, python, node
        "framework": "gin",       # gin, echo, fastapi, express
        "test_runner": "testing"  # testing, pytest, jest
    }
}
```

## 返回值格式

```python
{
    "success": True,              # 是否全部成功
    "tasks_completed": 4,         # 完成的任务数
    "tasks_total": 4,             # 总任务数
    "config_file": "ralph-config.yaml",  # 生成的配置文件
    "results": {                  # 每个任务的结果
        "task-1": {
            "success": True,
            "message": "任务完成"
        }
    },
    "message": "完成 4/4 个任务"
}
```

## 故障排查

### 问题：找不到 ralph 模块

**解决方案**：确保正确添加路径

```python
import sys
from pathlib import Path
skill_path = Path.home() / ".kiro" / "skills" / "ralph-skill"
sys.path.insert(0, str(skill_path / "src"))
```

### 问题：AI 引擎未配置

**解决方案**：Ralph 会自动使用 Qwen Code，确保已安装：

```bash
# 安装 Qwen Code
curl -fsSL https://qwen-code-assets.oss-cn-hangzhou.aliyuncs.com/installation/install-qwen.sh | bash

# 登录
qwen auth login
```

### 问题：任务执行失败

**解决方案**：查看返回的 `results` 字段了解具体错误

```python
if not result["success"]:
    for task_id, task_result in result["results"].items():
        if not task_result["success"]:
            print(f"任务 {task_id} 失败: {task_result['message']}")
```
