"""
执行模型单元测试
"""

from datetime import datetime

import pytest

from ralph.models import (
    BranchStatus,
    BuildResult,
    ContextStats,
    ErrorCategory,
    ErrorInfo,
    ExecutionResult,
    GitCommit,
    ResourceUsage,
    SecurityViolation,
    TestResult,
)


class TestErrorInfo:
    """测试错误信息"""

    def test_create_error_info(self):
        """测试创建错误信息"""
        error = ErrorInfo(
            type=ErrorCategory.SYNTAX_ERROR,
            message="缺少分号",
            file="main.go",
            line=42,
            column=10
        )
        
        assert error.type == ErrorCategory.SYNTAX_ERROR
        assert error.message == "缺少分号"
        assert error.file == "main.go"
        assert error.line == 42

    def test_error_info_str(self):
        """测试错误信息字符串表示"""
        error = ErrorInfo(
            type=ErrorCategory.COMPILATION_ERROR,
            message="未定义的变量",
            file="main.go",
            line=42,
            column=10
        )
        
        error_str = str(error)
        assert "compilation_error" in error_str
        assert "未定义的变量" in error_str
        assert "main.go:42:10" in error_str

    def test_error_info_without_location(self):
        """测试无位置信息的错误"""
        error = ErrorInfo(
            type=ErrorCategory.RUNTIME_ERROR,
            message="空指针异常"
        )
        
        error_str = str(error)
        assert "runtime_error" in error_str
        assert "空指针异常" in error_str


class TestResourceUsage:
    """测试资源使用情况"""

    def test_create_resource_usage(self):
        """测试创建资源使用情况"""
        usage = ResourceUsage(
            cpu_percent=50.0,
            memory_usage_mb=512.0,
            memory_limit_mb=1024.0,
            disk_usage_mb=100.0,
            execution_time=10.5
        )
        
        assert usage.cpu_percent == 50.0
        assert usage.memory_usage_mb == 512.0
        assert usage.execution_time == 10.5

    def test_get_memory_percent(self):
        """测试获取内存使用百分比"""
        usage = ResourceUsage(
            memory_usage_mb=512.0,
            memory_limit_mb=1024.0
        )
        
        assert usage.get_memory_percent() == 50.0

    def test_get_memory_percent_no_limit(self):
        """测试无内存限制时的百分比"""
        usage = ResourceUsage(
            memory_usage_mb=512.0,
            memory_limit_mb=0.0
        )
        
        assert usage.get_memory_percent() == 0.0


class TestSecurityViolation:
    """测试安全违规"""

    def test_create_security_violation(self):
        """测试创建安全违规"""
        violation = SecurityViolation(
            type="file_access",
            message="尝试访问 /etc/passwd",
            severity="high",
            blocked=True
        )
        
        assert violation.type == "file_access"
        assert violation.severity == "high"
        assert violation.blocked is True


class TestExecutionResult:
    """测试执行结果"""

    def test_create_execution_result(self):
        """测试创建执行结果"""
        result = ExecutionResult(
            success=True,
            output="执行成功",
            execution_time=10.5
        )
        
        assert result.success is True
        assert result.output == "执行成功"
        assert result.execution_time == 10.5
        assert result.exit_code == 0

    def test_add_error(self):
        """测试添加错误"""
        result = ExecutionResult(
            success=True,
            output="执行中"
        )
        
        error = ErrorInfo(
            type=ErrorCategory.SYNTAX_ERROR,
            message="语法错误"
        )
        
        result.add_error(error)
        
        assert result.success is False
        assert len(result.errors) == 1
        assert result.has_errors() is True

    def test_get_error_summary(self):
        """测试获取错误摘要"""
        result = ExecutionResult(
            success=False,
            output="执行失败"
        )
        
        result.add_error(ErrorInfo(
            type=ErrorCategory.SYNTAX_ERROR,
            message="错误1"
        ))
        result.add_error(ErrorInfo(
            type=ErrorCategory.SYNTAX_ERROR,
            message="错误2"
        ))
        result.add_error(ErrorInfo(
            type=ErrorCategory.RUNTIME_ERROR,
            message="错误3"
        ))
        
        summary = result.get_error_summary()
        assert "2 个 syntax_error" in summary
        assert "1 个 runtime_error" in summary

    def test_get_error_summary_no_errors(self):
        """测试无错误时的摘要"""
        result = ExecutionResult(
            success=True,
            output="成功"
        )
        
        assert result.get_error_summary() == "无错误"


