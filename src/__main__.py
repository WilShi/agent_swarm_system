"""
Agent Swarm CLI 入口

提供命令行接口来运行 Agent Swarm 系统。

用法:
    python -m src [options]

示例:
    python -m src --input "分析这段代码"
    python -m src --batch tasks.txt
    python -m src --interactive
"""
import argparse
import asyncio
import sys
from pathlib import Path

# 确保 src 模块可以被导入
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.main import MultiHarnessAgentSwarm


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        prog="agent-swarm",
        description="Multi-Harness Agent Swarm System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --input "分析这段代码的性能"
  %(prog)s --batch tasks.txt
  %(prog)s --interactive
        """
    )

    parser.add_argument(
        "--input", "-i",
        type=str,
        help="Single task input to process"
    )

    parser.add_argument(
        "--batch", "-b",
        type=str,
        metavar="FILE",
        help="Process multiple tasks from a file (one per line)"
    )

    parser.add_argument(
        "--interactive", "-it",
        action="store_true",
        help="Run in interactive mode"
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        metavar="FILE",
        help="Save results to file"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0"
    )

    return parser


async def process_single_input(system: MultiHarnessAgentSwarm, user_input: str, verbose: bool = False) -> dict:
    """处理单个输入"""
    if verbose:
        print(f"Processing: {user_input}")

    result = await system.process_request(user_input)

    if verbose:
        print(f"Result: {result}")

    return result


async def process_batch(system: MultiHarnessAgentSwarm, file_path: str, verbose: bool = False) -> list[dict]:
    """批量处理任务"""
    path = Path(file_path)

    if not path.exists():
        print(f"Error: File not found: {file_path}")
        return []

    with open(path, "r", encoding="utf-8") as f:
        tasks = [line.strip() for line in f if line.strip()]

    if verbose:
        print(f"Loaded {len(tasks)} tasks from {file_path}")

    results = await system.batch_process(tasks)
    return results


async def run_interactive(system: MultiHarnessAgentSwarm, verbose: bool = False):
    """运行交互模式"""
    print("=" * 60)
    print("Multi-Harness Agent Swarm - Interactive Mode")
    print("=" * 60)
    print("Enter tasks to process (type 'quit' or 'exit' to stop):\n")

    while True:
        try:
            user_input = input("> ").strip()

            if not user_input:
                continue

            if user_input.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break

            result = await process_single_input(system, user_input, verbose)

            if result["success"]:
                print(f"[OK] Task ID: {result['task_id']}")
                print(f"     Harness: {result['harness_type']}")
                print(f"     Type: {result['task_type']}")
                print(f"     Status: {result['result'].status}")
                if hasattr(result['result'], 'output') and result['result'].output:
                    print(f"     Output: {result['result'].output.get('message', 'N/A')}")
            else:
                print(f"[ERROR] {result.get('error', 'Unknown error')}")

            print()

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except EOFError:
            print("\nGoodbye!")
            break


async def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()

    # 创建系统实例
    system = MultiHarnessAgentSwarm()

    results = []

    try:
        if args.input:
            # 单任务模式
            result = await process_single_input(system, args.input, args.verbose)
            results.append(result)

            if result["success"]:
                print(f"Task ID: {result['task_id']}")
                print(f"Harness: {result['harness_type']}")
                print(f"Status: {result['result'].status}")
            else:
                print(f"Error: {result.get('error', 'Unknown error')}")
                return 1

        elif args.batch:
            # 批量模式
            results = await process_batch(system, args.batch, args.verbose)

            success_count = sum(1 for r in results if r.get("success"))
            print(f"\nProcessed {len(results)} tasks, {success_count} successful")

        elif args.interactive:
            # 交互模式
            await run_interactive(system, args.verbose)

        else:
            # 没有参数，显示帮助
            parser.print_help()
            return 0

        # 保存结果到文件
        if args.output and results:
            import json
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, default=str)
            print(f"Results saved to: {args.output}")

        return 0

    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
