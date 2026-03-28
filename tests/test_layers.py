"""
Agent Swarm 层模块测试
"""
import asyncio
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.types import Task, SubTask, TaskStatus, AgentConfig, AgentRole
from src.core.message_bus import MessageBus
from src.layers import (
    TaskDecomposer, ResourceAllocator, ValidationEngine, IntegrationEngine,
    QualityMetrics
)


class TestTaskDecomposer:
    """测试任务分解器"""
    
    def test_analysis_task_decomposition(self):
        """测试分析任务分解"""
        decomposer = TaskDecomposer()
        
        task = Task(
            description="Analyze user data",
            metadata={"task_type": "analysis"}
        )
        
        subtasks = decomposer.decompose(task)
        
        assert len(subtasks) == 4
        assert subtasks[0].task_type == "data_collection"
        assert subtasks[1].task_type == "data_preprocessing"
        assert subtasks[2].task_type == "analysis_execution"
        assert subtasks[3].task_type == "visualization"
        
        # 检查依赖关系
        assert subtasks[1].task_id in subtasks[2].dependencies
    
    def test_generation_task_decomposition(self):
        """测试生成任务分解"""
        decomposer = TaskDecomposer()
        
        task = Task(
            description="Generate content",
            metadata={"task_type": "generation"}
        )
        
        subtasks = decomposer.decompose(task)
        
        assert len(subtasks) == 3
        assert subtasks[0].task_type == "requirement_analysis"
        assert subtasks[1].task_type == "content_generation"
        assert subtasks[2].task_type == "content_optimization"
    
    def test_code_task_decomposition(self):
        """测试代码任务分解"""
        decomposer = TaskDecomposer()
        
        task = Task(
            description="Implement feature",
            metadata={"task_type": "code"}
        )
        
        subtasks = decomposer.decompose(task)
        
        assert len(subtasks) == 4
        assert subtasks[0].task_type == "requirement_understanding"
        assert subtasks[1].task_type == "code_design"
        assert subtasks[2].task_type == "code_implementation"
        assert subtasks[3].task_type == "test_writing"
    
    def test_default_task_decomposition(self):
        """测试默认任务分解"""
        decomposer = TaskDecomposer()
        
        task = Task(description="Simple task")
        
        subtasks = decomposer.decompose(task)
        
        assert len(subtasks) == 1
        assert subtasks[0].task_type == "generic_execution"


class TestResourceAllocator:
    """测试资源分配器"""
    
    def test_agent_registration(self):
        """测试Agent注册"""
        allocator = ResourceAllocator()
        
        allocator.register_agent("agent1", ["cap1", "cap2"])
        
        assert "agent1" in allocator._agent_capabilities
        assert "cap1" in allocator._agent_capabilities["agent1"]
        assert allocator._agent_loads["agent1"] == 0
    
    def test_task_allocation(self):
        """测试任务分配"""
        allocator = ResourceAllocator()
        
        allocator.register_agent("agent1", ["data_processing", "analysis"])
        allocator.register_agent("agent2", ["coding", "testing"])
        
        subtask = SubTask(
            description="Process data",
            task_type="data_preprocessing"
        )
        
        assigned = allocator.allocate_task(subtask, ["agent1", "agent2"])
        
        assert assigned == "agent1"
        assert allocator._agent_loads["agent1"] == 1
    
    def test_allocation_by_capability(self):
        """测试按能力分配"""
        allocator = ResourceAllocator()
        
        allocator.register_agent("agent1", ["general"])
        allocator.register_agent("agent2", ["coding"])
        
        subtask = SubTask(
            description="Write code",
            task_type="code_implementation"
        )
        
        assigned = allocator.allocate_task(subtask, ["agent1", "agent2"])
        
        # agent2有coding能力，应该被分配
        assert assigned == "agent2"
    
    def test_load_balancing(self):
        """测试负载均衡"""
        allocator = ResourceAllocator()
        
        allocator.register_agent("agent1", ["general"])
        allocator.register_agent("agent2", ["general"])
        
        # 增加agent1的负载
        allocator._agent_loads["agent1"] = 3
        allocator._agent_loads["agent2"] = 1
        
        subtask = SubTask(description="Task")
        
        assigned = allocator.allocate_task(subtask, ["agent1", "agent2"])
        
        # 应该选择负载较低的agent2
        assert assigned == "agent2"
    
    def test_no_capable_agent(self):
        """测试没有可用Agent的情况"""
        allocator = ResourceAllocator()
        
        allocator.register_agent("agent1", ["specific_cap"])
        
        subtask = SubTask(
            description="Task",
            task_type="unknown_type"
        )
        
        assigned = allocator.allocate_task(subtask, ["agent1"])
        
        assert assigned is None


