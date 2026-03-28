"""
确认流程管理模块
管理任务分类后的确认流程
"""
from typing import Dict, Any, Optional
from src.core.types import (
    ClassificationResult,
    ConfirmationRequest,
    ConfirmationResponse,
    HarnessType,
    TaskType
)
from src.core.config import get_config


class ConfirmationManager:
    """确认流程管理器"""

    def __init__(self):
        self.config = get_config().classification_config

    def needs_confirmation(self, classification: ClassificationResult) -> bool:
        """
        判断是否需要用户确认

        Args:
            classification: 分类结果

        Returns:
            是否需要确认
        """
        # 如果配置要求所有任务都确认
        if self.config.require_confirmation:
            return True

        # 如果置信度低于阈值，需要确认
        if classification.confidence < self.config.confidence_threshold:
            return True

        # 如果任务类型是 DEBUG 或 TEST，通常需要确认
        if classification.task_type in [TaskType.DEBUG, TaskType.TEST]:
            return True

        # 高复杂度任务需要确认
        if classification.estimated_complexity == "high":
            return True

        return False

    def create_confirmation_request(
        self,
        classification: ClassificationResult
    ) -> ConfirmationRequest:
        """
        创建确认请求

        Args:
            classification: 分类结果

        Returns:
            ConfirmationRequest 对象
        """
        # 构建确认问题
        question = self._build_question(classification)

        # 构建选项
        options = self._build_options(classification)

        return ConfirmationRequest(
            classification=classification,
            question=question,
            options=options,
            timeout=300,  # 默认5分钟超时
            allow_override=True
        )

    def _build_question(self, classification: ClassificationResult) -> str:
        """
        构建确认问题

        Args:
            classification: 分类结果

        Returns:
            确认问题文本
        """
        harness_name = self._get_harness_display_name(classification.harness_type)
        task_name = self._get_task_display_name(classification.task_type)

        question = f"""我分析了您的请求，建议如下处理方案：

任务类型: {task_name}
执行工具: {harness_name}
置信度: {classification.confidence:.0%}
预估复杂度: {classification.estimated_complexity}
预估耗时: {classification.estimated_duration}秒

分析理由: {classification.reasoning}

您是否同意此方案？"""

        return question

    def _build_options(
        self,
        classification: ClassificationResult
    ) -> list[dict[str, str]]:
        """
        构建确认选项

        Args:
            classification: 分类结果

        Returns:
            选项列表
        """
        options = [
            {"value": "confirm", "label": "确认执行"},
            {"value": "cancel", "label": "取消任务"},
        ]

        # 添加其他 harness 选项
        alternative_harnesses = self._get_alternative_harnesses(classification.harness_type)
        for harness in alternative_harnesses:
            harness_name = self._get_harness_display_name(harness)
            options.append({
                "value": f"switch:{harness.value}",
                "label": f"改用 {harness_name}"
            })

        return options

    def _get_alternative_harnesses(self, current: HarnessType) -> list[HarnessType]:
        """获取备选的 Harness 类型"""
        all_harnesses = [
            HarnessType.CLAUDE_CODE,
            HarnessType.CODE,
            HarnessType.DEBUG,
            HarnessType.TEST,
            HarnessType.EXECUTION,
            HarnessType.RESEARCH
        ]

        alternatives = [h for h in all_harnesses if h != current]
        return alternatives[:2]  # 返回前2个备选

    def _get_harness_display_name(self, harness_type: HarnessType) -> str:
        """获取 Harness 显示名称"""
        names = {
            HarnessType.CLAUDE_CODE: "Claude Code",
            HarnessType.CODE: "代码生成",
            HarnessType.DEBUG: "调试工具",
            HarnessType.TEST: "测试工具",
            HarnessType.EXECUTION: "通用执行",
            HarnessType.RESEARCH: "研究分析"
        }
        return names.get(harness_type, harness_type.value)

    def _get_task_display_name(self, task_type: TaskType) -> str:
        """获取任务类型显示名称"""
        names = {
            TaskType.ANALYSIS: "分析",
            TaskType.GENERATION: "生成",
            TaskType.CODE: "代码",
            TaskType.RESEARCH: "研究",
            TaskType.DEBUG: "调试",
            TaskType.TEST: "测试",
            TaskType.AUTOMATION: "自动化",
            TaskType.GENERAL: "通用"
        }
        return names.get(task_type, task_type.value)

    def process_response(
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
            更新后的分类结果
        """
        if not response.confirmed:
            # 用户取消，返回原分类结果但标记为需要取消
            result = request.classification
            return result

        # 检查是否有修改
        if response.selected_harness != request.classification.harness_type:
            # 用户选择了不同的 harness
            result = ClassificationResult(
                intent=request.classification.intent,
                task_type=request.classification.task_type,
                harness_type=response.selected_harness,
                confidence=request.classification.confidence,
                reasoning=request.classification.reasoning,
                sub_tasks=request.classification.sub_tasks,
                requirements=request.classification.requirements,
                keywords=request.classification.keywords,
                estimated_complexity=request.classification.estimated_complexity,
                estimated_duration=request.classification.estimated_duration
            )
            # 应用用户修改
            if response.modifications:
                for key, value in response.modifications.items():
                    if hasattr(result, key):
                        setattr(result, key, value)
            return result

        return request.classification

    def create_quick_confirmation(
        self,
        classification: ClassificationResult
    ) -> ConfirmationRequest:
        """
        创建简化版确认请求（用于低置信度但简单的情况）

        Args:
            classification: 分类结果

        Returns:
            ConfirmationRequest 对象
        """
        harness_name = self._get_harness_display_name(classification.harness_type)

        question = f"我将使用 {harness_name} 处理此请求（置信度: {classification.confidence:.0%}），是否继续？"

        options = [
            {"value": "yes", "label": "是"},
            {"value": "no", "label": "否"},
            {"value": "edit", "label": "修改方案"}
        ]

        return ConfirmationRequest(
            classification=classification,
            question=question,
            options=options,
            timeout=60,  # 1分钟超时
            allow_override=True
        )
