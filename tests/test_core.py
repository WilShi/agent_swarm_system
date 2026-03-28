"""
Agent Swarm 核心模块测试
"""
import asyncio
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.types import (
    AgentConfig, AgentRole, Message, MessageType,
    Task, SubTask, TaskStatus, ValidationResult, SwarmConfig
)
from src.core.message_bus import MessageBus, DirectChannel


class TestTypes:
    """测试核心类型"""
    
    def test_agent_config_creation(self):
        """测试Agent配置创建"""
        config = AgentConfig(
            name="TestAgent",
            role=AgentRole.EXECUTOR,
            capabilities=["test", "demo"]
        )
        
        assert config.name == "TestAgent"
        assert config.role == AgentRole.EXECUTOR
        assert "test" in config.capabilities
        assert config.agent_id is not None
    
    def test_message_creation(self):
        """测试消息创建"""
        msg = Message(
            msg_type=MessageType.TASK_ASSIGN,
            sender_id="agent1",
            receiver_id="agent2",
            content={"task": "test"},
            priority=5
        )
        
        assert msg.msg_type == MessageType.TASK_ASSIGN
        assert msg.sender_id == "agent1"
        assert msg.receiver_id == "agent2"
        assert msg.content["task"] == "test"
        assert msg.priority == 5
        assert msg.msg_id is not None
    
    def test_task_creation(self):
        """测试任务创建"""
        task = Task(
            description="Test task",
            requirements={"key": "value"},
            metadata={"type": "test"}
        )
        
        assert task.description == "Test task"
        assert task.requirements["key"] == "value"
        assert task.status == TaskStatus.PENDING
        assert task.task_id is not None
    
    def test_subtask_creation(self):
        """测试子任务创建"""
        subtask = SubTask(
            parent_task_id="parent123",
            description="Sub task",
            task_type="test"
        )
        
        assert subtask.parent_task_id == "parent123"
        assert subtask.description == "Sub task"
        assert subtask.task_type == "test"
        assert subtask.status == TaskStatus.PENDING
    
    def test_validation_result(self):
        """测试验证结果"""
        result = ValidationResult(
            is_valid=True,
            score=0.95,
            feedback="Good result",
            suggestions=["improve X"]
        )
        
        assert result.is_valid is True
        assert result.score == 0.95
        assert result.feedback == "Good result"
        assert "improve X" in result.suggestions


class TestMessageBus:
    """测试消息总线"""
    
    @pytest.mark.asyncio
    async def test_message_bus_start_stop(self):
        """测试消息总线启动和停止"""
        bus = MessageBus()
        
        await bus.start()
        assert bus._running is True
        
        await bus.stop()
        assert bus._running is False
    
    @pytest.mark.asyncio
    async def test_agent_registration(self):
        """测试Agent注册"""
        bus = MessageBus()
        await bus.start()
        
        await bus.register_agent("agent1")
        assert "agent1" in bus._queues
        
        await bus.unregister_agent("agent1")
        assert "agent1" not in bus._queues
        
        await bus.stop()
    
    @pytest.mark.asyncio
    async def test_send_receive_message(self):
        """测试发送和接收消息"""
        bus = MessageBus()
        await bus.start()
        
        await bus.register_agent("sender")
        await bus.register_agent("receiver")
        
        msg = Message(
            msg_type=MessageType.DIRECT,
            sender_id="sender",
            receiver_id="receiver",
            content={"data": "test"}
        )
        
        # 发送消息
        success = await bus.send_message(msg)
        assert success is True
        
        # 接收消息
        received = await bus.receive_message("receiver", timeout=1.0)
        assert received is not None
        assert received.content["data"] == "test"
        assert received.sender_id == "sender"
        
        await bus.stop()
    
    @pytest.mark.asyncio
    async def test_broadcast_message(self):
        """测试广播消息"""
        bus = MessageBus()
        await bus.start()
        
        await bus.register_agent("sender")
        await bus.register_agent("receiver1")
        await bus.register_agent("receiver2")
        
        msg = Message(
            msg_type=MessageType.BROADCAST,
            sender_id="sender",
            receiver_id=None,
            content={"broadcast": "test"}
        )
        
        success = await bus.send_message(msg)
        assert success is True
        
        # 等待广播处理
        await asyncio.sleep(0.1)
        
        await bus.stop()
    
    @pytest.mark.asyncio
    async def test_message_subscription(self):
        """测试消息订阅"""
        bus = MessageBus()
        await bus.start()
        
        received_messages = []
        
        async def callback(msg):
            received_messages.append(msg)
        
        bus.subscribe(MessageType.BROADCAST, callback)
        
        await bus.register_agent("agent1")
        
        # 使用广播消息类型触发订阅
        msg = Message(
            msg_type=MessageType.BROADCAST,
            sender_id="agent1",
            receiver_id=None,
            content={"task": "test"}
        )
        
        await bus.send_message(msg)
        await asyncio.sleep(0.3)
        
        assert len(received_messages) > 0
        
        await bus.stop()


class TestTaskStatus:
    """测试任务状态"""
    
    def test_task_status_transitions(self):
        """测试任务状态转换"""
        task = SubTask(description="Test")
        
        assert task.status == TaskStatus.PENDING
        
        task.status = TaskStatus.ASSIGNED
        assert task.status == TaskStatus.ASSIGNED
        
        task.status = TaskStatus.IN_PROGRESS
        assert task.status == TaskStatus.IN_PROGRESS
        
        task.status = TaskStatus.COMPLETED
        assert task.status == TaskStatus.COMPLETED
    
    def test_task_with_dependencies(self):
        """测试带依赖的任务"""
        task1 = SubTask(description="Task 1")
        task2 = SubTask(
            description="Task 2",
            dependencies=[task1.task_id]
        )
        
        assert task1.task_id in task2.dependencies
        assert task2.dependencies[0] == task1.task_id


class TestSwarmConfig:
    """测试Swarm配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = SwarmConfig()
        
        assert config.max_agents == 10
        assert config.enable_load_balancing is True
        assert config.enable_fault_tolerance is True
        assert config.message_queue_size == 1000
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = SwarmConfig(
            name="TestSwarm",
            max_agents=5,
            enable_load_balancing=False,
            message_queue_size=500
        )
        
        assert config.name == "TestSwarm"
        assert config.max_agents == 5
        assert config.enable_load_balancing is False
        assert config.message_queue_size == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
