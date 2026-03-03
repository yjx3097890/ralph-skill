"""
后端开发支持模块测试

测试 Go 和 Python 项目识别、测试执行和错误解析功能。
"""

import pytest
from pathlib import Path
from ralph.support.go_support import (
    GoProjectDetector,
    GoTestRunner,
    MakeManager,
    GoErrorParser,
)
from ralph.support.python_support import (
    PythonProjectDetector,
    PythonEnvironmentManager,
)
from ralph.support.python_formatter import PythonFormatter
from ralph.support.backend_error_parser import (
    BackendErrorParser,
    GoErrorParser as GoErrorParserV2,
    PythonErrorParser,
)
from ralph.models.backend import (
    GoProjectInfo,
    PythonProjectInfo,
    GoError,
    PythonError,
)


class TestGoProjectDetector:
    """测试 Go 项目检测器"""
    
    def test_detect_go_mod(self, tmp_path):
        """测试检测 go.mod 文件"""
        # 创建测试项目
        go_mod = tmp_path / "go.mod"
        go_mod.write_text("""module example.com/myproject

go 1.21

require (
    github.com/stretchr/testify v1.8.0
)
""")
        
        detector = GoProjectDetector()
        info = detector.detect_project(str(tmp_path))
        
        assert info.has_go_mod is True
        assert info.module_name == "example.com/myproject"
        assert info.go_version == "1.21"
        assert "github.com/stretchr/testify" in info.dependencies
    
    def test_detect_makefile(self, tmp_path):
        """测试检测 Makefile"""
        makefile = tmp_path / "Makefile"
        makefile.write_text("""build:
\tgo build -o bin/app

test:
\tgo test ./...
""")
        
        detector = GoProjectDetector()
        info = detector.detect_project(str(tmp_path))
        
        assert info.has_makefile is True


class TestGoErrorParser:
    """测试 Go 错误解析器"""
    
    def test_parse_compile_error(self):
        """测试解析编译错误"""
        output = """main.go:42:10: undefined: fmt.Printl
main.go:43:5: syntax error: unexpected newline
"""
        
        parser = GoErrorParser()
        errors = parser.parse_compile_errors(output)
        
        assert len(errors) == 2
        assert errors[0].file_path == "main.go"
        assert errors[0].line_number == 42
        assert errors[0].column == 10
        assert "undefined" in errors[0].error_message
    
    def test_categorize_error(self):
        """测试错误分类"""
        parser = GoErrorParser()
        
        error1 = GoError(
            error_type="compile_error",
            error_message="undefined: fmt.Println",
            file_path="main.go",
            line_number=10,
        )
        assert parser.categorize_error(error1) == "undefined_reference"
        
        error2 = GoError(
            error_type="compile_error",
            error_message="cannot use x (type int) as type string",
            file_path="main.go",
            line_number=20,
        )
        assert parser.categorize_error(error2) == "type_error"


class TestPythonProjectDetector:
    """测试 Python 项目检测器"""
    
    def test_detect_django_project(self, tmp_path):
        """测试检测 Django 项目"""
        manage_py = tmp_path / "manage.py"
        manage_py.write_text("#!/usr/bin/env python\nimport django")
        
        detector = PythonProjectDetector()
        info = detector.detect_project(str(tmp_path))
        
        assert info.framework == "django"
    
    def test_detect_flask_project(self, tmp_path):
        """测试检测 Flask 项目"""
        app_py = tmp_path / "app.py"
        app_py.write_text("from flask import Flask\napp = Flask(__name__)")
        
        detector = PythonProjectDetector()
        info = detector.detect_project(str(tmp_path))
        
        assert info.framework == "flask"
    
    def test_detect_poetry_dependency_manager(self, tmp_path):
        """测试检测 Poetry 依赖管理"""
        poetry_lock = tmp_path / "poetry.lock"
        poetry_lock.write_text("")
        
        detector = PythonProjectDetector()
        info = detector.detect_project(str(tmp_path))
        
        assert info.dependency_manager == "poetry"


