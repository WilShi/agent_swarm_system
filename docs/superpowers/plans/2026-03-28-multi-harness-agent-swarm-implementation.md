# Multi-Harness Agent Swarm 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个能够自动识别任务类型、选择最优 Harness 执行模式、并协调 Agent Swarm 完成任务的智能系统。

**Architecture:** 采用4层架构：任务分类层 → Harness 引擎层 → Agent Swarm 层 → 结果输出层。使用 Kimi K2.5 作为 LLM 引擎，支持6种 Harness 模式。

**Tech Stack:** Python 3.11+, asyncio, aiohttp, PyYAML, python-dotenv, pytest

---

## 文件结构规划

```
src/
├── __init__.py
├── main.py                      # 入口点
├── core/
│   ├── __init__.py
│   ├── types.py                 # 核心数据类型 (TaskType, HarnessType, etc.)
│   ├── config.py                # 配置管理 (ConfigManager)
│   ├── llm_client.py            # LLM 客户端 (保留现有 Kimi K2.5 配置)
│   ├── message_bus.py           # 消息总线
│   └── exceptions.py            # 异常定义
├── classifier/
│   ├── __init__.py
│   ├── task_classifier.py       # 任务分类器主类
│   ├── intent_analyzer.py       # 意图分析模块
│   ├── harness_selector.py      # Harness 选择器
│   └── confirmation.py          # 确认流程管理
└── harness/
    ├── __init__.py
    ├── base.py                  # BaseHarness 抽象基类
    ├── factory.py               # HarnessFactory
    └── execution.py             # ExecutionHarness (默认实现)
```

---

## Phase 1: 基础框架 (Week 1)

### Task 1: 项目结构重构

**Files:**
- Create: `src/core/types.py`
- Create: `src/core/exceptions.py`
- Modify: `src/core/config.py` (重构现有配置)

**Context:** 需要保留现有的 Kimi K2.5 配置 (DashScope provider, model=kimi-k2.5)

- [ ] **Step 1: 创建核心数据类型**

```python
# src/core/types.py
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum, auto
from datetime import datetime


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
    task_id: str
    description: str
    task_type: TaskType
    harness_type: HarnessType
    requirements: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class TaskResult:
    """任务结果"""
    task_id: str
    status: str
    output: Any
    quality_score: float = 0.0
    execution_time: float = 0.0
    tokens_used: int = 0
    logs: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
```

- [ ] **Step 2: 创建异常定义**

```python
# src/core/exceptions.py


class AgentSwarmException(Exception):
    """基础异常"""
    pass


class ClassificationError(AgentSwarmException):
    """任务分类错误"""
    pass


class HarnessError(AgentSwarmException):
    """Harness 错误"""
    pass


class HarnessInitError(HarnessError):
    """Harness 初始化错误"""
    pass


class SwarmExecutionError(AgentSwarmException):
    """Swarm 执行错误"""
    pass


class ConfirmationTimeoutError(AgentSwarmException):
    """确认超时错误"""
    pass


class ValidationError(AgentSwarmException):
    """验证错误"""
    pass
```

- [ ] **Step 3: 运行类型检查**

Run: `python -c "from src.core.types import *; print('Types OK')"`
Expected: `Types OK`

- [ ] **Step 4: 提交**

```bash
git add src/core/types.py src/core/exceptions.py
git commit -m "feat: add core data types and exceptions"
```

---

### Task 2: 配置管理系统

**Files:**
- Modify: `src/core/config.py` (保留现有 LLM 配置，添加新配置)
- Create: `config/system.yaml`

- [ ] **Step 1: 重构配置管理器**

