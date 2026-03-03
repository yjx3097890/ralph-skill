"""
Python 项目开发支持模块

提供 Python 项目识别、虚拟环境管理和 pytest 测试执行功能。
"""

import os
import re
import subprocess
import json
from pathlib import Path
from typing import List, Optional, Dict
import logging

from ralph.models.backend import (
    PythonProjectInfo,
    PythonEnvironmentInfo,
    PytestConfig,
    PytestResult,
    FailedPytestCase,
    AssertionInfo,
    CoverageReport,
    FileCoverage,
)

logger = logging.getLogger(__name__)


class PythonProjectDetector:
    """Python 项目检测器"""
    
    def detect_project(self, project_path: str) -> PythonProjectInfo:
        """检测 Python 项目类型和配置"""
        project_dir = Path(project_path)
        
        framework = self._detect_framework(project_dir)
        dependency_manager = self._detect_dependency_manager(project_dir)
        python_version = self._detect_python_version(project_dir)
        
        has_requirements = (project_dir / "requirements.txt").exists()
        has_pyproject = (project_dir / "pyproject.toml").exists()
        has_pipfile = (project_dir / "Pipfile").exists()
        
        test_framework = self._detect_test_framework(project_dir)
        
        return PythonProjectInfo(
            framework=framework,
            dependency_manager=dependency_manager,
            python_version=python_version,
            has_requirements=has_requirements,
            has_pyproject=has_pyproject,
            has_pipfile=has_pipfile,
            test_framework=test_framework,
        )
    
    def _detect_framework(self, project_dir: Path) -> str:
        """检测 Python 框架"""
        if (project_dir / "manage.py").exists():
            return "django"
        
        for file in ["app.py", "main.py", "__init__.py"]:
            file_path = project_dir / file
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding='utf-8')
                    if 'from flask import' in content or 'import flask' in content:
                        return "flask"
                    if 'from fastapi import' in content or 'import fastapi' in content:
                        return "fastapi"
                except Exception:
                    pass
        
        return "none"
    
    def _detect_dependency_manager(self, project_dir: Path) -> str:
        """检测依赖管理工具"""
        if (project_dir / "poetry.lock").exists():
            return "poetry"
        elif (project_dir / "Pipfile.lock").exists():
            return "pipenv"
        elif (project_dir / "requirements.txt").exists():
            return "pip"
        return "pip"
    
    def _detect_python_version(self, project_dir: Path) -> str:
        """检测 Python 版本"""
        python_version_file = project_dir / ".python-version"
        if python_version_file.exists():
            try:
                return python_version_file.read_text().strip()
            except Exception:
                pass
        
        import sys
        return f"{sys.version_info.major}.{sys.version_info.minor}"
    
    def _detect_test_framework(self, project_dir: Path) -> str:
        """检测测试框架"""
        if (project_dir / "pytest.ini").exists():
            return "pytest"
        
        for root, _, files in os.walk(project_dir):
            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    return "pytest"
        
        return "unittest"


class PythonEnvironmentManager:
    """Python 虚拟环境管理器"""
    
    def create_venv(self, env_path: str, python_version: Optional[str] = None) -> PythonEnvironmentInfo:
        """创建 venv 虚拟环境"""
        try:
            cmd = ["python3", "-m", "venv", env_path]
            if python_version:
                cmd[0] = f"python{python_version}"
            
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            return PythonEnvironmentInfo(
                env_type="venv",
                env_path=env_path,
                python_version=python_version or "3.9",
                is_active=False,
            )
        except Exception as e:
            logger.error(f"创建 venv 失败: {e}")
            raise
    
    def activate_env(self, env_path: str) -> Dict[str, str]:
        """获取激活虚拟环境的环境变量"""
        env_path = Path(env_path)
        
        if os.name == 'nt':
            python_exe = env_path / "Scripts" / "python.exe"
        else:
            python_exe = env_path / "bin" / "python"
        
        if not python_exe.exists():
            raise FileNotFoundError(f"虚拟环境不存在: {env_path}")
        
        env = os.environ.copy()
        env["VIRTUAL_ENV"] = str(env_path)
        env["PATH"] = f"{env_path / 'bin'}:{env.get('PATH', '')}"
        
        return env


