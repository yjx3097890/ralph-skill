"""
Playwright E2E 测试管理器

提供 Playwright 端到端测试执行、多浏览器支持、结果解析、错误诊断等功能。
"""

import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ralph.models.enums import (
    BrowserType,
    DependencyManager,
    ScreenshotMode,
    TraceMode,
    VideoMode,
)
from ralph.models.frontend import (
    BrowserTestResult,
    E2ETestResult,
    FailedE2ETest,
    PlaywrightConfig,
    Screenshot,
    TraceFile,
    VideoFile,
)


class PlaywrightManager:
    """Playwright E2E 测试管理器"""
    
    def __init__(
        self,
        project_path: Path,
        package_manager: DependencyManager = DependencyManager.NPM
    ):
        """
        初始化 Playwright 管理器
        
        Args:
            project_path: 项目根目录路径
            package_manager: 包管理器类型
        """
        self.project_path = Path(project_path)
        self.package_manager = package_manager

    def setup_browsers(self, browsers: List[BrowserType]) -> Dict[str, bool]:
        """
        设置浏览器环境
        
        Args:
            browsers: 浏览器类型列表
            
        Returns:
            Dict[str, bool]: 每个浏览器的安装状态
        """
        setup_results = {}
        
        for browser in browsers:
            try:
                # 检查浏览器是否已安装
                result = subprocess.run(
                    ["npx", "playwright", "install", browser.value, "--dry-run"],
                    cwd=self.project_path,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                # 如果需要安装，则执行安装
                if "needs to be installed" in result.stdout or result.returncode != 0:
                    install_result = subprocess.run(
                        ["npx", "playwright", "install", browser.value],
                        cwd=self.project_path,
                        capture_output=True,
                        text=True,
                        timeout=300  # 5 分钟超时
                    )
                    setup_results[browser.value] = install_result.returncode == 0
                else:
                    setup_results[browser.value] = True
                    
            except subprocess.TimeoutExpired:
                setup_results[browser.value] = False
            except Exception as e:
                print(f"设置浏览器 {browser.value} 失败: {e}")
                setup_results[browser.value] = False
        
        return setup_results

    def run_test_suite(
        self,
        test_files: Optional[List[str]] = None,
        config: Optional[PlaywrightConfig] = None,
        timeout: int = 600
    ) -> E2ETestResult:
        """
        运行 Playwright E2E 测试套件
        
        Args:
            test_files: 测试文件列表，None 表示运行所有测试
            config: Playwright 配置
            timeout: 超时时间（秒）
            
        Returns:
            E2ETestResult: E2E 测试结果
        """
        if config is None:
            config = PlaywrightConfig()
        
        # 构建测试命令
        cmd = self._build_test_command(test_files, config)
        
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
                result.returncode,
                config
            )
            
            return test_result
            
        except subprocess.TimeoutExpired:
            return self._create_timeout_result(timeout, config)
        except Exception as e:
            return self._create_error_result(str(e), config)

    def _build_test_command(
        self,
        test_files: Optional[List[str]],
        config: PlaywrightConfig
    ) -> List[str]:
        """构建 Playwright 测试命令"""
        # 获取包管理器命令
        if self.package_manager == DependencyManager.NPM:
            cmd = ["npx", "playwright", "test"]
        elif self.package_manager == DependencyManager.YARN:
            cmd = ["yarn", "playwright", "test"]
        elif self.package_manager == DependencyManager.PNPM:
            cmd = ["pnpm", "exec", "playwright", "test"]
        else:
            cmd = ["npx", "playwright", "test"]
        
        # 添加测试文件
        if test_files:
            cmd.extend(test_files)
        
        # 添加浏览器配置
        if config.browsers:
            for browser in config.browsers:
                cmd.extend(["--project", browser.value])
        
        # 添加其他配置
        if config.headless:
            cmd.append("--headed=false")
        else:
            cmd.append("--headed")
        
        # 添加重试次数
        if config.retries > 0:
            cmd.extend(["--retries", str(config.retries)])
        
        # 添加并行工作进程数
        if config.workers > 0:
            cmd.extend(["--workers", str(config.workers)])
        
        # 添加 reporter
        cmd.extend(["--reporter", "json"])
        
        return cmd

    def _parse_test_output(
        self,
        stdout: str,
        stderr: str,
        return_code: int,
        config: PlaywrightConfig
    ) -> E2ETestResult:
        """
        解析 Playwright 测试输出
        
        Args:
            stdout: 标准输出
            stderr: 标准错误输出
            return_code: 返回码
            config: Playwright 配置
            
        Returns:
            E2ETestResult: 解析后的 E2E 测试结果
        """
        # 合并输出
        output = stdout + "\n" + stderr
        
        # 尝试解析 JSON 报告
        json_report = self._extract_json_report(stdout)
        
        if json_report:
            return self._parse_json_report(json_report, output, return_code, config)
        else:
            # 如果没有 JSON 报告，使用文本解析
            return self._parse_text_output(output, return_code, config)

    def _extract_json_report(self, output: str) -> Optional[Dict]:
        """从输出中提取 JSON 报告"""
        try:
            # Playwright JSON reporter 输出格式
            # 查找 JSON 对象
            json_match = re.search(r'\{[\s\S]*"suites"[\s\S]*\}', output)
            if json_match:
                return json.loads(json_match.group(0))
            
            # 尝试直接解析整个输出
            return json.loads(output)
        except json.JSONDecodeError:
            return None
        except Exception:
            return None
    
    def _parse_json_report(
        self,
        report: Dict,
        output: str,
        return_code: int,
        config: PlaywrightConfig
    ) -> E2ETestResult:
        """解析 JSON 格式的测试报告"""
        # 提取测试统计
        stats = report.get('stats', {})
        total_tests = stats.get('expected', 0) + stats.get('unexpected', 0) + stats.get('skipped', 0)
        passed_tests = stats.get('expected', 0)
        failed_tests = stats.get('unexpected', 0)
        skipped_tests = stats.get('skipped', 0)
        execution_time = stats.get('duration', 0) / 1000.0  # 转换为秒
        
        # 按浏览器分组结果
        browser_results = self._group_results_by_browser(report, config)
        
        # 提取失败的测试详情
        failed_test_details = self._extract_failed_tests_from_json(report, config)
        
        # 收集截图、视频和追踪文件
        screenshots = self._collect_screenshots(config)
        videos = self._collect_videos(config)
        traces = self._collect_traces(config)
        
        # 判断测试是否成功
        success = return_code == 0 and failed_tests == 0
        
        return E2ETestResult(
            success=success,
            test_type="e2e",
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            skipped_tests=skipped_tests,
            execution_time=execution_time,
            test_output=output,
            browser_results=browser_results,
            screenshots=screenshots,
            videos=videos,
            traces=traces,
            failed_test_details=failed_test_details
        )

    def _parse_text_output(
        self,
        output: str,
        return_code: int,
        config: PlaywrightConfig
    ) -> E2ETestResult:
        """解析文本格式的测试输出"""
        # 提取测试统计信息
        total_tests, passed_tests, failed_tests, skipped_tests = self._extract_test_stats_from_text(output)
        
        # 提取执行时间
        execution_time = self._extract_execution_time_from_text(output)
        
        # 提取失败的测试详情
        failed_test_details = self._extract_failed_tests_from_text(output, config)
        
        # 创建浏览器结果（简化版）
        browser_results = {}
        for browser in config.browsers:
            browser_results[browser.value] = BrowserTestResult(
                browser=browser,
                version="unknown",
                success=failed_tests == 0,
                tests_run=total_tests,
                tests_passed=passed_tests,
                tests_failed=failed_tests,
                execution_time=execution_time,
                failed_tests=[]
            )
        
        # 收集截图、视频和追踪文件
        screenshots = self._collect_screenshots(config)
        videos = self._collect_videos(config)
        traces = self._collect_traces(config)
        
        # 判断测试是否成功
        success = return_code == 0 and failed_tests == 0
        
        return E2ETestResult(
            success=success,
            test_type="e2e",
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            skipped_tests=skipped_tests,
            execution_time=execution_time,
            test_output=output,
            browser_results=browser_results,
            screenshots=screenshots,
            videos=videos,
            traces=traces,
            failed_test_details=failed_test_details
        )

    def _group_results_by_browser(
        self,
        report: Dict,
        config: PlaywrightConfig
    ) -> Dict[str, BrowserTestResult]:
        """按浏览器分组测试结果"""
        browser_results = {}
        
        # 遍历所有测试套件
        for suite in report.get('suites', []):
            self._process_suite_for_browsers(suite, browser_results, config)
        
        return browser_results
    
    def _process_suite_for_browsers(
        self,
        suite: Dict,
        browser_results: Dict[str, BrowserTestResult],
        config: PlaywrightConfig
    ):
        """处理测试套件，提取浏览器结果"""
        # 获取项目名称（通常是浏览器名称）
        project = suite.get('project', {}).get('name', 'unknown')
        
        # 初始化浏览器结果
        if project not in browser_results:
            # 尝试匹配浏览器类型
            browser_type = self._match_browser_type(project)
            browser_results[project] = BrowserTestResult(
                browser=browser_type,
                version=suite.get('project', {}).get('version', 'unknown'),
                success=True,
                tests_run=0,
                tests_passed=0,
                tests_failed=0,
                execution_time=0.0,
                failed_tests=[]
            )
        
        # 处理测试用例
        for spec in suite.get('specs', []):
            for test in spec.get('tests', []):
                browser_results[project].tests_run += 1
                
                # 获取测试结果
                results = test.get('results', [])
                if results:
                    result = results[0]  # 取第一个结果
                    status = result.get('status', 'unknown')
                    duration = result.get('duration', 0) / 1000.0
                    
                    browser_results[project].execution_time += duration
                    
                    if status == 'passed':
                        browser_results[project].tests_passed += 1
                    elif status == 'failed':
                        browser_results[project].tests_failed += 1
                        browser_results[project].success = False
                        
                        # 添加失败测试详情
                        failed_test = self._create_failed_test_from_result(
                            test,
                            result,
                            browser_results[project].browser,
                            spec.get('file', 'unknown')
                        )
                        browser_results[project].failed_tests.append(failed_test)
        
        # 递归处理子套件
        for sub_suite in suite.get('suites', []):
            self._process_suite_for_browsers(sub_suite, browser_results, config)

    def _match_browser_type(self, project_name: str) -> BrowserType:
        """匹配浏览器类型"""
        project_lower = project_name.lower()
        
        if 'chromium' in project_lower or 'chrome' in project_lower:
            return BrowserType.CHROMIUM
        elif 'firefox' in project_lower:
            return BrowserType.FIREFOX
        elif 'webkit' in project_lower or 'safari' in project_lower:
            return BrowserType.WEBKIT
        else:
            return BrowserType.CHROMIUM  # 默认
    
    def _create_failed_test_from_result(
        self,
        test: Dict,
        result: Dict,
        browser: BrowserType,
        file_path: str
    ) -> FailedE2ETest:
        """从测试结果创建失败测试对象"""
        test_name = test.get('title', 'unknown')
        error = result.get('error', {})
        error_message = error.get('message', '测试失败')
        stack_trace = error.get('stack', '')
        
        # 提取附件路径
        attachments = result.get('attachments', [])
        screenshot_path = None
        video_path = None
        trace_path = None
        
        for attachment in attachments:
            name = attachment.get('name', '')
            path = attachment.get('path', '')
            
            if 'screenshot' in name.lower():
                screenshot_path = path
            elif 'video' in name.lower():
                video_path = path
            elif 'trace' in name.lower():
                trace_path = path
        
        return FailedE2ETest(
            test_name=test_name,
            browser=browser,
            error_message=error_message,
            stack_trace=stack_trace,
            screenshot_path=screenshot_path,
            video_path=video_path,
            trace_path=trace_path,
            retry_count=result.get('retry', 0)
        )

    def _extract_failed_tests_from_json(
        self,
        report: Dict,
        config: PlaywrightConfig
    ) -> List[FailedE2ETest]:
        """从 JSON 报告中提取失败的测试"""
        failed_tests = []
        
        for suite in report.get('suites', []):
            self._extract_failed_tests_from_suite(suite, failed_tests, config)
        
        return failed_tests
    
    def _extract_failed_tests_from_suite(
        self,
        suite: Dict,
        failed_tests: List[FailedE2ETest],
        config: PlaywrightConfig
    ):
        """从测试套件中提取失败的测试"""
        project_name = suite.get('project', {}).get('name', 'unknown')
        browser = self._match_browser_type(project_name)
        
        for spec in suite.get('specs', []):
            file_path = spec.get('file', 'unknown')
            
            for test in spec.get('tests', []):
                results = test.get('results', [])
                
                for result in results:
                    if result.get('status') == 'failed':
                        failed_test = self._create_failed_test_from_result(
                            test,
                            result,
                            browser,
                            file_path
                        )
                        failed_tests.append(failed_test)
        
        # 递归处理子套件
        for sub_suite in suite.get('suites', []):
            self._extract_failed_tests_from_suite(sub_suite, failed_tests, config)

    def _extract_test_stats_from_text(self, output: str) -> Tuple[int, int, int, int]:
        """从文本输出中提取测试统计信息"""
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        skipped_tests = 0
        
        # Playwright 输出格式示例：
        # 5 passed (10s)
        # 2 failed (5s)
        # 1 skipped
        
        # 提取通过的测试
        passed_match = re.search(r'(\d+)\s+passed', output)
        if passed_match:
            passed_tests = int(passed_match.group(1))
        
        # 提取失败的测试
        failed_match = re.search(r'(\d+)\s+failed', output)
        if failed_match:
            failed_tests = int(failed_match.group(1))
        
        # 提取跳过的测试
        skipped_match = re.search(r'(\d+)\s+skipped', output)
        if skipped_match:
            skipped_tests = int(skipped_match.group(1))
        
        # 计算总数
        total_tests = passed_tests + failed_tests + skipped_tests
        
        return total_tests, passed_tests, failed_tests, skipped_tests
    
    def _extract_execution_time_from_text(self, output: str) -> float:
        """从文本输出中提取执行时间"""
        # 匹配格式：(10s) 或 (1.5m) 或 (100ms)
        time_match = re.search(r'\((\d+(?:\.\d+)?)(s|m|ms)\)', output)
        
        if time_match:
            value = float(time_match.group(1))
            unit = time_match.group(2)
            
            if unit == 's':
                return value
            elif unit == 'm':
                return value * 60
            elif unit == 'ms':
                return value / 1000
        
        return 0.0

    def _extract_failed_tests_from_text(
        self,
        output: str,
        config: PlaywrightConfig
    ) -> List[FailedE2ETest]:
        """从文本输出中提取失败的测试"""
        failed_tests = []
        
        # Playwright 失败输出格式示例：
        # 1) [chromium] › tests/example.spec.ts:3:1 › should work
        #    Error: expect(received).toBe(expected)
        
        # 匹配失败的测试
        pattern = r'\d+\)\s+\[(\w+)\]\s+›\s+([^\s]+):(\d+):(\d+)\s+›\s+(.+?)(?=\n\s+Error:|\n\s+\d+\)|\Z)'
        
        for match in re.finditer(pattern, output, re.DOTALL):
            browser_name = match.group(1)
            file_path = match.group(2)
            line_number = int(match.group(3))
            test_name = match.group(5).strip()
            
            # 匹配浏览器类型
            browser = self._match_browser_type(browser_name)
            
            # 提取错误信息
            error_message, stack_trace = self._extract_error_from_text(
                output,
                test_name,
                file_path
            )
            
            failed_tests.append(FailedE2ETest(
                test_name=test_name,
                browser=browser,
                error_message=error_message,
                stack_trace=stack_trace,
                screenshot_path=None,
                video_path=None,
                trace_path=None,
                retry_count=0
            ))
        
        return failed_tests
    
    def _extract_error_from_text(
        self,
        output: str,
        test_name: str,
        file_path: str
    ) -> Tuple[str, str]:
        """从文本输出中提取错误信息"""
        # 查找测试失败的详细信息
        pattern = re.escape(test_name) + r'(.*?)(?=\d+\)|$)'
        match = re.search(pattern, output, re.DOTALL)
        
        if not match:
            return "测试失败", ""
        
        error_section = match.group(1)
        
        # 提取错误消息（第一行）
        error_lines = error_section.strip().split('\n')
        error_message = error_lines[0].strip() if error_lines else "测试失败"
        
        # 移除 ANSI 颜色代码
        error_message = re.sub(r'\x1b\[[0-9;]*m', '', error_message)
        
        # 提取堆栈跟踪
        stack_trace = error_section.strip()
        
        return error_message, stack_trace

    def _collect_screenshots(self, config: PlaywrightConfig) -> List[Screenshot]:
        """收集测试截图"""
        screenshots = []
        output_dir = self.project_path / config.output_dir
        
        if not output_dir.exists():
            return screenshots
        
        # 查找所有截图文件
        for screenshot_file in output_dir.rglob("*.png"):
            # 从文件名提取信息
            file_name = screenshot_file.stem
            
            # 尝试从文件名提取测试名称和浏览器
            # 格式通常是：test-name-chromium.png
            parts = file_name.rsplit('-', 1)
            test_name = parts[0] if len(parts) > 1 else file_name
            browser_name = parts[1] if len(parts) > 1 else 'unknown'
            
            browser = self._match_browser_type(browser_name)
            
            # 获取文件信息
            stat = screenshot_file.stat()
            
            screenshots.append(Screenshot(
                test_name=test_name,
                browser=browser,
                file_path=screenshot_file,
                timestamp=datetime.fromtimestamp(stat.st_mtime),
                test_status='failed',  # 通常只在失败时截图
                size_bytes=stat.st_size
            ))
        
        return screenshots
    
    def _collect_videos(self, config: PlaywrightConfig) -> List[VideoFile]:
        """收集测试视频"""
        videos = []
        output_dir = self.project_path / config.output_dir
        
        if not output_dir.exists():
            return videos
        
        # 查找所有视频文件
        for video_file in output_dir.rglob("*.webm"):
            # 从文件名提取信息
            file_name = video_file.stem
            parts = file_name.rsplit('-', 1)
            test_name = parts[0] if len(parts) > 1 else file_name
            browser_name = parts[1] if len(parts) > 1 else 'unknown'
            
            browser = self._match_browser_type(browser_name)
            
            # 获取文件信息
            stat = video_file.stat()
            
            videos.append(VideoFile(
                test_name=test_name,
                browser=browser,
                file_path=video_file,
                timestamp=datetime.fromtimestamp(stat.st_mtime),
                duration_seconds=0.0,  # 需要解析视频才能获取
                size_bytes=stat.st_size
            ))
        
        return videos
    
    def _collect_traces(self, config: PlaywrightConfig) -> List[TraceFile]:
        """收集测试追踪文件"""
        traces = []
        output_dir = self.project_path / config.output_dir
        
        if not output_dir.exists():
            return traces
        
        # 查找所有追踪文件
        for trace_file in output_dir.rglob("*.zip"):
            # 从文件名提取信息
            file_name = trace_file.stem
            parts = file_name.rsplit('-', 1)
            test_name = parts[0] if len(parts) > 1 else file_name
            browser_name = parts[1] if len(parts) > 1 else 'unknown'
            
            browser = self._match_browser_type(browser_name)
            
            # 获取文件信息
            stat = trace_file.stat()
            
            traces.append(TraceFile(
                test_name=test_name,
                browser=browser,
                file_path=trace_file,
                timestamp=datetime.fromtimestamp(stat.st_mtime),
                size_bytes=stat.st_size
            ))
        
        return traces

    def _create_timeout_result(
        self,
        timeout: int,
        config: PlaywrightConfig
    ) -> E2ETestResult:
        """创建超时错误结果"""
        return E2ETestResult(
            success=False,
            test_type="e2e",
            total_tests=0,
            passed_tests=0,
            failed_tests=0,
            skipped_tests=0,
            execution_time=timeout,
            test_output=f"E2E 测试执行超时（{timeout}秒）",
            browser_results={},
            screenshots=[],
            videos=[],
            traces=[],
            failed_test_details=[
                FailedE2ETest(
                    test_name="timeout",
                    browser=BrowserType.CHROMIUM,
                    error_message=f"测试执行超时（{timeout}秒）",
                    stack_trace="",
                    screenshot_path=None,
                    video_path=None,
                    trace_path=None,
                    retry_count=0
                )
            ]
        )
    
    def _create_error_result(
        self,
        error_message: str,
        config: PlaywrightConfig
    ) -> E2ETestResult:
        """创建错误结果"""
        return E2ETestResult(
            success=False,
            test_type="e2e",
            total_tests=0,
            passed_tests=0,
            failed_tests=0,
            skipped_tests=0,
            execution_time=0.0,
            test_output=f"E2E 测试执行失败: {error_message}",
            browser_results={},
            screenshots=[],
            videos=[],
            traces=[],
            failed_test_details=[
                FailedE2ETest(
                    test_name="error",
                    browser=BrowserType.CHROMIUM,
                    error_message=error_message,
                    stack_trace="",
                    screenshot_path=None,
                    video_path=None,
                    trace_path=None,
                    retry_count=0
                )
            ]
        )

    def diagnose_browser_launch_failure(self, browser: BrowserType) -> Dict[str, any]:
        """
        诊断浏览器启动失败
        
        Args:
            browser: 浏览器类型
            
        Returns:
            Dict: 诊断信息
        """
        diagnosis = {
            "browser": browser.value,
            "installed": False,
            "executable_found": False,
            "error": None,
            "suggestions": []
        }
        
        try:
            # 检查浏览器是否已安装
            result = subprocess.run(
                ["npx", "playwright", "install", browser.value, "--dry-run"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                diagnosis["installed"] = True
                diagnosis["executable_found"] = True
            else:
                diagnosis["error"] = result.stderr
                diagnosis["suggestions"].append(
                    f"运行 'npx playwright install {browser.value}' 安装浏览器"
                )
        
        except subprocess.TimeoutExpired:
            diagnosis["error"] = "检查浏览器状态超时"
            diagnosis["suggestions"].append("检查网络连接")
        
        except FileNotFoundError:
            diagnosis["error"] = "未找到 Playwright 命令"
            diagnosis["suggestions"].append("确保已安装 @playwright/test 包")
            diagnosis["suggestions"].append("运行 'npm install @playwright/test'")
        
        except Exception as e:
            diagnosis["error"] = str(e)
        
        return diagnosis
    
    def diagnose_test_timeout(
        self,
        test_name: str,
        timeout: int
    ) -> Dict[str, any]:
        """
        诊断测试超时
        
        Args:
            test_name: 测试名称
            timeout: 超时时间（毫秒）
            
        Returns:
            Dict: 诊断信息
        """
        diagnosis = {
            "test_name": test_name,
            "timeout": timeout,
            "possible_causes": [],
            "suggestions": []
        }
        
        # 分析可能的原因
        if timeout < 30000:  # 小于 30 秒
            diagnosis["possible_causes"].append("超时时间设置过短")
            diagnosis["suggestions"].append(f"增加超时时间到至少 30000ms")
        
        diagnosis["possible_causes"].extend([
            "页面加载缓慢",
            "网络请求超时",
            "元素定位失败",
            "JavaScript 执行时间过长"
        ])
        
        diagnosis["suggestions"].extend([
            "检查页面加载性能",
            "使用 page.waitForLoadState() 等待页面加载完成",
            "优化元素选择器",
            "检查是否有无限循环或长时间运行的脚本"
        ])
        
        return diagnosis

    def extract_error_summary(self, test_result: E2ETestResult) -> str:
        """
        提取 E2E 测试错误摘要
        
        Args:
            test_result: E2E 测试结果
            
        Returns:
            str: 错误摘要
        """
        if test_result.success:
            return "所有 E2E 测试通过"
        
        summary_lines = [
            f"E2E 测试失败: {test_result.failed_tests}/{test_result.total_tests} 个测试失败",
            ""
        ]
        
        # 按浏览器分组显示失败信息
        for browser_name, browser_result in test_result.browser_results.items():
            if browser_result.tests_failed > 0:
                summary_lines.append(f"浏览器: {browser_name}")
                summary_lines.append(f"  失败: {browser_result.tests_failed}/{browser_result.tests_run}")
                
                for failed_test in browser_result.failed_tests:
                    summary_lines.append(f"  - {failed_test.test_name}")
                    summary_lines.append(f"    错误: {failed_test.error_message}")
                    
                    if failed_test.screenshot_path:
                        summary_lines.append(f"    截图: {failed_test.screenshot_path}")
                    if failed_test.video_path:
                        summary_lines.append(f"    视频: {failed_test.video_path}")
                    if failed_test.trace_path:
                        summary_lines.append(f"    追踪: {failed_test.trace_path}")
                
                summary_lines.append("")
        
        # 如果没有浏览器结果，显示通用失败测试详情
        if not test_result.browser_results and test_result.failed_test_details:
            summary_lines.append("失败的测试:")
            for failed_test in test_result.failed_test_details:
                summary_lines.append(f"  - {failed_test.test_name}")
                summary_lines.append(f"    浏览器: {failed_test.browser.value}")
                summary_lines.append(f"    错误: {failed_test.error_message}")
                
                if failed_test.screenshot_path:
                    summary_lines.append(f"    截图: {failed_test.screenshot_path}")
                if failed_test.video_path:
                    summary_lines.append(f"    视频: {failed_test.video_path}")
                if failed_test.trace_path:
                    summary_lines.append(f"    追踪: {failed_test.trace_path}")
                
                summary_lines.append("")
        
        return "\n".join(summary_lines)
    
    def generate_test_report(self, test_result: E2ETestResult) -> Dict[str, any]:
        """
        生成 E2E 测试报告
        
        Args:
            test_result: E2E 测试结果
            
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
            "browsers": {},
            "failed_tests": [],
            "artifacts": {
                "screenshots": len(test_result.screenshots),
                "videos": len(test_result.videos),
                "traces": len(test_result.traces)
            }
        }
        
        # 添加浏览器结果
        for browser_name, browser_result in test_result.browser_results.items():
            report["browsers"][browser_name] = {
                "browser": browser_result.browser.value,
                "version": browser_result.version,
                "success": browser_result.success,
                "tests_run": browser_result.tests_run,
                "tests_passed": browser_result.tests_passed,
                "tests_failed": browser_result.tests_failed,
                "execution_time": browser_result.execution_time
            }
        
        # 添加失败测试详情
        for failed_test in test_result.failed_test_details:
            report["failed_tests"].append({
                "name": failed_test.test_name,
                "browser": failed_test.browser.value,
                "error": failed_test.error_message,
                "screenshot": str(failed_test.screenshot_path) if failed_test.screenshot_path else None,
                "video": str(failed_test.video_path) if failed_test.video_path else None,
                "trace": str(failed_test.trace_path) if failed_test.trace_path else None,
                "retry_count": failed_test.retry_count
            })
        
        return report
