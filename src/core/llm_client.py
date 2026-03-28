"""
LLM客户端模块
支持多种LLM提供商: OpenAI, Anthropic, Azure, Ollama, DashScope(阿里百炼)
"""
import asyncio
import json
from typing import AsyncIterator, Dict, Any, Optional, List
from abc import ABC, abstractmethod

from .config import LLMConfig, get_config


class BaseLLMClient(ABC):
    """LLM客户端基类"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
    
    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], 
                   temperature: float = None,
                   max_tokens: int = None,
                   stream: bool = False) -> str:
        """
        发送聊天请求
        
        Args:
            messages: 消息列表，格式 [{"role": "user", "content": "..."}, ...]
            temperature: 温度参数
            max_tokens: 最大token数
            stream: 是否流式输出
        
        Returns:
            模型回复文本
        """
        pass
    
    @abstractmethod
    async def chat_stream(self, messages: List[Dict[str, str]],
                          temperature: float = None,
                          max_tokens: int = None) -> AsyncIterator[str]:
        """流式聊天请求"""
        pass
    
    def _prepare_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """准备消息格式"""
        return messages


class OpenAICompatibleClient(BaseLLMClient):
    """
    OpenAI兼容客户端
    支持OpenAI、Azure、DashScope等兼容OpenAI API的提供商
    """
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.session = None
    
    async def _get_session(self):
        """获取HTTP会话"""
        if self.session is None:
            import aiohttp
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def chat(self, messages: List[Dict[str, str]],
                   temperature: float = None,
                   max_tokens: int = None,
                   stream: bool = False) -> str:
        """发送聊天请求"""
        session = await self._get_session()
        
        headers = {
            "Content-Type": "application/json"
        }
        
        # 添加API密钥
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        
        # 准备请求体
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "stream": stream
        }
        
        # 添加额外参数
        if self.config.extra_params:
            payload.update(self.config.extra_params)
        
        url = f"{self.config.base_url}/chat/completions"
        
        try:
            async with session.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.config.request_timeout
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API请求失败: {response.status} - {error_text}")
                
                result = await response.json()
                return result["choices"][0]["message"]["content"]
                
        except asyncio.TimeoutError:
            raise Exception(f"请求超时 (> {self.config.request_timeout}秒)")
        except Exception as e:
            raise Exception(f"请求失败: {e}")
    
    async def chat_stream(self, messages: List[Dict[str, str]],
                          temperature: float = None,
                          max_tokens: int = None) -> AsyncIterator[str]:
        """流式聊天请求"""
        session = await self._get_session()
        
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "stream": True
        }
        
        url = f"{self.config.base_url}/chat/completions"
        
        async with session.post(
            url,
            headers=headers,
            json=payload,
            timeout=self.config.request_timeout
        ) as response:
            async for line in response.content:
                line = line.decode('utf-8').strip()
                if line.startswith('data: '):
                    data = line[6:]
                    if data == '[DONE]':
                        break
                    try:
                        chunk = json.loads(data)
                        if 'choices' in chunk and len(chunk['choices']) > 0:
                            delta = chunk['choices'][0].get('delta', {})
                            if 'content' in delta:
                                yield delta['content']
                    except json.JSONDecodeError:
                        pass
    
    async def close(self):
        """关闭会话"""
        if self.session:
            await self.session.close()
            self.session = None


class OllamaClient(BaseLLMClient):
    """Ollama本地模型客户端"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.session = None
    
    async def _get_session(self):
        """获取HTTP会话"""
        if self.session is None:
            import aiohttp
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def chat(self, messages: List[Dict[str, str]],
                   temperature: float = None,
                   max_tokens: int = None,
                   stream: bool = False) -> str:
        """发送聊天请求"""
        session = await self._get_session()
        
        # Ollama使用不同的消息格式
        payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature or self.config.temperature
            }
        }
        
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        
        url = f"{self.config.base_url}/api/chat"
        
        try:
            async with session.post(
                url,
                json=payload,
                timeout=self.config.request_timeout
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Ollama请求失败: {response.status} - {error_text}")
                
                result = await response.json()
                return result["message"]["content"]
                
        except asyncio.TimeoutError:
            raise Exception(f"请求超时 (> {self.config.request_timeout}秒)")
        except Exception as e:
            raise Exception(f"请求失败: {e}")
    
    async def chat_stream(self, messages: List[Dict[str, str]],
                          temperature: float = None,
                          max_tokens: int = None) -> AsyncIterator[str]:
        """流式聊天请求"""
        session = await self._get_session()
        
        payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature or self.config.temperature
            }
        }
        
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        
        url = f"{self.config.base_url}/api/chat"
        
        async with session.post(
            url,
            json=payload,
            timeout=self.config.request_timeout
        ) as response:
            async for line in response.content:
                line = line.decode('utf-8').strip()
                if line:
                    try:
                        chunk = json.loads(line)
                        if 'message' in chunk and 'content' in chunk['message']:
                            yield chunk['message']['content']
                    except json.JSONDecodeError:
                        pass
    
    async def close(self):
        """关闭会话"""
        if self.session:
            await self.session.close()
            self.session = None


