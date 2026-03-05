"""
安全沙箱环境模块

提供安全的代码执行环境,包括:
- 文件系统访问权限控制
- 网络访问白名单机制
- 资源使用限制
- 危险操作检测和阻止
"""

import os
import psutil
import signal
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from ralph.models.execution import ExecutionResult, ResourceUsage, SecurityViolation


@dataclass
class FileSystemPolicy:
    """文件系统访问策略"""
    
    allowed_paths: List[str] = field(default_factory=list)  # 允许访问的路径列表
    read_only_paths: List[str] = field(default_factory=list)  # 只读路径列表
    forbidden_paths: List[str] = field(default_factory=list)  # 禁止访问的路径列表
    max_file_size_mb: int = 100  # 最大文件大小限制(MB)
    
    def is_path_allowed(self, path: str, write: bool = False) -> bool:
        """
        检查路径是否允许访问
        
        Args:
            path: 要检查的路径
            write: 是否为写操作
            
        Returns:
            是否允许访问
        """
        abs_path = os.path.abspath(path)
        
        # 检查是否在禁止路径中
        for forbidden in self.forbidden_paths:
            if abs_path.startswith(os.path.abspath(forbidden)):
                return False
        
        # 检查是否在只读路径中(写操作不允许)
        if write:
            for readonly in self.read_only_paths:
                if abs_path.startswith(os.path.abspath(readonly)):
                    return False
        
        # 检查是否在允许路径中
        for allowed in self.allowed_paths:
            if abs_path.startswith(os.path.abspath(allowed)):
                return True
        
        return False


@dataclass
class NetworkPolicy:
    """网络访问策略"""
    
    allow_network: bool = False  # 是否允许网络访问
    allowed_hosts: Set[str] = field(default_factory=set)  # 允许访问的主机白名单
    allowed_ports: Set[int] = field(default_factory=set)  # 允许访问的端口白名单
    blocked_hosts: Set[str] = field(default_factory=set)  # 禁止访问的主机黑名单
    
    def is_host_allowed(self, host: str, port: Optional[int] = None) -> bool:
        """
        检查主机是否允许访问
        
        Args:
            host: 主机名或IP地址
            port: 端口号(可选)
            
        Returns:
            是否允许访问
        """
        if not self.allow_network:
            return False
        
        # 检查黑名单
        if host in self.blocked_hosts:
            return False
        
        # 如果白名单为空,允许所有(除了黑名单)
        if not self.allowed_hosts:
            host_allowed = True
        else:
            host_allowed = host in self.allowed_hosts
        
        # 检查端口
        if port is not None and self.allowed_ports:
            port_allowed = port in self.allowed_ports
        else:
            port_allowed = True
        
        return host_allowed and port_allowed


@dataclass
class ResourceLimits:
    """资源使用限制"""
    
    max_cpu_percent: float = 80.0  # 最大CPU使用率(%)
    max_memory_mb: int = 1024  # 最大内存使用(MB)
    max_execution_time: int = 300  # 最大执行时间(秒)
    max_processes: int = 10  # 最大进程数
    max_open_files: int = 100  # 最大打开文件数


@dataclass
class SandboxConfig:
    """沙箱配置"""
    
    project_root: str  # 项目根目录
    filesystem_policy: FileSystemPolicy = field(default_factory=FileSystemPolicy)
    network_policy: NetworkPolicy = field(default_factory=NetworkPolicy)
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)
    enable_audit_log: bool = True  # 是否启用审计日志
    temp_dir: Optional[str] = None  # 临时目录(如果为None则自动创建)


