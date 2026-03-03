"""
模块分析器

分析模块结构、边界和依赖关系。
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


@dataclass
class ModuleInfo:
    """模块信息"""
    name: str
    path: str
    files: List[str] = field(default_factory=list)
    dependencies: Set[str] = field(default_factory=set)
    exports: Set[str] = field(default_factory=set)


class ModuleAnalyzer:
    """
    模块分析器
    
    功能:
    1. 识别模块边界
    2. 分析依赖关系
    3. 解析导入语句
    4. 构建模块依赖图
    """
    
    def __init__(self, project_root: str):
        """
        初始化模块分析器
        
        Args:
            project_root: 项目根目录
        """
        self.project_root = Path(project_root)
        self.modules: Dict[str, ModuleInfo] = {}
    
    def analyze_modules(self, file_indices: Dict[str, any]) -> Dict[str, ModuleInfo]:
        """
        分析项目模块
        
        Args:
            file_indices: 文件索引字典
        
        Returns:
            模块信息字典
        """
        self.modules.clear()
        
        # 识别模块(基于目录结构)
        for file_path in file_indices.keys():
            module_name = self._get_module_name(file_path)
            
            if module_name not in self.modules:
                self.modules[module_name] = ModuleInfo(
                    name=module_name,
                    path=str(Path(file_path).parent)
                )
            
            self.modules[module_name].files.append(file_path)
            
            # 分析依赖
            file_index = file_indices[file_path]
            for import_name in file_index.imports:
                dep_module = self._resolve_import_to_module(import_name)
                if dep_module and dep_module != module_name:
                    self.modules[module_name].dependencies.add(dep_module)
        
        return self.modules
    
    def _get_module_name(self, file_path: str) -> str:
        """
        从文件路径获取模块名
        
        Args:
            file_path: 文件路径
        
        Returns:
            模块名
        """
        parts = Path(file_path).parts
        if len(parts) > 1:
            return parts[0]
        return "root"
    
    def _resolve_import_to_module(self, import_name: str) -> str:
        """
        将导入名称解析为模块名
        
        Args:
            import_name: 导入名称
        
        Returns:
            模块名
        """
        # 简化实现:取第一部分作为模块名
        parts = import_name.split('.')
        return parts[0] if parts else import_name
