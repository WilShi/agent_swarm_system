"""
Test Harness - 测试验证和质量保证

专门用于处理测试生成、执行、覆盖率分析和质量评估的 Harness。
使用 Kimi K2.5 (via DashScope) 进行测试生成和分析。
"""
from typing import Dict, Any, List, Optional
import asyncio

from src.harness.base import BaseHarness
from src.harness.factory import HarnessFactory
from src.core.types import Task, TaskResult, HarnessConfig, HarnessType, TaskStatus
from src.core.llm_client import chat_completion


class TestHarness(BaseHarness):
    """测试 Harness - 专门处理测试验证任务

    功能：
    1. 测试生成 - 生成单元测试、集成测试
    2. 测试执行 - 运行测试并收集结果
    3. 覆盖率分析 - 分析代码覆盖率
    4. 质量指标 - 计算质量得分

    配置参数：
    - test_framework: 测试框架 (默认: pytest)
    - coverage_threshold: 覆盖率阈值 (默认: 80)
    - generate_missing_tests: 是否生成缺失的测试 (默认: True)
    """

    SYSTEM_PROMPT = """你是一个专业的测试工程师。你的任务是：
1. 分析代码和需求，生成全面的测试用例
2. 执行测试并收集结果
3. 分析测试覆盖率和质量
4. 提供测试报告和改进建议

请确保测试覆盖正常路径、边界条件和异常情况。

生成测试时请遵循以下原则：
- 使用给定的测试框架语法
- 包含边界条件测试
- 包含异常情况测试
- 添加清晰的测试文档
- 确保测试名称描述性强"""

    def __init__(self, config: HarnessConfig):
        super().__init__(config)
        self.test_framework = config.custom_params.get("test_framework", "pytest")
        self.coverage_threshold = config.custom_params.get("coverage_threshold", 80)
        self.generate_missing_tests = config.custom_params.get("generate_missing_tests", True)
        self.language = config.custom_params.get("language", "python")
        self._test_history: List[Dict[str, Any]] = []

    async def initialize(self):
        """初始化 Test Harness"""
        await super().initialize()
        self._initialized = True

    async def execute(self, task: Task) -> TaskResult:
        """执行测试任务

        执行流程：
        1. 提取代码和测试信息
        2. 生成测试（如果需要）
        3. 执行测试
        4. 分析覆盖率
        5. 生成报告
        6. 判断是否通过
        """
        try:
            # 1. 提取测试信息
            test_info = self._extract_test_info(task)

            # 2. 生成测试（如果需要）
            generated_tests = []
            if self.generate_missing_tests:
                generated_tests = await self._generate_tests(test_info)

            # 3. 执行测试
            test_results = await self._run_tests(test_info, generated_tests)

            # 4. 分析覆盖率
            coverage = await self._analyze_coverage(test_results, test_info)

            # 5. 生成报告
            report = await self._generate_report(test_results, coverage)

            # 6. 判断是否通过
            passed = self._check_passed(test_results, coverage)

            # 计算质量得分
            quality_score = self._calculate_quality_score(test_results, coverage)

            # 保存到历史记录
            self._test_history.append({
                "task_id": task.task_id,
                "test_results": test_results,
                "coverage": coverage,
                "passed": passed
            })

            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.COMPLETED.value if passed else TaskStatus.FAILED.value,
                output={
                    "test_results": test_results,
                    "coverage": coverage,
                    "report": report,
                    "generated_tests": generated_tests,
                    "passed": passed
                },
                quality_score=quality_score,
                metadata={
                    "harness_type": HarnessType.TEST.value,
                    "test_framework": self.test_framework,
                    "coverage_threshold": self.coverage_threshold,
                    "task_type": "test_execution"
                }
            )

        except Exception as e:
            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.FAILED.value,
                output=None,
                errors=[str(e)],
                metadata={"harness_type": HarnessType.TEST.value}
            )

    def _extract_test_info(self, task: Task) -> Dict[str, Any]:
        """提取测试信息

        从任务中提取代码、现有测试、测试类型等信息。
        """
        return {
            "code": task.requirements.get("code", ""),
            "existing_tests": task.requirements.get("existing_tests", []),
            "test_types": task.requirements.get("test_types", ["unit"]),
            "target_functions": task.requirements.get("target_functions", []),
            "language": task.requirements.get("language", self.language),
            "test_framework": task.requirements.get("test_framework", self.test_framework),
            "description": task.description
        }

    async def _generate_tests(self, test_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成测试用例

        使用 LLM 生成测试代码。
        """
        if not test_info["code"]:
            return []

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"""请为以下代码生成测试用例：

代码：
```python
{test_info['code']}
```

测试类型：{', '.join(test_info['test_types'])}
语言：{test_info['language']}
测试框架：{test_info['test_framework']}

请生成完整的测试代码，包括：
1. 必要的导入语句
2. 正常路径测试
3. 边界条件测试
4. 异常情况测试
5. 清晰的测试函数名称"""}
        ]

        try:
            response = await chat_completion(
                messages,
                temperature=0.3,
                max_tokens=2000
            )

            return [{
                "name": f"generated_test_{len(self._test_history)}",
                "code": response,
                "type": "generated",
                "framework": test_info['test_framework']
            }]
        except Exception:
            # 如果 LLM 调用失败，返回空列表
            return []

    async def _run_tests(self, test_info: Dict[str, Any],
                        generated_tests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """执行测试

        实际执行测试并收集结果。
        当前为模拟实现，实际应用中需要集成真实测试框架。
        """
        # 模拟测试执行
        # 实际实现中应该：
        # 1. 将生成的测试写入临时文件
        # 2. 使用 pytest / jest 等框架执行
        # 3. 收集测试结果

        total_tests = 10
        passed_tests = 8
        failed_tests = 2
        skipped_tests = 0

        # 如果有现有测试，调整数量
        if test_info["existing_tests"]:
            total_tests += len(test_info["existing_tests"])
            passed_tests += len(test_info["existing_tests"])

        # 模拟测试结果详情
        details = []
        for i in range(failed_tests):
            details.append({
                "test_name": f"test_case_{i}",
                "status": "failed",
                "error": f"Assertion error in test_case_{i}",
                "duration": 0.1
            })

        for i in range(passed_tests):
            details.append({
                "test_name": f"test_case_{i + failed_tests}",
                "status": "passed",
                "duration": 0.05
            })

        return {
            "total": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "skipped": skipped_tests,
            "duration": 5.5,
            "details": details,
            "framework": test_info.get("test_framework", self.test_framework)
        }

    async def _analyze_coverage(self, test_results: Dict[str, Any],
                               test_info: Dict[str, Any]) -> Dict[str, Any]:
        """分析覆盖率

        分析代码测试覆盖率。
        当前为模拟实现，实际应用中需要使用 coverage.py 等工具。
        """
        # 模拟覆盖率分析
        # 实际实现中应该：
        # 1. 使用 coverage.py / nyc 等工具
        # 2. 解析覆盖率报告
        # 3. 按文件和函数统计

        overall_coverage = 85.0

        # 如果测试中有失败，降低覆盖率
        if test_results["failed"] > 0:
            overall_coverage = max(0, overall_coverage - test_results["failed"] * 5)

        # 按文件统计（模拟）
        by_file = {}
        if test_info.get("code"):
            # 提取文件名（模拟）
            by_file["main.py"] = {
                "coverage": overall_coverage,
                "lines": 100,
                "covered": int(100 * overall_coverage / 100)
            }

        # 按函数统计（模拟）
        by_function = {}
        if test_info.get("target_functions"):
            for func in test_info["target_functions"]:
                by_function[func] = 90.0
        else:
            by_function["main_function"] = overall_coverage

        return {
            "overall": overall_coverage,
            "by_file": by_file,
            "by_function": by_function,
            "threshold": self.coverage_threshold
        }

    async def _generate_report(self, test_results: Dict[str, Any],
                              coverage: Dict[str, Any]) -> Dict[str, Any]:
        """生成测试报告

        生成包含摘要、覆盖率、建议的完整报告。
        """
        # 生成建议
        recommendations = []

        if test_results.get("failed", 0) > 0:
            recommendations.append(
                f"修复 {test_results['failed']} 个失败的测试用例"
            )

        if coverage.get("overall", 0) < self.coverage_threshold:
            recommendations.append(
                f"提高代码覆盖率至 {self.coverage_threshold}% 以上（当前 {coverage.get('overall', 0):.1f}%）"
            )

        if not test_results.get("details", []):
            recommendations.append("添加更多测试用例以覆盖边界条件")

        # 生成摘要
        pass_rate = (test_results["passed"] / test_results["total"] * 100) \
                    if test_results["total"] > 0 else 0

        summary = (
            f"Tests: {test_results['passed']}/{test_results['total']} passed "
            f"({pass_rate:.1f}%), "
            f"Coverage: {coverage['overall']:.1f}%"
        )

        return {
            "summary": summary,
            "pass_rate": pass_rate,
            "coverage": f"{coverage['overall']:.1f}%",
            "recommendations": recommendations,
            "framework": test_results.get("framework", self.test_framework)
        }

    def _check_passed(self, test_results: Dict[str, Any],
                     coverage: Dict[str, Any]) -> bool:
        """检查是否通过

        检查标准：
        1. 没有失败的测试
        2. 覆盖率达到阈值
        """
        no_failures = test_results.get("failed", 0) == 0
        coverage_ok = coverage.get("overall", 0) >= self.coverage_threshold

        return no_failures and coverage_ok

    def _calculate_quality_score(self, test_results: Dict[str, Any],
                                 coverage: Dict[str, Any]) -> float:
        """计算质量得分

        基于测试通过率和覆盖率计算质量得分（0-1）。
        """
        if test_results["total"] == 0:
            return 0.0

        pass_rate = test_results["passed"] / test_results["total"]
        coverage_rate = coverage.get("overall", 0) / 100

        # 质量得分 = 通过率 * 0.6 + 覆盖率 * 0.4
        quality_score = pass_rate * 0.6 + coverage_rate * 0.4

        return round(quality_score, 2)

    def get_test_history(self) -> List[Dict[str, Any]]:
        """获取测试历史记录"""
        return self._test_history.copy()

    def clear_history(self):
        """清空测试历史记录"""
        self._test_history.clear()

    async def cleanup(self):
        """清理资源"""
        self._test_history.clear()
        self._initialized = False
        await super().cleanup()


# 注册到工厂
HarnessFactory.register(HarnessType.TEST, TestHarness)
