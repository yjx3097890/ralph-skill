"""
Vite 构建工具管理器

提供 Vite 项目构建、开发服务器启动等功能。
"""

import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from ralph.models.enums import DependencyManager
from ralph.models.frontend import BuildResult, DevServerInfo


class ViteManager:
    """Vite 构建工具管理器"""
    
    def __init__(self, project_path: Path, package_manager: DependencyManager = DependencyManager.NPM):
        """
        初始化 Vite 管理器
        
        Args:
            project_path: 项目根目录路径
            package_manager: 包管理器类型
        """
        self.project_path = Path(project_path)
        self.package_manager = package_manager
        self._dev_server_process: Optional[subprocess.Popen] = None
    
    def build(self, mode: str = "production") -> BuildResult:
        """
        构建项目
        
        Args:
            mode: 构建模式，production 或 development
            
        Returns:
            BuildResult: 构建结果
        """
        start_time = time.time()
        
        # 构建命令
        cmd = self._get_build_command(mode)
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=600  # 10 分钟超时
            )
            
            build_time = time.time() - start_time
            
            # 检查构建输出目录
            output_dir = self.project_path / "dist"
            output_size = self._calculate_directory_size(output_dir) if output_dir.exists() else 0
            
            # 提取资产列表
            assets = self._extract_assets(output_dir) if output_dir.exists() else []
            
            # 提取错误和警告
            errors = self._extract_errors(result.stderr)
            warnings = self._extract_warnings(result.stderr)
            
            return BuildResult(
                success=result.returncode == 0,
                build_time=build_time,
                output_dir=output_dir,
                output_size_bytes=output_size,
                build_logs=result.stdout + result.stderr,
                errors=errors,
                warnings=warnings,
                assets=assets
            )
            
        except subprocess.TimeoutExpired:
            return BuildResult(
                success=False,
                build_time=time.time() - start_time,
                output_dir=self.project_path / "dist",
                output_size_bytes=0,
                build_logs="",
                errors=["构建超时（10 分钟）"]
            )
        except Exception as e:
            return BuildResult(
                success=False,
                build_time=time.time() - start_time,
                output_dir=self.project_path / "dist",
                output_size_bytes=0,
                build_logs="",
                errors=[f"构建失败: {str(e)}"]
            )
    
    def start_dev_server(self, port: int = 3000, host: str = "localhost") -> DevServerInfo:
        """
        启动开发服务器
        
        Args:
            port: 端口号
            host: 主机地址
            
        Returns:
            DevServerInfo: 开发服务器信息
        """
        # 如果已有服务器在运行，先停止
        if self._dev_server_process and self._dev_server_process.poll() is None:
            self.stop_dev_server()
        
        # 启动命令
        cmd = self._get_dev_command(port, host)
        
        try:
            self._dev_server_process = subprocess.Popen(
                cmd,
                cwd=self.project_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 等待服务器启动
            time.sleep(3)
            
            # 检查进程是否还在运行
            if self._dev_server_process.poll() is not None:
                # 进程已退出，读取错误信息
                _, stderr = self._dev_server_process.communicate()
                raise RuntimeError(f"开发服务器启动失败: {stderr}")
            
            return DevServerInfo(
                pid=self._dev_server_process.pid,
                port=port,
                host=host,
                url=f"http://{host}:{port}",
                started_at=datetime.now(),
                is_running=True
            )
            
        except Exception as e:
            raise RuntimeError(f"启动开发服务器失败: {str(e)}")
    
    def stop_dev_server(self) -> bool:
        """
        停止开发服务器
        
        Returns:
            bool: 是否成功停止
        """
        if not self._dev_server_process:
            return True
        
        try:
            self._dev_server_process.terminate()
            self._dev_server_process.wait(timeout=10)
            self._dev_server_process = None
            return True
        except subprocess.TimeoutExpired:
            # 强制杀死进程
            self._dev_server_process.kill()
            self._dev_server_process = None
            return True
        except Exception:
            return False
    
    def is_dev_server_running(self) -> bool:
        """检查开发服务器是否在运行"""
        if not self._dev_server_process:
            return False
        return self._dev_server_process.poll() is None
    
    def _get_build_command(self, mode: str) -> list:
        """获取构建命令"""
        if self.package_manager == DependencyManager.NPM:
            return ["npm", "run", "build"]
        elif self.package_manager == DependencyManager.YARN:
            return ["yarn", "build"]
        elif self.package_manager == DependencyManager.PNPM:
            return ["pnpm", "build"]
        else:
            return ["npm", "run", "build"]
    
    def _get_dev_command(self, port: int, host: str) -> list:
        """获取开发服务器命令"""
        if self.package_manager == DependencyManager.NPM:
            return ["npm", "run", "dev", "--", "--port", str(port), "--host", host]
        elif self.package_manager == DependencyManager.YARN:
            return ["yarn", "dev", "--port", str(port), "--host", host]
        elif self.package_manager == DependencyManager.PNPM:
            return ["pnpm", "dev", "--port", str(port), "--host", host]
        else:
            return ["npm", "run", "dev", "--", "--port", str(port), "--host", host]
    
    def _calculate_directory_size(self, directory: Path) -> int:
        """计算目录大小（字节）"""
        total_size = 0
        for file_path in directory.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size
    
    def _extract_assets(self, output_dir: Path) -> list:
        """提取构建产物列表"""
        assets = []
        if output_dir.exists():
            for file_path in output_dir.rglob("*"):
                if file_path.is_file():
                    relative_path = file_path.relative_to(output_dir)
                    assets.append(str(relative_path))
        return assets
    
    def _extract_errors(self, output: str) -> list:
        """从输出中提取错误信息"""
        errors = []
        lines = output.split('\n')
        
        for line in lines:
            # 检测常见的错误标记
            if any(marker in line.lower() for marker in ['error', 'failed', 'exception']):
                errors.append(line.strip())
        
        return errors
    
    def _extract_warnings(self, output: str) -> list:
        """从输出中提取警告信息"""
        warnings = []
        lines = output.split('\n')
        
        for line in lines:
            # 检测常见的警告标记
            if 'warning' in line.lower() or 'warn' in line.lower():
                warnings.append(line.strip())
        
        return warnings
    
    def preview_build(self, port: int = 4173) -> DevServerInfo:
        """
        预览构建结果
        
        Args:
            port: 预览服务器端口
            
        Returns:
            DevServerInfo: 预览服务器信息
        """
        cmd = self._get_preview_command(port)
        
        try:
            process = subprocess.Popen(
                cmd,
                cwd=self.project_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 等待服务器启动
            time.sleep(2)
            
            if process.poll() is not None:
                _, stderr = process.communicate()
                raise RuntimeError(f"预览服务器启动失败: {stderr}")
            
            return DevServerInfo(
                pid=process.pid,
                port=port,
                host="localhost",
                url=f"http://localhost:{port}",
                started_at=datetime.now(),
                is_running=True
            )
            
        except Exception as e:
            raise RuntimeError(f"启动预览服务器失败: {str(e)}")
    
    def _get_preview_command(self, port: int) -> list:
        """获取预览命令"""
        if self.package_manager == DependencyManager.NPM:
            return ["npm", "run", "preview", "--", "--port", str(port)]
        elif self.package_manager == DependencyManager.YARN:
            return ["yarn", "preview", "--port", str(port)]
        elif self.package_manager == DependencyManager.PNPM:
            return ["pnpm", "preview", "--port", str(port)]
        else:
            return ["npm", "run", "preview", "--", "--port", str(port)]
