"""
Execution Harness - 使用 Agent Swarm 执行通用任务
集成监控系统，实时显示 Agent 工作状态
"""
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

from src.core.types import Task, TaskResult, HarnessConfig, HarnessType, SwarmConfig, TaskStatus
from src.core.exceptions import SwarmExecutionError
from src.harness.base import BaseHarness
from src.harness.factory import HarnessFactory
from src.swarm_manager import SwarmManager
from src.monitoring.agent_monitor import AgentMonitor, AgentStatus
from src.monitoring.task_monitor import TaskMonitor, TaskStage
from src.monitoring.dashboard import MonitorDashboard


class ExecutionHarness(BaseHarness):
    """执行 Harness - 使用 Agent Swarm 执行通用任务，带监控"""

    def __init__(self, config: HarnessConfig):
        super().__init__(config)
        self.swarm_manager: Optional[SwarmManager] = None
        self.max_agents = config.custom_params.get("max_agents", 10)
        self.enable_monitoring = config.custom_params.get("enable_monitoring", True)
        self.show_dashboard = config.custom_params.get("show_dashboard", False)

        # 监控器
        self.agent_monitor: Optional[AgentMonitor] = None
        self.task_monitor: Optional[TaskMonitor] = None
        self.dashboard: Optional[MonitorDashboard] = None

    async def initialize(self):
        """初始化 Execution Harness，创建 SwarmManager 和监控器"""
        await super().initialize()

        # 创建监控器
        if self.enable_monitoring:
            self.agent_monitor = AgentMonitor()
            self.task_monitor = TaskMonitor()
            self.dashboard = MonitorDashboard(self.agent_monitor, self.task_monitor)

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

        # 注册 Swarm 中的 Agents 到监控器
        if self.enable_monitoring and self.swarm_manager:
            await self._register_swarm_agents()

        self._initialized = True

    async def _register_swarm_agents(self):
        """注册 Swarm 中的 Agents 到监控器"""
        if not self.agent_monitor or not self.swarm_manager:
            return

        # 注册 Coordinator
        if self.swarm_manager.coordinator:
            self.agent_monitor.register_agent(
                self.swarm_manager.coordinator.config.agent_id,
                self.swarm_manager.coordinator.config.name,
                "coordinator"
            )

        # 注册 Executors
        for agent_id, executor in self.swarm_manager.executors.items():
            self.agent_monitor.register_agent(
                agent_id,
                executor.config.name,
                "executor"
            )

        # 注册 Validators
        for agent_id, validator in self.swarm_manager.validators.items():
            self.agent_monitor.register_agent(
                agent_id,
                validator.config.name,
                "validator"
            )

        # 注册 Integrators
        for agent_id, integrator in self.swarm_manager.integrators.items():
            self.agent_monitor.register_agent(
                agent_id,
                integrator.config.name,
                "integrator"
            )

    async def execute(self, task: Task, progress_callback=None) -> TaskResult:
        """使用 Swarm 执行任务，集成监控"""
        start_time = datetime.now()

        try:
            # 更新任务状态
            task.status = TaskStatus.IN_PROGRESS

            # 在监控器中注册任务
            if self.task_monitor:
                self.task_monitor.register_task(
                    task.task_id,
                    task.description,
                    task.task_type.value if task.task_type else "general"
                )
                self.task_monitor.update_stage(task.task_id, TaskStage.EXECUTING)

            # 提交任务到 Swarm
            task_id = await self.swarm_manager.submit_task(
                description=task.description,
                task_type=task.task_type.value if task.task_type else "general",
                requirements=task.requirements,
                metadata=task.metadata
            )

            print(f"\n🚀 任务已提交到 Swarm: {task_id}")
            print(f"   描述: {task.description}")
            print(f"   类型: {task.task_type.value if task.task_type else 'general'}")

            # 启动监控仪表板（如果启用）
            if self.show_dashboard and self.dashboard:
                print("\n📊 启动监控仪表板...")
                dashboard_task = asyncio.create_task(self.dashboard.run(task_id))

            # 等待任务完成，同时显示进度
            swarm_result = await self._wait_with_progress(task_id, timeout=300.0, progress_callback=progress_callback)

            # 停止仪表板
            if self.show_dashboard and self.dashboard:
                self.dashboard._running = False
                await asyncio.sleep(0.5)

            execution_time = (datetime.now() - start_time).total_seconds()

            # 更新监控器状态
            if self.task_monitor:
                if "error" in swarm_result:
                    self.task_monitor.update_stage(task.task_id, TaskStage.FAILED)
                else:
                    self.task_monitor.update_stage(task.task_id, TaskStage.COMPLETED)

            # 检查是否出错
            if "error" in swarm_result:
                task.status = TaskStatus.FAILED
                print(f"\n❌ 任务执行失败: {swarm_result.get('error')}")
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

            print(f"\n✅ 任务执行成功！")
            print(f"   完成子任务: {swarm_result.get('completed_subtasks', 0)}/{swarm_result.get('subtasks_count', 0)}")
            print(f"   执行时间: {execution_time:.1f}秒")

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
            if self.task_monitor and task.task_id:
                self.task_monitor.update_stage(task.task_id, TaskStage.FAILED)
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

    async def _wait_with_progress(self, task_id: str, timeout: float = 300.0, progress_callback=None) -> Dict[str, Any]:
        """等待任务完成并显示进度"""
        import asyncio
        from datetime import datetime

        if not self.swarm_manager:
            return {"error": "SwarmManager not initialized"}

        start_time = datetime.now()
        last_status = None
        dots = 0

        while True:
            # 获取当前状态
            status = await self.swarm_manager.get_task_status(task_id)

            if status:
                current_status = {
                    "pending": status.get("pending_subtasks", 0),
                    "completed": status.get("completed_subtasks", 0),
                    "failed": status.get("failed_subtasks", 0),
                    "total": status.get("subtasks_count", 0)
                }

                # 状态变化时打印
                if last_status != current_status:
                    total = current_status["total"]
                    completed = current_status["completed"]
                    failed = current_status["failed"]
                    pending = current_status["pending"]

                    if total > 0:
                        progress = (completed + failed) / total * 100
                        print(f"\r   进度: [{completed}/{total}] {progress:.0f}% "
                              f"(✓{completed} ✗{failed} ⏳{pending})", end="", flush=True)

                    last_status = current_status

                # 检查是否完成
                if current_status["completed"] + current_status["failed"] >= current_status["total"] and current_status["total"] > 0:
                    print()  # 换行
                    return status

            # 检查超时
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > timeout:
                print(f"\n   ⚠️  任务超时 (> {timeout}秒)")
                return {"error": "Timeout", "status": status}

            # 显示等待动画
            dots = (dots + 1) % 4
            await asyncio.sleep(1.0)

    async def cleanup(self):
        """清理 Swarm 资源"""
        if self.swarm_manager:
            await self.swarm_manager.stop()
            self.swarm_manager = None
        self._initialized = False


# 注册到工厂
HarnessFactory.register(HarnessType.EXECUTION, ExecutionHarness)
