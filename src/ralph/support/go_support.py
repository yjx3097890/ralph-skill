"""
Go 项目开发支持模块

提供 Go 项目识别、测试执行、构建管理和错误解析功能。
"""

import os
import re
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

from ralph.models.backend import (
    GoProjectInfo,
    GoTestResult,
    GoFailedTest,
    GoBuildResult,
    GoBuildError,
    MakeTarget,
    MakeResult,
    GoError,
)

logger = logging.getLogger(__name__)


class GoProjectDetector:
    """Go 项目检测器"""
    
    def detect_project(self, project_path: str) -> GoProjectInfo:
        """
        检测 Go 项目结构和配置
        
        Args:
            project_path: 项目根目录路径
            
        Returns:
            GoProjectInfo: Go 项目信息
        """
        project_dir = Path(project_path)
        
        # 检查 go.mod 和 go.sum
        go_mod_path = project_dir / "go.mod"
        go_sum_path = project_dir / "go.sum"
        
        has_go_mod = go_mod_path.exists()
        has_go_sum = go_sum_path.exists()
        
        # 解析 go.mod
        module_name = ""
        go_version = ""
        dependencies = []
        
        if has_go_mod:
            module_name, go_version, dependencies = self._parse_go_mod(go_mod_path)
        
        # 查找测试文件
        test_files = self._find_test_files(project_dir)
        
        # 检查 Makefile
        has_makefile = (project_dir / "Makefile").exists()
        
        return GoProjectInfo(
            has_go_mod=has_go_mod,
            has_go_sum=has_go_sum,
            module_name=module_name,
            go_version=go_version,
            dependencies=dependencies,
            test_files=test_files,
            has_makefile=has_makefile,
        )
    
    def _parse_go_mod(self, go_mod_path: Path) -> tuple[str, str, List[str]]:
        """解析 go.mod 文件"""
        module_name = ""
        go_version = ""
        dependencies = []
        
        try:
            with open(go_mod_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取模块名
            module_match = re.search(r'^module\s+(.+)$', content, re.MULTILINE)
            if module_match:
                module_name = module_match.group(1).strip()
            
            # 提取 Go 版本
            go_match = re.search(r'^go\s+(\d+\.\d+)', content, re.MULTILINE)
            if go_match:
                go_version = go_match.group(1)
            
            # 提取依赖
            require_block = re.search(
                r'require\s*\((.*?)\)', content, re.DOTALL
            )
            if require_block:
                for line in require_block.group(1).split('\n'):
                    line = line.strip()
                    if line and not line.startswith('//'):
                        # 提取依赖名称（忽略版本）
                        dep_match = re.match(r'([^\s]+)', line)
                        if dep_match:
                            dependencies.append(dep_match.group(1))
        
        except Exception as e:
            logger.warning(f"解析 go.mod 失败: {e}")
        
        return module_name, go_version, dependencies
    
    def _find_test_files(self, project_dir: Path) -> List[str]:
        """查找所有测试文件"""
        test_files = []
        
        for root, _, files in os.walk(project_dir):
            # 跳过 vendor 和隐藏目录
            if 'vendor' in root or '/.git' in root:
                continue
            
            for file in files:
                if file.endswith('_test.go'):
                    rel_path = os.path.relpath(
                        os.path.join(root, file),
                        project_dir
                    )
                    test_files.append(rel_path)
        
        return test_files


class GoTestRunner:
    """Go 测试执行器"""
    
    def run_tests(
        self,
        project_path: str,
        package: str = "./...",
        coverage: bool = True,
        verbose: bool = True,
        timeout: int = 300,
    ) -> GoTestResult:
        """
        运行 Go 测试
        
        Args:
            project_path: 项目根目录
            package: 要测试的包路径
            coverage: 是否生成覆盖率报告
            verbose: 是否显示详细输出
            timeout: 超时时间（秒）
            
        Returns:
            GoTestResult: 测试结果
        """
        import time
        start_time = time.time()
        
        # 构建测试命令
        cmd = ["go", "test"]
        
        if verbose:
            cmd.append("-v")
        
        if coverage:
            cmd.extend(["-coverprofile=coverage.out", "-covermode=atomic"])
        
        cmd.append(package)
        
        try:
            result = subprocess.run(
                cmd,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            
            execution_time = time.time() - start_time
            
            # 解析测试输出
            return self._parse_test_output(
                result.stdout + result.stderr,
                result.returncode == 0,
                execution_time,
                coverage,
                project_path,
            )
        
        except subprocess.TimeoutExpired:
            logger.error(f"Go 测试超时（{timeout}秒）")
            return GoTestResult(
                success=False,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                skipped_tests=0,
                execution_time=timeout,
                output="测试超时",
            )
        
        except Exception as e:
            logger.error(f"运行 Go 测试失败: {e}")
            return GoTestResult(
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
    ) -> GoTestResult:
        """解析 Go 测试输出"""
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        skipped_tests = 0
        failed_details = []
        
        # 解析测试结果
        for line in output.split('\n'):
            # 匹配测试结果行: --- PASS: TestName (0.00s)
            if line.startswith('--- PASS:'):
                passed_tests += 1
                total_tests += 1
            elif line.startswith('--- FAIL:'):
                failed_tests += 1
                total_tests += 1
                # 提取失败测试详情
                failed_details.append(self._extract_failed_test(line, output))
            elif line.startswith('--- SKIP:'):
                skipped_tests += 1
                total_tests += 1
        
        # 提取覆盖率
        coverage = None
        if has_coverage:
            coverage = self._extract_coverage(output)
        
        return GoTestResult(
            success=success,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            skipped_tests=skipped_tests,
            execution_time=execution_time,
            coverage=coverage,
            failed_test_details=failed_details,
            output=output,
        )
    
    def _extract_failed_test(self, fail_line: str, full_output: str) -> GoFailedTest:
        """提取失败测试详情"""
        # 解析测试名称: --- FAIL: TestName (0.00s)
        match = re.search(r'--- FAIL:\s+(\S+)', fail_line)
        test_name = match.group(1) if match else "Unknown"
        
        # 查找错误信息和堆栈跟踪
        error_message = ""
        stack_trace = ""
        file_path = ""
        line_number = 0
        package = ""
        
        # 在输出中查找相关错误信息
        lines = full_output.split('\n')
        in_error_section = False
        
        for i, line in enumerate(lines):
            if test_name in line and 'FAIL' in line:
                in_error_section = True
                continue
            
            if in_error_section:
                # 查找文件路径和行号: file_test.go:42: error message
                location_match = re.search(r'(\S+\.go):(\d+):\s*(.+)', line)
                if location_match:
                    file_path = location_match.group(1)
                    line_number = int(location_match.group(2))
                    error_message = location_match.group(3)
                    stack_trace += line + '\n'
                elif line.strip().startswith('---'):
                    # 下一个测试开始
                    break
                elif line.strip():
                    stack_trace += line + '\n'
        
        return GoFailedTest(
            test_name=test_name,
            package=package,
            file_path=file_path,
            line_number=line_number,
            error_message=error_message.strip(),
            stack_trace=stack_trace.strip(),
        )
    
    def _extract_coverage(self, output: str) -> Optional[float]:
        """提取覆盖率百分比"""
        # 匹配覆盖率行: coverage: 85.7% of statements
        match = re.search(r'coverage:\s+([\d.]+)%', output)
        if match:
            return float(match.group(1))
        return None


class MakeManager:
    """Make 构建系统管理器"""
    
    def detect_targets(self, project_path: str) -> List[MakeTarget]:
        """
        检测 Makefile 中的目标
        
        Args:
            project_path: 项目根目录
            
        Returns:
            List[MakeTarget]: Make 目标列表
        """
        makefile_path = Path(project_path) / "Makefile"
        
        if not makefile_path.exists():
            return []
        
        targets = []
        
        try:
            with open(makefile_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 匹配目标定义: target: dependencies
            for match in re.finditer(r'^([a-zA-Z0-9_-]+):\s*([^\n]*)', content, re.MULTILINE):
                target_name = match.group(1)
                dependencies_str = match.group(2).strip()
                
                # 跳过特殊目标
                if target_name.startswith('.'):
                    continue
                
                dependencies = [d.strip() for d in dependencies_str.split() if d.strip()]
                
                # 查找目标描述（注释）
                description = self._find_target_description(content, target_name)
                
                targets.append(MakeTarget(
                    name=target_name,
                    description=description,
                    dependencies=dependencies,
                ))
        
        except Exception as e:
            logger.warning(f"解析 Makefile 失败: {e}")
        
        return targets
    
    def _find_target_description(self, content: str, target_name: str) -> Optional[str]:
        """查找目标的描述注释"""
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            if line.startswith(f"{target_name}:"):
                # 查找前面的注释
                if i > 0:
                    prev_line = lines[i - 1].strip()
                    if prev_line.startswith('#'):
                        return prev_line.lstrip('#').strip()
                break
        
        return None
    
    def run_target(
        self,
        project_path: str,
        target: str,
        timeout: int = 600,
    ) -> MakeResult:
        """
        执行 Make 目标
        
        Args:
            project_path: 项目根目录
            target: 目标名称
            timeout: 超时时间（秒）
            
        Returns:
            MakeResult: 执行结果
        """
        import time
        start_time = time.time()
        
        try:
            result = subprocess.run(
                ["make", target],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            
            execution_time = time.time() - start_time
            
            errors = []
            if result.returncode != 0:
                errors = self._extract_make_errors(result.stderr)
            
            return MakeResult(
                success=result.returncode == 0,
                target=target,
                execution_time=execution_time,
                output=result.stdout + result.stderr,
                errors=errors,
            )
        
        except subprocess.TimeoutExpired:
            logger.error(f"Make 目标 '{target}' 超时（{timeout}秒）")
            return MakeResult(
                success=False,
                target=target,
                execution_time=timeout,
                output="执行超时",
                errors=["执行超时"],
            )
        
        except Exception as e:
            logger.error(f"执行 Make 目标失败: {e}")
            return MakeResult(
                success=False,
                target=target,
                execution_time=time.time() - start_time,
                output=str(e),
                errors=[str(e)],
            )
    
    def _extract_make_errors(self, stderr: str) -> List[str]:
        """提取 Make 错误信息"""
        errors = []
        
        for line in stderr.split('\n'):
            line = line.strip()
            if line and ('error' in line.lower() or 'failed' in line.lower()):
                errors.append(line)
        
        return errors


class GoErrorParser:
    """Go 错误解析器"""
    
    def parse_compile_errors(self, output: str) -> List[GoError]:
        """
        解析 Go 编译错误
        
        Args:
            output: 编译输出
            
        Returns:
            List[GoError]: 错误列表
        """
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
        """
        解析 Go 测试错误
        
        Args:
            test_result: 测试结果
            
        Returns:
            List[GoError]: 错误列表
        """
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
        """
        对错误进行分类
        
        Args:
            error: Go 错误
            
        Returns:
            str: 错误类别
        """
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
