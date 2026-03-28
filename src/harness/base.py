"""
BaseHarness 抽象基类

定义所有 Harness 实现必须遵循的接口。
"""
from abc import ABC, abstractmethod
from src.core.types import Task, TaskResult, HarnessConfig


class BaseHarness(ABC):
    """
    Harness 抽象基类

    所有具体的 Harness 实现必须继承此类并实现以下抽象方法：
    - initialize: 初始化 Harness
    - execute: 执行任务
    - cleanup: 清理资源
    """

    def __init__(self, config: HarnessConfig):
        """
        初始化 Harness

        Args:
            config: Harness 配置对象
        """
        self.config = config
        self.harness_type = config.harness_type
        self._initialized = False

    @abstractmethod
    async def initialize(self):
        """
        初始化 Harness 资源

        在 Harness 可以执行任务之前调用，用于设置必要的资源。
        """
        pass

    @abstractmethod
    async def execute(self, task: Task) -> TaskResult:
        """
        执行任务

        Args:
            task: 要执行的任务对象

        Returns:
            TaskResult: 任务执行结果
        """
        pass

    @abstractmethod
    async def cleanup(self):
        """
        清理 Harness 资源

        在 Harness 不再需要时调用，用于释放资源。
        """
        pass

    async def run(self, task: Task) -> TaskResult:
        """
        完整的任务执行流程

        自动处理初始化、执行和清理。

        Args:
            task: 要执行的任务对象

        Returns:
            TaskResult: 任务执行结果
        """
        if not self._initialized:
            await self.initialize()
            self._initialized = True

        try:
            result = await self.execute(task)
            return result
        except Exception as e:
            from src.core.types import TaskStatus
            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.FAILED.value,
                errors=[str(e)],
                metadata={"harness_type": self.harness_type.value}
            )

    def is_initialized(self) -> bool:
        """
        检查 Harness 是否已初始化

        Returns:
            bool: True 如果已初始化
        """
        return self._initialized

    def get_config(self) -> HarnessConfig:
        """
        获取 Harness 配置

        Returns:
            HarnessConfig: 配置对象
        """
        return self.config
