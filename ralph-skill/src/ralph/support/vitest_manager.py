"""
Vitest 测试管理器

提供 Vitest 单元测试执行、结果解析、错误提取等功能。
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ralph.models.enums import DependencyManager
from ralph.models.frontend import (
    CoverageReport,
    FailedTestDetail,
    FileCoverage,
    TestResult,
    VitestConfig,
)


class VitestManager:
    """Vitest 测试管理器"""
    
    def __init__(self, project_path: Path, package_manager: DependencyManager = DependencyManager.NPM):
        """
        初始化 Vitest 管理器
        
        Args:
            project_path: 项目根目录路径
            package_manager: 包管理器类型
        """
        self.project_path = Path(project_path)
        self.package_manager = package_manager
    
    def run_tests(
        self,
        test_path: Optional[str] = None,
        config: Optional[VitestConfig] = None,
        timeout: int = 300
    ) -> TestResult:
        """
        运行 Vitest 测试
        
        Args:
            test_path: 测试文件或目录路径，None 表示运行所有测试
            config: Vitest 配置
            timeout: 超时时间（秒）
            
        Returns:
            TestResult: 测试结果
        """
        if config is None:
            config = VitestConfig()
        
        # 构建测试命令
        cmd = self._build_test_command(test_path, config)
        
        try:
            # 执行测试
            result = subprocess.run(
                cmd,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            # 解析测试输出
            test_result = self._parse_test_output(
                result.stdout,
                result.stderr,
                result.returncode
            )
            
            # 如果启用了覆盖率，解析覆盖率报告
            if config.coverage:
                coverage_report = self._parse_coverage_report()
                test_result.coverage = coverage_report
            
            return test_result
            
        except subprocess.TimeoutExpired:
            return TestResult(
                success=False,
                test_type="unit",
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                skipped_tests=0,
                execution_time=timeout,
                test_output=f"测试执行超时（{timeout}秒）",
                failed_test_details=[
                    FailedTestDetail(
                        test_name="timeout",
                        test_file="unknown",
                        error_message=f"测试执行超时（{timeout}秒）",
                        stack_trace=""
                    )
                ]
            )
        except Exception as e:
            return TestResult(
                success=False,
                test_type="unit",
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                skipped_tests=0,
                execution_time=0.0,
                test_output=f"测试执行失败: {str(e)}",
                failed_test_details=[
                    FailedTestDetail(
                        test_name="error",
                        test_file="unknown",
                        error_message=str(e),
                        stack_trace=""
                    )
                ]
            )
    
    def _build_test_command(
        self,
        test_path: Optional[str],
        config: VitestConfig
    ) -> List[str]:
        """构建测试命令"""
        # 获取包管理器命令
        if self.package_manager == DependencyManager.NPM:
            cmd = ["npm", "run", "test"]
        elif self.package_manager == DependencyManager.YARN:
            cmd = ["yarn", "test"]
        elif self.package_manager == DependencyManager.PNPM:
            cmd = ["pnpm", "test"]
        else:
            cmd = ["npm", "run", "test"]
        
        # 添加 --run 标志（非监视模式）
        cmd.append("--run")
        
        # 添加测试路径
        if test_path:
            cmd.append(test_path)
        
        # 添加覆盖率选项
        if config.coverage:
            cmd.append("--coverage")
        
        # 添加 reporter 选项
        if config.reporters:
            for reporter in config.reporters:
                cmd.extend(["--reporter", reporter])
        
        return cmd
    
    def _parse_test_output(
        self,
        stdout: str,
        stderr: str,
        return_code: int
    ) -> TestResult:
        """
        解析 Vitest 测试输出
        
        Args:
            stdout: 标准输出
            stderr: 标准错误输出
            return_code: 返回码
            
        Returns:
            TestResult: 解析后的测试结果
        """
        # 合并输出
        output = stdout + "\n" + stderr
        
        # 提取测试统计信息
        total_tests, passed_tests, failed_tests, skipped_tests = self._extract_test_stats(output)
        
        # 提取执行时间
        execution_time = self._extract_execution_time(output)
        
        # 提取失败的测试详情
        failed_test_details = self._extract_failed_tests(output)
        
        # 判断测试是否成功
        success = return_code == 0 and failed_tests == 0
        
        return TestResult(
            success=success,
            test_type="unit",
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            skipped_tests=skipped_tests,
            execution_time=execution_time,
            test_output=output,
            failed_test_details=failed_test_details
        )
    
    def _extract_test_stats(self, output: str) -> Tuple[int, int, int, int]:
        """
        提取测试统计信息
        
        Returns:
            (total_tests, passed_tests, failed_tests, skipped_tests)
        """
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        skipped_tests = 0
        
        # Vitest 输出格式示例：
        # Test Files  2 passed (2)
        # Tests  10 passed (10)
        # 或者：
        # Test Files  1 failed | 1 passed (2)
        # Tests  5 failed | 5 passed (10)
        # 或者带跳过：
        # Tests  8 passed | 2 skipped (10)
        
        # 提取测试用例统计 - 处理多种格式
        # 格式1: Tests  5 failed | 5 passed (10)
        tests_match = re.search(
            r'Tests\s+(?:(\d+)\s+failed\s+\|\s+)?(\d+)\s+passed\s+(?:\|\s+(\d+)\s+skipped\s+)?\((\d+)\)',
            output
        )
        
        if tests_match:
            failed_str = tests_match.group(1)
            passed_str = tests_match.group(2)
            skipped_str = tests_match.group(3)
            total_str = tests_match.group(4)
            
            failed_tests = int(failed_str) if failed_str else 0
            passed_tests = int(passed_str) if passed_str else 0
            skipped_tests = int(skipped_str) if skipped_str else 0
            total_tests = int(total_str) if total_str else 0
        else:
            # 尝试另一种格式: Tests  2 skipped | 8 passed (10)
            tests_match2 = re.search(
                r'Tests\s+(?:(\d+)\s+skipped\s+\|\s+)?(\d+)\s+passed\s+\((\d+)\)',
                output
            )
            if tests_match2:
                skipped_str = tests_match2.group(1)
                passed_str = tests_match2.group(2)
                total_str = tests_match2.group(3)
                
                skipped_tests = int(skipped_str) if skipped_str else 0
                passed_tests = int(passed_str) if passed_str else 0
                total_tests = int(total_str) if total_str else 0
        
        return total_tests, passed_tests, failed_tests, skipped_tests
    
    def _extract_execution_time(self, output: str) -> float:
        """提取测试执行时间（秒）"""
        # Vitest 输出格式示例：
        # Duration  1.23s (in thread 456ms, 268.42% of cpu)
        # 或者：
        # Duration  123ms
        
        # 尝试匹配秒
        time_match = re.search(r'Duration\s+([\d.]+)s', output)
        if time_match:
            return float(time_match.group(1))
        
        # 尝试匹配毫秒
        time_match = re.search(r'Duration\s+([\d.]+)ms', output)
        if time_match:
            return float(time_match.group(1)) / 1000.0
        
        return 0.0
    
    def _extract_failed_tests(self, output: str) -> List[FailedTestDetail]:
        """
        提取失败的测试详情
        
        Vitest 失败输出格式示例：
        ❯ src/components/Button.test.ts (1)
          ❯ Button component (1)
            × should render correctly
              AssertionError: expected '<button>Click</button>' to equal '<button>Submit</button>'
              
              - Expected
              + Received
              
              - <button>Submit</button>
              + <button>Click</button>
              
              ❯ src/components/Button.test.ts:15:7
        """
        failed_tests = []
        
        # 使用正则表达式提取失败的测试
        # 匹配测试文件和测试名称
        test_pattern = r'❯\s+([^\s]+\.test\.[jt]sx?)\s+\(\d+\).*?×\s+(.+?)(?=\n\s+(?:AssertionError|Error|TypeError))'
        
        for match in re.finditer(test_pattern, output, re.DOTALL):
            test_file = match.group(1).strip()
            test_name = match.group(2).strip()
            
            # 提取错误信息和堆栈跟踪（包含完整的错误部分）
            error_message, error_section, expected, actual = self._extract_error_details(
                output,
                test_file,
                test_name
            )
            
            # 从完整的错误部分提取行号
            line_number = self._extract_line_number(error_section)
            
            failed_tests.append(FailedTestDetail(
                test_name=test_name,
                test_file=test_file,
                error_message=error_message,
                stack_trace=error_section,
                line_number=line_number,
                expected=expected,
                actual=actual
            ))
        
        return failed_tests
    
    def _extract_error_details(
        self,
        output: str,
        test_file: str,
        test_name: str
    ) -> Tuple[str, str, Optional[str], Optional[str]]:
        """
        提取错误详情
        
        Returns:
            (error_message, stack_trace, expected, actual)
        """
        # 查找测试失败的详细信息
        # 从测试名称开始，到下一个测试或文件结束
        pattern = re.escape(test_name) + r'(.*?)(?=❯|$)'
        match = re.search(pattern, output, re.DOTALL)
        
        if not match:
            return "测试失败", "", None, None
        
        error_section = match.group(1)
        
        # 提取错误消息（第一行）
        error_lines = error_section.strip().split('\n')
        error_message = error_lines[0].strip() if error_lines else "测试失败"
        
        # 移除 ANSI 颜色代码
        error_message = re.sub(r'\x1b\[[0-9;]*m', '', error_message)
        
        # 提取 expected 和 actual
        expected = None
        actual = None
        
        # 查找 Expected 和 Received
        expected_match = re.search(r'-\s+Expected.*?\n\s*-\s*(.+)', error_section)
        if expected_match:
            expected = expected_match.group(1).strip()
        
        actual_match = re.search(r'\+\s+Received.*?\n\s*\+\s*(.+)', error_section)
        if actual_match:
            actual = actual_match.group(1).strip()
        
        # 提取堆栈跟踪
        stack_trace = error_section.strip()
        
        return error_message, stack_trace, expected, actual
    
    def _extract_line_number(self, stack_trace: str) -> Optional[int]:
        """从堆栈跟踪中提取行号"""
        # 匹配格式：❯ src/components/Button.test.ts:15:7
        # 或者：src/utils/math.test.ts:10:5
        line_match = re.search(r'\.test\.[jt]sx?:(\d+):\d+', stack_trace)
        if line_match:
            return int(line_match.group(1))
        return None
    
    def _parse_coverage_report(self) -> Optional[CoverageReport]:
        """
        解析覆盖率报告
        
        Vitest 会生成 coverage/coverage-final.json 文件
        """
        coverage_file = self.project_path / "coverage" / "coverage-final.json"
        
        if not coverage_file.exists():
            return None
        
        try:
            with open(coverage_file, 'r', encoding='utf-8') as f:
                coverage_data = json.load(f)
            
            # 计算总体覆盖率
            total_lines = 0
            covered_lines = 0
            total_branches = 0
            covered_branches = 0
            total_functions = 0
            covered_functions = 0
            total_statements = 0
            covered_statements = 0
            
            file_coverage_dict: Dict[str, FileCoverage] = {}
            
            # 遍历每个文件的覆盖率数据
            for file_path, file_data in coverage_data.items():
                # 提取行覆盖率
                line_coverage = file_data.get('s', {})  # statements
                lines_total = len(line_coverage)
                lines_covered = sum(1 for count in line_coverage.values() if count > 0)
                
                # 提取分支覆盖率
                branch_coverage = file_data.get('b', {})
                branches_total = sum(len(branches) for branches in branch_coverage.values())
                branches_covered = sum(
                    sum(1 for count in branches if count > 0)
                    for branches in branch_coverage.values()
                )
                
                # 提取函数覆盖率
                function_coverage = file_data.get('f', {})
                functions_total = len(function_coverage)
                functions_covered = sum(1 for count in function_coverage.values() if count > 0)
                
                # 计算文件覆盖率百分比
                coverage_percent = (lines_covered / lines_total * 100) if lines_total > 0 else 0.0
                
                # 提取未覆盖的行
                uncovered_lines = [
                    int(line_num)
                    for line_num, count in line_coverage.items()
                    if count == 0
                ]
                
                # 创建文件覆盖率对象
                file_coverage_dict[file_path] = FileCoverage(
                    file_path=file_path,
                    coverage_percent=coverage_percent,
                    lines_covered=lines_covered,
                    lines_total=lines_total,
                    branches_covered=branches_covered,
                    branches_total=branches_total,
                    functions_covered=functions_covered,
                    functions_total=functions_total,
                    uncovered_lines=uncovered_lines
                )
                
                # 累加总计
                total_lines += lines_total
                covered_lines += lines_covered
                total_branches += branches_total
                covered_branches += branches_covered
                total_functions += functions_total
                covered_functions += functions_covered
                total_statements += lines_total
                covered_statements += lines_covered
            
            # 计算总体覆盖率
            line_coverage_percent = (covered_lines / total_lines * 100) if total_lines > 0 else 0.0
            branch_coverage_percent = (covered_branches / total_branches * 100) if total_branches > 0 else 0.0
            function_coverage_percent = (covered_functions / total_functions * 100) if total_functions > 0 else 0.0
            statement_coverage_percent = (covered_statements / total_statements * 100) if total_statements > 0 else 0.0
            
            # 计算总体覆盖率（平均值）
            total_coverage = (
                line_coverage_percent +
                branch_coverage_percent +
                function_coverage_percent +
                statement_coverage_percent
            ) / 4.0
            
            return CoverageReport(
                total_coverage=total_coverage,
                line_coverage=line_coverage_percent,
                branch_coverage=branch_coverage_percent,
                function_coverage=function_coverage_percent,
                statement_coverage=statement_coverage_percent,
                file_coverage=file_coverage_dict
            )
            
        except Exception as e:
            print(f"解析覆盖率报告失败: {e}")
            return None
    
    def extract_error_summary(self, test_result: TestResult) -> str:
        """
        提取测试错误摘要
        
        Args:
            test_result: 测试结果
            
        Returns:
            str: 错误摘要
        """
        if test_result.success:
            return "所有测试通过"
        
        summary_lines = [
            f"测试失败: {test_result.failed_tests}/{test_result.total_tests} 个测试失败",
            ""
        ]
        
        # 添加失败测试的详情
        for i, failed_test in enumerate(test_result.failed_test_details, 1):
            summary_lines.append(f"{i}. {failed_test.test_name}")
            summary_lines.append(f"   文件: {failed_test.test_file}")
            if failed_test.line_number:
                summary_lines.append(f"   行号: {failed_test.line_number}")
            summary_lines.append(f"   错误: {failed_test.error_message}")
            
            if failed_test.expected and failed_test.actual:
                summary_lines.append(f"   期望: {failed_test.expected}")
                summary_lines.append(f"   实际: {failed_test.actual}")
            
            summary_lines.append("")
        
        return "\n".join(summary_lines)
    
    def generate_test_report(self, test_result: TestResult) -> Dict[str, any]:
        """
        生成测试报告
        
        Args:
            test_result: 测试结果
            
        Returns:
            Dict: 测试报告（JSON 格式）
        """
        report = {
            "success": test_result.success,
            "summary": {
                "total": test_result.total_tests,
                "passed": test_result.passed_tests,
                "failed": test_result.failed_tests,
                "skipped": test_result.skipped_tests,
                "execution_time": test_result.execution_time
            },
            "failed_tests": [
                {
                    "name": test.test_name,
                    "file": test.test_file,
                    "line": test.line_number,
                    "error": test.error_message,
                    "expected": test.expected,
                    "actual": test.actual
                }
                for test in test_result.failed_test_details
            ]
        }
        
        # 添加覆盖率信息
        if test_result.coverage:
            report["coverage"] = {
                "total": test_result.coverage.total_coverage,
                "line": test_result.coverage.line_coverage,
                "branch": test_result.coverage.branch_coverage,
                "function": test_result.coverage.function_coverage,
                "statement": test_result.coverage.statement_coverage
            }
        
        return report
