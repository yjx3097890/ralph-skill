"""
死循环检测器

检测重复的代码变更和错误信息，触发策略切换。
"""

import hashlib
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Deque, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CodeChange:
    """代码变更记录"""
    timestamp: datetime
    commit_hash: str
    files_changed: List[str]
    diff_hash: str  # diff 内容的哈希值
    message: str


@dataclass
class ErrorOccurrence:
    """错误发生记录"""
    timestamp: datetime
    error_hash: str  # 错误信息的哈希值
    error_message: str
    error_type: str
    task_id: Optional[str] = None


@dataclass
class DeadLoopPattern:
    """死循环模式"""
    pattern_type: str  # code_change, error_message
    occurrences: int
    confidence: float  # 置信度 (0.0 - 1.0)
    first_seen: datetime
    last_seen: datetime
    details: dict = field(default_factory=dict)


@dataclass
class DeadLoopConfig:
    """死循环检测配置"""
    max_code_change_repeats: int = 3  # 最大代码变更重复次数
    max_error_repeats: int = 3  # 最大错误重复次数
    history_window: int = 10  # 历史窗口大小
    min_confidence: float = 0.8  # 最小置信度阈值


class DeadLoopDetector:
    """
    死循环检测器
    
    功能：
    1. 检测重复的代码变更（连续 N 次相同提交）
    2. 检测重复的错误信息（连续 N 次相同报错）
    3. 分析模式和计算置信度
    4. 触发策略切换
    """
    
    def __init__(self, config: Optional[DeadLoopConfig] = None):
        """
        初始化死循环检测器
        
        Args:
            config: 检测配置
        """
        self.config = config or DeadLoopConfig()
        
        # 使用 deque 维护固定大小的历史窗口
        self.code_changes: Deque[CodeChange] = deque(
            maxlen=self.config.history_window
        )
        self.error_occurrences: Deque[ErrorOccurrence] = deque(
            maxlen=self.config.history_window
        )
        
        self.detected_patterns: List[DeadLoopPattern] = []
    
    def record_code_change(
        self,
        commit_hash: str,
        files_changed: List[str],
        diff_content: str,
        message: str = ""
    ) -> None:
        """
        记录代码变更
        
        Args:
            commit_hash: 提交哈希
            files_changed: 变更的文件列表
            diff_content: diff 内容
            message: 提交信息
        """
        # 计算 diff 内容的哈希值
        diff_hash = self._compute_hash(diff_content)
        
        change = CodeChange(
            timestamp=datetime.now(),
            commit_hash=commit_hash,
            files_changed=files_changed,
            diff_hash=diff_hash,
            message=message
        )
        
        self.code_changes.append(change)
        logger.debug(f"记录代码变更: {commit_hash[:8]}, diff_hash={diff_hash[:8]}")
    
    def record_error(
        self,
        error_message: str,
        error_type: str = "unknown",
        task_id: Optional[str] = None
    ) -> None:
        """
        记录错误发生
        
        Args:
            error_message: 错误信息
            error_type: 错误类型
            task_id: 任务 ID
        """
        # 计算错误信息的哈希值（忽略时间戳等动态内容）
        normalized_error = self._normalize_error_message(error_message)
        error_hash = self._compute_hash(normalized_error)
        
        occurrence = ErrorOccurrence(
            timestamp=datetime.now(),
            error_hash=error_hash,
            error_message=error_message,
            error_type=error_type,
            task_id=task_id
        )
        
        self.error_occurrences.append(occurrence)
        logger.debug(f"记录错误: {error_type}, error_hash={error_hash[:8]}")
    
    def detect_code_change_loop(self) -> Optional[DeadLoopPattern]:
        """
        检测代码变更死循环
        
        Returns:
            检测到的死循环模式，如果没有则返回 None
        """
        if len(self.code_changes) < self.config.max_code_change_repeats:
            return None
        
        # 检查最近 N 次变更是否相同
        recent_changes = list(self.code_changes)[-self.config.max_code_change_repeats:]
        
        # 获取最后一次变更的 diff_hash
        target_hash = recent_changes[-1].diff_hash
        
        # 检查是否所有变更都有相同的 diff_hash
        repeat_count = sum(1 for change in recent_changes if change.diff_hash == target_hash)
        
        if repeat_count >= self.config.max_code_change_repeats:
            # 计算置信度
            confidence = repeat_count / len(recent_changes)
            
            if confidence >= self.config.min_confidence:
                pattern = DeadLoopPattern(
                    pattern_type="code_change",
                    occurrences=repeat_count,
                    confidence=confidence,
                    first_seen=recent_changes[0].timestamp,
                    last_seen=recent_changes[-1].timestamp,
                    details={
                        "diff_hash": target_hash,
                        "files_changed": recent_changes[-1].files_changed,
                        "commits": [c.commit_hash for c in recent_changes]
                    }
                )
                
                self.detected_patterns.append(pattern)
                logger.warning(
                    f"检测到代码变更死循环: 连续 {repeat_count} 次相同变更, "
                    f"置信度={confidence:.2f}"
                )
                
                return pattern
        
        return None
    
    def detect_error_loop(self) -> Optional[DeadLoopPattern]:
        """
        检测错误信息死循环
        
        Returns:
            检测到的死循环模式，如果没有则返回 None
        """
        if len(self.error_occurrences) < self.config.max_error_repeats:
            return None
        
        # 检查最近 N 次错误是否相同
        recent_errors = list(self.error_occurrences)[-self.config.max_error_repeats:]
        
        # 获取最后一次错误的 error_hash
        target_hash = recent_errors[-1].error_hash
        
        # 检查是否所有错误都有相同的 error_hash
        repeat_count = sum(1 for error in recent_errors if error.error_hash == target_hash)
        
        if repeat_count >= self.config.max_error_repeats:
            # 计算置信度
            confidence = repeat_count / len(recent_errors)
            
            if confidence >= self.config.min_confidence:
                pattern = DeadLoopPattern(
                    pattern_type="error_message",
                    occurrences=repeat_count,
                    confidence=confidence,
                    first_seen=recent_errors[0].timestamp,
                    last_seen=recent_errors[-1].timestamp,
                    details={
                        "error_hash": target_hash,
                        "error_type": recent_errors[-1].error_type,
                        "error_message": recent_errors[-1].error_message
                    }
                )
                
                self.detected_patterns.append(pattern)
                logger.warning(
                    f"检测到错误信息死循环: 连续 {repeat_count} 次相同错误, "
                    f"置信度={confidence:.2f}"
                )
                
                return pattern
        
        return None
    
    def detect(self) -> List[DeadLoopPattern]:
        """
        执行死循环检测
        
        Returns:
            检测到的所有死循环模式列表
        """
        patterns = []
        
        # 检测代码变更死循环
        code_pattern = self.detect_code_change_loop()
        if code_pattern:
            patterns.append(code_pattern)
        
        # 检测错误信息死循环
        error_pattern = self.detect_error_loop()
        if error_pattern:
            patterns.append(error_pattern)
        
        return patterns
    
    def should_trigger_strategy_switch(self) -> bool:
        """
        判断是否应该触发策略切换
        
        Returns:
            True 如果应该切换策略，False 否则
        """
        patterns = self.detect()
        return len(patterns) > 0
    
    def get_statistics(self) -> dict:
        """
        获取检测统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "code_changes_recorded": len(self.code_changes),
            "errors_recorded": len(self.error_occurrences),
            "patterns_detected": len(self.detected_patterns),
            "config": {
                "max_code_change_repeats": self.config.max_code_change_repeats,
                "max_error_repeats": self.config.max_error_repeats,
                "history_window": self.config.history_window,
                "min_confidence": self.config.min_confidence
            }
        }
    
    def format_pattern(self, pattern: DeadLoopPattern) -> str:
        """
        格式化死循环模式为可读文本
        
        Args:
            pattern: 死循环模式
        
        Returns:
            格式化的文本
        """
        lines = [
            f"死循环模式检测:",
            f"  类型: {pattern.pattern_type}",
            f"  重复次数: {pattern.occurrences}",
            f"  置信度: {pattern.confidence:.2%}",
            f"  首次发现: {pattern.first_seen.strftime('%Y-%m-%d %H:%M:%S')}",
            f"  最后发现: {pattern.last_seen.strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]
        
        if pattern.pattern_type == "code_change":
            lines.extend([
                "  详细信息:",
                f"    变更文件: {', '.join(pattern.details.get('files_changed', []))}",
                f"    提交记录: {len(pattern.details.get('commits', []))} 个相同提交"
            ])
        elif pattern.pattern_type == "error_message":
            lines.extend([
                "  详细信息:",
                f"    错误类型: {pattern.details.get('error_type', 'unknown')}",
                f"    错误信息: {pattern.details.get('error_message', '')[:100]}..."
            ])
        
        return "\n".join(lines)
    
    def _compute_hash(self, content: str) -> str:
        """
        计算内容的哈希值
        
        Args:
            content: 内容字符串
        
        Returns:
            SHA256 哈希值
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _normalize_error_message(self, error_message: str) -> str:
        """
        规范化错误信息（移除动态内容）
        
        Args:
            error_message: 原始错误信息
        
        Returns:
            规范化后的错误信息
        """
        # 移除时间戳
        import re
        normalized = re.sub(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', '', error_message)
        
        # 移除内存地址
        normalized = re.sub(r'0x[0-9a-fA-F]+', '', normalized)
        
        # 移除临时文件路径中的随机部分
        normalized = re.sub(r'/tmp/[a-zA-Z0-9_-]+', '/tmp/TEMP', normalized)
        
        # 移除行号（可选，根据需求决定）
        # normalized = re.sub(r':\d+:', ':', normalized)
        
        return normalized.strip()
    
    def reset(self) -> None:
        """重置检测器状态"""
        self.code_changes.clear()
        self.error_occurrences.clear()
        self.detected_patterns.clear()
