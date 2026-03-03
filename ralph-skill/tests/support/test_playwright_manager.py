"""
Playwright 管理器单元测试
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from ralph.models.enums import BrowserType, DependencyManager
from ralph.models.frontend import (
    E2ETestResult,
    FailedE2ETest,
    PlaywrightConfig,
)
from ralph.support.playwright_manager import PlaywrightManager


@pytest.fixture
def temp_project(tmp_path):
    """创建临时项目目录"""
    project_path = tmp_path / "test_project"
    project_path.mkdir()
    
    # 创建 package.json
    package_json = {
        "name": "test-project",
        "version": "1.0.0",
        "devDependencies": {
            "@playwright/test": "^1.40.0"
        }
    }
    
    with open(project_path / "package.json", "w") as f:
        json.dump(package_json, f)
    
    # 创建测试目录
    test_dir = project_path / "tests" / "e2e"
    test_dir.mkdir(parents=True)
    
    # 创建测试结果目录
    results_dir = project_path / "test-results"
    results_dir.mkdir()
    
    return project_path


@pytest.fixture
def playwright_manager(temp_project):
    """创建 Playwright 管理器实例"""
    return PlaywrightManager(temp_project, DependencyManager.NPM)



class TestPlaywrightManager:
    """Playwright 管理器测试类"""
    
    def test_init(self, playwright_manager, temp_project):
        """测试初始化"""
        assert playwright_manager.project_path == temp_project
        assert playwright_manager.package_manager == DependencyManager.NPM
    
    def test_match_browser_type(self, playwright_manager):
        """测试浏览器类型匹配"""
        assert playwright_manager._match_browser_type("chromium") == BrowserType.CHROMIUM
        assert playwright_manager._match_browser_type("chrome") == BrowserType.CHROMIUM
        assert playwright_manager._match_browser_type("firefox") == BrowserType.FIREFOX
        assert playwright_manager._match_browser_type("webkit") == BrowserType.WEBKIT
        assert playwright_manager._match_browser_type("safari") == BrowserType.WEBKIT
        assert playwright_manager._match_browser_type("unknown") == BrowserType.CHROMIUM
    
    def test_build_test_command_basic(self, playwright_manager):
        """测试基本测试命令构建"""
        config = PlaywrightConfig()
        cmd = playwright_manager._build_test_command(None, config)
        
        assert "npx" in cmd
        assert "playwright" in cmd
        assert "test" in cmd
        assert "--reporter" in cmd
        assert "json" in cmd
    
    def test_build_test_command_with_browsers(self, playwright_manager):
        """测试带浏览器配置的命令构建"""
        config = PlaywrightConfig(
            browsers=[BrowserType.CHROMIUM, BrowserType.FIREFOX]
        )
        cmd = playwright_manager._build_test_command(None, config)
        
        assert "--project" in cmd
        assert "chromium" in cmd
        assert "firefox" in cmd
    
    def test_build_test_command_with_test_files(self, playwright_manager):
        """测试带测试文件的命令构建"""
        config = PlaywrightConfig()
        test_files = ["tests/e2e/login.spec.ts", "tests/e2e/dashboard.spec.ts"]
        cmd = playwright_manager._build_test_command(test_files, config)
        
        assert "tests/e2e/login.spec.ts" in cmd
        assert "tests/e2e/dashboard.spec.ts" in cmd

    
    def test_extract_test_stats_from_text(self, playwright_manager):
        """测试从文本提取测试统计"""
        output = """
        Running 10 tests using 4 workers
        
        5 passed (10s)
        2 failed (5s)
        1 skipped
        """
        
        total, passed, failed, skipped = playwright_manager._extract_test_stats_from_text(output)
        
        assert total == 8  # 5 + 2 + 1
        assert passed == 5
        assert failed == 2
        assert skipped == 1
    
    def test_extract_execution_time_from_text(self, playwright_manager):
        """测试从文本提取执行时间"""
        # 测试秒
        output1 = "5 passed (10s)"
        assert playwright_manager._extract_execution_time_from_text(output1) == 10.0
        
        # 测试分钟
        output2 = "5 passed (1.5m)"
        assert playwright_manager._extract_execution_time_from_text(output2) == 90.0
        
        # 测试毫秒
        output3 = "5 passed (500ms)"
        assert playwright_manager._extract_execution_time_from_text(output3) == 0.5
    
    def test_create_timeout_result(self, playwright_manager):
        """测试创建超时结果"""
        config = PlaywrightConfig()
        result = playwright_manager._create_timeout_result(600, config)
        
        assert result.success is False
        assert result.execution_time == 600
        assert len(result.failed_test_details) == 1
        assert "超时" in result.failed_test_details[0].error_message
    
    def test_create_error_result(self, playwright_manager):
        """测试创建错误结果"""
        config = PlaywrightConfig()
        error_msg = "浏览器启动失败"
        result = playwright_manager._create_error_result(error_msg, config)
        
        assert result.success is False
        assert len(result.failed_test_details) == 1
        assert error_msg in result.failed_test_details[0].error_message

    
    def test_diagnose_browser_launch_failure(self, playwright_manager):
        """测试浏览器启动失败诊断"""
        with patch('subprocess.run') as mock_run:
            # 模拟浏览器未安装
            mock_run.return_value = Mock(returncode=1, stderr="Browser not found")
            
            diagnosis = playwright_manager.diagnose_browser_launch_failure(BrowserType.CHROMIUM)
            
            assert diagnosis["browser"] == "chromium"
            assert diagnosis["installed"] is False
            assert len(diagnosis["suggestions"]) > 0
            assert "install" in diagnosis["suggestions"][0].lower()
    
    def test_diagnose_test_timeout(self, playwright_manager):
        """测试测试超时诊断"""
        diagnosis = playwright_manager.diagnose_test_timeout("login test", 5000)
        
        assert diagnosis["test_name"] == "login test"
        assert diagnosis["timeout"] == 5000
        assert len(diagnosis["possible_causes"]) > 0
        assert len(diagnosis["suggestions"]) > 0
        assert "超时时间设置过短" in diagnosis["possible_causes"]
    
    def test_extract_error_summary_success(self, playwright_manager):
        """测试提取成功测试的错误摘要"""
        result = E2ETestResult(
            success=True,
            test_type="e2e",
            total_tests=10,
            passed_tests=10,
            failed_tests=0,
            skipped_tests=0,
            execution_time=30.0,
            test_output="All tests passed",
            browser_results={},
            screenshots=[],
            videos=[],
            traces=[],
            failed_test_details=[]
        )
        
        summary = playwright_manager.extract_error_summary(result)
        assert "通过" in summary
    
    def test_extract_error_summary_failure(self, playwright_manager):
        """测试提取失败测试的错误摘要"""
        failed_test = FailedE2ETest(
            test_name="login test",
            browser=BrowserType.CHROMIUM,
            error_message="Element not found",
            stack_trace="at login.spec.ts:10",
            screenshot_path="/path/to/screenshot.png",
            video_path=None,
            trace_path=None,
            retry_count=0
        )
        
        result = E2ETestResult(
            success=False,
            test_type="e2e",
            total_tests=10,
            passed_tests=9,
            failed_tests=1,
            skipped_tests=0,
            execution_time=30.0,
            test_output="1 test failed",
            browser_results={},
            screenshots=[],
            videos=[],
            traces=[],
            failed_test_details=[failed_test]
        )
        
        summary = playwright_manager.extract_error_summary(result)
        assert "失败" in summary
        assert "login test" in summary
        assert "Element not found" in summary

    
    def test_generate_test_report(self, playwright_manager):
        """测试生成测试报告"""
        failed_test = FailedE2ETest(
            test_name="login test",
            browser=BrowserType.CHROMIUM,
            error_message="Element not found",
            stack_trace="at login.spec.ts:10",
            screenshot_path="/path/to/screenshot.png",
            video_path="/path/to/video.webm",
            trace_path="/path/to/trace.zip",
            retry_count=1
        )
        
        result = E2ETestResult(
            success=False,
            test_type="e2e",
            total_tests=10,
            passed_tests=9,
            failed_tests=1,
            skipped_tests=0,
            execution_time=30.0,
            test_output="1 test failed",
            browser_results={},
            screenshots=[],
            videos=[],
            traces=[],
            failed_test_details=[failed_test]
        )
        
        report = playwright_manager.generate_test_report(result)
        
        assert report["success"] is False
        assert report["summary"]["total"] == 10
        assert report["summary"]["passed"] == 9
        assert report["summary"]["failed"] == 1
        assert len(report["failed_tests"]) == 1
        assert report["failed_tests"][0]["name"] == "login test"
        assert report["failed_tests"][0]["browser"] == "chromium"
        assert report["failed_tests"][0]["screenshot"] == "/path/to/screenshot.png"
        assert report["failed_tests"][0]["video"] == "/path/to/video.webm"
        assert report["failed_tests"][0]["trace"] == "/path/to/trace.zip"
    
    def test_collect_screenshots(self, playwright_manager, temp_project):
        """测试收集截图"""
        # 创建测试截图文件
        results_dir = temp_project / "test-results"
        screenshot_file = results_dir / "login-test-chromium.png"
        screenshot_file.write_text("fake screenshot")
        
        config = PlaywrightConfig(output_dir="test-results")
        screenshots = playwright_manager._collect_screenshots(config)
        
        assert len(screenshots) > 0
        assert screenshots[0].test_name == "login-test"
        assert screenshots[0].browser == BrowserType.CHROMIUM
    
    def test_collect_videos(self, playwright_manager, temp_project):
        """测试收集视频"""
        # 创建测试视频文件
        results_dir = temp_project / "test-results"
        video_file = results_dir / "dashboard-test-firefox.webm"
        video_file.write_text("fake video")
        
        config = PlaywrightConfig(output_dir="test-results")
        videos = playwright_manager._collect_videos(config)
        
        assert len(videos) > 0
        assert videos[0].test_name == "dashboard-test"
        assert videos[0].browser == BrowserType.FIREFOX
    
    def test_collect_traces(self, playwright_manager, temp_project):
        """测试收集追踪文件"""
        # 创建测试追踪文件
        results_dir = temp_project / "test-results"
        trace_file = results_dir / "checkout-test-webkit.zip"
        trace_file.write_text("fake trace")
        
        config = PlaywrightConfig(output_dir="test-results")
        traces = playwright_manager._collect_traces(config)
        
        assert len(traces) > 0
        assert traces[0].test_name == "checkout-test"
        assert traces[0].browser == BrowserType.WEBKIT
