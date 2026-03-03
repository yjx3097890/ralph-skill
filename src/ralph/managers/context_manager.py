"""
上下文管理器

提供日志截断和上下文大小控制功能,防止上下文爆炸。
同时提供错误信息识别和提取功能,支持多种编程语言的错误格式。

## 功能特性

- **智能截断**: 保留前后关键信息,截断中间部分
- **截断标记**: 清晰标记截断位置和统计信息
- **统计功能**: 提供截断前后的详细统计
- **可配置**: 支持自定义截断策略和大小限制
- **多语言支持**: 正确处理多字节字符编码
- **错误提取**: 从长日志中识别和提取关键错误信息
- **多语言错误格式**: 支持 Python、Go、JavaScript/TypeScript 等语言的错误格式
- **优先级排序**: 根据错误严重程度进行优先级排序

## 使用示例

```python
from ralph.managers.context_manager import ContextManager

# 创建上下文管理器
manager = ContextManager(
    max_size=10000,
    head_size=2000,
    tail_size=2000
)

# 截断长输出
long_output = "..." * 10000
truncated = manager.truncate_output(long_output)

# 提取错误信息
errors = manager.extract_errors(long_output)
for error in errors:
    print(f"{error.priority}: {error.message}")

# 获取优先级最高的错误
priority_errors = manager.get_priority_errors(long_output, max_count=5)
```

## 验证需求

- **需求 2.1**: 实现日志截断机制,防止上下文爆炸
- **需求 2.2**: 实现错误信息识别和提取
- **需求 2.3**: 保留前后关键信息,智能截断中间部分
- **需求 2.4**: 支持多种编程语言的错误格式识别
- **需求 2.5**: 提供错误优先级排序
"""

import re
from dataclasses import dataclass
from typing import List, Optional

from ralph.models.constants import (
    CONTEXT_TRUNCATE_HEAD_SIZE,
    CONTEXT_TRUNCATE_TAIL_SIZE,
    DEFAULT_MAX_CONTEXT_SIZE,
)
from ralph.models.enums import ErrorCategory, ErrorPriority
from ralph.models.execution import ErrorInfo


@dataclass
class TruncationStats:
    """截断统计信息"""
    
    original_length: int  # 原始长度(字符数)
    truncated_length: int  # 截断后长度(字符数)
    truncated_chars: int  # 截断的字符数
    truncated_lines: int  # 截断的行数
    was_truncated: bool  # 是否发生了截断
    head_size: int  # 保留的头部大小
    tail_size: int  # 保留的尾部大小


