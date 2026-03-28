#!/usr/bin/env python3
"""
Agent Swarm CLI - 命令行工具

提供命令行接口来控制和使用 Multi-Harness Agent Swarm 系统
"""
import asyncio
import argparse
import sys
import json
from typing import Optional
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.harness import HarnessFactory, create_harness, get_available_harness_types
from src.classifier import TaskClassifier
from src.core.types import HarnessType, Task, TaskType


class AgentSwarmCLI:
    """Agent Swarm CLI 主类"""

    def __init__(self):
        self.classifier = TaskClassifier()

    async def classify_task(self, description: str) -> dict:
        """分类任务"""
        result = await self.classifier.classify(description)
        return {
            "intent": result.intent.primary_intent,
            "task_type": result.task_type.value,
            "harness_type": result.harness_type.value,
            "confidence": result.confidence,
            "reasoning": result.reasoning
        }

    async def execute_task(self, description: str, harness_type: Optional[str] = None,
                          enable_monitoring: bool = False,
                          show_dashboard: bool = False) -> dict:
        """执行任务"""
        # 如果没有指定 harness_type，自动分类
        if harness_type is None:
            classification = await self.classifier.classify(description)
            harness_type = classification.harness_type.value

        # 创建 Harness
        harness = create_harness(
            harness_type,
            config={
                "custom_params": {
                    "enable_monitoring": enable_monitoring,
                    "show_dashboard": show_dashboard
                }
            }
        )

        # 创建任务
        task = Task(
            description=description,
            task_type=TaskType.GENERAL,
            harness_type=HarnessType(harness_type)
        )

        # 执行任务
        result = await harness.run(task)

        return {
            "task_id": result.task_id,
            "status": result.status,
            "output": result.output,
            "quality_score": result.quality_score,
            "execution_time": result.execution_time,
            "errors": result.errors
        }

    def list_harnesses(self) -> list:
        """列出可用的 Harness"""
        return get_available_harness_types()


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        prog="agent-swarm",
        description="Multi-Harness Agent Swarm CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 自动分类并执行任务
  agent-swarm execute "帮我写个Python函数"

  # 使用特定 Harness
  agent-swarm execute "分析这段代码" --harness code

  # 启用监控仪表板
  agent-swarm execute "研究AI发展趋势" --harness research --dashboard

  # 只分类任务
  agent-swarm classify "生成测试用例"

  # 列出所有 Harness
  agent-swarm list
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # execute 命令
    execute_parser = subparsers.add_parser(
        "execute",
        help="执行任务",
        description="执行一个任务，自动或手动选择 Harness"
    )
    execute_parser.add_argument(
        "description",
        help="任务描述"
    )
    execute_parser.add_argument(
        "--harness", "-H",
        choices=get_available_harness_types(),
        help="指定 Harness 类型（默认自动选择）"
    )
    execute_parser.add_argument(
        "--monitor", "-m",
        action="store_true",
        help="启用监控"
    )
    execute_parser.add_argument(
        "--dashboard", "-d",
        action="store_true",
        help="启用交互式仪表板"
    )
    execute_parser.add_argument(
        "--output", "-o",
        help="输出结果到文件"
    )
    execute_parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出"
    )

    # classify 命令
    classify_parser = subparsers.add_parser(
        "classify",
        help="分类任务",
        description="分析任务并推荐最佳 Harness"
    )
    classify_parser.add_argument(
        "description",
        help="任务描述"
    )
    classify_parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出"
    )

    # list 命令
    list_parser = subparsers.add_parser(
        "list",
        help="列出 Harness",
        description="列出所有可用的 Harness 类型"
    )

    # info 命令
    info_parser = subparsers.add_parser(
        "info",
        help="显示系统信息",
        description="显示 Agent Swarm 系统信息"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    cli = AgentSwarmCLI()

    if args.command == "execute":
        print(f"🚀 执行任务: {args.description}")
        if args.harness:
            print(f"   使用 Harness: {args.harness}")
        else:
            print("   自动选择 Harness...")

        if args.dashboard:
            print("   启用交互式仪表板...")
        elif args.monitor:
            print("   启用监控...")

        print()

        try:
            result = await cli.execute_task(
                args.description,
                harness_type=args.harness,
                enable_monitoring=args.monitor or args.dashboard,
                show_dashboard=args.dashboard
            )

            if args.json:
                output = json.dumps(result, indent=2, ensure_ascii=False)
            else:
                output = f"""
✅ 任务完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
任务ID: {result['task_id']}
状态: {result['status']}
质量评分: {result['quality_score']:.2f}
执行时间: {result['execution_time']:.2f}秒

输出:
{json.dumps(result['output'], indent=2, ensure_ascii=False) if result['output'] else 'None'}

{('错误:\n' + '\n'.join(result['errors'])) if result['errors'] else ''}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

            print(output)

            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(output)
                print(f"\n💾 结果已保存到: {args.output}")

        except Exception as e:
            print(f"\n❌ 执行失败: {e}")
            sys.exit(1)

    elif args.command == "classify":
        print(f"🔍 分析任务: {args.description}\n")

        try:
            result = await cli.classify_task(args.description)

            if args.json:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print(f"""
📊 分类结果
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
意图: {result['intent']}
任务类型: {result['task_type']}
推荐 Harness: {result['harness_type']}
置信度: {result['confidence']:.2%}

推理:
{result['reasoning']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")

        except Exception as e:
            print(f"\n❌ 分类失败: {e}")
            sys.exit(1)

    elif args.command == "list":
        harnesses = cli.list_harnesses()

        print("📋 可用的 Harness 类型:\n")
        for ht in harnesses:
            print(f"  • {ht}")

        print(f"\n总计: {len(harnesses)} 种 Harness")

    elif args.command == "info":
        print("""
🤖 Multi-Harness Agent Swarm System
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

版本: 1.0.0
作者: Wilson
仓库: https://github.com/WilShi/agent_swarm_system

支持的 Harness:
  • execution  - 通用任务执行
  • code       - 代码生成与重构
  • debug      - 错误诊断修复
  • research   - 研究调研
  • test       - 测试验证
  • claude_code - 复杂多步骤任务

功能特性:
  ✅ 智能任务分类
  ✅ 自动 Harness 选择
  ✅ Agent Swarm 架构
  ✅ 实时监控
  ✅ 交互式仪表板

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")


if __name__ == "__main__":
    asyncio.run(main())
