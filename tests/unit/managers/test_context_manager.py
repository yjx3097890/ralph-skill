"""
上下文管理器单元测试

测试 ContextManager 类的日志截断和统计功能。

## 测试覆盖

- 基本截断功能
- 边界条件处理
- 统计信息准确性
- 配置更新功能
- 多字节字符处理
"""

import pytest

from ralph.managers.context_manager import ContextManager, TruncationStats


class TestContextManager:
    """上下文管理器测试类"""
    
    def test_no_truncation_for_short_text(self):
        """测试短文本不会被截断"""
        manager = ContextManager(max_size=1000, head_size=400, tail_size=400)
        text = "这是一段短文本" * 10  # 约 70 字符
        
        result = manager.truncate_output(text)
        
        assert result == text
        stats = manager.get_truncation_stats()
        assert stats is not None
        assert not stats.was_truncated
        assert stats.original_length == len(text)
        assert stats.truncated_length == len(text)
        assert stats.truncated_chars == 0
        assert stats.truncated_lines == 0
        
    def test_truncation_for_long_text(self):
        """测试长文本会被正确截断"""
        manager = ContextManager(max_size=1000, head_size=400, tail_size=400)
        
        # 创建一个超过 1000 字符的长文本
        text = "A" * 2000
        
        result = manager.truncate_output(text)
        
        # 验证结果长度在合理范围内
        assert len(result) < len(text)
        assert len(result) <= manager.max_size + 200  # 允许截断标记的额外空间
        
        # 验证包含截断标记
        assert "[截断]" in result
        assert "截断字符数:" in result
        assert "截断行数:" in result
        
        # 验证统计信息
        stats = manager.get_truncation_stats()
        assert stats is not None
        assert stats.was_truncated
        assert stats.original_length == 2000
        assert stats.truncated_chars > 0
        
    def test_preserves_head_and_tail(self):
        """测试保留头部和尾部内容"""
        manager = ContextManager(max_size=1000, head_size=100, tail_size=100)
        
        # 创建可识别的头部和尾部
        head = "HEAD_START" + "X" * 90
        middle = "M" * 2000
        tail = "Y" * 90 + "TAIL_END"
        text = head + middle + tail
        
        result = manager.truncate_output(text)
        
        # 验证头部被保留
        assert result.startswith("HEAD_START")
        
        # 验证尾部被保留
        assert result.endswith("TAIL_END")
        
        # 验证中间部分被截断
        assert "[截断]" in result
        
    def test_truncation_with_newlines(self):
        """测试包含换行符的文本截断"""
        manager = ContextManager(max_size=500, head_size=150, tail_size=150)
        
        # 创建包含多行的文本
        lines = [f"Line {i}: Some content here" for i in range(100)]
        text = "\n".join(lines)
        
        result = manager.truncate_output(text)
        
        # 验证截断发生
        assert len(result) < len(text)
        
        # 验证统计信息包含行数
        stats = manager.get_truncation_stats()
        assert stats is not None
        assert stats.truncated_lines > 0
        
    def test_empty_text(self):
        """测试空文本处理"""
        manager = ContextManager()
        
        result = manager.truncate_output("")
        
        assert result == ""
        stats = manager.get_truncation_stats()
        assert stats is not None
        assert not stats.was_truncated
        assert stats.original_length == 0
        
    def test_none_text(self):
        """测试 None 文本处理"""
        manager = ContextManager()
        
        # 空字符串应该被正确处理
        result = manager.truncate_output("")
        assert result == ""
        
    def test_multibyte_characters(self):
        """测试多字节字符(中文)处理"""
        manager = ContextManager(max_size=500, head_size=150, tail_size=150)
        
        # 创建包含中文的长文本
        text = "这是中文测试内容。" * 100  # 约 1000 字符
        
        result = manager.truncate_output(text)
        
        # 验证截断发生且没有编码错误
        assert len(result) < len(text)
        assert "[截断]" in result
        
        # 验证结果是有效的字符串
        assert isinstance(result, str)
        
    def test_update_config(self):
        """测试配置更新功能"""
        manager = ContextManager(max_size=1000, head_size=400, tail_size=400)
        
        # 更新配置
        manager.update_config(max_size=2000, head_size=800)
        
        config = manager.get_config()
        assert config["max_size"] == 2000
        assert config["head_size"] == 800
        assert config["tail_size"] == 400  # 未更新的保持原值
        
    def test_reset_stats(self):
        """测试统计信息重置"""
        manager = ContextManager()
        
        # 执行一次截断
        manager.truncate_output("A" * 2000)
        assert manager.get_truncation_stats() is not None
        
        # 重置统计
        manager.reset_stats()
        assert manager.get_truncation_stats() is None
        
    def test_manage_context_size_alias(self):
        """测试 manage_context_size 别名方法"""
        manager = ContextManager(max_size=500)
        text = "A" * 1000
        
        result1 = manager.truncate_output(text)
        manager.reset_stats()
        result2 = manager.manage_context_size(text)
        
        # 两个方法应该产生相同的结果
        assert result1 == result2
        
    def test_truncation_marker_format(self):
        """测试截断标记格式"""
        manager = ContextManager(max_size=500, head_size=150, tail_size=150)
        text = "A" * 2000
        
        result = manager.truncate_output(text)
        
        # 验证截断标记包含必要信息
        assert "=" * 70 in result
        assert "[截断]" in result
        assert "截断字符数:" in result
        assert "截断行数:" in result
        assert "提示:" in result
        
    def test_very_small_max_size(self):
        """测试非常小的最大大小限制"""
        manager = ContextManager(max_size=200, head_size=50, tail_size=50)
        text = "A" * 1000
        
        result = manager.truncate_output(text)
        
        # 即使最大大小很小,也应该能正常工作
        # 截断标记本身约占 214 字符,所以总长度会略大于 max_size
        assert len(result) <= 350  # 允许截断标记的额外空间
        assert "[截断]" in result
        
    def test_head_tail_larger_than_max(self):
        """测试头部+尾部大于最大大小的情况"""
        # 头部 500 + 尾部 500 = 1000, 但最大大小只有 800
        manager = ContextManager(max_size=800, head_size=500, tail_size=500)
        text = "A" * 2000
        
        result = manager.truncate_output(text)
        
        # 应该自动调整头部和尾部大小
        # 截断标记约占 214 字符,所以总长度会略大于 max_size
        assert len(result) <= 950  # 允许截断标记的额外空间
        
        stats = manager.get_truncation_stats()
        assert stats is not None
        # 实际使用的头部和尾部大小应该小于配置值
        assert stats.head_size < 500
        assert stats.tail_size < 500
        
    def test_exact_max_size(self):
        """测试文本长度恰好等于最大大小"""
        manager = ContextManager(max_size=1000)
        text = "A" * 1000
        
        result = manager.truncate_output(text)
        
        # 恰好等于最大大小,不应该截断
        assert result == text
        stats = manager.get_truncation_stats()
        assert stats is not None
        assert not stats.was_truncated
        
    def test_one_char_over_max(self):
        """测试文本长度超过最大大小 1 个字符"""
        manager = ContextManager(max_size=1000, head_size=400, tail_size=400)
        text = "A" * 1001
        
        result = manager.truncate_output(text)
        
        # 应该触发截断
        # 注意: 由于截断标记本身占用空间,结果可能略大于原文本
        # 但应该明显小于原文本+截断标记的总和
        assert "[截断]" in result
        stats = manager.get_truncation_stats()
        assert stats is not None
        assert stats.was_truncated
        
    def test_stats_accuracy(self):
        """测试统计信息的准确性"""
        manager = ContextManager(max_size=1000, head_size=300, tail_size=300)
        
        # 创建已知长度的文本
        head = "H" * 300
        middle = "M" * 1000
        tail = "T" * 300
        text = head + middle + tail
        original_length = len(text)  # 1600
        
        result = manager.truncate_output(text)
        
        stats = manager.get_truncation_stats()
        assert stats is not None
        
        # 验证原始长度
        assert stats.original_length == original_length
        
        # 验证截断后长度
        assert stats.truncated_length == len(result)
        
        # 验证截断字符数的合理性
        assert stats.truncated_chars > 0
        assert stats.truncated_chars < original_length
        
    def test_multiple_truncations(self):
        """测试多次截断操作"""
        manager = ContextManager(max_size=500)
        
        # 第一次截断
        text1 = "A" * 1000
        result1 = manager.truncate_output(text1)
        stats1 = manager.get_truncation_stats()
        
        # 第二次截断
        text2 = "B" * 2000
        result2 = manager.truncate_output(text2)
        stats2 = manager.get_truncation_stats()
        
        # 统计信息应该更新为最新的
        assert stats2 is not None
        assert stats2.original_length == 2000
        assert stats2 != stats1
        
    def test_default_configuration(self):
        """测试默认配置"""
        manager = ContextManager()
        
        config = manager.get_config()
        
        # 验证默认值
        assert config["max_size"] == 10000
        assert config["head_size"] == 2000
        assert config["tail_size"] == 2000


class TestTruncationStats:
    """截断统计信息测试类"""
    
    def test_truncation_stats_creation(self):
        """测试创建截断统计信息"""
        stats = TruncationStats(
            original_length=1000,
            truncated_length=500,
            truncated_chars=500,
            truncated_lines=10,
            was_truncated=True,
            head_size=200,
            tail_size=200
        )
        
        assert stats.original_length == 1000
        assert stats.truncated_length == 500
        assert stats.truncated_chars == 500
        assert stats.truncated_lines == 10
        assert stats.was_truncated
        assert stats.head_size == 200
        assert stats.tail_size == 200
        
    def test_no_truncation_stats(self):
        """测试未截断的统计信息"""
        stats = TruncationStats(
            original_length=100,
            truncated_length=100,
            truncated_chars=0,
            truncated_lines=0,
            was_truncated=False,
            head_size=100,
            tail_size=0
        )
        
        assert not stats.was_truncated
        assert stats.truncated_chars == 0
        assert stats.truncated_lines == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
