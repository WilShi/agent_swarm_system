# 交互式 CLI 设计文档

## 设计目标

创建一个类似 ChatGPT CLI 的交互式界面，支持：
- 多轮对话
- 上下文保持
- 命令补全
- 历史记录
- 实时显示执行进度

## 交互模式架构

```
┌─────────────────────────────────────────────────────────────┐
│                    交互式 CLI 架构                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Input     │───▶│   Parser    │───▶│   Router    │     │
│  │   Handler   │    │             │    │             │     │
│  └─────────────┘    └─────────────┘    └──────┬──────┘     │
│                                                 │           │
│                    ┌────────────────────────────┼──────┐    │
│                    │                            │      │    │
│                    ▼                            ▼      ▼    │
│              ┌─────────┐  ┌─────────┐  ┌─────────┐         │
│              │  Chat   │  │ Command │  │  Task   │         │
│              │  Mode   │  │  Mode   │  │  Mode   │         │
│              └────┬────┘  └────┬────┘  └────┬────┘         │
│                   │            │            │               │
│                   └────────────┼────────────┘               │
│                                ▼                            │
│                         ┌─────────────┐                     │
│                         │   Engine    │                     │
│                         │  (Harness)  │                     │
│                         └──────┬──────┘                     │
│                                │                            │
│                         ┌──────┴──────┐                     │
│                         │   Output    │                     │
│                         │  Formatter  │                     │
│                         └─────────────┘                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 交互模式类型

### 1. 聊天模式 (Chat Mode)
- 类似 ChatGPT 的对话界面
- 保持对话上下文
- 自动判断用户意图
- 支持多轮任务执行

### 2. 命令模式 (Command Mode)
- 类似 Vim 的命令行
- 以 `/` 开头的命令
- 快速执行特定操作

### 3. 任务模式 (Task Mode)
- 专注单个任务执行
- 显示详细进度
- 支持中断和恢复

## 界面设计

### 主界面

```
🤖 Agent Swarm Interactive CLI v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

模式: [聊天模式]  |  当前 Harness: auto  |  上下文: 5 轮

[1] 🤖 系统: 你好！我是 Agent Swarm 助手。请输入你的任务，或输入 /help 查看帮助。

[2] 👤 用户: 帮我写个Python函数计算斐波那契数列

[3] 🤖 系统: 我来帮你生成这个函数。
    🔍 分类: code (置信度: 85%)
    🚀 使用 CodeHarness 执行任务...
    ✅ 任务完成！

    ```python
    def fibonacci(n):
        if n <= 1:
            return n
        return fibonacci(n-1) + fibonacci(n-2)
    ```

[4] 👤 用户: 优化一下这个函数，用迭代方式

[5] 🤖 系统: 我来优化这个函数...
    🚀 使用 CodeHarness 执行优化...
    ✅ 优化完成！

    ```python
    def fibonacci(n):
        if n <= 1:
            return n
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b
    ```

👤 > _
```

### 命令模式

```
👤 > /help

📋 可用命令:

  /mode <chat|command|task>  - 切换模式
  /harness <type>            - 设置默认 Harness
  /list                      - 列出所有 Harness
  /clear                     - 清空上下文
  /history                   - 显示对话历史
  /save <file>               - 保存对话到文件
  /load <file>               - 从文件加载对话
  /monitor                   - 开启监控模式
  /dashboard                 - 开启仪表板
  /config                    - 显示当前配置
  /quit 或 /exit             - 退出

👤 > /harness code
✅ 默认 Harness 已设置为: code

👤 > /list
📋 可用 Harness:
  • execution   - 通用任务执行
  • code        - 代码生成 (当前默认)
  • debug       - 错误诊断
  • research    - 研究调研
  • test        - 测试验证
  • claude_code - 复杂任务
```

### 任务执行界面

```
👤 > 研究一下最新的AI大模型发展趋势

🔍 正在分析任务...
📊 分类结果:
   意图: 研究AI大模型发展趋势
   推荐 Harness: research
   置信度: 92%

🚀 启动 ResearchHarness...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
阶段 1/5: 分析研究需求 ✓
阶段 2/5: 搜索信息 [████████░░] 80%
   来源 1/10: OpenAI GPT-4 技术报告 ✓
   来源 2/10: Google Gemini 论文 ✓
   来源 3/10: Anthropic Claude 文档 ✓
   ...

按 Ctrl+C 中断任务
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## 核心功能

### 1. 上下文管理
- 保持对话历史
- 支持上下文窗口限制
- 支持上下文清空
- 支持历史保存/加载

