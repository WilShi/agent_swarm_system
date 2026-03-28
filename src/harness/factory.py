"""
HarnessFactory - Harness 工厂

用于创建和管理 Harness 实例。
"""
from typing import Dict, Type, Optional
from src.core.types import HarnessType, HarnessConfig
from src.core.exceptions import HarnessInitError
from src.harness.base import BaseHarness


class HarnessFactory:
    """
    Harness 工厂类

    负责注册和创建 Harness 实例。
    使用类级别的注册表来存储 Harness 类型到类的映射。
    """

    _registry: Dict[HarnessType, Type[BaseHarness]] = {}

    @classmethod
    def register(cls, harness_type: HarnessType, harness_class: Type[BaseHarness]):
        """
        注册 Harness 类型

        Args:
            harness_type: Harness 类型枚举
            harness_class: Harness 类（继承自 BaseHarness）

        Raises:
            TypeError: 如果 harness_class 不是 BaseHarness 的子类
        """
        if not issubclass(harness_class, BaseHarness):
            raise TypeError(
                f"Harness class must inherit from BaseHarness, "
                f"got {harness_class.__name__}"
            )
        cls._registry[harness_type] = harness_class

    @classmethod
    def create(
        cls,
        harness_type: HarnessType,
        config: Optional[dict] = None
    ) -> BaseHarness:
        """
        创建 Harness 实例

        Args:
            harness_type: Harness 类型
            config: 可选的配置字典

        Returns:
            BaseHarness: Harness 实例

        Raises:
            HarnessInitError: 如果 Harness 类型未注册
        """
        harness_class = cls._registry.get(harness_type)
        if not harness_class:
            registered_types = [ht.value for ht in cls._registry.keys()]
            raise HarnessInitError(
                f"Unknown harness type: {harness_type.value}. "
                f"Registered types: {registered_types}"
            )

        # 构建配置对象
        config_dict = config or {}
        harness_config = HarnessConfig(
            harness_type=harness_type,
            **config_dict
        )

        return harness_class(harness_config)

    @classmethod
    def unregister(cls, harness_type: HarnessType):
        """
        注销 Harness 类型

        Args:
            harness_type: 要注销的 Harness 类型
        """
        cls._registry.pop(harness_type, None)

    @classmethod
    def get_registered_types(cls) -> list[HarnessType]:
        """
        获取所有已注册的 Harness 类型

        Returns:
            list[HarnessType]: 已注册的类型列表
        """
        return list(cls._registry.keys())

    @classmethod
    def is_registered(cls, harness_type: HarnessType) -> bool:
        """
        检查 Harness 类型是否已注册

        Args:
            harness_type: Harness 类型

        Returns:
            bool: True 如果已注册
        """
        return harness_type in cls._registry

    @classmethod
    def clear_registry(cls):
        """
        清空注册表

        主要用于测试。
        """
        cls._registry.clear()
