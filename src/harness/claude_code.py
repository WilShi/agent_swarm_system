"""
Claude Code Harness - 复杂多步骤任务和自动化工作流
模拟 Claude Code 的功能：skills、plans、hooks、subagents
"""
import inspect
import json
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

from src.harness.base import BaseHarness
from src.harness.factory import HarnessFactory
from src.core.types import Task, TaskResult, HarnessConfig, HarnessType, TaskStatus
from src.core.llm_client import chat_completion


class Skill:
    """技能定义"""
    def __init__(self, name: str, description: str, func: Callable):
        self.name = name
        self.description = description
        self.func = func


class PlanStep:
    """计划步骤"""
    def __init__(self, step_id: str, description: str,
                 skill: Optional[str] = None, dependencies: List[str] = None):
        self.step_id = step_id
        self.description = description
        self.skill = skill
        self.dependencies = dependencies or []
        self.status = "pending"
        self.result = None
        self.start_time = None
        self.end_time = None


class Plan:
    """执行计划"""
    def __init__(self, plan_id: str, description: str):
        self.plan_id = plan_id
        self.description = description
        self.steps: List[PlanStep] = []
        self.created_at = datetime.now()
        self.status = "pending"

    def add_step(self, step: PlanStep):
        self.steps.append(step)


class ClaudeCodeHarness(BaseHarness):
    """Claude Code Harness - 处理复杂多步骤任务"""

    SYSTEM_PROMPT = """你是一个任务规划专家。你的任务是：
1. 分析复杂的用户需求
2. 创建详细的执行计划
3. 确定每个步骤所需的技能
4. 识别步骤间的依赖关系

请以JSON格式返回执行计划。"""

    def __init__(self, config: HarnessConfig):
        super().__init__(config)
        self.skills: Dict[str, Skill] = {}
        self.hooks: Dict[str, List[Callable]] = {
            "pre_execution": [],
            "post_execution": [],
            "pre_step": [],
            "post_step": []
        }
        self.max_subagents = config.custom_params.get("max_subagents", 5)
        self.enable_planning = config.custom_params.get("enable_planning", True)

        # 注册默认技能
        self._register_default_skills()

    def _register_default_skills(self):
        """注册默认技能"""
        self.register_skill("code_edit", "编辑代码文件", self._skill_code_edit)
        self.register_skill("file_read", "读取文件内容", self._skill_file_read)
        self.register_skill("file_write", "写入文件内容", self._skill_file_write)
        self.register_skill("shell_exec", "执行shell命令", self._skill_shell_exec)
        self.register_skill("web_search", "搜索网络信息", self._skill_web_search)
        self.register_skill("analysis", "分析数据或代码", self._skill_analysis)

    def register_skill(self, name: str, description: str, func: Callable):
        """注册技能"""
        self.skills[name] = Skill(name, description, func)

    def register_hook(self, hook_type: str, func: Callable):
        """注册钩子"""
        if hook_type in self.hooks:
            self.hooks[hook_type].append(func)

    async def initialize(self):
        """初始化 Harness"""
        self._initialized = True

    async def execute(self, task: Task) -> TaskResult:
        """执行复杂任务"""
        start_time = datetime.now()

        # 1. 执行 pre_execution hooks
        await self._run_hooks("pre_execution", task)

        # 2. 创建执行计划
        if self.enable_planning:
            plan = await self._create_plan(task)
        else:
            plan = self._create_simple_plan(task)

        # 3. 执行计划
        plan_results = await self._execute_plan(plan, task)

        # 4. 执行 post_execution hooks
        await self._run_hooks("post_execution", task, plan_results)

        # 5. 构建结果
        execution_time = (datetime.now() - start_time).total_seconds()

        return TaskResult(
            task_id=task.task_id,
            status=TaskStatus.COMPLETED.value,
            output={
                "plan": {
                    "plan_id": plan.plan_id,
                    "description": plan.description,
                    "steps": len(plan.steps),
                    "completed": sum(1 for s in plan.steps if s.status == "completed"),
                    "failed": sum(1 for s in plan.steps if s.status == "failed")
                },
                "step_results": plan_results,
                "skills_used": list(set(r.get("skill") for r in plan_results if r.get("skill")))
            },
            quality_score=0.9,
            execution_time=execution_time
        )

    async def _create_plan(self, task: Task) -> Plan:
        """使用LLM创建执行计划"""
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": f"请为以下任务创建执行计划：\n\n"
                                        f"任务：{task.description}\n\n"
                                        f"可用技能：{list(self.skills.keys())}\n\n"
                                        f"请以JSON格式返回，包含steps数组，"
                                        f"每个step有step_id、description、skill、dependencies字段。"}
        ]

        response = await chat_completion(messages, temperature=0.3, max_tokens=2000)

        # 解析计划
        plan = Plan(
            plan_id=f"plan-{task.task_id}",
            description=task.description
        )

        try:
            plan_data = json.loads(response)
            for step_data in plan_data.get("steps", []):
                step = PlanStep(
                    step_id=step_data["step_id"],
                    description=step_data["description"],
                    skill=step_data.get("skill"),
                    dependencies=step_data.get("dependencies", [])
                )
                plan.add_step(step)
        except json.JSONDecodeError:
            # 如果解析失败，创建简单计划
            plan = self._create_simple_plan(task)

        return plan

    def _create_simple_plan(self, task: Task) -> Plan:
        """创建简单计划"""
        plan = Plan(
            plan_id=f"plan-{task.task_id}",
            description=task.description
        )
        plan.add_step(PlanStep(
            step_id="step-1",
            description=task.description,
            skill="analysis"
        ))
        return plan

    async def _execute_plan(self, plan: Plan, task: Task) -> List[Dict[str, Any]]:
        """执行计划"""
        results = []
        completed_steps = set()

        while len(completed_steps) < len(plan.steps):
            for step in plan.steps:
                if step.step_id in completed_steps:
                    continue

                # 检查依赖
                if all(d in completed_steps for d in step.dependencies):
                    # 执行 pre_step hooks
                    await self._run_hooks("pre_step", step)

                    # 执行步骤
                    result = await self._execute_step(step, task)
                    results.append(result)

                    # 执行 post_step hooks
                    await self._run_hooks("post_step", step, result)

                    completed_steps.add(step.step_id)

        return results

    async def _execute_step(self, step: PlanStep, task: Task) -> Dict[str, Any]:
        """执行单个步骤"""
        step.start_time = datetime.now()
        step.status = "in_progress"

        try:
            # 如果有指定技能，使用技能执行
            if step.skill and step.skill in self.skills:
                skill = self.skills[step.skill]
                result = await skill.func(step.description, task)
            else:
                # 使用默认分析技能
                result = await self._skill_analysis(step.description, task)

            step.status = "completed"
            step.result = result
            step.end_time = datetime.now()

            return {
                "step_id": step.step_id,
                "status": "completed",
                "skill": step.skill,
                "result": result,
                "duration": (step.end_time - step.start_time).total_seconds()
            }
        except Exception as e:
            step.status = "failed"
            step.end_time = datetime.now()

            return {
                "step_id": step.step_id,
                "status": "failed",
                "skill": step.skill,
                "error": str(e),
                "duration": (step.end_time - step.start_time).total_seconds()
            }

    async def _run_hooks(self, hook_type: str, *args):
        """运行钩子"""
        for hook in self.hooks.get(hook_type, []):
            try:
                if inspect.iscoroutinefunction(hook):
                    await hook(*args)
                else:
                    hook(*args)
            except Exception as e:
                print(f"Hook error: {e}")

    # 默认技能实现
    async def _skill_code_edit(self, description: str, task: Task) -> Any:
        """代码编辑技能"""
        return {"action": "code_edit", "description": description}

    async def _skill_file_read(self, description: str, task: Task) -> Any:
        """文件读取技能"""
        return {"action": "file_read", "description": description}

    async def _skill_file_write(self, description: str, task: Task) -> Any:
        """文件写入技能"""
        return {"action": "file_write", "description": description}

    async def _skill_shell_exec(self, description: str, task: Task) -> Any:
        """Shell执行技能"""
        return {"action": "shell_exec", "description": description}

    async def _skill_web_search(self, description: str, task: Task) -> Any:
        """网络搜索技能"""
        return {"action": "web_search", "description": description}

    async def _skill_analysis(self, description: str, task: Task) -> Any:
        """分析技能"""
        messages = [
            {"role": "system", "content": "你是一个分析助手。请分析以下内容并提供见解。"},
            {"role": "user", "content": description}
        ]
        response = await chat_completion(messages, temperature=0.4, max_tokens=1000)
        return {"action": "analysis", "result": response}

    async def cleanup(self):
        """清理资源"""
        self._initialized = False


# 注册到工厂
HarnessFactory.register(HarnessType.CLAUDE_CODE, ClaudeCodeHarness)
