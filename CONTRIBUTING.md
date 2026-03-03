# 贡献指南

感谢您对 Ralph Skill 项目的关注！本文档将帮助您了解如何为项目做出贡献。

## 开发环境设置

### 前置要求

- Python 3.9 或更高版本
- Poetry（Python 依赖管理工具）
- Git

### 安装步骤

1. 克隆仓库

```bash
git clone <repository-url>
cd ralph-skill
```

2. 安装依赖

```bash
poetry install
```

3. 激活虚拟环境

```bash
poetry shell
```

## 开发工作流

### 1. 创建分支

```bash
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/your-bug-fix
```

### 2. 编写代码

- 遵循项目代码规范
- 为新功能编写测试
- 添加必要的中文注释

### 3. 运行测试

```bash
# 运行所有测试
make test

# 运行特定测试
poetry run pytest tests/unit/test_specific.py

# 生成覆盖率报告
make coverage
```

### 4. 代码质量检查

```bash
# 格式化代码
make format

# 运行代码检查
make lint
```

### 5. 提交代码

```bash
git add .
git commit -m "功能: 添加新功能描述"
```

提交信息格式：
- `功能: 描述` - 新功能
- `修复: 描述` - Bug 修复
- `文档: 描述` - 文档更新
- `测试: 描述` - 测试相关
- `重构: 描述` - 代码重构
- `样式: 描述` - 代码格式调整

### 6. 推送并创建 Pull Request

```bash
git push origin feature/your-feature-name
```

然后在 GitHub 上创建 Pull Request。

## 代码规范

### Python 代码规范

- 遵循 PEP 8 代码风格
- 使用 Black 进行代码格式化（行长度 100）
- 使用 isort 进行导入排序
- 使用类型注解（Type Hints）
- 编写中文注释和文档字符串

### 命名规范

- 类名：使用 PascalCase（如 `TaskManager`）
- 函数名：使用 snake_case（如 `create_task`）
- 常量：使用 UPPER_SNAKE_CASE（如 `MAX_RETRIES`）
- 私有成员：使用单下划线前缀（如 `_internal_method`）

### 文档字符串

```python
def create_task(task_config: TaskConfig) -> Task:
    """
    创建新任务
    
    Args:
        task_config: 任务配置对象
        
    Returns:
        创建的任务对象
        
    Raises:
        ValueError: 当配置无效时
    """
    pass
```

## 测试规范

### 测试类型

- **单元测试**: 测试单个函数或类的功能
- **集成测试**: 测试多个组件的协作
- **端到端测试**: 测试完整的工作流

### 测试文件组织

```
tests/
├── unit/              # 单元测试
│   ├── test_models.py
│   └── test_managers.py
├── integration/       # 集成测试
│   └── test_workflow.py
└── e2e/              # 端到端测试
    └── test_full_flow.py
```

### 测试命名

```python
def test_create_task_with_valid_config() -> None:
    """测试使用有效配置创建任务"""
    pass

def test_create_task_with_invalid_config_raises_error() -> None:
    """测试使用无效配置创建任务时抛出错误"""
    pass
```

### 使用 Pytest 标记

```python
import pytest

@pytest.mark.unit
def test_unit_function() -> None:
    """单元测试"""
    pass

@pytest.mark.integration
def test_integration_workflow() -> None:
    """集成测试"""
    pass

@pytest.mark.slow
def test_slow_operation() -> None:
    """慢速测试"""
    pass
```

## 常用命令

```bash
# 安装依赖
make install

# 运行测试
make test

# 代码检查
make lint

# 格式化代码
make format

# 生成覆盖率报告
make coverage

# 清理临时文件
make clean
```

## 问题反馈

如果您发现 Bug 或有功能建议，请在 GitHub Issues 中提交。

提交 Issue 时请包含：
- 问题描述
- 复现步骤
- 预期行为
- 实际行为
- 环境信息（Python 版本、操作系统等）

## 代码审查

所有 Pull Request 都需要经过代码审查。审查重点：

- 代码质量和可读性
- 测试覆盖率
- 文档完整性
- 是否遵循项目规范

## 许可证

通过提交代码，您同意您的贡献将在 MIT 许可证下发布。
