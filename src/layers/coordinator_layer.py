"""
第一层：协调/规划层 (Coordinator Layer)
负责任务分解、资源分配、策略制定
"""
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..core.base_agent import BaseAgent
from ..core.types import (
    AgentConfig, AgentRole, Message, MessageType,
    Task, SubTask, TaskStatus
)
from ..core.message_bus import MessageBus


class TaskDecomposer:
    """任务分解器"""
    
    def __init__(self):
        self._decomposition_strategies: Dict[str, callable] = {
            "analysis": self._decompose_analysis_task,
            "generation": self._decompose_generation_task,
            "research": self._decompose_research_task,
            "code": self._decompose_code_task,
            "default": self._decompose_default_task
        }
    
    def decompose(self, task: Task) -> List[SubTask]:
        """分解任务为子任务"""
        task_type = task.metadata.get("task_type", "default")
        strategy = self._decomposition_strategies.get(task_type, self._decomposition_strategies["default"])
        return strategy(task)
    
    def _decompose_analysis_task(self, task: Task) -> List[SubTask]:
        """分解分析类任务"""
        subtasks = []
        
        # 1. 数据收集
        subtasks.append(SubTask(
            parent_task_id=task.task_id,
            description=f"收集分析所需数据: {task.description}",
            task_type="data_collection",
            parameters={"source": task.requirements.get("data_source")}
        ))
        
        # 2. 数据预处理
        subtasks.append(SubTask(
            parent_task_id=task.task_id,
            description=f"预处理数据: {task.description}",
            task_type="data_preprocessing",
            dependencies=[subtasks[0].task_id]
        ))
        
        # 3. 分析执行
        subtasks.append(SubTask(
            parent_task_id=task.task_id,
            description=f"执行分析: {task.description}",
            task_type="analysis_execution",
            dependencies=[subtasks[1].task_id]
        ))
        
        # 4. 结果可视化
        subtasks.append(SubTask(
            parent_task_id=task.task_id,
            description=f"生成可视化报告: {task.description}",
            task_type="visualization",
            dependencies=[subtasks[2].task_id]
        ))
        
        return subtasks
    
    def _decompose_generation_task(self, task: Task) -> List[SubTask]:
        """分解生成类任务"""
        subtasks = []
        
        # 1. 需求分析
        subtasks.append(SubTask(
            parent_task_id=task.task_id,
            description=f"分析生成需求: {task.description}",
            task_type="requirement_analysis"
        ))
        
        # 2. 内容生成
        subtasks.append(SubTask(
            parent_task_id=task.task_id,
            description=f"生成内容: {task.description}",
            task_type="content_generation",
            dependencies=[subtasks[0].task_id]
        ))
        
        # 3. 内容优化
        subtasks.append(SubTask(
            parent_task_id=task.task_id,
            description=f"优化生成内容: {task.description}",
            task_type="content_optimization",
            dependencies=[subtasks[1].task_id]
        ))
        
        return subtasks
    
    def _decompose_research_task(self, task: Task) -> List[SubTask]:
        """分解研究类任务"""
        subtasks = []
        
        # 1. 文献检索
        subtasks.append(SubTask(
            parent_task_id=task.task_id,
            description=f"检索相关文献: {task.description}",
            task_type="literature_search"
        ))
        
        # 2. 信息提取
        subtasks.append(SubTask(
            parent_task_id=task.task_id,
            description=f"提取关键信息: {task.description}",
            task_type="information_extraction",
            dependencies=[subtasks[0].task_id]
        ))
        
        # 3. 知识综合
        subtasks.append(SubTask(
            parent_task_id=task.task_id,
            description=f"综合研究发现: {task.description}",
            task_type="knowledge_synthesis",
            dependencies=[subtasks[1].task_id]
        ))
        
        return subtasks
    
    def _decompose_code_task(self, task: Task) -> List[SubTask]:
        """分解代码类任务"""
        subtasks = []
        
        # 1. 需求理解
        subtasks.append(SubTask(
            parent_task_id=task.task_id,
            description=f"理解代码需求: {task.description}",
            task_type="requirement_understanding"
        ))
        
        # 2. 设计
        subtasks.append(SubTask(
            parent_task_id=task.task_id,
            description=f"设计代码结构: {task.description}",
            task_type="code_design",
            dependencies=[subtasks[0].task_id]
        ))
        
        # 3. 实现
        subtasks.append(SubTask(
            parent_task_id=task.task_id,
            description=f"编写代码: {task.description}",
            task_type="code_implementation",
            dependencies=[subtasks[1].task_id]
        ))
        
        # 4. 测试
        subtasks.append(SubTask(
            parent_task_id=task.task_id,
            description=f"编写测试: {task.description}",
            task_type="test_writing",
            dependencies=[subtasks[2].task_id]
        ))
        
        return subtasks
    
    def _decompose_default_task(self, task: Task) -> List[SubTask]:
        """默认任务分解"""
        return [SubTask(
            parent_task_id=task.task_id,
            description=task.description,
            task_type="generic_execution"
        )]


