# 端对端测试支持

## 概述

Ralph Skill 现在完全支持端对端（E2E）测试，可以自动检测和执行 Playwright 或 Cypress 测试。

## 功能特性

### 1. 自动检测 E2E 测试框架

Ralph 会根据配置文件中的 `e2e_runner` 字段自动检测项目使用的 E2E 测试框架：

```yaml
project:
  frontend:
    framework: vue3
    test_runner: vitest
    e2e_runner: playwright  # 支持 playwright 或 cypress
```

### 2. 智能测试命令生成

Ralph 会自动查找 `package.json` 中的 E2E 测试脚本：

- 优先使用 `test:e2e` 脚本
- 其次使用 `e2e` 脚本
- 如果没有配置脚本，使用默认命令：
  - Playwright: `npx playwright test`
  - Cypress: `npx cypress run`

### 3. 测试执行顺序

Ralph 按以下顺序执行测试：

1. **单元测试**：先执行单元测试
2. **E2E 测试**：单元测试通过后执行 E2E 测试

如果单元测试失败，会跳过 E2E 测试，避免浪费时间。

### 4. 详细的测试输出

测试结果会包含所有测试类型的输出：

```
==================================================
单元测试 测试结果
==================================================
[单元测试输出...]

==================================================
E2E测试 测试结果
==================================================
[E2E测试输出...]
```

## 配置示例

### 完整配置

```yaml
project:
  name: my-app
  type: fullstack
  frontend:
    framework: vue3
    test_runner: vitest
    e2e_runner: playwright
    build_tool: vite
    package_manager: npm
  backend:
    language: go
    framework: gin
    test_runner: testing

tasks:
  - id: task-tests
    name: 添加测试
    type: test
    description: |
      为实现的功能添加单元测试和端对端测试：
      - 单元测试覆盖率 > 80%
      - E2E 测试覆盖主要用户流程
    ai_engine: qwen_code
    max_retries: 3
    timeout: 1800
```

### package.json 配置

在前端项目的 `package.json` 中添加 E2E 测试脚本：

```json
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "test": "vitest",
    "test:e2e": "playwright test"
  },
  "devDependencies": {
    "@playwright/test": "^1.40.0",
    "vitest": "^1.0.0"
  }
}
```

## 使用方法

### 方式 1：通过配置文件

在 `ralph-config.yaml` 中配置 E2E 测试：

```yaml
project:
  frontend:
    e2e_runner: playwright

tasks:
  - id: task-tests
    name: 添加测试
    type: test
    description: 添加单元测试和 E2E 测试
```

Ralph 会自动：
1. 检测 E2E 测试框架
2. 生成测试代码
3. 执行单元测试和 E2E 测试

### 方式 2：通过 API

```python
from ralph import autonomous_develop

result = autonomous_develop(
    task_description="创建 Todo 应用",
    tech_stack={
        "frontend": {
            "framework": "vue3",
            "test_runner": "vitest",
            "e2e_runner": "playwright"  # 启用 E2E 测试
        },
        "backend": {
            "language": "go",
            "framework": "gin"
        }
    },
    requirements=[
        "支持添加、删除、完成待办事项",
        "包含单元测试和 E2E 测试"
    ],
    project_root="."
)
```

## 测试执行流程

```
1. 检查项目初始化状态
   ↓
2. 启动必要的服务（数据库、后端服务器等）
   ↓
3. 执行单元测试
   ├─ 通过 → 继续
   └─ 失败 → 返回错误，跳过 E2E 测试
   ↓
4. 执行 E2E 测试
   ├─ 通过 → 所有测试通过
   └─ 失败 → 返回错误
   ↓
5. 返回测试结果
```

## 支持的 E2E 框架

### Playwright

**配置**：
```yaml
frontend:
  e2e_runner: playwright
```

**默认命令**：`npx playwright test`

**推荐的 package.json 脚本**：
```json
{
  "scripts": {
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui",
    "test:e2e:debug": "playwright test --debug"
  }
}
```

### Cypress

**配置**：
```yaml
frontend:
  e2e_runner: cypress
```

**默认命令**：`npx cypress run`

