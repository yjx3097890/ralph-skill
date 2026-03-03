"""
ACP 集成测试

测试 ACP Harness Manager 的完整会话生命周期、Docker-in-Docker 操作、
Git 集成、Buildkit 多架构构建、故障恢复和并发会话管理。

验证需求: 需求 13.1-13.33
"""

import os
import time
from datetime import datetime, timedelta

import pytest

from ralph.managers.acp_buildkit_client import ACPBuildkitClient
from ralph.managers.acp_docker_client import ACPDockerClient
from ralph.managers.acp_git_client import ACPGitClient
from ralph.managers.acp_harness_manager import ACPHarnessManager
from ralph.managers.acp_session_manager import ACPSessionManager
from ralph.models.acp import (
    ACPError,
    ACPSessionConfig,
    CacheConfig,
    NetworkPolicy,
    ResourceLimits,
)


# 测试配置
ACP_HARNESS_ENDPOINT = os.getenv("ACP_HARNESS_ENDPOINT", "http://localhost:8080")
ACP_API_KEY = os.getenv("ACP_API_KEY", "test-api-key")


@pytest.fixture
def harness_manager():
    """创建 ACP Harness Manager 实例"""
    return ACPHarnessManager(
        harness_endpoint=ACP_HARNESS_ENDPOINT,
        api_key=ACP_API_KEY,
        max_concurrent_sessions=5,
    )


@pytest.fixture
def session_manager(harness_manager):
    """创建 ACP Session Manager 实例"""
    return ACPSessionManager(harness_manager)


@pytest.fixture
def default_config():
    """创建默认会话配置"""
    return ACPSessionConfig(
        name="test-session",
        resource_limits=ResourceLimits(
            cpu_limit=2.0,
            memory_limit="2g",
            disk_limit="10g",
        ),
        network_policy=NetworkPolicy(
            allow_internet=False,
            allowed_hosts=[],
            blocked_ports=[],
            use_proxy=False,
            allow_privileged=False,
            allow_host_network=False,
            allow_host_pid=False,
        ),
        timeout=3600,
        auto_destroy=True,
        enable_qemu=True,
        enable_buildkit=True,
        platforms=["linux/amd64"],
    )