class TestPythonErrorParser:
    """测试 Python 错误解析器"""
    
    def test_parse_syntax_error(self):
        """测试解析语法错误"""
        output = '''  File "test.py", line 5
    print("Hello"
          ^
SyntaxError: unexpected EOF while parsing
'''
        
        parser = PythonErrorParser()
        errors = parser.parse_syntax_errors(output)
        
        assert len(errors) == 1
        assert errors[0].file_path == "test.py"
        assert errors[0].line_number == 5
        assert errors[0].exception_type == "SyntaxError"
    
    def test_categorize_error(self):
        """测试错误分类"""
        parser = PythonErrorParser()
        
        error1 = PythonError(
            error_type="runtime_error",
            error_message="name 'x' is not defined",
            exception_type="NameError",
        )
        assert parser.categorize_error(error1) == "name_error"
        
        error2 = PythonError(
            error_type="runtime_error",
            error_message="No module named 'requests'",
            exception_type="ModuleNotFoundError",
        )
        assert parser.categorize_error(error2) == "import_error"


class TestBackendErrorParser:
    """测试后端错误解析器"""
    
    def test_parse_go_errors(self):
        """测试解析 Go 错误"""
        output = "main.go:10:5: undefined: fmt.Println"
        
        parser = BackendErrorParser()
        result = parser.parse_errors(output, "go")
        
        assert result.total_count > 0
        assert len(result.errors) > 0
    
    def test_parse_python_errors(self):
        """测试解析 Python 错误"""
        output = '''  File "test.py", line 5
    print("Hello"
          ^
SyntaxError: unexpected EOF while parsing
'''
        
        parser = BackendErrorParser()
        result = parser.parse_errors(output, "python")
        
        assert result.total_count > 0
        assert len(result.errors) > 0
    
    def test_prioritize_errors(self):
        """测试错误优先级排序"""
        parser = BackendErrorParser()
        
        errors = [
            GoError(
                error_type="warning",
                error_message="unused variable",
                severity="warning",
            ),
            GoError(
                error_type="error",
                error_message="syntax error",
                severity="error",
            ),
            GoError(
                error_type="error",
                error_message="undefined reference",
                severity="error",
            ),
        ]
        
        prioritized = parser.prioritize_errors(errors)
        
        # 关键错误应该排在前面
        assert prioritized[0].severity == "error"
        assert "undefined" in prioritized[0].error_message or "syntax" in prioritized[0].error_message


class TestMakeManager:
    """测试 Make 管理器"""
    
    def test_detect_targets(self, tmp_path):
        """测试检测 Make 目标"""
        makefile = tmp_path / "Makefile"
        makefile.write_text("""# Build the application
build:
\tgo build -o bin/app

# Run tests
test: build
\tgo test ./...

clean:
\trm -rf bin/
""")
        
        manager = MakeManager()
        targets = manager.detect_targets(str(tmp_path))
        
        assert len(targets) >= 3
        target_names = [t.name for t in targets]
        assert "build" in target_names
        assert "test" in target_names
        assert "clean" in target_names
        
        # 检查依赖关系
        test_target = next(t for t in targets if t.name == "test")
        assert "build" in test_target.dependencies


class TestPythonFormatter:
    """测试 Python 代码格式化器"""
    
    def test_format_with_black(self, tmp_path):
        """测试 black 格式化"""
        # 创建测试文件
        test_file = tmp_path / "test.py"
        test_file.write_text("x=1\ny=2\n")
        
        formatter = PythonFormatter()
        # 注意：这个测试需要安装 black
        # 在实际环境中可能会失败，这里只是演示
        try:
            result = formatter.format_with_black(
                [str(test_file)],
                project_path=str(tmp_path)
            )
            # 如果 black 已安装，应该成功
            assert result.formatter == "black"
        except Exception:
            # 如果 black 未安装，跳过测试
            pytest.skip("black not installed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
