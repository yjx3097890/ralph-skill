"""
CLI 进程管理器

管理 AI 引擎 CLI 工具的进程生命周期，处理输入输出和错误。

## 功能特点
- 进程启动和终止管理
- 输入输出流处理
- 超时控制
- 错误捕获和处理
- 流式输出支持

## 使用示例
```python
manager = CLIProcessManager()

# 启动 CLI 进程
process = manager.start_process(
    command=["qwen-code", "--model", "qwen-coder-plus"],
    env={"QWEN_API_KEY": "your-key"}
)

# 发送输入
manager.send_input(process, "实现一个快速排序算法")

# 读取输出
output = manager.read_output(process, timeout=60)

# 终止进程
manager.terminate_process(process)
```
"""

import os
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from queue import Queue, Empty
from typing import Dict, List, Optional, Callable

from ralph.models.enums import ProcessStatus


@dataclass
class ProcessConfig:
    """CLI 进程配置"""
    command: List[str]
    env: Dict[str, str] = field(default_factory=dict)
    cwd: Optional[str] = None
    timeout: int = 60
    buffer_size: int = 8192
    encoding: str = "utf-8"


@dataclass
class ProcessInfo:
    """进程信息"""
    pid: int
    command: str
    status: ProcessStatus
    started_at: datetime
    ended_at: Optional[datetime] = None
    exit_code: Optional[int] = None
    stdout_lines: int = 0
    stderr_lines: int = 0


