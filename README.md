# Multi-Harness Agent Swarm System

一个智能的多 Harness 任务执行系统，能够自动识别任务类型并选择最优的执行模式。系统集成 Agent Swarm 架构，支持实时监控和交互式仪表板。

[English](#english) | [中文](#中文)

---

<a name="中文"></a>
## 中文介绍

### 🎯 系统特点

- **智能任务分类** - 自动识别任务类型（代码、调试、研究、测试等）
- **多 Harness 支持** - 6 种专业 Harness 处理不同类型任务
- **Agent Swarm 架构** - 三层架构（协调层/执行层/验证层）分布式任务处理
- **实时监控** - 实时查看 Agent 工作状态和任务进度
- **交互式仪表板** - 可视化监控界面，支持查看详情

### 🏗️ 系统架构

```
用户请求 → TaskClassifier → HarnessFactory → 具体 Harness
                                          ↓
                              Execution/Code/Debug/Research/Test/ClaudeCode
                                          ↓
                              Agent Swarm (可选) / LLM 直接执行
                                          ↓
                              监控仪表板 (实时显示进度)
```

### 📦 支持的 Harness

| Harness | 功能 | 适用场景 |
|---------|------|----------|
| **ExecutionHarness** | 通用任务执行 | 标准任务处理，集成完整 Swarm |
| **CodeHarness** | 代码生成与重构 | 生成函数/类、重构代码、优化性能 |
| **DebugHarness** | 错误诊断修复 | 分析错误、定位问题、生成修复 |
| **ResearchHarness** | 研究调研 | 信息搜索、知识综合、生成报告 |
| **TestHarness** | 测试验证 | 生成测试用例、执行测试、分析覆盖率 |
| **ClaudeCodeHarness** | 复杂多步骤任务 | 自动化工作流、计划执行、技能调用 |

### 🚀 快速开始

#### 安装

```bash
# 克隆项目
git clone https://github.com/WilShi/agent_swarm_system.git
cd agent_swarm_project

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置你的 Kimi K2.5 API 密钥
```

#### 基本使用

```python
import asyncio
from src.harness import HarnessFactory
from src.core.types import HarnessType, Task, TaskType

async def main():
    # 创建 Harness
    harness = HarnessFactory.create(HarnessType.CODE)

    # 创建任务
    task = Task(
        task_id="task-001",
        description="生成一个Python函数来计算斐波那契数列",
        task_type=TaskType.CODE,
        harness_type=HarnessType.CODE
    )

    # 执行任务
    result = await harness.run(task)

    print(f"状态: {result.status}")
    print(f"输出: {result.output}")

asyncio.run(main())
```

#### 使用 TaskClassifier 自动分类

```python
from src.classifier import TaskClassifier

async def main():
    classifier = TaskClassifier()

    # 自动分类任务
    result = await classifier.classify("帮我写个Python函数")

    print(f"检测到的意图: {result.intent.primary_intent}")
    print(f"推荐 Harness: {result.harness_type.value}")
    print(f"置信度: {result.confidence:.2%}")

asyncio.run(main())
```

#### 使用监控仪表板

```python
# 启用监控仪表板
harness = HarnessFactory.create(
    HarnessType.EXECUTION,
    config={
        "custom_params": {
            "enable_monitoring": True,
            "show_dashboard": True  # 启动交互式仪表板
        }
    }
)
```

### 📊 监控功能

系统提供完整的监控功能：

- **Agent 监控** - 查看每个 Agent 的工作状态、进度、历史
- **任务监控** - 跟踪任务执行阶段、子任务详情
- **交互式仪表板** - 实时刷新、查看详情、操作控制

```
🤖 Agent Swarm 监控仪表板
============================================================

📊 整体进度
   总任务: 4  |  ✓完成: 2  |  ✗失败: 0  |  🔄进行中: 2
   [████████████████████░░░░░░░░░░] 50%

──────────────────── 正在工作的 Agent ────────────────────

  [1] Executor-2 (exec-002)
      状态: 🟢 运行中  |  进度: [██████████░░░░] 60%
      任务: data_preprocessing
      耗时: 15.3秒

操作: [w1]查看详情  [r]刷新  [q]退出
```

### 🧪 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定 Harness 测试
pytest tests/test_harness/test_code.py -v

# 运行监控演示
python examples/monitor_demo.py

# 运行带监控的任务执行
python examples/execution_with_monitor.py --dashboard
```

### 📁 项目结构

```
agent_swarm_project/
├── src/
│   ├── core/              # 核心类型、配置、LLM客户端
│   ├── classifier/        # 任务分类器
│   ├── harness/           # 6种 Harness 实现
│   ├── layers/            # Agent Swarm 三层架构
│   ├── monitoring/        # 监控系统
│   └── swarm_manager.py   # Swarm 管理器
├── tests/                 # 测试套件（137+ 测试）
├── examples/              # 使用示例
├── config/                # 配置文件
└── docs/                  # 设计文档
```

### 🔧 配置选项

每个 Harness 支持多种配置选项：

```python
# ExecutionHarness
config = {
    "max_agents": 10,              # 最大 Agent 数
    "enable_monitoring": True,     # 启用监控
    "show_dashboard": False        # 显示仪表板
}

# CodeHarness
config = {
    "language": "python",          # 编程语言
    "style_guide": "pep8"          # 代码风格
}

# ResearchHarness
config = {
    "max_sources": 10,             # 最大来源数
    "research_depth": "deep",      # 研究深度
    "output_format": "report"      # 输出格式
}
```

### 🛠️ 技术栈

- **Python 3.11+** - 主语言
- **asyncio** - 异步编程
- **Kimi K2.5** (via DashScope) - LLM 引擎
- **pytest** - 测试框架
- **Agent Swarm** - 分布式任务处理

### 📈 性能指标

- **测试覆盖率** - 137+ 测试用例
- **Harness 数量** - 6 种专业 Harness
- **Agent 并发** - 支持 10+ Agent 同时工作
- **任务超时** - 可配置，默认 300 秒

### 🤝 贡献

欢迎提交 Issue 和 Pull Request！

### 📄 许可证

MIT License

---

<a name="english"></a>
## English Introduction

### 🎯 Features

- **Intelligent Task Classification** - Automatically identify task types (code, debug, research, test, etc.)
- **Multi-Harness Support** - 6 specialized Harnesses for different task types
- **Agent Swarm Architecture** - Three-layer architecture (Coordination/Execution/Validation)
- **Real-time Monitoring** - View Agent working status and task progress in real-time
- **Interactive Dashboard** - Visual monitoring interface with detail view

### 🏗️ Architecture

```
User Request → TaskClassifier → HarnessFactory → Specific Harness
                                            ↓
                                Execution/Code/Debug/Research/Test/ClaudeCode
                                            ↓
                                Agent Swarm (optional) / LLM Direct Execution
                                            ↓
                                Monitor Dashboard (Real-time Progress)
```

### 📦 Supported Harnesses

| Harness | Function | Use Case |
|---------|----------|----------|
| **ExecutionHarness** | General task execution | Standard tasks with full Swarm |
| **CodeHarness** | Code generation & refactoring | Generate functions/classes, refactor, optimize |
| **DebugHarness** | Error diagnosis & fixing | Analyze errors, locate issues, generate fixes |
| **ResearchHarness** | Research & investigation | Info search, knowledge synthesis, reports |
| **TestHarness** | Testing & validation | Generate tests, execute, analyze coverage |
| **ClaudeCodeHarness** | Complex multi-step tasks | Automation workflows, plan execution |

### 🚀 Quick Start

#### Installation

```bash
# Clone project
git clone https://github.com/WilShi/agent_swarm_system.git
cd agent_swarm_project

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env file with your Kimi K2.5 API key
```

#### Basic Usage

```python
import asyncio
from src.harness import HarnessFactory
from src.core.types import HarnessType, Task, TaskType

async def main():
    # Create Harness
    harness = HarnessFactory.create(HarnessType.CODE)

    # Create task
    task = Task(
        task_id="task-001",
        description="Generate a Python function to calculate Fibonacci sequence",
        task_type=TaskType.CODE,
        harness_type=HarnessType.CODE
    )

    # Execute task
    result = await harness.run(task)

    print(f"Status: {result.status}")
    print(f"Output: {result.output}")

asyncio.run(main())
```

### 🧪 Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific Harness tests
pytest tests/test_harness/test_code.py -v

# Run monitoring demo
python examples/monitor_demo.py
```

### 🛠️ Tech Stack

- **Python 3.11+** - Main language
- **asyncio** - Async programming
- **Kimi K2.5** (via DashScope) - LLM engine
- **pytest** - Testing framework
- **Agent Swarm** - Distributed task processing

### 📈 Metrics

- **Test Coverage** - 137+ test cases
- **Harness Count** - 6 specialized Harnesses
- **Agent Concurrency** - Support 10+ Agents simultaneously
- **Task Timeout** - Configurable, default 300 seconds

### 🤝 Contributing

Issues and Pull Requests are welcome!

### 📄 License

MIT License

---

**Made with ❤️ by Wilson**