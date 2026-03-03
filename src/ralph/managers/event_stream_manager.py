"""
结构化事件流管理器

生成和输出 JSONL 格式的事件流,用于实时进度展示。
"""

import json
import logging
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, TextIO

logger = logging.getLogger(__name__)


class EventType(Enum):
    """事件类型"""
    TASK_START = "task_start"
    STEP_UPDATE = "step_update"
    GIT_COMMIT = "git_commit"
    TEST_RUN = "test_run"
    AI_CALL = "ai_call"
    ERROR = "error"
    TASK_COMPLETE = "task_complete"


@dataclass
class BaseEvent:
    """基础事件"""
    event_type: str
    timestamp: str
    task_id: Optional[str] = None


@dataclass
class TaskStartEvent(BaseEvent):
    """任务开始事件"""
    task_name: str = ""
    estimated_time: Optional[float] = None


@dataclass
class StepUpdateEvent(BaseEvent):
    """步骤更新事件"""
    step: str = ""
    status: str = ""  # pending, in_progress, completed, failed
    progress: Optional[float] = None


@dataclass
class GitCommitEvent(BaseEvent):
    """Git 提交事件"""
    commit_hash: str = ""
    message: str = ""
    files_changed: int = 0


@dataclass
class TestRunEvent(BaseEvent):
    """测试运行事件"""
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    duration: float = 0.0


@dataclass
class AICallEvent(BaseEvent):
    """AI 调用事件"""
    engine: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0


@dataclass
class ErrorEvent(BaseEvent):
    """错误事件"""
    error_type: str = ""
    error_message: str = ""
    stack_trace: Optional[str] = None


@dataclass
class TaskCompleteEvent(BaseEvent):
    """任务完成事件"""
    status: str = ""  # completed, failed, timeout
    summary: str = ""
    total_time: float = 0.0


class EventStreamManager:
    """
    结构化事件流管理器
    
    功能:
    1. 生成标准化事件
    2. 输出 JSONL 格式
    3. 支持多种输出目标(stdout/pipe)
    4. 事件缓冲和批处理
    """
    
    def __init__(self, output: Optional[TextIO] = None):
        """
        初始化事件流管理器
        
        Args:
            output: 输出流(默认为 stdout)
        """
        self.output = output or sys.stdout
        self.event_count = 0
        self.start_time: Optional[datetime] = None
    
    def emit_task_start(
        self,
        task_id: str,
        task_name: str,
        estimated_time: Optional[float] = None
    ) -> None:
        """
        发出任务开始事件
        
        Args:
            task_id: 任务 ID
            task_name: 任务名称
            estimated_time: 预估时间(秒)
        """
        self.start_time = datetime.now()
        
        event = TaskStartEvent(
            event_type=EventType.TASK_START.value,
            timestamp=self.start_time.isoformat(),
            task_id=task_id,
            task_name=task_name,
            estimated_time=estimated_time
        )
        
        self._emit_event(event)
    
    def emit_step_update(
        self,
        task_id: str,
        step: str,
        status: str,
        progress: Optional[float] = None
    ) -> None:
        """
        发出步骤更新事件
        
        Args:
            task_id: 任务 ID
            step: 步骤名称
            status: 状态
            progress: 进度(0.0-1.0)
        """
        event = StepUpdateEvent(
            event_type=EventType.STEP_UPDATE.value,
            timestamp=datetime.now().isoformat(),
            task_id=task_id,
            step=step,
            status=status,
            progress=progress
        )
        
        self._emit_event(event)
    
    def emit_git_commit(
        self,
        task_id: str,
        commit_hash: str,
        message: str,
        files_changed: int
    ) -> None:
        """
        发出 Git 提交事件
        
        Args:
            task_id: 任务 ID
            commit_hash: 提交哈希
            message: 提交信息
            files_changed: 变更文件数
        """
        event = GitCommitEvent(
            event_type=EventType.GIT_COMMIT.value,
            timestamp=datetime.now().isoformat(),
            task_id=task_id,
            commit_hash=commit_hash,
            message=message,
            files_changed=files_changed
        )
        
        self._emit_event(event)
    
    def emit_test_run(
        self,
        task_id: str,
        total_tests: int,
        passed: int,
        failed: int,
        skipped: int,
        duration: float
    ) -> None:
        """
        发出测试运行事件
        
        Args:
            task_id: 任务 ID
            total_tests: 总测试数
            passed: 通过数
            failed: 失败数
            skipped: 跳过数
            duration: 持续时间
        """
        event = TestRunEvent(
            event_type=EventType.TEST_RUN.value,
            timestamp=datetime.now().isoformat(),
            task_id=task_id,
            total_tests=total_tests,
            passed=passed,
            failed=failed,
            skipped=skipped,
            duration=duration
        )
        
        self._emit_event(event)
    
    def emit_ai_call(
        self,
        task_id: str,
        engine: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost: float
    ) -> None:
        """
        发出 AI 调用事件
        
        Args:
            task_id: 任务 ID
            engine: 引擎名称
            model: 模型名称
            input_tokens: 输入 token 数
            output_tokens: 输出 token 数
            cost: 成本
        """
        event = AICallEvent(
            event_type=EventType.AI_CALL.value,
            timestamp=datetime.now().isoformat(),
            task_id=task_id,
            engine=engine,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost
        )
        
        self._emit_event(event)
    
    def emit_error(
        self,
        task_id: str,
        error_type: str,
        error_message: str,
        stack_trace: Optional[str] = None
    ) -> None:
        """
        发出错误事件
        
        Args:
            task_id: 任务 ID
            error_type: 错误类型
            error_message: 错误信息
            stack_trace: 堆栈跟踪
        """
        event = ErrorEvent(
            event_type=EventType.ERROR.value,
            timestamp=datetime.now().isoformat(),
            task_id=task_id,
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace
        )
        
        self._emit_event(event)
    
    def emit_task_complete(
        self,
        task_id: str,
        status: str,
        summary: str
    ) -> None:
        """
        发出任务完成事件
        
        Args:
            task_id: 任务 ID
            status: 状态
            summary: 摘要
        """
        total_time = 0.0
        if self.start_time:
            total_time = (datetime.now() - self.start_time).total_seconds()
        
        event = TaskCompleteEvent(
            event_type=EventType.TASK_COMPLETE.value,
            timestamp=datetime.now().isoformat(),
            task_id=task_id,
            status=status,
            summary=summary,
            total_time=total_time
        )
        
        self._emit_event(event)
    
    def _emit_event(self, event: Any) -> None:
        """
        发出事件
        
        Args:
            event: 事件对象
        """
        try:
            # 转换为字典
            event_dict = asdict(event)
            
            # 输出 JSONL 格式(每行一个 JSON 对象)
            json_line = json.dumps(event_dict, ensure_ascii=False)
            self.output.write(json_line + '\n')
            self.output.flush()
            
            self.event_count += 1
            
        except Exception as e:
            logger.error(f"发出事件失败: {e}")
    
    def get_statistics(self) -> Dict[str, any]:
        """获取统计信息"""
        return {
            "total_events": self.event_count,
            "start_time": self.start_time.isoformat() if self.start_time else None
        }
