"""
Agent Swarm 基础示例
展示三层架构的基本使用方法
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import create_swarm, run_task


async def basic_demo():
    """基础演示"""
    print("\n" + "=" * 70)
    print("Agent Swarm 基础示例")
    print("=" * 70)
    
    # 创建并启动Swarm
    swarm = await create_swarm(name="DemoSwarm")
    
    try:
        # 示例1: 分析类任务
        print("\n📊 示例1: 数据分析任务")
        result1 = await run_task(
            swarm,
            description="分析用户行为数据，识别关键趋势",
            task_type="analysis",
            wait=True,
            timeout=30.0
        )
        print(f"结果: {result1}")
        
        # 示例2: 生成类任务
        print("\n✍️ 示例2: 内容生成任务")
        result2 = await run_task(
            swarm,
            description="生成一份产品描述文档",
            task_type="generation",
            wait=True,
            timeout=30.0
        )
        print(f"结果: {result2}")
        
        # 示例3: 代码类任务
        print("\n💻 示例3: 代码开发任务")
        result3 = await run_task(
            swarm,
            description="实现一个用户认证模块",
            task_type="code",
            wait=True,
            timeout=30.0
        )
        print(f"结果: {result3}")
        
        # 示例4: 研究类任务
        print("\n🔬 示例4: 研究任务")
        result4 = await run_task(
            swarm,
            description="调研最新的机器学习算法",
            task_type="research",
            wait=True,
            timeout=30.0
        )
        print(f"结果: {result4}")
        
        # 获取系统统计
        print("\n📈 系统统计")
        stats = swarm.get_system_stats()
        print(f"总Agent数: {stats['agents']['total']}")
        print(f"提交任务数: {stats['tasks']['total_submitted']}")
        print(f"运行时间: {stats.get('uptime_seconds', 0):.2f}秒")
        
    finally:
        # 停止Swarm
        await swarm.stop()


async def concurrent_tasks_demo():
    """并发任务演示"""
    print("\n" + "=" * 70)
    print("并发任务示例")
    print("=" * 70)
    
    swarm = await create_swarm(name="ConcurrentSwarm")
    
    try:
        # 提交多个并发任务
        print("\n🚀 提交5个并发任务...")
        
        tasks = [
            run_task(swarm, f"并发任务 {i+1}", "default", wait=False)
            for i in range(5)
        ]
        
        # 等待所有任务提交完成
        results = await asyncio.gather(*tasks)
        
        print("\n任务已提交:")
        for r in results:
            print(f"  - {r['task_id']}: {r['status']}")
        
        # 等待一段时间让任务执行
        await asyncio.sleep(5)
        
        # 获取系统统计
        stats = swarm.get_system_stats()
        print(f"\n总提交任务数: {stats['tasks']['total_submitted']}")
        
    finally:
        await swarm.stop()


async def custom_capabilities_demo():
    """自定义能力演示"""
    print("\n" + "=" * 70)
    print("动态添加执行器示例")
    print("=" * 70)
    
    swarm = await create_swarm(name="DynamicSwarm")
    
    try:
        print("\n初始Agent数:", swarm.get_system_stats()['agents']['total'])
        
        # 动态添加执行器
        print("\n➕ 添加自定义执行器...")
        new_agent_id = await swarm.add_executor(
            capabilities=["custom_ml", "data_analysis", "visualization"]
        )
        print(f"新执行器ID: {new_agent_id}")
        
        print("\n当前Agent数:", swarm.get_system_stats()['agents']['total'])
        
        # 提交一个任务
        result = await run_task(
            swarm,
            "使用自定义能力处理数据",
            "analysis",
            wait=True,
            timeout=20.0
        )
        print(f"\n任务结果: {result}")
        
        # 移除执行器
        print("\n➖ 移除执行器...")
        await swarm.remove_executor(new_agent_id)
        print("当前Agent数:", swarm.get_system_stats()['agents']['total'])
        
    finally:
        await swarm.stop()


async def main():
    """主函数"""
    print("\n🤖 Agent Swarm 系统演示")
    print("=" * 70)
    
    # 运行基础示例
    await basic_demo()
    
    # 运行并发示例
    await concurrent_tasks_demo()
    
    # 运行动态扩展示例
    await custom_capabilities_demo()
    
    print("\n" + "=" * 70)
    print("所有演示完成!")
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
