"""
DebugHarness 测试

测试 DebugHarness 的各项功能，包括：
1. 错误信息提取
2. 错误诊断
3. 修复建议
4. 修复应用
5. 修复验证
"""
import pytest
from unittest.mock import patch, AsyncMock

from src.harness.debug import DebugHarness
from src.harness.factory import HarnessFactory
from src.core.types import (
    Task, TaskResult, HarnessConfig, HarnessType, TaskStatus, TaskType
)


class TestDebugHarness:
    """DebugHarness 测试类"""

    def setup_method(self):
        """每个测试前清理注册表并创建测试实例"""
        HarnessFactory.clear_registry()

        # 注册 DebugHarness
        HarnessFactory.register(HarnessType.DEBUG, DebugHarness)

        # 创建测试配置
        self.config = HarnessConfig(
            harness_type=HarnessType.DEBUG,
            custom_params={
                "max_iterations": 5,
                "auto_fix": True,
                "enable_monitoring": False
            }
        )

        # 创建 harness 实例
        self.harness = DebugHarness(self.config)

    def teardown_method(self):
        """每个测试后清理"""
        HarnessFactory.clear_registry()

    @pytest.mark.asyncio
    async def test_initialize(self):
        """测试初始化"""
        await self.harness.initialize()
        assert self.harness.is_initialized()
        assert self.harness.max_iterations == 5
        assert self.harness.auto_fix is True
        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_extract_error_info_from_requirements(self):
        """测试从 requirements 中提取错误信息"""
        await self.harness.initialize()

        task = Task(
            description="Debug this error",
            requirements={
                "error": "NameError: name 'x' is not defined",
                "stack_trace": "File 'test.py', line 10, in <module>",
                "code": "print(x)",
                "context": "Running main function",
                "language": "python"
            }
        )

        error_info = self.harness._extract_error_info(task)

        assert error_info["error_message"] == "NameError: name 'x' is not defined"
        assert error_info["stack_trace"] == "File 'test.py', line 10, in <module>"
        assert error_info["code"] == "print(x)"
        assert error_info["context"] == "Running main function"
        assert error_info["language"] == "python"

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_extract_error_info_from_metadata(self):
        """测试从 metadata 中提取错误信息"""
        await self.harness.initialize()

        task = Task(
            description="Debug this error",
            requirements={},
            metadata={
                "error": "TypeError: unsupported operand type",
                "code": "x = '5' + 10",
                "language": "python"
            }
        )

        error_info = self.harness._extract_error_info(task)

        assert error_info["error_message"] == "TypeError: unsupported operand type"
        assert error_info["code"] == "x = '5' + 10"
        assert error_info["language"] == "python"

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_extract_error_info_defaults(self):
        """测试提取错误信息默认值"""
        await self.harness.initialize()

        task = Task(description="Debug this error")

        error_info = self.harness._extract_error_info(task)

        assert error_info["error_message"] == ""
        assert error_info["stack_trace"] == ""
        assert error_info["code"] == ""
        assert error_info["context"] == ""
        assert error_info["language"] == "python"

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_extract_error_info_with_error_message_key(self):
        """测试使用 error_message 键提取错误信息"""
        await self.harness.initialize()

        task = Task(
            description="Debug this error",
            requirements={
                "error_message": "ValueError: invalid literal for int()"
            }
        )

        error_info = self.harness._extract_error_info(task)

        assert error_info["error_message"] == "ValueError: invalid literal for int()"

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_parse_error_type(self):
        """测试解析错误类型"""
        await self.harness.initialize()

        # 测试中文格式
        response1 = "错误类型：TypeError\n根本原因：..."
        assert self.harness._parse_error_type(response1) == "TypeError"

        # 测试英文格式
        response2 = "Error Type: ValueError\nRoot cause: ..."
        assert self.harness._parse_error_type(response2) == "ValueError"

        # 测试代码块格式
        response3 = "这是一个 `KeyError` 错误"
        assert self.harness._parse_error_type(response3) == "KeyError"

        # 测试无法识别的情况
        response4 = "这是一个未知错误"
        assert self.harness._parse_error_type(response4) == "UnknownError"

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_parse_location(self):
        """测试解析错误位置"""
        await self.harness.initialize()

        # 测试完整位置信息
        response1 = """
        文件：test.py
        行：42
        函数：calculate_sum
        """
        location1 = self.harness._parse_location(response1)
        assert location1["file"] == "test.py"
        assert location1["line"] == 42
        assert location1["function"] == "calculate_sum"

        # 测试英文格式
        response2 = """
        File: 'app.py'
        Line: 15
        Function: main
        """
        location2 = self.harness._parse_location(response2)
        assert location2["file"] == "app.py"
        assert location2["line"] == 15
        assert location2["function"] == "main"

        # 测试部分信息
        response3 = "在第 100 行发生错误"
        location3 = self.harness._parse_location(response3)
        assert location3["line"] == 100
        assert location3["file"] is None
        assert location3["function"] is None

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_extract_code_from_response(self):
        """测试从响应中提取代码"""
        await self.harness.initialize()

        # 测试带语言标记的代码块
        response1 = """
        修复后的代码：
        ```python
def fixed_function():
    return 42
```
        """
        code1 = self.harness._extract_code_from_response(response1, "python")
        assert "def fixed_function():" in code1
        assert "return 42" in code1

        # 测试无语言标记的代码块
        response2 = """
        ```
var x = 10;
console.log(x);
```
        """
        code2 = self.harness._extract_code_from_response(response2, "javascript")
        assert "var x = 10" in code2

        # 测试无代码块标记的情况
        response3 = "这是修复后的代码：print('fixed')"
        code3 = self.harness._extract_code_from_response(response3, "python")
        assert code3 == "这是修复后的代码：print('fixed')"

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_diagnose_error(self):
        """测试错误诊断"""
        await self.harness.initialize()

        error_info = {
            "error_message": "IndexError: list index out of range",
            "stack_trace": "File 'test.py', line 5, in get_item\n    return items[index]",
            "code": "items = [1, 2, 3]\nprint(items[5])",
            "context": "Trying to access list item",
            "language": "python"
        }

        mock_response = """
错误类型：IndexError
根本原因：尝试访问列表中不存在的索引
位置：
- 文件：test.py
- 行：5
- 函数：get_item
可能的触发条件：索引值大于列表长度减1
"""

        with patch('src.harness.debug.chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = mock_response

            diagnosis = await self.harness._diagnose_error(error_info)

            assert diagnosis["error_type"] == "IndexError"
            assert "test.py" in diagnosis["root_cause"]
            assert diagnosis["location"]["file"] == "test.py"
            assert diagnosis["location"]["line"] == 5
            assert diagnosis["location"]["function"] == "get_item"

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_suggest_fix(self):
        """测试修复建议"""
        await self.harness.initialize()

        diagnosis = {
            "error_type": "IndexError",
            "root_cause": "List index out of range",
            "location": {"file": "test.py", "line": 5, "function": "get_item"}
        }

        error_info = {
            "code": "items = [1, 2, 3]\nprint(items[5])",
            "language": "python"
        }

        mock_response = """
修复后的代码：
```python
items = [1, 2, 3]
if len(items) > 5:
    print(items[5])
else:
    print("Index out of range")
```

修复说明：
添加了边界检查，防止索引越界。

预防措施：
在访问列表元素前检查索引范围。
"""

        with patch('src.harness.debug.chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = mock_response

            fix_suggestion = await self.harness._suggest_fix(diagnosis, error_info)

            assert fix_suggestion["can_fix"] is True
            assert fix_suggestion["fixed_code"] is not None
            assert "if len(items) > 5" in fix_suggestion["fixed_code"]
            assert fix_suggestion["confidence"] == 0.85
            assert fix_suggestion["language"] == "python"

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_apply_fix(self):
        """测试应用修复"""
        await self.harness.initialize()

        fix_suggestion = {
            "can_fix": True,
            "fixed_code": "def fixed():\n    return True",
            "language": "python"
        }

        error_info = {
            "code": "def broken():\n    return False",
            "language": "python"
        }

        fix_result = await self.harness._apply_fix(fix_suggestion, error_info)

        assert fix_result["success"] is True
        assert fix_result["fixed_code"] == "def fixed():\n    return True"
        assert fix_result["original_code"] == "def broken():\n    return False"
        assert fix_result["language"] == "python"

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_apply_fix_no_code(self):
        """测试没有修复代码时的应用修复"""
        await self.harness.initialize()

        fix_suggestion = {
            "can_fix": True,
            "fixed_code": None,
            "language": "python"
        }

        error_info = {"code": "broken code", "language": "python"}

        fix_result = await self.harness._apply_fix(fix_suggestion, error_info)

        assert fix_result["success"] is False
        assert "没有可应用的修复" in fix_result["message"]

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_verify_fix(self):
        """测试修复验证"""
        await self.harness.initialize()

        error_info = {
            "error_message": "IndexError: list index out of range",
            "language": "python"
        }

        fixed_code = "items = [1, 2, 3]\nif len(items) > index:\n    print(items[index])"

        diagnosis = {
            "error_type": "IndexError"
        }

        mock_response = """
验证结果：

1. 修复是否解决了原问题：是，添加了索引边界检查
2. 是否引入了新的问题：否，代码逻辑正确
3. 修复质量评分：8/10

这是一个良好的修复，解决了越界问题。
"""

        with patch('src.harness.debug.chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = mock_response

            verification = await self.harness._verify_fix(error_info, fixed_code, diagnosis)

            assert verification["verified"] is True
            assert verification["score"] == 8
            assert "良好的修复" in verification["feedback"]

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_verify_fix_low_score(self):
        """测试低分修复的验证"""
        await self.harness.initialize()

        error_info = {
            "error_message": "Some error",
            "language": "python"
        }

        fixed_code = "some code"

        diagnosis = {"error_type": "SomeError"}

        mock_response = """
验证结果：
修复质量评分：5/10
这个修复不完整。
"""

        with patch('src.harness.debug.chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = mock_response

            verification = await self.harness._verify_fix(error_info, fixed_code, diagnosis)

            assert verification["verified"] is False
            assert verification["score"] == 5

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_execute_debug_task(self):
        """测试执行完整的调试任务"""
        await self.harness.initialize()

        task = Task(
            description="Fix the index error",
            task_type=TaskType.DEBUG,
            requirements={
                "error": "IndexError: list index out of range",
                "stack_trace": "File 'test.py', line 5",
                "code": "items = [1, 2]\nprint(items[5])",
                "language": "python"
            }
        )

        mock_diagnosis = "错误类型：IndexError\n文件：test.py\n行：5"
        mock_fix = """
```python
items = [1, 2]
if len(items) > 5:
    print(items[5])
```
"""
        mock_verification = "修复质量评分：9/10"

        with patch('src.harness.debug.chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_chat.side_effect = [mock_diagnosis, mock_fix, mock_verification]

            result = await self.harness.execute(task)

            assert result.status == TaskStatus.COMPLETED.value
            assert result.output is not None
            assert "diagnosis" in result.output
            assert "fix_suggestion" in result.output
            assert "fix_result" in result.output
            assert result.metadata["harness_type"] == HarnessType.DEBUG.value
            assert result.metadata["task_subtype"] == "debug"

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_execute_without_error_info(self):
        """测试没有显式错误信息时使用描述作为错误信息"""
        await self.harness.initialize()

        task = Task(
            description="NameError: name 'undefined_var' is not defined",
            task_type=TaskType.DEBUG
        )

        mock_diagnosis = "错误类型：NameError"
        mock_fix = """
```python
undefined_var = None
print(undefined_var)
```
"""

        with patch('src.harness.debug.chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_chat.side_effect = [mock_diagnosis, mock_fix]

            result = await self.harness.execute(task)

            assert result.status == TaskStatus.COMPLETED.value
            assert result.output["error_info"]["error_message"] == task.description

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_execute_with_llm_error(self):
        """测试 LLM 调用失败时的处理 - 内部方法会捕获异常并返回错误信息"""
        await self.harness.initialize()

        task = Task(
            description="Debug this error",
            task_type=TaskType.DEBUG,
            requirements={
                "error": "SomeError",
                "code": "broken code"
            }
        )

        with patch('src.harness.debug.chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_chat.side_effect = Exception("LLM API Error")

            result = await self.harness.execute(task)

            # 即使 LLM 调用失败，任务也会完成，但诊断结果中会有错误信息
            assert result.status == TaskStatus.COMPLETED.value
            assert result.output is not None
            assert "diagnosis" in result.output
            # 诊断结果中包含错误信息
            assert "诊断失败" in result.output["diagnosis"]["root_cause"]

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_factory_registration(self):
        """测试工厂注册"""
        # 确保 DebugHarness 已注册
        assert HarnessFactory.is_registered(HarnessType.DEBUG)

        # 使用工厂创建实例
        harness = HarnessFactory.create(HarnessType.DEBUG)
        assert isinstance(harness, DebugHarness)

    @pytest.mark.asyncio
    async def test_factory_create_with_config(self):
        """测试工厂创建带配置的实例"""
        config = {
            "custom_params": {
                "max_iterations": 10,
                "auto_fix": False,
                "enable_monitoring": False
            }
        }

        harness = HarnessFactory.create(HarnessType.DEBUG, config=config)
        assert isinstance(harness, DebugHarness)
        assert harness.max_iterations == 10
        assert harness.auto_fix is False

    @pytest.mark.asyncio
    async def test_harness_config_defaults(self):
        """测试 Harness 配置默认值"""
        config = HarnessConfig(harness_type=HarnessType.DEBUG)
        harness = DebugHarness(config)

        assert harness.max_iterations == 5
        assert harness.auto_fix is True
        assert harness.enable_monitoring is True

    @pytest.mark.asyncio
    async def test_result_structure(self):
        """测试结果结构完整性"""
        await self.harness.initialize()

        task = Task(
            description="Debug this error",
            task_type=TaskType.DEBUG,
            requirements={
                "error": "TestError",
                "code": "test code"
            }
        )

        mock_diagnosis = "错误类型：TestError"
        mock_fix = "```python\nfixed code\n```"
        mock_verification = "评分：8/10"

        with patch('src.harness.debug.chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_chat.side_effect = [mock_diagnosis, mock_fix, mock_verification]

            result = await self.harness.execute(task)

            # 验证 TaskResult 结构
            assert result.task_id == task.task_id
            assert result.status == TaskStatus.COMPLETED.value
            assert isinstance(result.output, dict)
            assert "diagnosis" in result.output
            assert "fix_suggestion" in result.output
            assert "fix_result" in result.output
            assert "iterations" in result.output
            assert "error_info" in result.output
            assert isinstance(result.quality_score, float)
            assert isinstance(result.execution_time, float)
            assert isinstance(result.logs, list)
            assert isinstance(result.metadata, dict)
            assert result.metadata["harness_type"] == HarnessType.DEBUG.value

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """测试资源清理"""
        await self.harness.initialize()
        assert self.harness.is_initialized()

        await self.harness.cleanup()
        assert not self.harness.is_initialized()


class TestDebugHarnessMonitoring:
    """DebugHarness 监控功能测试"""

    @pytest.mark.asyncio
    async def test_monitoring_enabled(self):
        """测试启用监控"""
        HarnessFactory.clear_registry()
        HarnessFactory.register(HarnessType.DEBUG, DebugHarness)

        config = HarnessConfig(
            harness_type=HarnessType.DEBUG,
            custom_params={"enable_monitoring": True}
        )

        harness = DebugHarness(config)
        await harness.initialize()

        assert harness.task_monitor is not None

        await harness.cleanup()
        HarnessFactory.clear_registry()

    @pytest.mark.asyncio
    async def test_monitoring_disabled(self):
        """测试禁用监控"""
        HarnessFactory.clear_registry()
        HarnessFactory.register(HarnessType.DEBUG, DebugHarness)

        config = HarnessConfig(
            harness_type=HarnessType.DEBUG,
            custom_params={"enable_monitoring": False}
        )

        harness = DebugHarness(config)
        await harness.initialize()

        assert harness.task_monitor is None

        await harness.cleanup()
        HarnessFactory.clear_registry()


class TestDebugHarnessWithSourceCodeKey:
    """测试使用 source_code 键提取代码"""

    def setup_method(self):
        HarnessFactory.clear_registry()
        HarnessFactory.register(HarnessType.DEBUG, DebugHarness)

        self.config = HarnessConfig(
            harness_type=HarnessType.DEBUG,
            custom_params={"enable_monitoring": False}
        )
        self.harness = DebugHarness(self.config)

    def teardown_method(self):
        HarnessFactory.clear_registry()

    @pytest.mark.asyncio
    async def test_extract_source_code_from_requirements(self):
        """测试从 requirements 中使用 source_code 键提取"""
        await self.harness.initialize()

        task = Task(
            description="Debug this",
            requirements={
                "source_code": "def main():\n    pass"
            }
        )

        error_info = self.harness._extract_error_info(task)
        assert error_info["code"] == "def main():\n    pass"

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_extract_source_code_from_metadata(self):
        """测试从 metadata 中使用 source_code 键提取"""
        await self.harness.initialize()

        task = Task(
            description="Debug this",
            requirements={},
            metadata={
                "source_code": "class Test:\n    pass"
            }
        )

        error_info = self.harness._extract_error_info(task)
        assert error_info["code"] == "class Test:\n    pass"

        await self.harness.cleanup()
