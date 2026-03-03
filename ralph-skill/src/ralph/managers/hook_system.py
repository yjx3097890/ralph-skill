"""
钩子系统管理器

负责钩子的注册、执行和生命周期管理。

## 核心功能
- 钩子注册和管理
- 钩子执行和超时控制
- 钩子重试机制
- 钩子执行历史记录
- 并发安全保护

## 钩子类型
- PRE_TASK: 任务开始前执行
- PRE_TEST: 测试前执行（代码格式化）
- POST_TEST: 测试后执行（清理临时文件）
- POST_TASK: 任务完成后执行

## 使用示例
```python
hook_system = HookSystem()

# 注册钩子
hook_config = HookConfig(
    name="format_code",
    hook_type=HookType.PRE_TEST,
    command="black .",
    timeout=60
)
hook_system.register_hook(hook_config)

# 执行钩子
context = HookContext(
    hook_type=HookType.PRE_TEST,
    task_id="task_1",
    task_name="实现用户认证",
    timestamp=datetime.now(),
    working_directory="/path/to/project"
)
results = hook_system.execute_hooks(HookType.PRE_TEST, context)
```
"""

import logging
import os
import subprocess
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional

from ..models.enums import HookType
from ..models.hook import (
    HookConfig,
    HookContext,
    HookExecutionRecord,
    HookResult,
)

logger = logging.getLogger(__name__)


class HookExecutionError(Exception):
    """钩子执行错误"""
    pass


class HookTimeoutError(Exception):
    """钩子超时错误"""
    pass


