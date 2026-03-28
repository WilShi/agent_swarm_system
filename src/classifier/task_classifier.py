"""
TaskClassifier 主类
协调意图分析、Harness 选择和确认流程
"""
from typing import Dict, Any, Optional
from src.core.types import ClassificationResult, ConfirmationRequest, ConfirmationResponse
from src.classifier.intent_analyzer import IntentAnalyzer
from src.classifier.harness_selector import HarnessSelector
from src.classifier.confirmation import ConfirmationManager


class TaskClassifier:
    """
    任务分类器主类

    协调以下组件完成分类流程：
    1. IntentAnalyzer - 分析用户意图
    2. HarnessSelector - 选择合适的 Harness
    3. ConfirmationManager - 管理确认流程
    """

    def __init__(self):
        self.intent_analyzer = IntentAnalyzer()
        self.harness_selector = HarnessSelector()
        self.confirmation_manager = ConfirmationManager()

    async def classify(
        self,
        user_input: str,
        context: Dict[str, Any] = None
    ) -> ClassificationResult:
        """
        对用户输入进行分类

        Args:
            user_input: 用户输入文本
            context: 可选的上下文信息

        Returns:
            ClassificationResult 分类结果
        """
        # 1. 分析意图
        intent = await self.intent_analyzer.analyze(user_input, context)

        # 2. 选择 Harness
        (
            harness_type,
            task_type,
            confidence,
            reasoning,
            sub_tasks,
            requirements,
            keywords,
            estimated_complexity,
            estimated_duration
        ) = await self.harness_selector.select(user_input, intent)

        # 3. 构建分类结果
        classification = ClassificationResult(
            intent=intent,
            task_type=task_type,
            harness_type=harness_type,
            confidence=confidence,
            reasoning=reasoning,
            sub_tasks=sub_tasks,
            requirements=requirements,
            keywords=keywords,
            estimated_complexity=estimated_complexity,
            estimated_duration=estimated_duration
        )

        return classification

    async def classify_with_confirmation(
        self,
        user_input: str,
        context: Dict[str, Any] = None
    ) -> tuple[ClassificationResult, Optional[ConfirmationRequest]]:
        """
        分类并判断是否需要确认

        Args:
            user_input: 用户输入
            context: 上下文

        Returns:
            (分类结果, 确认请求或None)
        """
        # 1. 执行分类
        classification = await self.classify(user_input, context)

        # 2. 判断是否需要确认
        if self.confirmation_manager.needs_confirmation(classification):
            confirmation = self.confirmation_manager.create_confirmation_request(classification)
            return classification, confirmation

        return classification, None

    def process_confirmation_response(
        self,
        request: ConfirmationRequest,
        response: ConfirmationResponse
    ) -> ClassificationResult:
        """
        处理确认响应

        Args:
            request: 确认请求
            response: 用户响应

        Returns:
            最终的分类结果
        """
        return self.confirmation_manager.process_response(request, response)

    async def classify_batch(
        self,
        inputs: list[str],
        context: Dict[str, Any] = None
    ) -> list[ClassificationResult]:
        """
        批量分类多个输入

        Args:
            inputs: 用户输入列表
            context: 上下文

        Returns:
            分类结果列表
        """
        results = []
        for user_input in inputs:
            result = await self.classify(user_input, context)
            results.append(result)
        return results

    def get_intent_analyzer(self) -> IntentAnalyzer:
        """获取意图分析器"""
        return self.intent_analyzer

    def get_harness_selector(self) -> HarnessSelector:
        """获取 Harness 选择器"""
        return self.harness_selector

    def get_confirmation_manager(self) -> ConfirmationManager:
        """获取确认管理器"""
        return self.confirmation_manager
