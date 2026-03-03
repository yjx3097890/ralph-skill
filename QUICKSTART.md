# Ralph Skill 快速开始

5 分钟上手 Ralph Skill，创建你的第一个自治开发项目。

## 一、前置准备（一次性）

```bash
# 1. 验证 Ralph Skill 已安装
ls ~/.kiro/skills/ralph-skill

# 2. 安装 Qwen Code CLI
curl -fsSL https://qwen-code-assets.oss-cn-hangzhou.aliyuncs.com/installation/install-qwen.sh | bash

# 3. 登录认证
qwen auth login

# 4. 验证安装
qwen --version
```

## 二、创建新项目（3 步）

### 步骤 1：创建项目目录

```bash
mkdir my-app
cd my-app
git init
```

### 步骤 2：创建配置文件

创建 `ralph-config.yaml`：

```yaml
# 项目配置
project:
  name: "my-app"
  type: "fullstack"
  
  frontend:
    framework: "vue3"
    test_runner: "vitest"
    build_tool: "vite"
    package_manager: "npm"
  
  backend:
    language: "go"
    framework: "gin"
    build_system: "go"
    test_runner: "testing"

# 任务列表
tasks:
  - id: "init"
    name: "初始化项目"
    type: "feature"
    ai_engine: "qwen_code"
    config:
      description: "创建基础项目结构"

# AI 引擎
ai_engines:
  qwen_code:
    type: "qwen_code"
    cli_path: "qwen"
    model: "qwen3-coder-plus"
    timeout: 60
```

### 步骤 3：运行 Ralph

**方式 A：在 Kiro 中（推荐）**

在 Kiro 聊天中输入：

```
使用 Ralph Skill 根据 ralph-config.yaml 执行任务
```

**方式 B：使用脚本**

```bash
# 复制运行脚本
cp ~/.kiro/skills/ralph-skill/examples/simple-todo-app/run_ralph.py .

# 运行
cd ~/.kiro/skills/ralph-skill
poetry run python /path/to/my-app/run_ralph.py
```

## 三、使用示例模板（更快）

直接使用预配置的示例：

```bash
# 复制示例
cp -r ~/.kiro/skills/ralph-skill/examples/simple-todo-app my-todo-app
cd my-todo-app

# 在 Kiro 中运行
# 或使用脚本运行
```

## 四、常用配置模板

### Vue3 + Go 全栈

```yaml
project:
  name: "my-app"
  type: "fullstack"
  frontend:
    framework: "vue3"
    test_runner: "vitest"
  backend:
    language: "go"
    framework: "gin"
```

### React + Python 全栈

```yaml
project:
  name: "my-app"
  type: "fullstack"
  frontend:
    framework: "react"
    test_runner: "jest"
  backend:
    language: "python"
    framework: "fastapi"
```

### 纯前端项目

```yaml
project:
  name: "my-app"
  type: "frontend"
  frontend:
    framework: "vue3"
    test_runner: "vitest"
```

### 纯后端 API

```yaml
project:
  name: "my-api"
  type: "backend"
  backend:
    language: "go"
    framework: "gin"
```

## 五、常用任务模板

### 实现功能

```yaml
tasks:
  - id: "feature-1"
    name: "实现用户登录"
    type: "feature"
    ai_engine: "qwen_code"
    config:
      description: |
        实现用户登录功能：
        - 邮箱和密码登录
        - JWT 认证
        - 包含单元测试
```

### 修复 Bug

```yaml
tasks:
  - id: "bugfix-1"
    name: "修复登录失败"
    type: "bugfix"
    ai_engine: "qwen_code"
    config:
      description: |
        修复 Bug：
        - 问题：用户无法登录
        - 错误：invalid credentials
        - 文件：backend/handlers/auth.go
```

### 重构代码

```yaml
tasks:
  - id: "refactor-1"
    name: "重构用户服务"
    type: "refactor"
    ai_engine: "qwen_code"
    config:
      description: |
        重构目标：
        - 提取公共逻辑
        - 优化数据库查询
        - 改善错误处理
```

### 添加测试

```yaml
tasks:
  - id: "test-1"
    name: "添加单元测试"
    type: "test"
    ai_engine: "qwen_code"
    config:
      description: |
        为以下模块添加测试：
        - backend/handlers/user.go
        - 目标覆盖率：> 80%
```

## 六、故障排查

### 问题：找不到配置文件

```bash
# 确保在项目目录中
pwd

# 检查文件是否存在
ls ralph-config.yaml
```

### 问题：AI 引擎连接失败

```bash
# 检查 Qwen 是否安装
qwen --version

# 重新登录
qwen auth login

# 检查配置
cat ~/.qwen/settings.json
```

### 问题：任务执行失败

```bash
# 查看日志
tail -f ~/.kiro/skills/ralph-skill/logs/ralph.log

# 增加重试次数
# 在配置文件中设置：
max_retries: 5
```

## 七、下一步

- 📖 阅读 [完整使用指南](USAGE_GUIDE.md)
- 🎯 查看 [示例项目](examples/simple-todo-app/)
- 📚 了解 [Skill 功能](ralph-skill/SKILL.md)
- 💡 学习 [最佳实践](USAGE_GUIDE.md#最佳实践)

## 八、获取帮助

- 查看日志：`~/.kiro/skills/ralph-skill/logs/ralph.log`
- 示例配置：`~/.kiro/skills/ralph-skill/config.yaml`
- 提交 Issue：GitHub Issues
- 社区讨论：GitHub Discussions

---

**提示**：首次使用建议从简单项目开始，熟悉流程后再处理复杂项目。

**时间估算**：
- 简单项目（1-2 个任务）：5-10 分钟
- 中等项目（3-5 个任务）：15-30 分钟
- 复杂项目（6+ 个任务）：30-60 分钟