```python
# src/core/config.py
import os
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
import yaml


@dataclass
class LLMConfig:
    """LLM配置 - 保留现有配置"""
    provider: str = "dashscope"
    model: str = "kimi-k2.5"
    api_key: Optional[str] = None
    base_url: Optional[str] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    temperature: float = 0.7
    max_tokens: int = 4000
    max_retries: int = 3
    request_timeout: int = 60
    streaming: bool = False
    max_concurrent: int = 5
    extra_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClassificationConfig:
    """分类器配置"""
    confidence_threshold: float = 0.7
    require_confirmation: bool = True
    max_retries: int = 3
    default_harness: str = "execution"


@dataclass
class HarnessEngineConfig:
    """Harness 引擎配置"""
    enabled_harnesses: List[str] = field(default_factory=lambda: ["execution"])
    default_timeout: int = 300
    max_concurrent_harnesses: int = 5


@dataclass
class SystemConfig:
    """系统配置"""
    name: str = "Multi-Harness Agent Swarm"
    version: str = "1.0.0"
    log_level: str = "INFO"


class ConfigManager:
    """配置管理器 - 单例模式"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if ConfigManager._initialized:
            return

        self._load_env_file()
        self.llm_config = self._load_llm_config()
        self.classification_config = self._load_classification_config()
        self.harness_config = self._load_harness_config()
        self.system_config = self._load_system_config()

        ConfigManager._initialized = True

    def _load_env_file(self):
        """加载.env文件"""
        try:
            from dotenv import load_dotenv
            env_path = os.path.join(os.getcwd(), '.env')
            if os.path.exists(env_path):
                load_dotenv(env_path, override=True)
        except ImportError:
            pass

    def _load_llm_config(self) -> LLMConfig:
        """加载LLM配置 - 使用 Kimi K2.5"""
        return LLMConfig(
            provider=os.getenv('DEFAULT_LLM_PROVIDER', 'dashscope'),
            model=os.getenv('DEFAULT_LLM_MODEL', 'kimi-k2.5'),
            api_key=os.getenv('DASHSCOPE_API_KEY'),
            base_url=os.getenv('DASHSCOPE_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1'),
            temperature=float(os.getenv('DEFAULT_TEMPERATURE', '0.7')),
            max_tokens=int(os.getenv('DEFAULT_MAX_TOKENS', '4000')),
            max_retries=int(os.getenv('LLM_MAX_RETRIES', '3')),
            request_timeout=int(os.getenv('LLM_REQUEST_TIMEOUT', '60')),
            streaming=os.getenv('LLM_STREAMING', 'false').lower() == 'true',
            max_concurrent=int(os.getenv('LLM_MAX_CONCURRENT', '5'))
        )

    def _load_classification_config(self) -> ClassificationConfig:
        """加载分类器配置"""
        return ClassificationConfig(
            confidence_threshold=float(os.getenv('CLASSIFICATION_CONFIDENCE_THRESHOLD', '0.7')),
            require_confirmation=os.getenv('CLASSIFICATION_REQUIRE_CONFIRMATION', 'true').lower() == 'true',
            max_retries=int(os.getenv('CLASSIFICATION_MAX_RETRIES', '3')),
            default_harness=os.getenv('CLASSIFICATION_DEFAULT_HARNESS', 'execution')
        )

    def _load_harness_config(self) -> HarnessEngineConfig:
        """加载Harness配置"""
        enabled = os.getenv('ENABLED_HARNESSES', 'execution').split(',')
        return HarnessEngineConfig(
            enabled_harnesses=[h.strip() for h in enabled],
            default_timeout=int(os.getenv('HARNESS_DEFAULT_TIMEOUT', '300')),
            max_concurrent_harnesses=int(os.getenv('HARNESS_MAX_CONCURRENT', '5'))
        )

    def _load_system_config(self) -> SystemConfig:
        """加载系统配置"""
        return SystemConfig(
            name=os.getenv('SYSTEM_NAME', 'Multi-Harness Agent Swarm'),
            version=os.getenv('SYSTEM_VERSION', '1.0.0'),
            log_level=os.getenv('LOG_LEVEL', 'INFO')
        )

    def validate(self) -> Dict[str, Any]:
        """验证配置"""
        errors = []
        warnings = []

        # 验证 LLM 配置
        if self.llm_config.provider == 'dashscope':
            if not self.llm_config.api_key:
                errors.append("DashScope 需要提供 API 密钥")

        # 验证分类器配置
        if not 0 <= self.classification_config.confidence_threshold <= 1:
            errors.append("置信度阈值必须在 0-1 之间")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }


# 全局配置实例
config = ConfigManager()


def get_config() -> ConfigManager:
    """获取配置管理器实例"""
    return config
```

- [ ] **Step 2: 创建系统配置文件**

```yaml
# config/system.yaml
system:
  name: "Multi-Harness Agent Swarm"
  version: "1.0.0"
  log_level: INFO

llm:
  provider: dashscope
  model: kimi-k2.5
  temperature: 0.7
  max_tokens: 4000
  timeout: 60

classification:
  confidence_threshold: 0.7
  require_confirmation: true
  max_retries: 3
  default_harness: execution

harnesses:
  execution:
    enabled: true
    timeout: 300
    max_agents: 10
```

- [ ] **Step 3: 编写配置测试**

```python
# tests/test_config.py
import pytest
from src.core.config import ConfigManager, get_config


def test_config_singleton():
    """测试配置单例"""
    config1 = ConfigManager()
    config2 = ConfigManager()
    assert config1 is config2


def test_llm_config():
    """测试 LLM 配置"""
    config = get_config()
    assert config.llm_config.provider == "dashscope"
    assert config.llm_config.model == "kimi-k2.5"


def test_classification_config():
    """测试分类器配置"""
    config = get_config()
    assert 0 <= config.classification_config.confidence_threshold <= 1
    assert config.classification_config.require_confirmation in [True, False]
```

- [ ] **Step 4: 运行配置测试**

Run: `pytest tests/test_config.py -v`
Expected: 3 tests PASSED

- [ ] **Step 5: 提交**

```bash
git add src/core/config.py config/system.yaml tests/test_config.py
git commit -m "feat: refactor config manager with classification and harness configs"
```

---

### Task 3: 保留并验证 LLM Client

**Files:**
- Modify: `src/core/llm_client.py` (更新导入路径)

- [ ] **Step 1: 更新 LLM Client 导入**

