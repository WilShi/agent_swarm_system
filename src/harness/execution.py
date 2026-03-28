"""
ExecutionHarness - 默认执行 Harness

用于执行一般性任务的 Harness 实现。
"""
import time
from datetime import datetime
from src.harness.base import BaseHarness
from src.harness.factory import HarnessFactory
from src.core.types import Task, TaskResult, HarnessType, TaskStatus


class ExecutionHarness(BaseHarness):
    """
    执行 Harness

    默认的任务执行 Harness，用于执行一般性任务。
    可以与 LLM 客户端集成来处理任务。
    """

    async def initialize(self):
        """
        初始化 ExecutionHarness

        设置必要的资源，如 LLM 客户端连接等。
        """
        # 可以在这里初始化 LLM 客户端或其他资源
        self._initialized = True

    async def execute(self, task: Task) -> TaskResult:
        """
        执行任务

        Args:
            task: 要执行的任务

        Returns:
            TaskResult: 任务执行结果
        """
        start_time = time.time()

        try:
            # 更新任务状态
            task.status = TaskStatus.IN_PROGRESS

            # 这里可以集成 LLM 客户端来处理任务
            # 简化实现：返回基本成功结果
            output = {
                "message": f"Task executed: {task.description}",
                "harness": self.harness_type.value,
                "task_type": task.task_type.value if task.task_type else "general"
            }

            execution_time = time.time() - start_time

            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()

            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.COMPLETED.value,
                output=output,
                quality_score=1.0,
                execution_time=execution_time,
                tokens_used=0,
                logs=[f"Task {task.task_id} completed successfully"],
                errors=[],
                metadata={
                    "harness_type": self.harness_type.value,
                    "task_type": task.task_type.value if task.task_type else None
                }
            )

        except Exception as e:
            task.status = TaskStatus.FAILED
            execution_time = time.time() - start_time

            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.FAILED.value,
                output=None,
                quality_score=0.0,
                execution_time=execution_time,
                tokens_used=0,
                logs=[f"Task {task.task_id} failed"],
                errors=[str(e)],
                metadata={"harness_type": self.harness_type.value}
            )

    async def cleanup(self):
        """
        清理 ExecutionHarness 资源

        释放 LLM 客户端连接等资源。
        """
        self._initialized = False


# 注册 ExecutionHarness
HarnessFactory.register(HarnessType.EXECUTION, ExecutionHarness)
