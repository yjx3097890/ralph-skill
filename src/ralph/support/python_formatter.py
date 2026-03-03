"""
Python 代码格式化工具模块

提供 black、isort、autopep8、ruff 等格式化工具的集成。
"""

import subprocess
from pathlib import Path
from typing import List, Optional
import logging

from ralph.models.backend import (
    FormatResult,
    BlackConfig,
    IsortConfig,
    RuffConfig,
)

logger = logging.getLogger(__name__)


class PythonFormatter:
    """Python 代码格式化器"""
    
    def format_with_black(
        self,
        file_paths: List[str],
        config: Optional[BlackConfig] = None,
        project_path: Optional[str] = None,
    ) -> FormatResult:
        """使用 black 格式化代码"""
        import time
        start_time = time.time()
        
        if config is None:
            config = BlackConfig()
        
        cmd = ["black"]
        cmd.extend(["--line-length", str(config.line_length)])
        
        if config.skip_string_normalization:
            cmd.append("--skip-string-normalization")
        
        if config.fast:
            cmd.append("--fast")
        
        cmd.extend(file_paths)
        
        try:
            result = subprocess.run(
                cmd,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=60,
            )
            
            execution_time = time.time() - start_time
            
            # Black 返回码: 0=无变更, 1=有变更, 123=语法错误
            success = result.returncode in [0, 1]
            changes_made = result.returncode == 1
            
            errors = []
            if result.returncode == 123:
                errors = [result.stderr]
            
            return FormatResult(
                success=success,
                formatter="black",
                files_formatted=file_paths if success else [],
                changes_made=changes_made,
                errors=errors,
                execution_time=execution_time,
            )
        
        except Exception as e:
            logger.error(f"Black 格式化失败: {e}")
            return FormatResult(
                success=False,
                formatter="black",
                errors=[str(e)],
                execution_time=time.time() - start_time,
            )
    
    def format_with_isort(
        self,
        file_paths: List[str],
        config: Optional[IsortConfig] = None,
        project_path: Optional[str] = None,
    ) -> FormatResult:
        """使用 isort 排序导入"""
        import time
        start_time = time.time()
        
        if config is None:
            config = IsortConfig()
        
        cmd = ["isort"]
        cmd.extend(["--profile", config.profile])
        cmd.extend(["--line-length", str(config.line_length)])
        
        if config.include_trailing_comma:
            cmd.append("--trailing-comma")
        
        cmd.extend(file_paths)
        
        try:
            result = subprocess.run(
                cmd,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=60,
            )
            
            execution_time = time.time() - start_time
            
            success = result.returncode == 0
            
            return FormatResult(
                success=success,
                formatter="isort",
                files_formatted=file_paths if success else [],
                changes_made=True,  # isort 不区分是否有变更
                errors=[result.stderr] if not success else [],
                execution_time=execution_time,
            )
        
        except Exception as e:
            logger.error(f"Isort 格式化失败: {e}")
            return FormatResult(
                success=False,
                formatter="isort",
                errors=[str(e)],
                execution_time=time.time() - start_time,
            )
    
    def format_with_ruff(
        self,
        file_paths: List[str],
        config: Optional[RuffConfig] = None,
        project_path: Optional[str] = None,
    ) -> FormatResult:
        """使用 ruff 格式化和修复代码"""
        import time
        start_time = time.time()
        
        if config is None:
            config = RuffConfig()
        
        cmd = ["ruff", "check"]
        
        if config.fix:
            cmd.append("--fix")
        
        cmd.extend(["--line-length", str(config.line_length)])
        
        if config.select:
            cmd.extend(["--select", ",".join(config.select)])
        
        if config.ignore:
            cmd.extend(["--ignore", ",".join(config.ignore)])
        
        cmd.extend(file_paths)
        
        try:
            result = subprocess.run(
                cmd,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=60,
            )
            
            execution_time = time.time() - start_time
            
            # Ruff 返回码: 0=无问题, 1=有问题但已修复, 2=有问题未修复
            success = result.returncode in [0, 1]
            changes_made = result.returncode == 1
            
            errors = []
            if result.returncode == 2:
                errors = [result.stdout]
            
            return FormatResult(
                success=success,
                formatter="ruff",
                files_formatted=file_paths if success else [],
                changes_made=changes_made,
                errors=errors,
                execution_time=execution_time,
            )
        
        except Exception as e:
            logger.error(f"Ruff 格式化失败: {e}")
            return FormatResult(
                success=False,
                formatter="ruff",
                errors=[str(e)],
                execution_time=time.time() - start_time,
            )
    
    def format_with_autopep8(
        self,
        file_paths: List[str],
        project_path: Optional[str] = None,
    ) -> FormatResult:
        """使用 autopep8 格式化代码"""
        import time
        start_time = time.time()
        
        cmd = ["autopep8", "--in-place", "--aggressive", "--aggressive"]
        cmd.extend(file_paths)
        
        try:
            result = subprocess.run(
                cmd,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=60,
            )
            
            execution_time = time.time() - start_time
            
            success = result.returncode == 0
            
            return FormatResult(
                success=success,
                formatter="autopep8",
                files_formatted=file_paths if success else [],
                changes_made=True,
                errors=[result.stderr] if not success else [],
                execution_time=execution_time,
            )
        
        except Exception as e:
            logger.error(f"Autopep8 格式化失败: {e}")
            return FormatResult(
                success=False,
                formatter="autopep8",
                errors=[str(e)],
                execution_time=time.time() - start_time,
            )
