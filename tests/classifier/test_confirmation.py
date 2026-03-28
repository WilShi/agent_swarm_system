"""
ConfirmationManager 测试
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.classifier.confirmation import ConfirmationManager
from src.core.types import (
    ClassificationResult,
    ConfirmationRequest,
    ConfirmationResponse,
    HarnessType,
    TaskType,
    IntentAnalysis
)


class TestConfirmationManager:
    """测试 ConfirmationManager"""

    @pytest.fixture
    def manager(self):
        return ConfirmationManager()

    @pytest.fixture
    def sample_classification_low_confidence(self):
        """低置信度分类结果"""
        return ClassificationResult(
            intent=IntentAnalysis(primary_intent="测试"),
            task_type=TaskType.GENERAL,
            harness_type=HarnessType.EXECUTION,
            confidence=0.5,  # 低置信度
            reasoning="测试",
            sub_tasks=[],
            requirements={},
            keywords=[],
            estimated_complexity="medium",
            estimated_duration=60
        )

    @pytest.fixture
    def sample_classification_high_confidence(self):
        """高置信度分类结果"""
        return ClassificationResult(
            intent=IntentAnalysis(primary_intent="测试"),
            task_type=TaskType.CODE,
            harness_type=HarnessType.CODE,
            confidence=0.95,  # 高置信度
            reasoning="测试",
            sub_tasks=[],
            requirements={},
            keywords=[],
            estimated_complexity="low",
            estimated_duration=30
        )

    @pytest.fixture
    def sample_classification_high_complexity(self):
        """高复杂度分类结果"""
        return ClassificationResult(
            intent=IntentAnalysis(primary_intent="测试"),
            task_type=TaskType.DEBUG,
            harness_type=HarnessType.DEBUG,
            confidence=0.8,
            reasoning="测试",
            sub_tasks=[],
            requirements={},
            keywords=[],
            estimated_complexity="high",  # 高复杂度
            estimated_duration=300
        )

    def test_needs_confirmation_low_confidence(self, manager, sample_classification_low_confidence):
        """测试低置信度需要确认"""
        assert manager.needs_confirmation(sample_classification_low_confidence) is True

    def test_needs_confirmation_high_complexity(self, manager, sample_classification_high_complexity):
        """测试高复杂度需要确认"""
        assert manager.needs_confirmation(sample_classification_high_complexity) is True

    def test_needs_confirmation_debug_type(self, manager):
        """测试 DEBUG 类型需要确认"""
        classification = ClassificationResult(
            intent=IntentAnalysis(primary_intent="测试"),
            task_type=TaskType.DEBUG,
            harness_type=HarnessType.DEBUG,
            confidence=0.8,
            reasoning="测试",
            sub_tasks=[],
            requirements={},
            keywords=[],
            estimated_complexity="medium",
            estimated_duration=60
        )
        assert manager.needs_confirmation(classification) is True

    def test_create_confirmation_request(self, manager, sample_classification_high_confidence):
        """测试创建确认请求"""
        request = manager.create_confirmation_request(sample_classification_high_confidence)

        assert isinstance(request, ConfirmationRequest)
        assert request.classification == sample_classification_high_confidence
        assert request.question != ""
        assert len(request.options) > 0
        assert request.timeout == 300
        assert request.allow_override is True

    def test_build_question_contains_harness_name(self, manager, sample_classification_high_confidence):
        """测试构建的问题包含 harness 名称"""
        question = manager._build_question(sample_classification_high_confidence)

        # 应该包含 harness 名称
        assert "代码生成" in question or "执行工具" in question
        # 应该包含置信度
        assert "95%" in question or "0.95" in question

    def test_build_options(self, manager, sample_classification_high_confidence):
        """测试构建选项"""
        options = manager._build_options(sample_classification_high_confidence)

        # 至少应该有确认和取消选项
        assert len(options) >= 2

        # 检查选项结构
        for option in options:
            assert "value" in option
            assert "label" in option

        # 应该有确认选项
        confirm_options = [o for o in options if o["value"] == "confirm"]
        assert len(confirm_options) > 0

    def test_get_harness_display_name(self, manager):
        """测试获取 Harness 显示名称"""
        assert manager._get_harness_display_name(HarnessType.CODE) == "代码生成"
        assert manager._get_harness_display_name(HarnessType.DEBUG) == "调试工具"
        assert manager._get_harness_display_name(HarnessType.TEST) == "测试工具"
        assert manager._get_harness_display_name(HarnessType.EXECUTION) == "通用执行"
        assert manager._get_harness_display_name(HarnessType.RESEARCH) == "研究分析"
        assert manager._get_harness_display_name(HarnessType.CLAUDE_CODE) == "Claude Code"

    def test_get_task_display_name(self, manager):
        """测试获取任务类型显示名称"""
        assert manager._get_task_display_name(TaskType.CODE) == "代码"
        assert manager._get_task_display_name(TaskType.DEBUG) == "调试"
        assert manager._get_task_display_name(TaskType.TEST) == "测试"
        assert manager._get_task_display_name(TaskType.ANALYSIS) == "分析"
        assert manager._get_task_display_name(TaskType.GENERAL) == "通用"

    def test_process_response_confirmed(self, manager, sample_classification_high_confidence):
        """测试处理确认响应"""
        request = manager.create_confirmation_request(sample_classification_high_confidence)

        response = ConfirmationResponse(
            confirmed=True,
            selected_harness=HarnessType.CODE
        )

        result = manager.process_response(request, response)

        assert isinstance(result, ClassificationResult)
        # 返回的是原分类结果（因为选择相同的 harness）
        assert result.harness_type == request.classification.harness_type

    def test_process_response_with_modification(self, manager, sample_classification_high_confidence):
        """测试处理带修改的响应"""
        request = manager.create_confirmation_request(sample_classification_high_confidence)

        response = ConfirmationResponse(
            confirmed=True,
            selected_harness=HarnessType.DEBUG,  # 更改 harness
            modifications={"estimated_duration": 120}
        )

        result = manager.process_response(request, response)

        assert isinstance(result, ClassificationResult)
        assert result.harness_type == HarnessType.DEBUG

    def test_create_quick_confirmation(self, manager, sample_classification_low_confidence):
        """测试创建快速确认"""
        request = manager.create_quick_confirmation(sample_classification_low_confidence)

        assert isinstance(request, ConfirmationRequest)
        assert request.timeout == 60  # 快速确认超时更短
        assert len(request.options) == 3  # 是/否/修改

    def test_get_alternative_harnesses(self, manager):
        """测试获取备选 harness"""
        alternatives = manager._get_alternative_harnesses(HarnessType.CODE)

        assert isinstance(alternatives, list)
        assert len(alternatives) <= 2  # 最多返回2个备选
        assert HarnessType.CODE not in alternatives  # 不包含当前 harness


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
