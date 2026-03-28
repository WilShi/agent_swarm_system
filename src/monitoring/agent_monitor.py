"""
Agent 监控器 - 跟踪每个 Agent 的工作状态和进度
"""
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class AgentStatus(Enum):
    """Agent 工作状态"""
    IDLE = "idle"           # 空闲
    WORKING = "working"     # 工作中
    COMPLETED = "completed" # 已完成
    FAILED = "failed"       # 失败
    OFFLINE = "offline"     # 离线


@dataclass
class AgentWorkInfo:
    """Agent 工作信息"""
    agent_id: str
    agent_name: str
    agent_role: str
    status: AgentStatus
    current_task: Optional[str] = None
    task_type: Optional[str] = None
    task_description: str = ""
    progress: float = 0.0  # 0-100
    start_time: Optional[datetime] = None
    elapsed_time: float = 0.0  # 秒
    result: Any = None
    error: Optional[str] = None
    history: List[Dict[str, Any]] = field(default_factory=list)


class AgentMonitor:
    """Agent 监控器"""

    def __init__(self):
        self._agents: Dict[str, AgentWorkInfo] = {}
        self._update_callbacks: List[callable] = []
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None

    def register_agent(self, agent_id: str, agent_name: str, agent_role: str):
        """注册 Agent"""
        self._agents[agent_id] = AgentWorkInfo(
            agent_id=agent_id,
            agent_name=agent_name,
            agent_role=agent_role,
            status=AgentStatus.IDLE
        )

    def update_agent_status(self, agent_id: str, status: AgentStatus, **kwargs):
        """更新 Agent 状态"""
        if agent_id not in self._agents:
            return

        agent = self._agents[agent_id]
        agent.status = status

        if status == AgentStatus.WORKING:
            agent.current_task = kwargs.get("task_id")
            agent.task_type = kwargs.get("task_type")
            agent.task_description = kwargs.get("task_description", "")
            agent.progress = kwargs.get("progress", 0.0)
            agent.start_time = datetime.now()
            agent.result = None
            agent.error = None

        elif status in [AgentStatus.COMPLETED, AgentStatus.FAILED]:
            agent.progress = 100.0 if status == AgentStatus.COMPLETED else 0.0
            agent.result = kwargs.get("result")
            agent.error = kwargs.get("error")

            # 记录到历史
            if agent.current_task:
                agent.history.append({
                    "task_id": agent.current_task,
                    "task_type": agent.task_type,
                    "status": status.value,
                    "result": agent.result,
                    "error": agent.error,
                    "completed_at": datetime.now().isoformat()
                })

        # 触发回调
        for callback in self._update_callbacks:
            asyncio.create_task(callback(agent_id, agent))

    def update_progress(self, agent_id: str, progress: float, **kwargs):
        """更新进度"""
        if agent_id not in self._agents:
            return

        agent = self._agents[agent_id]
        agent.progress = min(100.0, max(0.0, progress))

        if agent.start_time:
            agent.elapsed_time = (datetime.now() - agent.start_time).total_seconds()

        # 更新其他字段
        for key, value in kwargs.items():
            if hasattr(agent, key):
                setattr(agent, key, value)

    def get_agent_info(self, agent_id: str) -> Optional[AgentWorkInfo]:
        """获取 Agent 信息"""
        return self._agents.get(agent_id)

    def get_working_agents(self) -> List[AgentWorkInfo]:
        """获取正在工作的 Agent"""
        return [a for a in self._agents.values() if a.status == AgentStatus.WORKING]

    def get_idle_agents(self) -> List[AgentWorkInfo]:
        """获取空闲的 Agent"""
        return [a for a in self._agents.values() if a.status == AgentStatus.IDLE]

    def get_completed_agents(self) -> List[AgentWorkInfo]:
        """获取已完成的 Agent"""
        return [a for a in self._agents.values() if a.status == AgentStatus.COMPLETED]

    def get_all_agents(self) -> List[AgentWorkInfo]:
        """获取所有 Agent"""
        return list(self._agents.values())

    def get_agent_stats(self) -> Dict[str, Any]:
        """获取 Agent 统计信息"""
        total = len(self._agents)
        working = len(self.get_working_agents())
        idle = len(self.get_idle_agents())
        completed = len(self.get_completed_agents())
        failed = len([a for a in self._agents.values() if a.status == AgentStatus.FAILED])

        return {
            "total": total,
            "working": working,
            "idle": idle,
            "completed": completed,
            "failed": failed,
            "utilization_rate": working / total if total > 0 else 0.0
        }

    def on_update(self, callback: Any):
        """注册更新回调"""
        self._update_callbacks.append(callback)

    async def start_monitoring(self, interval: float = 1.0):
        """开始监控"""
        self._monitoring = True
        while self._monitoring:
            # 更新所有工作中的 Agent 的 elapsed_time
            for agent in self._agents.values():
                if agent.status == AgentStatus.WORKING and agent.start_time:
                    agent.elapsed_time = (datetime.now() - agent.start_time).total_seconds()
            await asyncio.sleep(interval)

    def stop_monitoring(self):
        """停止监控"""
        self._monitoring = False
