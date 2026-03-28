"""
Agent Swarm 核心类型定义
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, AsyncIterator
from enum import Enum, auto
from datetime import datetime
from uuid import uuid4


# ============ Enums ============

class AgentRole(Enum):
    """Agent角色类型"""
    COORDINATOR = "coordinator"      # 协调器
    PLANNER = "planner"              # 规划器
    EXECUTOR = "executor"            # 执行器
    VALIDATOR = "validator"          # 验证器
    INTEGRATOR = "integrator"        # 整合器


class TaskType(Enum):
    """任务类型枚举"""
    ANALYSIS = "analysis"
    GENERATION = "generation"
    CODE = "code"
    RESEARCH = "research"
    DEBUG = "debug"
    TEST = "test"
    AUTOMATION = "automation"
    GENERAL = "general"


class HarnessType(Enum):
    """Harness 类型枚举"""
    CLAUDE_CODE = "claude_code"
    TEST = "test"
    EXECUTION = "execution"
    RESEARCH = "research"
    CODE = "code"
    DEBUG = "debug"


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    VALIDATING = "validating"
    VALIDATED = "validated"
    REJECTED = "rejected"


class MessageType(Enum):
    """消息类型"""
    TASK_ASSIGN = "task_assign"
    TASK_RESULT = "task_result"
    VALIDATION_REQUEST = "validation_request"
    VALIDATION_RESULT = "validation_result"
    COORDINATION = "coordination"
    BROADCAST = "broadcast"
    DIRECT = "direct"


# ============ Existing Core Types ============

@dataclass
class Message:
    """Agent间消息"""
    msg_id: str = field(default_factory=lambda: str(uuid4()))
    msg_type: MessageType = MessageType.DIRECT
    sender_id: str = ""
    receiver_id: Optional[str] = None  # None表示广播
    content: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    priority: int = 1  # 1-10, 数字越大优先级越高


@dataclass
class SubTask:
    """子任务定义"""
    task_id: str = field(default_factory=lambda: str(uuid4()))
    parent_task_id: Optional[str] = None
    description: str = ""
    task_type: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: Optional[str] = None
    result: Any = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool = False
    score: float = 0.0  # 0-1
    feedback: str = ""
    suggestions: List[str] = field(default_factory=list)
    validator_id: str = ""
    validated_at: datetime = field(default_factory=datetime.now)


@dataclass
class AgentConfig:
    """Agent配置"""
    agent_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    role: AgentRole = AgentRole.EXECUTOR
    capabilities: List[str] = field(default_factory=list)
    llm_config: Dict[str, Any] = field(default_factory=dict)
    max_concurrent_tasks: int = 3
    timeout_seconds: int = 300


@dataclass
class SwarmConfig:
    """Swarm系统配置"""
    swarm_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    max_agents: int = 10
    enable_load_balancing: bool = True
    enable_fault_tolerance: bool = True
    message_queue_size: int = 1000


# ============ New Classification Types ============

@dataclass
class IntentAnalysis:
    """意图分析结果"""
    primary_intent: str
    secondary_intents: List[str] = field(default_factory=list)
    entities: Dict[str, Any] = field(default_factory=dict)
    sentiment: str = "neutral"
    urgency: str = "normal"


@dataclass
class ClassificationResult:
    """分类结果"""
    intent: IntentAnalysis
    task_type: TaskType
    harness_type: HarnessType
    confidence: float
    reasoning: str
    sub_tasks: List[str] = field(default_factory=list)
    requirements: Dict[str, Any] = field(default_factory=dict)
    keywords: List[str] = field(default_factory=list)
    estimated_complexity: str = "medium"
    estimated_duration: int = 60


@dataclass
class ConfirmationRequest:
    """确认请求"""
    classification: ClassificationResult
    question: str
    options: List[Dict[str, str]]
    timeout: int = 300
    allow_override: bool = True


@dataclass
class ConfirmationResponse:
    """确认响应"""
    confirmed: bool
    selected_harness: HarnessType
    modifications: Dict[str, Any] = field(default_factory=dict)
    feedback: str = ""


@dataclass
class HarnessConfig:
    """Harness 配置基类"""
    harness_type: HarnessType
    enabled: bool = True
    timeout: int = 300
    max_retries: int = 3
    custom_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    """任务定义"""
    task_id: str = field(default_factory=lambda: str(uuid4()))
    description: str = ""
    task_type: Optional[TaskType] = None
    harness_type: Optional[HarnessType] = None
    requirements: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    subtasks: List[SubTask] = field(default_factory=list)
    final_result: Any = None


@dataclass
class TaskResult:
    """任务结果"""
    task_id: str = ""
    status: str = ""
    output: Any = None
    quality_score: float = 0.0
    execution_time: float = 0.0
    tokens_used: int = 0
    logs: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
