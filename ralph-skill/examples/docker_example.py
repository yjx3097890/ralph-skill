"""
Docker 支持模块使用示例

演示如何使用 Docker Manager 进行镜像构建、容器管理和测试执行。
"""

from ralph.support.docker_support import DockerSupport
from ralph.models.docker import ContainerConfig, HealthCheck


def example_detect_docker_config():
    """示例：检测项目的 Docker 配置"""
    print("=== 检测 Docker 配置 ===")
    
    with DockerSupport(project_path=".") as docker_support:
        config = docker_support.detect_docker_config()
        
        print(f"是否有 Dockerfile: {config.has_dockerfile}")
        print(f"是否有 docker-compose: {config.has_compose}")
        
        if config.has_dockerfile:
            print(f"Dockerfile 路径: {config.dockerfile_path}")
            print(f"基础镜像: {config.base_image}")
            print(f"暴露端口: {config.exposed_ports}")


def example_build_image():
    """示例：构建 Docker 镜像"""
    print("\n=== 构建 Docker 镜像 ===")
    
    with DockerSupport(project_path=".") as docker_support:
        result = docker_support.build_image(
            dockerfile_path="./Dockerfile",
            tag="myapp:latest",
            build_args={"VERSION": "1.0.0"},
        )
        
        if result.success:
            print(f"构建成功！")
            print(f"镜像 ID: {result.image_id}")
            print(f"构建时间: {result.build_time:.2f}秒")
            print(f"镜像大小: {result.size_bytes / (1024*1024):.2f}MB")
        else:
            print(f"构建失败！")
            for error in result.errors:
                print(f"  步骤 {error.step_number}: {error.error_message}")


def example_run_container():
    """示例：创建并运行容器"""
    print("\n=== 运行容器 ===")
    
    with DockerSupport(project_path=".") as docker_support:
        # 配置容器
        config = ContainerConfig(
            image="alpine:latest",
            name="test-container",
            command="echo 'Hello from Docker!'",
            environment={"ENV": "test"},
            ports={8080: 80},
            health_check=HealthCheck(
                test="echo 'healthy'",
                interval=10,
                timeout=5,
                retries=3,
            ),
        )
        
        # 创建并启动容器
        container_id = docker_support.create_and_start_container(config)
        print(f"容器已启动: {container_id[:12]}")
        
        # 获取容器日志
        logs = docker_support.container_manager.get_container_logs(container_id)
        print(f"容器日志:\n{logs}")


def example_run_tests_in_container():
    """示例：在容器中运行测试"""
    print("\n=== 容器化测试 ===")
    
    with DockerSupport(project_path=".") as docker_support:
        config = ContainerConfig(
            image="python:3.9-slim",
            name="test-runner",
            command="pytest tests/",
            environment={"PYTHONPATH": "/app"},
        )
        
        result = docker_support.run_tests_in_container(
            container_config=config,
            test_command="pytest tests/ -v",
            artifact_paths=["/app/test-results/", "/app/coverage.xml"],
            timeout=300,
        )
        
        print(f"测试{'成功' if result.success else '失败'}")
        print(f"退出码: {result.exit_code}")
        print(f"执行时间: {result.execution_time:.2f}秒")
        
        if result.resource_usage:
            print(f"CPU 使用: {result.resource_usage.cpu_percent:.1f}%")
            print(f"内存使用: {result.resource_usage.memory_usage_mb:.1f}MB")


def example_compose_orchestration():
    """示例：Docker Compose 编排"""
    print("\n=== Docker Compose 编排 ===")
    
    with DockerSupport(project_path=".") as docker_support:
        # 解析 compose 文件
        compose_config = docker_support.parse_compose_file("docker-compose.yml")
        
        print(f"服务数量: {len(compose_config.services)}")
        print(f"服务列表: {list(compose_config.services.keys())}")
        
        # 启动服务
        result = docker_support.start_compose_services(
            compose_config=compose_config,
            parallel=False,
            timeout=300,
        )
        
        if result.success:
            print(f"所有服务启动成功！")
            print(f"已启动: {result.services_started}")
        else:
            print(f"部分服务启动失败")
            print(f"失败服务: {result.services_failed}")
            print(f"错误信息: {result.errors}")
        
        # 获取服务状态
        for service_name in result.services_started:
            status = docker_support.get_service_status(service_name)
            if status:
                print(f"服务 {service_name}: {status.status} (健康: {status.health_status})")


def example_error_parsing():
    """示例：Docker 错误解析"""
    print("\n=== Docker 错误解析 ===")
    
    with DockerSupport(project_path=".") as docker_support:
        # 模拟构建错误
        build_output = """
        Step 3/5 : COPY app.py /app/
        COPY failed: stat /var/lib/docker/tmp/app.py: no such file or directory
        ERROR: failed to solve: process "/bin/sh -c apt-get update" did not complete
        """
        
        errors = docker_support.error_parser.parse_build_errors(build_output)
        
        print(f"发现 {len(errors)} 个错误:")
        for error in errors:
            print(f"\n错误类型: {error.error_type}")
            print(f"错误信息: {error.error_message}")
            
            # 获取修复建议
            from ralph.models.docker import DockerError
            docker_error = DockerError(
                error_type=error.error_type,
                error_message=error.error_message,
            )
            suggestions = docker_support.error_parser.suggest_fix(docker_error)
            
            print("修复建议:")
            for suggestion in suggestions:
                print(f"  - {suggestion.description}")
                if suggestion.command:
                    print(f"    命令: {suggestion.command}")


if __name__ == "__main__":
    print("Docker 支持模块使用示例\n")
    
    try:
        # 运行各个示例
        example_detect_docker_config()
        # example_build_image()  # 需要实际的 Dockerfile
        # example_run_container()  # 需要 Docker daemon 运行
        # example_run_tests_in_container()  # 需要 Docker daemon 运行
        # example_compose_orchestration()  # 需要 docker-compose.yml
        example_error_parsing()
        
        print("\n示例执行完成！")
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
