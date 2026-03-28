"""
Agent Swarm 高级示例
展示高级功能：自定义工具、验证策略、整合策略
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import create_swarm, run_task
from src.layers import ExecutorAgent, AgentConfig
from src.core import AgentRole, MessageBus


# 自定义工具函数
async def custom_data_processor(data: dict, operation: str = "sum") -> dict:
    """自定义数据处理工具"""
    if operation == "sum":
        result = sum(v for v in data.values() if isinstance(v, (int, float)))
    elif operation == "avg":
        values = [v for v in data.values() if isinstance(v, (int, float))]
        result = sum(values) / len(values) if values else 0
    elif operation == "count":
        result = len(data)
    else:
        result = 0
    
    return {
        "operation": operation,
        "result": result,
        "input_keys": list(data.keys())
    }


async def custom_text_analyzer(text: str, analysis_type: str = "sentiment") -> dict:
    """自定义文本分析工具"""
    if analysis_type == "sentiment":
        # 简单的情感分析模拟
        positive_words = ["good", "great", "excellent", "amazing", "wonderful"]
        negative_words = ["bad", "terrible", "awful", "poor", "worst"]
        
        text_lower = text.lower()
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)
        
        if pos_count > neg_count:
            sentiment = "positive"
            score = min(1.0, 0.5 + (pos_count - neg_count) * 0.1)
        elif neg_count > pos_count:
            sentiment = "negative"
            score = max(0.0, 0.5 - (neg_count - pos_count) * 0.1)
        else:
            sentiment = "neutral"
            score = 0.5
        
        return {
            "sentiment": sentiment,
            "score": score,
            "positive_words": pos_count,
            "negative_words": neg_count
        }
    
    elif analysis_type == "keywords":
        # 简单的关键词提取
        words = text.lower().split()
        word_freq = {}
        for word in words:
            if len(word) > 3:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "keywords": [k for k, v in top_keywords],
            "frequencies": dict(top_keywords),
            "total_words": len(words)
        }
    
    return {"error": "Unknown analysis type"}


async def custom_tools_demo():
    """自定义工具演示"""
    print("\n" + "=" * 70)
    print("自定义工具示例")
    print("=" * 70)
    
    swarm = await create_swarm(name="CustomToolsSwarm")
    
    try:
        # 为每个执行器注册自定义工具
        print("\n🔧 注册自定义工具...")
        for executor in swarm.executors.values():
            executor.register_custom_tool(
                "data_processor",
                custom_data_processor,
                "Process data with custom operations",
                {"data": "object", "operation": "string"}
            )
            executor.register_custom_tool(
                "text_analyzer",
                custom_text_analyzer,
                "Analyze text for sentiment and keywords",
                {"text": "string", "analysis_type": "string"}
            )
            print(f"  ✓ 为 {executor.config.name} 注册工具")
        
        # 使用自定义工具执行任务
        print("\n📊 执行数据处理任务...")
        
        # 手动创建一个执行任务
        from src.core.types import SubTask
        
        executor = list(swarm.executors.values())[0]
        
        task = SubTask(
            description="处理销售数据",
            task_type="generic_execution",
            parameters={
                "tool": "data_processor",
                "tool_params": {
                    "data": {"jan": 1000, "feb": 1200, "mar": 950, "apr": 1400},
                    "operation": "avg"
                }
            }
        )
        
        await executor.assign_task(task)
        
        # 等待任务完成
        await asyncio.sleep(2)
        
        print(f"任务状态: {task.status.value}")
        if task.result:
            print(f"结果: {task.result}")
        
        # 文本分析任务
        print("\n📝 执行文本分析任务...")
        
        task2 = SubTask(
            description="分析用户反馈",
            task_type="generic_execution",
            parameters={
                "tool": "text_analyzer",
                "tool_params": {
                    "text": "This product is great and amazing! I love the excellent quality.",
                    "analysis_type": "sentiment"
                }
            }
        )
        
        await executor.assign_task(task2)
        await asyncio.sleep(2)
        
        print(f"任务状态: {task2.status.value}")
        if task2.result:
            print(f"结果: {task2.result}")
        
    finally:
        await swarm.stop()


async def validation_strategies_demo():
    """验证策略演示"""
    print("\n" + "=" * 70)
    print("验证策略示例")
    print("=" * 70)
    
    swarm = await create_swarm(name="ValidationSwarm")
    
    try:
        from src.layers import ValidationEngine
        
        validator = ValidationEngine()
        
        # 测试数据
        test_results = [
            {
                "data": {"name": "Test", "value": 100, "status": "active"},
                "criteria": {
                    "required_fields": ["name", "value"],
                    "threshold": 0.8
                }
            },
            {
                "data": [1, 2, 3, 4, 5],
                "criteria": {
                    "min_items": 3,
                    "threshold": 0.8
                }
            },
            {
                "data": "This is a test result with good quality",
                "criteria": {
                    "expected_patterns": ["test", "quality"],
                    "threshold": 0.7
                }
            }
        ]
        
        print("\n🔍 执行验证...")
        for i, test in enumerate(test_results, 1):
            print(f"\n  测试 {i}:")
            print(f"    数据: {test['data']}")
            
            # 完整性验证
            completeness = await validator.validate(
                test['data'], "completeness", test['criteria']
            )
            print(f"    完整性: {completeness.score:.2f} - {completeness.feedback}")
            
            # 准确性验证
            accuracy = await validator.validate(
                test['data'], "accuracy", test['criteria']
            )
            print(f"    准确性: {accuracy.score:.2f} - {accuracy.feedback}")
        
    finally:
        await swarm.stop()


async def integration_strategies_demo():
    """整合策略演示"""
    print("\n" + "=" * 70)
    print("整合策略示例")
    print("=" * 70)
    
    swarm = await create_swarm(name="IntegrationSwarm")
    
    try:
        from src.layers import IntegrationEngine
        
        integrator = IntegrationEngine()
        
        # 测试数据
        results_to_integrate = [
            {"task": "A", "score": 0.9, "data": [1, 2, 3]},
            {"task": "B", "score": 0.8, "data": [4, 5, 6]},
            {"task": "C", "score": 0.95, "data": [7, 8, 9]}
        ]
        
        print("\n🔄 执行整合...")
        
        # 合并整合
        merged = await integrator.integrate(
            results_to_integrate, "merge", {"unique": True}
        )
        print(f"\n  合并结果: {merged}")
        
        # 摘要整合
        summarized = await integrator.integrate(
            results_to_integrate, "summarize", {"max_items": 5}
        )
        print(f"\n  摘要结果:")
        for key, value in summarized.items():
            print(f"    {key}: {value}")
        
        # 选择最佳
        best = await integrator.integrate(
            results_to_integrate, "select_best", {"scoring_key": "score"}
        )
        print(f"\n  最佳结果: {best}")
        
        # 聚合
        aggregated = await integrator.integrate(
            results_to_integrate, "aggregate", {"type": "avg"}
        )
        print(f"\n  聚合结果: {aggregated}")
        
    finally:
        await swarm.stop()


async def quality_metrics_demo():
    """质量指标演示"""
    print("\n" + "=" * 70)
    print("质量指标示例")
    print("=" * 70)
    
    from src.layers import QualityMetrics
    
    # 创建质量指标
    metrics = QualityMetrics(
        completeness=0.85,
        accuracy=0.92,
        consistency=0.78,
        performance=0.88
    )
    
    # 计算综合得分
    overall = metrics.calculate_overall()
    
    print(f"\n📊 质量指标:")
    print(f"  完整性: {metrics.completeness:.2%}")
    print(f"  准确性: {metrics.accuracy:.2%}")
    print(f"  一致性: {metrics.consistency:.2%}")
    print(f"  性能: {metrics.performance:.2%}")
    print(f"  综合得分: {overall:.2%}")
    
    # 使用自定义权重
    custom_overall = metrics.calculate_overall({
        "completeness": 0.4,
        "accuracy": 0.3,
        "consistency": 0.2,
        "performance": 0.1
    })
    print(f"\n  自定义权重综合得分: {custom_overall:.2%}")


async def main():
    """主函数"""
    print("\n🤖 Agent Swarm 高级功能演示")
    print("=" * 70)
    
    # 自定义工具
    await custom_tools_demo()
    
    # 验证策略
    await validation_strategies_demo()
    
    # 整合策略
    await integration_strategies_demo()
    
    # 质量指标
    await quality_metrics_demo()
    
    print("\n" + "=" * 70)
    print("高级演示完成!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
