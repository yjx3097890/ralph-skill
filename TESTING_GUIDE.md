# Ralph Skill 测试指南

## 测试结果

✅ 所有测试通过 (5/5)

## 测试项目

1. **Skill 安装检查** - 验证所有必需文件存在
2. **模块导入测试** - 验证核心模块可以正常导入
3. **配置文件解析** - 验证配置文件可以正确解析
4. **AI 引擎创建** - 验证 AI 引擎适配器可以正常创建
5. **任务管理器测试** - 验证任务管理器可以正常工作

## 运行测试

```bash
# 在 Skill 目录中运行
cd ~/.kiro/skills/ralph-skill
poetry run python ~/CODE/Ralph\ Skill/test_ralph_skill.py
```

## 配置说明

当前配置使用 Qwen Code 引擎：

```yaml
ai_engines:
  qwen_code:
    type: "qwen_code"
    cli_path: "qwen"
    model: "qwen3-coder-plus"
    timeout: 60
```

## 使用前准备

1. **安装 Qwen Code CLI**（如果使用 Qwen Code 引擎）：
   ```bash
   # 快速安装
   curl -fsSL https://qwen-code-assets.oss-cn-hangzhou.aliyuncs.com/installation/install-qwen.sh | bash
   
   # 或使用 npm
   npm install -g @qwen-code/qwen-code@latest
   
   # 或使用 Homebrew
   brew install qwen-code
   ```

2. **配置认证**：
   - Qwen OAuth 认证（推荐）：运行 `qwen auth login`
   - API-KEY 认证：在 `~/.qwen/settings.json` 中配置

3. **验证安装**：
   ```bash
   qwen --version
   ```

## 下一步

现在 Skill 已经安装并测试通过，你可以：

1. 在 Kiro 中使用 Skill 进行自治开发
2. 根据需要修改 `config.yaml` 配置
3. 添加更多 AI 引擎（Aider、Claude、GPT-4）
4. 创建自定义任务和工作流

## 故障排查

如果遇到问题：

1. **模块导入失败**：确保在 Poetry 虚拟环境中运行
   ```bash
   cd ~/.kiro/skills/ralph-skill
   poetry install
   poetry run python your_script.py
   ```

2. **配置解析失败**：检查 `config.yaml` 语法和枚举值是否正确

3. **AI 引擎创建失败**：确保 CLI 工具已安装并配置认证

4. **清理缓存**：
   ```bash
   find ~/.kiro/skills/ralph-skill -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
   ```

## 支持的框架和工具

### 前端框架
- Vue3, React, Angular

### 后端框架
- Go: Gin, Echo
- Python: Django, Flask, FastAPI
- Node.js: Express

### 测试工具
- 前端: Vitest, Jest, Playwright, Cypress
- 后端: Go testing, Pytest

### 构建工具
- Vite, Webpack, Rollup, Make, Go build

## 更新日志

### 2024-03-04
- ✅ 修复枚举定义（添加 Gin、Echo、Express、Go build、testing、cypress）
- ✅ 修复配置解析器参数映射
- ✅ 所有测试通过
- ✅ Skill 安装成功
