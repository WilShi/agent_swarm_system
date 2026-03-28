"""
Agent Swarm System
一个三层架构的多Agent协作系统
"""
from .swarm_manager import SwarmManager, create_swarm, run_task
from .core import (
    AgentConfig, AgentRole, Message, MessageType,
    Task, SubTask, TaskStatus, ValidationResult,
    SwarmConfig, BaseAgent, MessageBus
)
from .layers import (
    CoordinatorAgent, ExecutorAgent, ValidatorAgent, IntegratorAgent,
    TaskDecomposer, ResourceAllocator,
    ToolRegistry, ExecutionContext,
    ValidationEngine, IntegrationEngine, QualityMetrics
)

__version__ = "1.0.0"
__all__ = [
    # Manager
    'SwarmManager', 'create_swarm', 'run_task',
    # Core Types
    'AgentConfig', 'AgentRole', 'Message', 'MessageType',
    'Task', 'SubTask', 'TaskStatus', 'ValidationResult',
    'SwarmConfig', 'BaseAgent', 'MessageBus',
    # Layer Components
    'CoordinatorAgent', 'ExecutorAgent', 'ValidatorAgent', 'IntegratorAgent',
    'TaskDecomposer', 'ResourceAllocator',
    'ToolRegistry', 'ExecutionContext',
    'ValidationEngine', 'IntegrationEngine', 'QualityMetrics'
]
