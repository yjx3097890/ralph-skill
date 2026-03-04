# Ralph Skill - 企业级自治编程引擎

Ralph Skill 是一个企业级的自治编程引擎，将用户需求自动转化为可执行的代码。

## 目录

- [快速开始](#快速开始)
- [核心特性](#核心特性)
- [工作原理](#工作原理)
- [使用示例](#使用示例)
- [配置说明](#配置说明)
- [常见问题](#常见问题)

---

## 快速开始

### 1. 安装 Skill

```bash
# 复制到 Kiro Skills 目录
cp -r ralph-skill ~/.kiro/skills/

# 安装依赖
cd ~/.kiro/skills/ralph-skill
poetry install
```

### 2. 安装 AI 引擎

以 Qwen Code 为例：

```bash
# 快速安装
curl -fsSL https://qwen-code-assets.oss-cn-hangzhou.aliyuncs.com/installation/install-qwen.sh | bash

# 或使用 npm
npm install -g @qwen-code/qwen-code@latest

# 登录认证
qwen auth login

# 验证安装
qwen --version
```

### 3. 开始使用

**方式 A：在 Kiro 中使用（推荐）**

直接在 Kiro 聊天中描述需求：

```
帮我创建一个 Todo 应用，要求：
- 前端使用 Vue3
- 后端使用 Go + Gin
- 包含单元测试
```

Ralph 会自动：
1. 生成配置文件和任务列表
2. 依次执行所有任务
3. 每个任务：AI 生成代码 → 运行测试 → 失败重试
4. 返回执行结果

**方式 B：使用 Python 调用**

```python
from ralph import autonomous_develop

result = autonomous_develop(
    task_description="创建一个 Todo 应用",
    tech_stack={
        "frontend": {"framework": "vue3"},
        "backend": {"language": "go", "framework": "gin"}
    },
    requirements=[
        "支持添加、删除、完成待办事项",
        "包含单元测试"
    ]
)

print(f"完成 {result['tasks_completed']}/{result['tasks_total']} 个任务")
```

---

## 核心特性

### 🤖 完全自治

- **自动任务规划**：根据需求自动分解为可执行任务
- **智能代码生成**：调用 AI 引擎生成高质量代码
- **自动测试验证**：每个任务完成后自动运行测试
- **失败自动重试**：测试失败时自动重试，最多 3 次

### 🔒 安全可靠

- **Git 版本控制**：所有代码变更自动提交
- **一键回滚**：任何时候都可以回滚到之前的版本
- **安全沙箱**：代码执行在隔离环境中
- **上下文防爆**：智能管理上下文大小，防止 token 超限

### 🎯 技术栈支持

**前端**
- 框架：Vue3, React, Angular
- 测试：Vitest, Jest, Playwright, Cypress
- 构建：Vite, Webpack
- 包管理：npm, yarn, pnpm

**后端**
- 语言：Go, Python, Node.js
- 框架：Gin, Echo, FastAPI, Express
- 测试：Go testing, Pytest, Jest
- 数据库：PostgreSQL, MySQL, Redis

### 🔌 多引擎支持

- Qwen Code
- Aider
- Claude
- GPT-4

---

## 工作原理

```
用户需求 → Ralph Skill
    ↓
1. 任务规划器分析需求
    ↓
2. 生成配置文件和任务列表
    ↓
3. 按依赖顺序执行任务
    ↓
4. 每个任务循环：
   - AI 生成代码
   - 运行测试验证
   - 失败则重试
   - 成功则提交
    ↓
5. 返回执行结果
```

### 自动生成的配置示例

Ralph 会自动生成类似这样的配置：

```yaml
project:
  name: "todo-app"
  type: "fullstack"
  frontend:
    framework: "vue3"
    test_runner: "vitest"
  backend:
    language: "go"
    framework: "gin"

tasks:
  - id: "task-init"
    name: "初始化项目结构"
    type: "feature"
    depends_on: []
    
  - id: "task-backend"
    name: "实现后端 API"
    type: "feature"
    depends_on: ["task-init"]
    
  - id: "task-frontend"
    name: "实现前端界面"
    type: "feature"
    depends_on: ["task-backend"]
    
  - id: "task-tests"
    name: "添加测试"
    type: "test"
    depends_on: ["task-frontend"]

ai_engines:
  qwen_code:
    type: "qwen_code"
    model: "qwen3-coder-plus"
    timeout: 60
```

---

## 使用示例

### 示例 1：快速原型

```python
from ralph import autonomous_develop

# 创建一个简单的 API
result = autonomous_develop(
    task_description="创建一个 Hello World API",
    tech_stack={"backend": {"language": "go", "framework": "gin"}},
    requirements=["实现 GET /hello 端点", "返回 JSON 格式"]
)
```

### 示例 2：全栈应用

```python
# 创建完整的 Todo 应用
result = autonomous_develop(
    task_description="创建一个 Todo 应用",
    tech_stack={
        "frontend": {"framework": "vue3"},
        "backend": {"language": "go", "framework": "gin"}
    },
    requirements=[
        "支持添加、删除、完成待办事项",
        "前端使用 Vue3 + Vite",
        "后端使用 Go + Gin",
        "包含单元测试和 E2E 测试"
    ]
)
```

### 示例 3：使用配置文件

如果需要更精细的控制，可以手动创建配置文件：

```python
# 使用自定义配置
result = autonomous_develop(
    task_description="初始化项目",
    config_file="./my-config.yaml",
    project_root="./my-project"
)
```

---

## 配置说明

### 项目配置

```yaml
project:
  name: "项目名称"
  type: "fullstack"  # frontend, backend, fullstack
  
  frontend:
    framework: "vue3"  # vue3, react, angular
    test_runner: "vitest"  # vitest, jest
    e2e_runner: "playwright"  # playwright, cypress
    build_tool: "vite"  # vite, webpack
    package_manager: "npm"  # npm, yarn, pnpm
  
  backend:
    language: "go"  # go, python, node
    framework: "gin"  # gin, echo, fastapi, express
    build_system: "go"  # go, make
    test_runner: "testing"  # testing, pytest, jest
```

### 任务配置

```yaml
tasks:
  - id: "task-1"
    name: "任务名称"
    type: "feature"  # feature, bugfix, refactor, test, docs
    depends_on: []  # 依赖的任务 ID
    ai_engine: "qwen_code"
    max_retries: 3
    timeout: 1800
    config:
      description: "详细的任务描述"
```

### AI 引擎配置

```yaml
ai_engines:
  qwen_code:
    type: "qwen_code"
    model: "qwen3-coder-plus"
    timeout: 60
```

Ralph 会自动生成配置，也可以手动创建 `ralph-config.yaml`。

---

## 常见问题

### Q: 如何查看执行日志？

```bash
tail -f ~/.kiro/skills/ralph-skill/logs/ralph.log
```

### Q: 任务执行失败怎么办？

Ralph 会自动重试最多 3 次。如果仍然失败：

1. 查看日志了解错误原因
2. 检查 AI 引擎是否正常工作
3. 尝试调整任务描述，提供更多上下文

### Q: 如何回滚代码？

```bash
# 查看提交历史
git log --oneline

# 回滚到上一个版本
git reset --hard HEAD~1

# 回滚到特定提交
git reset --hard <commit-hash>
```

### Q: 支持哪些 AI 引擎？

目前支持：
- **Qwen Code**（推荐）：免费，性能好
- **Aider**：支持多种模型
- **Claude**：代码质量高
- **GPT-4**：通用性强

### Q: 如何添加自定义任务？

创建 `ralph-config.yaml` 并添加任务：

```yaml
tasks:
  - id: "custom-task"
    name: "自定义任务"
    type: "feature"
    depends_on: ["task-init"]
    ai_engine: "qwen_code"
    config:
      description: "你的任务描述"
```

### Q: 可以在团队中使用吗？

可以！建议：
1. 将生成的 `ralph-config.yaml` 提交到 Git
2. 使用环境变量管理敏感信息
3. 团队成员使用相同的配置

---

## 最佳实践

### 1. 明确需求

提供清晰、具体的需求描述：

```python
# ✅ 好的示例
autonomous_develop(
    task_description="实现用户登录功能",
    requirements=[
        "支持邮箱和密码登录",
        "使用 JWT 认证",
        "密码使用 bcrypt 加密",
        "登录失败 5 次后锁定 15 分钟",
        "包含单元测试和集成测试"
    ]
)

# ❌ 不好的示例
autonomous_develop(
    task_description="做一个登录"
)
```

### 2. 分步执行

对于复杂项目，建议分阶段执行：

```python
# 阶段 1：基础功能
autonomous_develop("实现基础 CRUD 功能")

# 阶段 2：添加验证
autonomous_develop("添加数据验证和错误处理")

# 阶段 3：添加权限
autonomous_develop("添加用户权限控制")
```

### 3. 代码审查

Ralph 生成的代码建议人工审查后再合并到主分支。

### 4. 测试验证

运行生成的测试确保功能正确：

```bash
# 后端测试
cd backend && go test ./...

# 前端测试
cd frontend && npm test
```

---

## 示例项目

查看 [`examples/simple-todo-app/`](examples/simple-todo-app/) 获取完整示例。

---

## 故障排查

### 问题：找不到 AI 引擎

```bash
# 检查 Qwen 是否安装
qwen --version

# 重新登录
qwen auth login
```

### 问题：测试失败

```bash
# 查看详细日志
tail -f ~/.kiro/skills/ralph-skill/logs/ralph.log

# 手动运行测试
cd backend && go test -v ./...
```

### 问题：配置解析失败

```bash
# 验证 YAML 语法
python -c "import yaml; yaml.safe_load(open('ralph-config.yaml'))"
```

---

## 技术架构

### 核心组件

- **TaskPlanner**: 任务规划器，分析需求并生成任务列表
- **RalphEngine**: 核心引擎，协调所有组件执行任务
- **AIEngineManager**: AI 引擎管理器，支持多种 AI 引擎
- **GitManager**: Git 管理器，处理版本控制
- **TestRunner**: 测试运行器，自动运行测试验证
- **SafetySandbox**: 安全沙箱，隔离代码执行

### 目录结构

```
ralph-skill/
├── SKILL.md               # Skill 元数据文件（必需）
├── config.example.yaml    # 配置文件示例
├── .env                   # 环境变量（需自行创建，不提交到 Git）
├── src/ralph/             # 源代码
│   ├── __main__.py        # 主入口
│   ├── core/              # 核心引擎
│   │   ├── ralph_engine.py
│   │   └── config_parser.py
│   ├── models/            # 数据模型
│   ├── managers/          # 管理器
│   │   ├── task_planner.py
│   │   ├── task_manager.py
│   │   ├── git_manager.py
│   │   └── ...
│   ├── adapters/          # AI 引擎适配器
│   │   ├── qwen_code_adapter.py
│   │   ├── aider_adapter.py
│   │   └── ...
│   ├── sandbox/           # 安全沙箱
│   └── support/           # 开发支持
├── tests/                 # 测试
├── docs/                  # 文档
├── examples/              # 示例
└── pyproject.toml         # Poetry 配置
```

---

## 开发

### 安装开发依赖

```bash
cd ralph-skill
poetry install
```

### 运行测试

```bash
# 运行所有测试
poetry run pytest

# 运行特定测试
poetry run pytest tests/unit/

# 查看覆盖率
poetry run pytest --cov=ralph --cov-report=html
```

### 代码质量

```bash
# 格式化代码
poetry run black src tests
poetry run isort src tests

# 类型检查
poetry run mypy src

# 代码检查
poetry run flake8 src tests
```

---

## 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md)

## 许可证

MIT License

---

## 支持

- 📖 [完整文档](docs/)
- 💬 [GitHub Discussions](https://github.com/yjx3097890/ralph-skill/discussions)
- 🐛 [报告问题](https://github.com/yjx3097890/ralph-skill/issues)
- 📧 联系作者

---

**提示**：首次使用建议从简单项目开始，熟悉流程后再处理复杂项目。
