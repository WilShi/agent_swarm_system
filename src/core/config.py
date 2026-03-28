"""
Agent Swarm 配置管理模块
支持从环境变量和 .env 文件加载配置
"""
import os
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class LLMConfig:
    """LLM配置"""
    provider: str = "ollama"  # openai, anthropic, azure, ollama, dashscope
    model: str = "llama3.2"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2000
    max_retries: int = 3
    request_timeout: int = 60
    streaming: bool = False
    max_concurrent: int = 5
    
    # Azure特有配置
    azure_endpoint: Optional[str] = None
    azure_api_version: Optional[str] = None
    
    # 额外参数
    extra_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SwarmSystemConfig:
    """Swarm系统配置"""
    max_agents: int = 10
    message_queue_size: int = 1000
    enable_load_balancing: bool = True
    enable_fault_tolerance: bool = True
    task_default_timeout: int = 300


@dataclass
class LogConfig:
    """日志配置"""
    level: str = "INFO"
    colorful: bool = True
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class ConfigManager:
    """配置管理器"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if ConfigManager._initialized:
            return
        
        self._load_env_file()
        self.llm_config = self._load_llm_config()
        self.swarm_config = self._load_swarm_config()
        self.log_config = self._load_log_config()
        
        ConfigManager._initialized = True
    
    def _load_env_file(self):
        """加载.env文件"""
        try:
            from dotenv import load_dotenv
            # 尝试加载.env文件
            env_path = os.path.join(os.getcwd(), '.env')
            if os.path.exists(env_path):
                load_dotenv(env_path, override=True)
                print(f"✅ 已加载配置文件: {env_path}")
            else:
                print(f"⚠️  未找到 .env 文件，使用默认配置")
                print(f"   如需配置，请复制 .env.example 为 .env 并填写你的API密钥")
        except ImportError:
            print("⚠️  未安装 python-dotenv，环境变量需要从系统加载")
    
    def _load_llm_config(self) -> LLMConfig:
        """加载LLM配置"""
        provider = os.getenv('DEFAULT_LLM_PROVIDER', 'ollama').lower()
        
        config = LLMConfig(
            provider=provider,
            model=os.getenv('DEFAULT_LLM_MODEL', 'llama3.2'),
            temperature=float(os.getenv('DEFAULT_TEMPERATURE', '0.7')),
            max_tokens=int(os.getenv('DEFAULT_MAX_TOKENS', '2000')),
            max_retries=int(os.getenv('LLM_MAX_RETRIES', '3')),
            request_timeout=int(os.getenv('LLM_REQUEST_TIMEOUT', '60')),
            streaming=os.getenv('LLM_STREAMING', 'false').lower() == 'true',
            max_concurrent=int(os.getenv('LLM_MAX_CONCURRENT', '5'))
        )
        
        # 根据提供商加载特定配置
        if provider == 'openai':
            config.api_key = os.getenv('OPENAI_API_KEY')
            config.base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
            config.model = os.getenv('OPENAI_MODEL', config.model)
            
        elif provider == 'anthropic':
            config.api_key = os.getenv('ANTHROPIC_API_KEY')
            config.base_url = os.getenv('ANTHROPIC_BASE_URL', 'https://api.anthropic.com')
            config.model = os.getenv('ANTHROPIC_MODEL', 'claude-3-sonnet-20240229')
            
        elif provider == 'azure':
            config.api_key = os.getenv('AZURE_OPENAI_API_KEY')
            config.azure_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
            config.model = os.getenv('AZURE_OPENAI_MODEL', 'gpt-4')
            config.azure_api_version = os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-01')
            
        elif provider == 'ollama':
            config.base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
            config.model = os.getenv('OLLAMA_MODEL', 'llama3.2')
            
        elif provider == 'dashscope':
            config.api_key = os.getenv('DASHSCOPE_API_KEY')
            config.base_url = os.getenv('DASHSCOPE_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
            config.model = os.getenv('DASHSCOPE_MODEL', 'qwen-max')
        
        return config
    
    def _load_swarm_config(self) -> SwarmSystemConfig:
        """加载Swarm系统配置"""
        return SwarmSystemConfig(
            max_agents=int(os.getenv('SWARM_MAX_AGENTS', '10')),
            message_queue_size=int(os.getenv('SWARM_MESSAGE_QUEUE_SIZE', '1000')),
            enable_load_balancing=os.getenv('SWARM_ENABLE_LOAD_BALANCING', 'true').lower() == 'true',
            enable_fault_tolerance=os.getenv('SWARM_ENABLE_FAULT_TOLERANCE', 'true').lower() == 'true',
            task_default_timeout=int(os.getenv('TASK_DEFAULT_TIMEOUT', '300'))
        )
    
    def _load_log_config(self) -> LogConfig:
        """加载日志配置"""
        return LogConfig(
            level=os.getenv('LOG_LEVEL', 'INFO').upper(),
            colorful=os.getenv('LOG_COLORFUL', 'true').lower() == 'true'
        )
    
    def get_llm_config(self, provider: str = None) -> LLMConfig:
        """
        获取LLM配置
        
        Args:
            provider: 指定提供商，默认使用配置的默认提供商
        
        Returns:
            LLMConfig实例
        """
        if provider is None or provider == self.llm_config.provider:
            return self.llm_config
        
        # 返回特定提供商的配置（从环境变量重新加载）
        config = LLMConfig(provider=provider)
        
        if provider == 'openai':
            config.api_key = os.getenv('OPENAI_API_KEY')
            config.base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
            config.model = os.getenv('OPENAI_MODEL', 'gpt-4')
            
        elif provider == 'anthropic':
            config.api_key = os.getenv('ANTHROPIC_API_KEY')
            config.base_url = os.getenv('ANTHROPIC_BASE_URL', 'https://api.anthropic.com')
            config.model = os.getenv('ANTHROPIC_MODEL', 'claude-3-sonnet-20240229')
            
        elif provider == 'ollama':
            config.base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
            config.model = os.getenv('OLLAMA_MODEL', 'llama3.2')
            
        elif provider == 'dashscope':
            config.api_key = os.getenv('DASHSCOPE_API_KEY')
            config.base_url = os.getenv('DASHSCOPE_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
            config.model = os.getenv('DASHSCOPE_MODEL', 'qwen-max')
        
        return config
    
    def update_llm_config(self, **kwargs):
        """更新LLM配置（运行时）"""
        for key, value in kwargs.items():
            if hasattr(self.llm_config, key):
                setattr(self.llm_config, key, value)
    
    def validate_config(self) -> Dict[str, Any]:
        """
        验证配置是否完整
        
        Returns:
            包含验证结果的字典
        """
        errors = []
        warnings = []
        
        # 验证LLM配置
        if self.llm_config.provider in ['openai', 'anthropic', 'azure', 'dashscope']:
            if not self.llm_config.api_key:
                errors.append(f"{self.llm_config.provider} 需要提供API密钥")
        
        if self.llm_config.provider == 'azure':
            if not self.llm_config.azure_endpoint:
                errors.append("Azure OpenAI 需要提供 ENDPOINT")
        
        if self.llm_config.provider == 'ollama':
            # 检查Ollama是否可连接
            import urllib.request
            try:
                urllib.request.urlopen(
                    f"{self.llm_config.base_url}/api/tags", 
                    timeout=2
                )
            except Exception as e:
                warnings.append(f"无法连接到Ollama服务: {e}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def print_config(self, hide_secrets: bool = True):
        """打印当前配置"""
        print("\n" + "=" * 60)
        print("📋 当前配置信息")
        print("=" * 60)
        
        print("\n🤖 LLM配置:")
        print(f"  提供商: {self.llm_config.provider}")
        print(f"  模型: {self.llm_config.model}")
        
        if self.llm_config.api_key:
            key_display = self.llm_config.api_key[:8] + "..." if hide_secrets else self.llm_config.api_key
            print(f"  API密钥: {key_display}")
        else:
            print(f"  API密钥: 未设置")
        
        if self.llm_config.base_url:
            print(f"  Base URL: {self.llm_config.base_url}")
        
        print(f"  温度: {self.llm_config.temperature}")
        print(f"  最大Token: {self.llm_config.max_tokens}")
        
        print("\n⚙️ Swarm配置:")
        print(f"  最大Agent数: {self.swarm_config.max_agents}")
        print(f"  负载均衡: {'开启' if self.swarm_config.enable_load_balancing else '关闭'}")
        print(f"  故障容错: {'开启' if self.swarm_config.enable_fault_tolerance else '关闭'}")
        
        print("\n📝 日志配置:")
        print(f"  日志级别: {self.log_config.level}")
        print(f"  彩色输出: {'开启' if self.log_config.colorful else '关闭'}")
        
        print("=" * 60)


# 全局配置实例
config = ConfigManager()


# 便捷函数
def get_config() -> ConfigManager:
    """获取配置管理器实例"""
    return config


def reload_config():
    """重新加载配置"""
    ConfigManager._initialized = False
    return ConfigManager()


if __name__ == "__main__":
    # 测试配置加载
    cfg = ConfigManager()
    cfg.print_config()
    
    # 验证配置
    validation = cfg.validate_config()
    if not validation["valid"]:
        print("\n❌ 配置错误:")
        for error in validation["errors"]:
            print(f"  - {error}")
    
    if validation["warnings"]:
        print("\n⚠️ 配置警告:")
        for warning in validation["warnings"]:
            print(f"  - {warning}")
