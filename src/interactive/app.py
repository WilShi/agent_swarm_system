#!/usr/bin/env python3
"""
交互式 CLI 应用

提供类似 ChatGPT 的交互式命令行界面
"""
import asyncio
import json
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter, Completer, Completion
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from prompt_toolkit.shortcuts import clear

from src.classifier import TaskClassifier
from src.harness import create_harness, get_available_harness_types
from src.core.types import HarnessType, Task, TaskType


class InteractiveApp:
    """交互式应用主类"""

    def __init__(self):
        self.classifier = TaskClassifier()
        self.context: List[Dict[str, Any]] = []
        self.current_harness: Optional[str] = None
        self.session_file: Optional[str] = None
        self.running = True

        # 命令补全
        self.commands = [
            '/help', '/mode', '/harness', '/list',
            '/clear', '/history', '/save', '/load',
            '/monitor', '/dashboard', '/config', '/quit', '/exit'
        ]
        self.harness_types = get_available_harness_types()

        # 创建 prompt session
        self.session = PromptSession(
            completer=self._create_completer(),
            style=self._create_style()
        )

        # 快捷键绑定
        self.kb = self._create_keybindings()

    def _create_completer(self) -> Completer:
        """创建命令补全器"""
        class CommandCompleter(Completer):
            def __init__(self, app):
                self.app = app

            def get_completions(self, document, complete_event):
                text = document.text
                word = document.get_word_before_cursor()

                # 命令补全
                if text.startswith('/'):
                    for cmd in self.app.commands:
                        if cmd.startswith(text):
                            yield Completion(cmd, start_position=-len(text))

                # Harness 类型补全
                if '/harness ' in text:
                    for ht in self.app.harness_types:
                        if ht.startswith(word):
                            yield Completion(ht, start_position=-len(word))

        return CommandCompleter(self)

    def _create_style(self) -> Style:
        """创建样式"""
        return Style.from_dict({
            'prompt': '#00aa00 bold',
            'user': '#0088ff',
            'assistant': '#00aa00',
            'system': '#888888',
            'error': '#ff0000',
            'warning': '#ffaa00',
            'info': '#00aaaa',
        })

    def _create_keybindings(self) -> KeyBindings:
        """创建快捷键绑定"""
        kb = KeyBindings()

        @kb.add('c-c')
        def _(event):
            """Ctrl+C - 中断"""
            print("\n\n⚠️  中断")

        @kb.add('c-d')
        def _(event):
            """Ctrl+D - 退出"""
            self.running = False
            event.app.exit()

        @kb.add('c-l')
        def _(event):
            """Ctrl+L - 清屏"""
            clear()
            self._print_header()

        return kb

    def _print_header(self):
        """打印头部信息"""
        print("""
🤖 Agent Swarm Interactive CLI v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

输入 /help 查看帮助，或输入任务开始对话
输入 /quit 退出
""")

    def _get_prompt(self) -> str:
        """获取提示符"""
        harness_info = f"[{self.current_harness}]" if self.current_harness else "[auto]"
        return f"\n👤 {harness_info} > "

    async def run(self):
        """主循环"""
        self._print_header()

        while self.running:
            try:
                # 获取输入
                user_input = await self.session.prompt_async(
                    self._get_prompt(),
                    key_bindings=self.kb
                )

                if not user_input.strip():
                    continue

                # 解析输入
                if user_input.startswith('/'):
                    await self._handle_command(user_input)
                else:
                    await self._handle_chat(user_input)

            except KeyboardInterrupt:
                continue
            except EOFError:
                break

        print("\n👋 再见！\n")

    async def _handle_command(self, cmd: str):
        """处理命令"""
        parts = cmd.strip().split()
        command = parts[0].lower()
        args = parts[1:]

        handlers = {
            '/help': self._cmd_help,
            '/harness': self._cmd_harness,
            '/list': self._cmd_list,
            '/clear': self._cmd_clear,
            '/history': self._cmd_history,
            '/save': self._cmd_save,
            '/load': self._cmd_load,
            '/config': self._cmd_config,
            '/quit': self._cmd_quit,
            '/exit': self._cmd_quit,
        }

        handler = handlers.get(command)
        if handler:
            await handler(args)
        else:
            print(f"❌ 未知命令: {command}")
            print("输入 /help 查看可用命令")

    async def _handle_chat(self, text: str):
        """处理聊天输入"""
        # 添加到上下文
        self._add_message("user", text)

        try:
            # 分类任务
            print("🔍 正在分析任务...")
            classification = await self.classifier.classify(text)

            harness_type = self.current_harness or classification.harness_type.value

            print(f"📊 分类结果: {classification.task_type.value} (置信度: {classification.confidence:.0%})")
            print(f"🚀 使用 Harness: {harness_type}")
            print()

            # 创建 Harness（不使用 Swarm，直接使用 LLM）
            harness = create_harness(
                harness_type,
                config={
                    "custom_params": {
                        "enable_monitoring": False,  # 禁用监控，避免 Swarm
                        "show_dashboard": False,
                        "language": "python",
                        "max_sources": 5
                    }
                }
            )

            # 创建任务
            task = Task(
                description=text,
                task_type=classification.task_type,
                harness_type=HarnessType(harness_type)
            )

            # 执行任务（带超时）
            print("⏳ 执行任务中... (按 Ctrl+C 中断)")
            try:
                result = await asyncio.wait_for(harness.run(task), timeout=60.0)
            except asyncio.TimeoutError:
                print("\n⚠️  任务执行超时 (60秒)")
                print("💡 提示: 任务过于复杂，请尝试简化描述")
                await harness.cleanup()
                return

            # 显示结果
            print(f"\n✅ 任务完成！")
            print(f"   状态: {result.status}")
            print(f"   质量评分: {result.quality_score:.2f}")
            print(f"   执行时间: {result.execution_time:.2f}秒")

            if result.output:
                print(f"\n📤 输出:")
                if isinstance(result.output, dict):
                    for key, value in result.output.items():
                        if key in ['code', 'report', 'result']:
                            print(f"\n{key}:")
                            print(f"```")
                            print(value)
                            print(f"```")
                        else:
                            print(f"  {key}: {value}")
                else:
                    print(result.output)

            if result.errors:
                print(f"\n❌ 错误:")
                for error in result.errors:
                    print(f"  - {error}")

            # 添加到上下文
            self._add_message("assistant", {
                "status": result.status,
                "output": result.output,
                "quality_score": result.quality_score
            })

        except Exception as e:
            print(f"\n❌ 执行失败: {e}")
            self._add_message("system", f"错误: {e}")

    def _add_message(self, role: str, content: Any):
        """添加消息到上下文"""
        self.context.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

    # 命令处理函数

    async def _cmd_help(self, args: List[str]):
        """帮助命令"""
        print("""
📋 可用命令:

  /help                      - 显示帮助
  /harness <type>            - 设置默认 Harness
  /list                      - 列出所有 Harness
  /clear                     - 清空上下文
  /history                   - 显示对话历史
  /save <file>               - 保存会话到文件
  /load <file>               - 从文件加载会话
  /config                    - 显示当前配置
  /quit, /exit               - 退出

快捷键:
  Ctrl+C                     - 中断当前操作
  Ctrl+D                     - 退出
  Ctrl+L                     - 清屏
  Tab                        - 命令补全
  ↑/↓                        - 历史记录
""")

    async def _cmd_harness(self, args: List[str]):
        """设置 Harness"""
        if not args:
            print(f"当前 Harness: {self.current_harness or 'auto'}")
            print("可用 Harness:", ", ".join(self.harness_types))
            return

        harness_type = args[0]
        if harness_type in self.harness_types:
            self.current_harness = harness_type
            print(f"✅ 默认 Harness 已设置为: {harness_type}")
        else:
            print(f"❌ 未知的 Harness: {harness_type}")
            print("可用 Harness:", ", ".join(self.harness_types))

    async def _cmd_list(self, args: List[str]):
        """列出 Harness"""
        print("📋 可用的 Harness 类型:\n")
        descriptions = {
            'execution': '通用任务执行',
            'code': '代码生成与重构',
            'debug': '错误诊断与修复',
            'research': '研究调研',
            'test': '测试验证',
            'claude_code': '复杂多步骤任务'
        }
        for ht in self.harness_types:
            marker = " ✓" if ht == self.current_harness else ""
            print(f"  • {ht:12} - {descriptions.get(ht, '未知')}{marker}")
        print(f"\n总计: {len(self.harness_types)} 种 Harness")

    async def _cmd_clear(self, args: List[str]):
        """清空上下文"""
        self.context.clear()
        print("✅ 上下文已清空")

    async def _cmd_history(self, args: List[str]):
        """显示历史"""
        if not self.context:
            print("暂无对话历史")
            return

        print(f"\n📜 对话历史 ({len(self.context)} 条):\n")
        for i, msg in enumerate(self.context, 1):
            role_icon = {"user": "👤", "assistant": "🤖", "system": "⚙️"}.get(msg['role'], "?")
            print(f"[{i}] {role_icon} {msg['role']}: {str(msg['content'])[:100]}...")

    async def _cmd_save(self, args: List[str]):
        """保存会话"""
        if not args:
            print("用法: /save <文件名>")
            return

        filename = args[0]
        data = {
            "context": self.context,
            "current_harness": self.current_harness,
            "saved_at": datetime.now().isoformat()
        }

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✅ 会话已保存到: {filename}")
        except Exception as e:
            print(f"❌ 保存失败: {e}")

    async def _cmd_load(self, args: List[str]):
        """加载会话"""
        if not args:
            print("用法: /load <文件名>")
            return

        filename = args[0]
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.context = data.get("context", [])
            self.current_harness = data.get("current_harness")

            print(f"✅ 会话已从 {filename} 加载")
            print(f"   上下文: {len(self.context)} 条消息")
            print(f"   Harness: {self.current_harness or 'auto'}")
        except Exception as e:
            print(f"❌ 加载失败: {e}")

    async def _cmd_config(self, args: List[str]):
        """显示配置"""
        print("""
⚙️ 当前配置:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
默认 Harness: {harness}
上下文长度: {context_len} 条
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(
            harness=self.current_harness or "auto (自动选择)",
            context_len=len(self.context)
        ))

    async def _cmd_quit(self, args: List[str]):
        """退出"""
        self.running = False


async def main():
    """入口函数"""
    app = InteractiveApp()
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
