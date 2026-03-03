# Ralph Skill - 企业级自治编程引擎

Ralph Skill 是一个企业级的自治编程引擎，旨在将基础的 Ralph 自治循环脚本升级为多智能体协作引擎。

## 快速安装

### 使用 Kiro 安装

```bash
# 从 GitHub 安装
kiro skill install https://github.com/yjx3097890/ralph-skill/tree/main/ralph-skill

# 从本地路径安装
kiro skill install /path/to/ralph-skill-repo/ralph-skill
```

### 使用 OpenClaw 安装

```bash
# 从 GitHub 安装
openclaw skill install https://github.com/yjx3097890/ralph-skill/tree/main/ralph-skill
```

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

## 目录结构

```
ralph-skill-repo/           # 仓库根目录
├── .github/               # GitHub 配置
├── ralph-skill/           # Skill 主目录（安装时指向这里）
│   ├── SKILL.md          # Skill 元数据（必需）
│   ├── config.yaml       # 配置文件
│   ├── src/              # 源代码
│   │   └── ralph/
│   │       ├── core/     # 核心引擎
│   │       ├── models/   # 数据模型
│   │       ├── managers/ # 管理器
│   │       ├── adapters/ # AI 引擎适配器
│   │       ├── sandbox/  # 安全沙箱
│   │       ├── support/  # 开发支持
│   │       └── utils/    # 工具函数
│   ├── tests/            # 测试
│   ├── docs/             # 文档
│   ├── examples/         # 示例
│   ├── pyproject.toml    # Poetry 配置
│   └── README.md         # 详细说明
├── INSTALL_GUIDE.md      # 安装指南
└── README.md             # 本文件
```

## 为什么需要子目录？

Kiro/OpenClaw 的 Skill 管理系统设计为支持一个仓库包含多个 Skills，因此要求：

- 每个 Skill 必须在独立的子目录中
- 子目录中必须包含 `SKILL.md` 文件
- 安装 URL 必须指向包含 `SKILL.md` 的子目录

这样的设计允许：
- 一个仓库管理多个相关的 Skills
- 更清晰的项目组织结构
- 更灵活的版本管理

## 文档

详细文档请查看 [`ralph-skill/README.md`](ralph-skill/README.md)

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

## 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](ralph-skill/CONTRIBUTING.md)

## 许可证

MIT License