class ContextManager:
    """
    上下文管理器
    
    负责管理上下文大小,通过智能截断长输出来防止上下文爆炸。
    
    截断策略:
    - 保留开头部分(默认 2000 字符)
    - 保留结尾部分(默认 2000 字符)
    - 中间部分用截断标记替代
    - 截断标记包含统计信息(截断的行数和字符数)
    """
    
    def __init__(
        self,
        max_size: int = DEFAULT_MAX_CONTEXT_SIZE,
        head_size: int = CONTEXT_TRUNCATE_HEAD_SIZE,
        tail_size: int = CONTEXT_TRUNCATE_TAIL_SIZE
    ):
        """
        初始化上下文管理器
        
        Args:
            max_size: 最大上下文大小(字符数)
            head_size: 保留的头部字符数
            tail_size: 保留的尾部字符数
        """
        self.max_size = max_size
        self.head_size = head_size
        self.tail_size = tail_size
        
        # 截断统计
        self._last_stats: Optional[TruncationStats] = None
        
    def truncate_output(self, text: str) -> str:
        """
        截断文本输出
        
        如果文本长度超过最大限制,则保留前后部分,中间用截断标记替代。
        
        Args:
            text: 要截断的文本
            
        Returns:
            str: 截断后的文本
            
        验证需求 2.1: 实现日志截断机制
        验证需求 2.3: 保留前后关键信息,智能截断中间部分
        """
        if not text:
            self._last_stats = TruncationStats(
                original_length=0,
                truncated_length=0,
                truncated_chars=0,
                truncated_lines=0,
                was_truncated=False,
                head_size=0,
                tail_size=0
            )
            return text
            
        original_length = len(text)
        
        # 如果文本长度未超过限制,直接返回
        if original_length <= self.max_size:
            self._last_stats = TruncationStats(
                original_length=original_length,
                truncated_length=original_length,
                truncated_chars=0,
                truncated_lines=0,
                was_truncated=False,
                head_size=original_length,
                tail_size=0
            )
            return text
            
        # 计算实际的头部和尾部大小
        # 确保头部+尾部不超过最大大小
        available_size = self.max_size - 100  # 预留空间给截断标记
        actual_head_size = min(self.head_size, available_size // 2)
        actual_tail_size = min(self.tail_size, available_size - actual_head_size)
        
        # 提取头部和尾部
        head = text[:actual_head_size]
        tail = text[-actual_tail_size:] if actual_tail_size > 0 else ""
        
        # 计算截断的部分
        truncated_start = actual_head_size
        truncated_end = original_length - actual_tail_size
        truncated_text = text[truncated_start:truncated_end]
        truncated_chars = len(truncated_text)
        truncated_lines = truncated_text.count('\n')
        
        # 生成截断标记
        truncation_marker = self._create_truncation_marker(
            truncated_chars,
            truncated_lines
        )
        
        # 组合结果
        result = head + truncation_marker + tail
        
        # 更新统计信息
        self._last_stats = TruncationStats(
            original_length=original_length,
            truncated_length=len(result),
            truncated_chars=truncated_chars,
            truncated_lines=truncated_lines,
            was_truncated=True,
            head_size=actual_head_size,
            tail_size=actual_tail_size
        )
        
        return result
        
    def get_truncation_stats(self) -> Optional[TruncationStats]:
        """
        获取最近一次截断的统计信息
        
        Returns:
            Optional[TruncationStats]: 截断统计信息,如果没有执行过截断则返回 None
            
        验证需求 2.5: 提供截断统计信息
        """
        return self._last_stats
        
    def manage_context_size(self, context: str) -> str:
        """
        管理上下文大小
        
        这是 truncate_output 的别名方法,提供更语义化的接口。
        
        Args:
            context: 上下文文本
            
        Returns:
            str: 管理后的上下文文本
        """
        return self.truncate_output(context)
        
    def _create_truncation_marker(
        self,
        truncated_chars: int,
        truncated_lines: int
    ) -> str:
        """
        创建截断标记
        
        Args:
            truncated_chars: 截断的字符数
            truncated_lines: 截断的行数
            
        Returns:
            str: 截断标记文本
        """
        return (
            f"\n\n"
            f"{'=' * 70}\n"
            f"[截断] 中间部分已截断\n"
            f"  - 截断字符数: {truncated_chars:,}\n"
            f"  - 截断行数: {truncated_lines:,}\n"
            f"  - 提示: 完整输出过长,已保留开头和结尾的关键信息\n"
            f"{'=' * 70}\n"
            f"\n"
        )
        
    def reset_stats(self) -> None:
        """重置截断统计信息"""
        self._last_stats = None
        
    def update_config(
        self,
        max_size: Optional[int] = None,
        head_size: Optional[int] = None,
        tail_size: Optional[int] = None
    ) -> None:
        """
        更新配置
        
        Args:
            max_size: 新的最大上下文大小
            head_size: 新的头部保留大小
            tail_size: 新的尾部保留大小
        """
        if max_size is not None:
            self.max_size = max_size
        if head_size is not None:
            self.head_size = head_size
        if tail_size is not None:
            self.tail_size = tail_size
            
    def get_config(self) -> dict:
        """
        获取当前配置
        
        Returns:
            dict: 配置字典
        """
        return {
            "max_size": self.max_size,
            "head_size": self.head_size,
            "tail_size": self.tail_size
        }
    
    def extract_errors(self, text: str) -> List[ErrorInfo]:
        """
        从文本中提取所有错误信息
        
        识别常见的错误模式,包括:
        - Python: Traceback, Exception, Error
        - Go: panic, error, FAIL
        - JavaScript/TypeScript: Error, at
        - 通用: ERROR, FAIL, FATAL
        
        Args:
            text: 要分析的文本
            
        Returns:
            List[ErrorInfo]: 提取的错误信息列表
            
        验证需求 2.2: 实现错误信息识别和提取
        验证需求 2.4: 支持多种编程语言的错误格式识别
        """
        if not text:
            return []
        
        errors: List[ErrorInfo] = []
        
        # 提取 Python 错误
        errors.extend(self._extract_python_errors(text))
        
        # 提取 Go 错误
        errors.extend(self._extract_go_errors(text))
        
        # 提取 JavaScript/TypeScript 错误
        errors.extend(self._extract_js_errors(text))
        
        # 提取通用错误
        errors.extend(self._extract_generic_errors(text))
        
        # 去重(基于消息和文件位置)
        unique_errors = self._deduplicate_errors(errors)
        
        return unique_errors
    
    def get_priority_errors(
        self,
        text: str,
        max_count: int = 10
    ) -> List[ErrorInfo]:
        """
        获取优先级最高的错误
        
        提取所有错误后,按优先级排序并返回前 N 个。
        
        Args:
            text: 要分析的文本
            max_count: 返回的最大错误数量
            
        Returns:
            List[ErrorInfo]: 优先级最高的错误列表
            
        验证需求 2.5: 提供错误优先级排序
        """
        all_errors = self.extract_errors(text)
        
        # 按优先级排序(优先级高的在前)
        sorted_errors = sorted(
            all_errors,
            key=lambda e: e.get_priority_value(),
            reverse=True
        )
        
        return sorted_errors[:max_count]
    
    def _extract_python_errors(self, text: str) -> List[ErrorInfo]:
        """
        提取 Python 错误
        
        识别模式:
        - Traceback (most recent call last):
        - Exception: message
        - Error: message
        - File "path", line N
        """
        errors: List[ErrorInfo] = []
        
        # 匹配 Python Traceback (包括后面的异常行)
        # 匹配从 Traceback 开始,包括所有缩进行和紧跟的异常行
        traceback_pattern = r'Traceback \(most recent call last\):.*?(?:\n  .*?)*\n(\w+(?:Error|Exception|Warning)):\s*(.+?)(?=\n|$)'
        for match in re.finditer(traceback_pattern, text, re.DOTALL):
            traceback_text = match.group(0)
            error_type = match.group(1)
            message = match.group(2).strip()
            
            # 提取文件和行号
            file_pattern = r'File "([^"]+)", line (\d+)'
            file_matches = list(re.finditer(file_pattern, traceback_text))
            
            # 获取最后一个文件位置(通常是错误发生的位置)
            file_path = None
            line_number = None
            if file_matches:
                last_match = file_matches[-1]
                file_path = last_match.group(1)
                line_number = int(last_match.group(2))
            
            # 确定优先级
            priority = self._determine_priority(error_type, message)
            
            errors.append(ErrorInfo(
                type=ErrorCategory.RUNTIME_ERROR,
                message=f"{error_type}: {message}",
                priority=priority,
                file=file_path,
                line=line_number,
                stack_trace=traceback_text
            ))
        
        # 匹配独立的 Python 错误行(不在 Traceback 中的)
        # 只在没有找到 Traceback 时才提取独立错误行
        if not errors:
            error_line_pattern = r'(\w+(?:Error|Exception|Warning)):\s*(.+?)(?=\n|$)'
            for match in re.finditer(error_line_pattern, text):
                error_type = match.group(1)
                message = match.group(2).strip()
                
                priority = self._determine_priority(error_type, message)
                
                errors.append(ErrorInfo(
                    type=ErrorCategory.RUNTIME_ERROR,
                    message=f"{error_type}: {message}",
                    priority=priority
                ))
        
        return errors
    
    def _extract_go_errors(self, text: str) -> List[ErrorInfo]:
        """
        提取 Go 错误
        
        识别模式:
        - panic: message
        - FAIL: message
        - error: message
        - path/file.go:line:column: message
        """
        errors: List[ErrorInfo] = []
        
        # 匹配 Go panic
        panic_pattern = r'panic:\s*(.+?)(?=\n|$)'
        for match in re.finditer(panic_pattern, text):
            message = match.group(1).strip()
            
            errors.append(ErrorInfo(
                type=ErrorCategory.RUNTIME_ERROR,
                message=f"panic: {message}",
                priority=ErrorPriority.FATAL
            ))
        
        # 匹配 Go 测试失败
        fail_pattern = r'FAIL:\s*(.+?)(?=\n|$)'
        for match in re.finditer(fail_pattern, text):
            message = match.group(1).strip()
            
            errors.append(ErrorInfo(
                type=ErrorCategory.TEST_FAILURE,
                message=f"FAIL: {message}",
                priority=ErrorPriority.ERROR
            ))
        
        # 匹配 Go 编译错误 (file.go:line:column: message)
        compile_pattern = r'([^\s:]+\.go):(\d+):(\d+):\s*(.+?)(?=\n|$)'
        for match in re.finditer(compile_pattern, text):
            file_path = match.group(1)
            line_number = int(match.group(2))
            column = int(match.group(3))
            message = match.group(4).strip()
            
            priority = self._determine_priority("", message)
            
            errors.append(ErrorInfo(
                type=ErrorCategory.COMPILATION_ERROR,
                message=message,
                priority=priority,
                file=file_path,
                line=line_number,
                column=column
            ))
        
        return errors
    
    def _extract_js_errors(self, text: str) -> List[ErrorInfo]:
        """
        提取 JavaScript/TypeScript 错误
        
        识别模式:
        - Error: message
        - at function (file:line:column)
        - TypeError: message
        - ReferenceError: message
        """
        errors: List[ErrorInfo] = []
        
        # 匹配 JS 错误
        error_pattern = r'(\w+Error):\s*(.+?)(?=\n|$)'
        for match in re.finditer(error_pattern, text):
            error_type = match.group(1)
            message = match.group(2).strip()
            
            # 查找相关的堆栈跟踪(在错误行之后的几行内)
            # 匹配 "at ... (file:line:column)" 格式
            stack_pattern = r'at\s+.+?\s+\(([^:)]+):(\d+):(\d+)\)'
            # 从错误位置开始向后查找最多 500 个字符
            search_text = text[match.start():match.end()+500]
            stack_match = re.search(stack_pattern, search_text)
            
            file_path = None
            line_number = None
            column = None
            if stack_match:
                file_path = stack_match.group(1)
                line_number = int(stack_match.group(2))
                column = int(stack_match.group(3))
            
            priority = self._determine_priority(error_type, message)
            
            errors.append(ErrorInfo(
                type=ErrorCategory.RUNTIME_ERROR,
                message=f"{error_type}: {message}",
                priority=priority,
                file=file_path,
                line=line_number,
                column=column
            ))
        
        return errors
    
    def _extract_generic_errors(self, text: str) -> List[ErrorInfo]:
        """
        提取通用错误
        
        识别模式:
        - ERROR: message
        - FATAL: message
        - FAILED: message
        - [ERROR] message
        """
        errors: List[ErrorInfo] = []
        
        # 匹配通用错误格式
        patterns = [
            (r'FATAL[:\s]+(.+?)(?=\n|$)', ErrorPriority.FATAL),
            (r'CRITICAL[:\s]+(.+?)(?=\n|$)', ErrorPriority.CRITICAL),
            (r'ERROR[:\s]+(.+?)(?=\n|$)', ErrorPriority.ERROR),
            (r'FAILED[:\s]+(.+?)(?=\n|$)', ErrorPriority.ERROR),
            (r'\[ERROR\]\s*(.+?)(?=\n|$)', ErrorPriority.ERROR),
            (r'\[FATAL\]\s*(.+?)(?=\n|$)', ErrorPriority.FATAL),
        ]
        
        for pattern, priority in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                message = match.group(1).strip()
                
                # 跳过太短的消息
                if len(message) < 5:
                    continue
                
                errors.append(ErrorInfo(
                    type=ErrorCategory.UNKNOWN_ERROR,
                    message=message,
                    priority=priority
                ))
        
        return errors
    
    def _determine_priority(self, error_type: str, message: str) -> ErrorPriority:
        """
        根据错误类型和消息确定优先级
        
        Args:
            error_type: 错误类型
            message: 错误消息
            
        Returns:
            ErrorPriority: 错误优先级
        """
        error_type_lower = error_type.lower()
        message_lower = message.lower()
        
        # FATAL 级别
        if any(keyword in error_type_lower or keyword in message_lower 
               for keyword in ['fatal', 'panic', 'segfault', 'abort']):
            return ErrorPriority.FATAL
        
        # CRITICAL 级别
        if any(keyword in error_type_lower or keyword in message_lower
               for keyword in ['critical']):
            return ErrorPriority.CRITICAL
        
        # WARNING 级别
        if any(keyword in error_type_lower or keyword in message_lower
               for keyword in ['warning', 'warn', 'deprecated']):
            return ErrorPriority.WARNING
        
        # INFO 级别
        if any(keyword in error_type_lower or keyword in message_lower
               for keyword in ['info', 'note', 'hint']):
            return ErrorPriority.INFO
        
        # 默认 ERROR 级别
        return ErrorPriority.ERROR
    
    def _deduplicate_errors(self, errors: List[ErrorInfo]) -> List[ErrorInfo]:
        """
        去除重复的错误
        
        基于消息和文件位置进行去重。
        
        Args:
            errors: 错误列表
            
        Returns:
            List[ErrorInfo]: 去重后的错误列表
        """
        seen = set()
        unique_errors = []
        
        for error in errors:
            # 创建唯一键
            key = (
                error.message,
                error.file,
                error.line,
                error.priority
            )
            
            if key not in seen:
                seen.add(key)
                unique_errors.append(error)
        
        return unique_errors