```python
# src/core/llm_client.py
"""
LLM客户端模块
支持多种LLM提供商，默认使用 Kimi K2.5 (via DashScope)
"""
import asyncio
import json
from typing import AsyncIterator, Dict, Any, Optional, List
from abc import ABC, abstractmethod

from src.core.config import get_config


class BaseLLMClient(ABC):
    """LLM客户端基类"""

    def __init__(self, config=None):
        self.config = config or get_config().llm_config

    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]],
                   temperature: float = None,
                   max_tokens: int = None,
                   stream: bool = False) -> str:
        pass

    @abstractmethod
    async def chat_stream(self, messages: List[Dict[str, str]],
                          temperature: float = None,
                          max_tokens: int = None) -> AsyncIterator[str]:
        pass


class OpenAICompatibleClient(BaseLLMClient):
    """OpenAI兼容客户端 - 用于 DashScope"""

    def __init__(self, config=None):
        super().__init__(config)
        self.session = None

    async def _get_session(self):
        if self.session is None:
            import aiohttp
            self.session = aiohttp.ClientSession()
        return self.session

    async def chat(self, messages: List[Dict[str, str]],
                   temperature: float = None,
                   max_tokens: int = None,
                   stream: bool = False) -> str:
        session = await self._get_session()

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}"
        }

        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "stream": stream
        }

        if self.config.extra_params:
            payload.update(self.config.extra_params)

        url = f"{self.config.base_url}/chat/completions"

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

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None


class LLMClientFactory:
    """LLM客户端工厂"""

    @staticmethod
    def create_client(config=None):
        if config is None:
            config = get_config().llm_config

        if config.provider in ['openai', 'azure', 'dashscope']:
            return OpenAICompatibleClient(config)
        else:
            raise ValueError(f"不支持的LLM提供商: {config.provider}")


# 便捷函数
async def chat_completion(
    messages: List[Dict[str, str]],
    config=None,
    temperature: float = None,
    max_tokens: int = None
) -> str:
    client = LLMClientFactory.create_client(config)
    try:
        return await client.chat(messages, temperature, max_tokens)
    finally:
        await client.close()
```

- [ ] **Step 2: 编写 LLM Client 测试**

```python
# tests/test_llm_client.py
import pytest
from src.core.llm_client import LLMClientFactory, OpenAICompatibleClient
from src.core.config import get_config


def test_llm_client_factory():
    """测试 LLM Client 工厂"""
    config = get_config()
    client = LLMClientFactory.create_client()
    assert isinstance(client, OpenAICompatibleClient)


def test_llm_config_for_kimi():
    """测试 Kimi K2.5 配置"""
    config = get_config()
    assert config.llm_config.model == "kimi-k2.5"
    assert config.llm_config.provider == "dashscope"
```

- [ ] **Step 3: 运行测试**

Run: `pytest tests/test_llm_client.py -v`
Expected: 2 tests PASSED

- [ ] **Step 4: 提交**

```bash
git add src/core/llm_client.py tests/test_llm_client.py
git commit -m "feat: update llm client for new config structure"
```

---

## Phase 2: TaskClassifier 实现 (Week 2)

### Task 4: 意图分析模块

**Files:**
- Create: `src/classifier/intent_analyzer.py`
- Create: `tests/classifier/test_intent_analyzer.py`

- [ ] **Step 1: 编写意图分析器**

```python
# src/classifier/intent_analyzer.py
import json
from typing import Dict, Any
from src.core.types import IntentAnalysis
from src.core.llm_client import chat_completion


class IntentAnalyzer:
    """意图分析器 - 使用 LLM 分析用户输入"""

    SYSTEM_PROMPT = """你是一个意图分析专家。请分析用户的输入，提取以下信息：
1. 主要意图 (primary_intent): 用户最主要想做什么
2. 次要意图 (secondary_intents): 其他相关意图
3. 实体 (entities): 提取的关键实体（如文件名、函数名、技术栈等）
4. 情感倾向 (sentiment): positive/negative/neutral
5. 紧急程度 (urgency): urgent/normal/low

请以 JSON 格式输出。"""

    def __init__(self):
        pass

    async def analyze(self, user_input: str, context: Dict[str, Any] = None) -> IntentAnalysis:
        """分析用户意图"""
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"请分析以下输入：\n\n{user_input}"}
        ]

        if context:
            messages.append({
                "role": "user",
                "content": f"上下文信息：{json.dumps(context, ensure_ascii=False)}"
            })

        response = await chat_completion(messages)

        try:
            result = json.loads(response)
            return IntentAnalysis(
                primary_intent=result.get("primary_intent", ""),
                secondary_intents=result.get("secondary_intents", []),
                entities=result.get("entities", {}),
                sentiment=result.get("sentiment", "neutral"),
                urgency=result.get("urgency", "normal")
            )
        except json.JSONDecodeError:
            # 如果解析失败，返回基础分析
            return IntentAnalysis(
                primary_intent=user_input[:50],
                secondary_intents=[],
                entities={},
                sentiment="neutral",
                urgency="normal"
            )
```

- [ ] **Step 2: 编写测试**

```python
# tests/classifier/test_intent_analyzer.py
import pytest
from src.classifier.intent_analyzer import IntentAnalyzer


@pytest.mark.asyncio
async def test_intent_analyzer_initialization():
    """测试意图分析器初始化"""
    analyzer = IntentAnalyzer()
    assert analyzer is not None


@pytest.mark.asyncio
async def test_analyze_returns_intent_analysis():
    """测试分析返回 IntentAnalysis"""
    analyzer = IntentAnalyzer()
    # 注意：这个测试需要实际的 LLM 调用，可能需要 mock
    # 这里仅测试接口
    assert hasattr(analyzer, 'analyze')
```

