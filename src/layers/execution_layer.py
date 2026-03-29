"""
第二层：执行层 (Execution Layer)
负责具体任务执行、工具调用、数据处理
"""
import asyncio
import json
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

from ..core.base_agent import BaseAgent
from ..core.types import (
    AgentConfig, AgentRole, Message, MessageType,
    SubTask, TaskStatus
)
from ..core.message_bus import MessageBus
from ..core.llm_client import LLMClientFactory, chat_completion


class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._tool_descriptions: Dict[str, Dict[str, Any]] = {}
    
    def register_tool(self, name: str, func: Callable, 
                     description: str = "", parameters: Dict[str, Any] = None):
        """注册工具"""
        self._tools[name] = func
        self._tool_descriptions[name] = {
            "name": name,
            "description": description,
            "parameters": parameters or {}
        }
    
    def unregister_tool(self, name: str):
        """注销工具"""
        if name in self._tools:
            del self._tools[name]
            del self._tool_descriptions[name]
    
    async def execute_tool(self, name: str, parameters: Dict[str, Any]) -> Any:
        """执行工具"""
        if name not in self._tools:
            raise ValueError(f"Tool {name} not found")
        
        tool_func = self._tools[name]
        
        # 检查是否为异步函数
        if asyncio.iscoroutinefunction(tool_func):
            return await tool_func(**parameters)
        else:
            return tool_func(**parameters)
    
    def get_tool_description(self, name: str) -> Optional[Dict[str, Any]]:
        """获取工具描述"""
        return self._tool_descriptions.get(name)
    
    def list_tools(self) -> List[str]:
        """列出所有工具"""
        return list(self._tools.keys())
    
    def get_all_descriptions(self) -> List[Dict[str, Any]]:
        """获取所有工具描述"""
        return list(self._tool_descriptions.values())


class ExecutionContext:
    """执行上下文"""
    
    def __init__(self):
        self._variables: Dict[str, Any] = {}
        self._execution_history: List[Dict[str, Any]] = []
        self._start_time: datetime = datetime.now()
    
    def set_variable(self, key: str, value: Any):
        """设置变量"""
        self._variables[key] = value
    
    def get_variable(self, key: str, default: Any = None) -> Any:
        """获取变量"""
        return self._variables.get(key, default)
    
    def log_execution(self, action: str, result: Any, duration_ms: float = 0):
        """记录执行历史"""
        self._execution_history.append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "result": result,
            "duration_ms": duration_ms
        })
    
    def get_history(self) -> List[Dict[str, Any]]:
        """获取执行历史"""
        return self._execution_history.copy()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "variables": self._variables.copy(),
            "history_count": len(self._execution_history),
            "start_time": self._start_time.isoformat()
        }


