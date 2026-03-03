"""
Vitest 管理器单元测试
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from ralph.models.enums import DependencyManager
from ralph.models.frontend import VitestConfig
from ralph.support.vitest_manager import VitestManager


@pytest.fixture
def temp_project(tmp_path):
    """创建临时项目目录"""
    project_path = tmp_path / "test-project"
    project_path.mkdir()
    
    # 创建 package.json
    package_json = {
        "name": "test-project",
        "version": "1.0.0",
        "scripts": {
            "test": "vitest"
        },
        "devDependencies": {
            "vitest": "^1.0.0"
        }
    }
    
    with open(project_path / "package.json", "w") as f:
        json.dump(package_json, f)
    
    return project_path


@pytest.fixture
def vitest_manager(temp_project):
    """创建 Vitest 管理器实例"""
    return VitestManager(temp_project, DependencyManager.NPM)


class TestVitestManager:
    """Vitest 管理器测试类"""
    
    def test_init(self, temp_project):
        """测试初始化"""
        manager = VitestManager(temp_project, DependencyManager.NPM)
        
        assert manager.project_path == temp_project
        assert manager.package_manager == DependencyManager.NPM
    
    def test_build_test_command_npm(self, vitest_manager):
        """测试构建 npm 测试命令"""
        config = VitestConfig()
        cmd = vitest_manager._build_test_command(None, config)
        
        assert cmd[0] == "npm"
        assert cmd[1] == "run"
        assert cmd[2] == "test"
        assert "--run" in cmd
        assert "--coverage" in cmd
    
    def test_build_test_command_yarn(self, temp_project):
        """测试构建 yarn 测试命令"""
        manager = VitestManager(temp_project, DependencyManager.YARN)
        config = VitestConfig(coverage=False)
        cmd = manager._build_test_command(None, config)
        
        assert cmd[0] == "yarn"
        assert cmd[1] == "test"
        assert "--run" in cmd
        assert "--coverage" not in cmd
    
    def test_build_test_command_with_test_path(self, vitest_manager):
        """测试构建带测试路径的命令"""
        config = VitestConfig()
        cmd = vitest_manager._build_test_command("src/components/Button.test.ts", config)
        
        assert "src/components/Button.test.ts" in cmd
    
    def test_extract_test_stats_all_passed(self, vitest_manager):
        """测试提取测试统计信息 - 全部通过"""
        output = """
Test Files  2 passed (2)
     Tests  10 passed (10)
  Start at  12:00:00
  Duration  1.23s (in thread 456ms, 268.42% of cpu)
"""
        
        total, passed, failed, skipped = vitest_manager._extract_test_stats(output)
        
        assert total == 10
        assert passed == 10
        assert failed == 0
        assert skipped == 0
    
    def test_extract_test_stats_with_failures(self, vitest_manager):
        """测试提取测试统计信息 - 有失败"""
        output = """
Test Files  1 failed | 1 passed (2)
     Tests  3 failed | 7 passed (10)
  Start at  12:00:00
  Duration  1.23s
"""
        
        total, passed, failed, skipped = vitest_manager._extract_test_stats(output)
        
        assert total == 10
        assert passed == 7
        assert failed == 3
        assert skipped == 0
    
    def test_extract_test_stats_with_skipped(self, vitest_manager):
        """测试提取测试统计信息 - 有跳过"""
        output = """
Test Files  2 passed (2)
     Tests  8 passed | 2 skipped (10)
  Start at  12:00:00
  Duration  1.23s
"""
        
        total, passed, failed, skipped = vitest_manager._extract_test_stats(output)
        
        assert total == 10
        assert passed == 8
        assert failed == 0
        assert skipped == 2
    
    def test_extract_execution_time_seconds(self, vitest_manager):
        """测试提取执行时间 - 秒"""
        output = "Duration  1.23s (in thread 456ms, 268.42% of cpu)"
        
        time = vitest_manager._extract_execution_time(output)
        
        assert time == 1.23
    
    def test_extract_execution_time_milliseconds(self, vitest_manager):
        """测试提取执行时间 - 毫秒"""
        output = "Duration  456ms"
        
        time = vitest_manager._extract_execution_time(output)
        
        assert time == 0.456
    
    def test_extract_execution_time_not_found(self, vitest_manager):
        """测试提取执行时间 - 未找到"""
        output = "No duration information"
        
        time = vitest_manager._extract_execution_time(output)
        
        assert time == 0.0
    
    def test_extract_line_number(self, vitest_manager):
        """测试提取行号"""
        stack_trace = "❯ src/components/Button.test.ts:15:7"
        
        line_number = vitest_manager._extract_line_number(stack_trace)
        
        assert line_number == 15
    
    def test_extract_line_number_not_found(self, vitest_manager):
        """测试提取行号 - 未找到"""
        stack_trace = "Some error without line number"
        
        line_number = vitest_manager._extract_line_number(stack_trace)
        
        assert line_number is None
    
    @patch('subprocess.run')
    def test_run_tests_success(self, mock_run, vitest_manager):
        """测试运行测试 - 成功"""
        # 模拟成功的测试输出
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = """
Test Files  1 passed (1)
     Tests  5 passed (5)
  Duration  1.23s
"""
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        result = vitest_manager.run_tests()
        
        assert result.success is True
        assert result.total_tests == 5
        assert result.passed_tests == 5
        assert result.failed_tests == 0
        assert result.execution_time == 1.23
    
    @patch('subprocess.run')
    def test_run_tests_with_failures(self, mock_run, vitest_manager):
        """测试运行测试 - 有失败"""
        # 模拟失败的测试输出
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = """
❯ src/components/Button.test.ts (1)
  ❯ Button component (1)
    × should render correctly
      AssertionError: expected '<button>Click</button>' to equal '<button>Submit</button>'
      
      - Expected
      + Received
      
      - <button>Submit</button>
      + <button>Click</button>
      
      ❯ src/components/Button.test.ts:15:7