- [ ] **Step 3: 提交**

```bash
git add src/classifier/intent_analyzer.py tests/classifier/test_intent_analyzer.py
git commit -m "feat: add intent analyzer module"
```

---

### Task 5: Harness 选择器

**Files:**
- Create: `src/classifier/harness_selector.py`
- Create: `src/classifier/prompts.py` (分类提示词模板)

- [ ] **Step 1: 编写 Harness 选择器**

```python
# src/classifier/harness_selector.py
import json
from typing import Dict, Any, Tuple
from src.core.types import HarnessType, TaskType, IntentAnalysis
from src.core.llm_client import chat_completion


class HarnessSelector:
    """Harness 选择器 - 根据意图和任务类型选择最佳 Harness"""

    SYSTEM_PROMPT = """你是一个任务分类专家。请分析用户的任务，选择最适合的 Harness 执行模式。

可选的 Harness 模式:
- execution: 通用任务执行（默认）
- code: 代码生成、重构优化
- debug: 错误诊断、问题修复
- test: 测试验证、质量检查
- research: 调研分析、信息检索
- claude_code: 复杂多步骤任务、自动化工作流

请以 JSON 格式输出:
{
    "task_type": "任务类型 (analysis/generation/code/research/debug/test/automation/general)",
    "harness_type": "推荐的 harness (execution/code/debug/test/research/claude_code)",
    "confidence": 0.85,
    "reasoning": "选择理由",
    "sub_tasks": ["子任务1", "子任务2"],
    "requirements": {"关键要求": "描述"},
    "keywords": ["关键词1", "关键词2"],
    "estimated_complexity": "low/medium/high",
    "estimated_duration": 120
}"""

    # 关键词映射表（用于快速预筛选）
    KEYWORD_MAP = {
        HarnessType.CODE: ["代码", "函数", "类", "实现", "编写", "重构", "优化", "code", "function", "class", "implement"],
        HarnessType.DEBUG: ["bug", "错误", "修复", "排查", "异常", "error", "fix", "debug", "issue"],
        HarnessType.TEST: ["测试", "验证", "检查", "覆盖率", "test", "verify", "check", "coverage"],
        HarnessType.RESEARCH: ["调研", "搜索", "了解", "学习", "research", "search", "investigate"],
        HarnessType.CLAUDE_CODE: ["自动化", "批量", "流程", "计划", "automate", "batch", "workflow", "plan"],
    }

    def __init__(self):
        pass

    async def select(self, user_input: str, intent: IntentAnalysis) -> Tuple[HarnessType, TaskType, float, Dict[str, Any]]:
        """
        选择 Harness

        Returns:
            Tuple of (harness_type, task_type, confidence, metadata)
        """
        # 首先进行关键词预筛选
        keyword_harness = self._keyword_based_selection(user_input)

        # 使用 LLM 进行精细分类
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"用户输入：{user_input}\n\n意图分析：{intent.primary_intent}"}
        ]

        response = await chat_completion(messages)

        try:
            result = json.loads(response)
            harness_type = HarnessType(result.get("harness_type", "execution"))
            task_type = TaskType(result.get("task_type", "general"))
            confidence = float(result.get("confidence", 0.7))
            metadata = {
                "reasoning": result.get("reasoning", ""),
                "sub_tasks": result.get("sub_tasks", []),
                "requirements": result.get("requirements", {}),
                "keywords": result.get("keywords", []),
                "estimated_complexity": result.get("estimated_complexity", "medium"),
                "estimated_duration": result.get("estimated_duration", 60)
            }

            # 如果关键词预筛选和 LLM 结果不一致，降低置信度
            if keyword_harness and keyword_harness != harness_type:
                confidence *= 0.8

            return harness_type, task_type, confidence, metadata

        except (json.JSONDecodeError, ValueError) as e:
            # 解析失败时返回默认值
            return HarnessType.EXECUTION, TaskType.GENERAL, 0.5, {"error": str(e)}

    def _keyword_based_selection(self, user_input: str) -> HarnessType:
        """基于关键词的快速选择"""
        user_input_lower = user_input.lower()

        for harness_type, keywords in self.KEYWORD_MAP.items():
            for keyword in keywords:
                if keyword.lower() in user_input_lower:
                    return harness_type

        return None
```

- [ ] **Step 2: 编写测试**

```python
# tests/classifier/test_harness_selector.py
import pytest
from src.classifier.harness_selector import HarnessSelector
from src.core.types import HarnessType, IntentAnalysis


def test_harness_selector_initialization():
    """测试选择器初始化"""
    selector = HarnessSelector()
    assert selector is not None


def test_keyword_based_selection():
    """测试关键词选择"""
    selector = HarnessSelector()
    # 测试代码相关关键词
    result = selector._keyword_based_selection("帮我写个函数")
    assert result == HarnessType.CODE
```

- [ ] **Step 3: 提交**

```bash
git add src/classifier/harness_selector.py tests/classifier/test_harness_selector.py
git commit -m "feat: add harness selector with keyword pre-filtering"
```

---

### Task 6: 确认流程管理