class ExecutorAgent(BaseAgent):
    """执行器Agent - 第二层核心"""
    
    def __init__(self, config: AgentConfig, message_bus: MessageBus):
        super().__init__(config, message_bus)
        self.tool_registry = ToolRegistry()
        self._execution_contexts: Dict[str, ExecutionContext] = {}
        self._coordinator_id: Optional[str] = None
        
        # 注册默认工具
        self._register_default_tools()
    
    def _register_default_tools(self):
        """注册默认工具"""
        # 数据处理工具
        self.tool_registry.register_tool(
            "data_transform",
            self._tool_data_transform,
            "Transform data using a specified function",
            {"data": "any", "transform": "string"}
        )
        
        # 文本处理工具
        self.tool_registry.register_tool(
            "text_process",
            self._tool_text_process,
            "Process text with various operations",
            {"text": "string", "operation": "string", "params": "object"}
        )
        
        # HTTP请求工具
        self.tool_registry.register_tool(
            "http_request",
            self._tool_http_request,
            "Make HTTP requests",
            {"url": "string", "method": "string", "headers": "object", "body": "any"}
        )
        
        # 文件操作工具
        self.tool_registry.register_tool(
            "file_operation",
            self._tool_file_operation,
            "Perform file operations",
            {"operation": "string", "path": "string", "content": "any"}
        )
        
        # 计算工具
        self.tool_registry.register_tool(
            "calculate",
            self._tool_calculate,
            "Perform calculations",
            {"expression": "string", "variables": "object"}
        )
    
    async def on_start(self):
        """启动执行器"""
        print(f"ExecutorAgent {self.config.agent_id} started")

        # 注册消息处理器
        self.register_message_handler(MessageType.TASK_ASSIGN, self._handle_task_assign)
        self.register_message_handler(MessageType.COORDINATION, self._handle_coordination)

        # 向协调器注册
        await self._register_with_coordinator()
    
    async def on_stop(self):
        """停止执行器"""
        print(f"ExecutorAgent {self.config.agent_id} stopped")
    
    async def process_task(self, task: SubTask) -> Any:
        """处理执行任务"""
        # 创建执行上下文
        context = ExecutionContext()
        context.set_variable("task_id", task.task_id)
        context.set_variable("task_type", task.task_type)
        context.set_variable("parameters", task.parameters)
        self._execution_contexts[task.task_id] = context
        
        start_time = datetime.now()
        
        try:
            # 根据任务类型执行不同的处理逻辑
            result = await self._execute_by_type(task, context)
            
            duration = (datetime.now() - start_time).total_seconds() * 1000
            context.log_execution(task.task_type, result, duration)
            
            return {
                "success": True,
                "result": result,
                "context": context.to_dict(),
                "execution_time_ms": duration
            }
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            context.log_execution(task.task_type, str(e), duration)
            
            return {
                "success": False,
                "error": str(e),
                "context": context.to_dict(),
                "execution_time_ms": duration
            }
        
        finally:
            # 清理上下文
            if task.task_id in self._execution_contexts:
                del self._execution_contexts[task.task_id]
    
    async def _execute_by_type(self, task: SubTask, context: ExecutionContext) -> Any:
        """根据任务类型执行"""
        task_type = task.task_type
        params = task.parameters
        
        # 数据收集
        if task_type == "data_collection":
            return await self._execute_data_collection(params, context)
        
        # 数据预处理
        elif task_type == "data_preprocessing":
            return await self._execute_data_preprocessing(params, context)
        
        # 分析执行
        elif task_type == "analysis_execution":
            return await self._execute_analysis(params, context)
        
        # 可视化
        elif task_type == "visualization":
            return await self._execute_visualization(params, context)
        
        # 内容生成
        elif task_type == "content_generation":
            return await self._execute_content_generation(params, context)
        
        # 代码实现
        elif task_type == "code_implementation":
            return await self._execute_code_implementation(params, context)
        
        # 测试编写
        elif task_type == "test_writing":
            return await self._execute_test_writing(params, context)
        
        # 通用执行
        else:
            return await self._execute_generic(task, context)
    
    async def _execute_data_collection(self, params: Dict[str, Any], 
                                       context: ExecutionContext) -> Any:
        """执行数据收集"""
        source = params.get("source", "default")
        
        # 模拟数据收集
        collected_data = {
            "source": source,
            "records": params.get("expected_records", 100),
            "fields": params.get("fields", []),
            "timestamp": datetime.now().isoformat()
        }
        
        context.set_variable("collected_data", collected_data)
        return collected_data
    
    async def _execute_data_preprocessing(self, params: Dict[str, Any], 
                                          context: ExecutionContext) -> Any:
        """执行数据预处理"""
        # 获取上游数据
        parent_data = params.get("parent_result", {})
        
        # 模拟预处理
        processed_data = {
            "original_records": parent_data.get("records", 0),
            "cleaned_records": int(parent_data.get("records", 0) * 0.95),
            "operations": ["deduplication", "normalization", "validation"],
            "timestamp": datetime.now().isoformat()
        }
        
        context.set_variable("processed_data", processed_data)
        return processed_data
    
    async def _execute_analysis(self, params: Dict[str, Any], 
                                context: ExecutionContext) -> Any:
        """执行分析（调用LLM）"""
        analysis_type = params.get("analysis_type", "general")
        data = params.get("data", "")
        question = params.get("question", "")
        
        # 构建提示词
        messages = [
            {"role": "system", "content": f"你是一个数据分析专家，擅长{analysis_type}分析。"},
            {"role": "user", "content": f"请分析以下数据并回答问题。\n\n数据：{data}\n\n问题：{question}\n\n请提供详细的分析结果和见解。"}
        ]
        
        try:
            # 调用LLM进行分析
            analysis_text = await chat_completion(messages)
            
            analysis_result = {
                "type": analysis_type,
                "analysis": analysis_text,
                "findings": ["基于LLM分析生成"],
                "timestamp": datetime.now().isoformat(),
                "model": self.config.llm_config.get("model", "unknown")
            }
        except Exception as e:
            # 如果LLM调用失败，返回模拟分析
            analysis_result = {
                "type": analysis_type,
                "analysis": f"[模拟分析] 分析类型: {analysis_type}\n\n(注意: LLM调用失败: {str(e)})",
                "findings": ["模拟发现1", "模拟发现2"],
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
        
        context.set_variable("analysis_result", analysis_result)
        return analysis_result
    
    async def _execute_visualization(self, params: Dict[str, Any], 
                                     context: ExecutionContext) -> Any:
        """执行可视化"""
        chart_type = params.get("chart_type", "bar")
        
        # 模拟可视化
        visualization = {
            "chart_type": chart_type,
            "data_points": 100,
            "format": "svg",
            "interactive": True,
            "timestamp": datetime.now().isoformat()
        }
        
        context.set_variable("visualization", visualization)
        return visualization
    
    async def _execute_content_generation(self, params: Dict[str, Any], 
                                          context: ExecutionContext) -> Any:
        """执行内容生成（调用LLM）"""
        content_type = params.get("content_type", "text")
        topic = params.get("topic", "general")
        description = params.get("description", "")
        
        # 构建提示词
        messages = [
            {"role": "system", "content": f"你是一个专业的{content_type}生成助手。"},
            {"role": "user", "content": f"请生成关于'{topic}'的内容。要求：{description}"}
        ]
        
        try:
            # 调用LLM生成内容
            generated_text = await chat_completion(messages)
            
            content = {
                "type": content_type,
                "topic": topic,
                "content": generated_text,
                "word_count": len(generated_text.split()),
                "timestamp": datetime.now().isoformat(),
                "model": self.config.llm_config.get("model", "unknown")
            }
        except Exception as e:
            # 如果LLM调用失败，返回模拟内容
            content = {
                "type": content_type,
                "topic": topic,
                "content": f"[模拟内容] 关于{topic}的生成内容\n\n(注意: LLM调用失败: {str(e)})",
                "word_count": 0,
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
        
        context.set_variable("generated_content", content)
        return content
    
    async def _execute_code_implementation(self, params: Dict[str, Any], 
                                           context: ExecutionContext) -> Any:
        """执行代码实现（调用LLM）"""
        language = params.get("language", "python")
        functionality = params.get("functionality", "")
        requirements = params.get("requirements", "")
        
        # 构建提示词
        messages = [
            {"role": "system", "content": f"你是一个专业的{language}程序员。请只输出代码，不要输出解释。"},
            {"role": "user", "content": f"请实现以下功能：{functionality}\n\n要求：{requirements}\n\n请提供完整的{language}代码。"}
        ]
        
        try:
            # 调用LLM生成代码
            generated_code = await chat_completion(messages)
            
            code = {
                "language": language,
                "functionality": functionality,
                "code": generated_code,
                "lines": len(generated_code.split('\n')),
                "timestamp": datetime.now().isoformat(),
                "model": self.config.llm_config.get("model", "unknown")
            }
        except Exception as e:
            # 如果LLM调用失败，返回模拟代码
            code = {
                "language": language,
                "functionality": functionality,
                "code": f"# [模拟代码] {functionality}\n# 注意: LLM调用失败: {str(e)}\n\ndef main():\n    pass",
                "lines": 5,
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
        
        context.set_variable("implemented_code", code)
        return code
    
    async def _execute_test_writing(self, params: Dict[str, Any], 
                                    context: ExecutionContext) -> Any:
        """执行测试编写"""
        test_framework = params.get("framework", "pytest")
        
        # 模拟测试编写
        tests = {
            "framework": test_framework,
            "test_cases": [
                {"name": "test_case_1", "type": "unit"},
                {"name": "test_case_2", "type": "integration"}
            ],
            "coverage": 0.85,
            "timestamp": datetime.now().isoformat()
        }
        
        context.set_variable("tests", tests)
        return tests
    
    async def _execute_generic(self, task: SubTask, 
                               context: ExecutionContext) -> Any:
        """通用任务执行"""
        # 尝试使用工具执行
        tool_name = task.parameters.get("tool")
        if tool_name and tool_name in self.tool_registry.list_tools():
            tool_params = task.parameters.get("tool_params", {})
            return await self.tool_registry.execute_tool(tool_name, tool_params)
        
        # 默认返回任务描述
        return {
            "executed": True,
            "task_type": task.task_type,
            "description": task.description,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _handle_coordination(self, message: Message):
        """处理协调消息"""
        content = message.content
        action = content.get("action")

        if action == "coordinator_assigned":
            self._coordinator_id = content.get("coordinator_id")
            print(f"Coordinator assigned: {self._coordinator_id}")

    async def _handle_task_assign(self, message: Message):
        """处理任务分配消息"""
        content = message.content
        action = content.get("action")

        if action == "assign_task":
            subtask_data = content.get("subtask", {})
            subtask = SubTask(**subtask_data)
            
            # 接受任务
            await self.assign_task(subtask)
            
            # 通知协调器任务已接受
            if self._coordinator_id:
                await self.send_to_agent(
                    self._coordinator_id,
                    {
                        "action": "task_accepted",
                        "task_id": subtask.task_id,
                        "agent_id": self.config.agent_id
                    }
                )
    
    async def _register_with_coordinator(self):
        """向协调器注册"""
        await self.broadcast(
            {
                "action": "register_agent",
                "agent_id": self.config.agent_id,
                "agent_role": "executor",
                "capabilities": self.config.capabilities
            },
            MessageType.COORDINATION
        )
    
    def register_custom_tool(self, name: str, func: Callable, 
                            description: str = "", parameters: Dict[str, Any] = None):
        """注册自定义工具"""
        self.tool_registry.register_tool(name, func, description, parameters)
    
    # 默认工具实现
    async def _tool_data_transform(self, data: Any, transform: str) -> Any:
        """数据转换工具"""
        if transform == "json":
            return json.dumps(data)
        elif transform == "reverse":
            if isinstance(data, list):
                return list(reversed(data))
            elif isinstance(data, str):
                return data[::-1]
        return data
    
    async def _tool_text_process(self, text: str, operation: str, 
                                  params: Dict[str, Any] = None) -> str:
        """文本处理工具"""
        params = params or {}
        
        if operation == "uppercase":
            return text.upper()
        elif operation == "lowercase":
            return text.lower()
        elif operation == "split":
            delimiter = params.get("delimiter", " ")
            return text.split(delimiter)
        elif operation == "replace":
            old = params.get("old", "")
            new = params.get("new", "")
            return text.replace(old, new)
        return text
    
    async def _tool_http_request(self, url: str, method: str = "GET",
                                  headers: Dict[str, str] = None,
                                  body: Any = None) -> Dict[str, Any]:
        """HTTP请求工具"""
        # 模拟HTTP请求
        return {
            "status": 200,
            "headers": {"Content-Type": "application/json"},
            "body": {"message": "Mock response", "url": url, "method": method}
        }
    
    async def _tool_file_operation(self, operation: str, path: str,
                                    content: Any = None) -> Any:
        """文件操作工具"""
        if operation == "read":
            return {"content": f"Mock content of {path}"}
        elif operation == "write":
            return {"written": True, "path": path, "size": len(str(content))}
        elif operation == "exists":
            return {"exists": True, "path": path}
        return {}
    
    async def _tool_calculate(self, expression: str, 
                              variables: Dict[str, float] = None) -> float:
        """计算工具"""
        try:
            # 安全计算（简化版）
            allowed_names = {"abs": abs, "max": max, "min": min, "sum": sum}
            if variables:
                allowed_names.update(variables)
            
            code = compile(expression, "<string>", "eval")
            return eval(code, {"__builtins__": {}}, allowed_names)
        except Exception as e:
            raise ValueError(f"Calculation error: {e}")
