"""
后端开发支持相关数据模型

包含 Go 和 Python 项目配置、测试结果、错误信息等数据结构。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any


# ============================================================================
# Go 项目相关模型
# ============================================================================

@dataclass
class GoProjectInfo:
    """Go 项目信息"""
    has_go_mod: bool
    has_go_sum: bool
    module_name: str
    go_version: str
    dependencies: List[str] = field(default_factory=list)
    test_files: List[str] = field(default_factory=list)
    has_makefile: bool = False


@dataclass
class GoTestResult:
    """Go 测试结果"""
    success: bool
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    execution_time: float
    coverage: Optional[float] = None
    failed_test_details: List['GoFailedTest'] = field(default_factory=list)
    output: str = ""


@dataclass
class GoFailedTest:
    """Go 失败测试详情"""
    test_name: str
    package: str
    file_path: str
    line_number: int
    error_message: str
    stack_trace: str


@dataclass
class GoBuildResult:
    """Go 构建结果"""
    success: bool
    output_binary: Optional[str]
    build_time: float
    errors: List['GoBuildError'] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class GoBuildError:
    """Go 构建错误"""
    file_path: str
    line_number: int
    column: int
    error_type: str
    error_message: str


# ============================================================================
# Python 项目相关模型
# ============================================================================

@dataclass
class PythonProjectInfo:
    """Python 项目信息"""
    framework: str  # django, flask, fastapi, none
    dependency_manager: str  # pip, poetry, pipenv
    python_version: str
    has_requirements: bool
    has_pyproject: bool
    has_pipfile: bool
    test_framework: str  # pytest, unittest
    virtual_env_path: Optional[str] = None


@dataclass
class PythonEnvironmentInfo:
    """Python 虚拟环境信息"""
    env_type: str  # venv, virtualenv, conda
    env_path: str
    python_version: str
    is_active: bool
    installed_packages: List[str] = field(default_factory=list)


@dataclass
class PytestConfig:
    """Pytest 配置"""
    test_dir: str = "tests"
    coverage: bool = True
    coverage_threshold: float = 80.0
    markers: List[str] = field(default_factory=list)
    plugins: List[str] = field(default_factory=list)
    parallel: bool = False
    num_workers: int = 4
    verbose: bool = True
    capture_output: str = "no"  # no, sys, fd
    timeout: int = 300


@dataclass
class PytestResult:
    """Pytest 测试结果"""
    success: bool
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    execution_time: float
    coverage: Optional['CoverageReport'] = None
    failed_test_details: List['FailedPytestCase'] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    output: str = ""


@dataclass
class FailedPytestCase:
    """Pytest 失败测试用例"""
    test_name: str
    test_file: str
    line_number: int
    error_type: str  # AssertionError, TypeError, etc.
    error_message: str
    stack_trace: str
    assertion_details: Optional['AssertionInfo'] = None


@dataclass
class AssertionInfo:
    """断言信息"""
    expected: str
    actual: str
    comparison_operator: str  # ==, !=, >, <, in, etc.


@dataclass
class CoverageReport:
    """覆盖率报告"""
    total_coverage: float
    line_coverage: float
    branch_coverage: float
    file_coverage: Dict[str, 'FileCoverage'] = field(default_factory=dict)
    missing_lines: Dict[str, List[int]] = field(default_factory=dict)


@dataclass
class FileCoverage:
    """文件覆盖率"""
    file_path: str
    coverage_percent: float
    lines_covered: int
    lines_total: int
    missing_lines: List[int] = field(default_factory=list)


# ============================================================================
# 代码格式化相关模型
# ============================================================================

@dataclass
class FormatResult:
    """代码格式化结果"""
    success: bool
    formatter: str  # black, isort, autopep8, ruff, gofmt
    files_formatted: List[str] = field(default_factory=list)
    changes_made: bool = False
    errors: List[str] = field(default_factory=list)
    execution_time: float = 0.0


@dataclass
class BlackConfig:
    """Black 格式化配置"""
    line_length: int = 88
    target_version: List[str] = field(default_factory=lambda: ["py39"])
    skip_string_normalization: bool = False
    fast: bool = False


@dataclass
class IsortConfig:
    """Isort 配置"""
    profile: str = "black"
    line_length: int = 88
    multi_line_output: int = 3
    include_trailing_comma: bool = True


@dataclass
class RuffConfig:
    """Ruff 配置"""
    line_length: int = 88
    select: List[str] = field(default_factory=lambda: ["E", "F", "W"])
    ignore: List[str] = field(default_factory=list)
    fix: bool = True


# ============================================================================
# 后端错误相关模型
# ============================================================================

@dataclass
class BackendError:
    """后端错误基类"""
    error_type: str
    error_message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    column: Optional[int] = None
    severity: str = "error"  # error, warning, info
    suggestion: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class GoError(BackendError):
    """Go 错误"""
    package: Optional[str] = None
    function: Optional[str] = None


@dataclass
class PythonError(BackendError):
    """Python 错误"""
    exception_type: Optional[str] = None
    traceback: Optional[str] = None


@dataclass
class ErrorParseResult:
    """错误解析结果"""
    errors: List[BackendError] = field(default_factory=list)
    warnings: List[BackendError] = field(default_factory=list)
    total_count: int = 0
    critical_count: int = 0
    parse_time: float = 0.0


# ============================================================================
# Make 构建相关模型
# ============================================================================

@dataclass
class MakeTarget:
    """Make 目标"""
    name: str
    description: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)


@dataclass
class MakeResult:
    """Make 执行结果"""
    success: bool
    target: str
    execution_time: float
    output: str
    errors: List[str] = field(default_factory=list)


# ============================================================================
# 依赖管理相关模型
# ============================================================================

@dataclass
class DependencyInfo:
    """依赖信息"""
    name: str
    version: str
    is_dev: bool = False
    is_optional: bool = False


@dataclass
class RequirementsInfo:
    """Requirements 信息"""
    file_path: str
    dependencies: List[DependencyInfo] = field(default_factory=list)
    has_version_pins: bool = False


@dataclass
class PyprojectInfo:
    """Pyproject.toml 信息"""
    file_path: str
    project_name: str
    version: str
    dependencies: List[DependencyInfo] = field(default_factory=list)
    dev_dependencies: List[DependencyInfo] = field(default_factory=list)
    build_system: str = "poetry"  # poetry, setuptools, flit


@dataclass
class PipfileInfo:
    """Pipfile 信息"""
    file_path: str
    dependencies: List[DependencyInfo] = field(default_factory=list)
    dev_dependencies: List[DependencyInfo] = field(default_factory=list)
    python_version: str = "3.9"
