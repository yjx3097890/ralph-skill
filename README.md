# Ralph Skill 企业级自治编程引擎

Ralph Skill 是一个企业级的自治编程引擎，旨在将基础的 Ralph 自治循环脚本升级为多智能体协作引擎。该系统封装为符合标准化 Function Calling Schema 的 Skill，供上层 Master Agent（如 OpenClaw、Kiro）调用，支持前端和后端的全栈自动化开发。

## 核心特性

- **安全性**: Git 级别的版本控制和回滚机制，安全沙箱环境
- **可靠性**: 上下文防爆机制，智能错误处理和恢复
- **扩展性**: 多 AI 引擎兼容，插件化钩子系统
- **易用性**: 标准化接口，配置文件驱动
- **全栈支持**: Vue3/Vitest/Playwright 前端，Go/Python 后端

## 技术栈

- **语言**: Python 3.9+
- **依赖管理**: Poetry
- **代码质量**: Black, Flake8, Mypy, isort
- **测试框架**: Pytest
- **版本控制**: GitPython

## 项目结构

```
ralph-skill/
├── skill.md               # Skill 元数据文件（必需）
├── config.yaml            # 配置文件
├── .env                   # 环境变量（需自行创建，不提交到 Git）
├── src/ralph/             # 源代码
│   ├── core/             # 核心引擎
│   ├── models/           # 数据模型
│   ├── managers/         # 管理器（任务、Git、上下文、钩子）
│   ├── adapters/         # AI 引擎适配器
│   ├── sandbox/          # 安全沙箱
│   ├── support/          # 开发支持（前端、后端、Docker）
│   └── utils/            # 工具函数
├── tests/                # 测试
│   ├── unit/            # 单元测试
│   ├── integration/     # 集成测试
│   └── e2e/             # 端到端测试
├── pyproject.toml       # Poetry 配置
└── README.md            # 项目说明
```

### 重要文件说明

- **skill.md**: Skill 元数据文件，定义 Skill 的名称、版本、能力和接口。这是 Kiro/OpenClaw 识别和加载 Skill 的关键文件，必须存在。
- **config.yaml**: 配置文件，包含项目、AI 引擎、安全等所有配置项。
- **pyproject.toml**: Python 项目配置，包含依赖和开发工具配置。

## 快速开始

### 安装依赖

```bash
# 安装 Poetry（如果尚未安装）
curl -sSL https://install.python-poetry.org | python3 -

# 安装项目依赖
poetry install
```

### 安装 AI 引擎 CLI 工具

Ralph Skill 通过 CLI 工具调用 AI 引擎，需要先安装相应的工具：

#### Qwen Code CLI

```bash
# 使用 pip 安装
pip install qwen-code

# 或使用 pipx 安装（推荐，避免依赖冲突）
pipx install qwen-code

# 验证安装
qwen-code --version
```

#### Aider CLI

```bash
# 使用 pip 安装
pip install aider-chat

# 或使用 pipx 安装（推荐）
pipx install aider-chat

# 验证安装
aider --version
```

#### Claude CLI（可选）

如果使用 Claude，请参考 Anthropic 官方文档安装 CLI 工具。

**注意**：只需安装你实际使用的 AI 引擎的 CLI 工具。例如，如果只使用 Qwen Code，只需安装 `qwen-code`。

### 运行测试

```bash
# 运行所有测试
poetry run pytest

# 运行单元测试
poetry run pytest tests/unit

# 运行测试并生成覆盖率报告
poetry run pytest --cov=ralph --cov-report=html
```

### 代码质量检查

```bash
# 代码格式化
poetry run black src tests

# 导入排序
poetry run isort src tests

# 代码检查
poetry run flake8 src tests

# 类型检查
poetry run mypy src
```

## 在 AI Agent 中使用 Ralph Skill

Ralph Skill 可以作为 Skill 集成到支持 Function Calling 的 AI Agent 系统中，如 OpenClaw 和 Kiro。

### 什么是 Skill？

Skill 是一种标准化的能力封装方式，让 AI Agent 能够调用外部工具和服务。Ralph Skill 将自治编程能力封装为标准接口，供上层 Agent 调用。

### 在 Kiro 中使用

Kiro 是一个 AI 驱动的 IDE，支持通过 Skills 扩展能力。

#### 1. 安装 Ralph Skill

将 Ralph Skill 安装到 Kiro 的 skills 目录：

```bash
# 用户级别（推荐）
mkdir -p ~/.kiro/skills/
cd ~/.kiro/skills/
git clone git@github.com:yjx3097890/ralph-skill.git

# 或工作区级别
mkdir -p .kiro/skills/
cd .kiro/skills/
git clone git@github.com:yjx3097890/ralph-skill.git
```