class ResourceAllocator:
    """资源分配器"""
    
    def __init__(self):
        self._agent_capabilities: Dict[str, List[str]] = {}
        self._agent_loads: Dict[str, int] = {}
        self._agent_status: Dict[str, str] = {}
    
    def register_agent(self, agent_id: str, capabilities: List[str]):
        """注册Agent"""
        self._agent_capabilities[agent_id] = capabilities
        self._agent_loads[agent_id] = 0
        self._agent_status[agent_id] = "available"
    
    def unregister_agent(self, agent_id: str):
        """注销Agent"""
        if agent_id in self._agent_capabilities:
            del self._agent_capabilities[agent_id]
            del self._agent_loads[agent_id]
            del self._agent_status[agent_id]
    
    def allocate_task(self, subtask: SubTask, 
                     available_agents: List[str]) -> Optional[str]:
        """为子任务分配Agent"""
        if not available_agents:
            return None
        
        # 获取任务所需能力
        required_capabilities = self._get_required_capabilities(subtask.task_type)
        
        # 筛选有能力的Agent
        capable_agents = [
            agent_id for agent_id in available_agents
            if agent_id in self._agent_capabilities
            and all(cap in self._agent_capabilities[agent_id] 
                   for cap in required_capabilities)
            and self._agent_status.get(agent_id) == "available"
        ]
        
        if not capable_agents:
            return None
        
        # 选择负载最低的Agent
        best_agent = min(capable_agents, key=lambda a: self._agent_loads.get(a, 0))
        self._agent_loads[best_agent] += 1
        
        return best_agent
    
    def release_task(self, agent_id: str):
        """释放任务占用"""
        if agent_id in self._agent_loads:
            self._agent_loads[agent_id] = max(0, self._agent_loads[agent_id] - 1)
    
    def update_agent_status(self, agent_id: str, status: str):
        """更新Agent状态"""
        if agent_id in self._agent_status:
            self._agent_status[agent_id] = status
    
    def _get_required_capabilities(self, task_type: str) -> List[str]:
        """获取任务类型所需能力"""
        capability_map = {
            "data_collection": ["data_access"],
            "data_preprocessing": ["data_processing"],
            "analysis_execution": ["analysis"],
            "visualization": ["visualization"],
            "content_generation": ["generation"],
            "content_optimization": ["optimization"],
            "code_implementation": ["coding"],
            "test_writing": ["testing"],
            "validation": ["validation"],
            "integration": ["integration"]
        }
        return capability_map.get(task_type, ["general"])
    
    def get_allocation_stats(self) -> Dict[str, Any]:
        """获取分配统计"""
        return {
            "agent_count": len(self._agent_capabilities),
            "total_load": sum(self._agent_loads.values()),
            "agent_loads": self._agent_loads.copy(),
            "agent_status": self._agent_status.copy()
        }


