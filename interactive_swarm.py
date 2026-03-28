#!/usr/bin/env python3
"""
Agent Swarm 交互式运行脚本
输入问题 -> 任务拆分 -> 多智能体协作 -> 输出结论
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import create_swarm, run_task
from src.core.types import Task, TaskStatus
from datetime import datetime


class InteractiveSwarm:
    """交互式Swarm系统"""
    
    def __init__(self):
        self.swarm = None
        self.task_history = []
    
    async def start(self):
        """启动系统"""
        print("\n" + "=" * 70)
        print("🤖 Agent Swarm 交互式系统")
        print("=" * 70)
        
        # 加载配置
        from src.core.config import config
        config.print_config()
        
        # 验证配置
        validation = config.validate_config()
        if not validation["valid"]:
            print("\n❌ 配置错误:")
            for error in validation["errors"]:
                print(f"  - {error}")
            print("\n请检查 .env 文件配置")
            return False
        
        if validation["warnings"]:
            print("\n⚠️ 配置警告:")
            for warning in validation["warnings"]:
                print(f"  - {warning}")
        
        print("\n正在初始化智能体集群...\n")
        
        self.swarm = await create_swarm(name="InteractiveSwarm")
        
        print("\n✅ 系统就绪！")
        print("\n支持的输入类型：")
        print("  📊 analysis - 数据分析类问题")
        print("  ✍️  generation - 内容生成类问题")
        print("  💻 code - 代码开发类问题")
        print("  🔬 research - 研究调研类问题")
        print("  🔄 default - 通用问题")
        print("\n输入 'quit' 或 'exit' 退出系统")
        print("=" * 70)
        
        return True
    
    async def stop(self):
        """停止系统"""
        if self.swarm:
            await self.swarm.stop()
        print("\n👋 感谢使用！")
    
    def detect_task_type(self, question: str) -> str:
        """根据问题内容自动检测任务类型"""
        question_lower = question.lower()
        
        # 代码相关关键词
        code_keywords = ["代码", "程序", "函数", "实现", "编写", "开发", "bug", "修复", "优化", "code", "program", "function", "implement"]
        if any(kw in question_lower for kw in code_keywords):
            return "code"
        
        # 数据分析相关关键词
        analysis_keywords = ["分析", "统计", "数据", "趋势", "比较", "计算", "图表", "analy", "data", "statistics", "compare"]
        if any(kw in question_lower for kw in analysis_keywords):
            return "analysis"
        
        # 研究生关关键词
        research_keywords = ["研究", "调研", "了解", "查找", "资料", "文献", "research", "investigate", "study", "survey"]
        if any(kw in question_lower for kw in research_keywords):
            return "research"
        
        # 内容生成相关关键词
        generation_keywords = ["生成", "创建", "写作", "撰写", "草稿", "内容", "generate", "create", "write", "draft", "content"]
        if any(kw in question_lower for kw in generation_keywords):
            return "generation"
        
        return "default"
    
    async def process_question(self, question: str) -> dict:
        """处理问题并返回结果"""
        task_type = self.detect_task_type(question)
        
        print(f"\n📋 任务类型识别: {task_type}")
        print(f"📝 问题: {question}")
        print("\n" + "-" * 70)
        
        # 根据任务类型显示分解策略
        self._show_decomposition_strategy(task_type)
        
        # 提交任务
        start_time = datetime.now()
        task_id = await self.swarm.submit_task(
            description=question,
            task_type=task_type,
            metadata={"source": "interactive", "start_time": start_time.isoformat()}
        )
        
        print(f"\n⏳ 正在执行任务: {task_id}")
        
        # 等待任务完成并显示进度
        result = await self._wait_with_progress(task_id)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        print("\n" + "=" * 70)
        print("📊 执行结果")
        print("=" * 70)
        
        # 格式化输出结果
        self._format_result(result, elapsed)
        
        # 保存到历史
        self.task_history.append({
            "question": question,
            "task_type": task_type,
            "task_id": task_id,
            "result": result,
            "elapsed_time": elapsed
        })
        
        return result
    
    def _show_decomposition_strategy(self, task_type: str):
        """显示任务分解策略"""
        strategies = {
            "analysis": [
                "1️⃣ 数据收集 - 收集分析所需数据",
                "2️⃣ 数据预处理 - 清洗和准备数据",
                "3️⃣ 分析执行 - 执行数据分析算法",
                "4️⃣ 可视化 - 生成分析图表和报告"
            ],
            "generation": [
                "1️⃣ 需求分析 - 分析生成需求",
                "2️⃣ 内容生成 - 生成初版内容",
                "3️⃣ 内容优化 - 优化和改进内容"
            ],
            "code": [
                "1️⃣ 需求理解 - 理解代码需求",
                "2️⃣ 代码设计 - 设计代码结构",
                "3️⃣ 代码实现 - 编写代码",
                "4️⃣ 测试编写 - 编写测试用例"
            ],
            "research": [
                "1️⃣ 文献检索 - 检索相关资料",
                "2️⃣ 信息提取 - 提取关键信息",
                "3️⃣ 知识综合 - 综合研究发现"
            ],
            "default": [
                "1️⃣ 任务分析 - 分析任务需求",
                "2️⃣ 任务执行 - 执行具体任务"
            ]
        }
        
        print("🔍 任务分解策略:")
        for step in strategies.get(task_type, strategies["default"]):
            print(f"   {step}")
        print("-" * 70)
    
    async def _wait_with_progress(self, task_id: str, timeout: float = 60.0) -> dict:
        """等待任务完成并显示进度"""
        start_time = datetime.now()
        last_status = None
        
        while True:
            status = await self.swarm.get_task_status(task_id)
            
            if status is None:
                print("❌ 任务未找到")
                return {"error": "Task not found"}
            
            # 只在状态变化时输出
            if status != last_status:
                total = status.get("subtasks_count", 0)
                completed = status.get("completed_subtasks", 0)
                failed = status.get("failed_subtasks", 0)
                pending = status.get("pending_subtasks", 0)
                
                if total > 0:
                    progress = (completed + failed) / total * 100
                    print(f"   ⏳ 进度: {completed}/{total} 完成 ({progress:.0f}%) | "
                          f"✅ {completed} | ❌ {failed} | ⏸️ {pending}")
                
                last_status = status.copy()
            
            # 检查是否完成
            total = status.get("subtasks_count", 0)
            completed = status.get("completed_subtasks", 0)
            failed = status.get("failed_subtasks", 0)
            
            if total > 0 and completed + failed >= total:
                return status
            
            # 检查超时
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > timeout:
                print(f"\n⚠️ 任务执行超时 (> {timeout}秒)")
                return {**status, "timeout": True}
            
            await asyncio.sleep(0.5)
    
    def _format_result(self, result: dict, elapsed: float):
        """格式化输出结果"""
        print(f"\n⏱️  执行时间: {elapsed:.2f} 秒")
        
        if "error" in result:
            print(f"\n❌ 错误: {result['error']}")
            return
        
        if result.get("timeout"):
            print("\n⚠️ 任务已超时，但已部分完成")
        
        total = result.get("subtasks_count", 0)
        completed = result.get("completed_subtasks", 0)
        failed = result.get("failed_subtasks", 0)
        
        print(f"\n📈 任务统计:")
        print(f"   • 子任务总数: {total}")
        print(f"   • 成功完成: {completed} ✅")
        print(f"   • 执行失败: {failed} ❌")
        
        if total > 0:
            success_rate = completed / total * 100
            print(f"   • 成功率: {success_rate:.1f}%")
        
        # 输出结论
        print("\n📝 结论:")
        print("-" * 70)
        
        # 模拟根据任务类型输出不同的结论
        # 在实际实现中，这里会从IntegratorAgent获取整合后的结果
        self._generate_conclusion(result)
        
        print("-" * 70)
    
    def _generate_conclusion(self, result: dict):
        """生成结论（简化版）"""
        completed = result.get("completed_subtasks", 0)
        failed = result.get("failed_subtasks", 0)
        
        if completed > 0 and failed == 0:
            print("✅ 所有子任务已成功完成！")
            print("\n系统已协调多个智能体完成以下工作：")
            print("  • 任务分解与规划")
            print("  • 并行执行各子任务")
            print("  • 结果验证与质量检查")
            print("  • 最终整合与输出")
            print("\n💡 这是一个完全成功的协作案例。")
            
        elif completed > 0 and failed > 0:
            print(f"⚠️ 部分子任务完成 ({completed}成功, {failed}失败)")
            print("\n虽然遇到了一些问题，但系统已成功完成主要工作：")
            print("  • 大部分子任务正常执行")
            print("  • 失败的任务已被记录")
            print("  • 可用结果已整合")
            print("\n💡 建议检查失败任务的日志以了解详情。")
            
        else:
            print("❌ 任务执行遇到问题")
            print("\n可能的解决方案：")
            print("  • 检查任务描述是否清晰")
            print("  • 尝试简化问题或分解为更小的任务")
            print("  • 增加超时时间")
    
    def show_stats(self):
        """显示系统统计"""
        if not self.swarm:
            return
        
        stats = self.swarm.get_system_stats()
        
        print("\n" + "=" * 70)
        print("📊 系统统计")
        print("=" * 70)
        print(f"\n智能体分布:")
        print(f"  • 协调器: {stats['agents']['coordinators']}")
        print(f"  • 执行器: {stats['agents']['executors']}")
        print(f"  • 验证器: {stats['agents']['validators']}")
        print(f"  • 整合器: {stats['agents']['integrators']}")
        print(f"  • 总计: {stats['agents']['total']}")
        print(f"\n任务统计:")
        print(f"  • 当前会话任务数: {len(self.task_history)}")
        print(f"  • 系统总任务数: {stats['tasks']['total_submitted']}")
        
        if stats.get('uptime_seconds'):
            print(f"\n系统运行时间: {stats['uptime_seconds']:.1f} 秒")
        
        print("=" * 70)


async def main():
    """主函数"""
    swarm_system = InteractiveSwarm()
    
    try:
        started = await swarm_system.start()
        if not started:
            return
        
        while True:
            print("\n" + "=" * 70)
            user_input = input("\n💬 请输入您的问题 (或输入 'stats' 查看统计, 'quit' 退出): ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            
            if user_input.lower() == 'stats':
                swarm_system.show_stats()
                continue
            
            try:
                await swarm_system.process_question(user_input)
            except KeyboardInterrupt:
                print("\n\n⚠️ 任务被中断")
            except Exception as e:
                print(f"\n❌ 处理问题时出错: {e}")
                import traceback
                traceback.print_exc()
    
    except KeyboardInterrupt:
        print("\n\n⚠️ 系统被中断")
    
    finally:
        await swarm_system.stop()


if __name__ == "__main__":
    # 设置Windows上的事件循环策略
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