class PytestManager:
    """Pytest 测试管理器"""
    
    def run_tests(
        self,
        project_path: str,
        config: PytestConfig,
        env_path: Optional[str] = None,
    ) -> PytestResult:
        """运行 pytest 测试"""
        import time
        start_time = time.time()
        
        if env_path:
            pytest_exe = Path(env_path) / ("Scripts/pytest.exe" if os.name == 'nt' else "bin/pytest")
            cmd = [str(pytest_exe)]
        else:
            cmd = ["pytest"]
        
        if config.verbose:
            cmd.append("-v")
        
        if config.coverage:
            cmd.extend(["--cov", "--cov-report=json"])
        
        cmd.append(config.test_dir)
        
        try:
            env = os.environ.copy()
            if env_path:
                env_manager = PythonEnvironmentManager()
                env = env_manager.activate_env(env_path)
            
            result = subprocess.run(
                cmd,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=config.timeout,
                env=env,
            )
            
            execution_time = time.time() - start_time
            
            return self._parse_test_output(
                result.stdout + result.stderr,
                result.returncode == 0,
                execution_time,
                config.coverage,
                project_path,
            )
        
        except subprocess.TimeoutExpired:
            return PytestResult(
                success=False,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                skipped_tests=0,
                execution_time=config.timeout,
                output="测试超时",
            )
        
        except Exception as e:
            logger.error(f"运行 pytest 失败: {e}")
            return PytestResult(
                success=False,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                skipped_tests=0,
                execution_time=time.time() - start_time,
                output=str(e),
            )
    
    def _parse_test_output(
        self,
        output: str,
        success: bool,
        execution_time: float,
        has_coverage: bool,
        project_path: str,
    ) -> PytestResult:
        """解析 pytest 输出"""
        stats_match = re.search(
            r'(\d+)\s+passed(?:,\s+(\d+)\s+failed)?(?:,\s+(\d+)\s+skipped)?',
            output
        )
        
        passed_tests = 0
        failed_tests = 0
        skipped_tests = 0
        
        if stats_match:
            passed_tests = int(stats_match.group(1))
            if stats_match.group(2):
                failed_tests = int(stats_match.group(2))
            if stats_match.group(3):
                skipped_tests = int(stats_match.group(3))
        
        total_tests = passed_tests + failed_tests + skipped_tests
        
        failed_details = self._extract_failed_tests(output)
        warnings = self._extract_warnings(output)
        
        coverage = None
        if has_coverage:
            coverage = self._parse_coverage(project_path)
        
        return PytestResult(
            success=success,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            skipped_tests=skipped_tests,
            execution_time=execution_time,
            coverage=coverage,
            failed_test_details=failed_details,
            warnings=warnings,
            output=output,
        )
    
    def _extract_failed_tests(self, output: str) -> List[FailedPytestCase]:
        """提取失败测试详情"""
        failed_tests = []
        
        for match in re.finditer(
            r'FAILED\s+([^:]+)::(\w+)',
            output
        ):
            test_file = match.group(1)
            test_name = match.group(2)
            
            failed_tests.append(FailedPytestCase(
                test_name=test_name,
                test_file=test_file,
                line_number=0,
                error_type="AssertionError",
                error_message="Test failed",
                stack_trace="",
            ))
        
        return failed_tests
    
    def _extract_warnings(self, output: str) -> List[str]:
        """提取警告信息"""
        warnings = []
        for match in re.finditer(r'WARNING:\s*(.+)', output):
            warnings.append(match.group(1).strip())
        return warnings
    
    def _parse_coverage(self, project_path: str) -> Optional[CoverageReport]:
        """解析覆盖率报告"""
        coverage_file = Path(project_path) / "coverage.json"
        
        if not coverage_file.exists():
            return None
        
        try:
            with open(coverage_file, 'r') as f:
                data = json.load(f)
            
            total_coverage = data.get('totals', {}).get('percent_covered', 0.0)
            
            return CoverageReport(
                total_coverage=total_coverage,
                line_coverage=total_coverage,
                branch_coverage=0.0,
            )
        
        except Exception as e:
            logger.warning(f"解析覆盖率报告失败: {e}")
            return None
