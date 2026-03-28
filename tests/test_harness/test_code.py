"""
CodeHarness 测试

测试 CodeHarness 的各项功能，包括：
1. 代码生成
2. 代码重构
3. 代码优化
4. 代码审查
5. 任务类型分析
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from src.harness.code import CodeHarness
from src.harness.factory import HarnessFactory
from src.core.types import (
    Task, TaskResult, HarnessConfig, HarnessType, TaskStatus, TaskType
)


class TestCodeHarness:
    """CodeHarness 测试类"""

    def setup_method(self):
        """每个测试前清理注册表并创建测试实例"""
        HarnessFactory.clear_registry()

        # 注册 CodeHarness
        HarnessFactory.register(HarnessType.CODE, CodeHarness)

        # 创建测试配置
        self.config = HarnessConfig(
            harness_type=HarnessType.CODE,
            custom_params={
                "language": "python",
                "style_guide": "pep8",
                "enable_monitoring": False
            }
        )

        # 创建 harness 实例
        self.harness = CodeHarness(self.config)

    def teardown_method(self):
        """每个测试后清理"""
        HarnessFactory.clear_registry()

    @pytest.mark.asyncio
    async def test_initialize(self):
        """测试初始化"""
        await self.harness.initialize()
        assert self.harness.is_initialized()
        assert self.harness.language == "python"
        assert self.harness.style_guide == "pep8"
        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_analyze_code_task_generate(self):
        """测试代码生成任务类型识别"""
        await self.harness.initialize()

        # 测试生成相关关键词
        assert self.harness._analyze_code_task("生成一个函数") == "generate"
        assert self.harness._analyze_code_task("Create a class") == "generate"
        assert self.harness._analyze_code_task("Write code to") == "generate"
        assert self.harness._analyze_code_task("实现一个排序算法") == "generate"
        assert self.harness._analyze_code_task("Generate a module") == "generate"

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_analyze_code_task_refactor(self):
        """测试代码重构任务类型识别"""
        await self.harness.initialize()

        # 测试重构相关关键词
        assert self.harness._analyze_code_task("重构这段代码") == "refactor"
        assert self.harness._analyze_code_task("Refactor this function") == "refactor"
        assert self.harness._analyze_code_task("Restructure the code") == "refactor"

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_analyze_code_task_optimize(self):
        """测试代码优化任务类型识别"""
        await self.harness.initialize()

        # 测试优化相关关键词
        assert self.harness._analyze_code_task("优化这个算法") == "optimize"
        assert self.harness._analyze_code_task("Optimize the performance") == "optimize"
        assert self.harness._analyze_code_task("Improve efficiency") == "optimize"

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_analyze_code_task_review(self):
        """测试代码审查任务类型识别"""
        await self.harness.initialize()

        # 测试审查相关关键词
        assert self.harness._analyze_code_task("审查这段代码") == "review"
        assert self.harness._analyze_code_task("Review this code") == "review"
        assert self.harness._analyze_code_task("Code review needed") == "review"
        assert self.harness._analyze_code_task("Analyze the code quality") == "review"

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_analyze_code_task_general(self):
        """测试通用代码帮助任务类型识别"""
        await self.harness.initialize()

        # 测试无法识别的任务类型
        assert self.harness._analyze_code_task("How to use Python") == "general"
        assert self.harness._analyze_code_task("Explain this syntax") == "general"

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_extract_code_from_task(self):
        """测试从任务中提取代码"""
        await self.harness.initialize()

        # 测试从 requirements 提取
        task = Task(
            description="Refactor this code",
            requirements={"code": "def foo(): pass"}
        )
        assert self.harness._extract_code_from_task(task) == "def foo(): pass"

        # 测试从 source_code 提取
        task = Task(
            description="Optimize this",
            requirements={"source_code": "class Bar: pass"}
        )
        assert self.harness._extract_code_from_task(task) == "class Bar: pass"

        # 测试从 metadata 提取
        task = Task(
            description="Review this",
            metadata={"code": "x = 1 + 2"}
        )
        assert self.harness._extract_code_from_task(task) == "x = 1 + 2"

        # 测试无代码的情况
        task = Task(description="Generate a function")
        assert self.harness._extract_code_from_task(task) is None

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_extract_language_from_task(self):
        """测试从任务中提取语言"""
        await self.harness.initialize()

        # 测试从 requirements 提取
        task = Task(
            description="Generate code",
            requirements={"language": "javascript"}
        )
        assert self.harness._extract_language_from_task(task) == "javascript"

        # 测试从 metadata 提取
        task = Task(
            description="Refactor code",
            metadata={"language": "typescript"}
        )
        assert self.harness._extract_language_from_task(task) == "typescript"

        # 测试使用默认值
        task = Task(description="Optimize code")
        assert self.harness._extract_language_from_task(task) == "python"

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_generate_code_without_code(self):
        """测试没有代码时的重构任务应该失败"""
        await self.harness.initialize()

        task = Task(
            description="重构这段代码",
            task_type=TaskType.CODE,
            requirements={}  # 没有提供代码
        )

        result = await self.harness._refactor_code(task)

        assert result.status == TaskStatus.FAILED.value
        assert "No code provided" in result.errors[0]

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_optimize_code_without_code(self):
        """测试没有代码时的优化任务应该失败"""
        await self.harness.initialize()

        task = Task(
            description="优化这个函数",
            task_type=TaskType.CODE,
            requirements={}  # 没有提供代码
        )

        result = await self.harness._optimize_code(task)

        assert result.status == TaskStatus.FAILED.value
        assert "No code provided" in result.errors[0]

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_review_code_without_code(self):
        """测试没有代码时的审查任务应该失败"""
        await self.harness.initialize()

        task = Task(
            description="审查这段代码",
            task_type=TaskType.CODE,
            requirements={}  # 没有提供代码
        )

        result = await self.harness._review_code(task)

        assert result.status == TaskStatus.FAILED.value
        assert "No code provided" in result.errors[0]

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_factory_registration(self):
        """测试工厂注册"""
        # 确保 CodeHarness 已注册
        assert HarnessFactory.is_registered(HarnessType.CODE)

        # 使用工厂创建实例
        harness = HarnessFactory.create(HarnessType.CODE)
        assert isinstance(harness, CodeHarness)

    @pytest.mark.asyncio
    async def test_factory_create_with_config(self):
        """测试工厂创建带配置的实例"""
        config = {
            "custom_params": {
                "language": "javascript",
                "style_guide": "airbnb",
                "enable_monitoring": False
            }
        }

        harness = HarnessFactory.create(HarnessType.CODE, config=config)
        assert isinstance(harness, CodeHarness)
        assert harness.language == "javascript"
        assert harness.style_guide == "airbnb"

    @pytest.mark.asyncio
    async def test_harness_config_defaults(self):
        """测试 Harness 配置默认值"""
        config = HarnessConfig(harness_type=HarnessType.CODE)
        harness = CodeHarness(config)

        assert harness.language == "python"
        assert harness.style_guide == "pep8"
        assert harness.enable_monitoring is True

    @pytest.mark.asyncio
    async def test_execute_generate_task(self):
        """测试执行生成任务"""
        await self.harness.initialize()

        task = Task(
            description="生成一个计算斐波那契数列的函数",
            task_type=TaskType.CODE
        )

        # Mock chat_completion
        mock_response = "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)"

        with patch('src.harness.code.chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = mock_response

            result = await self.harness.execute(task)

            assert result.status == TaskStatus.COMPLETED.value
            assert result.output["language"] == "python"
            assert result.output["task_type"] == "code_generation"
            assert mock_response in result.output["code"]
            assert result.metadata["task_subtype"] == "generate"

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_execute_refactor_task(self):
        """测试执行重构任务"""
        await self.harness.initialize()

        task = Task(
            description="重构这段代码",
            task_type=TaskType.CODE,
            requirements={
                "code": "def calc(a,b): return a+b"
            }
        )

        mock_response = "def calculate_sum(a: int, b: int) -> int:\n    \"\"\"计算两个数的和\"\"\"\n    return a + b"

        with patch('src.harness.code.chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = mock_response

            result = await self.harness.execute(task)

            assert result.status == TaskStatus.COMPLETED.value
            assert result.output["language"] == "python"
            assert result.output["task_type"] == "code_refactoring"
            assert result.metadata["task_subtype"] == "refactor"

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_execute_optimize_task(self):
        """测试执行优化任务"""
        await self.harness.initialize()

        task = Task(
            description="优化这个函数的性能",
            task_type=TaskType.CODE,
            requirements={
                "code": "def find_max(arr):\n    max_val = arr[0]\n    for i in range(len(arr)):\n        if arr[i] > max_val:\n            max_val = arr[i]\n    return max_val"
            }
        )

        mock_response = "def find_max(arr):\n    return max(arr)  # 使用内置函数"

        with patch('src.harness.code.chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = mock_response

            result = await self.harness.execute(task)

            assert result.status == TaskStatus.COMPLETED.value
            assert result.output["task_type"] == "code_optimization"
            assert result.metadata["task_subtype"] == "optimize"

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_execute_review_task(self):
        """测试执行审查任务"""
        await self.harness.initialize()

        task = Task(
            description="审查这段代码的质量",
            task_type=TaskType.CODE,
            requirements={
                "code": "def divide(a, b): return a / b"
            }
        )

        mock_response = """## 代码审查报告

