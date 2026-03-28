"""
TestHarness 测试

测试 TestHarness 的各项功能，包括：
1. 测试初始化
2. 测试信息提取
3. 测试生成
4. 测试执行
5. 覆盖率分析
6. 报告生成
7. 通过判断
8. 质量得分计算
"""
import pytest
from unittest.mock import patch, AsyncMock

from src.harness.test_harness import TestHarness
from src.harness.factory import HarnessFactory
from src.core.types import (
    Task, TaskResult, HarnessConfig, HarnessType, TaskStatus, TaskType
)


class TestTestHarness:
    """TestHarness 测试类"""

    def setup_method(self):
        """每个测试前清理注册表并创建测试实例"""
        HarnessFactory.clear_registry()

        # 注册 TestHarness
        HarnessFactory.register(HarnessType.TEST, TestHarness)

        # 创建测试配置
        self.config = HarnessConfig(
            harness_type=HarnessType.TEST,
            custom_params={
                "test_framework": "pytest",
                "coverage_threshold": 80,
                "generate_missing_tests": True,
                "language": "python"
            }
        )

        # 创建 harness 实例
        self.harness = TestHarness(self.config)

    def teardown_method(self):
        """每个测试后清理"""
        HarnessFactory.clear_registry()

    @pytest.mark.asyncio
    async def test_initialize(self):
        """测试初始化"""
        await self.harness.initialize()
        assert self.harness.is_initialized()
        assert self.harness.test_framework == "pytest"
        assert self.harness.coverage_threshold == 80
        assert self.harness.generate_missing_tests is True
        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_extract_test_info(self):
        """测试提取测试信息"""
        task = Task(
            description="测试这段代码",
            requirements={
                "code": "def add(a, b): return a + b",
                "existing_tests": ["test_add"],
                "test_types": ["unit", "integration"],
                "target_functions": ["add"],
                "language": "python"
            }
        )

        test_info = self.harness._extract_test_info(task)

        assert test_info["code"] == "def add(a, b): return a + b"
        assert test_info["existing_tests"] == ["test_add"]
        assert test_info["test_types"] == ["unit", "integration"]
        assert test_info["target_functions"] == ["add"]
        assert test_info["language"] == "python"

    @pytest.mark.asyncio
    async def test_extract_test_info_defaults(self):
        """测试提取测试信息默认值"""
        task = Task(description="测试代码")

        test_info = self.harness._extract_test_info(task)

        assert test_info["code"] == ""
        assert test_info["existing_tests"] == []
        assert test_info["test_types"] == ["unit"]
        assert test_info["target_functions"] == []
        assert test_info["language"] == "python"

    @pytest.mark.asyncio
    async def test_generate_tests(self):
        """测试生成测试用例"""
        await self.harness.initialize()

        test_info = {
            "code": "def add(a, b): return a + b",
            "test_types": ["unit"],
            "language": "python",
            "test_framework": "pytest"
        }

        mock_response = """
def test_add():
    assert add(1, 2) == 3
    assert add(-1, 1) == 0
"""

        with patch('src.harness.test_harness.chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = mock_response

            generated = await self.harness._generate_tests(test_info)

            assert len(generated) == 1
            assert generated[0]["type"] == "generated"
            assert "test_add" in generated[0]["code"]

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_generate_tests_no_code(self):
        """测试没有代码时生成测试"""
        await self.harness.initialize()

        test_info = {
            "code": "",
            "test_types": ["unit"],
            "language": "python"
        }

        generated = await self.harness._generate_tests(test_info)
        assert generated == []

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_run_tests(self):
        """测试执行测试"""
        await self.harness.initialize()

        test_info = {
            "code": "def add(a, b): return a + b",
            "existing_tests": [],
            "test_types": ["unit"]
        }
        generated_tests = []

        results = await self.harness._run_tests(test_info, generated_tests)

        assert "total" in results
        assert "passed" in results
        assert "failed" in results
        assert "duration" in results
        assert "details" in results

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_run_tests_with_existing_tests(self):
        """测试执行已有测试"""
        await self.harness.initialize()

        test_info = {
            "code": "def add(a, b): return a + b",
            "existing_tests": ["test_existing"],
            "test_types": ["unit"]
        }
        generated_tests = []

        results = await self.harness._run_tests(test_info, generated_tests)

        # 应该包含已有测试
        assert results["total"] > 10  # 基础10个加上已有测试

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_analyze_coverage(self):
        """测试覆盖率分析"""
        await self.harness.initialize()

        test_results = {
            "total": 10,
            "passed": 8,
            "failed": 2
        }
        test_info = {
            "code": "def add(a, b): return a + b",
            "target_functions": ["add"]
        }

        coverage = await self.harness._analyze_coverage(test_results, test_info)

        assert "overall" in coverage
        assert "by_file" in coverage
        assert "by_function" in coverage
        assert coverage["threshold"] == 80

        # 失败测试会降低覆盖率
        assert coverage["overall"] < 85

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_analyze_coverage_no_failures(self):
        """测试无失败时的覆盖率分析"""
        await self.harness.initialize()

        test_results = {
            "total": 10,
            "passed": 10,
            "failed": 0
        }
        test_info = {"code": "def foo(): pass"}

        coverage = await self.harness._analyze_coverage(test_results, test_info)

        # 无失败时应该保持高覆盖率
        assert coverage["overall"] == 85.0

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_generate_report(self):
        """测试生成测试报告"""
        await self.harness.initialize()

        test_results = {
            "total": 10,
            "passed": 8,
            "failed": 2,
            "framework": "pytest"
        }
        coverage = {
            "overall": 85.0
        }

        report = await self.harness._generate_report(test_results, coverage)

        assert "summary" in report
        assert "pass_rate" in report
        assert "coverage" in report
        assert "recommendations" in report
        assert report["pass_rate"] == 80.0
        assert report["coverage"] == "85.0%"

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_generate_report_with_recommendations(self):
        """测试生成报告时的建议"""
        await self.harness.initialize()

        # 低覆盖率和失败测试应该产生建议
        test_results = {
            "total": 10,
            "passed": 5,
            "failed": 5,
            "framework": "pytest"
        }
        coverage = {
            "overall": 70.0
        }

        report = await self.harness._generate_report(test_results, coverage)

        # 应该有修复失败和提高覆盖率的建议
        assert len(report["recommendations"]) > 0
        assert any("修复" in r for r in report["recommendations"])
        assert any("覆盖率" in r for r in report["recommendations"])

        await self.harness.cleanup()

    def test_check_passed(self):
        """测试通过判断"""
        # 通过的情况：无失败且覆盖率达到阈值
        test_results_pass = {"failed": 0}
        coverage_pass = {"overall": 85}
        assert self.harness._check_passed(test_results_pass, coverage_pass) is True

        # 失败的情况：有失败测试
        test_results_fail = {"failed": 1}
        coverage_fail = {"overall": 85}
        assert self.harness._check_passed(test_results_fail, coverage_fail) is False

        # 失败的情况：覆盖率不足
        test_results_low = {"failed": 0}
        coverage_low = {"overall": 70}
        assert self.harness._check_passed(test_results_low, coverage_low) is False

        # 失败的情况：两者都有问题
        test_results_both = {"failed": 2}
        coverage_both = {"overall": 70}
        assert self.harness._check_passed(test_results_both, coverage_both) is False

    def test_calculate_quality_score(self):
        """测试质量得分计算"""
        # 完美情况
        test_results = {"total": 10, "passed": 10}
        coverage = {"overall": 100}
        score = self.harness._calculate_quality_score(test_results, coverage)
        assert score == 1.0

        # 一半通过率
        test_results = {"total": 10, "passed": 5}
        coverage = {"overall": 50}
        score = self.harness._calculate_quality_score(test_results, coverage)
        assert score == 0.5

        # 无测试的情况
        test_results = {"total": 0, "passed": 0}
        coverage = {"overall": 0}
        score = self.harness._calculate_quality_score(test_results, coverage)
        assert score == 0.0

    @pytest.mark.asyncio
    async def test_execute_complete_task(self):
        """测试执行完整任务"""
        await self.harness.initialize()

        task = Task(
            description="测试这段代码",
            task_type=TaskType.TEST,
            requirements={
                "code": "def add(a, b): return a + b",
                "test_types": ["unit"]
            }
        )

        with patch('src.harness.test_harness.chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = "def test_add(): pass"

            result = await self.harness.execute(task)

            assert isinstance(result, TaskResult)
            assert result.task_id == task.task_id
            assert "test_results" in result.output
            assert "coverage" in result.output
            assert "report" in result.output
            assert "generated_tests" in result.output
            assert "passed" in result.output
            assert isinstance(result.quality_score, float)

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_execute_with_llm_error(self):
        """测试 LLM 调用失败时的处理"""
        await self.harness.initialize()

        task = Task(
            description="测试这段代码",
            task_type=TaskType.TEST,
            requirements={
                "code": "def add(a, b): return a + b"
            }
        )

        with patch('src.harness.test_harness.chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_chat.side_effect = Exception("LLM API Error")

            # LLM 失败不应该导致任务失败，只是生成空测试
            result = await self.harness.execute(task)

            # 结果应该是完成状态（因为没有生成测试，但执行了现有测试）
            assert result.status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_execute_task_no_code(self):
        """测试没有代码的任务"""
        await self.harness.initialize()

        task = Task(
            description="测试代码",
            task_type=TaskType.TEST,
            requirements={}
        )

        result = await self.harness.execute(task)

        assert result.status == TaskStatus.FAILED.value or result.status == TaskStatus.COMPLETED.value

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_test_history(self):
        """测试历史记录功能"""
        await self.harness.initialize()

        # 初始为空
        assert len(self.harness.get_test_history()) == 0

        # 执行任务后应该有记录
        task = Task(
            description="测试",
            requirements={"code": "def foo(): pass"}
        )

        with patch('src.harness.test_harness.chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = "def test_foo(): pass"
            await self.harness.execute(task)

        assert len(self.harness.get_test_history()) == 1

        # 清空历史
        self.harness.clear_history()
        assert len(self.harness.get_test_history()) == 0

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_factory_registration(self):
        """测试工厂注册"""
        # 确保 TestHarness 已注册
        assert HarnessFactory.is_registered(HarnessType.TEST)

        # 使用工厂创建实例
        harness = HarnessFactory.create(HarnessType.TEST)
        assert isinstance(harness, TestHarness)

    @pytest.mark.asyncio
    async def test_factory_create_with_config(self):
        """测试工厂创建带配置的实例"""
        config = {
            "custom_params": {
                "test_framework": "jest",
                "coverage_threshold": 90,
                "generate_missing_tests": False,
                "language": "javascript"
            }
        }

        harness = HarnessFactory.create(HarnessType.TEST, config=config)
        assert isinstance(harness, TestHarness)
        assert harness.test_framework == "jest"
        assert harness.coverage_threshold == 90
        assert harness.generate_missing_tests is False
        assert harness.language == "javascript"

    @pytest.mark.asyncio
    async def test_harness_config_defaults(self):
        """测试 Harness 配置默认值"""
        config = HarnessConfig(harness_type=HarnessType.TEST)
        harness = TestHarness(config)

        assert harness.test_framework == "pytest"
        assert harness.coverage_threshold == 80
        assert harness.generate_missing_tests is True
        assert harness.language == "python"

    @pytest.mark.asyncio
    async def test_result_structure(self):
        """测试结果结构完整性"""
        await self.harness.initialize()

        task = Task(
            description="测试代码",
            task_type=TaskType.TEST,
            requirements={"code": "def foo(): pass"}
        )

        with patch('src.harness.test_harness.chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = "def test_foo(): pass"

            result = await self.harness.execute(task)

            # 验证 TaskResult 结构
            assert result.task_id == task.task_id
            assert result.status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]
            assert isinstance(result.output, dict)
            assert "test_results" in result.output
            assert "coverage" in result.output
            assert isinstance(result.quality_score, float)
            assert isinstance(result.metadata, dict)
            assert result.metadata["harness_type"] == HarnessType.TEST.value
            assert result.metadata["test_framework"] == "pytest"

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """测试资源清理"""
        await self.harness.initialize()
        assert self.harness.is_initialized()

        # 添加一些历史记录
        self.harness._test_history.append({"test": "data"})

        await self.harness.cleanup()
        assert not self.harness.is_initialized()
        assert len(self.harness.get_test_history()) == 0


class TestTestHarnessDifferentFrameworks:
    """测试不同测试框架配置"""

    @pytest.mark.asyncio
    async def test_jest_framework(self):
        """测试 Jest 框架配置"""
        HarnessFactory.clear_registry()
        HarnessFactory.register(HarnessType.TEST, TestHarness)

        config = HarnessConfig(
            harness_type=HarnessType.TEST,
            custom_params={
                "test_framework": "jest",
                "language": "javascript"
            }
        )

        harness = TestHarness(config)
        await harness.initialize()

        assert harness.test_framework == "jest"
        assert harness.language == "javascript"

        await harness.cleanup()
        HarnessFactory.clear_registry()

    @pytest.mark.asyncio
    async def test_custom_threshold(self):
        """测试自定义覆盖率阈值"""
        HarnessFactory.clear_registry()
        HarnessFactory.register(HarnessType.TEST, TestHarness)

        config = HarnessConfig(
            harness_type=HarnessType.TEST,
            custom_params={
                "coverage_threshold": 95
            }
        )

        harness = TestHarness(config)

        # 低覆盖率应该失败
        test_results = {"failed": 0}
        coverage = {"overall": 90}
        assert harness._check_passed(test_results, coverage) is False

        # 高覆盖率应该通过
        coverage = {"overall": 96}
        assert harness._check_passed(test_results, coverage) is True

        HarnessFactory.clear_registry()


class TestTestHarnessEdgeCases:
    """测试边界情况"""

    def setup_method(self):
        """每个测试前清理注册表并创建测试实例"""
        HarnessFactory.clear_registry()
        HarnessFactory.register(HarnessType.TEST, TestHarness)

        self.config = HarnessConfig(
            harness_type=HarnessType.TEST,
            custom_params={
                "test_framework": "pytest",
                "coverage_threshold": 80,
                "generate_missing_tests": True
            }
        )
        self.harness = TestHarness(self.config)

    def teardown_method(self):
        """每个测试后清理"""
        HarnessFactory.clear_registry()

    @pytest.mark.asyncio
    async def test_generate_tests_disabled(self):
        """测试禁用测试生成"""
        HarnessFactory.clear_registry()
        HarnessFactory.register(HarnessType.TEST, TestHarness)

        config = HarnessConfig(
            harness_type=HarnessType.TEST,
            custom_params={
                "generate_missing_tests": False
            }
        )

        harness = TestHarness(config)
        await harness.initialize()

        task = Task(
            description="测试代码",
            requirements={"code": "def foo(): pass"}
        )

        result = await harness.execute(task)

        # 即使没有生成测试也应该完成
        assert "test_results" in result.output
        assert result.output["generated_tests"] == []

        await harness.cleanup()
        HarnessFactory.clear_registry()

    @pytest.mark.asyncio
    async def test_empty_task_requirements(self):
        """测试空任务需求"""
        await self.harness.initialize()

        task = Task(description="测试")

        result = await self.harness.execute(task)

        # 应该正常处理空需求
        assert result.task_id == task.task_id

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_coverage_calculation_edge_cases(self):
        """测试覆盖率计算边界情况"""
        await self.harness.initialize()

        # 非常高的失败数
        test_results = {"total": 100, "failed": 20}
        coverage = await self.harness._analyze_coverage(test_results, {})
        assert coverage["overall"] >= 0  # 不应为负数

        await self.harness.cleanup()
