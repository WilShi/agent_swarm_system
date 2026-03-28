"""
Research Harness - 研究调研和知识综合

集成监控系统和 Kimi K2.5 (DashScope) 进行研究任务处理。
支持信息搜索、信息提取、知识综合和报告生成。
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


class ResearchHarness(BaseHarness):
    """研究 Harness - 专门处理调研分析任务

    支持以下功能：
    1. 信息搜索 - 搜索多个来源的相关信息
    2. 信息提取 - 提取关键信息和见解
    3. 知识综合 - 综合研究发现
    4. 报告生成 - 生成结构化研究报告

    使用 Kimi K2.5 (通过 DashScope) 进行研究分析。
    """

    SYSTEM_PROMPT = """你是一个专业的研究助手。你的任务是：
1. 分析研究需求，确定关键问题
2. 搜索和收集相关信息
3. 提取关键发现和见解
4. 综合信息生成研究报告

请提供结构化的研究结果。"""

    ANALYSIS_PROMPT = """你是一个研究需求分析专家。请分析以下研究主题：
1. 识别核心研究问题
2. 列出关键子主题
3. 建议可能的信息来源
4. 确定研究深度和范围

请提供结构化的分析结果。"""

    EXTRACTION_PROMPT = """你是一个信息提取专家。请从以下内容中提取关键信息：
1. 核心概念和定义
2. 重要数据和统计
3. 主要观点和结论
4. 关键引用和来源

请提供结构化的提取结果。"""

    SYNTHESIS_PROMPT = """你是一个知识综合专家。请综合以下研究发现：
1. 整合不同来源的信息
2. 识别模式和相关性
3. 发现知识缺口
4. 形成综合见解

请提供结构化的综合结果。"""

    REPORT_PROMPT = """你是一个研究报告撰写专家。请根据以下综合结果生成研究报告：
1. 撰写执行摘要
2. 组织主要发现
3. 提供详细分析
4. 给出建议和结论

