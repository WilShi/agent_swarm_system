"""
Harness 模块

提供任务执行 Harness 的实现，包括：
- BaseHarness: Harness 抽象基类
- HarnessFactory: Harness 工厂，用于创建 Harness 实例
- ExecutionHarness: 默认执行 Harness 实现
- CodeHarness: 代码相关任务 Harness
- DebugHarness: 调试任务 Harness
- ResearchHarness: 研究调研任务 Harness
- TestHarness: 测试验证和质量保证 Harness

使用示例:
    from src.harness import HarnessFactory
    from src.core.types import HarnessType

    # 创建 Harness 实例
    harness = HarnessFactory.create(HarnessType.EXECUTION)

    # 运行任务
    result = await harness.run(task)
"""
from src.harness.base import BaseHarness
from src.harness.factory import HarnessFactory
from src.harness.execution import ExecutionHarness
from src.harness.code import CodeHarness
from src.harness.debug import DebugHarness
from src.harness.research import ResearchHarness
from src.harness.test_harness import TestHarness

__all__ = [
    "BaseHarness",
    "HarnessFactory",
    "ExecutionHarness",
    "CodeHarness",
    "DebugHarness",
    "ResearchHarness",
    "TestHarness",
]

# 版本信息
__version__ = "1.0.0"


# 确保 ExecutionHarness 已注册
# （已在 execution.py 中完成注册）
def get_available_harness_types() -> list[str]:
    """
    获取所有可用的 Harness 类型

    Returns:
        list[str]: Harness 类型名称列表
    """
    return [ht.value for ht in HarnessFactory.get_registered_types()]


def create_harness(harness_type, config: dict = None):
    """
    创建 Harness 实例的便捷函数

    Args:
        harness_type: Harness 类型（HarnessType 枚举或字符串）
        config: 可选的配置字典

    Returns:
        BaseHarness: Harness 实例

    Raises:
        ValueError: 如果 harness_type 无效
    """
    from src.core.types import HarnessType

    if isinstance(harness_type, str):
        try:
            harness_type = HarnessType(harness_type)
        except ValueError:
            raise ValueError(f"Invalid harness type: {harness_type}")

    return HarnessFactory.create(harness_type, config)
