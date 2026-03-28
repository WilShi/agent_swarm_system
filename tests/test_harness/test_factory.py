"""
HarnessFactory 测试
"""
import pytest
from src.harness.factory import HarnessFactory
from src.harness.base import BaseHarness
from src.core.types import HarnessType, HarnessConfig, Task, TaskResult


class DummyHarness(BaseHarness):
    """测试用的 Dummy Harness"""

    async def initialize(self):
        pass

    async def execute(self, task: Task) -> TaskResult:
        return TaskResult(
            task_id=task.task_id,
            status="completed",
            output={"harness": "dummy"}
        )

    async def cleanup(self):
        pass


class TestHarnessFactory:
    """HarnessFactory 测试类"""

    def setup_method(self):
        """每个测试前清理注册表"""
        HarnessFactory.clear_registry()

    def teardown_method(self):
        """每个测试后清理注册表"""
        HarnessFactory.clear_registry()

    def test_register(self):
        """测试注册 Harness"""
        HarnessFactory.register(HarnessType.TEST, DummyHarness)

        assert HarnessType.TEST in HarnessFactory.get_registered_types()
        assert HarnessFactory.is_registered(HarnessType.TEST)

    def test_register_invalid_class(self):
        """测试注册无效的类"""
        class NotAHarness:
            pass

        with pytest.raises(TypeError):
            HarnessFactory.register(HarnessType.TEST, NotAHarness)

    def test_create(self):
        """测试创建 Harness"""
        HarnessFactory.register(HarnessType.TEST, DummyHarness)

        harness = HarnessFactory.create(HarnessType.TEST)

        assert isinstance(harness, DummyHarness)
        assert harness.harness_type == HarnessType.TEST

    def test_create_with_config(self):
        """测试创建 Harness 带配置"""
        HarnessFactory.register(HarnessType.TEST, DummyHarness)

        config = {"timeout": 60, "max_retries": 5}
        harness = HarnessFactory.create(HarnessType.TEST, config=config)

        assert isinstance(harness, DummyHarness)
        assert harness.config.timeout == 60
        assert harness.config.max_retries == 5

    def test_create_unknown_harness(self):
        """测试创建未知的 Harness"""
        from src.core.exceptions import HarnessInitError

        with pytest.raises(HarnessInitError) as exc_info:
            HarnessFactory.create(HarnessType.CODE)

        assert "Unknown harness type" in str(exc_info.value)

    def test_unregister(self):
        """测试注销 Harness"""
        HarnessFactory.register(HarnessType.TEST, DummyHarness)
        assert HarnessFactory.is_registered(HarnessType.TEST)

        HarnessFactory.unregister(HarnessType.TEST)
        assert not HarnessFactory.is_registered(HarnessType.TEST)

    def test_get_registered_types(self):
        """测试获取已注册类型"""
        HarnessFactory.register(HarnessType.TEST, DummyHarness)
        HarnessFactory.register(HarnessType.EXECUTION, DummyHarness)

        types = HarnessFactory.get_registered_types()

        assert HarnessType.TEST in types
        assert HarnessType.EXECUTION in types

    def test_clear_registry(self):
        """测试清空注册表"""
        HarnessFactory.register(HarnessType.TEST, DummyHarness)
        assert len(HarnessFactory.get_registered_types()) > 0

        HarnessFactory.clear_registry()
        assert len(HarnessFactory.get_registered_types()) == 0

    def test_is_registered(self):
        """测试检查是否已注册"""
        assert not HarnessFactory.is_registered(HarnessType.TEST)

        HarnessFactory.register(HarnessType.TEST, DummyHarness)
        assert HarnessFactory.is_registered(HarnessType.TEST)
