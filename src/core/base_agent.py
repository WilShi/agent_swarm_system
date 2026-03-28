"""
Agent基类
"""
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

from .types import (
    AgentConfig, AgentRole, Message, MessageType, 
    Task, SubTask, TaskStatus
)
from .message_bus import MessageBus


class BaseAgent(ABC):
    """Agent基类"""
    
    def __init__(self, config: AgentConfig, message_bus: MessageBus):
        self.config = config
        self.message_bus = message_bus
        self._running = False
        self._task_queue: asyncio.Queue = asyncio.Queue()
        self._current_tasks: Dict[str, SubTask] = {}
        self._message_handlers: Dict[MessageType, List[Callable]] = {}
        self._lock = asyncio.Lock()
        self._metrics = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "start_time": None
        }
    
    async def start(self):
        """启动Agent"""
        await self.message_bus.register_agent(self.config.agent_id)
        self._running = True
        self._metrics["start_time"] = datetime.now()
        
        # 启动消息监听
        asyncio.create_task(self._message_loop())
        
        # 启动任务处理
        asyncio.create_task(self._task_loop())
        
        await self.on_start()
    
    async def stop(self):
        """停止Agent"""
        self._running = False
        await self.message_bus.unregister_agent(self.config.agent_id)
        await self.on_stop()
    
    @abstractmethod
    async def on_start(self):
        """启动时的自定义逻辑"""
        pass
    
    @abstractmethod
    async def on_stop(self):
        """停止时的自定义逻辑"""
        pass
    
    @abstractmethod
    async def process_task(self, task: SubTask) -> Any:
        """处理任务的核心逻辑"""
        pass
    
    async def send_message(self, message: Message) -> bool:
        """发送消息"""
        success = await self.message_bus.send_message(message)
        if success:
            self._metrics["messages_sent"] += 1
        return success
    
    async def send_to_agent(self, receiver_id: str, content: Dict[str, Any], 
                           msg_type: MessageType = MessageType.DIRECT) -> bool:
        """发送消息给指定Agent"""
        message = Message(
            msg_type=msg_type,
            sender_id=self.config.agent_id,
            receiver_id=receiver_id,
            content=content
        )
        return await self.send_message(message)
    
    async def broadcast(self, content: Dict[str, Any], 
                       msg_type: MessageType = MessageType.BROADCAST) -> bool:
        """广播消息"""
        message = Message(
            msg_type=msg_type,
            sender_id=self.config.agent_id,
            receiver_id=None,
            content=content
        )
        return await self.send_message(message)
    
    def register_message_handler(self, msg_type: MessageType, 
                                  handler: Callable[[Message], Any]):
        """注册消息处理器"""
        if msg_type not in self._message_handlers:
            self._message_handlers[msg_type] = []
        self._message_handlers[msg_type].append(handler)
    
    async def _message_loop(self):
        """消息监听循环"""
        while self._running:
            try:
                message = await self.message_bus.receive_message(
                    self.config.agent_id,
                    timeout=1.0
                )
                if message:
                    self._metrics["messages_received"] += 1
                    await self._handle_message(message)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                await self.on_error("message_loop", e)
    
    async def _handle_message(self, message: Message):
        """处理消息"""
        # 调用特定类型的处理器
        handlers = self._message_handlers.get(message.msg_type, [])
        for handler in handlers:
            try:
                await handler(message)
            except Exception as e:
                await self.on_error("message_handler", e)
        
        # 调用通用消息处理
        await self.on_message(message)
    
    async def on_message(self, message: Message):
        """通用消息处理，子类可重写"""
        pass
    
    async def _task_loop(self):
        """任务处理循环"""
        while self._running:
            try:
                task = await asyncio.wait_for(self._task_queue.get(), timeout=1.0)
                await self._execute_task(task)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                await self.on_error("task_loop", e)
    
    async def _execute_task(self, task: SubTask):
        """执行任务"""
        async with self._lock:
            if len(self._current_tasks) >= self.config.max_concurrent_tasks:
                await self._task_queue.put(task)
                return
            self._current_tasks[task.task_id] = task
        
        task.status = TaskStatus.IN_PROGRESS
        task.assigned_to = self.config.agent_id
        
        try:
            result = await asyncio.wait_for(
                self.process_task(task),
                timeout=self.config.timeout_seconds
            )
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            self._metrics["tasks_completed"] += 1
            
            # 发送任务完成消息
            await self.send_task_result(task)
            
        except asyncio.TimeoutError:
            task.status = TaskStatus.FAILED
            task.retry_count += 1
            self._metrics["tasks_failed"] += 1
            
            if task.retry_count < task.max_retries:
                task.status = TaskStatus.PENDING
                await self._task_queue.put(task)
            else:
                await self.send_task_result(task, success=False)
                
        except Exception as e:
            task.status = TaskStatus.FAILED
            self._metrics["tasks_failed"] += 1
            await self.on_error("task_execution", e)
            await self.send_task_result(task, success=False)
        
        finally:
            async with self._lock:
                if task.task_id in self._current_tasks:
                    del self._current_tasks[task.task_id]
    
    async def assign_task(self, task: SubTask) -> bool:
        """分配任务给Agent"""
        try:
            await self._task_queue.put(task)
            task.status = TaskStatus.ASSIGNED
            return True
        except Exception:
            return False
    
    async def send_task_result(self, task: SubTask, success: bool = True):
        """发送任务结果"""
        if task.parent_task_id:
            content = {
                "task_id": task.task_id,
                "parent_task_id": task.parent_task_id,
                "result": task.result if success else None,
                "success": success,
                "status": task.status.value
            }
            await self.broadcast(content, MessageType.TASK_RESULT)
    
    async def on_error(self, context: str, error: Exception):
        """错误处理，子类可重写"""
        print(f"Agent {self.config.agent_id} error in {context}: {error}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取Agent指标"""
        metrics = self._metrics.copy()
        if metrics["start_time"]:
            metrics["uptime_seconds"] = (datetime.now() - metrics["start_time"]).total_seconds()
        metrics["current_tasks"] = len(self._current_tasks)
        metrics["queue_size"] = self._task_queue.qsize()
        return metrics
    
    def has_capability(self, capability: str) -> bool:
        """检查是否具有特定能力"""
        return capability in self.config.capabilities