class HookSystem:
    """
    钩子系统管理器
    
    管理钩子的完整生命周期，包括注册、执行、重试和历史记录。
    使用线程锁保证并发安全。
    """
    
    def __init__(self):
        """初始化钩子系统"""
        # 钩子注册表：hook_type -> [HookConfig]
        self._hooks: Dict[HookType, List[HookConfig]] = {
            hook_type: [] for hook_type in HookType
        }
        
        # 钩子执行历史
        self._execution_history: List[HookExecutionRecord] = []
        
        # 线程锁保护共享状态
        self._lock = threading.RLock()
        
        logger.info("钩子系统已初始化")
    
    def register_hook(self, config: HookConfig) -> None:
        """
        注册钩子
        
        Args:
            config: 钩子配置
            
        Raises:
            ValueError: 如果钩子名称已存在
        """
        with self._lock:
            # 检查钩子名称是否已存在
            existing_hooks = self._hooks[config.hook_type]
            if any(h.name == config.name for h in existing_hooks):
                raise ValueError(
                    f"钩子名称已存在: {config.name} (类型: {config.hook_type.value})"
                )
            
            # 注册钩子
            self._hooks[config.hook_type].append(config)
            
            logger.info(
                f"钩子已注册: {config.name} "
                f"(类型: {config.hook_type.value}, 命令: {config.command})"
            )
    
    def unregister_hook(self, hook_type: HookType, hook_name: str) -> bool:
        """
        注销钩子
        
        Args:
            hook_type: 钩子类型
            hook_name: 钩子名称
            
        Returns:
            如果成功注销返回 True，如果钩子不存在返回 False
        """
        with self._lock:
            hooks = self._hooks[hook_type]
            original_count = len(hooks)
            
            # 移除匹配的钩子
            self._hooks[hook_type] = [h for h in hooks if h.name != hook_name]
            
            removed = len(self._hooks[hook_type]) < original_count
            
            if removed:
                logger.info(f"钩子已注销: {hook_name} (类型: {hook_type.value})")
            
            return removed
    
    def get_hooks(self, hook_type: HookType) -> List[HookConfig]:
        """
        获取指定类型的所有钩子
        
        Args:
            hook_type: 钩子类型
            
        Returns:
            钩子配置列表
        """
        with self._lock:
            return list(self._hooks[hook_type])
    
    def execute_hooks(
        self, 
        hook_type: HookType, 
        context: HookContext
    ) -> List[HookResult]:
        """
        执行指定类型的所有钩子
        
        Args:
            hook_type: 钩子类型
            context: 钩子执行上下文
            
        Returns:
            钩子执行结果列表
            
        Raises:
            HookExecutionError: 如果有钩子执行失败且 continue_on_failure 为 False
        """
        with self._lock:
            hooks = self.get_hooks(hook_type)
        
        if not hooks:
            logger.debug(f"没有注册的 {hook_type.value} 钩子")
            return []
        
        logger.info(f"开始执行 {len(hooks)} 个 {hook_type.value} 钩子")
        
        results = []
        for hook_config in hooks:
            result = self._execute_single_hook(hook_config, context)
            results.append(result)
            
            # 如果钩子失败且不允许继续，抛出异常
            if not result.success and not hook_config.continue_on_failure:
                error_msg = (
                    f"钩子执行失败: {hook_config.name} "
                    f"(类型: {hook_type.value})"
                )
                logger.error(error_msg)
                raise HookExecutionError(error_msg)
        
        # 统计执行结果
        success_count = sum(1 for r in results if r.success)
        logger.info(
            f"{hook_type.value} 钩子执行完成: "
            f"{success_count}/{len(results)} 成功"
        )
        
        return results
    
    def _execute_single_hook(
        self, 
        config: HookConfig, 
        context: HookContext
    ) -> HookResult:
        """
        执行单个钩子（带重试机制）
        
        Args:
            config: 钩子配置
            context: 钩子执行上下文
            
        Returns:
            钩子执行结果
        """
        # 创建执行记录
        record = HookExecutionRecord(
            hook_name=config.name,
            hook_type=config.hook_type,
            task_id=context.task_id,
            started_at=datetime.now(),
        )
        
        # 尝试执行（包括重试）
        result = None
        for attempt in range(config.max_retries + 1):
            try:
                result = self._run_hook_command(config, context)
                
                if result.success:
                    break  # 成功则退出重试循环
                
                # 失败但还有重试机会
                if attempt < config.max_retries:
                    logger.warning(
                        f"钩子执行失败，将在 {config.retry_delay} 秒后重试 "
                        f"(尝试 {attempt + 1}/{config.max_retries + 1}): "
                        f"{config.name}"
                    )
                    time.sleep(config.retry_delay)
                    record.retry_count += 1
                
            except Exception as e:
                logger.error(f"钩子执行异常: {config.name}, 错误: {str(e)}")
                result = HookResult(
                    success=False,
                    hook_type=config.hook_type,
                    hook_name=config.name,
                    execution_time=0.0,
                    error=str(e),
                    exit_code=-1,
                )
                
                # 如果还有重试机会，继续重试
                if attempt < config.max_retries:
                    time.sleep(config.retry_delay)
                    record.retry_count += 1
        
        # 更新执行记录
        record.completed_at = datetime.now()
        record.result = result
        
        # 保存执行历史
        with self._lock:
            self._execution_history.append(record)
        
        return result
    
    def _run_hook_command(
        self, 
        config: HookConfig, 
        context: HookContext
    ) -> HookResult:
        """
        运行钩子命令
        
        Args:
            config: 钩子配置
            context: 钩子执行上下文
            
        Returns:
            钩子执行结果
            
        Raises:
            HookTimeoutError: 如果执行超时
        """
        start_time = time.time()
        
        # 确定工作目录
        working_dir = config.working_directory or context.working_directory
        
        # 合并环境变量
        env = os.environ.copy()
        env.update(context.environment)
        env.update(config.environment)
        
        logger.info(
            f"执行钩子命令: {config.name} "
            f"(命令: {config.command}, 工作目录: {working_dir})"
        )
        
        try:
            # 执行命令
            process = subprocess.Popen(
                config.command,
                shell=True,
                cwd=working_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            
            # 等待命令完成（带超时）
            try:
                stdout, stderr = process.communicate(timeout=config.timeout)
                exit_code = process.returncode
            except subprocess.TimeoutExpired:
                # 超时，终止进程
                process.kill()
                stdout, stderr = process.communicate()
                
                execution_time = time.time() - start_time
                
                error_msg = f"钩子执行超时 ({config.timeout}秒): {config.name}"
                logger.error(error_msg)
                
                return HookResult(
                    success=False,
                    hook_type=config.hook_type,
                    hook_name=config.name,
                    execution_time=execution_time,
                    output=stdout,
                    error=error_msg,
                    exit_code=-1,
                )
            
            execution_time = time.time() - start_time
            
            # 构建结果
            success = exit_code == 0
            output = stdout.strip() if stdout else ""
            error = stderr.strip() if stderr and not success else None
            
            # 检测修改的文件（如果是格式化钩子）
            modified_files = []
            if config.hook_type == HookType.PRE_TEST and success:
                # 这里可以通过 git status 检测修改的文件
                # 简化实现，暂时留空
                pass
            
            result = HookResult(
                success=success,
                hook_type=config.hook_type,
                hook_name=config.name,
                execution_time=execution_time,
                output=output,
                error=error,
                exit_code=exit_code,
                modified_files=modified_files,
            )
            
            if success:
                logger.info(
                    f"钩子执行成功: {config.name} "
                    f"({execution_time:.2f}秒)"
                )
            else:
                logger.warning(
                    f"钩子执行失败: {config.name} "
                    f"(退出码: {exit_code}, 耗时: {execution_time:.2f}秒)"
                )
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            logger.error(f"钩子执行异常: {config.name}, 错误: {str(e)}")
            
            return HookResult(
                success=False,
                hook_type=config.hook_type,
                hook_name=config.name,
                execution_time=execution_time,
                error=str(e),
                exit_code=-1,
            )
    
    def get_execution_history(
        self, 
        task_id: Optional[str] = None,
        hook_type: Optional[HookType] = None,
        limit: Optional[int] = None
    ) -> List[HookExecutionRecord]:
        """
        获取钩子执行历史
        
        Args:
            task_id: 可选的任务 ID 过滤器
            hook_type: 可选的钩子类型过滤器
            limit: 可选的结果数量限制
            
        Returns:
            钩子执行记录列表（按时间倒序）
        """
        with self._lock:
            records = list(self._execution_history)
        
        # 应用过滤器
        if task_id is not None:
            records = [r for r in records if r.task_id == task_id]
        
        if hook_type is not None:
            records = [r for r in records if r.hook_type == hook_type]
        
        # 按时间倒序排序
        records.sort(key=lambda r: r.started_at, reverse=True)
        
        # 应用限制
        if limit is not None and limit > 0:
            records = records[:limit]
        
        return records
    
    def clear_execution_history(self) -> None:
        """清空执行历史"""
        with self._lock:
            self._execution_history.clear()
        
        logger.info("钩子执行历史已清空")
    
    def get_statistics(self) -> Dict[str, any]:
        """
        获取钩子系统统计信息
        
        Returns:
            统计信息字典
        """
        with self._lock:
            total_hooks = sum(len(hooks) for hooks in self._hooks.values())
            total_executions = len(self._execution_history)
            successful_executions = sum(
                1 for r in self._execution_history if r.is_successful
            )
            
            stats = {
                "total_registered_hooks": total_hooks,
                "hooks_by_type": {
                    hook_type.value: len(hooks)
                    for hook_type, hooks in self._hooks.items()
                },
                "total_executions": total_executions,
                "successful_executions": successful_executions,
                "failed_executions": total_executions - successful_executions,
                "success_rate": (
                    successful_executions / total_executions * 100
                    if total_executions > 0 else 0.0
                ),
            }
            
            return stats

