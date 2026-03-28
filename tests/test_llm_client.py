"""
Tests for LLM Client module
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from src.core.llm_client import (
    BaseLLMClient,
    OpenAICompatibleClient,
    OllamaClient,
    LLMClientFactory,
    chat_completion,
    chat_completion_stream,
)
from src.core.config import LLMConfig, get_config

# Check if aiohttp is available
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False


class TestLLMConfig:
    """Test LLM configuration loading"""

    def test_default_config_loading(self):
        """Test that default config loads correctly"""
        config = get_config()
        assert config.llm_config is not None
        assert isinstance(config.llm_config, LLMConfig)

    def test_dashscope_config(self):
        """Test DashScope provider configuration (Kimi K2.5)"""
        config = get_config()
        llm_config = config.get_llm_config('dashscope')

        assert llm_config.provider == 'dashscope'
        assert llm_config.model == 'kimi-k2.5'
        assert llm_config.base_url == 'https://dashscope.aliyuncs.com/compatible-mode/v1'
        # API key should be loaded from env
        assert llm_config.api_key is not None
        assert llm_config.api_key.startswith('sk-')

    def test_ollama_config(self):
        """Test Ollama provider configuration"""
        config = get_config()
        llm_config = config.get_llm_config('ollama')

        assert llm_config.provider == 'ollama'
        assert llm_config.model == 'llama3.2'
        assert llm_config.base_url == 'http://localhost:11434'

    def test_openai_config(self):
        """Test OpenAI provider configuration"""
        config = get_config()
        llm_config = config.get_llm_config('openai')

        assert llm_config.provider == 'openai'
        assert llm_config.base_url == 'https://api.openai.com/v1'


class TestOpenAICompatibleClient:
    """Test OpenAI Compatible Client"""

    @pytest.fixture
    def mock_config(self):
        """Create a mock config for testing"""
        config = LLMConfig(
            provider='dashscope',
            model='kimi-k2.5',
            api_key='test-api-key',
            base_url='https://dashscope.aliyuncs.com/compatible-mode/v1',
            temperature=0.7,
            max_tokens=2000,
            request_timeout=60
        )
        return config

    @pytest.mark.asyncio
    async def test_client_initialization(self, mock_config):
        """Test client initialization"""
        client = OpenAICompatibleClient(mock_config)
        assert client.config == mock_config
        assert client.session is None

    @pytest.mark.asyncio
    @pytest.mark.skipif(not AIOHTTP_AVAILABLE, reason="aiohttp not installed")
    async def test_get_session_creates_session(self, mock_config):
        """Test that _get_session creates a new session"""
        client = OpenAICompatibleClient(mock_config)

        # Mock aiohttp.ClientSession
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session_instance = AsyncMock()
            mock_session_class.return_value = mock_session_instance

            session = await client._get_session()

            mock_session_class.assert_called_once()
            assert session == mock_session_instance

        await client.close()

    @pytest.mark.asyncio
    async def test_close_session(self, mock_config):
        """Test closing the session"""
        client = OpenAICompatibleClient(mock_config)

        # Create a mock session
        mock_session = AsyncMock()
        client.session = mock_session

        await client.close()

        mock_session.close.assert_called_once()
        assert client.session is None


class TestOllamaClient:
    """Test Ollama Client"""

    @pytest.fixture
    def mock_config(self):
        """Create a mock config for Ollama"""
        config = LLMConfig(
            provider='ollama',
            model='llama3.2',
            base_url='http://localhost:11434',
            temperature=0.7,
            max_tokens=2000,
            request_timeout=60
        )
        return config

    @pytest.mark.asyncio
    async def test_client_initialization(self, mock_config):
        """Test Ollama client initialization"""
        client = OllamaClient(mock_config)
        assert client.config == mock_config
        assert client.session is None

    @pytest.mark.asyncio
    @pytest.mark.skipif(not AIOHTTP_AVAILABLE, reason="aiohttp not installed")
    async def test_get_session_creates_session(self, mock_config):
        """Test that _get_session creates a new session"""
        client = OllamaClient(mock_config)

        # Mock aiohttp.ClientSession
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session_instance = AsyncMock()
            mock_session_class.return_value = mock_session_instance

            session = await client._get_session()

            mock_session_class.assert_called_once()
            assert session == mock_session_instance

        await client.close()


class TestLLMClientFactory:
    """Test LLM Client Factory"""

    def test_create_dashscope_client(self):
        """Test creating DashScope client"""
        config = LLMConfig(
            provider='dashscope',
            model='kimi-k2.5',
            api_key='test-key',
            base_url='https://dashscope.aliyuncs.com/compatible-mode/v1'
        )

        client = LLMClientFactory.create_client(config)
        assert isinstance(client, OpenAICompatibleClient)

    def test_create_openai_client(self):
        """Test creating OpenAI client"""
        config = LLMConfig(
            provider='openai',
            model='gpt-4',
            api_key='test-key',
            base_url='https://api.openai.com/v1'
        )

        client = LLMClientFactory.create_client(config)
        assert isinstance(client, OpenAICompatibleClient)

    def test_create_ollama_client(self):
        """Test creating Ollama client"""
        config = LLMConfig(
            provider='ollama',
            model='llama3.2',
            base_url='http://localhost:11434'
        )

        client = LLMClientFactory.create_client(config)
        assert isinstance(client, OllamaClient)

    def test_create_azure_client(self):
        """Test creating Azure client (uses OpenAICompatibleClient)"""
        config = LLMConfig(
            provider='azure',
            model='gpt-4',
            api_key='test-key',
            azure_endpoint='https://test.openai.azure.com'
        )

        client = LLMClientFactory.create_client(config)
        assert isinstance(client, OpenAICompatibleClient)

    def test_create_anthropic_client(self):
        """Test creating Anthropic client (uses OpenAICompatibleClient for now)"""
        config = LLMConfig(
            provider='anthropic',
            model='claude-3-sonnet',
            api_key='test-key'
        )

        client = LLMClientFactory.create_client(config)
        assert isinstance(client, OpenAICompatibleClient)

    def test_create_client_with_default_config(self):
        """Test creating client with default config from get_config()"""
        with patch('src.core.llm_client.get_config') as mock_get_config:
            mock_config = Mock()
            mock_config.llm_config = LLMConfig(
                provider='dashscope',
                model='kimi-k2.5',
                api_key='test-key',
                base_url='https://dashscope.aliyuncs.com/compatible-mode/v1'
            )
            mock_get_config.return_value = mock_config

            client = LLMClientFactory.create_client()
            assert isinstance(client, OpenAICompatibleClient)

    def test_unsupported_provider(self):
        """Test that unsupported provider raises ValueError"""
        config = LLMConfig(
            provider='unsupported',
            model='test-model'
        )

        with pytest.raises(ValueError) as exc_info:
            LLMClientFactory.create_client(config)

        assert "不支持的LLM提供商" in str(exc_info.value)


class TestBaseLLMClient:
    """Test BaseLLMClient abstract class"""

    def test_abstract_methods(self):
        """Test that BaseLLMClient cannot be instantiated directly"""
        config = LLMConfig(provider='test')

        with pytest.raises(TypeError):
            BaseLLMClient(config)

    def test_prepare_messages(self):
        """Test message preparation"""
        # Create a concrete implementation for testing
        class TestClient(BaseLLMClient):
            async def chat(self, messages, temperature=None, max_tokens=None, stream=False):
                return "test"

            async def chat_stream(self, messages, temperature=None, max_tokens=None):
                yield "test"

        config = LLMConfig(provider='test')
        client = TestClient(config)

        messages = [
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi!"}
        ]

        prepared = client._prepare_messages(messages)
        assert prepared == messages


class TestConfigCompatibility:
    """Test that LLM client is compatible with config structure"""

    def test_import_path(self):
        """Test that import from src.core.config works correctly"""
        # This tests the import statement in llm_client.py
        from src.core.llm_client import get_config as llm_get_config
        from src.core.config import get_config as core_get_config

        assert llm_get_config == core_get_config

    def test_llm_config_attributes(self):
        """Test that all required LLMConfig attributes are accessible"""
        config = LLMConfig(
            provider='dashscope',
            model='kimi-k2.5',
            api_key='test-key',
            base_url='https://dashscope.aliyuncs.com/compatible-mode/v1',
            temperature=0.7,
            max_tokens=2000,
            max_retries=3,
            request_timeout=60,
            streaming=False,
            max_concurrent=5,
            azure_endpoint=None,
            azure_api_version=None,
            extra_params={}
        )

        # Verify all attributes used by OpenAICompatibleClient
        assert config.provider == 'dashscope'
        assert config.model == 'kimi-k2.5'
        assert config.api_key == 'test-key'
        assert config.base_url == 'https://dashscope.aliyuncs.com/compatible-mode/v1'
        assert config.temperature == 0.7
        assert config.max_tokens == 2000
        assert config.request_timeout == 60
        assert config.extra_params == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
