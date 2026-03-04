---
name: ralph-skill
version: 1.0.0
author: Ralph Team
description: 企业级自治编程引擎，支持前后端全栈自动化开发
keywords: [autonomous, coding, fullstack, ai, automation, vue3, go, python]
category: development
license: MIT
---

# Ralph Skill - 企业级自治编程引擎

## 简介

Ralph Skill 是一个企业级的自治编程引擎，将基础的 Ralph 自治循环脚本升级为多智能体协作引擎。该系统封装为符合标准化 Function Calling Schema 的 Skill，供上层 Master Agent（如 OpenClaw、Kiro）调用，支持前端和后端的全栈自动化开发。

## 核心能力

### 1. 自治开发
根据需求描述自动生成代码，支持多种编程语言和框架。

**示例**：
```
实现用户认证模块，要求：
- 支持邮箱和密码登录
- 使用 JWT 认证
- 包含单元测试
- 技术栈：Go + Gin + GORM
```

### 2. 测试生成
自动生成单元测试、集成测试和端到端测试。

**示例**：
```
为用户服务层生成完整的测试套件，包括：
- 单元测试（覆盖率 > 80%）
- 集成测试
- Mock 数据
```

### 3. 代码重构
智能重构和优化代码，提升代码质量。

**示例**：
```
重构用户服务层，要求：
- 提取公共逻辑
- 优化数据库查询
- 改善错误处理
```

### 4. Bug 修复
自动诊断和修复代码问题。

**示例**：
```
修复登录失败的 bug：
- 用户输入正确密码但无法登录
- 错误信息：invalid credentials
```

### 5. 文档生成
生成 API 文档、代码注释和使用说明。

**示例**：
```
为用户 API 生成 OpenAPI 文档，包括：
- 所有端点说明
- 请求/响应示例
- 错误码说明
```

### 6. 前端开发
支持 Vue3/React 组件开发和测试。

**示例**：
```
实现登录表单组件（Vue3），要求：
- 表单验证
- 错误提示
- 响应式设计
- Vitest 单元测试
```

### 7. 后端开发
支持 Go/Python 服务开发和测试。

**示例**：
```
实现 RESTful API，要求：
- CRUD 操作
- 参数验证
- 错误处理
- 单元测试
```

## 技术栈支持

### 前端
- **框架**: Vue3, React, Angular
- **测试**: Vitest, Jest, Playwright, Cypress
- **构建**: Vite, Webpack
- **包管理**: npm, yarn, pnpm

### 后端
- **语言**: Go, Python, Node.js
- **框架**: Gin, Echo, FastAPI, Express
- **测试**: Go testing, Pytest, Jest
- **数据库**: PostgreSQL, MySQL, Redis

### DevOps
- **容器**: Docker, Docker Compose
- **版本控制**: Git
- **CI/CD**: GitHub Actions, GitLab CI

## 配置要求

### 必需配置

```yaml
# 项目基本信息
project:
  name: "项目名称"
  type: "fullstack"  # fullstack, frontend, backend

# AI 引擎配置（至少配置一个）
ai_engines:
  claude:
    type: "claude"
    api_key: "${CLAUDE_API_KEY}"
    model: "claude-3-5-sonnet-20241022"
```

### 可选配置

```yaml
# 前端配置
project:
  frontend:
    framework: "vue3"
    test_runner: "vitest"
    e2e_runner: "playwright"

# 后端配置
project:
  backend:
    language: "go"
    framework: "gin"
    test_runner: "testing"

# 系统设置
settings:
  max_context_size: 100000
  git_auto_commit: true
  enable_hooks: true
```

## 使用方法

### 在 Kiro 中使用

#### 1. 安装

```bash
# 用户级别
mkdir -p ~/.kiro/skills/
cd ~/.kiro/skills/
git clone https://github.com/your-org/ralph-skill.git
cd ralph-skill
poetry install
```

#### 2. 配置

```bash
cp config.example.yaml config.yaml
# 编辑 config.yaml 设置 API 密钥
```

#### 3. 使用

在 Kiro 聊天中直接描述需求：

```
使用 Ralph Skill 实现用户登录功能
```

或在 Spec 中引用：

```markdown
使用 #ralph-skill 进行自治开发
```

### 在 OpenClaw 中使用

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

## Function Calling Schema

Ralph Skill 提供以下函数接口：

### 1. autonomous_develop

自治开发功能。

**参数**：
- `task_description` (string, required): 任务描述
- `tech_stack` (object, optional): 技术栈配置
- `requirements` (array, optional): 具体需求列表
- `constraints` (array, optional): 约束条件

**返回**：
- `success` (boolean): 是否成功
- `files_changed` (array): 修改的文件列表
- `commit_hash` (string): Git 提交哈希
- `message` (string): 执行消息

### 2. generate_tests

生成测试代码。