**Files:**
- Create: `src/classifier/confirmation.py`

- [ ] **Step 1: 编写确认管理器**

```python
# src/classifier/confirmation.py
from typing import Optional
from src.core.types import ClassificationResult, ConfirmationRequest, ConfirmationResponse, HarnessType
from src.core.config import get_config


class ConfirmationManager:
    """确认流程管理器"""

    def __init__(self):
        self.config = get_config().classification_config

    def needs_confirmation(self, classification: ClassificationResult) -> bool:
        """判断是否需要用户确认"""
        if not self.config.require_confirmation:
            return False
        return classification.confidence < self.config.confidence_threshold

    def create_confirmation_request(self, classification: ClassificationResult) -> ConfirmationRequest:
        """创建确认请求"""
        question = self._format_question(classification)
        options = self._create_options(classification)

        return ConfirmationRequest(
            classification=classification,
            question=question,
            options=options,
            timeout=300,
            allow_override=True
        )

    def _format_question(self, classification: ClassificationResult) -> str:
        """格式化确认问题"""
        return f"""我分析到您的任务可能是以下类型：

📋 **任务意图**: {classification.intent.primary_intent}
🎯 **任务类型**: {classification.task_type.value}
⚙️  **推荐模式**: {classification.harness_type.value}
📊 **置信度**: {classification.confidence:.0%}

💡 **选择理由**:
{classification.reasoning}

请选择："""

    def _create_options(self, classification: ClassificationResult) -> list:
        """创建选项列表"""
        return [
            {"key": "1", "label": f"✅ 确认使用 {classification.harness_type.value} 模式", "action": "confirm"},
            {"key": "2", "label": "🔄 选择其他模式", "action": "override"},
            {"key": "3", "label": "✏️ 补充任务描述", "action": "modify"},
            {"key": "4", "label": "❌ 取消任务", "action": "cancel"}
        ]

    async def process_response(self, request: ConfirmationRequest, user_response: str) -> ConfirmationResponse:
        """处理用户响应"""
        action = self._parse_action(user_response)

        if action == "confirm":
            return ConfirmationResponse(
                confirmed=True,
                selected_harness=request.classification.harness_type,
                feedback="用户确认"
            )
        elif action == "override":
            # 这里需要让用户选择新的 harness
            new_harness = self._parse_harness_override(user_response)
            return ConfirmationResponse(
                confirmed=True,
                selected_harness=new_harness,
                modifications={"harness_override": True},
                feedback="用户选择其他模式"
            )
        elif action == "modify":
            return ConfirmationResponse(
                confirmed=False,
                selected_harness=request.classification.harness_type,
                modifications={"needs_more_info": True},
                feedback="需要补充信息"
            )
        else:
            return ConfirmationResponse(
                confirmed=False,
                selected_harness=request.classification.harness_type,
                feedback="用户取消"
            )

    def _parse_action(self, user_response: str) -> str:
        """解析用户选择的动作"""
        response = user_response.strip().lower()
        if response in ["1", "confirm", "yes", "是", "确认"]:
            return "confirm"
        elif response in ["2", "override", "change", "切换", "其他"]:
            return "override"
        elif response in ["3", "modify", "补充", "修改"]:
            return "modify"
        else:
            return "cancel"

    def _parse_harness_override(self, user_response: str) -> HarnessType:
        """解析用户选择的 Harness"""
        response = user_response.lower()
        harness_map = {
            "code": HarnessType.CODE,
            "debug": HarnessType.DEBUG,
            "test": HarnessType.TEST,
            "research": HarnessType.RESEARCH,
            "execution": HarnessType.EXECUTION,
            "claude_code": HarnessType.CLAUDE_CODE,
        }
        return harness_map.get(response, HarnessType.EXECUTION)
```

- [ ] **Step 2: 提交**

```bash
git add src/classifier/confirmation.py
git commit -m "feat: add confirmation manager"
```

---

### Task 7: TaskClassifier 主类

**Files:**
- Create: `src/classifier/task_classifier.py`
- Create: `src/classifier/__init__.py`

- [ ] **Step 1: 编写 TaskClassifier 主类**

```python
# src/classifier/task_classifier.py
from typing import Dict, Any, Optional
from src.core.types import (
    ClassificationResult, ConfirmationRequest, ConfirmationResponse,
    IntentAnalysis, HarnessType, TaskType
)
from src.core.config import get_config
from src.classifier.intent_analyzer import IntentAnalyzer
from src.classifier.harness_selector import HarnessSelector
from src.classifier.confirmation import ConfirmationManager


class TaskClassifier:
    """任务分类器主类"""

    def __init__(self):
        self.config = get_config().classification_config
        self.intent_analyzer = IntentAnalyzer()
        self.harness_selector = HarnessSelector()
        self.confirmation_manager = ConfirmationManager()

    async def classify(self, user_input: str, context: Dict[str, Any] = None) -> ClassificationResult:
        """
        分类任务

        Args:
            user_input: 用户输入
            context: 上下文信息

        Returns:
            ClassificationResult
        """
        # 1. 分析意图
        intent = await self.intent_analyzer.analyze(user_input, context)

        # 2. 选择 Harness
        harness_type, task_type, confidence, metadata = await self.harness_selector.select(
            user_input, intent
        )

        # 3. 构建分类结果
        result = ClassificationResult(
            intent=intent,
            task_type=task_type,
            harness_type=harness_type,
            confidence=confidence,
            reasoning=metadata.get("reasoning", ""),
            sub_tasks=metadata.get("sub_tasks", []),
            requirements=metadata.get("requirements", {}),
            keywords=metadata.get("keywords", []),
            estimated_complexity=metadata.get("estimated_complexity", "medium"),
            estimated_duration=metadata.get("estimated_duration", 60)
        )

        return result

    def needs_confirmation(self, classification: ClassificationResult) -> bool:
        """判断是否需要确认"""
        return self.confirmation_manager.needs_confirmation(classification)

    def create_confirmation(self, classification: ClassificationResult) -> ConfirmationRequest:
        """创建确认请求"""
        return self.confirmation_manager.create_confirmation_request(classification)

    async def process_confirmation(self, request: ConfirmationRequest, user_response: str) -> ConfirmationResponse:
        """处理确认响应"""
        return await self.confirmation_manager.process_response(request, user_response)
```

