# 多 Harness 模式自适应 Agent Swarm 系统设计文档

**版本**: 1.0
**日期**: 2026-03-28
**模型**: Kimi K2.5 (via DashScope)
**状态**: 设计阶段

---

## 目录

1. [概述](#1-概述)
2. [架构设计](#2-架构设计)
3. [Harness 模式详解](#3-harness-模式详解)
4. [核心组件设计](#4-核心组件设计)
5. [工作流程](#5-工作流程)
6. [数据模型](#6-数据模型)
7. [配置管理](#7-配置管理)
8. [错误处理与恢复](#8-错误处理与恢复)
9. [实现计划](#9-实现计划)

---

## 1. 概述

### 1.1 设计目标

构建一个能够自动识别任务类型、选择最优 Harness 执行模式、并协调 Agent Swarm 完成任务的智能系统。

### 1.2 核心能力

- **智能任务识别**: 基于 LLM 自动分析用户意图和任务类型
- **自适应 Harness 选择**: 根据任务特征选择最佳执行模式
- **多层执行架构**: TaskClassifier → Harness Engine → Agent Swarm
- **用户确认机制**: 关键决策点提供确认和修正机会
- **统一结果输出**: 标准化结果格式和质量评估

### 1.3 支持的 Harness 模式

| Harness 模式 | 适用场景 | 核心能力 |
|-------------|---------|---------|
| **Claude Code Harness** | 自动化工作流、复杂多步骤任务 | Skills、Plans、Hooks、Subagents |
| **Test Harness** | 测试验证、质量检查 | 单元测试、集成测试、性能测试、回归测试 |
| **Execution Harness** | 通用任务执行 | 任务编排、资源管理、错误恢复、超时控制 |
| **Research Harness** | 调研分析、信息检索 | 多源搜索、知识综合、报告生成 |
| **Code Harness** | 代码生成、重构优化 | 代码生成、代码审查、重构建议 |
| **Debug Harness** | 错误诊断、问题修复 | 错误定位、修复建议、验证修复 |

---

## 2. 架构设计

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户交互层 (User Interface Layer)                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  CLI / API / Web Interface                                          │   │
│  │  - 任务输入接收                                                     │   │
│  │  - 确认交互处理                                                     │   │
│  │  - 结果展示输出                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         第一层：任务理解与路由层                              │
│                    (Task Understanding & Routing Layer)                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  TaskClassifier (任务分类器)                                        │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │   │
│  │  │ Intent      │ │ Task Type   │ │ Harness     │ │ Confidence  │   │   │
│  │  │ Recognition │ │ Detection   │ │ Selector    │ │ Scorer      │   │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘   │   │
│  │  ┌─────────────┐                                                   │   │
│  │  │ Confirmation│ - 生成确认问题                                     │   │
│  │  │ Dialog      │ - 处理用户反馈                                     │   │
│  │  │ Generator   │ - 支持修正和重选                                   │   │
│  │  └─────────────┘                                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         第二层：Harness 执行引擎层                            │
│                         (Harness Execution Engine Layer)                     │
│                                                                              │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐                  │
│  │ Claude Code    │ │ Test           │ │ Execution      │                  │
│  │ Harness        │ │ Harness        │ │ Harness        │                  │
│  │                │ │                │ │                │                  │
│  │ • Skills       │ │ • Unit Test    │ │ • Task Orche   │                  │
│  │ • Plans        │ │ • Integration  │ │ • Resource Mgr │                  │
│  │ • Hooks        │ │ • Performance  │ │ • Error Recov  │                  │
│  │ • Subagents    │ │ • Regression   │ │ • Timeout Ctrl │                  │
│  └────────────────┘ └────────────────┘ └────────────────┘                  │
│                                                                              │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐                  │
│  │ Research       │ │ Code           │ │ Debug          │                  │
│  │ Harness        │ │ Harness        │ │ Harness        │                  │
│  │                │ │                │ │                │                  │
│  │ • Info Search  │ │ • Code Gen     │ │ • Error Diag   │                  │
│  │ • Knowledge    │ │ • Code Review  │ │ • Fix Suggest  │                  │
│  │   Synthesis    │ │ • Refactor     │ │ • Verify Fix   │                  │
│  │ • Report Gen   │ │ • Optimization │ │ • Root Cause   │                  │
│  └────────────────┘ └────────────────┘ └────────────────┘                  │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Harness Factory & Registry                                         │   │
│  │  - Harness 实例化管理                                               │   │
│  │  - 配置加载与验证                                                   │   │
│  │  - 生命周期管理                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         第三层：Agent Swarm 执行层                            │
│                         (Agent Swarm Execution Layer)                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      Swarm Orchestrator                             │   │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐ │   │
│  │  │ Coordinator │───▶│  Executors  │───▶│ Validator / Integrator  │ │   │
│  │  │   Agents    │    │   Agents    │    │       Agents            │ │   │
│  │  │             │    │             │    │                         │ │   │
│  │  │ • Task Decomp│   │ • Tool Exec │    │ • Quality Check         │ │   │
│  │  │ • Resource   │   │ • Data Proc │    │ • Result Merge          │ │   │
│  │  │   Alloc      │   │ • Code Run  │    │ • Conflict Resolve      │ │   │
│  │  │ • Strategy   │   │ • API Call  │    │ • Final Output          │ │   │
│  │  └─────────────┘    └─────────────┘    └─────────────────────────┘ │   │
│  │                                                                     │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │ Message Bus (消息总线)                                       │   │   │
│  │  │ - 异步消息传递                                               │   │   │
│  │  │ - 点对点通信                                                 │   │   │
│  │  │ - 广播机制                                                   │   │   │
│  │  │ - 订阅模式                                                   │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         第四层：结果整合与输出层                              │
│                    (Result Synthesis & Output Layer)                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Result Synthesizer (结果合成器)                                    │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │   │
│  │  │ Result      │ │ Quality     │ │ Format      │ │ Feedback    │   │   │
│  │  │ Validation  │ │ Assessment  │ │ Converter   │ │ Learning    │   │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              基础设施层 (Infrastructure)                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │ LLM Client  │ │ Config      │ │ Logging     │ │ Metrics     │           │
│  │ (Kimi K2.5) │ │ Manager     │ │ & Tracing   │ │ & Monitoring│           │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 组件关系图

```
┌─────────────────────────────────────────────────────────────────┐
│                         System Entry                            │
│                    (user_input / API call)                      │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  TaskClassifier                                                 │
│  ├── analyze_intent(user_input) → IntentAnalysis                │
│  ├── detect_task_type(intent) → TaskType                        │
│  ├── select_harness(task_type, intent) → HarnessType            │
│  ├── calculate_confidence() → ConfidenceScore                   │
│  └── generate_confirmation() → ConfirmationRequest              │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  User Confirmation (if confidence < threshold)                  │
│  ├── confirm_harness_selection()                                │
│  ├── modify_task_requirements()                                 │
│  └── override_harness_selection()                               │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  HarnessEngine                                                  │
│  ├── factory.create_harness(harness_type) → HarnessInstance     │
│  ├── harness.initialize(config)                                 │
│  ├── harness.create_plan(task) → ExecutionPlan                  │
│  └── harness.execute_plan(plan) → SwarmManager                  │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  SwarmManager                                                   │
│  ├── create_coordinator(harness_specific_config)                │
│  ├── create_executors(count, capabilities)                      │
│  ├── create_validators(count, validation_rules)                 │
│  ├── create_integrators(count, integration_strategy)            │
│  ├── submit_task(task) → task_id                                │
│  └── wait_for_result(task_id) → TaskResult                      │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  ResultSynthesizer                                              │
│  ├── validate_result(result, criteria) → ValidationReport       │
│  ├── assess_quality(result) → QualityScore                      │
│  ├── format_output(result, format_type) → FormattedOutput       │
│  └── learn_from_execution(execution_log) → ModelUpdate          │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Final Output                             │
│              (formatted result to user / API)                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Harness 模式详解

### 3.1 Claude Code Harness

**用途**: 复杂多步骤任务、自动化工作流、需要规划和协调的任务

**核心组件**:
- **Skill Registry**: 管理可调用技能
- **Plan Engine**: 创建和执行分步计划
- **Hook System**: 在关键点执行自定义逻辑
- **Subagent Manager**: 管理子代理执行

**适用任务特征**:
- 包含多个步骤的复杂任务
- 需要特定领域技能的任务
- 需要人机协作的任务
- 需要严格流程控制的任务

**配置示例**:
```yaml
claude_code_harness:
  enabled: true
  skills:
    - name: code_review
      description: "代码审查技能"
    - name: documentation
      description: "文档生成技能"
  hooks:
    pre_execution: validate_input
    post_execution: save_result
  max_subagents: 5
  timeout: 600
```

### 3.2 Test Harness

**用途**: 测试验证、质量检查、覆盖率分析

**核心组件**:
- **Test Generator**: 自动生成测试用例
- **Test Executor**: 执行测试并收集结果
- **Coverage Analyzer**: 分析代码覆盖率
- **Report Builder**: 生成测试报告

**支持测试类型**:
- 单元测试 (Unit Test)
- 集成测试 (Integration Test)
- 性能测试 (Performance Test)
- 回归测试 (Regression Test)
- 模糊测试 (Fuzzing)

**适用任务特征**:
- 包含"测试"、"验证"、"检查"关键词
- 代码质量保证需求
- 回归验证需求
- 性能基准测试

### 3.3 Execution Harness

**用途**: 通用任务执行、标准三层 Swarm 模式

**核心组件**:
- **Task Orchestrator**: 任务编排和调度
- **Resource Manager**: 资源分配和监控
- **Error Recovery**: 错误恢复和重试
- **Timeout Controller**: 超时控制和管理

**适用任务特征**:
- 通用分析任务
- 数据处理任务
- 无法明确分类的其他任务
- 作为默认 Harness 使用

### 3.4 Research Harness

**用途**: 调研分析、信息检索、知识综合

**核心组件**:
- **Search Planner**: 搜索策略规划
- **Multi-source Collector**: 多源信息收集
- **Information Extractor**: 信息提取和结构化
- **Knowledge Synthesizer**: 知识综合和总结
- **Report Generator**: 报告生成和格式化

**适用任务特征**:
- 包含"调研"、"搜索"、"了解"、"学习"关键词
- 需要多源信息整合
- 需要生成研究报告
- 知识库构建任务

### 3.5 Code Harness

**用途**: 代码生成、代码审查、重构优化

**核心组件**:
- **Code Generator**: 代码生成
- **Code Reviewer**: 代码审查
- **Refactoring Engine**: 重构引擎
- **Optimization Suggester**: 优化建议
- **Documentation Generator**: 文档生成

**适用任务特征**:
- 包含"写代码"、"实现"、"函数"、"类"关键词
- 代码重构需求
- 代码优化需求
- 算法实现需求

### 3.6 Debug Harness

**用途**: 错误诊断、问题定位、自动修复

**核心组件**:
- **Error Parser**: 错误信息解析
- **Root Cause Analyzer**: 根因分析
- **Fix Suggester**: 修复建议生成
- **Patch Applier**: 补丁应用
- **Verification Runner**: 修复验证

**适用任务特征**:
- 包含"bug"、"错误"、"修复"、"排查"关键词
- 异常处理需求
- 问题诊断需求
- 代码调试需求

---

## 4. 核心组件设计

### 4.1 TaskClassifier

**职责**: 分析用户输入，识别任务类型，推荐 Harness 模式

**类设计**:
```python
class TaskClassifier:
    """任务分类器"""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.confidence_threshold = 0.7

    async def classify(self, user_input: str, context: Dict = None) -> ClassificationResult:
        """
        分类任务

        Returns:
            ClassificationResult 包含:
            - intent: 用户意图
            - task_type: 任务类型
            - harness_type: 推荐的 Harness 类型
            - confidence: 置信度 (0-1)
            - reasoning: 推理过程
            - confirmation_questions: 确认问题列表
        """
        pass

    async def analyze_intent(self, user_input: str) -> IntentAnalysis:
        """分析用户意图"""
        pass

    async def detect_task_type(self, intent: IntentAnalysis) -> TaskType:
        """检测任务类型"""
        pass

    async def select_harness(self, task_type: TaskType, intent: IntentAnalysis) -> HarnessType:
        """选择 Harness 类型"""
        pass

    def calculate_confidence(self, analysis: Dict) -> float:
        """计算置信度"""
        pass

    def generate_confirmation(self, result: ClassificationResult) -> ConfirmationRequest:
        """生成确认请求"""
        pass
```

**分类提示词模板**:
```
你是一个任务分类专家。请分析用户的输入，识别任务类型并推荐最适合的执行模式。

用户输入: {user_input}

请分析:
1. 用户的主要意图是什么？
2. 这属于什么类型的任务？
3. 应该使用哪种 Harness 模式？
4. 置信度是多少（0-1）？
5. 为什么这样选择？

可选的 Harness 模式:
- claude_code: 复杂多步骤任务、自动化工作流
- test: 测试验证、质量检查
- execution: 通用任务执行
- research: 调研分析、信息检索
- code: 代码生成、重构优化
- debug: 错误诊断、问题修复

请以 JSON 格式输出:
{
    "intent": "用户意图描述",
    "task_type": "任务类型",
    "harness_type": "推荐的 harness",
    "confidence": 0.85,
    "reasoning": "选择理由",
    "sub_tasks": ["子任务1", "子任务2"],
    "requirements": {"关键要求": "描述"}
}
```

### 4.2 HarnessEngine

**职责**: 管理所有 Harness 的创建、配置和执行

**类设计**:
```python
class HarnessEngine:
    """Harness 执行引擎"""

    def __init__(self, config: HarnessEngineConfig):
        self.config = config
        self.factory = HarnessFactory()
        self.registry = HarnessRegistry()
        self.active_harnesses: Dict[str, BaseHarness] = {}

    async def initialize(self):
        """初始化引擎"""
        pass

    async def create_harness(self, harness_type: HarnessType,
                            task_config: TaskConfig) -> BaseHarness:
        """创建 Harness 实例"""
        pass

    async def execute_task(self, harness: BaseHarness,
                          task: Task) -> TaskResult:
        """使用 Harness 执行任务"""
        pass

    async def shutdown(self):
        """关闭引擎"""
        pass


class HarnessFactory:
    """Harness 工厂"""

    _harness_map = {
        HarnessType.CLAUDE_CODE: ClaudeCodeHarness,
        HarnessType.TEST: TestHarness,
        HarnessType.EXECUTION: ExecutionHarness,
        HarnessType.RESEARCH: ResearchHarness,
        HarnessType.CODE: CodeHarness,
        HarnessType.DEBUG: DebugHarness,
    }

    def create(self, harness_type: HarnessType, config: Dict) -> BaseHarness:
        """创建 Harness 实例"""
        harness_class = self._harness_map.get(harness_type)
        if not harness_class:
            raise ValueError(f"Unknown harness type: {harness_type}")
        return harness_class(config)
```

### 4.3 BaseHarness

**职责**: 所有 Harness 的基类，定义通用接口

**类设计**:
```python
class BaseHarness(ABC):
    """Harness 基类"""

    def __init__(self, config: HarnessConfig):
        self.config = config
        self.swarm_manager: Optional[SwarmManager] = None
        self.execution_plan: Optional[ExecutionPlan] = None
        self.metrics = HarnessMetrics()

    @abstractmethod
    async def initialize(self):
        """初始化 Harness"""
        pass

    @abstractmethod
    async def create_plan(self, task: Task) -> ExecutionPlan:
        """创建执行计划"""
        pass

    @abstractmethod
    async def execute_plan(self, plan: ExecutionPlan) -> TaskResult:
        """执行计划"""
        pass

    @abstractmethod
    async def configure_swarm(self) -> SwarmConfig:
        """配置 Swarm"""
        pass

    async def run(self, task: Task) -> TaskResult:
        """运行 Harness"""
        # 1. 初始化
        await self.initialize()

        # 2. 创建计划
        plan = await self.create_plan(task)

        # 3. 配置 Swarm
        swarm_config = await self.configure_swarm()
        self.swarm_manager = SwarmManager(swarm_config)
        await self.swarm_manager.start()

        # 4. 执行计划
        result = await self.execute_plan(plan)

        # 5. 清理
        await self.swarm_manager.stop()

        return result

    async def get_status(self) -> HarnessStatus:
        """获取 Harness 状态"""
        pass

    async def cleanup(self):
        """清理资源"""
        pass
```

### 4.4 ConfirmationManager

**职责**: 管理用户确认流程

**类设计**:
```python
class ConfirmationManager:
    """确认管理器"""

    def __init__(self, ui_interface: UIInterface):
        self.ui = ui_interface
        self.timeout = 300  # 5分钟超时

    async def request_confirmation(self, request: ConfirmationRequest) -> ConfirmationResponse:
        """
        请求用户确认

        返回用户的选择和可能的修改
        """
        pass

    def format_confirmation_prompt(self, result: ClassificationResult) -> str:
        """格式化确认提示"""
        prompt = f"""
我分析到您的任务可能是以下类型：

📋 **任务意图**: {result.intent}
🎯 **任务类型**: {result.task_type.value}
⚙️  **推荐模式**: {result.harness_type.value}
📊 **置信度**: {result.confidence:.0%}

💡 **选择理由**:
{result.reasoning}

请选择：
1. ✅ 确认使用 {result.harness_type.value} 模式
2. 🔄 选择其他模式
3. ✏️  补充任务描述
4. ❌ 取消任务
        """
        return prompt

    async def handle_override(self, current: HarnessType) -> HarnessType:
        """处理用户覆盖选择"""
        pass
```

---

## 5. 工作流程

### 5.1 主流程

```
┌─────────────────────────────────────────────────────────────────┐
│                         开始                                    │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. 接收用户输入                                                │
│     - 文本输入 / API 请求 / 文件上传                            │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. TaskClassifier 分析                                         │
│     - 意图识别                                                  │
│     - 任务类型检测                                              │
│     - Harness 推荐                                              │
│     - 置信度计算                                                │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. 判断置信度                                                  │
│     ┌─────────────────────────────────────────────────────┐    │
│     │ confidence >= threshold ?                           │    │
│     └─────────────────────────────────────────────────────┘    │
│          │                              │                      │
│          ▼                              ▼                      │
│     ┌─────────┐                   ┌─────────┐                 │
│     │   Yes   │                   │   No    │                 │
│     └────┬────┘                   └────┬────┘                 │
│          │                              │                      │
│          ▼                              ▼                      │
│     跳过确认                      显示确认问题                  │
│          │                              │                      │
│          └──────────────┬───────────────┘                      │
│                         ▼                                      │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. 用户确认                                                    │
│     - 确认 Harness 选择                                         │
│     - 或选择其他 Harness                                        │
│     - 或补充任务信息                                            │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. HarnessEngine 初始化                                        │
│     - 创建 Harness 实例                                         │
│     - 加载 Harness 配置                                         │
│     - 初始化 Swarm 配置                                         │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  6. 创建执行计划                                                │
│     - Harness 特定计划生成                                      │
│     - 任务分解                                                  │
│     - 依赖分析                                                  │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  7. Agent Swarm 执行                                            │
│     - 启动 Swarm                                                │
│     - Coordinator 分配任务                                      │
│     - Executors 并行执行                                        │
│     - Validators 验证结果                                       │
│     - Integrators 整合输出                                      │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  8. 结果处理                                                    │
│     - 结果验证                                                  │
│     - 质量评估                                                  │
│     - 格式化输出                                                │
│     - 保存执行记录                                              │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  9. 返回结果给用户                                              │
│     - 格式化展示                                                │
│     - 提供后续操作选项                                          │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                         结束                                    │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Harness 执行子流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    Harness.execute_plan()                       │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. 预执行检查                                                  │
│     - 验证输入                                                  │
│     - 检查资源                                                  │
│     - 加载必要组件                                              │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. 初始化 SwarmManager                                         │
│     - 创建 Coordinator                                          │
│     - 创建 Executors (根据 Harness 配置)                        │
│     - 创建 Validators                                           │
│     - 创建 Integrators                                          │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. 提交任务到 Coordinator                                      │
│     - 分解子任务                                                │
│     - 分配资源                                                  │
│     - 设置监控                                                  │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. 监控执行                                                    │
│     - 跟踪任务进度                                              │
│     - 处理超时                                                  │
│     - 处理错误重试                                              │
│     - 收集中间结果                                              │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. 收集最终结果                                                │
│     - 从 Integrator 获取结果                                    │
│     - 验证结果完整性                                            │
│     - 格式化结果                                                │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  6. 清理 Swarm                                                  │
│     - 停止所有 Agents                                           │
│     - 释放资源                                                  │
│     - 保存执行日志                                              │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    返回 TaskResult                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. 数据模型

### 6.1 核心数据类

```python
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from enum import Enum, auto
from datetime import datetime


class TaskType(Enum):
    """任务类型枚举"""
    ANALYSIS = "analysis"           # 分析任务
    GENERATION = "generation"       # 生成任务
    CODE = "code"                   # 代码任务
    RESEARCH = "research"           # 研究任务
    DEBUG = "debug"                 # 调试任务
    TEST = "test"                   # 测试任务
    AUTOMATION = "automation"       # 自动化任务
    GENERAL = "general"             # 通用任务


class HarnessType(Enum):
    """Harness 类型枚举"""
    CLAUDE_CODE = "claude_code"     # Claude Code 风格
    TEST = "test"                   # 测试 Harness
    EXECUTION = "execution"         # 执行 Harness
    RESEARCH = "research"           # 研究 Harness
    CODE = "code"                   # 代码 Harness
    DEBUG = "debug"                 # 调试 Harness


@dataclass
class IntentAnalysis:
    """意图分析结果"""
    primary_intent: str             # 主要意图
    secondary_intents: List[str]    # 次要意图
    entities: Dict[str, Any]        # 提取的实体
    sentiment: str                  # 情感倾向
    urgency: str                    # 紧急程度


@dataclass
class ClassificationResult:
    """分类结果"""
    intent: IntentAnalysis          # 意图分析
    task_type: TaskType             # 任务类型
    harness_type: HarnessType       # Harness 类型
    confidence: float               # 置信度 (0-1)
    reasoning: str                  # 推理过程
    sub_tasks: List[str]            # 子任务列表
    requirements: Dict[str, Any]    # 任务要求
    keywords: List[str]             # 关键词
    estimated_complexity: str       # 预估复杂度 (low/medium/high)
    estimated_duration: int         # 预估时长(秒)


@dataclass
class ConfirmationRequest:
    """确认请求"""
    classification: ClassificationResult
    question: str                   # 确认问题
    options: List[Dict[str, str]]   # 选项列表
    timeout: int                    # 超时时间
    allow_override: bool            # 是否允许覆盖


@dataclass
class ConfirmationResponse:
    """确认响应"""
    confirmed: bool                 # 是否确认
    selected_harness: HarnessType   # 选择的 Harness
    modifications: Dict[str, Any]   # 用户修改
    feedback: str                   # 用户反馈


@dataclass
class HarnessConfig:
    """Harness 配置基类"""
    harness_type: HarnessType
    enabled: bool = True
    timeout: int = 300
    max_retries: int = 3
    custom_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionPlan:
    """执行计划"""
    plan_id: str
    task: Task
    steps: List[PlanStep]           # 执行步骤
    dependencies: Dict[str, List[str]]  # 步骤依赖
    estimated_duration: int         # 预估时长
    resources_required: Dict[str, Any]  # 所需资源


@dataclass
class PlanStep:
    """计划步骤"""
    step_id: str
    description: str
    step_type: str                  # 步骤类型
    agent_type: str                 # 执行 Agent 类型
    input_data: Dict[str, Any]      # 输入数据
    output_schema: Dict[str, Any]   # 输出格式
    dependencies: List[str]         # 依赖步骤
    timeout: int                    # 超时时间
    retry_policy: Dict[str, Any]    # 重试策略


@dataclass
class TaskResult:
    """任务结果"""
    task_id: str
    status: str                     # 状态
    output: Any                     # 输出内容
    quality_score: float            # 质量评分
    execution_time: float           # 执行时间
    tokens_used: int                # Token 使用量
    subtask_results: List[Dict]     # 子任务结果
    logs: List[str]                 # 执行日志
    errors: List[str]               # 错误信息
    metadata: Dict[str, Any]        # 元数据


@dataclass
class HarnessMetrics:
    """Harness 指标"""
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_execution_time: float = 0.0
    average_quality_score: float = 0.0
    token_usage: int = 0
    error_rate: float = 0.0
```

---

## 7. 配置管理

### 7.1 系统配置结构

```yaml
# config/system.yaml
system:
  name: "Multi-Harness Agent Swarm"
  version: "1.0.0"
  log_level: INFO

llm:
  provider: dashscope
  model: kimi-k2.5
  api_key: ${DASHSCOPE_API_KEY}
  base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
  temperature: 0.7
  max_tokens: 4000
  timeout: 60

classification:
  confidence_threshold: 0.7
  require_confirmation: true
  max_retries: 3

harnesses:
  claude_code:
    enabled: true
    timeout: 600
    max_subagents: 5
    skills:
      - code_review
      - documentation
      - planning
    hooks:
      pre_execution: validate_input
      post_execution: save_result

  test:
    enabled: true
    timeout: 300
    test_types:
      - unit
      - integration
      - performance
    coverage_threshold: 80

  execution:
    enabled: true
    timeout: 300
    max_agents: 10
    enable_load_balancing: true

  research:
    enabled: true
    timeout: 600
    max_sources: 10
    search_engines:
      - google
      - bing
      - arxiv

  code:
    enabled: true
    timeout: 300
    languages:
      - python
      - javascript
      - typescript
    enable_linting: true

  debug:
    enabled: true
    timeout: 300
    max_iterations: 10
    enable_auto_fix: true

swarm:
  max_agents: 20
  message_queue_size: 1000
  enable_fault_tolerance: true
  task_timeout: 300

monitoring:
  enabled: true
  metrics_interval: 60
  tracing_enabled: true
```

### 7.2 Harness 特定配置

```python
# src/config/harness_config.py

@dataclass
class ClaudeCodeHarnessConfig(HarnessConfig):
    """Claude Code Harness 配置"""
    skills: List[str] = field(default_factory=list)
    hooks: Dict[str, str] = field(default_factory=dict)
    max_subagents: int = 5
    plan_template_dir: str = "templates/plans"


@dataclass
class TestHarnessConfig(HarnessConfig):
    """Test Harness 配置"""
    test_types: List[str] = field(default_factory=lambda: ["unit"])
    coverage_threshold: float = 80.0
    test_framework: str = "pytest"
    mock_enabled: bool = True
    parallel_execution: bool = True


@dataclass
class ResearchHarnessConfig(HarnessConfig):
    """Research Harness 配置"""
    max_sources: int = 10
    search_engines: List[str] = field(default_factory=list)
    enable_caching: bool = True
    cache_ttl: int = 3600
    synthesis_model: str = "kimi-k2.5"
```

---

## 8. 错误处理与恢复

### 8.1 错误分类

| 错误类型 | 描述 | 处理策略 |
|---------|------|---------|
| **ClassificationError** | 任务分类失败 | 使用默认 Execution Harness，记录日志 |
| **HarnessInitError** | Harness 初始化失败 | 尝试备用 Harness，或降级到 Execution |
| **SwarmExecutionError** | Swarm 执行错误 | 重试、子任务降级、人工介入 |
| **TimeoutError** | 执行超时 | 保存状态、异步继续、部分结果返回 |
| **ResourceError** | 资源不足 | 排队等待、资源扩容、任务拆分 |
| **ValidationError** | 结果验证失败 | 重新执行、降低要求、人工审核 |

### 8.2 恢复策略

```python
class ErrorRecoveryManager:
    """错误恢复管理器"""

    async def handle_error(self, error: Exception, context: ExecutionContext) -> RecoveryAction:
        """处理错误并决定恢复策略"""

        error_type = self.classify_error(error)

        recovery_strategies = {
            ErrorType.CLASSIFICATION_ERROR: self._handle_classification_error,
            ErrorType.HARNESS_INIT_ERROR: self._handle_harness_init_error,
            ErrorType.SWARM_EXECUTION_ERROR: self._handle_swarm_error,
            ErrorType.TIMEOUT_ERROR: self._handle_timeout,
            ErrorType.RESOURCE_ERROR: self._handle_resource_error,
            ErrorType.VALIDATION_ERROR: self._handle_validation_error,
        }

        handler = recovery_strategies.get(error_type, self._handle_unknown_error)
        return await handler(error, context)

    async def _handle_swarm_error(self, error: Exception, context: ExecutionContext) -> RecoveryAction:
        """处理 Swarm 执行错误"""
        if context.retry_count < context.max_retries:
            return RecoveryAction.RETRY
        elif context.can_degrade:
            return RecoveryAction.DEGRADE
        else:
            return RecoveryAction.ESCALATE
```

---

## 9. 实现计划

### 9.1 阶段划分

#### 阶段 1: 基础框架 (Week 1-2)
- [ ] 项目结构重构
- [ ] 核心数据模型定义
- [ ] LLM Client 适配 Kimi K2.5
- [ ] 配置管理系统
- [ ] 日志和监控基础

#### 阶段 2: TaskClassifier (Week 3)
- [ ] 意图识别模块
- [ ] 任务类型检测
- [ ] Harness 选择器
- [ ] 置信度计算
- [ ] 确认流程管理

#### 阶段 3: Harness 引擎 (Week 4-5)
- [ ] BaseHarness 抽象
- [ ] HarnessFactory 实现
- [ ] Execution Harness (默认)
- [ ] Code Harness
- [ ] Research Harness

#### 阶段 4: Agent Swarm 集成 (Week 6)
- [ ] SwarmManager 重构
- [ ] Coordinator 适配
- [ ] Executor 适配
- [ ] Validator/Integrator 适配
- [ ] 消息总线优化

#### 阶段 5: 高级 Harness (Week 7)
- [ ] Claude Code Harness
- [ ] Test Harness
- [ ] Debug Harness
- [ ] Harness 间协作

#### 阶段 6: 完善与优化 (Week 8)
- [ ] 错误恢复机制
- [ ] 性能优化
- [ ] 完整测试覆盖
- [ ] 文档完善
- [ ] 示例和教程

### 9.2 项目结构

```
agent_swarm_project/
├── src/
│   ├── __init__.py
│   ├── main.py                      # 入口点
│   ├── core/
│   │   ├── __init__.py
│   │   ├── types.py                 # 核心数据类型
│   │   ├── config.py                # 配置管理
│   │   ├── llm_client.py            # LLM 客户端 (Kimi K2.5)
│   │   ├── message_bus.py           # 消息总线
│   │   └── exceptions.py            # 异常定义
│   ├── classifier/
│   │   ├── __init__.py
│   │   ├── task_classifier.py       # 任务分类器
│   │   ├── intent_analyzer.py       # 意图分析
│   │   ├── harness_selector.py      # Harness 选择
│   │   └── confirmation.py          # 确认管理
│   ├── harness/
│   │   ├── __init__.py
│   │   ├── base.py                  # Harness 基类
│   │   ├── factory.py               # Harness 工厂
│   │   ├── registry.py              # Harness 注册表
│   │   ├── claude_code.py           # Claude Code Harness
│   │   ├── test.py                  # Test Harness
│   │   ├── execution.py             # Execution Harness
│   │   ├── research.py              # Research Harness
│   │   ├── code.py                  # Code Harness
│   │   └── debug.py                 # Debug Harness
│   ├── swarm/
│   │   ├── __init__.py
│   │   ├── manager.py               # Swarm 管理器
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # Agent 基类
│   │   │   ├── coordinator.py       # 协调器
│   │   │   ├── executor.py          # 执行器
│   │   │   ├── validator.py         # 验证器
│   │   │   └── integrator.py        # 整合器
│   │   └── resources/
│   │       ├── __init__.py
│   │       ├── allocator.py         # 资源分配
│   │       └── monitor.py           # 资源监控
│   ├── result/
│   │   ├── __init__.py
│   │   ├── synthesizer.py           # 结果合成
│   │   ├── validator.py             # 结果验证
│   │   └── formatter.py             # 格式化输出
│   └── utils/
│       ├── __init__.py
│       ├── logging.py               # 日志工具
│       └── metrics.py               # 指标收集
├── config/
│   ├── system.yaml                  # 系统配置
│   └── harnesses/                   # Harness 配置
│       ├── claude_code.yaml
│       ├── test.yaml
│       └── ...
├── prompts/                         # LLM 提示词
│   ├── classification/
│   ├── harness/
│   └── swarm/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── examples/                        # 使用示例
├── docs/                            # 文档
└── scripts/                         # 工具脚本
```

### 9.3 关键里程碑

| 里程碑 | 时间 | 交付物 |
|-------|------|-------|
| M1: 基础框架 | Week 2 | 可运行的基础框架，支持配置和日志 |
| M2: 分类器 | Week 3 | 可自动识别任务类型并选择 Harness |
| M3: 核心 Harness | Week 5 | Execution、Code、Research Harness 可用 |
| M4: Swarm 集成 | Week 6 | 完整的三层 Swarm 执行能力 |
| M5: 全部 Harness | Week 7 | 6 种 Harness 全部可用 |
| M6: 发布 | Week 8 | 完整测试、文档、示例 |

---

## 附录

### A. 提示词模板库

见 `prompts/` 目录

### B. API 接口定义

见 `docs/api.md`

### C. 部署指南

见 `docs/deployment.md`

---

**文档维护者**: AI Assistant
**最后更新**: 2026-03-28