Test Files  1 failed (1)
     Tests  1 failed | 4 passed (5)
  Duration  1.23s
"""
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        result = vitest_manager.run_tests()
        
        assert result.success is False
        assert result.total_tests == 5
        assert result.passed_tests == 4
        assert result.failed_tests == 1
        assert len(result.failed_test_details) > 0
    
    @patch('subprocess.run')
    def test_run_tests_timeout(self, mock_run, vitest_manager):
        """测试运行测试 - 超时"""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="npm test", timeout=300)
        
        result = vitest_manager.run_tests(timeout=300)
        
        assert result.success is False
        assert "超时" in result.test_output
        assert len(result.failed_test_details) == 1
        assert result.failed_test_details[0].test_name == "timeout"
    
    @patch('subprocess.run')
    def test_run_tests_exception(self, mock_run, vitest_manager):
        """测试运行测试 - 异常"""
        mock_run.side_effect = Exception("Test execution failed")
        
        result = vitest_manager.run_tests()
        
        assert result.success is False
        assert "Test execution failed" in result.test_output
        assert len(result.failed_test_details) == 1
    
    def test_extract_error_summary_success(self, vitest_manager):
        """测试提取错误摘要 - 成功"""
        from ralph.models.frontend import TestResult
        
        test_result = TestResult(
            success=True,
            test_type="unit",
            total_tests=10,
            passed_tests=10,
            failed_tests=0,
            skipped_tests=0,
            execution_time=1.23,
            test_output=""
        )
        
        summary = vitest_manager.extract_error_summary(test_result)
        
        assert "所有测试通过" in summary
    
    def test_extract_error_summary_with_failures(self, vitest_manager):
        """测试提取错误摘要 - 有失败"""
        from ralph.models.frontend import FailedTestDetail, TestResult
        
        test_result = TestResult(
            success=False,
            test_type="unit",
            total_tests=10,
            passed_tests=8,
            failed_tests=2,
            skipped_tests=0,
            execution_time=1.23,
            test_output="",
            failed_test_details=[
                FailedTestDetail(
                    test_name="should render correctly",
                    test_file="src/components/Button.test.ts",
                    error_message="AssertionError: expected '<button>Click</button>' to equal '<button>Submit</button>'",
                    stack_trace="",
                    line_number=15,
                    expected="<button>Submit</button>",
                    actual="<button>Click</button>"
                )
            ]
        )
        
        summary = vitest_manager.extract_error_summary(test_result)
        
        assert "测试失败: 2/10" in summary
        assert "should render correctly" in summary
        assert "src/components/Button.test.ts" in summary
        assert "行号: 15" in summary
    
    def test_generate_test_report(self, vitest_manager):
        """测试生成测试报告"""
        from ralph.models.frontend import FailedTestDetail, TestResult
        
        test_result = TestResult(
            success=False,
            test_type="unit",
            total_tests=10,
            passed_tests=8,
            failed_tests=2,
            skipped_tests=0,
            execution_time=1.23,
            test_output="",
            failed_test_details=[
                FailedTestDetail(
                    test_name="should render correctly",
                    test_file="src/components/Button.test.ts",
                    error_message="AssertionError",
                    stack_trace="",
                    line_number=15
                )
            ]
        )
        
        report = vitest_manager.generate_test_report(test_result)
        
        assert report["success"] is False
        assert report["summary"]["total"] == 10
        assert report["summary"]["passed"] == 8
        assert report["summary"]["failed"] == 2
        assert len(report["failed_tests"]) == 1
        assert report["failed_tests"][0]["name"] == "should render correctly"
    
    def test_parse_coverage_report_not_found(self, vitest_manager):
        """测试解析覆盖率报告 - 文件不存在"""
        coverage = vitest_manager._parse_coverage_report()
        
        assert coverage is None
    
    def test_parse_coverage_report_success(self, vitest_manager, temp_project):
        """测试解析覆盖率报告 - 成功"""
        # 创建覆盖率报告目录和文件
        coverage_dir = temp_project / "coverage"
        coverage_dir.mkdir()
        
        coverage_data = {
            "src/components/Button.vue": {
                "s": {"1": 10, "2": 10, "3": 0, "4": 5},
                "b": {"1": [10, 5], "2": [0, 10]},
                "f": {"1": 10, "2": 0}
            }
        }
        
        with open(coverage_dir / "coverage-final.json", "w") as f:
            json.dump(coverage_data, f)
        
        coverage = vitest_manager._parse_coverage_report()
        
        assert coverage is not None
        assert coverage.total_coverage > 0
        assert coverage.line_coverage > 0
        assert len(coverage.file_coverage) == 1
        assert "src/components/Button.vue" in coverage.file_coverage


class TestVitestConfig:
    """Vitest 配置测试类"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = VitestConfig()
        
        assert config.test_dir == "tests"
        assert config.coverage is True
        assert config.coverage_threshold == 80.0
        assert "default" in config.reporters
        assert "json" in config.reporters
        assert config.globals is True
        assert config.environment == "jsdom"
        assert config.timeout == 5000
        assert config.threads is True
        assert config.isolate is True
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = VitestConfig(
            test_dir="test",
            coverage=False,
            coverage_threshold=90.0,
            reporters=["verbose"],
            environment="node",
            timeout=10000
        )
        
        assert config.test_dir == "test"
        assert config.coverage is False
        assert config.coverage_threshold == 90.0
        assert config.reporters == ["verbose"]
        assert config.environment == "node"
        assert config.timeout == 10000
