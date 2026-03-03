"""测试项目结构和基础配置"""

from pathlib import Path


def test_project_structure() -> None:
    """测试项目目录结构是否正确"""
    # 检查源代码目录
    assert Path("src/ralph").exists()
    assert Path("src/ralph/__init__.py").exists()

    # 检查核心模块
    assert Path("src/ralph/core").exists()
    assert Path("src/ralph/models").exists()
    assert Path("src/ralph/managers").exists()
    assert Path("src/ralph/adapters").exists()
    assert Path("src/ralph/sandbox").exists()
    assert Path("src/ralph/support").exists()
    assert Path("src/ralph/utils").exists()

    # 检查测试目录
    assert Path("tests").exists()
    assert Path("tests/unit").exists()
    assert Path("tests/integration").exists()
    assert Path("tests/e2e").exists()


def test_configuration_files() -> None:
    """测试配置文件是否存在"""
    assert Path("pyproject.toml").exists()
    assert Path(".flake8").exists()
    assert Path(".gitignore").exists()
    assert Path("README.md").exists()


def test_package_import() -> None:
    """测试包是否可以正常导入"""
    import ralph

    assert hasattr(ralph, "__version__")
    assert ralph.__version__ == "0.1.0"
    assert hasattr(ralph, "__author__")