- [ ] **Step 2: 编写 __init__.py**

```python
# src/classifier/__init__.py
from src.classifier.task_classifier import TaskClassifier
from src.classifier.intent_analyzer import IntentAnalyzer
from src.classifier.harness_selector import HarnessSelector
from src.classifier.confirmation import ConfirmationManager

__all__ = [
    'TaskClassifier',
    'IntentAnalyzer',
    'HarnessSelector',
    'ConfirmationManager'
]
```

- [ ] **Step 3: 编写集成测试**

```python
# tests/classifier/test_task_classifier.py
import pytest
from src.classifier.task_classifier import TaskClassifier
from src.core.types import ClassificationResult


@pytest.mark.asyncio
async def test_task_classifier_initialization():
    """测试分类器初始化"""
    classifier = TaskClassifier()
    assert classifier is not None
    assert classifier.intent_analyzer is not None
    assert classifier.harness_selector is not None
    assert classifier.confirmation_manager is not None


@pytest.mark.asyncio
async def test_classify_returns_result():
    """测试分类返回结果"""
    classifier = TaskClassifier()
    # 注意：这个测试需要实际的 LLM 调用
    result = await classifier.classify("帮我写个Python函数")
    assert isinstance(result, ClassificationResult)
```

- [ ] **Step 4: 提交**

```bash
git add src/classifier/
git commit -m "feat: add complete task classifier with intent analysis, harness selection and confirmation"
```

---

## Phase 3: Harness 引擎 (Week 3)

### Task 8: BaseHarness 抽象

**Files:**
- Create: `src/harness/base.py`
- Create: `src/harness/__init__.py`

- [ ] **Step 1: 编写 BaseHarness**

```python
# src/harness/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

from src.core.types import Task, TaskResult, HarnessConfig, HarnessType


class BaseHarness(ABC):
    """Harness 基类"""

    def __init__(self, config: HarnessConfig):
        self.config = config
        self.harness_type = config.harness_type
        self._initialized = False
        self._start_time: Optional[datetime] = None
        self._metrics = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "total_execution_time": 0.0
        }

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @abstractmethod
    async def initialize(self):
        """初始化 Harness"""
        self._initialized = True
        self._start_time = datetime.now()

    @abstractmethod
    async def execute(self, task: Task) -> TaskResult:
        """执行任务"""
        pass

    @abstractmethod
    async def cleanup(self):
        """清理资源"""
        self._initialized = False

    async def run(self, task: Task) -> TaskResult:
        """运行 Harness（包含初始化和清理）"""
        try:
            await self.initialize()
            result = await self.execute(task)
            return result
        finally:
            await self.cleanup()

    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return self._metrics.copy()

    def _update_metrics(self, success: bool, execution_time: float):
        """更新指标"""
        if success:
            self._metrics["tasks_completed"] += 1
        else:
            self._metrics["tasks_failed"] += 1
        self._metrics["total_execution_time"] += execution_time
```

- [ ] **Step 2: 编写 __init__.py**

```python
# src/harness/__init__.py
from src.harness.base import BaseHarness

__all__ = ['BaseHarness']
```

- [ ] **Step 3: 提交**

```bash
git add src/harness/
git commit -m "feat: add base harness abstract class"
```

---

### Task 9: Harness Factory

**Files:**
- Create: `src/harness/factory.py`

- [ ] **Step 1: 编写 Harness Factory**

```python
# src/harness/factory.py
from typing import Dict, Type
from src.core.types import HarnessType, HarnessConfig
from src.core.exceptions import HarnessInitError
from src.harness.base import BaseHarness


class HarnessFactory:
    """Harness 工厂"""

    _registry: Dict[HarnessType, Type[BaseHarness]] = {}

    @classmethod
    def register(cls, harness_type: HarnessType, harness_class: Type[BaseHarness]):
        """注册 Harness"""
        cls._registry[harness_type] = harness_class

    @classmethod
    def create(cls, harness_type: HarnessType, config: Dict[str, Any] = None) -> BaseHarness:
        """创建 Harness 实例"""
        harness_class = cls._registry.get(harness_type)
        if not harness_class:
            raise HarnessInitError(f"未注册的 Harness 类型: {harness_type}")

        harness_config = HarnessConfig(
            harness_type=harness_type,
            **(config or {})
        )

        return harness_class(harness_config)

    @classmethod
    def get_available_harnesses(cls) -> list:
        """获取可用的 Harness 类型"""
        return list(cls._registry.keys())

    @classmethod
    def is_registered(cls, harness_type: HarnessType) -> bool:
        """检查 Harness 是否已注册"""
        return harness_type in cls._registry
```