**推荐的 package.json 脚本**：
```json
{
  "scripts": {
    "test:e2e": "cypress run",
    "test:e2e:open": "cypress open"
  }
}
```

## 最佳实践

### 1. 测试描述要明确

在任务描述中明确要求 E2E 测试：

```yaml
tasks:
  - id: task-tests
    name: 添加测试
    description: |
      添加完整的测试套件：
      
      单元测试：
      - 组件测试
      - API 测试
      - 工具函数测试
      - 覆盖率 > 80%
      
      E2E 测试：
      - 用户登录流程
      - 创建待办事项
      - 编辑待办事项
      - 删除待办事项
      - 标记完成/未完成
```

### 2. 合理设置超时时间

E2E 测试通常比单元测试慢，建议设置较长的超时时间：

```yaml
tasks:
  - id: task-tests
    timeout: 1800  # 30 分钟
```

### 3. 确保服务已启动

E2E 测试需要前后端服务都在运行。Ralph 会自动启动数据库服务，但你可能需要：

- 在测试前启动后端服务器
- 在测试前启动前端开发服务器
- 或者配置测试使用生产构建

### 4. 使用测试钩子

可以使用钩子在测试前后执行特定操作：

```yaml
tasks:
  - id: task-tests
    hooks:
      pre_test:
        - name: start_backend
          command: "cd backend && go run cmd/server/main.go &"
        - name: start_frontend
          command: "cd frontend && npm run dev &"
      post_test:
        - name: cleanup
          command: "pkill -f 'go run'"
```

## 故障排查

### 问题 1：E2E 测试未执行

**可能原因**：
- 配置文件中未设置 `e2e_runner`
- `package.json` 中没有 E2E 测试脚本
- E2E 测试框架未安装

**解决方案**：
1. 检查配置文件中的 `e2e_runner` 字段
2. 在 `package.json` 中添加 `test:e2e` 脚本
3. 安装 E2E 测试框架：`npm install -D @playwright/test`

### 问题 2：E2E 测试超时

**可能原因**：
- 服务器未启动
- 测试超时时间设置过短
- 网络问题

**解决方案**：
1. 确保后端服务器正在运行
2. 增加任务的 `timeout` 配置
3. 检查 Playwright/Cypress 配置中的超时设置

### 问题 3：E2E 测试失败但单元测试通过

**可能原因**：
- 前后端集成问题
- API 端点不匹配
- 环境变量未设置

**解决方案**：
1. 检查前端 API 调用的 URL
2. 确保后端服务器在正确的端口运行
3. 检查环境变量配置

## 示例项目

### Vue3 + Go + Playwright

```yaml
project:
  name: todo-app
  type: fullstack
  frontend:
    framework: vue3
    test_runner: vitest
    e2e_runner: playwright
    build_tool: vite
    package_manager: npm
  backend:
    language: go
    framework: gin
    test_runner: testing

tasks:
  - id: task-init
    name: 初始化项目
    type: feature
    description: 创建项目结构
    
  - id: task-backend
    name: 实现后端
    type: feature
    depends_on: [task-init]
    description: 实现 RESTful API
    
  - id: task-frontend
    name: 实现前端
    type: feature
    depends_on: [task-backend]
    description: 实现用户界面
    
  - id: task-tests
    name: 添加测试
    type: test
    depends_on: [task-frontend]
    description: |
      添加完整的测试套件：
      - 后端单元测试（Go testing）
      - 前端单元测试（Vitest）
      - E2E 测试（Playwright）
      - 覆盖率 > 80%
    timeout: 1800
```

## 更新日志

### v1.1.0 (2024-03-06)
- ✨ 新增：完整的 E2E 测试支持
- ✨ 新增：自动检测 Playwright 和 Cypress
- ✨ 新增：智能测试命令生成
- ✨ 改进：测试执行顺序优化
- ✨ 改进：详细的测试输出格式

## 相关文档

- [任务管理器使用指南](./task_manager_usage.md)
- [Kiro Agent 集成指南](./kiro_agent_integration.md)
- [Agent 驱动执行模式](./agent_driven_execution.md)
