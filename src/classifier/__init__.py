"""
Classifier 模块

提供任务分类功能，包括：
- IntentAnalyzer: 意图分析
- HarnessSelector: Harness 选择
- ConfirmationManager: 确认流程管理
- TaskClassifier: 主分类器类
"""
from src.classifier.task_classifier import TaskClassifier
from src.classifier.intent_analyzer import IntentAnalyzer
from src.classifier.harness_selector import HarnessSelector
from src.classifier.confirmation import ConfirmationManager

__all__ = [
    "TaskClassifier",
    "IntentAnalyzer",
    "HarnessSelector",
    "ConfirmationManager"
]

# 版本信息
__version__ = "1.0.0"


def create_classifier() -> TaskClassifier:
    """
    创建分类器实例的便捷函数

    Returns:
        TaskClassifier 实例
    """
    return TaskClassifier()
