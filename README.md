# Ralph Skill - 企业级自治编程引擎

Ralph Skill 是一个企业级的自治编程引擎，将用户需求自动转化为可执行的代码。

## 特点

- 🤖 **完全自治**：自动任务规划、代码生成、测试验证、失败重试
- 🔒 **安全可靠**：Git 版本控制、一键回滚、安全沙箱
- 🎯 **全栈支持**：Vue3/React 前端，Go/Python 后端
- 🔌 **多引擎**：支持 Qwen Code、Aider、Claude、GPT-4

## 快速安装

```bash
# 从 GitHub 安装
kiro skill install https://github.com/yjx3097890/ralph-skill/tree/main/ralph-skill

# 从本地路径安装
kiro skill install /path/to/ralph-skill-repo/ralph-skill
```

## 快速开始

在 Kiro 中直接描述需求：

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

## 目录结构

```
ralph-skill-repo/           # 仓库根目录
├── ralph-skill/           # Skill 主目录（安装时指向这里）
│   ├── SKILL.md          # Skill 元数据（必需）
│   ├── README.md         # 完整使用文档
│   ├── config.example.yaml  # 配置文件示例
│   ├── src/ralph/        # 源代码
│   ├── tests/            # 测试
│   ├── docs/             # 文档
│   └── examples/         # 示例项目
└── README.md             # 本文件
```

## 为什么需要子目录？

Kiro/OpenClaw 的 Skill 管理系统要求：
- 每个 Skill 必须在独立的子目录中
- 子目录中必须包含 `SKILL.md` 文件
- 安装 URL 必须指向包含 `SKILL.md` 的子目录

这样的设计允许一个仓库管理多个相关的 Skills。

## 文档

完整文档请查看：
- 📖 [使用文档](ralph-skill/README.md) - 快速开始、使用示例、配置说明
- 📋 [安装指南](INSTALL_GUIDE.md) - 详细安装步骤
- 🎯 [示例项目](ralph-skill/examples/) - 实际项目示例
- 📚 [技术文档](ralph-skill/docs/) - 架构和开发指南

## 开发

```bash
cd ralph-skill

# 安装依赖
poetry install

# 运行测试
poetry run pytest

# 代码格式化
poetry run black src tests
poetry run isort src tests

# 类型检查
poetry run mypy src
```

## 许可证

MIT License