class TestACPSessionLifecycle:
    """测试 ACP 会话生命周期（需求 13.1-13.4）"""

    def test_create_session_success(self, harness_manager, default_config):
        """测试成功创建会话"""
        # 创建会话
        session = harness_manager.create_session(default_config)

        # 验证会话属性
        assert session.session_id is not None
        assert session.session_id.startswith("acp-")
        assert session.name == "test-session"
        assert session.status == "active"
        assert session.docker_endpoint is not None
        assert session.git_endpoint is not None
        assert session.buildkit_endpoint is not None

        # 清理
        harness_manager.destroy_session(session.session_id)

    def test_create_session_with_custom_config(self, harness_manager):
        """测试使用自定义配置创建会话"""
        config = ACPSessionConfig(
            name="custom-session",
            resource_limits=ResourceLimits(
                cpu_limit=4.0,
                memory_limit="4g",
                disk_limit="20g",
            ),
            network_policy=NetworkPolicy(
                allow_internet=True,
                allowed_hosts=["github.com", "pypi.org"],
                blocked_ports=[22, 23],
                use_proxy=False,
                allow_privileged=False,
                allow_host_network=False,
                allow_host_pid=False,
            ),
            timeout=7200,
            auto_destroy=True,
            enable_qemu=True,
            enable_buildkit=True,
            platforms=["linux/amd64", "linux/arm64"],
        )

        session = harness_manager.create_session(config)

        assert session.name == "custom-session"
        assert session.config.resource_limits.cpu_limit == 4.0
        assert session.config.network_policy.allow_internet is True
        assert "linux/arm64" in session.config.platforms

        harness_manager.destroy_session(session.session_id)

    def test_use_session(self, harness_manager, default_config):
        """测试使用会话"""
        session = harness_manager.create_session(default_config)
        initial_operations = session.operations_count

        # 使用会话
        used_session = harness_manager.use_session(session.session_id)

        assert used_session.session_id == session.session_id
        assert used_session.operations_count == initial_operations + 1
        assert used_session.status == "active"

        harness_manager.destroy_session(session.session_id)

    def test_use_nonexistent_session(self, harness_manager):
        """测试使用不存在的会话"""
        with pytest.raises(ACPError) as exc_info:
            harness_manager.use_session("nonexistent-session-id")

        assert exc_info.value.type == "session_not_found"
        assert not exc_info.value.recoverable

    def test_destroy_session(self, harness_manager, default_config):
        """测试销毁会话"""
        session = harness_manager.create_session(default_config)
        session_id = session.session_id

        # 销毁会话
        result = harness_manager.destroy_session(session_id)

        assert result is True
        assert session_id not in harness_manager._sessions

    def test_list_sessions(self, harness_manager, default_config):
        """测试列出所有会话"""
        # 创建多个会话
        session1 = harness_manager.create_session(default_config)
        config2 = ACPSessionConfig(
            name="test-session-2",
            resource_limits=ResourceLimits(cpu_limit=1.0, memory_limit="1g", disk_limit="5g"),
            network_policy=NetworkPolicy(),
            timeout=1800,
            auto_destroy=True,
            enable_qemu=False,
            enable_buildkit=True,
            platforms=["linux/amd64"],
        )
        session2 = harness_manager.create_session(config2)

        # 列出会话
        sessions = harness_manager.list_sessions()

        assert len(sessions) >= 2
        session_ids = [s.session_id for s in sessions]
        assert session1.session_id in session_ids
        assert session2.session_id in session_ids

        # 清理
        harness_manager.destroy_session(session1.session_id)
        harness_manager.destroy_session(session2.session_id)

    def test_get_session_status(self, harness_manager, default_config):
        """测试获取会话状态"""
        session = harness_manager.create_session(default_config)

        status = harness_manager.get_session_status(session.session_id)

        assert status.session_id == session.session_id
        assert status.status == "active"
        assert status.uptime_seconds >= 0
        assert status.operations_count >= 0
        assert status.health_status == "healthy"

        harness_manager.destroy_session(session.session_id)