#### 2. 配置 Skill

在 Ralph Skill 目录中编辑配置文件：

```bash
cd ~/.kiro/skills/ralph-skill

# 编辑配置文件
vim config.yaml
```

创建 `.env` 文件设置 API 密钥（只需配置你要使用的 AI 引擎）：

```bash
# 创建 .env 文件
# 注意：只需要配置你实际使用的 AI 引擎的 API 密钥
# 例如，如果只使用 Qwen，只需设置 QWEN_API_KEY

cat > .env << EOF
# 根据需要选择配置一个或多个
QWEN_API_KEY=your-qwen-api-key
# CLAUDE_API_KEY=your-claude-api-key
# OPENAI_API_KEY=your-openai-api-key
EOF
```

编辑 `config.yaml` 指定使用的 AI 引擎：

```yaml
# 在任务配置中指定使用的引擎
tasks:
  - id: "task-1"
    name: "实现用户认证"
    ai_engine: "qwen_code"  # 使用 Qwen（或 claude, gpt4, aider）
    
# AI 引擎配置（只需保留你使用的引擎配置）
ai_engines:
  qwen_code:
    type: "qwen_code"
    api_key: "${QWEN_API_KEY}"
    model: "qwen-coder-plus"
```

**重要说明**：
- 你只需要配置实际使用的 AI 引擎的 API 密钥
- 未配置的引擎不会被使用，也不会报错
- 建议在 `config.yaml` 中删除或注释掉不使用的引擎配置，保持配置文件简洁

#### 3. 在 Kiro 中激活 Skill

在 Kiro 中，你可以通过以下方式使用 Ralph Skill：

**方式 1：通过聊天界面**

```
你: 使用 Ralph Skill 帮我实现一个用户登录功能

Kiro: [自动检测并激活 Ralph Skill]
      正在使用 Ralph Skill 进行自治开发...
```

**方式 2：通过命令面板**

1. 按 `Cmd/Ctrl + Shift + P` 打开命令面板
2. 输入 "Activate Skill"
3. 选择 "ralph-skill"
4. 在聊天中描述你的需求

**方式 3：在 Spec 中引用**

在 `.kiro/specs/` 目录下的需求文档中引用 Skill：

```markdown
# 需求文档

## 实现方式

使用 #ralph-skill 进行自治开发，实现以下功能：
- 用户注册
- 用户登录
- 密码重置
```

#### 4. 查看 Skill 状态

```bash
# 查看已安装的 Skills
ls ~/.kiro/skills/

# 查看 Ralph Skill 日志
tail -f ~/.kiro/skills/ralph-skill/logs/ralph.log
```

### 在 OpenClaw 中使用

OpenClaw 是一个多智能体协作平台，支持通过 Skills 扩展能力。

#### 1. 注册 Skill

在 OpenClaw 配置文件中注册 Ralph Skill：

```yaml
# ~/.openclaw/config.yaml
skills:
  - name: ralph-skill
    path: /path/to/ralph-skill
    enabled: true
    config:
      ai_engine:
        type: claude
        api_key: ${CLAUDE_API_KEY}
```

#### 2. 调用 Skill

在 OpenClaw 的任务定义中调用 Ralph Skill：

```python
from openclaw import Agent, Task

agent = Agent(name="developer")

task = Task(
    description="实现用户认证模块",
    agent=agent,
    skills=["ralph-skill"],
    context={
        "requirements": "支持邮箱和手机号登录",
        "tech_stack": "Go + Gin + GORM"
    }
)

result = task.execute()
```

### Skill 功能说明

Ralph Skill 提供以下核心能力：

| 功能 | 说明 | 示例 |
|------|------|------|
| **自治开发** | 根据需求自动生成代码 | "实现用户注册功能" |
| **测试生成** | 自动生成单元测试和集成测试 | "为登录模块生成测试" |
| **代码重构** | 智能重构和优化代码 | "重构用户服务层" |
| **Bug 修复** | 自动诊断和修复问题 | "修复登录失败的 bug" |
| **文档生成** | 生成 API 文档和注释 | "生成 API 文档" |
| **前端支持** | Vue3/React 组件开发 | "实现登录表单组件" |
| **后端支持** | Go/Python 服务开发 | "实现 RESTful API" |

### 配置选项

Ralph Skill 支持丰富的配置选项：