class CoordinatorAgent(BaseAgent):
    """协调器Agent - 第一层核心"""
    
    def __init__(self, config: AgentConfig, message_bus: MessageBus):
        super().__init__(config, message_bus)
        self.decomposer = TaskDecomposer()
        self.allocator = ResourceAllocator()
        self._active_tasks: Dict[str, Task] = {}
        self._subtask_status: Dict[str, TaskStatus] = {}
        self._execution_agents: List[str] = []
        self._validator_agents: List[str] = []
        self._integrator_agents: List[str] = []
    
    async def on_start(self):
        """启动协调器"""
        print(f"CoordinatorAgent {self.config.agent_id} started")
        
        # 注册消息处理器
        self.register_message_handler(MessageType.COORDINATION, self._handle_coordination)
        self.register_message_handler(MessageType.TASK_RESULT, self._handle_task_result)
    
    async def on_stop(self):
        """停止协调器"""
        print(f"CoordinatorAgent {self.config.agent_id} stopped")
    
    async def process_task(self, task: SubTask) -> Any:
        """协调器处理任务（实际为任务分解和分配）"""
        # 获取完整任务信息
        full_task = self._active_tasks.get(task.parent_task_id)
        if not full_task:
            raise ValueError(f"Task {task.parent_task_id} not found")
        
        # 分解任务
        subtasks = self.decomposer.decompose(full_task)
        full_task.subtasks = subtasks
        
        # 分配子任务
        await self._distribute_subtasks(full_task)
        
        return {"decomposed_into": len(subtasks), "subtasks": [s.task_id for s in subtasks]}
    
    async def submit_task(self, task: Task) -> str:
        """提交新任务"""
        self._active_tasks[task.task_id] = task
        task.status = TaskStatus.IN_PROGRESS
        
        # 创建协调子任务
        coord_subtask = SubTask(
            parent_task_id=task.task_id,
            description=f"协调任务: {task.description}",
            task_type="coordination"
        )
        
        await self.assign_task(coord_subtask)
        
        return task.task_id
    
    async def _distribute_subtasks(self, task: Task):
        """分发子任务"""
        for subtask in task.subtasks:
            # 根据任务类型选择Agent池
            if subtask.task_type in ["validation", "verification"]:
                agent_pool = self._validator_agents
            elif subtask.task_type in ["integration", "synthesis"]:
                agent_pool = self._integrator_agents
            else:
                agent_pool = self._execution_agents
            
            # 分配Agent
            assigned_agent = self.allocator.allocate_task(subtask, agent_pool)
            
            if assigned_agent:
                subtask.assigned_to = assigned_agent
                subtask.status = TaskStatus.ASSIGNED
                
                # 发送任务分配消息
                await self.send_to_agent(
                    assigned_agent,
                    {
                        "action": "assign_task",
                        "subtask": subtask.__dict__
                    },
                    MessageType.TASK_ASSIGN
                )
            else:
                # 没有可用Agent，稍后重试
                subtask.status = TaskStatus.PENDING
                asyncio.create_task(self._retry_assign(subtask, task.task_id))
    
    async def _retry_assign(self, subtask: SubTask, task_id: str, delay: float = 2.0):
        """重试分配任务"""
        await asyncio.sleep(delay)
        if task_id in self._active_tasks:
            task = self._active_tasks[task_id]
            await self._distribute_subtasks(task)
    
    async def _handle_coordination(self, message: Message):
        """处理协调消息"""
        content = message.content
        action = content.get("action")
        
        if action == "register_agent":
            agent_id = content.get("agent_id")
            agent_role = content.get("agent_role")
            capabilities = content.get("capabilities", [])
            
            self.allocator.register_agent(agent_id, capabilities)
            
            if agent_role == "executor":
                self._execution_agents.append(agent_id)
            elif agent_role == "validator":
                self._validator_agents.append(agent_id)
            elif agent_role == "integrator":
                self._integrator_agents.append(agent_id)

            print(f"Registered {agent_role} agent: {agent_id}")

            # 向 Agent 发送确认，告知 Coordinator ID
            await self.send_to_agent(
                agent_id,
                {
                    "action": "coordinator_assigned",
                    "coordinator_id": self.config.agent_id
                },
                MessageType.COORDINATION
            )
    
    async def _handle_task_result(self, message: Message):
        """处理任务结果"""
        content = message.content
        task_id = content.get("task_id")
        parent_task_id = content.get("parent_task_id")
        success = content.get("success", False)
        
        if parent_task_id and parent_task_id in self._active_tasks:
            task = self._active_tasks[parent_task_id]
            
            # 更新子任务状态
            for subtask in task.subtasks:
                if subtask.task_id == task_id:
                    subtask.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
                    subtask.result = content.get("result")
                    subtask.completed_at = datetime.now()
                    
                    # 释放Agent资源
                    if subtask.assigned_to:
                        self.allocator.release_task(subtask.assigned_to)
                    break
            
            # 检查任务是否完成
            await self._check_task_completion(task)
    
    async def _check_task_completion(self, task: Task):
        """检查任务完成状态"""
        completed = all(
            s.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]
            for s in task.subtasks
        )
        
        if completed:
            # 所有子任务完成，触发验证
            await self._trigger_validation(task)
    
    async def _trigger_validation(self, task: Task):
        """触发验证流程"""
        # 发送验证请求给验证层
        for validator_id in self._validator_agents:
            await self.send_to_agent(
                validator_id,
                {
                    "action": "validate_task",
                    "task_id": task.task_id,
                    "subtasks_results": [
                        {
                            "subtask_id": s.task_id,
                            "result": s.result,
                            "status": s.status.value
                        }
                        for s in task.subtasks
                    ]
                },
                MessageType.VALIDATION_REQUEST
            )
    
    def register_execution_agent(self, agent_id: str, capabilities: List[str]):
        """注册执行层Agent"""
        self._execution_agents.append(agent_id)
        self.allocator.register_agent(agent_id, capabilities)
    
    def register_validator_agent(self, agent_id: str, capabilities: List[str]):
        """注册验证层Agent"""
        self._validator_agents.append(agent_id)
        self.allocator.register_agent(agent_id, capabilities)
    
    def register_integrator_agent(self, agent_id: str, capabilities: List[str]):
        """注册整合层Agent"""
        self._integrator_agents.append(agent_id)
        self.allocator.register_agent(agent_id, capabilities)
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        if task_id not in self._active_tasks:
            return None
        
        task = self._active_tasks[task_id]
        return {
            "task_id": task_id,
            "status": task.status.value,
            "subtasks_count": len(task.subtasks),
            "completed_subtasks": sum(1 for s in task.subtasks if s.status == TaskStatus.COMPLETED),
            "failed_subtasks": sum(1 for s in task.subtasks if s.status == TaskStatus.FAILED),
            "pending_subtasks": sum(1 for s in task.subtasks if s.status in [TaskStatus.PENDING, TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS]),
            "result": task.final_result
        }
