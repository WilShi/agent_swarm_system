# Agent Swarm System

一个基于三层架构的多Agent协作系统，支持任务分解、分布式执行、结果验证和智能整合。

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    第一层：协调/规划层                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  CoordinatorAgent (协调器)                          │   │
│  │  - TaskDecomposer (任务分解器)                      │   │
│  │  - ResourceAllocator (资源分配器)                   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      第二层：执行层                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  ExecutorAgent(s) (执行器)                          │   │
│  │  - ToolRegistry (工具注册表)                        │   │
│  │  - ExecutionContext (执行上下文)                    │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    第三层：验证/整合层                        │
│  ┌─────────────────┐    ┌─────────────────────────────┐   │
│  │ ValidatorAgent  │    │ IntegratorAgent             │   │
│  │ (验证器)        │    │ (整合器)                    │   │
│  │ - 质量检查      │    │ - 结果整合                  │   │
│  │ - 准确性验证    │    │ - 智能合并                  │   │
│  └─────────────────┘    └─────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 核心特性

### 1. 三层架构
- **第一层（协调/规划层）**: 负责任务分解、资源分配、策略制定
- **第二层（执行层）**: 负责具体任务执行、工具调用、数据处理
- **第三层（验证/整合层）**: 负责结果验证、质量检查、最终整合

### 2. 任务分解策略
- 分析类任务: 数据收集 → 预处理 → 分析执行 → 可视化
- 生成类任务: 需求分析 → 内容生成 → 内容优化
- 代码类任务: 需求理解 → 设计 → 实现 → 测试
- 研究类任务: 文献检索 → 信息提取 → 知识综合

### 3. 验证引擎
- **完整性验证**: 检查必需字段和数据完整性
- **准确性验证**: 验证结果准确性和模式匹配
- **一致性验证**: 检查数据内部一致性
- **性能验证**: 验证执行时间和资源使用
- **格式验证**: 验证输出格式符合预期

### 4. 整合策略
- **合并 (Merge)**: 合并多个字典或列表
- **连接 (Concatenate)**: 连接字符串或列表
- **摘要 (Summarize)**: 生成统计摘要
- **聚合 (Aggregate)**: 数值聚合计算
- **选择最佳 (Select Best)**: 基于评分选择最优结果

### 5. 通信机制
- **消息总线**: 异步消息传递系统
- **点对点通信**: Agent间直接通信
- **广播**: 向所有Agent广播消息
- **订阅模式**: 按消息类型订阅

## 快速开始

### 安装

```bash
# 克隆项目
git clone <repository-url>
cd agent_swarm_project

# 安装依赖
pip install -r requirements.txt
```

### 基础使用

```python
import asyncio
from src import create_swarm, run_task

async def main():
    # 创建并启动Swarm
    swarm = await create_swarm(name="MySwarm")
    
    try:
        # 提交分析任务
        result = await run_task(
            swarm,
            description="分析用户行为数据",
            task_type="analysis",
            wait=True,
            timeout=30.0
        )
        print(f"任务结果: {result}")
        
        # 获取系统统计
        stats = swarm.get_system_stats()
        print(f"总Agent数: {stats['agents']['total']}")
        
    finally:
        # 停止Swarm
        await swarm.stop()

# 运行
asyncio.run(main())
```

### 运行示例

```bash
# 基础示例
python examples/basic_example.py

# 高级示例
python examples/advanced_example.py
```

## 项目结构

```
agent_swarm_project/
├── src/
│   ├── __init__.py
│   ├── swarm_manager.py      # Swarm管理器
│   ├── core/
│   │   ├── __init__.py
│   │   ├── types.py          # 核心类型定义
│   │   ├── base_agent.py     # Agent基类
│   │   └── message_bus.py    # 消息总线
│   └── layers/
│       ├── __init__.py
│       ├── coordinator_layer.py  # 协调层
│       ├── execution_layer.py    # 执行层
│       └── validation_layer.py   # 验证层
├── examples/
│   ├── __init__.py
│   ├── basic_example.py      # 基础示例
│   └── advanced_example.py   # 高级示例
├── tests/
│   ├── __init__.py
│   ├── test_core.py          # 核心模块测试
│   └── test_layers.py        # 层模块测试
└── README.md
```

## 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_core.py -v
pytest tests/test_layers.py -v
```

## 高级功能

### 自定义工具

```python
async def my_custom_tool(data: dict) -> dict:
    return {"processed": True, "data": data}

# 注册到执行器
executor.register_custom_tool(
    "my_tool",
    my_custom_tool,
    "My custom tool",
    {"data": "object"}
)
```

### 动态扩展Agent

```python
# 添加新的执行器
new_agent_id = await swarm.add_executor(
    capabilities=["custom_ml", "data_analysis"]
)

# 移除执行器
await swarm.remove_executor(new_agent_id)
```

### 自定义验证策略

```python
from src.layers import ValidationEngine

validator = ValidationEngine()

# 执行特定验证
result = await validator.validate(
    data=my_data,
    validation_type="completeness",
    criteria={"required_fields": ["name", "value"]}
)
```

## 配置选项

```python
from src.core.types import SwarmConfig

config = SwarmConfig(
    name="MySwarm",
    max_agents=20,
    enable_load_balancing=True,
    enable_fault_tolerance=True,
    message_queue_size=2000
)

swarm = SwarmManager(config)
```

## Agent配置

```python
from src.core.types import AgentConfig, AgentRole

config = AgentConfig(
    name="MyAgent",
    role=AgentRole.EXECUTOR,
    capabilities=["coding", "testing"],
    max_concurrent_tasks=5,
    timeout_seconds=300
)
```

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！