class SafetySandbox:
    """
    安全沙箱环境
    
    提供安全的代码执行环境,限制文件系统访问、网络访问和资源使用。
    """
    
    def __init__(self, config: SandboxConfig):
        """
        初始化安全沙箱
        
        Args:
            config: 沙箱配置
        """
        self.config = config
        self.audit_log: List[Dict] = []
        self._setup_filesystem_policy()
        self._setup_temp_dir()
        self._running_processes: Dict[int, psutil.Process] = {}
        self._resource_monitor_thread: Optional[threading.Thread] = None
        self._stop_monitoring = threading.Event()
    
    def _setup_filesystem_policy(self) -> None:
        """设置文件系统策略"""
        # 确保项目根目录在允许路径中
        project_root = os.path.abspath(self.config.project_root)
        if project_root not in self.config.filesystem_policy.allowed_paths:
            self.config.filesystem_policy.allowed_paths.append(project_root)
        
        # 添加系统关键路径到禁止列表
        system_paths = [
            "/etc",
            "/sys",
            "/proc",
            "/dev",
            "/boot",
            "/root",
        ]
        for path in system_paths:
            if path not in self.config.filesystem_policy.forbidden_paths:
                self.config.filesystem_policy.forbidden_paths.append(path)
    
    def _setup_temp_dir(self) -> None:
        """设置临时目录"""
        if self.config.temp_dir is None:
            self.config.temp_dir = tempfile.mkdtemp(prefix="ralph_sandbox_")
        else:
            os.makedirs(self.config.temp_dir, exist_ok=True)
        
        # 临时目录添加到允许路径
        if self.config.temp_dir not in self.config.filesystem_policy.allowed_paths:
            self.config.filesystem_policy.allowed_paths.append(self.config.temp_dir)
    
    def check_file_access(self, path: str, write: bool = False) -> bool:
        """
        检查文件访问权限
        
        Args:
            path: 文件路径
            write: 是否为写操作
            
        Returns:
            是否允许访问
        """
        allowed = self.config.filesystem_policy.is_path_allowed(path, write)
        
        if self.config.enable_audit_log:
            self._log_audit_event(
                event_type="file_access_check",
                details={
                    "path": path,
                    "write": write,
                    "allowed": allowed,
                }
            )
        
        return allowed
    
    def check_network_access(self, host: str, port: Optional[int] = None) -> bool:
        """
        检查网络访问权限
        
        Args:
            host: 主机名或IP地址
            port: 端口号(可选)
            
        Returns:
            是否允许访问
        """
        allowed = self.config.network_policy.is_host_allowed(host, port)
        
        if self.config.enable_audit_log:
            self._log_audit_event(
                event_type="network_access_check",
                details={
                    "host": host,
                    "port": port,
                    "allowed": allowed,
                }
            )
        
        return allowed
    
    def execute_code(
        self,
        code: str,
        language: str,
        working_dir: Optional[str] = None,
    ) -> ExecutionResult:
        """
        在沙箱中执行代码
        
        Args:
            code: 要执行的代码
            language: 编程语言
            working_dir: 工作目录(可选)
            
        Returns:
            执行结果
        """
        if working_dir is None:
            working_dir = self.config.project_root
        
        # 检查工作目录访问权限
        if not self.check_file_access(working_dir, write=False):
            return ExecutionResult(
                success=False,
                output="",
                errors=[],
                execution_time=0.0,
                resource_usage=ResourceUsage(),
                security_violations=[
                    SecurityViolation(
                        type="filesystem_access_denied",
                        message=f"工作目录访问被拒绝: {working_dir}",
                        severity="high",
                    )
                ],
            )
        
        # 记录审计日志
        if self.config.enable_audit_log:
            self._log_audit_event(
                event_type="code_execution",
                details={
                    "language": language,
                    "working_dir": working_dir,
                    "code_length": len(code),
                }
            )
        
        # TODO: 实际的代码执行逻辑将在后续任务中实现
        # 这里只是框架实现
        return ExecutionResult(
            success=True,
            output="",
            errors=[],
            execution_time=0.0,
            resource_usage=ResourceUsage(),
            security_violations=[],
        )
    
    def run_tests(
        self,
        test_command: str,
        working_dir: Optional[str] = None,
    ) -> ExecutionResult:
        """
        在沙箱中运行测试
        
        Args:
            test_command: 测试命令
            working_dir: 工作目录(可选)
            
        Returns:
            执行结果
        """
        if working_dir is None:
            working_dir = self.config.project_root
        
        # 检查工作目录访问权限
        if not self.check_file_access(working_dir, write=False):
            return ExecutionResult(
                success=False,
                output="",
                errors=[],
                execution_time=0.0,
                resource_usage=ResourceUsage(),
                security_violations=[
                    SecurityViolation(
                        type="filesystem_access_denied",
                        message=f"工作目录访问被拒绝: {working_dir}",
                        severity="high",
                    )
                ],
            )
        
        # 记录审计日志
        if self.config.enable_audit_log:
            self._log_audit_event(
                event_type="test_execution",
                details={
                    "command": test_command,
                    "working_dir": working_dir,
                }
            )
        
        # TODO: 实际的测试执行逻辑将在后续任务中实现
        return ExecutionResult(
            success=True,
            output="",
            errors=[],
            execution_time=0.0,
            resource_usage=ResourceUsage(),
            security_violations=[],
        )
    def execute_command(
        self,
        command: str,
        timeout: Optional[int] = None,
        cwd: Optional[str] = None
    ) -> ExecutionResult:
        """
        在沙箱中执行命令

        参数:
            command: 要执行的命令
            timeout: 超时时间（秒）
            cwd: 工作目录

        返回:
            ExecutionResult: 执行结果
        """
        import subprocess
        import time

        if timeout is None:
            timeout = self.config.resource_limits.max_execution_time

        if cwd is None:
            cwd = self.config.project_root

        # 检查命令安全性
        violations = self.detect_dangerous_operations(command)
        if violations:
            return ExecutionResult(
                success=False,
                exit_code=-1,
                output=f"命令包含危险操作: {', '.join(v.message for v in violations)}",
                execution_time=0.0,
                security_violations=violations
            )

        start_time = time.time()

        try:
            # 执行命令
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
                text=True
            )

            # 等待完成
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                exit_code = process.returncode
                output = stdout if stdout else stderr
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                return ExecutionResult(
                    success=False,
                    exit_code=-1,
                    output=f"命令执行超时（{timeout}秒）\n{stderr}",
                    execution_time=time.time() - start_time
                )

            execution_time = time.time() - start_time

            return ExecutionResult(
                success=exit_code == 0,
                exit_code=exit_code,
                output=output,
                execution_time=execution_time
            )

        except Exception as e:
            return ExecutionResult(
                success=False,
                exit_code=-1,
                output=f"命令执行失败: {str(e)}",
                execution_time=time.time() - start_time
            )


    
    def check_security(self, code: str) -> List[SecurityViolation]:
        """
        检查代码安全性
        
        Args:
            code: 要检查的代码
            
        Returns:
            安全违规列表
        """
        violations: List[SecurityViolation] = []
        
        # 检查危险操作模式
        dangerous_patterns = [
            ("rm -rf /", "尝试删除根目录", "critical"),
            ("eval(", "使用eval函数", "high"),
            ("exec(", "使用exec函数", "high"),
            ("__import__", "动态导入模块", "medium"),
            ("os.system", "执行系统命令", "medium"),
            ("subprocess.call", "执行子进程", "medium"),
        ]
        
        for pattern, message, severity in dangerous_patterns:
            if pattern in code:
                violations.append(
                    SecurityViolation(
                        type="dangerous_operation",
                        message=message,
                        severity=severity,
                        details={"pattern": pattern},
                    )
                )
        
        # 记录审计日志
        if self.config.enable_audit_log and violations:
            self._log_audit_event(
                event_type="security_check",
                details={
                    "code_length": len(code),
                    "violations_count": len(violations),
                    "violations": [v.type for v in violations],
                }
            )
        
        return violations
    
    def get_audit_log(self) -> List[Dict]:
        """
        获取审计日志
        
        Returns:
            审计日志列表
        """
        return self.audit_log.copy()
    
    def clear_audit_log(self) -> None:
        """清空审计日志"""
        self.audit_log.clear()
    
    def cleanup(self) -> None:
        """清理沙箱资源"""
        # 停止资源监控
        self._stop_resource_monitoring()
        
        # 终止所有运行中的进程
        self._terminate_all_processes()
        
        # 清理临时目录
        if self.config.temp_dir and os.path.exists(self.config.temp_dir):
            import shutil
            try:
                shutil.rmtree(self.config.temp_dir)
            except Exception as e:
                # 记录清理失败但不抛出异常
                if self.config.enable_audit_log:
                    self._log_audit_event(
                        event_type="cleanup_failed",
                        details={"error": str(e)}
                    )
    
    def _log_audit_event(self, event_type: str, details: Dict) -> None:
        """
        记录审计事件
        
        Args:
            event_type: 事件类型
            details: 事件详情
        """
        self.audit_log.append({
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "details": details,
        })
    
    def _start_resource_monitoring(self, process: psutil.Process) -> None:
        """
        启动资源监控线程
        
        Args:
            process: 要监控的进程
        """
        self._running_processes[process.pid] = process
        self._stop_monitoring.clear()
        
        self._resource_monitor_thread = threading.Thread(
            target=self._monitor_resources,
            args=(process,),
            daemon=True
        )
        self._resource_monitor_thread.start()
    
    def _stop_resource_monitoring(self) -> None:
        """停止资源监控线程"""
        self._stop_monitoring.set()
        if self._resource_monitor_thread and self._resource_monitor_thread.is_alive():
            self._resource_monitor_thread.join(timeout=1.0)
    
    def _monitor_resources(self, process: psutil.Process) -> None:
        """
        监控进程资源使用
        
        Args:
            process: 要监控的进程
        """
        start_time = time.time()
        limits = self.config.resource_limits
        
        while not self._stop_monitoring.is_set():
            try:
                if not process.is_running():
                    break
                
                # 检查执行时间
                elapsed_time = time.time() - start_time
                if elapsed_time > limits.max_execution_time:
                    self._terminate_process_with_violation(
                        process,
                        "execution_timeout",
                        f"执行时间超过限制: {elapsed_time:.2f}秒 > {limits.max_execution_time}秒"
                    )
                    break
                
                # 检查 CPU 使用率
                cpu_percent = process.cpu_percent(interval=0.1)
                if cpu_percent > limits.max_cpu_percent:
                    self._terminate_process_with_violation(
                        process,
                        "cpu_limit_exceeded",
                        f"CPU 使用率超过限制: {cpu_percent:.2f}% > {limits.max_cpu_percent}%"
                    )
                    break
                
                # 检查内存使用
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / (1024 * 1024)
                if memory_mb > limits.max_memory_mb:
                    self._terminate_process_with_violation(
                        process,
                        "memory_limit_exceeded",
                        f"内存使用超过限制: {memory_mb:.2f}MB > {limits.max_memory_mb}MB"
                    )
                    break
                
                # 检查进程数
                children = process.children(recursive=True)
                total_processes = len(children) + 1
                if total_processes > limits.max_processes:
                    self._terminate_process_with_violation(
                        process,
                        "process_limit_exceeded",
                        f"进程数超过限制: {total_processes} > {limits.max_processes}"
                    )
                    break
                
                # 检查打开文件数
                try:
                    open_files = len(process.open_files())
                    if open_files > limits.max_open_files:
                        self._terminate_process_with_violation(
                            process,
                            "file_limit_exceeded",
                            f"打开文件数超过限制: {open_files} > {limits.max_open_files}"
                        )
                        break
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    pass
                
                # 短暂休眠避免过度占用 CPU
                time.sleep(0.5)
                
            except psutil.NoSuchProcess:
                # 进程已结束
                break
            except Exception as e:
                if self.config.enable_audit_log:
                    self._log_audit_event(
                        event_type="resource_monitoring_error",
                        details={"error": str(e), "pid": process.pid}
                    )
                break
    
    def _terminate_process_with_violation(
        self,
        process: psutil.Process,
        violation_type: str,
        message: str
    ) -> None:
        """
        终止进程并记录安全违规
        
        Args:
            process: 要终止的进程
            violation_type: 违规类型
            message: 违规消息
        """
        if self.config.enable_audit_log:
            self._log_audit_event(
                event_type="resource_limit_violation",
                details={
                    "pid": process.pid,
                    "violation_type": violation_type,
                    "message": message,
                }
            )
        
        # 终止进程及其子进程
        try:
            children = process.children(recursive=True)
            for child in children:
                try:
                    child.terminate()
                except psutil.NoSuchProcess:
                    pass
            
            process.terminate()
            
            # 等待进程终止
            try:
                process.wait(timeout=3)
            except psutil.TimeoutExpired:
                # 强制杀死进程
                process.kill()
                for child in children:
                    try:
                        child.kill()
                    except psutil.NoSuchProcess:
                        pass
        except psutil.NoSuchProcess:
            pass
    
    def _terminate_all_processes(self) -> None:
        """终止所有运行中的进程"""
        for pid, process in list(self._running_processes.items()):
            try:
                if process.is_running():
                    process.terminate()
                    try:
                        process.wait(timeout=3)
                    except psutil.TimeoutExpired:
                        process.kill()
            except psutil.NoSuchProcess:
                pass
            finally:
                self._running_processes.pop(pid, None)
    
    def _collect_resource_usage(self, process: psutil.Process, elapsed_time: float) -> ResourceUsage:
        """
        收集进程资源使用情况
        
        Args:
            process: 进程对象
            elapsed_time: 执行时间
            
        Returns:
            资源使用情况
        """
        try:
            if not process.is_running():
                return ResourceUsage(execution_time=elapsed_time)
            
            cpu_percent = process.cpu_percent(interval=0.1)
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
            
            # 尝试获取网络 I/O (可能不可用)
            network_rx = 0
            network_tx = 0
            try:
                io_counters = process.io_counters()
                network_rx = io_counters.read_bytes
                network_tx = io_counters.write_bytes
            except (psutil.AccessDenied, AttributeError):
                pass
            
            return ResourceUsage(
                cpu_percent=cpu_percent,
                memory_usage_mb=memory_mb,
                memory_limit_mb=self.config.resource_limits.max_memory_mb,
                execution_time=elapsed_time,
                network_rx_bytes=network_rx,
                network_tx_bytes=network_tx,
            )
        except psutil.NoSuchProcess:
            return ResourceUsage(execution_time=elapsed_time)
    
    def detect_dangerous_operations(self, command: str) -> List[SecurityViolation]:
        """
        检测命令中的危险操作
        
        Args:
            command: 要检查的命令
            
        Returns:
            安全违规列表
        """
        violations: List[SecurityViolation] = []
        
        # 危险命令模式
        dangerous_commands = [
            (r"rm\s+-rf\s+/", "尝试删除根目录", "critical"),
            (r"dd\s+if=", "使用 dd 命令可能破坏数据", "high"),
            (r"mkfs\.", "尝试格式化文件系统", "critical"),
            (r":(){ :|:& };:", "Fork 炸弹攻击", "critical"),
            (r"chmod\s+777", "设置过于宽松的文件权限", "medium"),
            (r"curl.*\|\s*bash", "从网络下载并执行脚本", "high"),
            (r"wget.*\|\s*sh", "从网络下载并执行脚本", "high"),
        ]
        
        import re
        for pattern, message, severity in dangerous_commands:
            if re.search(pattern, command):
                violations.append(
                    SecurityViolation(
                        type="dangerous_command",
                        message=message,
                        severity=severity,
                        details={"pattern": pattern, "command": command},
                    )
                )
        
        return violations