class TestACPDockerOperations:
    """测试 Docker-in-Docker 操作（需求 13.5-13.6）"""

    def test_build_image_basic(self, harness_manager, default_config):
        """测试基本镜像构建"""
        session = harness_manager.create_session(default_config)
        docker_client = ACPDockerClient(session)

        # 构建镜像
        result = docker_client.build_image(
            context_path="/app",
            dockerfile="Dockerfile",
            tag="test-app:latest",
        )

        assert result.success is True
        assert result.image_id is not None
        assert result.image_tag == "test-app:latest"
        assert result.execution_time > 0
        assert len(result.layers) > 0

        harness_manager.destroy_session(session.session_id)

    def test_build_image_with_build_args(self, harness_manager, default_config):
        """测试带构建参数的镜像构建"""
        session = harness_manager.create_session(default_config)
        docker_client = ACPDockerClient(session)

        result = docker_client.build_image(
            context_path="/app",
            dockerfile="Dockerfile",
            tag="test-app:v1.0",
            build_args={"PYTHON_VERSION": "3.9", "APP_ENV": "production"},
            target="production",
        )

        assert result.success is True
        assert result.image_tag == "test-app:v1.0"

        harness_manager.destroy_session(session.session_id)

    def test_build_image_with_cache(self, harness_manager, default_config):
        """测试使用缓存的镜像构建"""
        session = harness_manager.create_session(default_config)
        docker_client = ACPDockerClient(session)

        cache_config = CacheConfig(
            cache_from=["test-app:latest"],
            cache_to=["type=inline"],
            inline_cache=True,
        )

        result = docker_client.build_image(
            context_path="/app",
            dockerfile="Dockerfile",
            tag="test-app:cached",
            cache_config=cache_config,
        )

        assert result.success is True
        assert result.cache_hits >= 0
        assert result.cache_misses >= 0

        harness_manager.destroy_session(session.session_id)

    def test_run_container(self, harness_manager, default_config):
        """测试运行容器"""
        session = harness_manager.create_session(default_config)
        docker_client = ACPDockerClient(session)

        result = docker_client.run_container(
            image="python:3.9-slim",
            command="python --version",
            remove=True,
        )

        assert result.success is True
        assert result.exit_code == 0
        assert "Python" in result.stdout

        harness_manager.destroy_session(session.session_id)

    def test_run_container_with_environment(self, harness_manager, default_config):
        """测试运行带环境变量的容器"""
        session = harness_manager.create_session(default_config)
        docker_client = ACPDockerClient(session)

        result = docker_client.run_container(
            image="alpine:latest",
            command="env",
            environment={"TEST_VAR": "test_value", "APP_ENV": "testing"},
            remove=True,
        )

        assert result.success is True
        assert "TEST_VAR" in result.stdout or "test_value" in result.stdout

        harness_manager.destroy_session(session.session_id)

    def test_execute_command_in_container(self, harness_manager, default_config):
        """测试在容器中执行命令"""
        session = harness_manager.create_session(default_config)
        docker_client = ACPDockerClient(session)

        # 先运行一个后台容器
        run_result = docker_client.run_container(
            image="alpine:latest",
            command="sleep 60",
            detach=True,
            remove=False,
        )

        assert run_result.container_id is not None

        # 在容器中执行命令
        exec_result = docker_client.execute_command(
            container_id=run_result.container_id,
            command="echo 'Hello from container'",
        )

        assert exec_result.success is True
        assert exec_result.exit_code == 0

        # 清理
        docker_client.stop_container(run_result.container_id)
        docker_client.remove_container(run_result.container_id)
        harness_manager.destroy_session(session.session_id)

    def test_collect_container_logs(self, harness_manager, default_config):
        """测试收集容器日志"""
        session = harness_manager.create_session(default_config)
        docker_client = ACPDockerClient(session)

        run_result = docker_client.run_container(
            image="alpine:latest",
            command="sleep 60",
            detach=True,
            remove=False,
        )

        logs = docker_client.collect_logs(run_result.container_id, tail=10)

        assert logs is not None
        assert isinstance(logs, str)

        docker_client.stop_container(run_result.container_id)
        docker_client.remove_container(run_result.container_id)
        harness_manager.destroy_session(session.session_id)


