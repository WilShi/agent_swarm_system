"""
Execution Harness - 使用 Agent Swarm 执行通用任务
"""
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

from src.core.types import Task, TaskResult, HarnessConfig, HarnessType, SwarmConfig, TaskStatus
from src.core.exceptions import SwarmExecutionError
from src.harness.base import BaseHarness
from src.harness.factory import HarnessFactory
from src.swarm_manager import SwarmManager


class ExecutionHarness(BaseHarness):
    """执行 Harness - 使用 Agent Swarm 执行通用任务"""

    def __init__(self, config: HarnessConfig):
        super().__init__(config)
        self.swarm_manager: Optional[SwarmManager] = None
        self.max_agents = config.custom_params.get("max_agents", 10)

    async def initialize(self):
        """初始化 Execution Harness，创建 SwarmManager"""
        await super().initialize()

        # 创建 Swarm 配置
        swarm_config = SwarmConfig(
            name=f"{self.harness_type.value}_swarm",
            max_agents=self.max_agents,
            enable_load_balancing=True,
            enable_fault_tolerance=True,
            message_queue_size=1000
        )

        # 创建并启动 SwarmManager
        self.swarm_manager = SwarmManager(swarm_config)
        await self.swarm_manager.start()
        self._initialized = True

    async def execute(self, task: Task) -> TaskResult:
        """使用 Swarm 执行任务"""
        start_time = datetime.now()

        try:
            # 更新任务状态
            task.status = TaskStatus.IN_PROGRESS

            # 提交任务到 Swarm
            task_id = await self.swarm_manager.submit_task(
                description=task.description,
                task_type=task.task_type.value if task.task_type else "general",
                requirements=task.requirements,
                metadata=task.metadata
            )

            # 等待任务完成（增加超时时间）
            swarm_result = await self.swarm_manager.wait_for_task(task_id, timeout=180.0)

            execution_time = (datetime.now() - start_time).total_seconds()

            # 检查是否出错
            if "error" in swarm_result:
                task.status = TaskStatus.FAILED
                return TaskResult(
                    task_id=task.task_id,
                    status=TaskStatus.FAILED.value,
                    output=None,
                    quality_score=0.0,
                    execution_time=execution_time,
                    logs=[f"Swarm task {task_id} failed"],
                    errors=[swarm_result.get("error", "Unknown error")],
                    metadata={"swarm_task_id": task_id}
                )

            # 任务成功完成
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()

            # 构建 TaskResult
            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.COMPLETED.value,
                output=swarm_result.get("result", swarm_result),
                quality_score=swarm_result.get("quality_score", 0.8),
                execution_time=execution_time,
                logs=[f"Swarm task {task_id} completed"],
                metadata={
                    "swarm_task_id": task_id,
                    "harness_type": self.harness_type.value,
                    "task_type": task.task_type.value if task.task_type else None
                }
            )

        except Exception as e:
            task.status = TaskStatus.FAILED
            execution_time = (datetime.now() - start_time).total_seconds()
            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.FAILED.value,
                output=None,
                quality_score=0.0,
                execution_time=execution_time,
                logs=[f"Task {task.task_id} failed"],
                errors=[str(e)],
                metadata={"harness_type": self.harness_type.value}
            )

    async def cleanup(self):
        """清理 Swarm 资源"""
        if self.swarm_manager:
            await self.swarm_manager.stop()
            self.swarm_manager = None
        self._initialized = False


# 注册到工厂
HarnessFactory.register(HarnessType.EXECUTION, ExecutionHarness)