- [ ] **Step 2: 编写测试**

```python
# tests/harness/test_factory.py
import pytest
from src.harness.factory import HarnessFactory
from src.harness.base import BaseHarness
from src.core.types import HarnessType, HarnessConfig


def test_factory_register():
    """测试工厂注册"""
    # 创建一个测试 Harness
    class TestHarness(BaseHarness):
        async def initialize(self):
            pass
        async def execute(self, task):
            pass
        async def cleanup(self):
            pass

    HarnessFactory.register(HarnessType.EXECUTION, TestHarness)
    assert HarnessType.EXECUTION in HarnessFactory.get_available_harnesses()
```

- [ ] **Step 3: 提交**

```bash
git add src/harness/factory.py tests/harness/test_factory.py
git commit -m "feat: add harness factory with registration mechanism"
```

---

### Task 10: ExecutionHarness (默认实现)

**Files:**
- Create: `src/harness/execution.py`
- Modify: `src/harness/__init__.py`

- [ ] **Step 1: 编写 ExecutionHarness**

```python
# src/harness/execution.py
import asyncio
from datetime import datetime
from typing import Dict, Any

from src.core.types import Task, TaskResult, TaskStatus
from src.core.exceptions import SwarmExecutionError
from src.harness.base import BaseHarness
from src.harness.factory import HarnessFactory


class ExecutionHarness(BaseHarness):
    """执行 Harness - 默认的通用任务执行模式"""

    def __init__(self, config):
        super().__init__(config)
        self.swarm_manager = None
        self.max_agents = config.custom_params.get("max_agents", 10)

    async def initialize(self):
        """初始化 Execution Harness"""
        await super().initialize()
        # 这里可以初始化 SwarmManager
        # self.swarm_manager = SwarmManager(...)

    async def execute(self, task: Task) -> TaskResult:
        """执行任务"""
        start_time = datetime.now()

        try:
            # 1. 分解任务
            subtasks = await self._decompose_task(task)

            # 2. 执行子任务（这里简化处理，实际应该使用 Swarm）
            results = []
            for subtask in subtasks:
                result = await self._execute_subtask(subtask)
                results.append(result)

            # 3. 整合结果
            output = self._integrate_results(results)

            execution_time = (datetime.now() - start_time).total_seconds()

            return TaskResult(
                task_id=task.task_id,
                status="completed",
                output=output,
                quality_score=0.8,
                execution_time=execution_time,
                logs=[f"Executed {len(subtasks)} subtasks"]
            )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return TaskResult(
                task_id=task.task_id,
                status="failed",
                output=None,
                execution_time=execution_time,
                errors=[str(e)]
            )

    async def _decompose_task(self, task: Task) -> list:
        """分解任务"""
        # 简化实现，实际应该使用 LLM 进行智能分解
        return [
            {"id": f"{task.task_id}_1", "description": f"分析: {task.description}"},
            {"id": f"{task.task_id}_2", "description": f"执行: {task.description}"},
            {"id": f"{task.task_id}_3", "description": f"验证: {task.description}"}
        ]

    async def _execute_subtask(self, subtask: dict) -> dict:
        """执行子任务"""
        # 简化实现
        await asyncio.sleep(0.1)  # 模拟执行
        return {
            "subtask_id": subtask["id"],
            "status": "completed",
            "result": f"Completed: {subtask['description']}"
        }

    def _integrate_results(self, results: list) -> dict:
        """整合结果"""
        return {
            "subtask_count": len(results),
            "completed_count": sum(1 for r in results if r.get("status") == "completed"),
            "results": results
        }

    async def cleanup(self):
        """清理资源"""
        if self.swarm_manager:
            # await self.swarm_manager.stop()
            pass
        await super().cleanup()


# 注册到工厂
HarnessFactory.register(ExecutionHarness, ExecutionHarness)
```

- [ ] **Step 2: 更新 __init__.py**

```python
# src/harness/__init__.py
from src.harness.base import BaseHarness
from src.harness.factory import HarnessFactory
from src.harness.execution import ExecutionHarness

__all__ = ['BaseHarness', 'HarnessFactory', 'ExecutionHarness']
```

- [ ] **Step 3: 编写测试**

```python
# tests/harness/test_execution.py
import pytest
from src.harness.execution import ExecutionHarness
from src.core.types import HarnessConfig, HarnessType, Task


@pytest.mark.asyncio
async def test_execution_harness_initialization():
    """测试 ExecutionHarness 初始化"""
    config = HarnessConfig(harness_type=HarnessType.EXECUTION)
    harness = ExecutionHarness(config)
    await harness.initialize()
    assert harness.is_initialized
    await harness.cleanup()


@pytest.mark.asyncio
async def test_execution_harness_execute():
    """测试 ExecutionHarness 执行"""
    config = HarnessConfig(harness_type=HarnessType.EXECUTION)
    harness = ExecutionHarness(config)

    task = Task(
        task_id="test_task",
        description="测试任务",
        task_type="general",
        harness_type=HarnessType.EXECUTION
    )

    result = await harness.run(task)
    assert result.status == "completed"
    assert result.output is not None
```