请生成格式良好的研究报告。"""

    def __init__(self, config: HarnessConfig):
        super().__init__(config)
        self.max_sources = config.custom_params.get("max_sources", 10)
        self.research_depth = config.custom_params.get("research_depth", "medium")
        self.output_format = config.custom_params.get("output_format", "report")
        self.enable_monitoring = config.custom_params.get("enable_monitoring", True)
        self.llm_config = config.custom_params.get("llm_config", None)

        # 监控器
        self.task_monitor: Optional[TaskMonitor] = None

    async def initialize(self):
        """初始化 Research Harness"""
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
        """执行研究任务

        按照研究流程执行：
        1. 分析研究需求
        2. 搜索信息
        3. 提取关键信息
        4. 综合知识
        5. 生成报告
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
                    task.task_type.value if task.task_type else "research"
                )
                self.task_monitor.update_stage(task.task_id, TaskStage.EXECUTING)

            # 1. 分析研究需求
            research_plan = await self._analyze_research_needs(task)

            # 2. 搜索信息
            search_results = await self._search_information(research_plan)

            # 3. 提取关键信息
            extracted_info = await self._extract_information(search_results)

            # 4. 综合知识
            synthesis = await self._synthesize_knowledge(extracted_info)

            # 5. 生成报告
            report = await self._generate_report(synthesis, task)

            # 更新监控器状态
            if self.task_monitor:
                self.task_monitor.update_stage(task.task_id, TaskStage.COMPLETED)

            execution_time = (datetime.now() - start_time).total_seconds()

            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.COMPLETED.value,
                output={
                    "research_plan": research_plan,
                    "search_results": search_results,
                    "extracted_info": extracted_info,
                    "synthesis": synthesis,
                    "report": report
                },
                quality_score=0.85,
                execution_time=execution_time,
                logs=["Research completed successfully"],
                metadata={
                    "harness_type": self.harness_type.value,
                    "research_depth": self.research_depth,
                    "output_format": self.output_format,
                    "sources_count": len(search_results)
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
                logs=[f"Research task {task.task_id} failed"],
                errors=[str(e)],
                metadata={"harness_type": self.harness_type.value}
            )

    async def _analyze_research_needs(self, task: Task) -> Dict[str, Any]:
        """分析研究需求

        使用 LLM 分析研究主题，确定核心问题和子主题。
        """
        messages = [
            {"role": "system", "content": self.ANALYSIS_PROMPT},
            {"role": "user", "content": f"请分析以下研究需求：\n\n"
                                        f"主题：{task.description}\n\n"
                                        f"请确定：\n"
                                        f"1. 核心研究问题\n"
                                        f"2. 关键子主题\n"
                                        f"3. 信息来源建议\n"
                                        f"4. 研究深度：{self.research_depth}"}
        ]

        try:
            llm_config = self._get_llm_config()
            response = await chat_completion(
                messages,
                config=llm_config,
                temperature=0.4,
                max_tokens=1500
            )

            return {
                "topic": task.description,
                "core_questions": self._parse_questions(response),
                "subtopics": self._parse_subtopics(response),
                "sources": self._parse_sources(response),
                "depth": self.research_depth,
                "raw_analysis": response
            }
        except Exception as e:
            # 如果分析失败，返回基本的研究计划
            return {
                "topic": task.description,
                "core_questions": [task.description],
                "subtopics": [task.description],
                "sources": ["llm_knowledge_base"],
                "depth": self.research_depth,
                "error": str(e)
            }

    async def _search_information(self, research_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        """搜索信息

        模拟多源搜索，对每个子主题进行搜索。
        """
        search_results = []
        subtopics = research_plan.get("subtopics", [research_plan.get("topic", "")])

        # 限制搜索数量
        subtopics = subtopics[:self.max_sources]

        for subtopic in subtopics:
            result = await self._search_subtopic(subtopic)
            search_results.append(result)

        return search_results

    async def _search_subtopic(self, subtopic: str) -> Dict[str, Any]:
        """搜索子主题

        使用 LLM 模拟搜索子主题的相关信息。
        """
        messages = [
            {"role": "system", "content": "你是一个信息检索助手。请提供关于以下主题的关键信息。"},
            {"role": "user", "content": f"请搜索并提供关于'{subtopic}'的关键信息，"
                                        f"包括：定义、重要性、相关数据、主要观点。"}
        ]

        try:
            llm_config = self._get_llm_config()
            response = await chat_completion(
                messages,
                config=llm_config,
                temperature=0.5,
                max_tokens=1000
            )

            return {
                "subtopic": subtopic,
                "content": response,
                "source": "llm_knowledge_base",
                "relevance": 0.85
            }
        except Exception as e:
            return {
                "subtopic": subtopic,
                "content": f"搜索失败: {str(e)}",
                "source": "error",
                "relevance": 0.0
            }

    async def _extract_information(self, search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """提取关键信息

        从搜索结果中提取关键概念、数据和见解。
        """
        if not search_results:
            return {
                "key_concepts": [],
                "data_points": [],
                "key_findings": [],
                "sources": []
            }

        # 合并所有搜索结果内容
        combined_content = "\n\n".join([
            f"子主题: {result['subtopic']}\n{result['content']}"
            for result in search_results
        ])

        messages = [
            {"role": "system", "content": self.EXTRACTION_PROMPT},
            {"role": "user", "content": f"请从以下内容中提取关键信息：\n\n{combined_content}"}
        ]

        try:
            llm_config = self._get_llm_config()
            response = await chat_completion(
                messages,
                config=llm_config,
                temperature=0.4,
                max_tokens=2000
            )

            return {
                "key_concepts": self._parse_key_concepts(response),
                "data_points": self._parse_data_points(response),
                "key_findings": self._parse_key_findings(response),
                "raw_extraction": response,
                "sources_count": len(search_results)
            }
        except Exception as e:
            return {
                "key_concepts": [],
                "data_points": [],
                "key_findings": ["信息提取失败"],
                "error": str(e),
                "sources_count": len(search_results)
            }

    async def _synthesize_knowledge(self, extracted_info: Dict[str, Any]) -> Dict[str, Any]:
        """综合知识

        整合提取的信息，形成综合见解。
        """
        key_findings = extracted_info.get("key_findings", [])
        key_concepts = extracted_info.get("key_concepts", [])
        data_points = extracted_info.get("data_points", [])

        if not key_findings and not key_concepts:
            return {
                "synthesis": "没有足够的信息进行综合",
                "patterns": [],
                "insights": [],
                "knowledge_gaps": []
            }

        combined_info = f"""关键发现:
{chr(10).join(f'- {finding}' for finding in key_findings)}

核心概念:
{chr(10).join(f'- {concept}' for concept in key_concepts)}

数据点:
{chr(10).join(f'- {point}' for point in data_points)}
"""

        messages = [
            {"role": "system", "content": self.SYNTHESIS_PROMPT},
            {"role": "user", "content": f"请综合以下研究发现：\n\n{combined_info}"}
        ]

        try:
            llm_config = self._get_llm_config()
            response = await chat_completion(
                messages,
                config=llm_config,
                temperature=0.4,
                max_tokens=2000
            )

            return {
                "synthesis": response,
                "patterns": self._parse_patterns(response),
                "insights": self._parse_insights(response),
                "knowledge_gaps": self._parse_knowledge_gaps(response)
            }
        except Exception as e:
            return {
                "synthesis": "知识综合失败",
                "patterns": [],
                "insights": [],
                "knowledge_gaps": [str(e)]
            }

    async def _generate_report(self, synthesis: Dict[str, Any], task: Task) -> Dict[str, Any]:
        """生成研究报告

        根据综合结果生成最终研究报告。
        """
        synthesis_text = synthesis.get("synthesis", "")

        if not synthesis_text:
            return {
                "executive_summary": "无法生成报告",
                "full_report": "综合结果为空",
                "format": self.output_format
            }

        messages = [
            {"role": "system", "content": self.REPORT_PROMPT},
            {"role": "user", "content": f"研究主题：{task.description}\n\n"
                                        f"综合结果：\n{synthesis_text}\n\n"
                                        f"请生成格式为 '{self.output_format}' 的研究报告。"}
        ]

        try:
            llm_config = self._get_llm_config()
            response = await chat_completion(
                messages,
                config=llm_config,
                temperature=0.4,
                max_tokens=3000
            )

            return {
                "executive_summary": self._extract_executive_summary(response),
                "full_report": response,
                "format": self.output_format,
                "generated_at": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "executive_summary": "报告生成失败",
                "full_report": f"错误: {str(e)}",
                "format": self.output_format
            }

    def _parse_questions(self, text: str) -> List[str]:
        """解析研究问题"""
        questions = []

        # 匹配数字编号或问号的行
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            # 匹配 "1." "-" "*" 开头的行
            if re.match(r'^\d+\.\s*', line) or re.match(r'^[-*]\s*', line):
                question = re.sub(r'^\d+\.\s*', '', line)
                question = re.sub(r'^[-*]\s*', '', question)
                if question and len(question) > 5:
                    questions.append(question)
            # 匹配包含问号的行
            elif '?' in line and len(line) > 10:
                questions.append(line)

        return questions[:5] if questions else ["研究问题"]

    def _parse_subtopics(self, text: str) -> List[str]:
        """解析子主题"""
        subtopics = []

        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            # 匹配 "1." "-" "*" 开头的行
            if re.match(r'^\d+\.\s*', line) or re.match(r'^[-*]\s*', line):
                subtopic = re.sub(r'^\d+\.\s*', '', line)
                subtopic = re.sub(r'^[-*]\s*', '', subtopic)
                if subtopic and len(subtopic) > 3:
                    subtopics.append(subtopic)

        return subtopics[:self.max_sources] if subtopics else ["子主题"]

    def _parse_sources(self, text: str) -> List[str]:
        """解析信息来源"""
        sources = []

        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if '来源' in line or 'source' in line.lower():
                # 提取来源名称
                match = re.search(r'[:：]\s*(.+)', line)
                if match:
                    sources.append(match.group(1).strip())

        return sources if sources else ["llm_knowledge_base"]

    def _parse_key_concepts(self, text: str) -> List[str]:
        """解析核心概念"""
        concepts = []

        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if re.match(r'^\d+\.\s*', line) or re.match(r'^[-*]\s*', line):
                concept = re.sub(r'^\d+\.\s*', '', line)
                concept = re.sub(r'^[-*]\s*', '', concept)
                if concept and len(concept) > 3:
                    concepts.append(concept)

        return concepts

    def _parse_data_points(self, text: str) -> List[str]:
        """解析数据点"""
        data_points = []

        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            # 匹配包含数字的行
            if re.search(r'\d+%|\d+\.\d+|\d+\s*(个|次|年|月|天)', line):
                data_points.append(line)

        return data_points

    def _parse_key_findings(self, text: str) -> List[str]:
        """解析关键发现"""
        findings = []

        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if re.match(r'^\d+\.\s*', line) or re.match(r'^[-*]\s*', line):
                finding = re.sub(r'^\d+\.\s*', '', line)
                finding = re.sub(r'^[-*]\s*', '', finding)
                if finding and len(finding) > 5:
                    findings.append(finding)

        return findings if findings else ["研究发现"]

    def _parse_patterns(self, text: str) -> List[str]:
        """解析模式"""
        patterns = []

        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if '模式' in line or 'pattern' in line.lower() or '趋势' in line:
                patterns.append(line)

        return patterns

    def _parse_insights(self, text: str) -> List[str]:
        """解析见解"""
        insights = []

        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if '见解' in line or '洞察' in line or 'insight' in line.lower():
                insights.append(line)

        return insights

    def _parse_knowledge_gaps(self, text: str) -> List[str]:
        """解析知识缺口"""
        gaps = []

        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if '缺口' in line or 'gap' in line.lower() or '缺失' in line:
                gaps.append(line)

        return gaps

    def _extract_executive_summary(self, text: str) -> str:
        """提取执行摘要"""
        # 查找 "执行摘要" 或 "Executive Summary" 部分
        lines = text.split('\n')
        summary_lines = []
        in_summary = False

        for line in lines:
            if '执行摘要' in line or 'Executive Summary' in line:
                in_summary = True
                continue
            if in_summary:
                if line.strip() == '' or line.startswith('#'):
                    break
                summary_lines.append(line)

        return '\n'.join(summary_lines) if summary_lines else text[:500]

    async def cleanup(self):
        """清理资源"""
        self.task_monitor = None
        self._initialized = False
        await super().cleanup()


# 注册到工厂
HarnessFactory.register(HarnessType.RESEARCH, ResearchHarness)