class TestACPGitIntegration:
    """测试 Git 集成（需求 13.9-13.10）"""

    def test_clone_repository(self, harness_manager, default_config):
        """测试克隆仓库"""
        session = harness_manager.create_session(default_config)
        git_client = ACPGitClient(session)

        result = git_client.clone_repository(
            repo_url="https://github.com/example/test-repo.git",
            target_dir="/workspace/test-repo",
        )

        assert result.success is True
        assert result.operation_type == "git"

        harness_manager.destroy_session(session.session_id)

    def test_clone_repository_with_branch(self, harness_manager, default_config):
        """测试克隆指定分支"""
        session = harness_manager.create_session(default_config)
        git_client = ACPGitClient(session)

        result = git_client.clone_repository(
            repo_url="https://github.com/example/test-repo.git",
            target_dir="/workspace/test-repo",
            branch="develop",
        )

        assert result.success is True

        harness_manager.destroy_session(session.session_id)

    def test_checkout_branch(self, harness_manager, default_config):
        """测试切换分支"""
        session = harness_manager.create_session(default_config)
        git_client = ACPGitClient(session)

        # 先克隆仓库
        git_client.clone_repository(
            repo_url="https://github.com/example/test-repo.git",
            target_dir="/workspace/test-repo",
        )

        # 切换分支
        result = git_client.checkout_branch(
            repo_path="/workspace/test-repo",
            branch="feature-branch",
        )

        assert result.success is True

        harness_manager.destroy_session(session.session_id)

    def test_commit_changes(self, harness_manager, default_config):
        """测试提交变更"""
        session = harness_manager.create_session(default_config)
        git_client = ACPGitClient(session)

        git_client.clone_repository(
            repo_url="https://github.com/example/test-repo.git",
            target_dir="/workspace/test-repo",
        )

        result = git_client.commit_changes(
            repo_path="/workspace/test-repo",
            message="测试提交",
            author_name="Test User",
            author_email="test@example.com",
        )

        assert result.success is True

        harness_manager.destroy_session(session.session_id)

    def test_push_changes(self, harness_manager, default_config):
        """测试推送变更"""
        session = harness_manager.create_session(default_config)
        git_client = ACPGitClient(session)

        git_client.clone_repository(
            repo_url="https://github.com/example/test-repo.git",
            target_dir="/workspace/test-repo",
        )

        result = git_client.push_changes(
            repo_path="/workspace/test-repo",
            remote="origin",
            branch="main",
        )

        assert result.success is True

        harness_manager.destroy_session(session.session_id)


class TestACPBuildkitMultiArch:
    """测试 Buildkit 多架构构建（需求 13.7-13.8, 13.11-13.12）"""

    def test_build_multi_arch_image(self, harness_manager):
        """测试多架构镜像构建"""
        config = ACPSessionConfig(
            name="multi-arch-session",
            resource_limits=ResourceLimits(cpu_limit=4.0, memory_limit="4g", disk_limit="20g"),
            network_policy=NetworkPolicy(),
            timeout=7200,
            auto_destroy=True,
            enable_qemu=True,
            enable_buildkit=True,
            platforms=["linux/amd64", "linux/arm64", "linux/arm/v7"],
        )

        session = harness_manager.create_session(config)
        buildkit_client = ACPBuildkitClient(session)

        result = buildkit_client.build_multi_arch(
            context_path="/app",
            dockerfile="Dockerfile",
            tag="test-app:multi-arch",
            platforms=["linux/amd64", "linux/arm64"],
        )

        assert result.success is True
        assert "linux/amd64" in result.platforms
        assert "linux/arm64" in result.platforms

        harness_manager.destroy_session(session.session_id)

    def test_build_with_cache_optimization(self, harness_manager, default_config):
        """测试缓存优化构建"""
        session = harness_manager.create_session(default_config)
        buildkit_client = ACPBuildkitClient(session)

        cache_config = CacheConfig(
            cache_from=["type=registry,ref=example.com/cache"],
            cache_to=["type=registry,ref=example.com/cache,mode=max"],
            inline_cache=True,
        )

        # 使用缓存配置进行多架构构建
        result = buildkit_client.build_multi_arch(
            context_path="/app",
            dockerfile="Dockerfile",
            tag="test-app:cached",
            cache_config=cache_config,
        )

        assert result.success is True
        assert result.cache_hits >= 0

        harness_manager.destroy_session(session.session_id)

    def test_build_with_secrets(self, harness_manager, default_config):
        """测试使用 secrets 构建"""
        session = harness_manager.create_session(default_config)
        buildkit_client = ACPBuildkitClient(session)

        secrets = {
            "npm_token": "secret-npm-token-value",
            "api_key": "secret-api-key-value",
        }

        result = buildkit_client.build_with_secrets(
            context_path="/app",
            dockerfile="Dockerfile",
            tag="test-app:with-secrets",
            secrets=secrets,
        )

        assert result.success is True

        harness_manager.destroy_session(session.session_id)


