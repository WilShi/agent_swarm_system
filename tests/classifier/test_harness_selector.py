"""
HarnessSelector 测试
"""
import pytest
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.classifier.harness_selector import HarnessSelector
from src.core.types import HarnessType, TaskType, IntentAnalysis


class TestHarnessSelector:
    """测试 HarnessSelector"""

    @pytest.fixture
    def selector(self):
        return HarnessSelector()

    @pytest.fixture
    def sample_intent(self):
        return IntentAnalysis(
            primary_intent="编写一个 Python 函数",
            secondary_intents=["代码生成"],
            entities={"language": "python"},
            sentiment="neutral",
            urgency="normal"
        )

    def test_keyword_pre_screening_code(self, selector):
        """测试代码相关关键词预筛选"""
        intent = IntentAnalysis(
            primary_intent="编写函数",
            secondary_intents=[],
            entities={},
            sentiment="neutral",
            urgency="normal"
        )

        hints = selector._keyword_pre_screening("编写一个排序函数", intent)

        # 应该匹配到 CODE harness
        assert "code" in hints["harness_hints"] or len(hints["harness_hints"]) > 0

    def test_keyword_pre_screening_debug(self, selector):
        """测试调试相关关键词预筛选"""
        intent = IntentAnalysis(
            primary_intent="修复错误",
            secondary_intents=[],
            entities={},
            sentiment="negative",
            urgency="high"
        )

        hints = selector._keyword_pre_screening("这个 bug 怎么修复？", intent)

        # 应该匹配到 DEBUG harness
        assert len(hints["harness_hints"]) > 0

    def test_parse_harness_type(self, selector):
        """测试解析 HarnessType"""
        assert selector._parse_harness_type("code") == HarnessType.CODE
        assert selector._parse_harness_type("debug") == HarnessType.DEBUG
        assert selector._parse_harness_type("test") == HarnessType.TEST
        assert selector._parse_harness_type("claude_code") == HarnessType.CLAUDE_CODE
        assert selector._parse_harness_type("unknown") == HarnessType.EXECUTION

    def test_parse_task_type(self, selector):
        """测试解析 TaskType"""
        assert selector._parse_task_type("code") == TaskType.CODE
        assert selector._parse_task_type("debug") == TaskType.DEBUG
        assert selector._parse_task_type("test") == TaskType.TEST
        assert selector._parse_task_type("analysis") == TaskType.ANALYSIS
        assert selector._parse_task_type("unknown") == TaskType.GENERAL

    def test_extract_json(self, selector):
        """测试 JSON 提取"""
        text = '```json\n{"key": "value"}\n```'
        result = selector._extract_json(text)
        assert result == '{"key": "value"}'

    def test_get_default_result(self, selector):
        """测试获取默认结果"""
        result = selector._get_default_result()

        assert result[0] == HarnessType.EXECUTION
        assert result[1] == TaskType.GENERAL
        assert result[2] == 0.5
        assert result[3] == "使用默认配置"

    def test_get_harness_recommendations(self, selector):
        """测试获取 Harness 推荐"""
        intent = IntentAnalysis(
            primary_intent="编写代码",
            secondary_intents=[],
            entities={},
            sentiment="neutral",
            urgency="normal"
        )

        recommendations = selector.get_harness_recommendations(intent)

        # 验证返回列表
        assert isinstance(recommendations, list)
        # 每个推荐项应该是 (HarnessType, score) 元组
        for rec in recommendations:
            assert isinstance(rec, tuple)
            assert len(rec) == 2
            assert isinstance(rec[0], HarnessType)
            assert isinstance(rec[1], float)

    @pytest.mark.asyncio
    async def test_select_returns_tuple(self, selector, sample_intent):
        """测试 select 方法返回元组"""
        result = await selector.select("测试输入", sample_intent)

        # 验证返回的是9个元素的元组
        assert isinstance(result, tuple)
        assert len(result) == 9

        # 验证类型
        assert isinstance(result[0], HarnessType)
        assert isinstance(result[1], TaskType)
        assert isinstance(result[2], float)  # confidence
        assert isinstance(result[3], str)     # reasoning
        assert isinstance(result[4], list)    # sub_tasks
        assert isinstance(result[5], dict)    # requirements
        assert isinstance(result[6], list)    # keywords
        assert isinstance(result[7], str)     # estimated_complexity
        assert isinstance(result[8], int)     # estimated_duration


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
