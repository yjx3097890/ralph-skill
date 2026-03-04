# 简单 Todo 应用示例

这是一个使用 Ralph Skill 创建的最简单的全栈应用示例，适合快速入门。

## 项目概述

- **前端**：Vue3 + Vite + Vitest
- **后端**：Go + Gin（内存存储）
- **功能**：基础的 Todo CRUD 操作

## 快速开始

### 前置条件

1. 已安装 Ralph Skill
2. 已安装并配置 Qwen Code CLI
3. 已安装 Node.js 和 Go

### 步骤 1：创建项目目录

```bash
# 创建项目目录
mkdir simple-todo-app
cd simple-todo-app

# 初始化 Git
git init

# 复制配置文件
cp ~/.kiro/skills/ralph-skill/examples/simple-todo-app/ralph-config.yaml .
```

### 步骤 2：使用 Ralph 生成代码

#### 方式 A：在 Kiro 中使用（推荐）

1. 在 Kiro 中打开项目目录
2. 在聊天中输入：

```
使用 Ralph Skill 根据 ralph-config.yaml 执行所有任务
```

或者更简单：

```
帮我用 Ralph 创建一个 Todo 应用
```

#### 方式 B：使用 Python 脚本

创建 `run.py`：

```python
#!/usr/bin/env python3
import sys
from pathlib import Path

# 添加 Ralph Skill 到路径
skill_path = Path.home() / ".kiro" / "skills" / "ralph-skill"
sys.path.insert(0, str(skill_path / "src"))

from ralph.core.config_parser import ConfigParser
from ralph.core.ralph_engine import RalphEngine

# 解析配置
parser = ConfigParser()
config = parser.parse_config("ralph-config.yaml")

# 运行 Ralph
engine = RalphEngine(config)
results = engine.run_all_tasks()

# 打印结果
for task_id, result in results.items():
    status = "✅" if result.success else "❌"
    print(f"{status} {task_id}: {result.message}")
```

运行：

```bash
cd ~/.kiro/skills/ralph-skill
poetry run python /path/to/simple-todo-app/run.py
```

### 步骤 3：运行应用

生成代码后，项目结构如下：

```
simple-todo-app/
├── frontend/           # Vue3 前端
│   ├── src/
│   ├── tests/
│   ├── package.json
│   └── vite.config.ts
├── backend/            # Go 后端
│   ├── main.go
│   ├── handlers/
│   ├── models/
│   ├── tests/
│   └── go.mod
├── ralph-config.yaml
└── README.md
```

启动后端：

```bash
cd backend
go run main.go
# 后端运行在 http://localhost:8080
```

启动前端（新终端）：

```bash
cd frontend
npm install
npm run dev
# 前端运行在 http://localhost:5173
```

### 步骤 4：测试应用

访问 http://localhost:5173，你应该看到：

- 一个输入框用于添加新 todo
- Todo 列表显示所有待办事项
- 每个 todo 有复选框（标记完成）和删除按钮

### 步骤 5：运行测试

后端测试：

```bash
cd backend
go test ./...
```

前端测试：

```bash
cd frontend
npm run test
```

## 预期结果

### 后端 API

```bash
# 获取所有 todos
curl http://localhost:8080/api/todos

# 创建 todo
curl -X POST http://localhost:8080/api/todos \
  -H "Content-Type: application/json" \
  -d '{"title":"学习 Ralph Skill"}'

# 更新 todo
curl -X PUT http://localhost:8080/api/todos/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"学习 Ralph Skill","completed":true}'

# 删除 todo
curl -X DELETE http://localhost:8080/api/todos/1
```

### 前端界面

简单的 Todo 应用界面，包含：

- 顶部输入框和"添加"按钮
- Todo 列表，每项显示：
  - 复选框（点击切换完成状态）
  - Todo 标题（已完成的会有删除线）
  - 删除按钮

## 自定义配置

你可以修改 `ralph-config.yaml` 来调整项目：

### 更改技术栈

```yaml
# 使用 React 替代 Vue3
frontend:
  framework: "react"
  test_runner: "jest"

# 使用 Python FastAPI 替代 Go
backend:
  language: "python"
  framework: "fastapi"
  test_runner: "pytest"
```

### 添加更多功能

在 `tasks` 中添加新任务：

```yaml
tasks:
  # ... 现有任务 ...
  
  # 新任务：添加筛选功能
  - id: "filter"
    name: "添加筛选功能"
    type: "feature"
    depends_on: ["frontend"]
    ai_engine: "qwen_code"
    config:
      description: |
        添加筛选功能：
        - 全部
        - 未完成
        - 已完成
```

### 使用不同的 AI 引擎

```yaml
ai_engines:
  # 添加 Claude
  claude:
    type: "claude"
    cli_path: "claude"
    model: "claude-3-5-sonnet-20241022"
    timeout: 60

tasks:
  - id: "frontend"
    ai_engine: "claude"  # 使用 Claude 生成前端代码
```

## 故障排查

### 问题 1：后端启动失败

```bash
# 检查端口是否被占用
lsof -i :8080

# 更改端口（修改 main.go）
# 或杀死占用端口的进程
kill -9 <PID>
```

### 问题 2：前端无法连接后端

检查 CORS 配置，确保后端允许前端域名：

```go
// backend/main.go
router.Use(cors.New(cors.Config{
    AllowOrigins: []string{"http://localhost:5173"},
    AllowMethods: []string{"GET", "POST", "PUT", "DELETE"},
}))
```

### 问题 3：Ralph 执行失败

1. 检查配置文件语法：
   ```bash
   # 验证 YAML 语法
   python -c "import yaml; yaml.safe_load(open('ralph-config.yaml'))"
   ```

2. 查看日志：
   ```bash
   tail -f ~/.kiro/skills/ralph-skill/logs/ralph.log
   ```

3. 增加重试次数：
   ```yaml
   tasks:
     - id: "task-id"
       max_retries: 5  # 增加到 5 次
   ```

## 下一步

完成这个简单示例后，你可以：

1. **添加数据库**：将内存存储改为 PostgreSQL
   ```yaml
   project:
     database:
       type: "postgresql"
       host: "localhost"
       port: 5432
       database: "todo_db"
   ```

2. **添加用户认证**：实现登录和注册功能

3. **添加 E2E 测试**：使用 Playwright 测试完整流程

4. **部署应用**：添加 Docker 配置和部署任务

5. **查看更多示例**：
   - [完整 Todo 应用](../full-todo-app/) - 包含数据库和认证
   - [博客系统](../blog-system/) - 更复杂的应用
   - [API 服务](../api-service/) - 纯后端服务

## 学习资源

- [Ralph Skill 使用指南](../../USAGE_GUIDE.md) - 详细的使用文档
- [配置文件参考](../../ralph-skill/config.example.yaml) - 完整的配置示例
- [SKILL.md](../../ralph-skill/SKILL.md) - Skill 功能说明

## 反馈

如果遇到问题或有建议，欢迎：
- 提交 Issue
- 参与讨论
- 贡献代码

---

**提示**：第一次使用可能需要几分钟时间，请耐心等待 AI 生成代码。
