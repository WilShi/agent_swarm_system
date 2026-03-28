"""
Agent Swarm Manager
管理整个三层Agent Swarm系统的生命周期
"""
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

from .core.types import AgentConfig, AgentRole, Task, SwarmConfig, TaskStatus
from .core.message_bus import MessageBus
from .layers.coordinator_layer import CoordinatorAgent
from .layers.execution_layer import ExecutorAgent
from .layers.validation_layer import ValidatorAgent, IntegratorAgent


class SwarmManager:
    """
    Agent Swarm管理器
    负责协调三层架构的所有Agent
    """
    
    def __init__(self, config: SwarmConfig = None):
        self.config = config or SwarmConfig()
        self.message_bus = MessageBus(max_queue_size=self.config.message_queue_size)
        
        # Agent实例
        self.coordinator: Optional[CoordinatorAgent] = None
        self.executors: Dict[str, ExecutorAgent] = {}
        self.validators: Dict[str, ValidatorAgent] = {}
        self.integrators: Dict[str, IntegratorAgent] = {}
        
        # 状态
        self._running = False
        self._start_time: Optional[datetime] = None
        self._task_history: List[Dict[str, Any]] = []
    
    async def start(self):
        """启动Swarm系统"""
        print("=" * 60)
        print("Starting Agent Swarm System")
        print("=" * 60)
        
        # 启动消息总线
        await self.message_bus.start()
        print("✓ Message bus started")
        
        # 创建并启动协调器
        await self._create_coordinator()
        print("✓ Coordinator layer initialized")
        
        # 创建执行层Agent
        await self._create_executors()
        print(f"✓ Execution layer initialized ({len(self.executors)} agents)")
        
        # 创建验证层Agent
        await self._create_validators()
        print(f"✓ Validation layer initialized ({len(self.validators)} validators)")
        
        # 创建整合层Agent
        await self._create_integrators()
        print(f"✓ Integration layer initialized ({len(self.integrators)} integrators)")
        
        self._running = True
        self._start_time = datetime.now()
        
        print("=" * 60)
        print("Agent Swarm System Ready")
        print("=" * 60)
    
    async def stop(self):
        """停止Swarm系统"""
        print("\n" + "=" * 60)
        print("Stopping Agent Swarm System")
        print("=" * 60)
        
        self._running = False
        
        # 停止所有Agent
        for agent in list(self.integrators.values()):
            await agent.stop()
        print(f"✓ Stopped {len(self.integrators)} integrators")
        
        for agent in list(self.validators.values()):
            await agent.stop()
        print(f"✓ Stopped {len(self.validators)} validators")
        
        for agent in list(self.executors.values()):
            await agent.stop()
        print(f"✓ Stopped {len(self.executors)} executors")
        
        if self.coordinator:
            await self.coordinator.stop()
            print("✓ Stopped coordinator")
        
        # 停止消息总线
        await self.message_bus.stop()
        print("✓ Message bus stopped")
        
        print("=" * 60)
        print("Agent Swarm System Stopped")
        print("=" * 60)
    
    async def _create_coordinator(self):
        """创建协调器"""
        config = AgentConfig(
            name="MainCoordinator",
            role=AgentRole.COORDINATOR,
            capabilities=["coordination", "planning", "resource_management"],
            max_concurrent_tasks=10
        )
        
        self.coordinator = CoordinatorAgent(config, self.message_bus)
        await self.coordinator.start()
    
    async def _create_executors(self, count: int = 3):
        """创建执行层Agent"""
        capabilities_list = [
            ["data_access", "data_processing", "analysis"],
            ["generation", "optimization", "coding"],
            ["testing", "visualization", "general"]
        ]
        
        for i in range(count):
            config = AgentConfig(
                name=f"Executor-{i+1}",
                role=AgentRole.EXECUTOR,
                capabilities=capabilities_list[i % len(capabilities_list)],
                max_concurrent_tasks=3
            )
            
            executor = ExecutorAgent(config, self.message_bus)
            await executor.start()
            
            self.executors[config.agent_id] = executor
            
            # 注册到协调器
            if self.coordinator:
                self.coordinator.register_execution_agent(
                    config.agent_id, config.capabilities
                )
    
    async def _create_validators(self, count: int = 2):
        """创建验证层Agent"""
        for i in range(count):
            config = AgentConfig(
                name=f"Validator-{i+1}",
                role=AgentRole.VALIDATOR,
                capabilities=["validation", "quality_check", "verification"],
                max_concurrent_tasks=5
            )
            
            validator = ValidatorAgent(config, self.message_bus)
            await validator.start()
            
            self.validators[config.agent_id] = validator
            
            # 注册到协调器
            if self.coordinator:
                self.coordinator.register_validator_agent(
                    config.agent_id, config.capabilities
                )
    
    async def _create_integrators(self, count: int = 1):
        """创建整合层Agent"""
        for i in range(count):
            config = AgentConfig(
                name=f"Integrator-{i+1}",
                role=AgentRole.INTEGRATOR,
                capabilities=["integration", "synthesis", "aggregation"],
                max_concurrent_tasks=3
            )
            
            integrator = IntegratorAgent(config, self.message_bus)
            await integrator.start()
            
            self.integrators[config.agent_id] = integrator
            
            # 注册到协调器
            if self.coordinator:
                self.coordinator.register_integrator_agent(
                    config.agent_id, config.capabilities
                )
    
    async def submit_task(self, description: str, task_type: str = "default",
                         requirements: Dict[str, Any] = None,
                         metadata: Dict[str, Any] = None) -> str:
        """
        提交任务到Swarm
        
        Args:
            description: 任务描述
            task_type: 任务类型 (analysis, generation, research, code, default)
            requirements: 任务要求
            metadata: 任务元数据
        
        Returns:
            任务ID
        """
        if not self._running or not self.coordinator:
            raise RuntimeError("Swarm system is not running")
        
        task = Task(
            description=description,
            requirements=requirements or {},
            metadata={**(metadata or {}), "task_type": task_type}
        )
        
        task_id = await self.coordinator.submit_task(task)
        
        # 记录任务
        self._task_history.append({
            "task_id": task_id,
            "description": description,
            "task_type": task_type,
            "submitted_at": datetime.now().isoformat(),
            "status": TaskStatus.PENDING.value
        })
        
        print(f"\n📋 Task submitted: {task_id}")
        print(f"   Description: {description}")
        print(f"   Type: {task_type}")
        
        return task_id
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        if not self.coordinator:
            return None
        return self.coordinator.get_task_status(task_id)
    
    async def wait_for_task(self, task_id: str, timeout: float = 60.0) -> Dict[str, Any]:
        """等待任务完成"""
        start_time = datetime.now()
        
        while True:
            status = await self.get_task_status(task_id)
            
            if not status:
                return {"error": "Task not found"}
            
            # 检查是否完成
            if status.get("completed_subtasks", 0) + status.get("failed_subtasks", 0) >= status.get("subtasks_count", 0):
                if status.get("subtasks_count", 0) > 0:
                    return status
            
            # 检查超时
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > timeout:
                return {"error": "Timeout", "status": status}
            
            await asyncio.sleep(0.5)
    
    def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        stats = {
            "running": self._running,
            "agents": {
                "coordinators": 1 if self.coordinator else 0,
                "executors": len(self.executors),
                "validators": len(self.validators),
                "integrators": len(self.integrators),
                "total": (1 if self.coordinator else 0) + 
                        len(self.executors) + 
                        len(self.validators) + 
                        len(self.integrators)
            },
            "tasks": {
                "total_submitted": len(self._task_history),
                "history": self._task_history[-10:]  # 最近10个
            }
        }
        
        if self._start_time:
            stats["uptime_seconds"] = (datetime.now() - self._start_time).total_seconds()
        
        # 获取各层统计
        if self.coordinator:
            stats["coordinator"] = self.coordinator.get_metrics()
            stats["coordinator"]["allocator"] = self.coordinator.allocator.get_allocation_stats()
        
        return stats
    
    async def add_executor(self, capabilities: List[str] = None) -> str:
        """动态添加执行器"""
        config = AgentConfig(
            name=f"Executor-{len(self.executors)+1}",
            role=AgentRole.EXECUTOR,
            capabilities=capabilities or ["general"],
            max_concurrent_tasks=3
        )
        
        executor = ExecutorAgent(config, self.message_bus)
        await executor.start()
        
        self.executors[config.agent_id] = executor
        
        if self.coordinator:
            self.coordinator.register_execution_agent(
                config.agent_id, config.capabilities
            )
        
        return config.agent_id
    
    async def remove_executor(self, agent_id: str) -> bool:
        """移除执行器"""
        if agent_id not in self.executors:
            return False
        
        executor = self.executors.pop(agent_id)
        await executor.stop()
        
        if self.coordinator:
            self.coordinator.allocator.unregister_agent(agent_id)
        
        return True


# 便捷函数
async def create_swarm(name: str = "AgentSwarm", max_agents: int = 10) -> SwarmManager:
    """创建并启动Swarm"""
    config = SwarmConfig(name=name, max_agents=max_agents)
    manager = SwarmManager(config)
    await manager.start()
    return manager


async def run_task(swarm: SwarmManager, description: str, 
                   task_type: str = "default",
                   wait: bool = True,
                   timeout: float = 60.0) -> Dict[str, Any]:
    """
    在Swarm中运行任务
    
    Args:
        swarm: Swarm管理器实例
        description: 任务描述
        task_type: 任务类型
        wait: 是否等待完成
        timeout: 等待超时时间
    
    Returns:
        任务状态或结果
    """
    task_id = await swarm.submit_task(description, task_type)
    
    if wait:
        return await swarm.wait_for_task(task_id, timeout)
    else:
        return {"task_id": task_id, "status": "submitted"}