class TestTestResult:
    """测试测试结果"""

    def test_create_test_result(self):
        """测试创建测试结果"""
        result = TestResult(
            success=True,
            test_type="unit",
            total_tests=10,
            passed_tests=9,
            failed_tests=1,
            skipped_tests=0,
            execution_time=5.5,
            coverage=85.5
        )
        
        assert result.success is True
        assert result.total_tests == 10
        assert result.passed_tests == 9
        assert result.coverage == 85.5

    def test_get_pass_rate(self):
        """测试获取通过率"""
        result = TestResult(
            success=True,
            test_type="unit",
            total_tests=10,
            passed_tests=8,
            failed_tests=2,
            skipped_tests=0,
            execution_time=5.5
        )
        
        assert result.get_pass_rate() == 80.0

    def test_get_pass_rate_no_tests(self):
        """测试无测试时的通过率"""
        result = TestResult(
            success=True,
            test_type="unit",
            total_tests=0,
            passed_tests=0,
            failed_tests=0,
            skipped_tests=0,
            execution_time=0.0
        )
        
        assert result.get_pass_rate() == 0.0


class TestBuildResult:
    """测试构建结果"""

    def test_create_build_result(self):
        """测试创建构建结果"""
        result = BuildResult(
            success=True,
            build_time=30.5,
            output="构建成功",
            artifacts=["app.exe", "app.dll"]
        )
        
        assert result.success is True
        assert result.build_time == 30.5
        assert len(result.artifacts) == 2

    def test_has_warnings(self):
        """测试是否有警告"""
        result = BuildResult(
            success=True,
            build_time=30.5,
            output="构建成功",
            warnings=["警告: 未使用的变量"]
        )
        
        assert result.has_warnings() is True

    def test_no_warnings(self):
        """测试无警告"""
        result = BuildResult(
            success=True,
            build_time=30.5,
            output="构建成功"
        )
        
        assert result.has_warnings() is False


class TestGitCommit:
    """测试 Git 提交信息"""

    def test_create_git_commit(self):
        """测试创建 Git 提交"""
        commit = GitCommit(
            hash="abc123def456",
            message="feat: 添加新功能",
            author="张三",
            timestamp=datetime.now(),
            files_changed=["main.go", "utils.go"]
        )
        
        assert commit.hash == "abc123def456"
        assert commit.message == "feat: 添加新功能"
        assert len(commit.files_changed) == 2

    def test_git_commit_str(self):
        """测试 Git 提交字符串表示"""
        commit = GitCommit(
            hash="abc123def456",
            message="feat: 添加新功能",
            author="张三",
            timestamp=datetime.now()
        )
        
        commit_str = str(commit)
        assert "abc123d" in commit_str
        assert "feat: 添加新功能" in commit_str


class TestBranchStatus:
    """测试分支状态"""

    def test_create_branch_status(self):
        """测试创建分支状态"""
        commit = GitCommit(
            hash="abc123",
            message="最新提交",
            author="张三",
            timestamp=datetime.now()
        )
        
        status = BranchStatus(
            name="main",
            current=True,
            commits_ahead=2,
            commits_behind=0,
            has_uncommitted_changes=False,
            last_commit=commit
        )
        
        assert status.name == "main"
        assert status.current is True
        assert status.commits_ahead == 2
        assert status.last_commit is not None


class TestContextStats:
    """测试上下文统计"""

    def test_create_context_stats(self):
        """测试创建上下文统计"""
        stats = ContextStats(
            total_size=15000,
            truncated=True,
            truncated_size=5000,
            error_count=3,
            warning_count=5,
            preserved_errors=2
        )
        
        assert stats.total_size == 15000
        assert stats.truncated is True
        assert stats.truncated_size == 5000
        assert stats.error_count == 3