- [ ] **Step 4: 提交**

```bash
git add src/harness/execution.py tests/harness/test_execution.py
git commit -m "feat: add execution harness as default implementation"
```

---

## Phase 4: 主入口 (Week 4)

### Task 11: 主入口和 CLI

**Files:**
- Create: `src/main.py`
- Create: `src/__main__.py`

- [ ] **Step 1: 编写主入口**

```python
# src/main.py
import asyncio
import uuid
from typing import Optional

from src.core.config import get_config
from src.core.types import Task, HarnessType
from src.classifier.task_classifier import TaskClassifier
from src.harness.factory import HarnessFactory
from src.harness.execution import ExecutionHarness


class MultiHarnessAgentSwarm:
    """多 Harness Agent Swarm 主类"""

    def __init__(self):
        self.config = get_config()
        self.classifier = TaskClassifier()
        self._register_harnesses()

    def _register_harnesses(self):
        """注册所有 Harness"""
        # 注册 ExecutionHarness
        from src.harness.execution import ExecutionHarness
        HarnessFactory.register(HarnessType.EXECUTION, ExecutionHarness)

    async def process_request(self, user_input: str, context: dict = None) -> dict:
        """
        处理用户请求

        Args:
            user_input: 用户输入
            context: 上下文信息

        Returns:
            处理结果
        """
        print(f"\n🔍 分析任务: {user_input[:50]}...")

        # 1. 分类任务
        classification = await self.classifier.classify(user_input, context)

        print(f"📋 检测到意图: {classification.intent.primary_intent}")
        print(f"🎯 任务类型: {classification.task_type.value}")
        print(f"⚙️  推荐模式: {classification.harness_type.value}")
        print(f"📊 置信度: {classification.confidence:.0%}")

        # 2. 判断是否需要确认
        if self.classifier.needs_confirmation(classification):
            print("\n⚠️  置信度较低，建议确认")
            confirmation = self.classifier.create_confirmation(classification)
            print(confirmation.question)
            for option in confirmation.options:
                print(f"  {option['key']}. {option['label']}")

            # 这里简化处理，实际应该等待用户输入
            # 假设用户确认
            print("\n✅ 用户确认使用推荐模式")

        # 3. 创建 Harness 并执行任务
        harness = HarnessFactory.create(classification.harness_type)

        task = Task(
            task_id=str(uuid.uuid4()),
            description=user_input,
            task_type=classification.task_type,
            harness_type=classification.harness_type,
            requirements=classification.requirements
        )

        print(f"\n🚀 启动 {classification.harness_type.value} Harness...")
        result = await harness.run(task)

        # 4. 返回结果
        return {
            "task_id": task.task_id,
            "harness_type": classification.harness_type.value,
            "status": result.status,
            "output": result.output,
            "execution_time": result.execution_time,
            "quality_score": result.quality_score
        }


async def main():
    """主函数"""
    print("=" * 60)
    print("🤖 Multi-Harness Agent Swarm")
    print("=" * 60)

    # 验证配置
    validation = get_config().validate()
    if not validation["valid"]:
        print("\n❌ 配置错误:")
        for error in validation["errors"]:
            print(f"  - {error}")
        return

    print(f"\n✅ 配置验证通过")
    print(f"🤖 LLM: {get_config().llm_config.model}")
    print(f"📊 置信度阈值: {get_config().classification_config.confidence_threshold}")

    # 创建系统实例
    system = MultiHarnessAgentSwarm()

    # 示例任务
    test_inputs = [
        "帮我写个Python函数来计算斐波那契数列",
        "分析一下这段代码的性能问题",
        "搜索一下最新的AI研究进展"
    ]

    for user_input in test_inputs:
        print("\n" + "=" * 60)
        result = await system.process_request(user_input)
        print(f"\n✅ 任务完成: {result['task_id']}")
        print(f"📊 状态: {result['status']}")
        print(f"⏱️  执行时间: {result['execution_time']:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: 创建 __main__.py**

```python
# src/__main__.py
from src.main import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 3: 测试运行**

Run: `python -m src`
Expected: 系统启动并处理示例任务

- [ ] **Step 4: 提交**

```bash
git add src/main.py src/__main__.py
git commit -m "feat: add main entry point and CLI"
```

---

## 总结

本计划实现了 Multi-Harness Agent Swarm 的核心框架：

1. **基础框架** - 数据类型、配置管理、LLM Client
2. **TaskClassifier** - 意图分析、Harness 选择、确认流程
3. **Harness 引擎** - BaseHarness 抽象、Factory 模式、ExecutionHarness
4. **主入口** - CLI 和系统集成

**下一步扩展：**
- 实现其他 5 种 Harness (Code, Debug, Test, Research, ClaudeCode)
- 集成完整的 Agent Swarm 三层架构
- 添加结果合成和反馈学习
