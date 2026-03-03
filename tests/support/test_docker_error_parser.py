"""
Docker 错误解析器单元测试
"""

import pytest
from ralph.support.docker_error_parser import DockerErrorParser
from ralph.models.docker import DockerError, BuildError


class TestDockerErrorParser:
    """Docker 错误解析器测试类"""

    @pytest.fixture
    def parser(self):
        """创建错误解析器实例"""
        return DockerErrorParser()

    def test_parse_build_errors_syntax(self, parser):
        """测试解析 Dockerfile 语法错误"""
        output = """
        Dockerfile parse error line 5: unknown instruction: INVALID
        """
        
        errors = parser.parse_build_errors(output)
        
        assert len(errors) > 0
        assert errors[0].step_number == 5
        assert errors[0].error_type == "syntax"
        assert "unknown instruction" in errors[0].error_message

    def test_parse_build_errors_file_not_found(self, parser):
        """测试解析文件未找到错误"""
        output = """
        Step 3/5 : COPY app.py /app/
        COPY failed: stat /var/lib/docker/tmp/app.py: no such file or directory
        """
        
        errors = parser.parse_build_errors(output)
        
        assert len(errors) > 0
        assert any(e.error_type == "file_not_found" for e in errors)

    def test_parse_build_errors_step_error(self, parser):
        """测试解析构建步骤错误"""
        output = """
        Step 2/5 : RUN apt-get update
         ---> Running in abc123
        ERROR: failed to solve: process "/bin/sh -c apt-get update" did not complete
        """
        
        errors = parser.parse_build_errors(output)
        
        assert len(errors) > 0

    def test_classify_build_error_file_not_found(self, parser):
        """测试分类文件未找到错误"""
        error_type = parser._classify_build_error("no such file or directory")
        assert error_type == "file_not_found"

    def test_classify_build_error_network(self, parser):
        """测试分类网络错误"""
        error_type = parser._classify_build_error("network connection failed")
        assert error_type == "network"

    def test_classify_build_error_permission(self, parser):
        """测试分类权限错误"""
        error_type = parser._classify_build_error("permission denied")
        assert error_type == "permission"

    def test_parse_container_errors(self, parser):
        """测试解析容器运行时错误"""
        logs = """
        Starting application...
        Error: Cannot find module 'express'
        Exception: Database connection failed
        FATAL: Out of memory
        """
        
        errors = parser.parse_container_errors(logs)
        
        assert len(errors) >= 3
        error_types = [e.error_type for e in errors]
        assert "runtime_error" in error_types
        assert "exception" in error_types
        assert "fatal" in error_types

    def test_parse_network_errors(self, parser):
        """测试解析网络错误"""
        output = """
        Error: network mynetwork not found
        Error: endpoint mycontainer already exists in network bridge
        Error: address already in use
        """
        
        errors = parser.parse_network_errors(output)
        
        assert len(errors) >= 2
        error_types = [e.error_type for e in errors]
        assert "network_not_found" in error_types
        assert "address_in_use" in error_types

    def test_identify_failed_step(self, parser):
        """测试识别失败的构建步骤"""
        output = """
        Step 1/5 : FROM alpine:latest
         ---> abc123
        Step 2/5 : RUN apk add python3
         ---> def456
        Step 3/5 : COPY app.py /app/
        ERROR: failed
        """
        
        step = parser.identify_failed_step(output)
        
        assert step == 3

    def test_suggest_fix_file_not_found(self, parser):
        """测试文件未找到错误的修复建议"""
        error = DockerError(
            error_type="file_not_found",
            error_message="no such file or directory: app.py",
        )
        
        suggestions = parser.suggest_fix(error)
        
        assert len(suggestions) > 0
        assert any("文件路径" in s.description for s in suggestions)

    def test_suggest_fix_network_error(self, parser):
        """测试网络错误的修复建议"""
        error = DockerError(
            error_type="network",
            error_message="network connection timeout",
        )
        
        suggestions = parser.suggest_fix(error)
        
        assert len(suggestions) > 0
        assert any("网络" in s.description for s in suggestions)

    def test_suggest_fix_permission_error(self, parser):
        """测试权限错误的修复建议"""
        error = DockerError(
            error_type="permission",
            error_message="permission denied",
        )
        
        suggestions = parser.suggest_fix(error)
        
        assert len(suggestions) > 0
        assert any("权限" in s.description for s in suggestions)

    def test_suggest_fix_port_in_use(self, parser):
        """测试端口占用错误的修复建议"""
        error = DockerError(
            error_type="port_error",
            error_message="address already in use",
        )
        
        suggestions = parser.suggest_fix(error)
        
        assert len(suggestions) > 0
        assert any("端口" in s.description for s in suggestions)

    def test_prioritize_errors(self, parser):
        """测试错误优先级排序"""
        errors = [
            DockerError(error_type="unknown", error_message="unknown error"),
            DockerError(error_type="syntax", error_message="syntax error"),
            DockerError(error_type="network", error_message="network error"),
            DockerError(error_type="file_not_found", error_message="file not found"),
        ]
        
        sorted_errors = parser.prioritize_errors(errors)
        
        # 语法错误应该排在最前面
        assert sorted_errors[0].error_type == "syntax"
        # 文件未找到应该排在第二
        assert sorted_errors[1].error_type == "file_not_found"
        # unknown 应该排在最后
        assert sorted_errors[-1].error_type == "unknown"

    def test_extract_error_context(self, parser):
        """测试提取错误上下文"""
        error = DockerError(
            error_type="file_not_found",
            error_message="no such file: app.py",
        )
        
        full_output = """
        Step 1/5 : FROM alpine
        Step 2/5 : WORKDIR /app
        Step 3/5 : COPY app.py /app/
        ERROR: no such file: app.py
        Step 4/5 : CMD python app.py
        """
        
        context = parser.extract_error_context(error, full_output)
        
        assert context.error == error
        assert len(context.related_logs) > 0
        assert len(context.suggestions) > 0
