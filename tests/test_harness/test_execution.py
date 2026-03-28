"""
ExecutionHarness 测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
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

    @pytest.fixture
    def mock_swarm_manager(self):
        """模拟 SwarmManager"""
        mock = AsyncMock()
        mock.start = AsyncMock()
        mock.stop = AsyncMock()
        mock.submit_task = AsyncMock(return_value="swarm-task-456")
        # _wait_with_progress 使用 get_task_status 而不是 wait_for_task
        # 使用 side_effect 来返回不同的值，第一次返回进行中，第二次返回完成
        call_count = [0]
        async def mock_get_task_status(task_id):
            call_count[0] += 1
            if call_count[0] == 1:
                return {
                    "status": "in_progress",
                    "result": None,
                    "subtasks_count": 3,
                    "completed_subtasks": 1,
                    "failed_subtasks": 0,
                    "pending_subtasks": 2
                }
            else:
                return {
                    "status": "completed",
                    "result": {"message": "Task completed successfully"},
                    "quality_score": 0.85,
                    "subtasks_count": 3,
                    "completed_subtasks": 3,
                    "failed_subtasks": 0,
                    "pending_subtasks": 0
                }
        mock.get_task_status = mock_get_task_status
        # 设置 executors, validators, integrators 为字典
        mock.executors = {}
        mock.validators = {}
        mock.integrators = {}
        mock.coordinator = None
        return mock

    @pytest.mark.asyncio
    async def test_initialize(self, execution_harness, mock_swarm_manager):
        """测试初始化"""
        with patch('src.harness.execution.SwarmManager', return_value=mock_swarm_manager):
            await execution_harness.initialize()
            assert execution_harness.is_initialized()
            assert execution_harness.swarm_manager is not None
            mock_swarm_manager.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute(self, execution_harness, sample_task, mock_swarm_manager):
        """测试执行"""
        with patch('src.harness.execution.SwarmManager', return_value=mock_swarm_manager):
            await execution_harness.initialize()
            result = await execution_harness.execute(sample_task)

            assert result.task_id == sample_task.task_id
            assert result.status == TaskStatus.COMPLETED.value
            assert result.output is not None
            assert result.quality_score == 0.85
            mock_swarm_manager.submit_task.assert_called_once()
            # get_task_status 是自定义函数，检查调用次数通过检查输出
            assert result.status == TaskStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_execute_updates_task_status(self, execution_harness, sample_task, mock_swarm_manager):
        """测试执行更新任务状态"""
        with patch('src.harness.execution.SwarmManager', return_value=mock_swarm_manager):
            await execution_harness.initialize()

            assert sample_task.status == TaskStatus.PENDING

            await execution_harness.execute(sample_task)

            assert sample_task.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_with_swarm_error(self, execution_harness, sample_task, mock_swarm_manager):
        """测试 Swarm 返回错误时的处理"""
        mock_swarm_manager.get_task_status = AsyncMock(return_value={
            "error": "Task execution failed",
            "subtasks_count": 1,
            "completed_subtasks": 0,
            "failed_subtasks": 0,
            "pending_subtasks": 1
        })

        with patch('src.harness.execution.SwarmManager', return_value=mock_swarm_manager):
            await execution_harness.initialize()
            result = await execution_harness.execute(sample_task)

            assert result.status == TaskStatus.FAILED.value
            assert result.errors == ["Task execution failed"]
            assert result.quality_score == 0.0

    @pytest.mark.asyncio
    async def test_execute_with_exception(self, execution_harness, sample_task, mock_swarm_manager):
        """测试执行抛出异常时的处理"""
        mock_swarm_manager.submit_task = AsyncMock(side_effect=Exception("Connection error"))

        with patch('src.harness.execution.SwarmManager', return_value=mock_swarm_manager):
            await execution_harness.initialize()
            result = await execution_harness.execute(sample_task)

            assert result.status == TaskStatus.FAILED.value
            assert "Connection error" in result.errors[0]
            assert result.quality_score == 0.0

    @pytest.mark.asyncio
    async def test_cleanup(self, execution_harness, mock_swarm_manager):
        """测试清理"""
        with patch('src.harness.execution.SwarmManager', return_value=mock_swarm_manager):
            await execution_harness.initialize()
            assert execution_harness.is_initialized()

            await execution_harness.cleanup()
            assert not execution_harness.is_initialized()
            assert execution_harness.swarm_manager is None
            mock_swarm_manager.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_full_cycle(self, execution_harness, sample_task, mock_swarm_manager):
        """测试完整的运行周期"""
        with patch('src.harness.execution.SwarmManager', return_value=mock_swarm_manager):
            result = await execution_harness.run(sample_task)

            assert result.task_id == sample_task.task_id
            assert result.status == TaskStatus.COMPLETED.value
            assert result.output is not None
            assert result.execution_time > 0

    @pytest.mark.asyncio
    async def test_run_already_initialized(self, execution_harness, sample_task, mock_swarm_manager):
        """测试已初始化时的运行"""
        with patch('src.harness.execution.SwarmManager', return_value=mock_swarm_manager):
            await execution_harness.initialize()
            assert execution_harness.is_initialized()

            # 第二次运行不应重新初始化
            result = await execution_harness.run(sample_task)
            assert result.status == TaskStatus.COMPLETED.value

    def test_registration(self):
        """测试 ExecutionHarness 已注册"""
        # 导入 ExecutionHarness 触发注册
        from src.harness.execution import ExecutionHarness
        assert HarnessFactory.is_registered(HarnessType.EXECUTION)

    @pytest.mark.asyncio
    async def test_create_via_factory(self, mock_swarm_manager):
        """测试通过工厂创建"""
        # 导入 ExecutionHarness 触发注册
        from src.harness.execution import ExecutionHarness
        with patch('src.harness.execution.SwarmManager', return_value=mock_swarm_manager):
            harness = HarnessFactory.create(HarnessType.EXECUTION)
            assert isinstance(harness, ExecutionHarness)
            assert harness.harness_type == HarnessType.EXECUTION

    @pytest.mark.asyncio
    async def test_result_metadata(self, execution_harness, sample_task, mock_swarm_manager):
        """测试结果元数据"""
        with patch('src.harness.execution.SwarmManager', return_value=mock_swarm_manager):
            await execution_harness.initialize()
            result = await execution_harness.execute(sample_task)

            assert result.metadata is not None
            assert result.metadata["harness_type"] == HarnessType.EXECUTION.value
            assert "task_type" in result.metadata
            assert "swarm_task_id" in result.metadata

    @pytest.mark.asyncio
    async def test_max_agents_config(self):
        """测试 max_agents 配置"""
        config = HarnessConfig(
            harness_type=HarnessType.EXECUTION,
            enabled=True,
            timeout=300,
            custom_params={"max_agents": 5}
        )
        harness = ExecutionHarness(config)
        assert harness.max_agents == 5

    @pytest.mark.asyncio
    async def test_default_max_agents(self, harness_config):
        """测试默认 max_agents 值"""
        harness = ExecutionHarness(harness_config)
        assert harness.max_agents == 10
