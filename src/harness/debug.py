"""
Debug Harness - 错误诊断和调试

集成监控系统和 Kimi K2.5 (DashScope) 进行错误诊断和修复。
"""
import re
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


class DebugHarness(BaseHarness):
    """调试 Harness - 专门处理错误诊断和修复任务

    支持以下功能：
    1. 错误诊断 - 分析错误消息和堆栈跟踪
    2. 根本原因分析 - 找出问题的源头
    3. 修复建议 - 提供具体的代码修复方案
    4. 自动修复 - 应用修复到代码（可选）

    使用 Kimi K2.5 (通过 DashScope) 进行分析。
    """

    SYSTEM_PROMPT = """你是一个专业的调试助手。你的任务是：
1. 分析错误信息和堆栈跟踪
2. 找出问题的根本原因
3. 提供具体的修复建议
4. 生成修复后的代码

请提供详细的诊断过程和修复方案。"""

    DIAGNOSIS_PROMPT = """你是一个专业的错误诊断专家。请分析以下错误信息并提供诊断：
1. 错误类型（如 SyntaxError、TypeError、IndexError 等）
2. 根本原因分析
3. 发生位置（文件、行号、函数）
4. 可能的触发条件

请提供详细的诊断报告。"""

    FIX_PROMPT = """你是一个专业的代码修复专家。请根据诊断结果提供修复方案：
1. 修复后的完整代码
2. 修复说明（解释改动原因）
3. 预防措施（如何避免类似问题）

请确保修复后的代码是正确的、可运行的。"""

    VERIFICATION_PROMPT = """你是一个代码验证专家。请验证修复是否正确：
1. 检查修复是否解决了原问题
2. 检查是否引入了新的问题
3. 评估修复质量

请提供验证报告。"""

    def __init__(self, config: HarnessConfig):
        super().__init__(config)
        self.max_iterations = config.custom_params.get("max_iterations", 5)
        self.auto_fix = config.custom_params.get("auto_fix", True)
        self.enable_monitoring = config.custom_params.get("enable_monitoring", True)
        self.llm_config = config.custom_params.get("llm_config", None)

        # 监控器
        self.task_monitor: Optional[TaskMonitor] = None

    async def initialize(self):
        """初始化 Debug Harness"""
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
        """执行调试任务

        执行完整的调试流程：诊断 -> 修复建议 -> 应用修复 -> 验证
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
                    task.task_type.value if task.task_type else "debug"
                )
                self.task_monitor.update_stage(task.task_id, TaskStage.EXECUTING)

            # 1. 提取错误信息
            error_info = self._extract_error_info(task)

            if not error_info["error_message"] and not error_info["stack_trace"]:
                # 没有错误信息，尝试从描述中提取
                error_info["error_message"] = task.description

            # 2. 诊断错误
            diagnosis = await self._diagnose_error(error_info)

            # 3. 生成修复建议
            fix_suggestion = await self._suggest_fix(diagnosis, error_info)

            # 4. 如果需要，应用修复
            fix_result = None
            if self.auto_fix and fix_suggestion.get("can_fix"):
                fix_result = await self._apply_fix(fix_suggestion, error_info)

                # 5. 验证修复
                if fix_result and fix_result.get("fixed_code"):
                    verification = await self._verify_fix(
                        error_info, fix_result["fixed_code"], diagnosis
                    )
                    fix_result["verification"] = verification

            # 更新监控器状态
            if self.task_monitor:
                self.task_monitor.update_stage(task.task_id, TaskStage.COMPLETED)

            execution_time = (datetime.now() - start_time).total_seconds()

            # 构建结果
            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.COMPLETED.value,
                output={
                    "diagnosis": diagnosis,
                    "fix_suggestion": fix_suggestion,
                    "fix_result": fix_result,
                    "iterations": 1,
                    "error_info": error_info
                },
                quality_score=fix_suggestion.get("confidence", 0.85),
                execution_time=execution_time,
                tokens_used=0,  # 将在实际调用时统计
                logs=["Debug analysis completed"],
                metadata={
                    "harness_type": self.harness_type.value,
                    "task_subtype": "debug",
                    "auto_fix_applied": self.auto_fix and fix_suggestion.get("can_fix", False)
                }
            )

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
                logs=[f"Debug task {task.task_id} failed"],
                errors=[str(e)],
                metadata={"harness_type": self.harness_type.value}
            )

    def _extract_error_info(self, task: Task) -> Dict[str, Any]:
        """从任务中提取错误信息

        从 task.requirements 中提取错误相关的信息。

        Args:
            task: 任务对象

        Returns:
            包含错误信息的字典
        """
        error_info = {
            "error_message": "",
            "stack_trace": "",
            "code": "",
            "context": "",
            "language": "python"
        }

        # 从 requirements 中提取
        if "error" in task.requirements:
            error_info["error_message"] = task.requirements["error"]
        if "error_message" in task.requirements:
            error_info["error_message"] = task.requirements["error_message"]
        if "stack_trace" in task.requirements:
            error_info["stack_trace"] = task.requirements["stack_trace"]
        if "code" in task.requirements:
            error_info["code"] = task.requirements["code"]
        if "source_code" in task.requirements:
            error_info["code"] = task.requirements["source_code"]
        if "context" in task.requirements:
            error_info["context"] = task.requirements["context"]
        if "language" in task.requirements:
            error_info["language"] = task.requirements["language"]

        # 从 metadata 中提取（作为备选）
        if task.metadata:
            if not error_info["error_message"] and "error" in task.metadata:
                error_info["error_message"] = task.metadata["error"]
            if not error_info["stack_trace"] and "stack_trace" in task.metadata:
                error_info["stack_trace"] = task.metadata["stack_trace"]
            if not error_info["code"] and "code" in task.metadata:
                error_info["code"] = task.metadata["code"]
            if not error_info["code"] and "source_code" in task.metadata:
                error_info["code"] = task.metadata["source_code"]
            if not error_info["language"] and "language" in task.metadata:
                error_info["language"] = task.metadata["language"]

        return error_info

    def _parse_error_type(self, response: str) -> str:
        """从响应中解析错误类型

        Args:
            response: LLM 响应文本

        Returns:
            错误类型字符串
        """
        # 尝试匹配常见的错误类型
        error_patterns = [
            r"错误类型[:：]\s*(\w+Error)",
            r"Error Type[:：]\s*(\w+Error)",
            r"(\w+Error)\s*[:：]",
            r"`(\w+Error)`",
        ]

        for pattern in error_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                return match.group(1)

        return "UnknownError"

    def _parse_location(self, response: str) -> Dict[str, Any]:
        """从响应中解析错误位置

        Args:
            response: LLM 响应文本

        Returns:
            包含位置信息的字典
        """
        location = {
            "file": None,
            "line": None,
            "function": None
        }

        # 匹配文件路径
        file_patterns = [
            r"文件[:：]\s*([\w\./\\]+\.py)",
            r"File[:：]\s*[\"']?([\w\./\\]+\.[\w]+)[\"']?",
            r"[Ff]ile\s+[\"']?([\w\./\\]+\.[\w]+)[\"']?",
        ]

        for pattern in file_patterns:
            match = re.search(pattern, response)
            if match:
                location["file"] = match.group(1)
                break

        # 匹配行号
        line_patterns = [
            r"行[:：]\s*(\d+)",
            r"[Ll]ine[:：]\s*(\d+)",
            r"第\s*(\d+)\s*行",
            r"line\s+(\d+)",
        ]

        for pattern in line_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                location["line"] = int(match.group(1))
                break

        # 匹配函数名
        func_patterns = [
            r"函数[:：]\s*(\w+)",
            r"[Ff]unction[:：]\s*(\w+)",
            r"def\s+(\w+)",
            r"in\s+(\w+)\s*\(",
        ]

        for pattern in func_patterns:
            match = re.search(pattern, response)
            if match:
                location["function"] = match.group(1)
                break

        return location

    async def _diagnose_error(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """诊断错误

        使用 LLM 分析错误信息和堆栈跟踪。

        Args:
            error_info: 错误信息字典

        Returns:
            诊断结果字典
        """
        messages = [
            {"role": "system", "content": self.DIAGNOSIS_PROMPT},
            {"role": "user", "content": f"请诊断以下错误：\n\n"
                                        f"错误信息：{error_info['error_message']}\n\n"
                                        f"堆栈跟踪：\n{error_info['stack_trace']}\n\n"
                                        f"代码：\n```{error_info['language']}\n"
                                        f"{error_info['code']}\n```\n\n"
                                        f"上下文：{error_info['context']}\n\n"
                                        f"请提供：\n"
                                        f"1. 错误类型\n"
                                        f"2. 根本原因\n"
                                        f"3. 发生位置\n"
                                        f"4. 可能的触发条件"}
        ]

        try:
            llm_config = self._get_llm_config()
            response = await chat_completion(
                messages,
                config=llm_config,
                temperature=0.3,
                max_tokens=2000
            )

            return {
                "error_type": self._parse_error_type(response),
                "root_cause": response,
                "location": self._parse_location(response),
                "raw_response": response
            }

        except Exception as e:
            return {
                "error_type": "UnknownError",
                "root_cause": f"诊断失败: {str(e)}",
                "location": {},
                "raw_response": ""
            }

    async def _suggest_fix(self, diagnosis: Dict[str, Any],
                          error_info: Dict[str, Any]) -> Dict[str, Any]:
        """生成修复建议

        根据诊断结果生成具体的修复方案。

        Args:
            diagnosis: 诊断结果
            error_info: 错误信息

        Returns:
            修复建议字典
        """
        messages = [
            {"role": "system", "content": self.FIX_PROMPT},
            {"role": "user", "content": f"请为以下错误提供修复方案：\n\n"
                                        f"错误类型：{diagnosis['error_type']}\n\n"
                                        f"诊断结果：\n{diagnosis['root_cause']}\n\n"
                                        f"原始代码：\n```{error_info['language']}\n"
                                        f"{error_info['code']}\n```\n\n"
                                        f"请提供：\n"
                                        f"1. 修复后的完整代码\n"
                                        f"2. 修复说明\n"
                                        f"3. 预防措施"}
        ]

        try:
            llm_config = self._get_llm_config()
            response = await chat_completion(
                messages,
                config=llm_config,
                temperature=0.3,
                max_tokens=3000
            )

            # 从响应中提取代码块
            fixed_code = self._extract_code_from_response(response, error_info['language'])

            return {
                "can_fix": bool(fixed_code),
                "fixed_code": fixed_code,
                "explanation": response,
                "confidence": 0.85 if fixed_code else 0.5,
                "language": error_info['language']
            }

        except Exception as e:
            return {
                "can_fix": False,
                "fixed_code": None,
                "explanation": f"生成修复建议失败: {str(e)}",
                "confidence": 0.0,
                "language": error_info['language']
            }

    def _extract_code_from_response(self, response: str, language: str) -> Optional[str]:
        """从 LLM 响应中提取代码块

        Args:
            response: LLM 响应文本
            language: 编程语言

        Returns:
            提取的代码字符串，如果没有则返回 None
        """
        # 匹配代码块
        code_pattern = rf"```{language}\s*\n(.*?)\n```"
        match = re.search(code_pattern, response, re.DOTALL)
        if match:
            return match.group(1).strip()

        # 尝试通用代码块匹配
        generic_pattern = r"```\s*\n(.*?)\n```"
        match = re.search(generic_pattern, response, re.DOTALL)
        if match:
            return match.group(1).strip()

        # 如果没有代码块标记，返回整个响应
        return response.strip()

    async def _apply_fix(self, fix_suggestion: Dict[str, Any],
                        error_info: Dict[str, Any]) -> Dict[str, Any]:
        """应用修复

        Args:
            fix_suggestion: 修复建议
            error_info: 错误信息

        Returns:
            修复结果字典
        """
        fixed_code = fix_suggestion.get("fixed_code")

        if not fixed_code:
            return {
                "success": False,
                "message": "没有可应用的修复",
                "fixed_code": None
            }

        # 这里可以实现实际的文件写入逻辑
        # 目前只是返回修复后的代码
        return {
            "success": True,
            "message": "修复已生成",
            "fixed_code": fixed_code,
            "original_code": error_info["code"],
            "language": fix_suggestion.get("language", "python")
        }

    async def _verify_fix(self, error_info: Dict[str, Any],
                         fixed_code: str,
                         diagnosis: Dict[str, Any]) -> Dict[str, Any]:
        """验证修复

        使用 LLM 验证修复是否正确解决了问题。

        Args:
            error_info: 原始错误信息
            fixed_code: 修复后的代码
            diagnosis: 诊断结果

        Returns:
            验证结果字典
        """
        messages = [
            {"role": "system", "content": self.VERIFICATION_PROMPT},
            {"role": "user", "content": f"请验证以下修复是否正确：\n\n"
                                        f"原始错误：{error_info['error_message']}\n\n"
                                        f"错误类型：{diagnosis['error_type']}\n\n"
                                        f"修复后的代码：\n```{error_info['language']}\n"
                                        f"{fixed_code}\n```\n\n"
                                        f"请评估：\n"
                                        f"1. 修复是否解决了原问题\n"
                                        f"2. 是否引入了新的问题\n"
                                        f"3. 修复质量评分（1-10）"}
        ]

        try:
            llm_config = self._get_llm_config()
            response = await chat_completion(
                messages,
                config=llm_config,
                temperature=0.3,
                max_tokens=1500
            )

            # 从响应中提取评分
            score_match = re.search(r'(\d+)/10', response)
            score = int(score_match.group(1)) if score_match else 7

            return {
                "verified": score >= 7,
                "score": score,
                "feedback": response
            }

        except Exception as e:
            return {
                "verified": False,
                "score": 0,
                "feedback": f"验证失败: {str(e)}"
            }

    async def cleanup(self):
        """清理资源"""
        self.task_monitor = None
        self._initialized = False
        await super().cleanup()


# 注册到工厂
HarnessFactory.register(HarnessType.DEBUG, DebugHarness)
