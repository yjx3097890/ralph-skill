# Ralph Skill 安装指南

## Kiro 安装方式

由于 Kiro 要求 SKILL.md 必须在子目录中，请使用以下 URL 安装：

```bash
# 方式 1: 使用 GitHub URL（推荐）
kiro skill install https://github.com/yjx3097890/ralph-skill/tree/main/ralph-skill

# 方式 2: 使用本地路径
kiro skill install /path/to/ralph-skill-repo/ralph-skill
```

## 目录结构说明

```
ralph-skill-repo/           # 仓库根目录
├── ralph-skill/           # Skill 子目录（Kiro 安装指向这里）
│   ├── SKILL.md          # Skill 元数据
│   ├── config.yaml       # 配置文件
│   ├── src/              # 源代码
│   └── ...
└── README.md             # 仓库说明
```

## 为什么需要子目录？

Kiro 的 Skill 管理系统设计为支持一个仓库包含多个 Skills，因此要求：
- 每个 Skill 必须在独立的子目录中
- 子目录中必须包含 SKILL.md 文件
- 安装 URL 必须指向包含 SKILL.md 的子目录

这样的设计允许：
- 一个仓库管理多个相关的 Skills
- 更清晰的项目组织结构
- 更灵活的版本管理
