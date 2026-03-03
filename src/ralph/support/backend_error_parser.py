"""
后端错误解析器模块

提供统一的 Go 和 Python 错误解析接口。
"""

import re
from typing import List
import logging

from ralph.models.backend import (
    BackendError,
    GoError,
    PythonError,
    ErrorParseResult,
    GoTestResult,
    PytestResult,
)

logger = logging.getLogger(__name__)


class BackendErrorParser:
    """后端错误解析器基类"""
    
    def parse_errors(self, output: str, language: str) -> ErrorParseResult:
        """
        解析错误输出
        
        Args:
            output: 错误输出文本
            language: 编程语言 (go, python)
            
        Returns:
            ErrorParseResult: 解析结果
        """
        import time
        start_time = time.time()
        
        if language == "go":
            parser = GoErrorParser()
            errors = parser.parse_compile_errors(output)
        elif language == "python":
            parser = PythonErrorParser()
            errors = parser.parse_syntax_errors(output)
        else:
            errors = []
        
        # 分类错误和警告
        error_list = [e for e in errors if e.severity == "error"]
        warning_list = [e for e in errors if e.severity == "warning"]
        
        # 统计关键错误
        critical_count = sum(1 for e in error_list if self._is_critical(e))
        
        parse_time = time.time() - start_time
        
        return ErrorParseResult(
            errors=error_list,
            warnings=warning_list,
            total_count=len(errors),
            critical_count=critical_count,
            parse_time=parse_time,
        )
    
    def _is_critical(self, error: BackendError) -> bool:
        """判断是否为关键错误"""
        critical_keywords = [
            "syntax error",
            "undefined",
            "cannot find",
            "import error",
            "panic",
            "segmentation fault",
        ]
        
        message_lower = error.error_message.lower()
        return any(keyword in message_lower for keyword in critical_keywords)
    
    def prioritize_errors(self, errors: List[BackendError]) -> List[BackendError]:
        """对错误进行优先级排序"""
        def error_priority(error: BackendError) -> int:
            """计算错误优先级（数字越小优先级越高）"""
            if self._is_critical(error):
                return 0
            elif error.severity == "error":
                return 1
            elif error.severity == "warning":
                return 2
            else:
                return 3
        
        return sorted(errors, key=error_priority)


class GoErrorParser:
    """Go 错误解析器"""
    
    def parse_compile_errors(self, output: str) -> List[GoError]:
        """解析 Go 编译错误"""
        errors = []
        
        # 匹配编译错误: file.go:42:10: error message
        for match in re.finditer(
            r'([^:\s]+\.go):(\d+):(\d+):\s*(.+)',
            output
        ):
            file_path = match.group(1)
            line_number = int(match.group(2))
            column = int(match.group(3))
            error_message = match.group(4).strip()
            
            errors.append(GoError(
                error_type="compile_error",
                error_message=error_message,
                file_path=file_path,
                line_number=line_number,
                column=column,
            ))
        
        return errors
    
    def parse_test_errors(self, test_result: GoTestResult) -> List[GoError]:
        """解析 Go 测试错误"""
        errors = []
        
        for failed_test in test_result.failed_test_details:
            errors.append(GoError(
                error_type="test_failure",
                error_message=failed_test.error_message,
                file_path=failed_test.file_path,
                line_number=failed_test.line_number,
                package=failed_test.package,
                function=failed_test.test_name,
            ))
        
        return errors
    
    def categorize_error(self, error: GoError) -> str:
        """对 Go 错误进行分类"""
        message_lower = error.error_message.lower()
        
        if 'undefined' in message_lower:
            return "undefined_reference"
        elif 'cannot use' in message_lower or 'type' in message_lower:
            return "type_error"
        elif 'syntax' in message_lower:
            return "syntax_error"
        elif 'import' in message_lower:
            return "import_error"
        elif 'panic' in message_lower:
            return "runtime_panic"
        else:
            return "unknown"
    
    def suggest_fix(self, error: GoError) -> str:
        """为 Go 错误提供修复建议"""
        category = self.categorize_error(error)
        
        suggestions = {
            "undefined_reference": "检查变量或函数是否已定义，或是否需要导入相应的包",
            "type_error": "检查类型是否匹配，可能需要类型转换",
            "syntax_error": "检查语法错误，如缺少括号、分号等",
            "import_error": "检查导入路径是否正确，包是否已安装",
            "runtime_panic": "检查运行时错误，如空指针、数组越界等",
        }
        
        return suggestions.get(category, "请检查错误信息并修复相关问题")