```yaml
# config.yaml

# AI 引擎配置
ai_engine:
  type: "claude"              # AI 引擎类型
  api_key: "your-api-key"     # API 密钥
  model: "claude-3-5-sonnet"  # 模型名称
  temperature: 0.7            # 温度参数
  max_tokens: 4096            # 最大 token 数

# 安全配置
safety:
  enable_sandbox: true        # 启用沙箱
  max_context_tokens: 100000  # 最大上下文 token
  allowed_commands:           # 允许的命令
    - "git"
    - "npm"
    - "go"

# Git 配置
git:
  auto_commit: true           # 自动提交
  commit_message_prefix: "feat" # 提交信息前缀
  enable_rollback: true       # 启用回滚

# 钩子配置
hooks:
  pre_task: []                # 任务前钩子
  post_task: []               # 任务后钩子
  on_error: []                # 错误钩子

# 前端支持
frontend:
  framework: "vue3"           # 前端框架
  test_framework: "vitest"    # 测试框架
  e2e_framework: "playwright" # E2E 测试框架

# 后端支持
backend:
  language: "go"              # 后端语言
  test_framework: "testing"   # 测试框架
```

### 常见问题

**Q: 只配置一个 AI 引擎可以吗？**

A: 可以！你只需要配置实际使用的 AI 引擎。例如只使用 Qwen：

```bash
# .env 文件
QWEN_API_KEY=your-qwen-api-key
```

```yaml
# config.yaml - 只保留 qwen_code 配置
ai_engines:
  qwen_code:
    type: "qwen_code"
    api_key: "${QWEN_API_KEY}"
    model: "qwen-coder-plus"

# 任务中指定使用 qwen_code
tasks:
  - id: "task-1"
    ai_engine: "qwen_code"
```

未配置的引擎不会被加载，也不会报错。

**Q: 如何知道 Skill 是否安装成功？**

A: 在 Kiro 中，打开命令面板（`Cmd/Ctrl + Shift + P`），输入 "List Skills"，应该能看到 ralph-skill。

**Q: Skill 调用失败怎么办？**

A: 检查以下几点：
1. 配置文件是否正确（`config.yaml`）
2. API 密钥是否有效
3. 查看日志文件：`~/.kiro/skills/ralph-skill/logs/ralph.log`

**Q: 如何更新 Skill？**

A: 进入 Skill 目录执行：
```bash
cd ~/.kiro/skills/ralph-skill
git pull
poetry install
```

注意：更新后请检查 `config.yaml` 是否需要添加新的配置项。

**Q: 可以同时使用多个 AI 引擎吗？**

A: 可以。在配置文件中设置 `ai_engine.type`，支持 claude、gpt4、aider、qwen 等。

**Q: Skill 会修改我的代码吗？**

A: Ralph Skill 使用 Git 进行版本控制，所有修改都会自动提交。如果不满意，可以使用 `git reset` 回滚。

### 最佳实践

1. **明确需求**：向 Agent 提供清晰的需求描述，包括功能、技术栈、约束条件
2. **分步执行**：对于复杂任务，建议分解为多个小任务逐步完成
3. **代码审查**：Skill 生成的代码建议人工审查后再合并到主分支
4. **测试验证**：运行生成的测试确保功能正确性
5. **配置管理**：使用环境变量管理敏感信息（如 API 密钥）

### 示例：完整工作流

```bash
# 1. 安装 Skill
mkdir -p ~/.kiro/skills/
cd ~/.kiro/skills/
git clone git@github.com:yjx3097890/ralph-skill.git
cd ralph-skill
poetry install

# 2. 配置环境变量（只配置你使用的 AI 引擎）
cat > .env << EOF
QWEN_API_KEY=your-qwen-api-key
EOF

# 3. 编辑配置文件（可选，默认配置已包含常用引擎）
# 如果只使用 Qwen，建议删除其他引擎配置保持简洁
vim config.yaml

# 4. 在 Kiro 中使用
# 打开 Kiro，在聊天中输入：
# "使用 Ralph Skill 实现用户登录功能，要求：
#  - 支持邮箱和密码登录
#  - 使用 JWT 认证
#  - 包含单元测试
#  - 技术栈：Go + Gin + GORM"

# 4. 查看结果
git log  # 查看自动提交记录
git diff HEAD~1  # 查看代码变更

# 5. 运行测试
go test ./...

# 6. 如果需要回滚
git reset --hard HEAD~1
```

## 开发指南

### 代码规范

- 遵循 PEP 8 代码风格
- 使用 Black 进行代码格式化（行长度 100）
- 使用 isort 进行导入排序
- 使用类型注解（Type Hints）
- 编写中文注释和文档字符串

### 测试规范

- 单元测试覆盖率 > 80%
- 为所有公共函数编写测试
- 使用 pytest 标记区分测试类型（unit, integration, e2e）
- 测试文件命名：`test_*.py` 或 `*_test.py`

### 提交规范

- 提交信息使用中文
- 格式：`类型: 简短描述`
- 类型：功能、修复、文档、测试、重构、样式

## 许可证

MIT License

## 联系方式

Ralph Team
