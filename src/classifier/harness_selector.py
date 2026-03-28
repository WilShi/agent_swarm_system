"""
Harness 选择器模块
基于意图分析选择最适合的 Harness 类型
"""
import json
from typing import Dict, Any, Tuple, List
from src.core.types import HarnessType, TaskType, IntentAnalysis
from src.core.llm_client import chat_completion


class HarnessSelector:
    """Harness 选择器"""

    SYSTEM_PROMPT = """你是一个任务分类专家。你的任务是根据用户的意图分析结果，选择最适合的 Harness 类型和任务类型。

可用的 Harness 类型：
- claude_code: 使用 Claude Code 工具执行，适合代码编辑、文件操作、项目导航等
- code: 代码生成、重构、分析任务
- debug: 调试、错误诊断、问题排查
- test: 测试生成、测试执行、测试分析
- execution: 通用任务执行
- research: 研究、信息收集、分析任务

可用的任务类型：
- analysis: 分析类任务
- generation: 生成类任务
- code: 代码相关任务
- research: 研究类任务
- debug: 调试类任务
- test: 测试类任务
- automation: 自动化任务
- general: 通用任务

请以JSON格式返回结果，格式如下：
{
    "harness_type": "选择的 harness 类型",
    "task_type": "选择的 task 类型",
    "confidence": 0.85,
    "reasoning": "选择理由的详细说明",
    "sub_tasks": ["子任务1", "子任务2"],
    "requirements": {"key": "value"},
    "keywords": ["关键词1", "关键词2"],
    "estimated_complexity": "low|medium|high",
    "estimated_duration": 120
}

confidence 是 0-1 之间的浮点数，表示你对选择的信心程度。
estimated_duration 是预估执行时间（秒）。

只返回JSON，不要有其他文字说明。"""

    # 关键词映射表，用于预筛选
    KEYWORD_MAP = {
        HarnessType.CODE: [
            "代码", "函数", "class", "code", "function", "编写", "实现",
            "重构", "refactor", "optimize", "优化", "class", "module",
            "import", "def", "async", "await"
        ],
        HarnessType.DEBUG: [
            "bug", "错误", "error", "fix", "debug", "调试", "排查",
            "问题", "issue", "crash", "异常", "exception", "失败",
            "fail", "broken", "not working"
        ],
        HarnessType.TEST: [
            "测试", "test", "unittest", "pytest", "验证", "verify",
            "assert", "mock", "coverage", "覆盖率", "test case",
            "单元测试", "集成测试"
        ],
        HarnessType.EXECUTION: [
            "执行", "运行", "run", "execute", "启动", "start",
            "停止", "stop", "部署", "deploy", "build", "构建",
            "install", "安装", "update", "更新"
        ],
        HarnessType.RESEARCH: [
            "研究", "research", "分析", "analyze", "调查", "investigate",
            "探索", "explore", "查找", "search", "了解", "understand",
            "文档", "documentation", "学习", "learn"
        ],
        HarnessType.CLAUDE_CODE: [
            "编辑", "edit", "文件", "file", "目录", "folder", "导航",
            "navigate", "搜索", "search", "替换", "replace", "创建",
            "create", "删除", "delete", "移动", "move"
        ]
    }

    # 任务类型关键词映射
    TASK_KEYWORD_MAP = {
        TaskType.CODE: ["代码", "code", "编写", "实现", "function", "class"],
        TaskType.DEBUG: ["debug", "调试", "bug", "错误", "修复", "fix"],
        TaskType.TEST: ["测试", "test", "验证", "verify", "assert"],
        TaskType.ANALYSIS: ["分析", "analyze", "研究", "research", "调查"],
        TaskType.GENERATION: ["生成", "generate", "创建", "create", "编写"],
        TaskType.AUTOMATION: ["自动", "auto", "脚本", "script", "批量"],
        TaskType.RESEARCH: ["研究", "research", "查找", "search", "了解"],
        TaskType.GENERAL: ["通用", "general", "帮助", "help", "助手"]
    }

    async def select(
        self,
        user_input: str,
        intent: IntentAnalysis
    ) -> Tuple[HarnessType, TaskType, float, str, List[str], Dict[str, Any], List[str], str, int]:
        """
        选择最适合的 Harness 和任务类型

        Args:
            user_input: 原始用户输入
            intent: 意图分析结果

        Returns:
            Tuple: (harness_type, task_type, confidence, reasoning, sub_tasks,
                   requirements, keywords, estimated_complexity, estimated_duration)
        """
        # 1. 关键词预筛选
        keyword_hints = self._keyword_pre_screening(user_input, intent)

        # 2. 使用 LLM 进行精细分类
        llm_result = await self._llm_classify(user_input, intent, keyword_hints)

        return llm_result

    def _keyword_pre_screening(
        self,
        user_input: str,
        intent: IntentAnalysis
    ) -> Dict[str, List[str]]:
        """
        基于关键词进行预筛选

        Args:
            user_input: 用户输入
            intent: 意图分析

        Returns:
            关键词提示字典
        """
        user_input_lower = user_input.lower()
        primary_intent_lower = intent.primary_intent.lower()

        matched_harnesses = {}
        matched_tasks = {}

        # 匹配 Harness 关键词
        for harness, keywords in self.KEYWORD_MAP.items():
            matches = []
            for keyword in keywords:
                if keyword.lower() in user_input_lower or keyword.lower() in primary_intent_lower:
                    matches.append(keyword)
            if matches:
                matched_harnesses[harness.value] = matches

        # 匹配任务类型关键词
        for task, keywords in self.TASK_KEYWORD_MAP.items():
            matches = []
            for keyword in keywords:
                if keyword.lower() in user_input_lower or keyword.lower() in primary_intent_lower:
                    matches.append(keyword)
            if matches:
                matched_tasks[task.value] = matches

        return {
            "harness_hints": matched_harnesses,
            "task_hints": matched_tasks
        }

    async def _llm_classify(
        self,
        user_input: str,
        intent: IntentAnalysis,
        keyword_hints: Dict[str, Any]
    ) -> Tuple[HarnessType, TaskType, float, str, List[str], Dict[str, Any], List[str], str, int]:
        """
        使用 LLM 进行分类

        Args:
            user_input: 用户输入
            intent: 意图分析
            keyword_hints: 关键词提示

        Returns:
            分类结果元组
        """
        # 构建分析数据
        analysis_data = {
            "user_input": user_input,
            "primary_intent": intent.primary_intent,
            "secondary_intents": intent.secondary_intents,
            "entities": intent.entities,
            "sentiment": intent.sentiment,
            "urgency": intent.urgency,
            "keyword_hints": keyword_hints
        }

        user_message = f"请根据以下分析数据进行分类：\n\n```json\n{json.dumps(analysis_data, ensure_ascii=False, indent=2)}\n```"

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]

        try:
            response = await chat_completion(messages, temperature=0.3, max_tokens=1500)

            # 解析 JSON
            json_str = self._extract_json(response)
            result = json.loads(json_str)

            # 解析 harness_type
            harness_value = result.get("harness_type", "execution").lower()
            harness_type = self._parse_harness_type(harness_value)

            # 解析 task_type
            task_value = result.get("task_type", "general").lower()
            task_type = self._parse_task_type(task_value)

            return (
                harness_type,
                task_type,
                float(result.get("confidence", 0.7)),
                result.get("reasoning", ""),
                result.get("sub_tasks", []),
                result.get("requirements", {}),
                result.get("keywords", []),
                result.get("estimated_complexity", "medium"),
                int(result.get("estimated_duration", 60))
            )

        except Exception as e:
            # 出错时返回默认值
            return self._get_default_result()

    def _parse_harness_type(self, value: str) -> HarnessType:
        """解析 HarnessType"""
        value = value.lower().replace(" ", "_")

        harness_map = {
            "claude_code": HarnessType.CLAUDE_CODE,
            "code": HarnessType.CODE,
            "debug": HarnessType.DEBUG,
            "test": HarnessType.TEST,
            "execution": HarnessType.EXECUTION,
            "research": HarnessType.RESEARCH
        }

        return harness_map.get(value, HarnessType.EXECUTION)

    def _parse_task_type(self, value: str) -> TaskType:
        """解析 TaskType"""
        value = value.lower().replace(" ", "_")

        task_map = {
            "analysis": TaskType.ANALYSIS,
            "generation": TaskType.GENERATION,
            "code": TaskType.CODE,
            "research": TaskType.RESEARCH,
            "debug": TaskType.DEBUG,
            "test": TaskType.TEST,
            "automation": TaskType.AUTOMATION,
            "general": TaskType.GENERAL
        }

        return task_map.get(value, TaskType.GENERAL)

    def _extract_json(self, text: str) -> str:
        """从文本中提取 JSON"""
        text = text.strip()

        if text.startswith("```"):
            lines = text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        return text

    def _get_default_result(self) -> Tuple:
        """获取默认结果"""
        return (
            HarnessType.EXECUTION,
            TaskType.GENERAL,
            0.5,
            "使用默认配置",
            [],
            {},
            [],
            "medium",
            60
        )

    def get_harness_recommendations(
        self,
        intent: IntentAnalysis
    ) -> List[Tuple[HarnessType, float]]:
        """
        获取 Harness 推荐列表（按匹配度排序）

        Args:
            intent: 意图分析

        Returns:
            Harness 推荐列表
        """
        recommendations = []
        primary = intent.primary_intent.lower()

        for harness, keywords in self.KEYWORD_MAP.items():
            score = 0.0
            for keyword in keywords:
                if keyword.lower() in primary:
                    score += 1.0
            if score > 0:
                recommendations.append((harness, score))

        # 按分数排序
        recommendations.sort(key=lambda x: x[1], reverse=True)
        return recommendations
