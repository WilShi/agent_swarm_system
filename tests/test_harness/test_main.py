"""
Main 模块测试
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.main import MultiHarnessAgentSwarm
from src.core.types import (
    ClassificationResult,
    IntentAnalysis,
    HarnessType,
    TaskType,
    TaskResult,
    TaskStatus
)

# Import to ensure ExecutionHarness is registered
from src.harness.execution import ExecutionHarness
from src.harness.factory import HarnessFactory


class TestMultiHarnessAgentSwarm:
    """MultiHarnessAgentSwarm 测试类"""

    @pytest.fixture(autouse=True)
    def setup_execution_harness(self):
        """确保 ExecutionHarness 已注册"""
        # Import triggers registration
        from src.harness.execution import ExecutionHarness
        if not HarnessFactory.is_registered(HarnessType.EXECUTION):
            HarnessFactory.register(HarnessType.EXECUTION, ExecutionHarness)
        yield

    @pytest.fixture
    def swarm(self):
        return MultiHarnessAgentSwarm()

    @pytest.fixture
    def mock_classification(self):
        return ClassificationResult(
            intent=IntentAnalysis(primary_intent="test"),
            task_type=TaskType.GENERAL,
            harness_type=HarnessType.EXECUTION,
            confidence=0.9,
            reasoning="Test reasoning",
            sub_tasks=[],
            requirements={},
            keywords=[],
            estimated_complexity="low",
            estimated_duration=60
        )

    @pytest.mark.asyncio
    async def test_init(self):
        """测试初始化"""
        swarm = MultiHarnessAgentSwarm()
        assert swarm.classifier is not None

    @pytest.mark.asyncio
    async def test_process_request(self, swarm, mock_classification):
        """测试处理请求"""
        with patch.object(
            swarm.classifier, 'classify', new_callable=AsyncMock
        ) as mock_classify:
            mock_classify.return_value = mock_classification

            result = await swarm.process_request("Test input")

            assert result["success"] is True
            assert "task_id" in result
            assert result["harness_type"] == HarnessType.EXECUTION.value
            assert "result" in result

    @pytest.mark.asyncio
    async def test_process_request_error(self, swarm):
        """测试处理请求错误"""
        with patch.object(
            swarm.classifier, 'classify', new_callable=AsyncMock
        ) as mock_classify:
            mock_classify.side_effect = Exception("Test error")

            result = await swarm.process_request("Test input")

            assert result["success"] is False
            assert "error" in result
            assert "Test error" in result["error"]

    @pytest.mark.asyncio
    async def test_process_with_confirmation_no_confirm(self, swarm, mock_classification):
        """测试处理无需确认的请求"""
        with patch.object(
            swarm.classifier, 'classify_with_confirmation', new_callable=AsyncMock
        ) as mock_method:
            mock_method.return_value = (mock_classification, None)

            with patch.object(
                swarm.classifier, 'classify', new_callable=AsyncMock
            ) as mock_classify:
                mock_classify.return_value = mock_classification

                result = await swarm.process_with_confirmation("Test input")

                assert result["success"] is True

    @pytest.mark.asyncio
    async def test_process_with_confirmation_needed(self, swarm, mock_classification):
        """测试需要确认的请求"""
        from src.core.types import ConfirmationRequest

        confirmation = ConfirmationRequest(
            classification=mock_classification,
            question="Confirm?",
            options=[]
        )

        with patch.object(
            swarm.classifier, 'classify_with_confirmation', new_callable=AsyncMock
        ) as mock_method:
            mock_method.return_value = (mock_classification, confirmation)

            result = await swarm.process_with_confirmation("Test input")

            assert result["success"] is False
            assert result["needs_confirmation"] is True
            assert "confirmation" in result

    @pytest.mark.asyncio
    async def test_batch_process(self, swarm, mock_classification):
        """测试批量处理"""
        inputs = ["Task 1", "Task 2", "Task 3"]

        with patch.object(
            swarm.classifier, 'classify', new_callable=AsyncMock
        ) as mock_classify:
            mock_classify.return_value = mock_classification

            results = await swarm.batch_process(inputs)

            assert len(results) == 3
            for result in results:
                assert result["success"] is True

    @pytest.mark.asyncio
    async def test_get_classifier(self, swarm):
        """测试获取分类器"""
        classifier = swarm.get_classifier()
        assert classifier is not None
        assert classifier == swarm.classifier

    @pytest.mark.asyncio
    async def test_process_request_with_context(self, swarm, mock_classification):
        """测试带上下文的请求处理"""
        context = {"user_id": "123", "session": "abc"}

        with patch.object(
            swarm.classifier, 'classify', new_callable=AsyncMock
        ) as mock_classify:
            mock_classify.return_value = mock_classification

            result = await swarm.process_request("Test input", context)

            assert result["success"] is True
            mock_classify.assert_called_once_with("Test input", context)
