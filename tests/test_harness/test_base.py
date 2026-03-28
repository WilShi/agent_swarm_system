"""
BaseHarness 测试
"""
import pytest
from src.harness.base import BaseHarness
from src.core.types import HarnessConfig, HarnessType, Task, TaskResult


class MockHarness(BaseHarness):
    """测试用的 Mock Harness"""

    async def initialize(self):
        self._initialized = True

    async def execute(self, task: Task) -> TaskResult:
        return TaskResult(
            task_id=task.task_id,
            status="completed",
            output={"message": "Mock execution"}
        )

    async def cleanup(self):
        self._initialized = False


@pytest.fixture
def harness_config():
    return HarnessConfig(
        harness_type=HarnessType.EXECUTION,
        enabled=True,
        timeout=300
    )


@pytest.fixture
def mock_harness(harness_config):
    return MockHarness(harness_config)


@pytest.fixture
def sample_task():
    return Task(description="Test task")


class TestBaseHarness:
    """BaseHarness 测试类"""

    def test_init(self, harness_config):
        """测试初始化"""
        harness = MockHarness(harness_config)
        assert harness.config == harness_config
        assert harness.harness_type == HarnessType.EXECUTION
        assert not harness.is_initialized()

    @pytest.mark.asyncio
    async def test_run(self, mock_harness, sample_task):
        """测试 run 方法"""
        result = await mock_harness.run(sample_task)

        assert isinstance(result, TaskResult)
        assert result.status == "completed"
        assert result.output["message"] == "Mock execution"
        assert mock_harness.is_initialized()

    @pytest.mark.asyncio
    async def test_run_error_handling(self, harness_config):
        """测试 run 方法的错误处理"""
        class ErrorHarness(BaseHarness):
            async def initialize(self):
                pass

            async def execute(self, task: Task) -> TaskResult:
                raise ValueError("Test error")

            async def cleanup(self):
                pass

        harness = ErrorHarness(harness_config)
        task = Task(description="Error task")

        result = await harness.run(task)

        assert result.status == "failed"
        assert len(result.errors) > 0
        assert "Test error" in result.errors[0]

    @pytest.mark.asyncio
    async def test_initialize(self, mock_harness):
        """测试初始化"""
        await mock_harness.initialize()
        assert mock_harness.is_initialized()

    @pytest.mark.asyncio
    async def test_cleanup(self, mock_harness):
        """测试清理"""
        await mock_harness.initialize()
        assert mock_harness.is_initialized()

        await mock_harness.cleanup()
        assert not mock_harness.is_initialized()

    def test_get_config(self, mock_harness, harness_config):
        """测试获取配置"""
        config = mock_harness.get_config()
        assert config == harness_config
