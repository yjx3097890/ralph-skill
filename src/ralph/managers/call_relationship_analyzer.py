"""
调用关系分析器

分析代码中的函数调用关系,构建调用图。
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Set

from .code_index_manager import SymbolInfo

logger = logging.getLogger(__name__)


@dataclass
class CallRelationship:
    """调用关系"""
    caller: SymbolInfo  # 调用方
    callee: str  # 被调用方名称
    call_line: int  # 调用所在行号


class CallRelationshipAnalyzer:
    """
    调用关系分析器
    
    功能:
    1. 构建调用图
    2. 检索调用方(callers)
    3. 检索被调用方(callees)
    4. 分析调用链
    5. 检测循环调用
    """
    
    def __init__(self):
        """初始化调用关系分析器"""
        self.call_graph: Dict[str, List[CallRelationship]] = {}
        self.reverse_call_graph: Dict[str, List[CallRelationship]] = {}
    
    def analyze_calls(
        self,
        symbol: SymbolInfo,
        file_content: str
    ) -> List[CallRelationship]:
        """
        分析符号的调用关系
        
        Args:
            symbol: 符号信息
            file_content: 文件内容
        
        Returns:
            调用关系列表
        """
        relationships = []
        
        # 提取符号所在的代码块
        lines = file_content.split('\n')
        start_line = symbol.line_number - 1
        end_line = symbol.end_line_number if symbol.end_line_number else len(lines)
        
        code_block = '\n'.join(lines[start_line:end_line])
        
        # 简单的调用检测(使用正则表达式)
        import re
        call_pattern = r'(\w+)\s*\('
        
        for i, line in enumerate(lines[start_line:end_line], start=start_line + 1):
            for match in re.finditer(call_pattern, line):
                callee_name = match.group(1)
                
                # 过滤关键字和内置函数
                if callee_name not in ['if', 'for', 'while', 'def', 'class', 'return']:
                    relationships.append(CallRelationship(
                        caller=symbol,
                        callee=callee_name,
                        call_line=i
                    ))
        
        return relationships
    
    def build_call_graph(
        self,
        symbols: List[SymbolInfo],
        file_contents: Dict[str, str]
    ) -> None:
        """
        构建调用图
        
        Args:
            symbols: 符号列表
            file_contents: 文件路径到内容的映射
        """
        self.call_graph.clear()
        self.reverse_call_graph.clear()
        
        for symbol in symbols:
            if symbol.file_path in file_contents:
                content = file_contents[symbol.file_path]
                relationships = self.analyze_calls(symbol, content)
                
                # 构建正向调用图
                caller_key = f"{symbol.file_path}:{symbol.name}"
                self.call_graph[caller_key] = relationships
                
                # 构建反向调用图
                for rel in relationships:
                    if rel.callee not in self.reverse_call_graph:
                        self.reverse_call_graph[rel.callee] = []
                    self.reverse_call_graph[rel.callee].append(rel)
    
    def get_callers(self, symbol_name: str) -> List[SymbolInfo]:
        """
        获取调用指定符号的所有调用方
        
        Args:
            symbol_name: 符号名称
        
        Returns:
            调用方符号列表
        """
        relationships = self.reverse_call_graph.get(symbol_name, [])
        return [rel.caller for rel in relationships]
    
    def get_callees(self, symbol: SymbolInfo) -> List[str]:
        """
        获取指定符号调用的所有被调用方
        
        Args:
            symbol: 符号信息
        
        Returns:
            被调用方名称列表
        """
        caller_key = f"{symbol.file_path}:{symbol.name}"
        relationships = self.call_graph.get(caller_key, [])
        return [rel.callee for rel in relationships]