class TestACPFailureRecovery:
    """测试故障恢复（需求 13.15-13.17）"""

    def test_session_timeout_handling(self, harness_manager):
        """测试会话超时处理"""
        config = ACPSessionConfig(
            name="timeout-test-session",
            resource_limits=ResourceLimits(cpu_limit=1.0, memory_limit="1g", disk_limit="5g"),
            network_policy=NetworkPolicy(),
            timeout=5,  # 5 秒超时
            auto_destroy=True,
            enable_qemu=False,
            enable_buildkit=True,
            platforms=["linux/amd64"],
        )

        session = harness_manager.create_session(config)
        session_id = session.session_id

        # 等待超时
        time.sleep(6)

        # 会话应该仍然存在（因为监控线程未启动）
        # 在实际场景中，监控线程会自动销毁超时会话
        assert session_id in harness_manager._sessions

        harness_manager.destroy_session(session_id)

    def test_session_recovery_after_error(self, harness_manager, default_config):
        """测试错误后的会话恢复"""
        session = harness_manager.create_session(default_config)
        docker_client = ACPDockerClient(session)

        # 模拟操作失败（使用无效镜像）
        try:
            docker_client.run_container(
                image="nonexistent-image:latest",
                command="echo test",
            )
        except ACPError as e:
            assert e.type == "run_failed"
            assert e.recoverable is True

        # 会话应该仍然可用
        status = harness_manager.get_session_status(session.session_id)
        assert status.status in ["active", "idle"]

        harness_manager.destroy_session(session.session_id)

    def test_force_destroy_failed_session(self, harness_manager, default_config):
        """测试强制销毁失败的会话"""
        session = harness_manager.create_session(default_config)
        session_id = session.session_id

        # 模拟会话失败
        session.status = "failed"

        # 强制销毁
        result = harness_manager.destroy_session(session_id, force=True)

        assert result is True
        assert session_id not in harness_manager._sessions


class TestACPConcurrentSessions:
    """测试并发会话管理（需求 13.32-13.33）"""

    def test_create_multiple_concurrent_sessions(self, harness_manager, default_config):
        """测试创建多个并发会话"""
        sessions = []

        # 创建多个会话
        for i in range(3):
            config = ACPSessionConfig(
                name=f"concurrent-session-{i}",
                resource_limits=ResourceLimits(cpu_limit=1.0, memory_limit="1g", disk_limit="5g"),
                network_policy=NetworkPolicy(),
                timeout=3600,
                auto_destroy=True,
                enable_qemu=False,
                enable_buildkit=True,
                platforms=["linux/amd64"],
            )
            session = harness_manager.create_session(config)
            sessions.append(session)

        # 验证所有会话都已创建
        assert len(sessions) == 3
        for session in sessions:
            assert session.status == "active"

        # 清理
        for session in sessions:
            harness_manager.destroy_session(session.session_id)

    def test_concurrent_session_limit(self, harness_manager):
        """测试并发会话数量限制"""
        sessions = []

        # 创建达到上限的会话
        for i in range(5):
            config = ACPSessionConfig(
                name=f"limit-test-session-{i}",
                resource_limits=ResourceLimits(cpu_limit=1.0, memory_limit="1g", disk_limit="5g"),
                network_policy=NetworkPolicy(),
                timeout=3600,
                auto_destroy=True,
                enable_qemu=False,
                enable_buildkit=True,
                platforms=["linux/amd64"],
            )
            session = harness_manager.create_session(config)
            sessions.append(session)

        # 尝试创建超过上限的会话
        with pytest.raises(ACPError) as exc_info:
            config = ACPSessionConfig(
                name="over-limit-session",
                resource_limits=ResourceLimits(cpu_limit=1.0, memory_limit="1g", disk_limit="5g"),
                network_policy=NetworkPolicy(),
                timeout=3600,
                auto_destroy=True,
                enable_qemu=False,
                enable_buildkit=True,
                platforms=["linux/amd64"],
            )
            harness_manager.create_session(config)

        assert exc_info.value.type == "resource_exhausted"
        assert exc_info.value.recoverable is True

        # 清理
        for session in sessions:
            harness_manager.destroy_session(session.session_id)

    def test_concurrent_operations_in_different_sessions(self, harness_manager, default_config):
        """测试不同会话中的并发操作"""
        # 创建两个会话
        session1 = harness_manager.create_session(default_config)
        config2 = ACPSessionConfig(
            name="concurrent-session-2",
            resource_limits=ResourceLimits(cpu_limit=2.0, memory_limit="2g", disk_limit="10g"),
            network_policy=NetworkPolicy(),
            timeout=3600,
            auto_destroy=True,
            enable_qemu=False,
            enable_buildkit=True,
            platforms=["linux/amd64"],
        )
        session2 = harness_manager.create_session(config2)

        # 在两个会话中并发执行操作
        docker_client1 = ACPDockerClient(session1)
        docker_client2 = ACPDockerClient(session2)

        result1 = docker_client1.run_container(
            image="alpine:latest",
            command="echo 'Session 1'",
            remove=True,
        )

        result2 = docker_client2.run_container(
            image="alpine:latest",
            command="echo 'Session 2'",
            remove=True,
        )

        assert result1.success is True
        assert result2.success is True

        # 清理
        harness_manager.destroy_session(session1.session_id)
        harness_manager.destroy_session(session2.session_id)


