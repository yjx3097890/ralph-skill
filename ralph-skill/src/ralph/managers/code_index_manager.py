"""
代码索引管理器

使用 AST 工具生成项目符号表,支持代码结构分析和调用关系检索。
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class SymbolInfo:
    """符号信息"""
    name: str
    symbol_type: str  # function, class, method, variable
    file_path: str
    line_number: int
    end_line_number: Optional[int] = None
    signature: Optional[str] = None  # 函数签名或类定义
    docstring: Optional[str] = None
    parent: Optional[str] = None  # 父类或父函数名称


@dataclass
class FileIndex:
    """文件索引"""
    file_path: str
    language: str
    symbols: List[SymbolInfo] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    last_indexed: Optional[datetime] = None
    file_hash: Optional[str] = None  # 文件内容哈希,用于增量更新


@dataclass
class IndexStats:
    """索引统计信息"""
    total_files: int = 0
    total_symbols: int = 0
    indexed_files: int = 0
    failed_files: int = 0
    index_time: float = 0.0


class CodeIndexManager:
    """
    代码索引管理器
    
    功能:
    1. 使用 AST 工具生成项目符号表
    2. 提取函数、类、方法的定义和位置
    3. 支持增量更新
    4. 智能过滤(只索引相关子目录)
    """
    
    # 支持的语言和文件扩展名
    SUPPORTED_LANGUAGES = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.go': 'go',
        '.java': 'java',
        '.cpp': 'cpp',
        '.c': 'c',
        '.rs': 'rust',
    }
    
    # 需要排除的目录
    EXCLUDED_DIRS = {
        '.git', '.svn', '.hg',
        'node_modules', '__pycache__', '.pytest_cache',
        'venv', 'env', '.venv',
        'build', 'dist', 'target',
        '.mypy_cache', '.tox',
        'htmlcov', 'coverage',
    }
    
    def __init__(self, project_root: str):
        """
        初始化代码索引管理器
        
        Args:
            project_root: 项目根目录路径
        """
        self.project_root = Path(project_root).resolve()
        self.file_indices: Dict[str, FileIndex] = {}
        self.symbol_map: Dict[str, List[SymbolInfo]] = {}  # 符号名 -> 符号信息列表
        self.stats = IndexStats()
    
    def index_project(
        self,
        include_dirs: Optional[List[str]] = None,
        exclude_dirs: Optional[List[str]] = None
    ) -> IndexStats:
        """
        索引整个项目
        
        Args:
            include_dirs: 包含的目录列表(相对于项目根目录)
            exclude_dirs: 额外排除的目录列表
        
        Returns:
            索引统计信息
        """
        start_time = datetime.now()
        
        # 合并排除目录
        excluded = self.EXCLUDED_DIRS.copy()
        if exclude_dirs:
            excluded.update(exclude_dirs)
        
        # 确定要索引的目录
        if include_dirs:
            search_dirs = [self.project_root / d for d in include_dirs]
        else:
            search_dirs = [self.project_root]
        
        # 收集所有代码文件
        code_files = []
        for search_dir in search_dirs:
            if not search_dir.exists():
                logger.warning(f"目录不存在: {search_dir}")
                continue
            
            for file_path in self._walk_directory(search_dir, excluded):
                if self._is_code_file(file_path):
                    code_files.append(file_path)
        
        self.stats.total_files = len(code_files)
        logger.info(f"找到 {len(code_files)} 个代码文件")
        
        # 索引每个文件
        for file_path in code_files:
            try:
                self._index_file(file_path)
                self.stats.indexed_files += 1
            except Exception as e:
                logger.error(f"索引文件失败 {file_path}: {e}")
                self.stats.failed_files += 1
        
        # 构建符号映射
        self._build_symbol_map()
        
        # 更新统计信息
        elapsed = (datetime.now() - start_time).total_seconds()
        self.stats.index_time = elapsed
        self.stats.total_symbols = len(self.symbol_map)
        
        logger.info(
            f"索引完成: {self.stats.indexed_files}/{self.stats.total_files} 个文件, "
            f"{self.stats.total_symbols} 个符号, 耗时 {elapsed:.2f} 秒"
        )
        
        return self.stats
    
    def _walk_directory(self, directory: Path, excluded: Set[str]) -> List[Path]:
        """
        遍历目录,排除指定目录
        
        Args:
            directory: 要遍历的目录
            excluded: 排除的目录名集合
        
        Returns:
            文件路径列表
        """
        files = []
        
        try:
            for item in directory.iterdir():
                # 跳过排除的目录
                if item.is_dir():
                    if item.name in excluded:
                        continue
                    files.extend(self._walk_directory(item, excluded))
                elif item.is_file():
                    files.append(item)
        except PermissionError:
            logger.warning(f"无权限访问目录: {directory}")
        
        return files
    
    def _is_code_file(self, file_path: Path) -> bool:
        """
        判断是否为代码文件
        
        Args:
            file_path: 文件路径
        
        Returns:
            True 如果是支持的代码文件
        """
        return file_path.suffix in self.SUPPORTED_LANGUAGES
    
    def _index_file(self, file_path: Path) -> FileIndex:
        """
        索引单个文件
        
        Args:
            file_path: 文件路径
        
        Returns:
            文件索引
        """
        language = self.SUPPORTED_LANGUAGES.get(file_path.suffix, 'unknown')
        relative_path = str(file_path.relative_to(self.project_root))
        
        # 读取文件内容
        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            # 尝试其他编码
            content = file_path.read_text(encoding='latin-1')
        
        # 计算文件哈希
        import hashlib
        file_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
        
        # 检查是否需要重新索引
        if relative_path in self.file_indices:
            existing = self.file_indices[relative_path]
            if existing.file_hash == file_hash:
                logger.debug(f"文件未变更,跳过索引: {relative_path}")
                return existing
        
        # 解析文件并提取符号
        symbols = self._parse_file(content, language, relative_path)
        imports = self._extract_imports(content, language)
        
        # 创建文件索引
        file_index = FileIndex(
            file_path=relative_path,
            language=language,
            symbols=symbols,
            imports=imports,
            last_indexed=datetime.now(),
            file_hash=file_hash
        )
        
        self.file_indices[relative_path] = file_index
        logger.debug(f"索引文件: {relative_path}, 找到 {len(symbols)} 个符号")
        
        return file_index
    
    def _parse_file(
        self,
        content: str,
        language: str,
        file_path: str
    ) -> List[SymbolInfo]:
        """
        解析文件内容并提取符号
        
        Args:
            content: 文件内容
            language: 编程语言
            file_path: 文件路径
        
        Returns:
            符号信息列表
        """
        if language == 'python':
            return self._parse_python(content, file_path)
        else:
            # 其他语言使用简单的正则表达式解析
            return self._parse_generic(content, language, file_path)
    
    def _parse_python(self, content: str, file_path: str) -> List[SymbolInfo]:
        """
        解析 Python 文件
        
        Args:
            content: 文件内容
            file_path: 文件路径
        
        Returns:
            符号信息列表
        """
        import ast
        
        symbols = []
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                # 函数定义
                if isinstance(node, ast.FunctionDef):
                    # 提取函数签名
                    args = [arg.arg for arg in node.args.args]
                    signature = f"def {node.name}({', '.join(args)})"
                    
                    # 提取文档字符串
                    docstring = ast.get_docstring(node)
                    
                    symbols.append(SymbolInfo(
                        name=node.name,
                        symbol_type='function',
                        file_path=file_path,
                        line_number=node.lineno,
                        end_line_number=node.end_lineno,
                        signature=signature,
                        docstring=docstring
                    ))
                
                # 类定义
                elif isinstance(node, ast.ClassDef):
                    # 提取基类
                    bases = [base.id if isinstance(base, ast.Name) else str(base) 
                            for base in node.bases]
                    signature = f"class {node.name}({', '.join(bases)})" if bases else f"class {node.name}"
                    
                    # 提取文档字符串
                    docstring = ast.get_docstring(node)
                    
                    symbols.append(SymbolInfo(
                        name=node.name,
                        symbol_type='class',
                        file_path=file_path,
                        line_number=node.lineno,
                        end_line_number=node.end_lineno,
                        signature=signature,
                        docstring=docstring
                    ))
                    
                    # 提取类方法
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            args = [arg.arg for arg in item.args.args]
                            method_signature = f"def {item.name}({', '.join(args)})"
                            method_docstring = ast.get_docstring(item)
                            
                            symbols.append(SymbolInfo(
                                name=item.name,
                                symbol_type='method',
                                file_path=file_path,
                                line_number=item.lineno,
                                end_line_number=item.end_lineno,
                                signature=method_signature,
                                docstring=method_docstring,
                                parent=node.name
                            ))
        
        except SyntaxError as e:
            logger.warning(f"Python 语法错误 {file_path}:{e.lineno}: {e.msg}")
        
        return symbols
    
    def _parse_generic(
        self,
        content: str,
        language: str,
        file_path: str
    ) -> List[SymbolInfo]:
        """
        使用正则表达式解析通用代码文件
        
        Args:
            content: 文件内容
            language: 编程语言
            file_path: 文件路径
        
        Returns:
            符号信息列表
        """
        import re
        
        symbols = []
        lines = content.split('\n')
        
        # 简单的函数和类匹配模式
        patterns = {
            'javascript': [
                (r'function\s+(\w+)\s*\(', 'function'),
                (r'class\s+(\w+)', 'class'),
                (r'const\s+(\w+)\s*=\s*\(.*?\)\s*=>', 'function'),
            ],
            'go': [
                (r'func\s+(\w+)\s*\(', 'function'),
                (r'type\s+(\w+)\s+struct', 'class'),
            ],
        }
        
        if language in patterns:
            for i, line in enumerate(lines, 1):
                for pattern, symbol_type in patterns[language]:
                    match = re.search(pattern, line)
                    if match:
                        symbols.append(SymbolInfo(
                            name=match.group(1),
                            symbol_type=symbol_type,
                            file_path=file_path,
                            line_number=i,
                            signature=line.strip()
                        ))
        
        return symbols
    
    def _extract_imports(self, content: str, language: str) -> List[str]:
        """
        提取导入语句
        
        Args:
            content: 文件内容
            language: 编程语言
        
        Returns:
            导入的模块列表
        """
        import re
        
        imports = []
        
        if language == 'python':
            # 匹配 import 和 from ... import 语句
            import_pattern = r'^\s*(?:from\s+([\w.]+)\s+)?import\s+([\w.,\s]+)'
            for match in re.finditer(import_pattern, content, re.MULTILINE):
                if match.group(1):
                    imports.append(match.group(1))
                imports.extend([m.strip() for m in match.group(2).split(',')])
        
        return imports
    
    def _build_symbol_map(self) -> None:
        """构建符号名到符号信息的映射"""
        self.symbol_map.clear()
        
        for file_index in self.file_indices.values():
            for symbol in file_index.symbols:
                if symbol.name not in self.symbol_map:
                    self.symbol_map[symbol.name] = []
                self.symbol_map[symbol.name].append(symbol)
    
    def find_symbol(self, name: str) -> List[SymbolInfo]:
        """
        查找符号
        
        Args:
            name: 符号名称
        
        Returns:
            符号信息列表
        """
        return self.symbol_map.get(name, [])
    
    def get_file_symbols(self, file_path: str) -> List[SymbolInfo]:
        """
        获取文件中的所有符号
        
        Args:
            file_path: 文件路径(相对于项目根目录)
        
        Returns:
            符号信息列表
        """
        file_index = self.file_indices.get(file_path)
        return file_index.symbols if file_index else []
    
    def get_statistics(self) -> Dict[str, any]:
        """
        获取索引统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "total_files": self.stats.total_files,
            "indexed_files": self.stats.indexed_files,
            "failed_files": self.stats.failed_files,
            "total_symbols": self.stats.total_symbols,
            "index_time": self.stats.index_time,
            "languages": self._get_language_stats()
        }
    
    def _get_language_stats(self) -> Dict[str, int]:
        """获取各语言的文件数量统计"""
        stats = {}
        for file_index in self.file_indices.values():
            lang = file_index.language
            stats[lang] = stats.get(lang, 0) + 1
        return stats
