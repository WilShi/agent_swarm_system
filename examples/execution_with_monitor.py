"""
演示 ExecutionHarness 集成监控功能
展示如何实时监控 Agent 工作状态
"""
import asyncio
import sys
sys.path.insert(0, '/Users/wilson/Documents/研究/AI研究课题/智能体群体智能/agent_swarm_project')

from src.harness import HarnessFactory
from src.core.types import Task, HarnessType, TaskType


async def demo_with_monitoring():
    """演示带监控的任务执行"""
    print("🚀 演示: ExecutionHarness 集成监控")
    print("=" * 60)

    # 创建 ExecutionHarness，启用监控
    harness = HarnessFactory.create(
        HarnessType.EXECUTION,
        config={
            "max_agents": 10,
            "enable_monitoring": True,
            "show_dashboard": False  # 设置为 True 启动交互式仪表板
        }
    )

    # 创建任务
    task = Task(
        task_id="demo-task-001",
        description="分析用户行为数据并生成报告",
        task_type=TaskType.ANALYSIS,
        harness_type=HarnessType.EXECUTION
    )

    print(f"\n📋 任务信息:")
    print(f"   ID: {task.task_id}")
    print(f"   描述: {task.description}")
    print(f"   类型: {task.task_type.value}")

    # 执行任务
    print(f"\n🎯 开始执行任务...")
    result = await harness.run(task)

    print(f"\n{'=' * 60}")
    print(f"📊 执行结果:")
    print(f"   状态: {result.status}")
    print(f"   质量评分: {result.quality_score}")
    print(f"   执行时间: {result.execution_time:.2f}秒")

    if result.output:
        print(f"\n📄 输出内容:")
        print(f"   {result.output}")

    if result.errors:
        print(f"\n❌ 错误:")
        for error in result.errors:
            print(f"   - {error}")

    # 清理
    await harness.cleanup()
    print(f"\n✅ 演示完成")


async def demo_with_dashboard():
    """演示带交互式仪表板的任务执行"""
    print("🚀 演示: ExecutionHarness 交互式监控仪表板")
    print("=" * 60)
    print("注意: 仪表板启动后，按 'q' 退出，按 'r' 刷新")
    print("      按 'w1' 查看工作中 Agent 详情")
    print("      按 's1' 查看子任务详情")
    print("=" * 60)

    # 创建 ExecutionHarness，启用仪表板
    harness = HarnessFactory.create(
        HarnessType.EXECUTION,
        config={
            "max_agents": 10,
            "enable_monitoring": True,
            "show_dashboard": True  # 启用交互式仪表板
        }
    )

    # 创建任务
    task = Task(
        task_id="demo-task-002",
        description="生成数据分析报告",
        task_type=TaskType.ANALYSIS,
        harness_type=HarnessType.EXECUTION
    )

    print(f"\n📋 任务信息:")
    print(f"   ID: {task.task_id}")
    print(f"   描述: {task.description}")

    # 执行任务（会启动仪表板）
    print(f"\n🎯 开始执行任务...")
    result = await harness.run(task)

    print(f"\n{'=' * 60}")
    print(f"📊 最终状态: {result.status}")

    # 清理
    await harness.cleanup()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ExecutionHarness 监控演示")
    parser.add_argument("--dashboard", "-d", action="store_true",
                       help="启用交互式仪表板")

    args = parser.parse_args()

    try:
        if args.dashboard:
            asyncio.run(demo_with_dashboard())
        else:
            asyncio.run(demo_with_monitoring())
    except KeyboardInterrupt:
        print("\n\n👋 演示已退出")