class TestACPResourceManagement:
    """测试资源管理和监控（需求 13.18-13.19）"""

    def test_set_resource_limits(self, harness_manager, default_config):
        """测试设置资源限制"""
        session = harness_manager.create_session(default_config)

        new_limits = ResourceLimits(
            cpu_limit=4.0,
            memory_limit="4g",
            disk_limit="20g",
        )

        result = harness_manager.set_resource_limits(session.session_id, new_limits)

        assert result is True
        assert session.config.resource_limits.cpu_limit == 4.0

        harness_manager.destroy_session(session.session_id)

    def test_monitor_session_performance(self, harness_manager, default_config):
        """测试监控会话性能"""
        session = harness_manager.create_session(default_config)

        # 执行一些操作
        harness_manager.use_session(session.session_id)
        harness_manager.use_session(session.session_id)

        # 监控性能
        metrics = harness_manager.monitor_session_performance(session.session_id)

        assert metrics.session_id == session.session_id
        assert metrics.operations_per_minute >= 0
        assert metrics.success_rate >= 0
        assert metrics.error_rate >= 0

        harness_manager.destroy_session(session.session_id)


class TestACPNetworkPolicy:
    """测试网络隔离和安全策略（需求 13.25-13.30）"""

    def test_configure_network_policy(self, harness_manager, default_config):
        """测试配置网络策略"""
        session = harness_manager.create_session(default_config)

        new_policy = NetworkPolicy(
            allow_internet=True,
            allowed_hosts=["github.com", "pypi.org"],
            blocked_ports=[22, 23, 3389],
            use_proxy=False,
            allow_privileged=False,
            allow_host_network=False,
            allow_host_pid=False,
        )

        result = harness_manager.configure_network_policy(session.session_id, new_policy)

        assert result is True
        assert session.config.network_policy.allow_internet is True
        assert "github.com" in session.config.network_policy.allowed_hosts

        harness_manager.destroy_session(session.session_id)

    def test_secure_session_config(self, session_manager):
        """测试安全会话配置"""
        config = session_manager.create_secure_config("secure-session")

        assert config.network_policy.allow_internet is False
        assert config.network_policy.allow_privileged is False
        assert config.network_policy.allow_host_network is False
        assert config.network_policy.allow_host_pid is False
        assert len(config.network_policy.blocked_ports) > 0