class CLIProcessManager:
    """CLI 进程管理器"""
    
    def __init__(self):
        """初始化进程管理器"""
        self.processes: Dict[int, subprocess.Popen] = {}
        self.process_info: Dict[int, ProcessInfo] = {}
    
    def start_process(
        self,
        command: List[str],
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None
    ) -> subprocess.Popen:
        """
        启动 CLI 进程
        
        Args:
            command: 命令和参数列表
            env: 环境变量字典
            cwd: 工作目录
            
        Returns:
            subprocess.Popen: 进程对象
            
        Raises:
            FileNotFoundError: CLI 工具未找到
            PermissionError: 权限不足
        """
        # 合并环境变量
        process_env = os.environ.copy()
        if env:
            process_env.update(env)
        
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=process_env,
                cwd=cwd,
                text=True,
                bufsize=1,  # 行缓冲
                universal_newlines=True
            )
            
            # 记录进程信息
            self.processes[process.pid] = process
            self.process_info[process.pid] = ProcessInfo(
                pid=process.pid,
                command=" ".join(command),
                status=ProcessStatus.RUNNING,
                started_at=datetime.now()
            )
            
            return process
            
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"CLI 工具未找到: {command[0]}\n"
                f"请确保已安装该工具并添加到 PATH 环境变量"
            ) from e
        except PermissionError as e:
            raise PermissionError(
                f"权限不足，无法执行: {command[0]}"
            ) from e
    
    def send_input(
        self,
        process: subprocess.Popen,
        input_text: str,
        flush: bool = True
    ) -> None:
        """
        向进程发送输入
        
        Args:
            process: 进程对象
            input_text: 输入文本
            flush: 是否立即刷新缓冲区
            
        Raises:
            BrokenPipeError: 进程已终止
        """
        try:
            if process.stdin:
                process.stdin.write(input_text)
                if not input_text.endswith('\n'):
                    process.stdin.write('\n')
                if flush:
                    process.stdin.flush()
        except BrokenPipeError as e:
            raise BrokenPipeError(
                f"无法向进程 {process.pid} 发送输入：进程已终止"
            ) from e
    
    def read_output(
        self,
        process: subprocess.Popen,
        timeout: int = 60,
        stream: str = "stdout"
    ) -> str:
        """
        读取进程输出
        
        Args:
            process: 进程对象
            timeout: 超时时间（秒）
            stream: 输出流类型（stdout 或 stderr）
            
        Returns:
            str: 输出文本
            
        Raises:
            TimeoutError: 读取超时
        """
        output_stream = process.stdout if stream == "stdout" else process.stderr
        if not output_stream:
            return ""
        
        output_lines = []
        start_time = time.time()
        
        try:
            while True:
                # 检查超时
                if time.time() - start_time > timeout:
                    raise TimeoutError(
                        f"读取进程 {process.pid} 输出超时（{timeout}秒）"
                    )
                
                # 检查进程是否结束
                if process.poll() is not None:
                    # 读取剩余输出
                    remaining = output_stream.read()
                    if remaining:
                        output_lines.append(remaining)
                    break
                
                # 读取一行
                line = output_stream.readline()
                if line:
                    output_lines.append(line)
                    
                    # 更新统计
                    if process.pid in self.process_info:
                        if stream == "stdout":
                            self.process_info[process.pid].stdout_lines += 1
                        else:
                            self.process_info[process.pid].stderr_lines += 1
                else:
                    # 短暂休眠避免 CPU 占用过高
                    time.sleep(0.1)
            
            return "".join(output_lines)
            
        except Exception as e:
            raise RuntimeError(
                f"读取进程 {process.pid} 输出时发生错误: {e}"
            ) from e
    
    def read_output_stream(
        self,
        process: subprocess.Popen,
        callback: Callable[[str], None],
        timeout: int = 60
    ) -> None:
        """
        流式读取进程输出并调用回调函数
        
        Args:
            process: 进程对象
            callback: 回调函数，接收每行输出
            timeout: 超时时间（秒）
            
        Raises:
            TimeoutError: 读取超时
        """
        if not process.stdout:
            return
        
        start_time = time.time()
        
        try:
            for line in iter(process.stdout.readline, ''):
                # 检查超时
                if time.time() - start_time > timeout:
                    raise TimeoutError(
                        f"流式读取进程 {process.pid} 输出超时（{timeout}秒）"
                    )
                
                if line:
                    callback(line.rstrip('\n'))
                    
                    # 更新统计
                    if process.pid in self.process_info:
                        self.process_info[process.pid].stdout_lines += 1
                
                # 检查进程是否结束
                if process.poll() is not None:
                    break
                    
        except Exception as e:
            raise RuntimeError(
                f"流式读取进程 {process.pid} 输出时发生错误: {e}"
            ) from e
    
    def wait_for_completion(
        self,
        process: subprocess.Popen,
        timeout: Optional[int] = None
    ) -> int:
        """
        等待进程完成
        
        Args:
            process: 进程对象
            timeout: 超时时间（秒），None 表示无限等待
            
        Returns:
            int: 进程退出码
            
        Raises:
            TimeoutError: 等待超时
        """
        try:
            exit_code = process.wait(timeout=timeout)
            
            # 更新进程信息
            if process.pid in self.process_info:
                info = self.process_info[process.pid]
                info.status = ProcessStatus.COMPLETED if exit_code == 0 else ProcessStatus.FAILED
                info.ended_at = datetime.now()
                info.exit_code = exit_code
            
            return exit_code
            
        except subprocess.TimeoutExpired as e:
            # 更新进程状态
            if process.pid in self.process_info:
                self.process_info[process.pid].status = ProcessStatus.TIMEOUT
            
            raise TimeoutError(
                f"等待进程 {process.pid} 完成超时（{timeout}秒）"
            ) from e
    
    def terminate_process(
        self,
        process: subprocess.Popen,
        force: bool = False,
        timeout: int = 5
    ) -> bool:
        """
        终止进程
        
        Args:
            process: 进程对象
            force: 是否强制终止（使用 SIGKILL）
            timeout: 等待进程终止的超时时间（秒）
            
        Returns:
            bool: 是否成功终止
        """
        if process.poll() is not None:
            # 进程已经结束
            return True
        
        try:
            if force:
                # 强制终止
                process.kill()
            else:
                # 优雅终止
                process.terminate()
            
            # 等待进程结束
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                # 超时后强制终止
                process.kill()
                process.wait()
            
            # 更新进程信息
            if process.pid in self.process_info:
                info = self.process_info[process.pid]
                info.status = ProcessStatus.TERMINATED
                info.ended_at = datetime.now()
                info.exit_code = process.returncode
            
            # 清理进程记录
            if process.pid in self.processes:
                del self.processes[process.pid]
            
            return True
            
        except Exception as e:
            print(f"终止进程 {process.pid} 时发生错误: {e}")
            return False
    
    def get_process_info(self, pid: int) -> Optional[ProcessInfo]:
        """
        获取进程信息
        
        Args:
            pid: 进程 ID
            
        Returns:
            Optional[ProcessInfo]: 进程信息，如果不存在则返回 None
        """
        return self.process_info.get(pid)
    
    def list_active_processes(self) -> List[ProcessInfo]:
        """
        列出所有活动进程
        
        Returns:
            List[ProcessInfo]: 活动进程信息列表
        """
        return [
            info for info in self.process_info.values()
            if info.status == ProcessStatus.RUNNING
        ]
    
    def cleanup_all(self) -> None:
        """清理所有进程"""
        for pid, process in list(self.processes.items()):
            self.terminate_process(process, force=True)
        
        self.processes.clear()
        self.process_info.clear()
    
    def __del__(self):
        """析构函数：清理所有进程"""
        self.cleanup_all()