class TestValidationEngine:
    """测试验证引擎"""
    
    @pytest.mark.asyncio
    async def test_completeness_validation(self):
        """测试完整性验证"""
        validator = ValidationEngine()
        
        data = {"name": "Test", "value": 100}
        criteria = {"required_fields": ["name", "value"], "threshold": 0.8}
        
        result = await validator.validate(data, "completeness", criteria)
        
        assert result.is_valid is True
        assert result.score == 1.0
    
    @pytest.mark.asyncio
    async def test_completeness_validation_missing_fields(self):
        """测试完整性验证 - 缺少字段"""
        validator = ValidationEngine()
        
        data = {"name": "Test"}
        criteria = {"required_fields": ["name", "value"], "threshold": 0.8}
        
        result = await validator.validate(data, "completeness", criteria)
        
        assert result.is_valid is False
        assert result.score < 1.0
        assert "Missing" in result.feedback
    
    @pytest.mark.asyncio
    async def test_accuracy_validation(self):
        """测试准确性验证"""
        validator = ValidationEngine()
        
        data = "This is a test with good quality"
        criteria = {"expected_patterns": ["test", "quality"], "threshold": 0.7}
        
        result = await validator.validate(data, "accuracy", criteria)
        
        assert result.score == 1.0
        assert result.is_valid is True
    
    @pytest.mark.asyncio
    async def test_consistency_validation(self):
        """测试一致性验证"""
        validator = ValidationEngine()
        
        data = {"percentage": 50, "score": 0.8}
        criteria = {"threshold": 0.8}
        
        result = await validator.validate(data, "consistency", criteria)
        
        assert result.is_valid is True
    
    @pytest.mark.asyncio
    async def test_consistency_validation_inconsistent(self):
        """测试一致性验证 - 不一致数据"""
        validator = ValidationEngine()
        
        data = {"percentage": 150}  # 超出范围
        criteria = {"threshold": 0.8}
        
        result = await validator.validate(data, "consistency", criteria)
        
        assert result.score < 1.0
    
    @pytest.mark.asyncio
    async def test_performance_validation(self):
        """测试性能验证"""
        validator = ValidationEngine()
        
        data = {"execution_time_ms": 100, "memory_usage_mb": 256}
        criteria = {"max_execution_time_ms": 5000, "max_memory_mb": 512}
        
        result = await validator.validate(data, "performance", criteria)
        
        assert result.is_valid is True
    
    @pytest.mark.asyncio
    async def test_format_validation(self):
        """测试格式验证"""
        validator = ValidationEngine()
        
        data = {"key": "value"}
        criteria = {"expected_format": "json", "threshold": 0.9}
        
        result = await validator.validate(data, "format", criteria)
        
        assert result.is_valid is True
    
    @pytest.mark.asyncio
    async def test_validate_all(self):
        """测试全部验证"""
        validator = ValidationEngine()
        
        data = {"name": "Test", "value": 100}
        
        results = await validator.validate_all(data)
        
        assert "completeness" in results
        assert "accuracy" in results
        assert "consistency" in results
        assert "performance" in results
        assert "format" in results


class TestIntegrationEngine:
    """测试整合引擎"""
    
    @pytest.mark.asyncio
    async def test_merge_integration(self):
        """测试合并整合"""
        integrator = IntegrationEngine()
        
        results = [
            {"a": 1, "b": 2},
            {"c": 3, "d": 4}
        ]
        
        merged = await integrator.integrate(results, "merge")
        
        assert merged["a"] == 1
        assert merged["b"] == 2
        assert merged["c"] == 3
        assert merged["d"] == 4
    
    @pytest.mark.asyncio
    async def test_concatenate_integration(self):
        """测试连接整合"""
        integrator = IntegrationEngine()
        
        results = ["Hello", "World"]
        
        concatenated = await integrator.integrate(results, "concatenate", {"separator": " "})
        
        assert concatenated == "Hello World"
    
    @pytest.mark.asyncio
    async def test_summarize_integration(self):
        """测试摘要整合"""
        integrator = IntegrationEngine()
        
        results = [
            {"score": 0.9, "data": [1, 2]},
            {"score": 0.8, "data": [3, 4]}
        ]
        
        summary = await integrator.integrate(results, "summarize")
        
        assert summary["total_results"] == 2
        assert "result_types" in summary
        assert "timestamp" in summary
    
    @pytest.mark.asyncio
    async def test_aggregate_integration(self):
        """测试聚合整合"""
        integrator = IntegrationEngine()
        
        results = [10, 20, 30]
        
        aggregated = await integrator.integrate(results, "aggregate", {"type": "avg"})
        
        assert aggregated == 20.0
    
    @pytest.mark.asyncio
    async def test_select_best_integration(self):
        """测试选择最佳整合"""
        integrator = IntegrationEngine()
        
        results = [
            {"name": "A", "score": 0.7},
            {"name": "B", "score": 0.9},
            {"name": "C", "score": 0.8}
        ]
        
        best = await integrator.integrate(results, "select_best", {"scoring_key": "score"})
        
        assert best["name"] == "B"
        assert best["score"] == 0.9


class TestQualityMetrics:
    """测试质量指标"""
    
    def test_overall_score_calculation(self):
        """测试综合得分计算"""
        metrics = QualityMetrics(
            completeness=1.0,
            accuracy=0.9,
            consistency=0.8,
            performance=0.85
        )
        
        overall = metrics.calculate_overall()
        
        expected = (1.0 * 0.3 + 0.9 * 0.3 + 0.8 * 0.2 + 0.85 * 0.2)
        assert abs(overall - expected) < 0.001
    
    def test_custom_weights(self):
        """测试自定义权重"""
        metrics = QualityMetrics(
            completeness=1.0,
            accuracy=0.5
        )
        
        custom_weights = {
            "completeness": 0.6,
            "accuracy": 0.4,
            "consistency": 0.0,
            "performance": 0.0
        }
        
        overall = metrics.calculate_overall(custom_weights)
        
        expected = 1.0 * 0.6 + 0.5 * 0.4
        assert abs(overall - expected) < 0.001
    
    def test_default_values(self):
        """测试默认值"""
        metrics = QualityMetrics()
        
        assert metrics.completeness == 0.0
        assert metrics.accuracy == 0.0
        assert metrics.consistency == 0.0
        assert metrics.performance == 0.0
        assert metrics.overall_score == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
