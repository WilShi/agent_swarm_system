"""
IntentAnalyzer 测试
"""
import pytest
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.classifier.intent_analyzer import IntentAnalyzer
from src.core.types import IntentAnalysis


class TestIntentAnalyzer:
    """测试 IntentAnalyzer"""

    @pytest.fixture
    def analyzer(self):
        return IntentAnalyzer()

    def test_extract_json_with_markdown(self, analyzer):
        """测试从 markdown 代码块提取 JSON"""
        text = """```json
{"primary_intent": "test", "sentiment": "neutral"}
```"""
        result = analyzer._extract_json(text)
        assert result == '{"primary_intent": "test", "sentiment": "neutral"}'

    def test_extract_json_without_markdown(self, analyzer):
        """测试直接提取 JSON"""
        text = '{"primary_intent": "test", "sentiment": "neutral"}'
        result = analyzer._extract_json(text)
        assert result == text

    def test_intent_analysis_structure(self, analyzer):
        """测试意图分析结果结构"""
        intent = IntentAnalysis(
            primary_intent="测试意图",
            secondary_intents=["次要意图1"],
            entities={"key": "value"},
            sentiment="positive",
            urgency="high"
        )

        assert intent.primary_intent == "测试意图"
        assert "次要意图1" in intent.secondary_intents
        assert intent.entities["key"] == "value"
        assert intent.sentiment == "positive"
        assert intent.urgency == "high"

    @pytest.mark.asyncio
    async def test_analyze_default_response(self, analyzer):
        """测试分析返回默认响应（模拟 LLM 失败情况）"""
        # 注意：此测试可能失败如果 LLM 正常响应
        # 主要用于验证错误处理逻辑
        result = await analyzer.analyze("这是一个测试输入")

        # 验证返回的是 IntentAnalysis 类型
        assert isinstance(result, IntentAnalysis)
        assert hasattr(result, 'primary_intent')
        assert hasattr(result, 'secondary_intents')
        assert hasattr(result, 'entities')
        assert hasattr(result, 'sentiment')
        assert hasattr(result, 'urgency')

    @pytest.mark.asyncio
    async def test_analyze_batch(self, analyzer):
        """测试批量分析"""
        inputs = ["输入1", "输入2", "输入3"]
        results = await analyzer.analyze_batch(inputs)

        assert len(results) == 3
        for result in results:
            assert isinstance(result, IntentAnalysis)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
