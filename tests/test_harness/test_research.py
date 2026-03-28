"""
ResearchHarness 测试

测试 ResearchHarness 的各项功能，包括：
1. 研究需求分析
2. 信息搜索
3. 信息提取
4. 知识综合
5. 报告生成
"""
import pytest
from unittest.mock import patch, AsyncMock

from src.harness.research import ResearchHarness
from src.harness.factory import HarnessFactory
from src.core.types import (
    Task, TaskResult, HarnessConfig, HarnessType, TaskStatus, TaskType
)


class TestResearchHarness:
    """ResearchHarness 测试类"""

    def setup_method(self):
        """每个测试前清理注册表并创建测试实例"""
        HarnessFactory.clear_registry()

        # 注册 ResearchHarness
        HarnessFactory.register(HarnessType.RESEARCH, ResearchHarness)

        # 创建测试配置
        self.config = HarnessConfig(
            harness_type=HarnessType.RESEARCH,
            custom_params={
                "max_sources": 5,
                "research_depth": "medium",
                "output_format": "report",
                "enable_monitoring": False
            }
        )

        # 创建 harness 实例
        self.harness = ResearchHarness(self.config)

    def teardown_method(self):
        """每个测试后清理"""
        HarnessFactory.clear_registry()

    @pytest.mark.asyncio
    async def test_initialize(self):
        """测试初始化"""
        await self.harness.initialize()
        assert self.harness.is_initialized()
        assert self.harness.max_sources == 5
        assert self.harness.research_depth == "medium"
        assert self.harness.output_format == "report"
        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_parse_questions(self):
        """测试解析研究问题"""
        await self.harness.initialize()

        # 测试数字编号格式
        text1 = """
1. 什么是机器学习？
2. 机器学习的主要应用有哪些？
3. 机器学习的发展趋势是什么？
"""
        questions1 = self.harness._parse_questions(text1)
        assert len(questions1) == 3
        assert "什么是机器学习？" in questions1[0]

        # 测试列表格式
        text2 = """
- 如何提高代码质量？
- 最佳实践有哪些？
* 另一个问题
"""
        questions2 = self.harness._parse_questions(text2)
        assert len(questions2) >= 2

        # 测试空内容
        questions3 = self.harness._parse_questions("")
        assert len(questions3) == 1  # 返回默认问题

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_parse_subtopics(self):
        """测试解析子主题"""
        await self.harness.initialize()

        text = """
1. 深度学习基础
2. 卷积神经网络
3. 循环神经网络
- 自然语言处理
* 计算机视觉
"""
        subtopics = self.harness._parse_subtopics(text)
        assert len(subtopics) >= 3
        assert "深度学习基础" in subtopics

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_parse_sources(self):
        """测试解析信息来源"""
        await self.harness.initialize()

        text = """
建议来源：学术论文
来源：技术博客
信息来源：官方文档
Source: GitHub repositories
"""
        sources = self.harness._parse_sources(text)
        assert len(sources) >= 1

        # 测试无来源时返回默认值
        empty_sources = self.harness._parse_sources("")
        assert len(empty_sources) == 1
        assert empty_sources[0] == "llm_knowledge_base"

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_parse_key_concepts(self):
        """测试解析核心概念"""
        await self.harness.initialize()

        text = """
1. 神经网络
2. 反向传播
- 梯度下降
* 激活函数
"""
        concepts = self.harness._parse_key_concepts(text)
        assert len(concepts) >= 2

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_parse_data_points(self):
        """测试解析数据点"""
        await self.harness.initialize()

        text = """
准确率达到 95%
训练时间为 2.5 小时
模型大小为 100 MB
共进行了 1000 次迭代
"""
        data_points = self.harness._parse_data_points(text)
        assert len(data_points) >= 2

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_parse_key_findings(self):
        """测试解析关键发现"""
        await self.harness.initialize()

        text = """
1. 深度学习在图像识别中表现优异
2. Transformer 架构改变了 NLP 领域
- 数据质量对模型性能影响重大
"""
        findings = self.harness._parse_key_findings(text)
        assert len(findings) >= 2

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_extract_executive_summary(self):
        """测试提取执行摘要"""
        await self.harness.initialize()

        text = """
# 研究报告

## 执行摘要

本研究分析了人工智能的发展趋势。
主要发现包括深度学习的广泛应用。

## 详细内容

更多内容...
"""
        summary = self.harness._extract_executive_summary(text)
        assert "人工智能" in summary or "本研究" in summary

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_analyze_research_needs(self):
        """测试分析研究需求"""
        await self.harness.initialize()

        task = Task(
            description="研究人工智能在医疗领域的应用",
            task_type=TaskType.RESEARCH
        )

        mock_response = """
核心研究问题：
1. AI在医疗诊断中的准确率如何？
2. 哪些医疗场景最适合AI应用？

关键子主题：
1. 医学影像分析
2. 药物研发
3. 个性化治疗

信息来源：
- 学术论文
- 技术报告
"""

        with patch('src.harness.research.chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = mock_response

            research_plan = await self.harness._analyze_research_needs(task)

            assert research_plan["topic"] == task.description
            assert "core_questions" in research_plan
            assert "subtopics" in research_plan
            assert "sources" in research_plan
            assert research_plan["depth"] == "medium"

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_search_subtopic(self):
        """测试搜索子主题"""
        await self.harness.initialize()

        mock_response = """
定义：机器学习是人工智能的一个分支
重要性：能够自动从数据中学习模式
相关数据：市场规模预计在2025年达到1000亿美元
主要观点：深度学习是当前最热门的技术
"""

        with patch('src.harness.research.chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = mock_response

            result = await self.harness._search_subtopic("机器学习")

            assert result["subtopic"] == "机器学习"
            assert "content" in result
            assert result["source"] == "llm_knowledge_base"
            assert result["relevance"] == 0.85

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_extract_information(self):
        """测试提取关键信息"""
        await self.harness.initialize()

        search_results = [
            {
                "subtopic": "深度学习",
                "content": "深度学习是一种机器学习技术，使用多层神经网络。"
            },
            {
                "subtopic": "CNN",
                "content": "卷积神经网络是深度学习在图像处理中的应用。"
            }
        ]

        mock_response = """
核心概念：
1. 神经网络
2. 卷积层

关键发现：
1. CNN在图像识别中准确率达到99%
2. 深度学习需要大量训练数据

数据点：
- 训练时间：24小时
- 准确率：95%
"""

        with patch('src.harness.research.chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = mock_response

            extracted = await self.harness._extract_information(search_results)

            assert "key_concepts" in extracted
            assert "key_findings" in extracted
            assert "data_points" in extracted
            assert extracted["sources_count"] == 2

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_synthesize_knowledge(self):
        """测试知识综合"""
        await self.harness.initialize()

        extracted_info = {
            "key_findings": [
                "深度学习在图像识别中表现优异",
                "Transformer改变了NLP"
            ],
            "key_concepts": [
                "神经网络",
                "注意力机制"
            ],
            "data_points": [
                "准确率：95%"
            ]
        }

        mock_response = """
综合见解：
深度学习技术已在多个领域取得突破。

模式：
1. 端到端学习的趋势
2. 大模型时代的到来

见解：
AI正在改变软件开发的范式

知识缺口：
- 可解释性仍需提升
"""

        with patch('src.harness.research.chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = mock_response

            synthesis = await self.harness._synthesize_knowledge(extracted_info)

            assert "synthesis" in synthesis
            assert "patterns" in synthesis
            assert "insights" in synthesis
            assert "knowledge_gaps" in synthesis

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_generate_report(self):
        """测试生成研究报告"""
        await self.harness.initialize()

        synthesis = {
            "synthesis": "人工智能正在快速发展",
            "patterns": ["端到端学习", "大模型时代"],
            "insights": ["AI改变软件开发"],
            "knowledge_gaps": ["可解释性"]
        }

        task = Task(
            description="研究人工智能发展趋势",
            task_type=TaskType.RESEARCH
        )

        mock_response = """
# 研究报告：人工智能发展趋势

## 执行摘要

本研究分析了人工智能的最新发展趋势...

## 主要发现

1. 深度学习技术持续进步
2. 大语言模型改变交互方式

## 详细分析

更多详细内容...

## 建议

1. 关注AI伦理问题
2. 投资AI基础设施
"""

        with patch('src.harness.research.chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = mock_response

            report = await self.harness._generate_report(synthesis, task)

            assert "executive_summary" in report
            assert "full_report" in report
            assert report["format"] == "report"
            assert "generated_at" in report

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_execute_full_research_task(self):
        """测试执行完整的研究任务"""
        await self.harness.initialize()

        task = Task(
            description="研究机器学习在医疗诊断中的应用",
            task_type=TaskType.RESEARCH
        )

        # Mock responses for each step
        mock_analysis = """
核心研究问题：
1. 机器学习如何提高诊断准确性？

关键子主题：
1. 医学影像分析
2. 疾病预测

信息来源：
- 学术论文
"""

        mock_search = """
医学影像分析使用深度学习技术
准确率可达95%以上
"""

        mock_extraction = """
核心概念：
1. CNN
2. 图像分割

关键发现：
1. AI辅助诊断准确率提升15%
"""

        mock_synthesis = """
综合见解：
AI在医疗诊断中具有巨大潜力

模式：
1. 从辅助到主导的转变

见解：
需要解决数据隐私问题
"""

        mock_report = """
# 研究报告

## 执行摘要

AI在医疗诊断中的应用前景广阔...
"""

        with patch('src.harness.research.chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_chat.side_effect = [
                mock_analysis,  # _analyze_research_needs
                mock_search,    # _search_subtopic
                mock_extraction, # _extract_information
                mock_synthesis,  # _synthesize_knowledge
                mock_report      # _generate_report
            ]

            result = await self.harness.execute(task)

            assert result.status == TaskStatus.COMPLETED.value
            assert result.output is not None
            assert "research_plan" in result.output
            assert "search_results" in result.output
            assert "extracted_info" in result.output
            assert "synthesis" in result.output
            assert "report" in result.output
            assert result.metadata["harness_type"] == HarnessType.RESEARCH.value

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_execute_with_llm_error(self):
        """测试 LLM 调用失败时的处理 - ResearchHarness 采用优雅降级策略"""
        await self.harness.initialize()

        task = Task(
            description="研究某个主题",
            task_type=TaskType.RESEARCH
        )

        with patch('src.harness.research.chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_chat.side_effect = Exception("LLM API Error")

            result = await self.harness.execute(task)

            # ResearchHarness 采用优雅降级策略，即使 LLM 调用失败也会尝试完成任务
            # 任务状态会是 COMPLETED，但研究计划中可能包含错误信息
            assert result.status == TaskStatus.COMPLETED.value
            assert result.output is not None
            assert "research_plan" in result.output
            # 错误信息会被记录在研究计划中
            assert "error" in result.output["research_plan"]

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_factory_registration(self):
        """测试工厂注册"""
        # 确保 ResearchHarness 已注册
        assert HarnessFactory.is_registered(HarnessType.RESEARCH)

        # 使用工厂创建实例
        harness = HarnessFactory.create(HarnessType.RESEARCH)
        assert isinstance(harness, ResearchHarness)

    @pytest.mark.asyncio
    async def test_factory_create_with_config(self):
        """测试工厂创建带配置的实例"""
        config = {
            "custom_params": {
                "max_sources": 8,
                "research_depth": "deep",
                "output_format": "summary",
                "enable_monitoring": False
            }
        }

        harness = HarnessFactory.create(HarnessType.RESEARCH, config=config)
        assert isinstance(harness, ResearchHarness)
        assert harness.max_sources == 8
        assert harness.research_depth == "deep"
        assert harness.output_format == "summary"

    @pytest.mark.asyncio
    async def test_harness_config_defaults(self):
        """测试 Harness 配置默认值"""
        config = HarnessConfig(harness_type=HarnessType.RESEARCH)
        harness = ResearchHarness(config)

        assert harness.max_sources == 10
        assert harness.research_depth == "medium"
        assert harness.output_format == "report"
        assert harness.enable_monitoring is True

    @pytest.mark.asyncio
    async def test_result_structure(self):
        """测试结果结构完整性"""
        await self.harness.initialize()

        task = Task(
            description="研究测试主题",
            task_type=TaskType.RESEARCH
        )

        mock_analysis = "核心问题：测试问题\n子主题：测试主题"
        mock_search = "搜索结果内容"
        mock_extraction = "提取的信息"
        mock_synthesis = "综合结果"
        mock_report = "# 报告"

        with patch('src.harness.research.chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_chat.side_effect = [
                mock_analysis,
                mock_search,
                mock_extraction,
                mock_synthesis,
                mock_report
            ]

            result = await self.harness.execute(task)

            # 验证 TaskResult 结构
            assert result.task_id == task.task_id
            assert result.status == TaskStatus.COMPLETED.value
            assert isinstance(result.output, dict)
            assert "research_plan" in result.output
            assert "report" in result.output
            assert isinstance(result.quality_score, float)
            assert isinstance(result.execution_time, float)
            assert isinstance(result.logs, list)
            assert isinstance(result.metadata, dict)
            assert result.metadata["harness_type"] == HarnessType.RESEARCH.value

        await self.harness.cleanup()

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """测试资源清理"""
        await self.harness.initialize()
        assert self.harness.is_initialized()

        await self.harness.cleanup()
        assert not self.harness.is_initialized()


class TestResearchHarnessMonitoring:
    """ResearchHarness 监控功能测试"""

    @pytest.mark.asyncio
    async def test_monitoring_enabled(self):
        """测试启用监控"""
        HarnessFactory.clear_registry()
        HarnessFactory.register(HarnessType.RESEARCH, ResearchHarness)

        config = HarnessConfig(
            harness_type=HarnessType.RESEARCH,
            custom_params={"enable_monitoring": True}
        )

        harness = ResearchHarness(config)
        await harness.initialize()

        assert harness.task_monitor is not None

        await harness.cleanup()
        HarnessFactory.clear_registry()

    @pytest.mark.asyncio
    async def test_monitoring_disabled(self):
        """测试禁用监控"""
        HarnessFactory.clear_registry()
        HarnessFactory.register(HarnessType.RESEARCH, ResearchHarness)

        config = HarnessConfig(
            harness_type=HarnessType.RESEARCH,
            custom_params={"enable_monitoring": False}
        )

        harness = ResearchHarness(config)
        await harness.initialize()

        assert harness.task_monitor is None

        await harness.cleanup()
        HarnessFactory.clear_registry()


class TestResearchHarnessDepth:
    """ResearchHarness 不同研究深度测试"""

    def setup_method(self):
        HarnessFactory.clear_registry()
        HarnessFactory.register(HarnessType.RESEARCH, ResearchHarness)

    def teardown_method(self):
        HarnessFactory.clear_registry()

    @pytest.mark.asyncio
    async def test_shallow_research_depth(self):
        """测试浅层研究深度"""
        config = HarnessConfig(
            harness_type=HarnessType.RESEARCH,
            custom_params={
                "research_depth": "shallow",
                "max_sources": 3,
                "enable_monitoring": False
            }
        )
        harness = ResearchHarness(config)

        assert harness.research_depth == "shallow"
        assert harness.max_sources == 3

    @pytest.mark.asyncio
    async def test_deep_research_depth(self):
        """测试深层研究深度"""
        config = HarnessConfig(
            harness_type=HarnessType.RESEARCH,
            custom_params={
                "research_depth": "deep",
                "max_sources": 15,
                "enable_monitoring": False
            }
        )
        harness = ResearchHarness(config)

        assert harness.research_depth == "deep"
        assert harness.max_sources == 15


class TestResearchHarnessOutputFormats:
    """ResearchHarness 不同输出格式测试"""

    def setup_method(self):
        HarnessFactory.clear_registry()
        HarnessFactory.register(HarnessType.RESEARCH, ResearchHarness)

    def teardown_method(self):
        HarnessFactory.clear_registry()

    @pytest.mark.asyncio
    async def test_report_format(self):
        """测试报告格式"""
        config = HarnessConfig(
            harness_type=HarnessType.RESEARCH,
            custom_params={
                "output_format": "report",
                "enable_monitoring": False
            }
        )
        harness = ResearchHarness(config)

        assert harness.output_format == "report"

    @pytest.mark.asyncio
    async def test_summary_format(self):
        """测试摘要格式"""
        config = HarnessConfig(
            harness_type=HarnessType.RESEARCH,
            custom_params={
                "output_format": "summary",
                "enable_monitoring": False
            }
        )
        harness = ResearchHarness(config)

        assert harness.output_format == "summary"

    @pytest.mark.asyncio
    async def test_bullets_format(self):
        """测试要点格式"""
        config = HarnessConfig(
            harness_type=HarnessType.RESEARCH,
            custom_params={
                "output_format": "bullets",
                "enable_monitoring": False
            }
        )
        harness = ResearchHarness(config)

        assert harness.output_format == "bullets"