class LLMClientFactory:
    """LLM客户端工厂"""
    
    @staticmethod
    def create_client(config: LLMConfig = None) -> BaseLLMClient:
        """
        创建LLM客户端
        
        Args:
            config: LLM配置，默认使用全局配置
        
        Returns:
            LLM客户端实例
        """
        if config is None:
            config = get_config().llm_config
        
        if config.provider in ['openai', 'azure', 'dashscope']:
            # 这些提供商都兼容OpenAI API格式
            return OpenAICompatibleClient(config)
        elif config.provider == 'ollama':
            return OllamaClient(config)
        elif config.provider == 'anthropic':
            # Anthropic有自己的API格式，这里简化处理
            # 实际使用时可以实现AnthropicClient
            return OpenAICompatibleClient(config)
        else:
            raise ValueError(f"不支持的LLM提供商: {config.provider}")


# 便捷函数
async def chat_completion(
    messages: List[Dict[str, str]],
    config: LLMConfig = None,
    temperature: float = None,
    max_tokens: int = None
) -> str:
    """
    发送聊天完成请求
    
    Args:
        messages: 消息列表
        config: LLM配置
        temperature: 温度
        max_tokens: 最大token数
    
    Returns:
        模型回复
    """
    client = LLMClientFactory.create_client(config)
    try:
        return await client.chat(messages, temperature, max_tokens)
    finally:
        await client.close()


async def chat_completion_stream(
    messages: List[Dict[str, str]],
    config: LLMConfig = None,
    temperature: float = None,
    max_tokens: int = None
) -> AsyncIterator[str]:
    """
    流式聊天完成请求
    
    Args:
        messages: 消息列表
        config: LLM配置
        temperature: 温度
        max_tokens: 最大token数
    
    Yields:
        模型回复的每个token
    """
    client = LLMClientFactory.create_client(config)
    try:
        async for token in client.chat_stream(messages, temperature, max_tokens):
            yield token
    finally:
        await client.close()


# 测试代码
if __name__ == "__main__":
    async def test():
        """测试LLM客户端"""
        config = get_config().llm_config
        print(f"测试 {config.provider} 客户端")
        print(f"模型: {config.model}")
        print(f"Base URL: {config.base_url}")
        
        try:
            client = LLMClientFactory.create_client(config)
            
            messages = [
                {"role": "system", "content": "你是一个有帮助的助手。"},
                {"role": "user", "content": "你好！请简单介绍一下自己。"}
            ]
            
            print("\n发送请求...")
            response = await client.chat(messages)
            print(f"\n回复: {response}")
            
            await client.close()
            
        except Exception as e:
            print(f"错误: {e}")
    
    asyncio.run(test())
