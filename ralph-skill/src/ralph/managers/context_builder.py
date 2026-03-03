"""
上下文构建器

构建代码上下文,包括代码片段、调用关系和文件树。
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Set

from .call_relationship_analyzer import CallRelationshipAnalyzer
from .code_index_manager import CodeIndexManager, SymbolInfo

logger = logging.getLogger(__name__)


class ContextBuilder:
    """
    上下文构建器
    
    功能:
    1. 提取代码片段
    2. 注入调用关系到 Prompt
    3. 生成文件树(排除无关目录)
    4. 格式化上下文
    """
    
    # 排除的目录(与 CodeIndexManager 保持一致)
    EXCLUDED_DIRS = {
        '.git', '.svn', '.hg',
        'node_modules', '__pycache__', '.pytest_cache',
        'venv', 'env', '.venv',
        'build', 'dist', 'target',
        '.mypy_cache', '.tox',
        'htmlcov', 'coverage',
    }
    
    def __init__(
        self,
        index_manager: CodeIndexManager,
        call_analyzer: Optional[CallRelationshipAnalyzer] = None
    ):
        """
        初始化上下文构建器
        
        Args:
            index_manager: 代码索引管理器
            call_analyzer: 调用关系分析器
        """
        self.index_manager = index_manager
        self.call_analyzer = call_analyzer
    
    def build_context_for_symbol(
        self,
        symbol: SymbolInfo,
        file_contents: Dict[str, str],
        include_callers: bool = True,
        include_callees: bool = True
    ) -> str:
        """
        为指定符号构建上下文
        
        Args:
            symbol: 符号信息
            file_contents: 文件路径到内容的映射
            include_callers: 是否包含调用方
            include_callees: 是否包含被调用方
        
        Returns:
            格式化的上下文字符串
        """
        context_parts = []
        
        # 1. 符号定义
        context_parts.append("## 目标符号")
        context_parts.append(self._format_symbol(symbol, file_contents))
        
        # 2. 调用方
        if include_callers and self.call_analyzer:
            callers = self.call_analyzer.get_callers(symbol.name)
            if callers:
                context_parts.append("\n## 调用方 (Callers)")
                for caller in callers[:5]:  # 限制数量
                    context_parts.append(self._format_symbol(caller, file_contents))
        
        # 3. 被调用方
        if include_callees and self.call_analyzer:
            callees = self.call_analyzer.get_callees(symbol)
            if callees:
                context_parts.append("\n## 被调用方 (Callees)")
                context_parts.append(f"调用了以下函数: {', '.join(callees[:10])}")
        
        return "\n\n".join(context_parts)
    
    def _format_symbol(
        self,
        symbol: SymbolInfo,
        file_contents: Dict[str, str]
    ) -> str:
        """
        格式化符号信息
        
        Args:
            symbol: 符号信息
            file_contents: 文件路径到内容的映射
        
        Returns:
            格式化的符号字符串
        """
        lines = [
            f"**{symbol.name}** ({symbol.symbol_type})",
            f"文件: `{symbol.file_path}:{symbol.line_number}`"
        ]
        
        if symbol.signature:
            lines.append(f"签名: `{symbol.signature}`")
        
        if symbol.docstring:
            lines.append(f"文档: {symbol.docstring[:200]}...")
        
        # 提取代码片段
        if symbol.file_path in file_contents:
            code_snippet = self._extract_code_snippet(
                file_contents[symbol.file_path],
                symbol.line_number,
                symbol.end_line_number
            )
            lines.append(f"\n```python\n{code_snippet}\n```")
        
        return "\n".join(lines)
    
    def _extract_code_snippet(
        self,
        content: str,
        start_line: int,
        end_line: Optional[int] = None,
        context_lines: int = 2
    ) -> str:
        """
        提取代码片段
        
        Args:
            content: 文件内容
            start_line: 起始行号(1-based)
            end_line: 结束行号(1-based)
            context_lines: 上下文行数
        
        Returns:
            代码片段
        """
        lines = content.split('\n')
        
        # 计算实际范围
        start_idx = max(0, start_line - 1 - context_lines)
        end_idx = (end_line if end_line else start_line) + context_lines
        end_idx = min(len(lines), end_idx)
        
        return '\n'.join(lines[start_idx:end_idx])
    
    def generate_file_tree(
        self,
        root_dir: Optional[str] = None,
        max_depth: int = 3
    ) -> str:
        """
        生成文件树结构
        
        Args:
            root_dir: 根目录(默认为项目根目录)
            max_depth: 最大深度
        
        Returns:
            文件树字符串
        """
        root = Path(root_dir) if root_dir else self.index_manager.project_root
        
        lines = [f"项目结构: {root.name}/"]
        self._build_tree_recursive(root, lines, "", max_depth, 0)
        
        return "\n".join(lines)
    
    def _build_tree_recursive(
        self,
        directory: Path,
        lines: List[str],
        prefix: str,
        max_depth: int,
        current_depth: int
    ) -> None:
        """
        递归构建文件树
        
        Args:
            directory: 当前目录
            lines: 输出行列表
            prefix: 前缀字符串
            max_depth: 最大深度
            current_depth: 当前深度
        """
        if current_depth >= max_depth:
            return
        
        try:
            items = sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name))
            
            for i, item in enumerate(items):
                # 跳过排除的目录
                if item.is_dir() and item.name in self.EXCLUDED_DIRS:
                    continue
                
                is_last = i == len(items) - 1
                current_prefix = "└── " if is_last else "├── "
                next_prefix = "    " if is_last else "│   "
                
                lines.append(f"{prefix}{current_prefix}{item.name}{'/' if item.is_dir() else ''}")
                
                if item.is_dir():
                    self._build_tree_recursive(
                        item,
                        lines,
                        prefix + next_prefix,
                        max_depth,
                        current_depth + 1
                    )
        
        except PermissionError:
            pass
    
    def build_full_context(
        self,
        target_file: str,
        target_symbol: Optional[str] = None,
        file_contents: Optional[Dict[str, str]] = None
    ) -> str:
        """
        构建完整上下文
        
        Args:
            target_file: 目标文件路径
            target_symbol: 目标符号名称
            file_contents: 文件内容映射
        
        Returns:
            完整上下文字符串
        """
        context_parts = []
        
        # 1. 文件树
        context_parts.append("# 项目结构")
        context_parts.append(self.generate_file_tree())
        
        # 2. 目标文件符号
        symbols = self.index_manager.get_file_symbols(target_file)
        if symbols:
            context_parts.append("\n# 文件符号")
            context_parts.append(f"文件 `{target_file}` 包含以下符号:")
            for symbol in symbols:
                context_parts.append(f"- {symbol.name} ({symbol.symbol_type})")
        
        # 3. 目标符号详情
        if target_symbol and file_contents:
            symbol_list = self.index_manager.find_symbol(target_symbol)
            target_symbols = [s for s in symbol_list if s.file_path == target_file]
            
            if target_symbols:
                context_parts.append("\n# 目标符号详情")
                context_parts.append(
                    self.build_context_for_symbol(
                        target_symbols[0],
                        file_contents
                    )
                )
        
        return "\n\n".join(context_parts)
