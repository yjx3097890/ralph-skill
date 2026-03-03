# Ralph Skill 使用指南

本指南将通过一个简单的 Todo 应用示例，教你如何在新项目中使用 Ralph Skill 进行自治开发。

## 目录

1. [快速开始](#快速开始)
2. [项目示例：Todo 应用](#项目示例todo-应用)
3. [配置文件详解](#配置文件详解)
4. [使用场景](#使用场景)
5. [最佳实践](#最佳实践)

---

## 快速开始

### 前置条件

1. **已安装 Ralph Skill**
   ```bash
   # 验证安装
   ls ~/.kiro/skills/ralph-skill
   ```

2. **已安装 AI 引擎 CLI 工具**（以 Qwen Code 为例）
   ```bash
   # 安装 Qwen Code
   curl -fsSL https://qwen-code-assets.oss-cn-hangzhou.aliyuncs.com/installation/install-qwen.sh | bash
   
   # 登录认证
   qwen auth login
   
   # 验证
   qwen --version
   ```

3. **创建新项目目录**
   ```bash
   mkdir my-todo-app
   cd my-todo-app
   git init
   ```

---

## 项目示例：Todo 应用

我们将创建一个全栈 Todo 应用：
- **前端**：Vue3 + Vite + Vitest
- **后端**：Go + Gin
- **数据库**：PostgreSQL

### 步骤 1：创建项目配置文件

在项目根目录创建 `ralph-config.yaml`：

```yaml
# ralph-config.yaml
# Todo 应用配置

# 项目配置
project:
  name: "todo-app"
  type: "fullstack"
  
  # 前端配置
  frontend:
    framework: "vue3"
    test_runner: "vitest"
    e2e_runner: "playwright"
    build_tool: "vite"
    package_manager: "npm"
  
  # 后端配置
  backend:
    language: "go"
    framework: "gin"
    build_system: "go"
    dependency_manager: "go_mod"
    test_runner: "testing"
  
  # 数据库配置
  database:
    type: "postgresql"
    host: "localhost"
    port: 5432
    database: "todo_db"
    user: "todo_user"
    password: "todo_pass"
    ssl_mode: "prefer"
    connection_timeout: 30
    pool_size: 10
    max_overflow: 20

# 任务配置
tasks:
  # 任务 1：初始化项目结构
  - id: "task-1"
    name: "初始化项目结构"
    type: "feature"
    depends_on: []
    ai_engine: "qwen_code"
    max_retries: 3
    timeout: 1800
    hooks:
      pre_task: []
      post_task: []
    config:
      description: |
        创建项目基础结构：
        - 前端目录：frontend/（Vue3 + Vite）
        - 后端目录：backend/（Go + Gin）
        - 数据库迁移目录：backend/migrations/
        - 配置文件：.env.example
        - README.md
  
  # 任务 2：实现后端 API
  - id: "task-2"
    name: "实现后端 Todo API"
    type: "feature"
    depends_on: ["task-1"]
    ai_engine: "qwen_code"
    max_retries: 3
    timeout: 1800
    hooks:
      pre_task: []
      post_task: []
    config:
      description: |
        实现 RESTful API：
        - GET /api/todos - 获取所有待办事项
        - POST /api/todos - 创建待办事项
        - PUT /api/todos/:id - 更新待办事项
        - DELETE /api/todos/:id - 删除待办事项
        - 包含单元测试（覆盖率 > 80%）
        - 包含 API 文档
  
  # 任务 3：实现前端界面
  - id: "task-3"
    name: "实现前端 Todo 界面"
    type: "feature"
    depends_on: ["task-2"]
    ai_engine: "qwen_code"
    max_retries: 3
    timeout: 1800
    hooks:
      pre_task: []
      post_task: []
    config:
      description: |
        实现 Vue3 组件：
        - TodoList.vue - 待办列表组件
        - TodoItem.vue - 待办项组件
        - TodoForm.vue - 添加表单组件
        - 使用 Composition API
        - 包含 Vitest 单元测试
        - 响应式设计
  
  # 任务 4：集成测试
  - id: "task-4"
    name: "编写端到端测试"
    type: "test"
    depends_on: ["task-3"]
    ai_engine: "qwen_code"
    max_retries: 3
    timeout: 1800
    hooks:
      pre_task: []
      post_task: []
    config:
      description: |
        使用 Playwright 编写 E2E 测试：
        - 测试添加待办事项
        - 测试标记完成
        - 测试删除待办事项
        - 测试筛选功能

# 安全配置
safety:
  enable_sandbox: true
  max_context_tokens: 100000
  allowed_commands:
    - "git"
    - "npm"
    - "go"
    - "docker"
    - "make"

# Git 配置
git:
  auto_commit: true
  commit_message_prefix: "feat"
  enable_rollback: true

# 系统设置
settings:
  sandbox_timeout: 300
  max_retries: 3
  log_level: "info"
  enable_hooks: true

# AI 引擎配置
ai_engines:
  qwen_code:
    type: "qwen_code"
    cli_path: "qwen"
    model: "qwen3-coder-plus"
    timeout: 60
```

### 步骤 2：在 Kiro 中使用 Ralph Skill

#### 方式 1：通过 Kiro 聊天

在 Kiro 中打开项目目录，然后在聊天中输入：

```
使用 Ralph Skill 根据 ralph-config.yaml 配置文件执行任务 task-1
```

或者更简单的方式：

```
帮我用 Ralph 初始化一个 Todo 应用项目
```

#### 方式 2：通过 Python 脚本

创建 `run_ralph.py`：

```python
#!/usr/bin/env python3
"""
Ralph Skill 运行脚本
"""

import sys
from pathlib import Path

# 添加 Ralph Skill 到 Python 路径
skill_path = Path.home() / ".kiro" / "skills" / "ralph-skill"
sys.path.insert(0, str(skill_path / "src"))

from ralph.core.config_parser import ConfigParser
from ralph.core.ralph_engine import RalphEngine

def main():
    # 解析配置文件
    config_file = Path("ralph-config.yaml")
    if not config_file.exists():
        print("❌ 配置文件不存在: ralph-config.yaml")
        return 1
    
    parser = ConfigParser()
    config = parser.parse_config(str(config_file))
    
    print(f"📋 项目: {config.project.name}")
    print(f"📦 任务数量: {len(config.tasks)}")
    print()
    
    # 创建 Ralph 引擎
    engine = RalphEngine(config)
    
    # 执行所有任务
    print("🚀 开始执行任务...")
    results = engine.run_all_tasks()
    
    # 打印结果
    print("\n" + "=" * 60)
    print("执行结果")
    print("=" * 60)
    
    for task_id, result in results.items():
        status = "✅" if result.success else "❌"
        print(f"{status} {task_id}: {result.message}")
    
    return 0 if all(r.success for r in results.values()) else 1

if __name__ == "__main__":
    sys.exit(main())
```

运行脚本：

```bash
# 在 Ralph Skill 的虚拟环境中运行
cd ~/.kiro/skills/ralph-skill
poetry run python /path/to/your/project/run_ralph.py
```

### 步骤 3：查看生成的代码

执行完成后，项目结构应该如下：

```
my-todo-app/
├── frontend/                 # 前端代码
│   ├── src/
│   │   ├── components/
│   │   │   ├── TodoList.vue
│   │   │   ├── TodoItem.vue
│   │   │   └── TodoForm.vue
│   │   ├── App.vue
│   │   └── main.ts
│   ├── tests/               # 前端测试
│   │   └── unit/
│   ├── e2e/                 # E2E 测试
│   ├── package.json
│   ├── vite.config.ts
│   └── vitest.config.ts
├── backend/                 # 后端代码
│   ├── main.go
│   ├── handlers/
│   │   └── todo_handler.go
│   ├── models/
│   │   └── todo.go
│   ├── database/
│   │   └── db.go
│   ├── migrations/
│   │   └── 001_create_todos.sql
│   ├── tests/
│   │   └── todo_test.go
│   ├── go.mod
│   └── go.sum
├── ralph-config.yaml        # Ralph 配置
├── .env.example             # 环境变量示例
├── docker-compose.yml       # Docker 配置
└── README.md                # 项目文档
```

### 步骤 4：运行项目

```bash
# 启动数据库
docker-compose up -d postgres

# 运行后端
cd backend
go run main.go

# 运行前端（新终端）
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173 查看应用。

### 步骤 5：运行测试

```bash
# 后端测试
cd backend
go test ./...

# 前端单元测试
cd frontend
npm run test

# E2E 测试
npm run test:e2e
```

---

## 配置文件详解

### 项目配置 (project)

```yaml
project:
  name: "项目名称"           # 必需
  type: "fullstack"          # 必需：frontend, backend, fullstack
  
  frontend:                  # 可选：前端配置
    framework: "vue3"        # vue3, react, angular
    test_runner: "vitest"    # vitest, jest
    e2e_runner: "playwright" # playwright, cypress
    build_tool: "vite"       # vite, webpack
    package_manager: "npm"   # npm, yarn, pnpm
  
  backend:                   # 可选：后端配置
    language: "go"           # go, python, node
    framework: "gin"         # gin, echo, fastapi, express
    build_system: "go"       # go, make
    dependency_manager: "go_mod"  # go_mod, pip, npm
    test_runner: "testing"   # testing, pytest, jest
  
  database:                  # 可选：数据库配置
    type: "postgresql"       # postgresql, mysql, redis
    host: "localhost"
    port: 5432
    database: "mydb"
    user: "user"
    password: "password"
```

### 任务配置 (tasks)

```yaml
tasks:
  - id: "task-1"             # 必需：唯一标识符
    name: "任务名称"          # 必需：任务描述
    type: "feature"          # 必需：feature, bugfix, refactor, test, docs
    depends_on: []           # 可选：依赖的任务 ID 列表
    ai_engine: "qwen_code"   # 必需：使用的 AI 引擎
    max_retries: 3           # 可选：最大重试次数
    timeout: 1800            # 可选：超时时间（秒）
    hooks:                   # 可选：钩子配置
      pre_task: []           # 任务前执行的命令
      post_task: []          # 任务后执行的命令
    config:                  # 可选：任务特定配置
      description: "详细描述"
```

### AI 引擎配置 (ai_engines)

```yaml
ai_engines:
  # Qwen Code
  qwen_code:
    type: "qwen_code"
    cli_path: "qwen"         # CLI 工具路径
    model: "qwen3-coder-plus"
    timeout: 60
  
  # Aider
  aider:
    type: "aider"
    cli_path: "aider"
    model: "gpt-4"
    timeout: 60
  
  # Claude
  claude:
    type: "claude"
    cli_path: "claude"
    model: "claude-3-5-sonnet-20241022"
    timeout: 60
```

---

## 使用场景

### 场景 1：快速原型开发

```yaml
# 配置简单的单页应用
project:
  name: "landing-page"
  type: "frontend"
  frontend:
    framework: "vue3"
    test_runner: "vitest"

tasks:
  - id: "prototype"
    name: "创建落地页原型"
    type: "feature"
    ai_engine: "qwen_code"
    config:
      description: |
        创建一个产品落地页，包含：
        - Hero 区域
        - 功能介绍
        - 定价表
        - 联系表单
```

### 场景 2：Bug 修复

```yaml
tasks:
  - id: "fix-login-bug"
    name: "修复登录失败问题"
    type: "bugfix"
    ai_engine: "qwen_code"
    config:
      description: |
        修复 Bug：
        - 问题：用户输入正确密码但无法登录
        - 错误信息：invalid credentials
        - 受影响文件：backend/handlers/auth.go
```

### 场景 3：代码重构

```yaml
tasks:
  - id: "refactor-user-service"
    name: "重构用户服务层"
    type: "refactor"
    ai_engine: "qwen_code"
    config:
      description: |
        重构目标：
        - 提取公共逻辑到 utils
        - 优化数据库查询
        - 改善错误处理
        - 添加日志记录
```

### 场景 4：测试补充

```yaml
tasks:
  - id: "add-tests"
    name: "补充单元测试"
    type: "test"
    ai_engine: "qwen_code"
    config:
      description: |
        为以下模块添加测试：
        - backend/handlers/todo_handler.go
        - 目标覆盖率：> 80%
        - 包含边界情况测试
```

### 场景 5：文档生成

```yaml
tasks:
  - id: "generate-docs"
    name: "生成 API 文档"
    type: "docs"
    ai_engine: "qwen_code"
    config:
      description: |
        生成文档：
        - OpenAPI 3.0 规范
        - 包含所有端点
        - 请求/响应示例
        - 错误码说明
```

---

## 最佳实践

### 1. 任务拆分

将大任务拆分为小任务，每个任务专注于单一功能：

```yaml
# ❌ 不好的做法
tasks:
  - id: "build-everything"
    name: "构建整个应用"
    # 太大，难以管理

# ✅ 好的做法
tasks:
  - id: "setup-project"
    name: "初始化项目结构"
  
  - id: "implement-models"
    name: "实现数据模型"
    depends_on: ["setup-project"]
  
  - id: "implement-api"
    name: "实现 API 端点"
    depends_on: ["implement-models"]
  
  - id: "add-tests"
    name: "添加测试"
    depends_on: ["implement-api"]
```

### 2. 明确需求描述

提供清晰、具体的需求描述：

```yaml
# ❌ 不好的做法
config:
  description: "做一个登录功能"

# ✅ 好的做法
config:
  description: |
    实现用户登录功能：
    - 支持邮箱和密码登录
    - 使用 JWT 认证
    - 密码使用 bcrypt 加密
    - 登录失败 5 次后锁定账户 15 分钟
    - 包含单元测试和集成测试
    - 返回标准 JSON 响应
```

### 3. 使用依赖关系

合理使用 `depends_on` 确保任务按正确顺序执行：

```yaml
tasks:
  - id: "database-schema"
    name: "设计数据库模式"
    depends_on: []
  
  - id: "backend-api"
    name: "实现后端 API"
    depends_on: ["database-schema"]  # 依赖数据库模式
  
  - id: "frontend-ui"
    name: "实现前端界面"
    depends_on: ["backend-api"]      # 依赖后端 API
  
  - id: "e2e-tests"
    name: "端到端测试"
    depends_on: ["frontend-ui"]      # 依赖前端界面
```

### 4. 配置钩子

使用钩子在任务前后执行命令：

```yaml
tasks:
  - id: "deploy-backend"
    name: "部署后端服务"
    type: "feature"
    ai_engine: "qwen_code"
    hooks:
      pre_task:
        - "go test ./..."           # 部署前运行测试
        - "go build -o app main.go" # 构建应用
      post_task:
        - "docker build -t myapp ."  # 构建 Docker 镜像
        - "docker push myapp:latest" # 推送镜像
```

### 5. 版本控制

启用自动提交，方便回滚：

```yaml
git:
  auto_commit: true                # 自动提交代码变更
  commit_message_prefix: "feat"    # 提交信息前缀
  enable_rollback: true            # 启用回滚功能
```

如果需要回滚：

```bash
# 查看提交历史
git log --oneline

# 回滚到上一个版本
git reset --hard HEAD~1

# 回滚到特定提交
git reset --hard <commit-hash>
```

### 6. 多引擎策略

为不同任务使用不同的 AI 引擎：

```yaml
ai_engines:
  qwen_code:
    type: "qwen_code"
    model: "qwen3-coder-plus"
  
  claude:
    type: "claude"
    model: "claude-3-5-sonnet-20241022"

tasks:
  - id: "implement-feature"
    name: "实现功能"
    ai_engine: "qwen_code"  # 使用 Qwen 实现功能
  
  - id: "code-review"
    name: "代码审查"
    ai_engine: "claude"     # 使用 Claude 审查代码
```

### 7. 测试驱动开发

先写测试，再实现功能：

```yaml
tasks:
  - id: "write-tests"
    name: "编写测试用例"
    type: "test"
    ai_engine: "qwen_code"
    config:
      description: "为用户认证功能编写测试用例"
  
  - id: "implement-feature"
    name: "实现功能"
    type: "feature"
    depends_on: ["write-tests"]  # 先有测试，再实现
    ai_engine: "qwen_code"
    config:
      description: "实现用户认证功能，确保所有测试通过"
```

### 8. 增量开发

逐步添加功能，每次提交都是可工作的版本：

```yaml
tasks:
  # 第一阶段：基础功能
  - id: "basic-crud"
    name: "实现基础 CRUD"
  
  # 第二阶段：添加验证
  - id: "add-validation"
    name: "添加数据验证"
    depends_on: ["basic-crud"]
  
  # 第三阶段：添加权限
  - id: "add-auth"
    name: "添加权限控制"
    depends_on: ["add-validation"]
  
  # 第四阶段：性能优化
  - id: "optimize"
    name: "性能优化"
    depends_on: ["add-auth"]
```

---

## 常见问题

### Q1: 如何查看任务执行日志？

日志文件位于：`~/.kiro/skills/ralph-skill/logs/ralph.log`

```bash
# 实时查看日志
tail -f ~/.kiro/skills/ralph-skill/logs/ralph.log
```

### Q2: 任务执行失败怎么办？

1. 查看错误信息
2. 检查配置文件语法
3. 验证 AI 引擎配置
4. 增加 `max_retries` 重试次数
5. 调整任务描述，提供更多上下文

### Q3: 如何暂停/恢复任务执行？

Ralph 支持任务状态管理：

```python
# 暂停任务
engine.pause_task("task-id")

# 恢复任务
engine.resume_task("task-id")

# 取消任务
engine.cancel_task("task-id")
```

### Q4: 如何自定义 AI 引擎参数？

在配置文件中调整参数：

```yaml
ai_engines:
  qwen_code:
    type: "qwen_code"
    cli_path: "qwen"
    model: "qwen3-coder-plus"
    timeout: 120              # 增加超时时间
    temperature: 0.7          # 调整创造性
    max_tokens: 8192          # 增加最大 token 数
```

### Q5: 如何在团队中共享配置？

1. 将 `ralph-config.yaml` 提交到 Git
2. 使用环境变量管理敏感信息
3. 创建 `.env.example` 文件作为模板

```yaml
# ralph-config.yaml
project:
  database:
    host: "${DB_HOST}"
    password: "${DB_PASSWORD}"
```

```bash
# .env
DB_HOST=localhost
DB_PASSWORD=secret
```

---

## 下一步

- 查看 [SKILL.md](ralph-skill/SKILL.md) 了解更多功能
- 查看 [examples/](ralph-skill/examples/) 目录获取更多示例
- 加入社区讨论和反馈

---

**提示**：首次使用建议从简单项目开始，熟悉流程后再处理复杂项目。
