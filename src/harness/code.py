"""
Code Harness - 代码生成、重构和优化

集成监控系统和 Kimi K2.5 (DashScope) 进行代码相关任务处理。
"""
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List

from src.core.types import (
    Task, TaskResult, HarnessConfig, HarnessType, TaskStatus
)
from src.core.llm_client import chat_completion
from src.core.config import get_config, LLMConfig
from src.harness.base import BaseHarness
from src.harness.factory import HarnessFactory
from src.monitoring.task_monitor import TaskMonitor, TaskStage


class CodeHarness(BaseHarness):
    """代码 Harness - 专门处理代码相关任务

    支持以下功能：
    1. 代码生成（函数、类、模块）
    2. 代码重构（重命名、提取、内联）
    3. 代码优化（性能、可读性）
    4. 代码审查（分析、建议改进）

    使用 Kimi K2.5 (通过 DashScope) 进行代码生成。
    """

    SYSTEM_PROMPT = """你是一个专业的代码助手。根据用户的需求：
1. 生成高质量、可维护的代码
2. 提供清晰的注释和文档
3. 遵循最佳实践和设计模式
4. 考虑错误处理和边界情况

请根据任务类型生成合适的代码。"""

    REFACTOR_PROMPT = """你是一个专业的代码重构专家。请分析以下代码并提供重构建议：
1. 改进代码结构和可读性
2. 应用设计模式和最佳实践
3. 消除重复代码
4. 优化命名和注释

请提供重构后的代码和重构说明。"""

    OPTIMIZE_PROMPT = """你是一个专业的代码优化专家。请分析以下代码并提供优化建议：
1. 提高执行性能
2. 减少内存使用
3. 优化算法复杂度
4. 改进资源管理

请提供优化后的代码和优化说明。"""

    REVIEW_PROMPT = """你是一个专业的代码审查专家。请审查以下代码并提供反馈：
1. 代码质量和可维护性
2. 潜在的错误和安全问题
3. 是否符合最佳实践
4. 测试覆盖情况

请提供详细的审查报告和改进建议。"""

    def __init__(self, config: HarnessConfig):
        super().__init__(config)
        self.language = config.custom_params.get("language", "python")
        self.style_guide = config.custom_params.get("style_guide", "pep8")
        self.enable_monitoring = config.custom_params.get("enable_monitoring", True)
        self.llm_config = config.custom_params.get("llm_config", None)

        # 监控器
        self.task_monitor: Optional[TaskMonitor] = None

    async def initialize(self):
        """初始化 Code Harness"""
        await super().initialize()

        # 创建监控器
        if self.enable_monitoring:
            self.task_monitor = TaskMonitor()

        self._initialized = True

    def _get_llm_config(self) -> Optional[LLMConfig]:
        """获取 LLM 配置

        优先使用自定义配置，否则使用 DashScope 配置 (Kimi K2.5)
        """
        if self.llm_config:
            return self.llm_config

        # 使用 DashScope 配置 (Kimi K2.5)
        config = get_config()
        return config.get_llm_config("dashscope")

    async def execute(self, task: Task) -> TaskResult:
        """执行代码任务

        根据任务描述自动识别任务类型并执行相应的处理。
        """
        start_time = datetime.now()

        try:
            # 更新任务状态
            task.status = TaskStatus.IN_PROGRESS

            # 在监控器中注册任务
            if self.task_monitor:
                self.task_monitor.register_task(
                    task.task_id,
                    task.description,
                    task.task_type.value if task.task_type else "code"
                )
                self.task_monitor.update_stage(task.task_id, TaskStage.EXECUTING)

            # 分析任务类型（生成/重构/优化/审查）
            code_task_type = self._analyze_code_task(task.description)

            # 根据任务类型执行
            if code_task_type == "generate":
                result = await self._generate_code(task)
            elif code_task_type == "refactor":
                result = await self._refactor_code(task)
            elif code_task_type == "optimize":
                result = await self._optimize_code(task)
            elif code_task_type == "review":
                result = await self._review_code(task)
            else:
                result = await self._general_code_help(task)

            # 更新监控器状态
            if self.task_monitor:
                if result.status == TaskStatus.COMPLETED.value:
                    self.task_monitor.update_stage(task.task_id, TaskStage.COMPLETED)
                else:
                    self.task_monitor.update_stage(task.task_id, TaskStage.FAILED)

            return result

        except Exception as e:
            task.status = TaskStatus.FAILED
            if self.task_monitor and task.task_id:
                self.task_monitor.update_stage(task.task_id, TaskStage.FAILED)

            execution_time = (datetime.now() - start_time).total_seconds()
            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.FAILED.value,
                output=None,
                quality_score=0.0,
                execution_time=execution_time,
                logs=[f"Code task {task.task_id} failed"],
                errors=[str(e)],
                metadata={"harness_type": self.harness_type.value}
            )

    def _analyze_code_task(self, description: str) -> str:
        """分析代码任务类型

        通过关键词匹配识别任务类型。

        Args:
            description: 任务描述

        Returns:
            任务类型: generate, refactor, optimize, review, general
        """
        description_lower = description.lower()

        # 生成相关关键词（避免与 review 关键词冲突）
        generate_keywords = ["生成", "generate", "write", "实现", "implement",
                            "编写", "创建", "开发", "write a", "create a"]

        # 重构相关关键词
        refactor_keywords = ["重构", "refactor", "restructure", "rewrite",
                            "重组", "重新组织", "整理"]

        # 优化相关关键词
        optimize_keywords = ["优化", "optimize", "performance", "improve",
                            "提速", "加速", "性能", "效率"]

        # 审查相关关键词
        review_keywords = ["审查", "review", "检查", "check", "analyze",
                          "分析", "评估", "evaluate"]

        if any(kw in description_lower for kw in generate_keywords):
            return "generate"
        elif any(kw in description_lower for kw in refactor_keywords):
            return "refactor"
        elif any(kw in description_lower for kw in optimize_keywords):
            return "optimize"
        elif any(kw in description_lower for kw in review_keywords):
            return "review"

        return "general"

    def _extract_code_from_task(self, task: Task) -> Optional[str]:
        """从任务中提取代码

        从 task.requirements 或 task.metadata 中提取代码内容。

        Args:
            task: 任务对象

        Returns:
            代码字符串，如果没有则返回 None
        """
        # 从 requirements 中查找
        if "code" in task.requirements:
            return task.requirements["code"]
        if "source_code" in task.requirements:
            return task.requirements["source_code"]

        # 从 metadata 中查找
        if task.metadata:
            if "code" in task.metadata:
                return task.metadata["code"]
            if "source_code" in task.metadata:
                return task.metadata["source_code"]

        return None

    def _extract_language_from_task(self, task: Task) -> str:
        """从任务中提取编程语言

        Args:
            task: 任务对象

        Returns:
            编程语言字符串
        """
        # 从 requirements 中查找
        if "language" in task.requirements:
            return task.requirements["language"]

        # 从 metadata 中查找
        if task.metadata and "language" in task.metadata:
            return task.metadata["language"]

        return self.language

    async def _generate_code(self, task: Task) -> TaskResult:
        """生成代码

        使用 LLM 根据任务描述生成代码。

        Args:
            task: 任务对象

        Returns:
            TaskResult 包含生成的代码
        """
        start_time = datetime.now()
        language = self._extract_language_from_task(task)

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"请生成以下代码：\n\n{task.description}\n\n"
                                        f"编程语言: {language}\n"
                                        f"代码风格: {self.style_guide}\n\n"
                                        f"请只输出代码，不需要额外的解释文字。"}
        ]

        try:
            llm_config = self._get_llm_config()
            response = await chat_completion(
                messages,
                config=llm_config,
                temperature=0.3,
                max_tokens=4000
            )

            execution_time = (datetime.now() - start_time).total_seconds()

            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.COMPLETED.value,
                output={
                    "code": response,
                    "language": language,
                    "task_type": "code_generation",
                    "style_guide": self.style_guide
                },
                quality_score=0.9,
                execution_time=execution_time,
                tokens_used=len(response) // 4,  # 粗略估计
                logs=["Code generated successfully"],
                metadata={
                    "harness_type": self.harness_type.value,
                    "task_subtype": "generate",
                    "language": language
                }
            )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.FAILED.value,
                output=None,
                quality_score=0.0,
                execution_time=execution_time,
                logs=["Code generation failed"],
                errors=[str(e)],
                metadata={"harness_type": self.harness_type.value}
            )

    async def _refactor_code(self, task: Task) -> TaskResult:
        """重构代码

        分析代码并提供重构建议。

        Args:
            task: 任务对象

        Returns:
            TaskResult 包含重构后的代码和建议
        """
        start_time = datetime.now()
        code = self._extract_code_from_task(task)
        language = self._extract_language_from_task(task)

        if not code:
            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.FAILED.value,
                output=None,
                quality_score=0.0,
                execution_time=(datetime.now() - start_time).total_seconds(),
                errors=["No code provided for refactoring. Please include code in requirements or metadata."]
            )

        messages = [
            {"role": "system", "content": self.REFACTOR_PROMPT},
            {"role": "user", "content": f"请重构以下 {language} 代码：\n\n```{language}\n{code}\n```\n\n"
                                        f"代码风格: {self.style_guide}\n\n"
                                        f"请提供：\n1. 重构后的完整代码\n2. 重构说明（列出主要改动）"}
        ]

        try:
            llm_config = self._get_llm_config()
            response = await chat_completion(
                messages,
                config=llm_config,
                temperature=0.3,
                max_tokens=4000
            )

            execution_time = (datetime.now() - start_time).total_seconds()

            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.COMPLETED.value,
                output={
                    "refactored_code": response,
                    "original_code": code,
                    "language": language,
                    "task_type": "code_refactoring"
                },
                quality_score=0.85,
                execution_time=execution_time,
                tokens_used=len(response) // 4,
                logs=["Code refactored successfully"],
                metadata={
                    "harness_type": self.harness_type.value,
                    "task_subtype": "refactor",
                    "language": language
                }
            )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.FAILED.value,
                output=None,
                quality_score=0.0,
                execution_time=execution_time,
                logs=["Code refactoring failed"],
                errors=[str(e)],
                metadata={"harness_type": self.harness_type.value}
            )

    async def _optimize_code(self, task: Task) -> TaskResult:
        """优化代码

        分析代码性能并提供优化建议。

        Args:
            task: 任务对象

        Returns:
            TaskResult 包含优化后的代码和建议
        """
        start_time = datetime.now()
        code = self._extract_code_from_task(task)
        language = self._extract_language_from_task(task)

        if not code:
            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.FAILED.value,
                output=None,
                quality_score=0.0,
                execution_time=(datetime.now() - start_time).total_seconds(),
                errors=["No code provided for optimization. Please include code in requirements or metadata."]
            )

        messages = [
            {"role": "system", "content": self.OPTIMIZE_PROMPT},
            {"role": "user", "content": f"请优化以下 {language} 代码：\n\n```{language}\n{code}\n```\n\n"
                                        f"请提供：\n1. 优化后的完整代码\n2. 优化说明（列出性能改进点）"}
        ]

        try:
            llm_config = self._get_llm_config()
            response = await chat_completion(
                messages,
                config=llm_config,
                temperature=0.3,
                max_tokens=4000
            )

            execution_time = (datetime.now() - start_time).total_seconds()

            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.COMPLETED.value,
                output={
                    "optimized_code": response,
                    "original_code": code,
                    "language": language,
                    "task_type": "code_optimization"
                },
                quality_score=0.85,
                execution_time=execution_time,
                tokens_used=len(response) // 4,
                logs=["Code optimized successfully"],
                metadata={
                    "harness_type": self.harness_type.value,
                    "task_subtype": "optimize",
                    "language": language
                }
            )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.FAILED.value,
                output=None,
                quality_score=0.0,
                execution_time=execution_time,
                logs=["Code optimization failed"],
                errors=[str(e)],
                metadata={"harness_type": self.harness_type.value}
            )

    async def _review_code(self, task: Task) -> TaskResult:
        """审查代码

        分析代码质量并提供审查报告。

        Args:
            task: 任务对象

        Returns:
            TaskResult 包含审查报告
        """
        start_time = datetime.now()
        code = self._extract_code_from_task(task)
        language = self._extract_language_from_task(task)

        if not code:
            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.FAILED.value,
                output=None,
                quality_score=0.0,
                execution_time=(datetime.now() - start_time).total_seconds(),
                errors=["No code provided for review. Please include code in requirements or metadata."]
            )

        messages = [
            {"role": "system", "content": self.REVIEW_PROMPT},
            {"role": "user", "content": f"请审查以下 {language} 代码：\n\n```{language}\n{code}\n```\n\n"
                                        f"代码风格标准: {self.style_guide}\n\n"
                                        f"请提供详细的审查报告，包括：\n"
                                        f"1. 代码质量评分（1-10）\n"
                                        f"2. 主要问题列表\n"
                                        f"3. 改进建议\n"
                                        f"4. 安全风险（如有）"}
        ]

        try:
            llm_config = self._get_llm_config()
            response = await chat_completion(
                messages,
                config=llm_config,
                temperature=0.3,
                max_tokens=4000
            )

            execution_time = (datetime.now() - start_time).total_seconds()

            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.COMPLETED.value,
                output={
                    "review_report": response,
                    "original_code": code,
                    "language": language,
                    "task_type": "code_review"
                },
                quality_score=0.9,
                execution_time=execution_time,
                tokens_used=len(response) // 4,
                logs=["Code reviewed successfully"],
                metadata={
                    "harness_type": self.harness_type.value,
                    "task_subtype": "review",
                    "language": language
                }
            )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.FAILED.value,
                output=None,
                quality_score=0.0,
                execution_time=execution_time,
                logs=["Code review failed"],
                errors=[str(e)],
                metadata={"harness_type": self.harness_type.value}
            )

    async def _general_code_help(self, task: Task) -> TaskResult:
        """通用代码帮助

        处理无法明确分类的代码相关任务。

        Args:
            task: 任务对象

        Returns:
            TaskResult 包含帮助内容
        """
        start_time = datetime.now()
        language = self._extract_language_from_task(task)
        code = self._extract_code_from_task(task)

        user_content = f"请帮助解决以下代码问题：\n\n{task.description}\n\n"
        if code:
            user_content += f"相关代码 ({language}):\n```{language}\n{code}\n```\n\n"
        user_content += f"编程语言: {language}\n代码风格: {self.style_guide}"

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ]

        try:
            llm_config = self._get_llm_config()
            response = await chat_completion(
                messages,
                config=llm_config,
                temperature=0.3,
                max_tokens=4000
            )

            execution_time = (datetime.now() - start_time).total_seconds()

            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.COMPLETED.value,
                output={
                    "response": response,
                    "code": code,
                    "language": language,
                    "task_type": "code_help"
                },
                quality_score=0.8,
                execution_time=execution_time,
                tokens_used=len(response) // 4,
                logs=["Code help provided successfully"],
                metadata={
                    "harness_type": self.harness_type.value,
                    "task_subtype": "general",
                    "language": language
                }
            )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.FAILED.value,
                output=None,
                quality_score=0.0,
                execution_time=execution_time,
                logs=["Code help failed"],
                errors=[str(e)],
                metadata={"harness_type": self.harness_type.value}
            )

    async def cleanup(self):
        """清理资源"""
        self.task_monitor = None
        self._initialized = False
        await super().cleanup()


# 注册到工厂
HarnessFactory.register(HarnessType.CODE, CodeHarness)
