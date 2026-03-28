"""
ClaudeCodeHarness 测试
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.harness.claude_code import (
    ClaudeCodeHarness,
    Skill,
    PlanStep,
    Plan
)
from src.harness.factory import HarnessFactory
from src.core.types import (
    Task,
    HarnessConfig,
    HarnessType,
    TaskStatus,
    TaskType
)


class TestSkill:
    """Skill 测试类"""

    def test_skill_creation(self):
        """测试技能创建"""
        async def test_func(desc, task):
            return {"result": "test"}

        skill = Skill("test_skill", "测试技能", test_func)
        assert skill.name == "test_skill"
        assert skill.description == "测试技能"
        assert skill.func == test_func


class TestPlanStep:
    """PlanStep 测试类"""

    def test_plan_step_creation(self):
        """测试计划步骤创建"""
        step = PlanStep(
            step_id="step-1",
            description="测试步骤",
            skill="analysis",
            dependencies=["step-0"]
        )
        assert step.step_id == "step-1"
        assert step.description == "测试步骤"
        assert step.skill == "analysis"
        assert step.dependencies == ["step-0"]
        assert step.status == "pending"
        assert step.result is None

    def test_plan_step_default_dependencies(self):
        """测试计划步骤默认依赖"""
        step = PlanStep(step_id="step-1", description="测试步骤")
        assert step.dependencies == []


class TestPlan:
    """Plan 测试类"""

    def test_plan_creation(self):
        """测试计划创建"""
        plan = Plan(plan_id="plan-123", description="测试计划")
        assert plan.plan_id == "plan-123"
        assert plan.description == "测试计划"
        assert plan.steps == []
        assert plan.status == "pending"

    def test_add_step(self):
        """测试添加步骤"""
        plan = Plan(plan_id="plan-123", description="测试计划")
        step = PlanStep(step_id="step-1", description="步骤1")
        plan.add_step(step)
        assert len(plan.steps) == 1
        assert plan.steps[0] == step


class TestClaudeCodeHarness:
    """ClaudeCodeHarness 测试类"""

    @pytest.fixture
    def harness_config(self):
        return HarnessConfig(
            harness_type=HarnessType.CLAUDE_CODE,
            enabled=True,
            timeout=300
        )

    @pytest.fixture
    def claude_code_harness(self, harness_config):
        return ClaudeCodeHarness(harness_config)

    @pytest.fixture
    def sample_task(self):
        return Task(
            task_id="test-task-123",
            description="测试复杂任务",
            task_type=TaskType.AUTOMATION
        )

    @pytest.mark.asyncio
    async def test_initialize(self, claude_code_harness):
        """测试初始化"""
        await claude_code_harness.initialize()
        assert claude_code_harness.is_initialized()

    def test_default_skills_registration(self, claude_code_harness):
        """测试默认技能注册"""
        expected_skills = [
            "code_edit", "file_read", "file_write",
            "shell_exec", "web_search", "analysis"
        ]
        for skill_name in expected_skills:
            assert skill_name in claude_code_harness.skills

    def test_register_skill(self, claude_code_harness):
        """测试注册技能"""
        async def custom_skill(desc, task):
            return {"custom": True}

        claude_code_harness.register_skill("custom", "自定义技能", custom_skill)
        assert "custom" in claude_code_harness.skills
        assert claude_code_harness.skills["custom"].description == "自定义技能"

    def test_register_hook(self, claude_code_harness):
        """测试注册钩子"""
        def pre_exec_hook(task):
            pass

        claude_code_harness.register_hook("pre_execution", pre_exec_hook)
        assert pre_exec_hook in claude_code_harness.hooks["pre_execution"]

    def test_invalid_hook_type(self, claude_code_harness):
        """测试无效钩子类型"""
        def invalid_hook(task):
            pass

        claude_code_harness.register_hook("invalid_type", invalid_hook)
        # 应该被忽略，不会抛出异常
        assert "invalid_type" not in claude_code_harness.hooks

    def test_config_params(self):
        """测试配置参数"""
        config = HarnessConfig(
            harness_type=HarnessType.CLAUDE_CODE,
            custom_params={
                "max_subagents": 10,
                "enable_planning": False
            }
        )
        harness = ClaudeCodeHarness(config)
        assert harness.max_subagents == 10
        assert harness.enable_planning is False

    def test_default_config_params(self, harness_config):
        """测试默认配置参数"""
        harness = ClaudeCodeHarness(harness_config)
        assert harness.max_subagents == 5
        assert harness.enable_planning is True

    @pytest.mark.asyncio
    async def test_create_simple_plan(self, claude_code_harness, sample_task):
        """测试创建简单计划"""
        plan = claude_code_harness._create_simple_plan(sample_task)
        assert plan.plan_id == f"plan-{sample_task.task_id}"
        assert plan.description == sample_task.description
        assert len(plan.steps) == 1
        assert plan.steps[0].skill == "analysis"

    @pytest.mark.asyncio
    async def test_execute_step_with_skill(self, claude_code_harness, sample_task):
        """测试使用技能执行步骤"""
        step = PlanStep(
            step_id="step-1",
            description="测试步骤",
            skill="file_read"
        )
        result = await claude_code_harness._execute_step(step, sample_task)

        assert result["step_id"] == "step-1"
        assert result["status"] == "completed"
        assert result["skill"] == "file_read"
        assert "result" in result
        assert step.status == "completed"

    @pytest.mark.asyncio
    async def test_execute_step_without_skill(self, claude_code_harness, sample_task):
        """测试不使用技能执行步骤"""
        step = PlanStep(
            step_id="step-1",
            description="测试步骤",
            skill="nonexistent_skill"
        )

        with patch.object(claude_code_harness, '_skill_analysis') as mock_analysis:
            mock_analysis.return_value = {"analysis": "result"}
            result = await claude_code_harness._execute_step(step, sample_task)

        assert result["status"] == "completed"
        assert result["skill"] == "nonexistent_skill"

    @pytest.mark.asyncio
    async def test_execute_step_failure(self, claude_code_harness, sample_task):
        """测试步骤执行失败"""
        async def failing_skill(desc, task):
            raise Exception("Skill failed")

        claude_code_harness.register_skill("failing", "失败技能", failing_skill)
        step = PlanStep(
            step_id="step-1",
            description="测试步骤",
            skill="failing"
        )
        result = await claude_code_harness._execute_step(step, sample_task)

        assert result["status"] == "failed"
        assert "error" in result
        assert step.status == "failed"

    @pytest.mark.asyncio
    async def test_run_hooks(self, claude_code_harness, sample_task):
        """测试运行钩子"""
        hook_called = False

        def test_hook(task):
            nonlocal hook_called
            hook_called = True

        claude_code_harness.register_hook("pre_execution", test_hook)
        await claude_code_harness._run_hooks("pre_execution", sample_task)
        assert hook_called

    @pytest.mark.asyncio
    async def test_run_async_hooks(self, claude_code_harness, sample_task):
        """测试运行异步钩子"""
        hook_called = False

        async def async_hook(task):
            nonlocal hook_called
            hook_called = True

        claude_code_harness.register_hook("pre_execution", async_hook)
        await claude_code_harness._run_hooks("pre_execution", sample_task)
        assert hook_called

    @pytest.mark.asyncio
    async def test_run_hooks_error_handling(self, claude_code_harness, sample_task):
        """测试钩子错误处理"""
        def failing_hook(task):
            raise Exception("Hook failed")

        claude_code_harness.register_hook("pre_execution", failing_hook)
        # 不应该抛出异常
        await claude_code_harness._run_hooks("pre_execution", sample_task)

    @pytest.mark.asyncio
    async def test_execute_plan(self, claude_code_harness, sample_task):
        """测试执行计划"""
        plan = Plan(plan_id="plan-123", description="测试计划")
        plan.add_step(PlanStep(step_id="step-1", description="步骤1", skill="file_read"))
        plan.add_step(PlanStep(step_id="step-2", description="步骤2", skill="file_write", dependencies=["step-1"]))

        results = await claude_code_harness._execute_plan(plan, sample_task)

        assert len(results) == 2
        assert results[0]["status"] == "completed"
        assert results[1]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_execute_with_planning_disabled(self, claude_code_harness, sample_task):
        """测试禁用计划功能"""
        claude_code_harness.enable_planning = False

        with patch.object(claude_code_harness, '_run_hooks') as mock_hooks:
            mock_hooks.return_value = None
            with patch.object(claude_code_harness, '_execute_plan') as mock_execute:
                mock_execute.return_value = [
                    {"step_id": "step-1", "status": "completed", "skill": "analysis"}
                ]
                result = await claude_code_harness.execute(sample_task)

        assert result.status == TaskStatus.COMPLETED.value
        assert result.output["plan"]["steps"] == 1

    @pytest.mark.asyncio
    async def test_create_plan_with_llm(self, claude_code_harness, sample_task):
        """测试使用LLM创建计划"""
        plan_json = {
            "steps": [
                {"step_id": "step-1", "description": "分析需求", "skill": "analysis", "dependencies": []},
                {"step_id": "step-2", "description": "读取文件", "skill": "file_read", "dependencies": ["step-1"]}
            ]
        }

        with patch('src.harness.claude_code.chat_completion') as mock_chat:
            mock_chat.return_value = json.dumps(plan_json)
            plan = await claude_code_harness._create_plan(sample_task)

        assert len(plan.steps) == 2
        assert plan.steps[0].step_id == "step-1"
        assert plan.steps[1].dependencies == ["step-1"]

    @pytest.mark.asyncio
    async def test_create_plan_json_decode_error(self, claude_code_harness, sample_task):
        """测试创建计划时JSON解析错误"""
        with patch('src.harness.claude_code.chat_completion') as mock_chat:
            mock_chat.return_value = "invalid json"
            plan = await claude_code_harness._create_plan(sample_task)

        # 应该回退到简单计划
        assert len(plan.steps) == 1
        assert plan.steps[0].skill == "analysis"

    @pytest.mark.asyncio
    async def test_cleanup(self, claude_code_harness):
        """测试清理"""
        await claude_code_harness.initialize()
        assert claude_code_harness.is_initialized()

        await claude_code_harness.cleanup()
        # cleanup() in BaseHarness sets _initialized to False
        assert not claude_code_harness.is_initialized()

    def test_registration(self):
        """测试 ClaudeCodeHarness 已注册"""
        # 重新注册（其他测试可能已清理）
        from src.harness.claude_code import ClaudeCodeHarness
        HarnessFactory.register(HarnessType.CLAUDE_CODE, ClaudeCodeHarness)
        assert HarnessFactory.is_registered(HarnessType.CLAUDE_CODE)

    @pytest.mark.asyncio
    async def test_create_via_factory(self):
        """测试通过工厂创建"""
        # 确保已注册
        from src.harness.claude_code import ClaudeCodeHarness
        if not HarnessFactory.is_registered(HarnessType.CLAUDE_CODE):
            HarnessFactory.register(HarnessType.CLAUDE_CODE, ClaudeCodeHarness)
        harness = HarnessFactory.create(HarnessType.CLAUDE_CODE)
        assert isinstance(harness, ClaudeCodeHarness)
        assert harness.harness_type == HarnessType.CLAUDE_CODE

    # 技能测试
    @pytest.mark.asyncio
    async def test_skill_code_edit(self, claude_code_harness, sample_task):
        """测试代码编辑技能"""
        result = await claude_code_harness._skill_code_edit("编辑代码", sample_task)
        assert result["action"] == "code_edit"
        assert result["description"] == "编辑代码"

    @pytest.mark.asyncio
    async def test_skill_file_read(self, claude_code_harness, sample_task):
        """测试文件读取技能"""
        result = await claude_code_harness._skill_file_read("读取文件", sample_task)
        assert result["action"] == "file_read"
        assert result["description"] == "读取文件"

    @pytest.mark.asyncio
    async def test_skill_file_write(self, claude_code_harness, sample_task):
        """测试文件写入技能"""
        result = await claude_code_harness._skill_file_write("写入文件", sample_task)
        assert result["action"] == "file_write"
        assert result["description"] == "写入文件"

    @pytest.mark.asyncio
    async def test_skill_shell_exec(self, claude_code_harness, sample_task):
        """测试Shell执行技能"""
        result = await claude_code_harness._skill_shell_exec("执行命令", sample_task)
        assert result["action"] == "shell_exec"
        assert result["description"] == "执行命令"

    @pytest.mark.asyncio
    async def test_skill_web_search(self, claude_code_harness, sample_task):
        """测试网络搜索技能"""
        result = await claude_code_harness._skill_web_search("搜索内容", sample_task)
        assert result["action"] == "web_search"
        assert result["description"] == "搜索内容"

    @pytest.mark.asyncio
    async def test_skill_analysis(self, claude_code_harness, sample_task):
        """测试分析技能"""
        with patch('src.harness.claude_code.chat_completion') as mock_chat:
            mock_chat.return_value = "分析结果"
            result = await claude_code_harness._skill_analysis("分析内容", sample_task)

        assert result["action"] == "analysis"
        assert result["result"] == "分析结果"

    @pytest.mark.asyncio
    async def test_full_execute(self, claude_code_harness, sample_task):
        """测试完整执行流程"""
        with patch('src.harness.claude_code.chat_completion') as mock_chat:
            mock_chat.return_value = json.dumps({
                "steps": [
                    {"step_id": "step-1", "description": "分析", "skill": "analysis", "dependencies": []}
                ]
            })

            result = await claude_code_harness.run(sample_task)

        assert result.task_id == sample_task.task_id
        assert result.status == TaskStatus.COMPLETED.value
        assert result.output is not None
        assert "plan" in result.output
        assert "step_results" in result.output
        assert "skills_used" in result.output
        assert result.quality_score == 0.9
        assert result.execution_time > 0
