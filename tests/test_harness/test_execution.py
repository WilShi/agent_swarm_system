"""
ExecutionHarness 测试
"""
import pytest
from src.harness.execution import ExecutionHarness
from src.harness.factory import HarnessFactory
from src.core.types import (
    Task,
    HarnessConfig,
    HarnessType,
    TaskStatus,
    TaskType
)


class TestExecutionHarness:
    """ExecutionHarness 测试类"""

    @pytest.fixture
    def harness_config(self):
        return HarnessConfig(
            harness_type=HarnessType.EXECUTION,
            enabled=True,
            timeout=300
        )

    @pytest.fixture
    def execution_harness(self, harness_config):
        return ExecutionHarness(harness_config)

    @pytest.fixture
    def sample_task(self):
        return Task(
            task_id="test-task-123",
            description="Test execution task",
            task_type=TaskType.GENERAL
        )

    @pytest.mark.asyncio
    async def test_initialize(self, execution_harness):
        """测试初始化"""
        await execution_harness.initialize()
        assert execution_harness.is_initialized()

    @pytest.mark.asyncio
    async def test_execute(self, execution_harness, sample_task):
        """测试执行"""
        await execution_harness.initialize()
        result = await execution_harness.execute(sample_task)

        assert result.task_id == sample_task.task_id
        assert result.status == TaskStatus.COMPLETED.value
        assert result.output is not None
        assert "message" in result.output
        assert result.quality_score == 1.0

    @pytest.mark.asyncio
    async def test_execute_updates_task_status(self, execution_harness, sample_task):
        """测试执行更新任务状态"""
        await execution_harness.initialize()

        assert sample_task.status == TaskStatus.PENDING

        await execution_harness.execute(sample_task)

        assert sample_task.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_cleanup(self, execution_harness):
        """测试清理"""
        await execution_harness.initialize()
        assert execution_harness.is_initialized()

        await execution_harness.cleanup()
        assert not execution_harness.is_initialized()

    @pytest.mark.asyncio
    async def test_run_full_cycle(self, execution_harness, sample_task):
        """测试完整的运行周期"""
        result = await execution_harness.run(sample_task)

        assert result.task_id == sample_task.task_id
        assert result.status == TaskStatus.COMPLETED.value
        assert result.output is not None
        assert result.execution_time > 0

    @pytest.mark.asyncio
    async def test_run_already_initialized(self, execution_harness, sample_task):
        """测试已初始化时的运行"""
        await execution_harness.initialize()
        assert execution_harness.is_initialized()

        # 第二次运行不应重新初始化
        result = await execution_harness.run(sample_task)
        assert result.status == TaskStatus.COMPLETED.value

    def test_registration(self):
        """测试 ExecutionHarness 已注册"""
        assert HarnessFactory.is_registered(HarnessType.EXECUTION)

    @pytest.mark.asyncio
    async def test_create_via_factory(self):
        """测试通过工厂创建"""
        harness = HarnessFactory.create(HarnessType.EXECUTION)
        assert isinstance(harness, ExecutionHarness)
        assert harness.harness_type == HarnessType.EXECUTION

    @pytest.mark.asyncio
    async def test_result_metadata(self, execution_harness, sample_task):
        """测试结果元数据"""
        await execution_harness.initialize()
        result = await execution_harness.execute(sample_task)

        assert result.metadata is not None
        assert result.metadata["harness_type"] == HarnessType.EXECUTION.value
        assert "task_type" in result.metadata