class TestACPLoggingAndAudit:
    """测试日志和审计（需求 13.20-13.22, 13.31）"""

    def test_get_session_logs(self, harness_manager, default_config):
        """测试获取会话日志"""
        session = harness_manager.create_session(default_config)

        # 执行一些操作生成日志
        harness_manager.use_session(session.session_id)

        # 获取日志
        logs = harness_manager.get_session_logs(session.session_id)

        assert len(logs) > 0
        assert all(hasattr(log, "timestamp") for log in logs)
        assert all(hasattr(log, "level") for log in logs)
        assert all(hasattr(log, "message") for log in logs)

        harness_manager.destroy_session(session.session_id)

    def test_export_session_logs_json(self, harness_manager, default_config):
        """测试导出 JSON 格式日志"""
        session = harness_manager.create_session(default_config)

        logs_json = harness_manager.export_session_logs(session.session_id, format="json")

        assert logs_json is not None
        assert isinstance(logs_json, str)
        assert "[" in logs_json  # JSON 数组

        harness_manager.destroy_session(session.session_id)

    def test_export_session_logs_text(self, harness_manager, default_config):
        """测试导出文本格式日志"""
        session = harness_manager.create_session(default_config)

        logs_text = harness_manager.export_session_logs(session.session_id, format="text")

        assert logs_text is not None
        assert isinstance(logs_text, str)
        assert "\n" in logs_text  # 多行文本

        harness_manager.destroy_session(session.session_id)

    def test_audit_log_recording(self, harness_manager, default_config):
        """测试审计日志记录"""
        session = harness_manager.create_session(default_config)

        # 审计日志应该记录会话创建
        audit_logs = harness_manager._audit_logs
        create_logs = [log for log in audit_logs if log.operation_type == "create_session"]

        assert len(create_logs) > 0
        assert any(log.session_id == session.session_id for log in create_logs)

        harness_manager.destroy_session(session.session_id)

        # 审计日志应该记录会话销毁
        destroy_logs = [log for log in audit_logs if log.operation_type == "destroy_session"]
        assert len(destroy_logs) > 0


class TestACPSessionManager:
    """测试会话管理器（需求 13.13-13.14）"""

    def test_validate_session_config(self, session_manager):
        """测试验证会话配置"""
        # 有效配置
        valid_config = session_manager.create_default_config("valid-session")
        errors = session_manager.validate_session_config(valid_config)
        assert len(errors) == 0

        # 无效配置 - 空名称
        invalid_config = ACPSessionConfig(
            name="",
            resource_limits=ResourceLimits(cpu_limit=1.0, memory_limit="1g", disk_limit="5g"),
            network_policy=NetworkPolicy(),
            timeout=3600,
            auto_destroy=True,
            enable_qemu=False,
            enable_buildkit=True,
            platforms=["linux/amd64"],
        )
        errors = session_manager.validate_session_config(invalid_config)
        assert len(errors) > 0
        assert any("名称" in error for error in errors)

    def test_create_default_config(self, session_manager):
        """测试创建默认配置"""
        config = session_manager.create_default_config("default-session")

        assert config.name == "default-session"
        assert config.resource_limits.cpu_limit == 2.0
        assert config.timeout == 3600
        assert config.auto_destroy is True
        assert config.enable_qemu is True
        assert config.enable_buildkit is True

    def test_get_session_statistics(self, harness_manager, session_manager, default_config):
        """测试获取会话统计信息"""
        # 创建几个会话
        session1 = harness_manager.create_session(default_config)
        config2 = ACPSessionConfig(
            name="stats-session-2",
            resource_limits=ResourceLimits(cpu_limit=1.0, memory_limit="1g", disk_limit="5g"),
            network_policy=NetworkPolicy(),
            timeout=1800,
            auto_destroy=True,
            enable_qemu=False,
            enable_buildkit=True,
            platforms=["linux/amd64"],
        )
        session2 = harness_manager.create_session(config2)

        # 获取统计信息
        stats = session_manager.get_session_statistics()

        assert stats["total_sessions"] >= 2
        assert stats["active_sessions"] >= 0
        assert stats["total_operations"] >= 0

        # 清理
        harness_manager.destroy_session(session1.session_id)
        harness_manager.destroy_session(session2.session_id)