### 代码质量评分: 5/10

### 主要问题:
1. 缺少错误处理（除以零）
2. 缺少文档字符串
3. 缺少类型注解

### 改进建议:
- 添加 try-except 处理 ZeroDivisionError
- 添加函数文档
- 添加参数类型注解"""

        with patch('src.harness.code.chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = mock_response

            result = await self.harness.execute(task)

            assert result.status == TaskStatus.COMPLETED.value
            assert result.output["task_type"] == "code_review"
            assert result.metadata["task_subtype"] == "review"

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_execute_general_task(self):
        """测试执行通用帮助任务"""
        await self.harness.initialize()

        task = Task(
            description="解释 Python 中的装饰器是什么",
            task_type=TaskType.CODE
        )

        mock_response = "装饰器是 Python 中一种修改或增强函数或类行为的语法糖..."

        with patch('src.harness.code.chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = mock_response

            result = await self.harness.execute(task)

            assert result.status == TaskStatus.COMPLETED.value
            assert result.output["task_type"] == "code_help"
            assert result.metadata["task_subtype"] == "general"

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_execute_with_llm_error(self):
        """测试 LLM 调用失败时的处理"""
        await self.harness.initialize()

        task = Task(
            description="生成一个函数",
            task_type=TaskType.CODE
        )

        with patch('src.harness.code.chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_chat.side_effect = Exception("LLM API Error")

            result = await self.harness.execute(task)

            assert result.status == TaskStatus.FAILED.value
            assert "LLM API Error" in result.errors[0]

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_result_structure(self):
        """测试结果结构完整性"""
        await self.harness.initialize()

        task = Task(
            description="生成一个函数",
            task_type=TaskType.CODE
        )

        with patch('src.harness.code.chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = "def test(): pass"

            result = await self.harness.execute(task)

            # 验证 TaskResult 结构
            assert result.task_id == task.task_id
            assert result.status == TaskStatus.COMPLETED.value
            assert isinstance(result.output, dict)
            assert "code" in result.output or "response" in result.output
            assert isinstance(result.quality_score, float)
            assert isinstance(result.execution_time, float)
            assert isinstance(result.logs, list)
            assert isinstance(result.metadata, dict)
            assert result.metadata["harness_type"] == HarnessType.CODE.value

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """测试资源清理"""
        await self.harness.initialize()
        assert self.harness.is_initialized()

        await self.harness.cleanup()
        assert not self.harness.is_initialized()


class TestCodeHarnessMonitoring:
    """CodeHarness 监控功能测试"""

    @pytest.mark.asyncio
    async def test_monitoring_enabled(self):
        """测试启用监控"""
        HarnessFactory.clear_registry()
        HarnessFactory.register(HarnessType.CODE, CodeHarness)

        config = HarnessConfig(
            harness_type=HarnessType.CODE,
            custom_params={"enable_monitoring": True}
        )

        harness = CodeHarness(config)
        await harness.initialize()

        assert harness.task_monitor is not None

        await harness.cleanup()
        HarnessFactory.clear_registry()

    @pytest.mark.asyncio
    async def test_monitoring_disabled(self):
        """测试禁用监控"""
        HarnessFactory.clear_registry()
        HarnessFactory.register(HarnessType.CODE, CodeHarness)

        config = HarnessConfig(
            harness_type=HarnessType.CODE,
            custom_params={"enable_monitoring": False}
        )

        harness = CodeHarness(config)
        await harness.initialize()

        assert harness.task_monitor is None

        await harness.cleanup()
        HarnessFactory.clear_registry()