**参数**：
- `target_files` (array, required): 目标文件列表
- `test_type` (string, optional): 测试类型 (unit, integration, e2e)
- `coverage_target` (number, optional): 覆盖率目标 (默认 80)

**返回**：
- `success` (boolean): 是否成功
- `test_files` (array): 生成的测试文件
- `coverage` (number): 测试覆盖率

### 3. refactor_code

重构代码。

**参数**：
- `target_files` (array, required): 目标文件列表
- `refactor_goals` (array, required): 重构目标
- `preserve_behavior` (boolean, optional): 是否保持行为不变 (默认 true)

**返回**：
- `success` (boolean): 是否成功
- `files_changed` (array): 修改的文件列表
- `improvements` (array): 改进说明

### 4. fix_bug

修复 Bug。

**参数**：
- `bug_description` (string, required): Bug 描述
- `error_message` (string, optional): 错误信息
- `affected_files` (array, optional): 受影响的文件

**返回**：
- `success` (boolean): 是否成功
- `fix_description` (string): 修复说明
- `files_changed` (array): 修改的文件列表

### 5. generate_docs

生成文档。

**参数**：
- `doc_type` (string, required): 文档类型 (api, readme, comments)
- `target_files` (array, optional): 目标文件列表
- `format` (string, optional): 文档格式 (markdown, openapi, jsdoc)

**返回**：
- `success` (boolean): 是否成功
- `doc_files` (array): 生成的文档文件

## 安全特性

### 1. Git 版本控制
所有代码修改都会自动提交到 Git，支持回滚。

```bash
# 查看修改历史
git log

# 回滚到上一个版本
git reset --hard HEAD~1
```

### 2. 安全沙箱
代码执行在隔离的沙箱环境中，防止恶意操作。

### 3. 上下文防爆
智能管理上下文大小，防止 token 超限。

### 4. 错误恢复
自动检测和恢复错误，支持重试机制。

## 最佳实践

### 1. 明确需求
提供清晰的需求描述，包括功能、技术栈、约束条件。

**好的示例**：
```
实现用户注册功能，要求：
- 支持邮箱注册
- 发送验证邮件
- 密码强度验证
- 技术栈：Go + Gin + GORM + Redis
- 包含单元测试和集成测试
```

**不好的示例**：
```
做一个注册功能
```

### 2. 分步执行
对于复杂任务，建议分解为多个小任务逐步完成。

```
任务 1: 实现用户模型和数据库迁移
任务 2: 实现注册 API
任务 3: 实现邮件发送服务
任务 4: 编写测试
```

### 3. 代码审查
Skill 生成的代码建议人工审查后再合并到主分支。

### 4. 测试验证
运行生成的测试确保功能正确性。

```bash
# 前端测试
npm run test

# 后端测试
go test ./...
```

### 5. 配置管理
使用环境变量管理敏感信息。

```bash
# .env 文件
CLAUDE_API_KEY=your-api-key
DATABASE_URL=postgresql://localhost/mydb
```

## 故障排查

### 问题 1: Skill 无法加载

**症状**: Kiro 无法识别 Ralph Skill

**解决方案**:
1. 检查 skill.md 文件是否存在
2. 检查目录结构是否正确
3. 重启 Kiro

### 问题 2: API 调用失败

**症状**: 错误信息显示 API 认证失败

**解决方案**:
1. 检查 API 密钥是否正确
2. 检查环境变量是否设置
3. 查看日志文件：`~/.kiro/skills/ralph-skill/logs/ralph.log`

### 问题 3: 代码生成质量不佳

**症状**: 生成的代码不符合预期

**解决方案**:
1. 提供更详细的需求描述
2. 指定明确的技术栈和约束
3. 尝试分步执行
4. 调整 AI 引擎的 temperature 参数

### 问题 4: 测试失败

**症状**: 生成的测试无法通过

**解决方案**:
1. 检查测试环境配置
2. 查看测试错误信息
3. 手动修复测试代码
4. 向 Skill 反馈错误信息

## 性能优化

### 1. 上下文管理
- 只包含相关文件
- 使用 `.gitignore` 排除无关文件
- 定期清理临时文件

### 2. 并行执行
- 独立任务可以并行执行
- 使用任务依赖管理执行顺序

### 3. 缓存利用
- 复用已生成的代码
- 缓存 AI 响应结果

## 更新日志

### v1.0.0 (2024-03-04)
- 初始版本发布
- 支持 Vue3/Go 全栈开发
- 集成 Claude/GPT-4/Qwen 引擎
- 实现安全沙箱和 Git 版本控制

## 支持与反馈

- **文档**: [README.md](./README.md)
- **问题反馈**: GitHub Issues
- **讨论**: GitHub Discussions

## 许可证

MIT License

---

**注意**: 使用本 Skill 前，请确保已阅读并理解配置要求和安全特性。
