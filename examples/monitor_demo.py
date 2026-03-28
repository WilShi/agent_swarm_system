"""
监控仪表板演示
展示如何使用监控功能实时查看 Agent 工作状态
"""
import asyncio
import sys
sys.path.insert(0, '/Users/wilson/Documents/研究/AI研究课题/智能体群体智能/agent_swarm_project')

from src.monitoring.agent_monitor import AgentMonitor, AgentStatus
from src.monitoring.task_monitor import TaskMonitor, TaskStage
from src.monitoring.dashboard import MonitorDashboard


async def demo_monitoring():
    """演示监控功能"""
    print("🚀 启动监控演示...")

    # 创建监控器
    agent_monitor = AgentMonitor()
    task_monitor = TaskMonitor()

    # 注册一些模拟的 Agent
    agents = [
        ("exec-001", "Executor-1", "executor"),
        ("exec-002", "Executor-2", "executor"),
        ("exec-003", "Executor-3", "executor"),
        ("val-001", "Validator-1", "validator"),
        ("val-002", "Validator-2", "validator"),
        ("int-001", "Integrator-1", "integrator"),
    ]

    for agent_id, name, role in agents:
        agent_monitor.register_agent(agent_id, name, role)

    # 注册任务
    task_id = "task-001"
    task_monitor.register_task(task_id, "分析用户行为数据", "analysis")
    task_monitor.update_stage(task_id, TaskStage.EXECUTING)

    # 注册子任务
    subtasks = [
        ("sub-001", "data_collection", "收集用户行为数据"),
        ("sub-002", "data_preprocessing", "预处理数据"),
        ("sub-003", "analysis_execution", "执行数据分析"),
        ("sub-004", "visualization", "生成可视化报告"),
    ]

    for subtask_id, task_type, desc in subtasks:
        task_monitor.register_subtask(task_id, subtask_id, task_type, desc)

    # 模拟 Agent 工作状态变化
    print("\n📊 模拟 Agent 工作状态...")

    # Executor-1 完成数据收集
    agent_monitor.update_agent_status(
        "exec-001", AgentStatus.COMPLETED,
        task_id="sub-001",
        task_type="data_collection",
        result="成功收集 10000 条用户记录"
    )
    task_monitor.update_subtask_status("sub-001", "completed", "exec-001", "Executor-1")
    task_monitor.update_subtask_result("sub-001", "10000 条记录")

    # Executor-2 正在进行数据预处理
    agent_monitor.update_agent_status(
        "exec-002", AgentStatus.WORKING,
        task_id="sub-002",
        task_type="data_preprocessing",
        task_description="预处理数据: 分析用户行为数据",
        progress=60.0
    )
    task_monitor.update_subtask_status("sub-002", "in_progress", "exec-002", "Executor-2")

    # Executor-3 正在进行分析执行
    agent_monitor.update_agent_status(
        "exec-003", AgentStatus.WORKING,
        task_id="sub-003",
        task_type="analysis_execution",
        task_description="执行数据分析: 分析用户行为数据",
        progress=25.0
    )
    task_monitor.update_subtask_status("sub-003", "in_progress", "exec-003", "Executor-3")

    # 更新任务进度
    task_monitor._update_progress(task_id)

    print("✅ 模拟数据准备完成")
    print("\n🖥️  启动监控仪表板...")
    print("提示: 按 'r' 刷新, 'q' 退出, 'w1' 查看工作中Agent详情, 's1' 查看子任务详情\n")

    # 启动监控仪表板
    dashboard = MonitorDashboard(agent_monitor, task_monitor)
    await dashboard.run(task_id)


if __name__ == "__main__":
    try:
        asyncio.run(demo_monitoring())
    except KeyboardInterrupt:
        print("\n\n👋 演示已退出")
