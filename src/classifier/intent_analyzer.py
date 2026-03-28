"""
意图分析模块
使用 LLM 分析用户输入的意图
"""
import json
from typing import Dict, Any, List
from src.core.types import IntentAnalysis
from src.core.llm_client import chat_completion


class IntentAnalyzer:
    """意图分析器"""

    SYSTEM_PROMPT = """你是一个意图分析专家。你的任务是分析用户的输入，提取出主要意图、次要意图、关键实体、情感倾向和紧急程度。

请以JSON格式返回分析结果，格式如下：
{
    "primary_intent": "主要意图描述",
    "secondary_intents": ["次要意图1", "次要意图2"],
    "entities": {
        "entity_type": "entity_value"
    },
    "sentiment": "positive|negative|neutral",
    "urgency": "low|normal|high|urgent"
}

分析指南：
1. primary_intent: 用户最核心的请求或目的
2. secondary_intents: 相关的次要目的或隐含需求
3. entities: 提取关键实体，如文件名、函数名、代码片段、技术栈等
4. sentiment: 用户情感倾向（积极、消极、中性）
5. urgency: 紧急程度（低、普通、高、紧急）

只返回JSON，不要有其他文字说明。"""

    async def analyze(self, user_input: str, context: Dict[str, Any] = None) -> IntentAnalysis:
        """
        分析用户输入的意图

        Args:
            user_input: 用户输入文本
            context: 可选的上下文信息

        Returns:
            IntentAnalysis 对象
        """
        # 构建用户消息
        user_message = f"请分析以下用户输入：\n\n{user_input}"

        if context:
            context_str = json.dumps(context, ensure_ascii=False, indent=2)
            user_message += f"\n\n上下文信息：\n{context_str}"

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]

        try:
            # 调用 LLM 进行分析
            response = await chat_completion(messages, temperature=0.3, max_tokens=1000)

            # 解析 JSON 响应
            # 尝试提取 JSON 部分（LLM 可能会添加 markdown 代码块）
            json_str = self._extract_json(response)
            result = json.loads(json_str)

            return IntentAnalysis(
                primary_intent=result.get("primary_intent", ""),
                secondary_intents=result.get("secondary_intents", []),
                entities=result.get("entities", {}),
                sentiment=result.get("sentiment", "neutral"),
                urgency=result.get("urgency", "normal")
            )

        except json.JSONDecodeError as e:
            # JSON 解析失败，返回基本分析结果
            return IntentAnalysis(
                primary_intent=user_input[:100],
                secondary_intents=[],
                entities={},
                sentiment="neutral",
                urgency="normal"
            )
        except Exception as e:
            # 其他错误，返回默认分析结果
            return IntentAnalysis(
                primary_intent=user_input[:100],
                secondary_intents=[],
                entities={},
                sentiment="neutral",
                urgency="normal"
            )

    def _extract_json(self, text: str) -> str:
        """
        从文本中提取 JSON 部分

        Args:
            text: 可能包含 JSON 的文本

        Returns:
            提取的 JSON 字符串
        """
        text = text.strip()

        # 检查是否有 markdown 代码块
        if text.startswith("```"):
            # 提取代码块内容
            lines = text.split("\n")
            # 移除第一行（```json 或 ```）
            if lines[0].startswith("```"):
                lines = lines[1:]
            # 移除最后一行（```）
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        return text

    async def analyze_batch(self, inputs: List[str]) -> List[IntentAnalysis]:
        """
        批量分析多个用户输入

        Args:
            inputs: 用户输入列表

        Returns:
            IntentAnalysis 列表
        """
        results = []
        for user_input in inputs:
            result = await self.analyze(user_input)
            results.append(result)
        return results
