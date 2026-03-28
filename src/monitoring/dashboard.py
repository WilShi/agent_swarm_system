"""
监控仪表板 - 提供交互式监控界面
"""
import asyncio
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime

from src.monitoring.agent_monitor import AgentMonitor, AgentStatus
from src.monitoring.task_monitor import TaskMonitor, TaskStage


class MonitorDashboard:
    """监控仪表板"""

    def __init__(self, agent_monitor: AgentMonitor, task_monitor: TaskMonitor):
        self.agent_monitor = agent_monitor
        self.task_monitor = task_monitor
        self._running = False
        self._selected_agent: Optional[str] = None
        self._selected_task: Optional[str] = None

    def clear_screen(self):
        """清屏"""
        print("\033[2J\033[H", end="")

    def print_header(self, title: str):
        """打印标题"""
        print("=" * 70)
        print(f"  {title}")
        print("=" * 70)

    def print_separator(self, title: str = ""):
        """打印分隔线"""
        if title:
            print(f"\n{'─' * 20} {title} {'─' * (50 - len(title))}")
        else:
            print("─" * 70)

    def format_duration(self, seconds: float) -> str:
        """格式化时长"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds / 60:.1f}m"
        else:
            return f"{seconds / 3600:.1f}h"

    def format_progress_bar(self, progress: float, width: int = 30) -> str:
        """格式化进度条"""
        filled = int(width * progress / 100)
        bar = "█" * filled + "░" * (width - filled)
        return f"[{bar}] {progress:.0f}%"

    def render_overall_progress(self, task_id: str):
        """渲染整体进度"""
        task_info = self.task_monitor.get_task_info(task_id)
        if not task_info:
            return

        total = len(task_info.subtasks)
        completed = sum(1 for s in task_info.subtasks if s.status == "completed")
        failed = sum(1 for s in task_info.subtasks if s.status == "failed")
        in_progress = sum(1 for s in task_info.subtasks if s.status == "in_progress")

        print(f"\n📊 整体进度")
        print(f"   总任务: {total}  |  ✓完成: {completed}  |  ✗失败: {failed}  |  🔄进行中: {in_progress}")
        print(f"   {self.format_progress_bar(task_info.progress)}")
        print(f"   阶段: {task_info.stage.value}  |  耗时: {self.format_duration(task_info.duration)}")

    def render_working_agents(self) -> List[str]:
        """渲染正在工作的 Agent"""
        working = self.agent_monitor.get_working_agents()

        if not working:
            print("\n   (无)")
            return []

        agent_ids = []
        for i, agent in enumerate(working, 1):
            agent_ids.append(agent.agent_id)
            print(f"\n  [{i}] {agent.agent_name} ({agent.agent_id[:8]})")
            print(f"      状态: 🟢 运行中  |  角色: {agent.agent_role}")
            print(f"      任务: {agent.task_type or 'N/A'}")
            print(f"      描述: {agent.task_description[:50]}...")
            print(f"      进度: {self.format_progress_bar(agent.progress)}")
            print(f"      耗时: {self.format_duration(agent.elapsed_time)}")

        return agent_ids

    def render_idle_agents(self):
        """渲染空闲的 Agent"""
        idle = self.agent_monitor.get_idle_agents()

        if not idle:
            return

        print("\n   ", end="")
        for agent in idle:
            print(f"{agent.agent_name} ({agent.agent_id[:8]}) ⏸️  ", end="")
        print()

    def render_completed_agents(self) -> List[str]:
        """渲染已完成的 Agent"""
        completed = self.agent_monitor.get_completed_agents()

        if not completed:
            print("\n   (无)")
            return []

        agent_ids = []
        for i, agent in enumerate(completed, 1):
            agent_ids.append(agent.agent_id)
            status_icon = "✅" if not agent.error else "❌"
            print(f"\n  [{i}] {agent.agent_name}")
            print(f"      状态: {status_icon} {'完成' if not agent.error else '失败'}")
            print(f"      任务: {agent.task_type or 'N/A'}")
            print(f"      耗时: {self.format_duration(agent.elapsed_time)}")
            if agent.result:
                result_str = str(agent.result)[:60]
                print(f"      结果: {result_str}...")

        return agent_ids

    def render_subtasks(self, task_id: str):
        """渲染子任务列表"""
        task_info = self.task_monitor.get_task_info(task_id)
        if not task_info or not task_info.subtasks:
            return

        print(f"\n📋 子任务详情")
        for i, subtask in enumerate(task_info.subtasks, 1):
            status_icon = {
                "pending": "⏳",
                "assigned": "📋",
                "in_progress": "🔄",
                "completed": "✅",
                "failed": "❌"
            }.get(subtask.status, "❓")

            print(f"\n  [{i}] {status_icon} {subtask.task_type}")
            print(f"      描述: {subtask.description[:50]}...")
            print(f"      状态: {subtask.status}")

            if subtask.agent_name:
                print(f"      执行者: {subtask.agent_name}")

            if subtask.duration > 0:
                print(f"      耗时: {self.format_duration(subtask.duration)}")

            if subtask.result:
                result_str = str(subtask.result)[:60]
                print(f"      结果: {result_str}...")

    def render_dashboard(self, task_id: str):
        """渲染完整仪表板"""
        self.clear_screen()
        self.print_header("🤖 Agent Swarm 监控仪表板")

        # 整体进度
        self.render_overall_progress(task_id)

        # 工作中的 Agent
        self.print_separator("正在工作的 Agent")
        working_ids = self.render_working_agents()

        # 空闲的 Agent
        self.print_separator("等待中的 Agent")
        self.render_idle_agents()

        # 已完成的 Agent
        self.print_separator("已完成的 Agent")
        completed_ids = self.render_completed_agents()

        # 子任务详情
        self.render_subtasks(task_id)

        # 操作提示
        self.print_separator()
        print("\n操作: [w+数字]查看工作中Agent详情  [c+数字]查看已完成Agent详情")
        print("       [s+数字]查看子任务详情  [r]刷新  [q]退出")
        print()

        return working_ids, completed_ids

    def show_agent_detail(self, agent_id: str):
        """显示 Agent 详情"""
        agent = self.agent_monitor.get_agent_info(agent_id)
        if not agent:
            print("\n❌ Agent 不存在")
            return

        self.clear_screen()
        self.print_header(f"🔍 Agent 详情: {agent.agent_name}")

        print(f"\n  基本信息:")
        print(f"    ID: {agent.agent_id}")
        print(f"    名称: {agent.agent_name}")
        print(f"    角色: {agent.agent_role}")
        print(f"    状态: {agent.status.value}")

        if agent.current_task:
            print(f"\n  当前任务:")
            print(f"    任务ID: {agent.current_task}")
            print(f"    类型: {agent.task_type}")
            print(f"    描述: {agent.task_description}")
            print(f"    进度: {self.format_progress_bar(agent.progress)}")
            print(f"    耗时: {self.format_duration(agent.elapsed_time)}")

        if agent.result:
            print(f"\n  执行结果:")
            print(f"    {agent.result}")

        if agent.error:
            print(f"\n  错误信息:")
            print(f"    ❌ {agent.error}")

        if agent.history:
            print(f"\n  历史记录 ({len(agent.history)} 条):")
            for i, h in enumerate(agent.history[-5:], 1):
                print(f"    {i}. {h['task_type']} - {h['status']} ({h['completed_at']})")

        input("\n按 Enter 返回...")

    def show_subtask_detail(self, task_id: str, subtask_index: int):
        """显示子任务详情"""
        task_info = self.task_monitor.get_task_info(task_id)
        if not task_info or subtask_index >= len(task_info.subtasks):
            print("\n❌ 子任务不存在")
            return

        subtask = task_info.subtasks[subtask_index]

        self.clear_screen()
        self.print_header(f"🔍 子任务详情: {subtask.task_type}")

        print(f"\n  基本信息:")
        print(f"    ID: {subtask.subtask_id}")
        print(f"    类型: {subtask.task_type}")
        print(f"    状态: {subtask.status}")

        print(f"\n  描述:")
        print(f"    {subtask.description}")

        if subtask.agent_name:
            print(f"\n  执行信息:")
            print(f"    执行者: {subtask.agent_name}")
            print(f"    Agent ID: {subtask.assigned_to}")

        if subtask.start_time:
            print(f"\n  时间信息:")
            print(f"    开始: {subtask.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            if subtask.end_time:
                print(f"    结束: {subtask.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"    耗时: {self.format_duration(subtask.duration)}")

        if subtask.dependencies:
            print(f"\n  依赖任务:")
            for dep in subtask.dependencies:
                print(f"    - {dep}")

        if subtask.result:
            print(f"\n  执行结果:")
            print(f"    {subtask.result}")

        if subtask.error:
            print(f"\n  错误信息:")
            print(f"    ❌ {subtask.error}")

        input("\n按 Enter 返回...")

    async def run(self, task_id: str):
        """运行监控仪表板"""
        self._running = True

        while self._running:
            try:
                working_ids, completed_ids = self.render_dashboard(task_id)

                # 等待用户输入（带超时自动刷新）
                cmd = await asyncio.wait_for(
                    asyncio.to_thread(input, "> "),
                    timeout=2.0
                )

                cmd = cmd.strip().lower()

                if cmd == 'q':
                    self._running = False
                elif cmd == 'r':
                    continue
                elif cmd.startswith('w') and len(cmd) > 1:
                    try:
                        idx = int(cmd[1:]) - 1
                        if 0 <= idx < len(working_ids):
                            self.show_agent_detail(working_ids[idx])
                    except ValueError:
                        pass
                elif cmd.startswith('c') and len(cmd) > 1:
                    try:
                        idx = int(cmd[1:]) - 1
                        if 0 <= idx < len(completed_ids):
                            self.show_agent_detail(completed_ids[idx])
                    except ValueError:
                        pass
                elif cmd.startswith('s') and len(cmd) > 1:
                    try:
                        idx = int(cmd[1:]) - 1
                        self.show_subtask_detail(task_id, idx)
                    except ValueError:
                        pass

            except asyncio.TimeoutError:
                # 超时自动刷新
                continue
            except KeyboardInterrupt:
                self._running = False

        print("\n👋 监控已退出")