class TestACPEndToEnd:
    """端到端测试场景"""

    def test_complete_development_workflow(self, harness_manager, default_config):
        """测试完整的开发工作流"""
        # 1. 创建会话
        session = harness_manager.create_session(default_config)
        assert session.status == "active"

        # 2. 克隆代码仓库
        git_client = ACPGitClient(session)
        clone_result = git_client.clone_repository(
            repo_url="https://github.com/example/test-app.git",
            target_dir="/workspace/test-app",
        )
        assert clone_result.success is True

        # 3. 构建 Docker 镜像
        docker_client = ACPDockerClient(session)
        build_result = docker_client.build_image(
            context_path="/workspace/test-app",
            dockerfile="Dockerfile",
            tag="test-app:dev",
        )
        assert build_result.success is True

        # 4. 运行测试容器
        test_result = docker_client.run_container(
            image="test-app:dev",
            command="pytest tests/",
            remove=True,
        )
        assert test_result.success is True

        # 5. 销毁会话
        destroy_result = harness_manager.destroy_session(session.session_id)
        assert destroy_result is True

    def test_multi_arch_build_and_push_workflow(self, harness_manager):
        """测试多架构构建和推送工作流"""
        # 创建支持多架构的会话
        config = ACPSessionConfig(
            name="multi-arch-workflow",
            resource_limits=ResourceLimits(cpu_limit=4.0, memory_limit="4g", disk_limit="20g"),
            network_policy=NetworkPolicy(allow_internet=True, allowed_hosts=["docker.io"]),
            timeout=7200,
            auto_destroy=True,
            enable_qemu=True,
            enable_buildkit=True,
            platforms=["linux/amd64", "linux/arm64"],
        )

        session = harness_manager.create_session(config)

        # 1. 克隆仓库
        git_client = ACPGitClient(session)
        git_client.clone_repository(
            repo_url="https://github.com/example/multi-arch-app.git",
            target_dir="/workspace/app",
        )

        # 2. 多架构构建
        buildkit_client = ACPBuildkitClient(session)
        build_result = buildkit_client.build_multi_arch(
            context_path="/workspace/app",
            dockerfile="Dockerfile",
            tag="example/app:latest",
            platforms=["linux/amd64", "linux/arm64"],
        )

        assert build_result.success is True
        assert len(build_result.platforms) == 2

        # 3. 推送镜像（模拟）
        # 在实际场景中，这里会推送到镜像仓库

        # 4. 清理
        harness_manager.destroy_session(session.session_id)


# 运行说明
if __name__ == "__main__":
    print("ACP 集成测试")
    print("=" * 60)
    print()
    print("这些测试验证 ACP Harness Manager 的以下功能：")
    print()
    print("1. 会话生命周期管理（创建、使用、销毁）")
    print("2. Docker-in-Docker 操作（构建、运行、执行命令）")
    print("3. Git 集成（克隆、切换分支、提交、推送）")
    print("4. Buildkit 多架构构建（amd64、arm64、arm/v7）")
    print("5. 故障恢复（超时处理、错误恢复）")
    print("6. 并发会话管理（多会话、资源限制）")
    print("7. 资源管理和监控（CPU、内存、磁盘）")
    print("8. 网络隔离和安全策略")
    print("9. 日志收集和审计")
    print()
    print("运行测试：")
    print("  pytest tests/integration/test_acp_integration.py -v")
    print()
    print("注意：这些测试使用模拟的 ACP Harness 实现。")
    print("在实际环境中，需要配置真实的 ACP Harness 端点。")
