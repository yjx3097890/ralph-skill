"""
开发支持模块

提供前端、后端、Python、Docker 等不同技术栈的开发支持功能。
"""

from ralph.support.frontend_support import FrontendSupport
from ralph.support.vite_manager import ViteManager
from ralph.support.go_support import (
    GoProjectDetector,
    GoTestRunner,
    MakeManager,
    GoErrorParser,
)
from ralph.support.python_support import (
    PythonProjectDetector,
    PythonEnvironmentManager,
    PytestManager,
)
from ralph.support.python_formatter import PythonFormatter
from ralph.support.backend_error_parser import (
    BackendErrorParser,
    GoErrorParser as GoErrorParserV2,
    PythonErrorParser,
)
from ralph.support.docker_detector import DockerDetector

__all__ = [
    "FrontendSupport",
    "ViteManager",
    "GoProjectDetector",
    "GoTestRunner",
    "MakeManager",
    "GoErrorParser",
    "PythonProjectDetector",
    "PythonEnvironmentManager",
    "PytestManager",
    "PythonFormatter",
    "BackendErrorParser",
    "GoErrorParserV2",
    "PythonErrorParser",
    "DockerDetector",
]
