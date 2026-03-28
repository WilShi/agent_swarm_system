"""
Multi-Harness Agent Swarm - 系统主入口

提供 Agent Swarm 系统的主要功能，包括任务分类、Harness 选择和任务执行。
"""
import asyncio
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from src.classifier import TaskClassifier
from src.harness import HarnessFactory
from src.core.types import Task, TaskResult, ClassificationResult


class MultiHarnessAgentSwarm:
    """
    Multi-Harness Agent Swarm 主类

    协调以下组件完成用户请求处理：
    1. TaskClassifier - 任务分类
    2. HarnessFactory - Harness 创建
    3. BaseHarness - 任务执行
    """

    def __init__(self):
        """初始化 Multi-Harness Agent Swarm 系统"""
        self.classifier = TaskClassifier()
        self._active_harnesses: Dict[str, Any] = {}

    async def process_request(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        处理用户请求

        完整的处理流程：
        1. 分类任务
        2. 创建 Harness
        3. 执行任务
        4. 返回结果

        Args:
            user_input: 用户输入文本
            context: 可选的上下文信息

        Returns:
            Dict: 包含任务结果的字典
        """
        context = context or {}

        try:
            # 1. 分类任务
            classification = await self.classifier.classify(user_input, context)

            # 2. 创建 Harness
            harness = HarnessFactory.create(
                classification.harness_type,
                config=classification.requirements
            )

            # 3. 创建任务
            task = Task(
                task_id=str(uuid.uuid4()),
                description=user_input,
                task_type=classification.task_type,
                harness_type=classification.harness_type,
                requirements=classification.requirements,
                metadata={
                    "classification": classification,
                    "context": context,
                    "created_at": datetime.now().isoformat()
                }
            )

            # 4. 执行任务
            result = await harness.run(task)

            # 5. 清理 Harness
            await harness.cleanup()

            return {
                "success": True,
                "task_id": task.task_id,
                "harness_type": classification.harness_type.value,
                "task_type": classification.task_type.value,
                "result": result,
                "classification": classification
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "user_input": user_input
            }

    async def process_with_confirmation(
        self,
        user_input: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        处理用户请求（带确认流程）

        在需要时会返回确认请求。

        Args:
            user_input: 用户输入文本
            context: 可选的上下文信息

        Returns:
            Dict: 包含任务结果或确认请求的字典
        """
        context = context or {}

        # 1. 分类并检查是否需要确认
        classification, confirmation = await self.classifier.classify_with_confirmation(
            user_input, context
        )

        # 2. 如果需要确认，返回确认请求
        if confirmation:
            return {
                "success": False,
                "needs_confirmation": True,
                "confirmation": confirmation,
                "classification": classification
            }

        # 3. 不需要确认，直接处理
        return await self.process_request(user_input, context)

    async def batch_process(
        self,
        inputs: list[str],
        context: Dict[str, Any] = None
    ) -> list[Dict[str, Any]]:
        """
        批量处理多个请求

        Args:
            inputs: 用户输入列表
            context: 可选的上下文信息

        Returns:
            list[Dict]: 结果列表
        """
        results = []
        for user_input in inputs:
            result = await self.process_request(user_input, context)
            results.append(result)
        return results

    def get_classifier(self) -> TaskClassifier:
        """
        获取任务分类器

        Returns:
            TaskClassifier: 分类器实例
        """
        return self.classifier


async def main():
    """
    主函数 - 示例用法

    演示如何使用 MultiHarnessAgentSwarm 处理任务。
    """
    print("=" * 60)
    print("Multi-Harness Agent Swarm")
    print("=" * 60)

    # 创建系统实例
    system = MultiHarnessAgentSwarm()

    # 示例任务列表
    example_tasks = [
        "分析这份代码的性能问题",
        "帮我调试这个 Python 错误",
        "研究一下最新的机器学习论文",
        "执行这个自动化脚本",
        "写一个简单的 Hello World 程序"
    ]

    print("\n处理示例任务:\n")

    for i, task_input in enumerate(example_tasks, 1):
        print(f"[{i}] 输入: {task_input}")

        try:
            result = await system.process_request(task_input)

            if result["success"]:
                print(f"    任务ID: {result['task_id']}")
                print(f"    Harness: {result['harness_type']}")
                print(f"    任务类型: {result['task_type']}")
                print(f"    状态: {result['result'].status}")
                if result['result'].output:
                    print(f"    输出: {result['result'].output.get('message', 'N/A')}")
            else:
                print(f"    错误: {result.get('error', 'Unknown error')}")

        except Exception as e:
            print(f"    异常: {e}")

        print()

    print("=" * 60)
    print("处理完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
