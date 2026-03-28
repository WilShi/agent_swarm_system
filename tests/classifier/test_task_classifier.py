"""
TaskClassifier 测试
"""
import pytest
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.classifier.task_classifier import TaskClassifier
from src.classifier.intent_analyzer import IntentAnalyzer
from src.classifier.harness_selector import HarnessSelector
from src.classifier.confirmation import ConfirmationManager
from src.core.types import (
    ClassificationResult,
    ConfirmationRequest,
    ConfirmationResponse,
    HarnessType,
    TaskType
)


class TestTaskClassifier:
    """测试 TaskClassifier"""

    @pytest.fixture
    def classifier(self):
        return TaskClassifier()

    def test_initialization(self, classifier):
        """测试初始化"""
        assert isinstance(classifier.intent_analyzer, IntentAnalyzer)
        assert isinstance(classifier.harness_selector, HarnessSelector)
        assert isinstance(classifier.confirmation_manager, ConfirmationManager)

    @pytest.mark.asyncio
    async def test_classify_returns_result(self, classifier):
        """测试 classify 返回 ClassificationResult"""
        result = await classifier.classify("测试输入")

        assert isinstance(result, ClassificationResult)
        assert hasattr(result, 'intent')
        assert hasattr(result, 'task_type')
        assert hasattr(result, 'harness_type')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'reasoning')

    @pytest.mark.asyncio
    async def test_classify_with_context(self, classifier):
        """测试带上下文的分类"""
        context = {"previous_task": "test", "user_id": "123"}
        result = await classifier.classify("测试输入", context)

        assert isinstance(result, ClassificationResult)

    @pytest.mark.asyncio
    async def test_classify_with_confirmation_low_confidence(self, classifier):
        """测试低置信度分类需要确认"""
        # 使用一个模糊的输入，可能导致低置信度
        result, confirmation = await classifier.classify_with_confirmation(
            "随便做点什么"
        )

        assert isinstance(result, ClassificationResult)
        # 可能返回确认请求（取决于置信度）
        if confirmation is not None:
            assert isinstance(confirmation, ConfirmationRequest)

    @pytest.mark.asyncio
    async def test_classify_batch(self, classifier):
        """测试批量分类"""
        inputs = ["输入1", "输入2", "输入3"]
        results = await classifier.classify_batch(inputs)

        assert len(results) == 3
        for result in results:
            assert isinstance(result, ClassificationResult)

    def test_get_intent_analyzer(self, classifier):
        """测试获取 intent_analyzer"""
        analyzer = classifier.get_intent_analyzer()
        assert isinstance(analyzer, IntentAnalyzer)
        assert analyzer is classifier.intent_analyzer

    def test_get_harness_selector(self, classifier):
        """测试获取 harness_selector"""
        selector = classifier.get_harness_selector()
        assert isinstance(selector, HarnessSelector)
        assert selector is classifier.harness_selector

    def test_get_confirmation_manager(self, classifier):
        """测试获取 confirmation_manager"""
        manager = classifier.get_confirmation_manager()
        assert isinstance(manager, ConfirmationManager)
        assert manager is classifier.confirmation_manager

    def test_process_confirmation_response(self, classifier):
        """测试处理确认响应"""
        from src.core.types import IntentAnalysis

        # 创建测试用的分类结果
        classification = ClassificationResult(
            intent=IntentAnalysis(primary_intent="测试"),
            task_type=TaskType.GENERAL,
            harness_type=HarnessType.EXECUTION,
            confidence=0.5,
            reasoning="测试",
            sub_tasks=[],
            requirements={},
            keywords=[],
            estimated_complexity="medium",
            estimated_duration=60
        )

        request = ConfirmationRequest(
            classification=classification,
            question="确认执行？",
            options=[{"value": "yes", "label": "是"}],
            timeout=300,
            allow_override=True
        )

        response = ConfirmationResponse(
            confirmed=True,
            selected_harness=HarnessType.CODE
        )

        result = classifier.process_confirmation_response(request, response)

        assert isinstance(result, ClassificationResult)


class TestTaskClassifierIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_end_to_end_flow(self):
        """测试端到端流程"""
        classifier = TaskClassifier()

        # 1. 分类用户输入
        result = await classifier.classify("编写一个 Python 函数来计算斐波那契数列")

        # 2. 验证结果
        assert isinstance(result, ClassificationResult)
        assert result.intent is not None

        # 3. 检查是否需要确认
        manager = classifier.get_confirmation_manager()
        needs_confirm = manager.needs_confirmation(result)

        # 验证方法正常工作
        assert isinstance(needs_confirm, bool)

        # 4. 如果需要确认，创建请求
        if needs_confirm:
            confirmation = manager.create_confirmation_request(result)
            assert isinstance(confirmation, ConfirmationRequest)

    @pytest.mark.asyncio
    async def test_multiple_inputs(self):
        """测试多个不同类型的输入"""
        classifier = TaskClassifier()

        inputs = [
            "帮我调试这个错误",
            "写一个单元测试",
            "分析一下这段代码",
            "搜索相关信息"
        ]

        for user_input in inputs:
            result = await classifier.classify(user_input)
            assert isinstance(result, ClassificationResult)
            assert result.intent is not None
            assert result.task_type is not None
            assert result.harness_type is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
