"""
消息总线 - 实现Agent间通信
"""
import asyncio
from typing import Dict, List, Callable, Any
from collections import defaultdict
from .types import Message, MessageType


class MessageBus:
    """异步消息总线"""
    
    def __init__(self, max_queue_size: int = 1000):
        self.max_queue_size = max_queue_size
        self._queues: Dict[str, asyncio.Queue] = {}
        self._subscribers: Dict[MessageType, List[Callable]] = defaultdict(list)
        self._broadcast_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._running = False
        self._lock = asyncio.Lock()
    
    async def start(self):
        """启动消息总线"""
        self._running = True
        asyncio.create_task(self._broadcast_loop())
    
    async def stop(self):
        """停止消息总线"""
        self._running = False
    
    async def register_agent(self, agent_id: str):
        """注册Agent到消息总线"""
        async with self._lock:
            if agent_id not in self._queues:
                self._queues[agent_id] = asyncio.Queue(maxsize=self.max_queue_size)
    
    async def unregister_agent(self, agent_id: str):
        """注销Agent"""
        async with self._lock:
            if agent_id in self._queues:
                del self._queues[agent_id]
    
    async def send_message(self, message: Message) -> bool:
        """发送消息"""
        try:
            if message.msg_type == MessageType.BROADCAST:
                await self._broadcast_queue.put(message)
                return True
            elif message.receiver_id and message.receiver_id in self._queues:
                await self._queues[message.receiver_id].put(message)
                return True
            return False
        except asyncio.QueueFull:
            return False
    
    async def receive_message(self, agent_id: str, timeout: float = None) -> Message:
        """接收消息"""
        if agent_id not in self._queues:
            raise ValueError(f"Agent {agent_id} not registered")
        
        try:
            return await asyncio.wait_for(
                self._queues[agent_id].get(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            return None
    
    def subscribe(self, msg_type: MessageType, callback: Callable[[Message], Any]):
        """订阅特定类型的消息"""
        self._subscribers[msg_type].append(callback)
    
    def unsubscribe(self, msg_type: MessageType, callback: Callable[[Message], Any]):
        """取消订阅"""
        if callback in self._subscribers[msg_type]:
            self._subscribers[msg_type].remove(callback)
    
    async def _broadcast_loop(self):
        """广播循环"""
        while self._running:
            try:
                message = await asyncio.wait_for(
                    self._broadcast_queue.get(),
                    timeout=1.0
                )
                # 发送给所有注册的Agent
                for agent_id, queue in self._queues.items():
                    if agent_id != message.sender_id:
                        try:
                            queue.put_nowait(message)
                        except asyncio.QueueFull:
                            pass
                
                # 调用订阅者回调
                for callback in self._subscribers[message.msg_type]:
                    try:
                        asyncio.create_task(callback(message))
                    except Exception:
                        pass
                        
            except asyncio.TimeoutError:
                continue
            except Exception:
                if not self._running:
                    break


class DirectChannel:
    """点对点通信通道"""
    
    def __init__(self, agent1_id: str, agent2_id: str, bus: MessageBus):
        self.agent1_id = agent1_id
        self.agent2_id = agent2_id
        self.bus = bus
        self._callbacks: List[Callable[[Message], Any]] = []
    
    async def send(self, from_agent: str, content: Dict[str, Any]) -> bool:
        """发送消息"""
        to_agent = self.agent2_id if from_agent == self.agent1_id else self.agent1_id
        message = Message(
            msg_type=MessageType.DIRECT,
            sender_id=from_agent,
            receiver_id=to_agent,
            content=content
        )
        return await self.bus.send_message(message)
    
    def on_message(self, callback: Callable[[Message], Any]):
        """注册消息回调"""
        self._callbacks.append(callback)
    
    async def process_message(self, message: Message):
        """处理接收到的消息"""
        for callback in self._callbacks:
            try:
                await callback(message)
            except Exception:
                pass