### 2. 自动补全
- 命令补全 (Tab 键)
- Harness 类型补全
- 历史记录补全
- 文件路径补全

### 3. 实时显示
- 打字机效果输出
- 进度条显示
- 实时状态更新
- 支持中断操作

### 4. 会话管理
- 会话保存/恢复
- 多会话支持
- 会话切换

## 命令设计

### 系统命令

| 命令 | 功能 | 示例 |
|------|------|------|
| `/help` | 显示帮助 | `/help` |
| `/mode` | 切换模式 | `/mode chat` |
| `/harness` | 设置 Harness | `/harness code` |
| `/list` | 列出 Harness | `/list` |
| `/clear` | 清空上下文 | `/clear` |
| `/history` | 显示历史 | `/history` |
| `/save` | 保存会话 | `/save session.json` |
| `/load` | 加载会话 | `/load session.json` |
| `/monitor` | 开启监控 | `/monitor` |
| `/dashboard` | 开启仪表板 | `/dashboard` |
| `/config` | 显示配置 | `/config` |
| `/quit` | 退出 | `/quit` |

### 快捷操作

| 快捷键 | 功能 |
|--------|------|
| `Tab` | 命令补全 |
| `↑/↓` | 历史记录 |
| `Ctrl+C` | 中断任务 |
| `Ctrl+D` | 退出 |
| `Ctrl+L` | 清屏 |

## 实现方案

### 技术选型

- **prompt_toolkit** - 高级输入处理，支持补全、语法高亮
- **rich** - 美化输出，支持表格、进度条、Markdown
- **asyncio** - 异步任务处理
- **readline** - 历史记录

### 模块设计

```python
# src/interactive/
├── __init__.py
├── app.py              # 主应用类
├── modes/
│   ├── __init__.py
│   ├── base.py         # 模式基类
│   ├── chat.py         # 聊天模式
│   ├── command.py      # 命令模式
│   └── task.py         # 任务模式
├── completer.py        # 自动补全
├── history.py          # 历史管理
├── context.py          # 上下文管理
├── renderer.py         # 输出渲染
└── keybindings.py      # 快捷键绑定
```

### 核心类设计

```python
class InteractiveApp:
    """交互式应用主类"""

    def __init__(self):
        self.mode = ChatMode()  # 当前模式
        self.context = Context()  # 上下文
        self.history = History()  # 历史记录
        self.completer = CommandCompleter()  # 补全器
        self.session = PromptSession()  # 输入会话

    async def run(self):
        """主循环"""
        while True:
            try:
                # 获取输入
                user_input = await self.session.prompt_async(
                    self.get_prompt(),
                    completer=self.completer
                )

                # 解析输入
                if user_input.startswith('/'):
                    await self.handle_command(user_input)
                else:
                    await self.handle_chat(user_input)

            except KeyboardInterrupt:
                continue
            except EOFError:
                break

    async def handle_chat(self, input_text: str):
        """处理聊天输入"""
        # 添加到上下文
        self.context.add_message("user", input_text)

        # 分类任务
        classification = await self.classifier.classify(input_text)

        # 选择 Harness
        harness = self.get_harness(classification.harness_type)

        # 执行任务
        result = await harness.run(task)

        # 显示结果
        self.render_result(result)

        # 添加到上下文
        self.context.add_message("assistant", result)
```

## 使用示例

### 启动交互模式

```bash
# 启动交互式 CLI
agent-swarm interactive

# 或简写
agent-swarm -i
```

### 聊天示例

```
$ agent-swarm interactive

🤖 Agent Swarm Interactive CLI v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👤 > 帮我写个Python函数
🤖 我来帮你生成这个函数...
    🔍 分类: code (置信度: 85%)
    ✅ 完成！
    ```python
    def hello():
        print("Hello, World!")
    ```

👤 > 优化一下，添加类型提示
🤖 我来优化...
    ✅ 优化完成！
    ```python
    def hello() -> None:
        print("Hello, World!")
    ```

👤 > /save my_session.json
✅ 会话已保存

👤 > /quit
👋 再见！
```

## 下一步实现

1. **基础框架** - 创建 InteractiveApp 类
2. **输入处理** - 集成 prompt_toolkit
3. **模式切换** - 实现三种模式
4. **命令系统** - 实现 / 命令
5. **上下文管理** - 实现对话历史
6. **自动补全** - 实现 Tab 补全
7. **美化输出** - 集成 rich
8. **会话管理** - 实现保存/加载