class PythonErrorParser:
    """Python 错误解析器"""
    
    def parse_syntax_errors(self, output: str) -> List[PythonError]:
        """解析 Python 语法错误"""
        errors = []
        
        # 匹配语法错误: File "file.py", line 42
        for match in re.finditer(
            r'File\s+"([^"]+)",\s+line\s+(\d+).*?\n\s*(.+)\n\s*\^\s*\n(\w+):\s*(.+)',
            output,
            re.DOTALL
        ):
            file_path = match.group(1)
            line_number = int(match.group(2))
            code_line = match.group(3).strip()
            exception_type = match.group(4)
            error_message = match.group(5).strip()
            
            errors.append(PythonError(
                error_type="syntax_error",
                error_message=error_message,
                file_path=file_path,
                line_number=line_number,
                exception_type=exception_type,
            ))
        
        return errors
    
    def parse_runtime_errors(self, output: str) -> List[PythonError]:
        """解析 Python 运行时错误"""
        errors = []
        
        # 匹配 Traceback
        traceback_pattern = r'Traceback \(most recent call last\):(.*?)(\w+Error):\s*(.+?)(?=\n\n|\Z)'
        
        for match in re.finditer(traceback_pattern, output, re.DOTALL):
            traceback = match.group(1).strip()
            exception_type = match.group(2)
            error_message = match.group(3).strip()
            
            # 提取最后一个文件位置
            file_match = re.search(
                r'File\s+"([^"]+)",\s+line\s+(\d+)',
                traceback
            )
            
            file_path = file_match.group(1) if file_match else None
            line_number = int(file_match.group(2)) if file_match else None
            
            errors.append(PythonError(
                error_type="runtime_error",
                error_message=error_message,
                file_path=file_path,
                line_number=line_number,
                exception_type=exception_type,
                traceback=traceback,
            ))
        
        return errors
    
    def parse_pytest_errors(self, test_result: PytestResult) -> List[PythonError]:
        """解析 pytest 测试错误"""
        errors = []
        
        for failed_test in test_result.failed_test_details:
            errors.append(PythonError(
                error_type="test_failure",
                error_message=failed_test.error_message,
                file_path=failed_test.test_file,
                line_number=failed_test.line_number,
                exception_type=failed_test.error_type,
                traceback=failed_test.stack_trace,
            ))
        
        return errors
    
    def categorize_error(self, error: PythonError) -> str:
        """对 Python 错误进行分类"""
        if error.exception_type:
            exception_lower = error.exception_type.lower()
            
            if 'syntax' in exception_lower:
                return "syntax_error"
            elif 'import' in exception_lower or 'module' in exception_lower:
                return "import_error"
            elif 'name' in exception_lower:
                return "name_error"
            elif 'type' in exception_lower:
                return "type_error"
            elif 'attribute' in exception_lower:
                return "attribute_error"
            elif 'index' in exception_lower or 'key' in exception_lower:
                return "access_error"
            elif 'assertion' in exception_lower:
                return "assertion_error"
        
        return "unknown"
    
    def suggest_fix(self, error: PythonError) -> str:
        """为 Python 错误提供修复建议"""
        category = self.categorize_error(error)
        
        suggestions = {
            "syntax_error": "检查语法错误，如缺少冒号、括号不匹配等",
            "import_error": "检查模块是否已安装，导入路径是否正确",
            "name_error": "检查变量或函数是否已定义",
            "type_error": "检查类型是否匹配，可能需要类型转换",
            "attribute_error": "检查对象是否有该属性或方法",
            "access_error": "检查索引或键是否存在",
            "assertion_error": "检查断言条件是否正确",
        }
        
        return suggestions.get(category, "请检查错误信息并修复相关问题")
