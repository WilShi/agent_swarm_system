"""
第三层：验证/整合层 (Validation Layer)
负责结果验证、质量检查、最终整合
"""
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field

from ..core.base_agent import BaseAgent
from ..core.types import (
    AgentConfig, AgentRole, Message, MessageType,
    SubTask, Task, TaskStatus, ValidationResult
)
from ..core.message_bus import MessageBus


@dataclass
class QualityMetrics:
    """质量指标"""
    completeness: float = 0.0  # 完整性 0-1
    accuracy: float = 0.0      # 准确性 0-1
    consistency: float = 0.0   # 一致性 0-1
    performance: float = 0.0   # 性能 0-1
    overall_score: float = 0.0 # 综合得分
    
    def calculate_overall(self, weights: Dict[str, float] = None):
        """计算综合得分"""
        if weights is None:
            weights = {
                "completeness": 0.3,
                "accuracy": 0.3,
                "consistency": 0.2,
                "performance": 0.2
            }
        
        self.overall_score = (
            self.completeness * weights["completeness"] +
            self.accuracy * weights["accuracy"] +
            self.consistency * weights["consistency"] +
            self.performance * weights["performance"]
        )
        return self.overall_score


class ValidationEngine:
    """验证引擎"""
    
    def __init__(self):
        self._validators: Dict[str, callable] = {
            "completeness": self._validate_completeness,
            "accuracy": self._validate_accuracy,
            "consistency": self._validate_consistency,
            "performance": self._validate_performance,
            "format": self._validate_format
        }
    
    async def validate(self, result: Any, validation_type: str, 
                      criteria: Dict[str, Any] = None) -> ValidationResult:
        """执行验证"""
        validator = self._validators.get(validation_type, self._validate_generic)
        return await validator(result, criteria or {})
    
    async def validate_all(self, result: Any, 
                          criteria: Dict[str, Any] = None) -> Dict[str, ValidationResult]:
        """执行所有验证"""
        results = {}
        for validation_type in self._validators.keys():
            results[validation_type] = await self.validate(result, validation_type, criteria)
        return results
    
    async def _validate_completeness(self, result: Any, 
                                     criteria: Dict[str, Any]) -> ValidationResult:
        """验证完整性"""
        required_fields = criteria.get("required_fields", [])
        min_items = criteria.get("min_items", 0)
        
        score = 1.0
        feedback = []
        
        if isinstance(result, dict):
            missing_fields = [f for f in required_fields if f not in result]
            if missing_fields:
                score -= len(missing_fields) / len(required_fields) if required_fields else 0
                feedback.append(f"Missing fields: {missing_fields}")
        
        if isinstance(result, list):
            if len(result) < min_items:
                score = len(result) / min_items if min_items > 0 else 1.0
                feedback.append(f"Insufficient items: {len(result)} < {min_items}")
        
        return ValidationResult(
            is_valid=score >= criteria.get("threshold", 0.8),
            score=max(0, score),
            feedback="; ".join(feedback) if feedback else "Completeness check passed",
            validator_id="completeness_validator"
        )
    
    async def _validate_accuracy(self, result: Any, 
                                 criteria: Dict[str, Any]) -> ValidationResult:
        """验证准确性"""
        expected_patterns = criteria.get("expected_patterns", [])
        reference_data = criteria.get("reference_data")
        
        score = 1.0
        feedback = []
        
        # 检查是否包含期望的模式
        result_str = str(result)
        for pattern in expected_patterns:
            if pattern not in result_str:
                score -= 0.1
                feedback.append(f"Missing pattern: {pattern}")
        
        # 与参考数据比较
        if reference_data is not None:
            similarity = self._calculate_similarity(result, reference_data)
            score *= similarity
            if similarity < 0.8:
                feedback.append(f"Low similarity with reference: {similarity:.2f}")
        
        return ValidationResult(
            is_valid=score >= criteria.get("threshold", 0.8),
            score=max(0, score),
            feedback="; ".join(feedback) if feedback else "Accuracy check passed",
            validator_id="accuracy_validator"
        )
    
    async def _validate_consistency(self, result: Any, 
                                    criteria: Dict[str, Any]) -> ValidationResult:
        """验证一致性"""
        score = 1.0
        feedback = []
        
        if isinstance(result, dict):
            # 检查内部一致性
            inconsistencies = self._check_dict_consistency(result)
            if inconsistencies:
                score -= len(inconsistencies) * 0.1
                feedback.extend(inconsistencies)
        
        if isinstance(result, list) and len(result) > 1:
            # 检查列表项之间的一致性
            item_types = set(type(item).__name__ for item in result)
            if len(item_types) > 1:
                score -= 0.1
                feedback.append(f"Mixed types in list: {item_types}")
        
        return ValidationResult(
            is_valid=score >= criteria.get("threshold", 0.8),
            score=max(0, score),
            feedback="; ".join(feedback) if feedback else "Consistency check passed",
            validator_id="consistency_validator"
        )
    
    async def _validate_performance(self, result: Any, 
                                    criteria: Dict[str, Any]) -> ValidationResult:
        """验证性能"""
        max_execution_time = criteria.get("max_execution_time_ms", 5000)
        max_memory_usage = criteria.get("max_memory_mb", 512)
        
        score = 1.0
        feedback = []
        suggestions = []
        
        # 检查结果中是否包含性能指标
        if isinstance(result, dict):
            execution_time = result.get("execution_time_ms", 0)
            if execution_time > max_execution_time:
                score -= min(0.5, (execution_time - max_execution_time) / max_execution_time)
                feedback.append(f"Execution time exceeded: {execution_time}ms > {max_execution_time}ms")
                suggestions.append("Consider optimizing the algorithm")
            
            memory_usage = result.get("memory_usage_mb", 0)
            if memory_usage > max_memory_usage:
                score -= min(0.3, (memory_usage - max_memory_usage) / max_memory_usage)
                feedback.append(f"Memory usage high: {memory_usage}MB > {max_memory_usage}MB")
                suggestions.append("Consider memory optimization techniques")
        
        return ValidationResult(
            is_valid=score >= criteria.get("threshold", 0.7),
            score=max(0, score),
            feedback="; ".join(feedback) if feedback else "Performance check passed",
            suggestions=suggestions,
            validator_id="performance_validator"
        )
    
    async def _validate_format(self, result: Any, 
                               criteria: Dict[str, Any]) -> ValidationResult:
        """验证格式"""
        expected_format = criteria.get("expected_format", "any")
        schema = criteria.get("schema")
        
        score = 1.0
        feedback = []
        
        if expected_format == "json":
            if not isinstance(result, (dict, list)):
                score = 0.0
                feedback.append("Result is not valid JSON")
        
        elif expected_format == "string":
            if not isinstance(result, str):
                score = 0.5
                feedback.append("Result is not a string")
        
        # 验证schema
        if schema and isinstance(result, dict):
            schema_errors = self._validate_schema(result, schema)
            if schema_errors:
                score -= len(schema_errors) * 0.1
                feedback.extend(schema_errors)
        
        return ValidationResult(
            is_valid=score >= criteria.get("threshold", 0.9),
            score=max(0, score),
            feedback="; ".join(feedback) if feedback else "Format check passed",
            validator_id="format_validator"
        )
    
    async def _validate_generic(self, result: Any, 
                                criteria: Dict[str, Any]) -> ValidationResult:
        """通用验证"""
        return ValidationResult(
            is_valid=True,
            score=1.0,
            feedback="Generic validation passed",
            validator_id="generic_validator"
        )
    
    def _calculate_similarity(self, a: Any, b: Any) -> float:
        """计算相似度"""
        if type(a) != type(b):
            return 0.0
        
        if isinstance(a, dict):
            keys_a = set(a.keys())
            keys_b = set(b.keys())
            if not keys_a:
                return 1.0 if not keys_b else 0.0
            intersection = keys_a & keys_b
            return len(intersection) / len(keys_a | keys_b)
        
        if isinstance(a, list):
            if not a:
                return 1.0 if not b else 0.0
            matches = sum(1 for x, y in zip(a, b) if x == y)
            return matches / max(len(a), len(b))
        
        return 1.0 if a == b else 0.0
    
    def _check_dict_consistency(self, data: Dict) -> List[str]:
        """检查字典一致性"""
        inconsistencies = []
        
        # 检查数值范围一致性
        for key, value in data.items():
            if isinstance(value, (int, float)):
                if "percentage" in key.lower() and (value < 0 or value > 100):
                    inconsistencies.append(f"{key} percentage out of range: {value}")
                if "score" in key.lower() and (value < 0 or value > 1):
                    inconsistencies.append(f"{key} score out of range: {value}")
        
        return inconsistencies
    
    def _validate_schema(self, data: Dict, schema: Dict) -> List[str]:
        """验证数据schema"""
        errors = []
        
        for key, expected_type in schema.items():
            if key not in data:
                errors.append(f"Missing required field: {key}")
            elif not isinstance(data[key], eval(expected_type) if isinstance(expected_type, str) else expected_type):
                errors.append(f"Type mismatch for {key}: expected {expected_type}")
        
        return errors


class IntegrationEngine:
    """整合引擎"""
    
    def __init__(self):
        self._integration_strategies: Dict[str, callable] = {
            "concatenate": self._integrate_concatenate,
            "merge": self._integrate_merge,
            "summarize": self._integrate_summarize,
            "aggregate": self._integrate_aggregate,
            "select_best": self._integrate_select_best
        }
    
    async def integrate(self, results: List[Any], strategy: str = "merge",
                       params: Dict[str, Any] = None) -> Any:
        """整合多个结果"""
        integrator = self._integration_strategies.get(strategy, self._integrate_merge)
        return await integrator(results, params or {})
    
    async def _integrate_concatenate(self, results: List[Any], 
                                     params: Dict[str, Any]) -> Any:
        """连接整合"""
        separator = params.get("separator", "\n")
        
        if all(isinstance(r, str) for r in results):
            return separator.join(results)
        
        if all(isinstance(r, list) for r in results):
            concatenated = []
            for r in results:
                concatenated.extend(r)
            return concatenated
        
        return results
    
    async def _integrate_merge(self, results: List[Any], 
                               params: Dict[str, Any]) -> Any:
        """合并整合"""
        if all(isinstance(r, dict) for r in results):
            merged = {}
            for r in results:
                merged.update(r)
            return merged
        
        if all(isinstance(r, list) for r in results):
            merged = []
            for r in results:
                merged.extend(r)
            return list(set(merged)) if params.get("unique", False) else merged
        
        return results
    
    async def _integrate_summarize(self, results: List[Any], 
                                   params: Dict[str, Any]) -> Any:
        """摘要整合"""
        max_items = params.get("max_items", 5)
        
        summary = {
            "total_results": len(results),
            "result_types": list(set(type(r).__name__ for r in results)),
            "timestamp": datetime.now().isoformat()
        }
        
        if all(isinstance(r, dict) for r in results):
            # 提取关键字段
            all_keys = set()
            for r in results:
                all_keys.update(r.keys())
            summary["available_fields"] = list(all_keys)
            
            # 统计数值字段
            numeric_stats = {}
            for key in all_keys:
                values = [r.get(key) for r in results if isinstance(r.get(key), (int, float))]
                if values:
                    numeric_stats[key] = {
                        "min": min(values),
                        "max": max(values),
                        "avg": sum(values) / len(values)
                    }
            if numeric_stats:
                summary["numeric_statistics"] = numeric_stats
        
        return summary
    
    async def _integrate_aggregate(self, results: List[Any], 
                                   params: Dict[str, Any]) -> Any:
        """聚合整合"""
        aggregation_type = params.get("type", "sum")
        
        if all(isinstance(r, (int, float)) for r in results):
            if aggregation_type == "sum":
                return sum(results)
            elif aggregation_type == "avg":
                return sum(results) / len(results) if results else 0
            elif aggregation_type == "max":
                return max(results) if results else 0
            elif aggregation_type == "min":
                return min(results) if results else 0
            elif aggregation_type == "count":
                return len(results)
        
        if all(isinstance(r, dict) for r in results):
            aggregated = {}
            for r in results:
                for key, value in r.items():
                    if key not in aggregated:
                        aggregated[key] = []
                    aggregated[key].append(value)
            
            # 对数值字段进行聚合
            for key, values in aggregated.items():
                if all(isinstance(v, (int, float)) for v in values):
                    if aggregation_type == "sum":
                        aggregated[key] = sum(values)
                    elif aggregation_type == "avg":
                        aggregated[key] = sum(values) / len(values)
            
            return aggregated
        
        return results
    
    async def _integrate_select_best(self, results: List[Any], 
                                     params: Dict[str, Any]) -> Any:
        """选择最佳结果"""
        scoring_key = params.get("scoring_key", "score")
        
        if not results:
            return None
        
        if all(isinstance(r, dict) for r in results):
            scored_results = [
                (r, r.get(scoring_key, 0)) for r in results
            ]
            scored_results.sort(key=lambda x: x[1], reverse=True)
            return scored_results[0][0] if scored_results else None
        
        # 默认返回第一个
        return results[0]


class ValidatorAgent(BaseAgent):
    """验证器Agent"""
    
    def __init__(self, config: AgentConfig, message_bus: MessageBus):
        super().__init__(config, message_bus)
        self.validation_engine = ValidationEngine()
        self._validation_history: List[Dict[str, Any]] = []
    
    async def on_start(self):
        """启动验证器"""
        print(f"ValidatorAgent {self.config.agent_id} started")
        self.register_message_handler(MessageType.VALIDATION_REQUEST, 
                                      self._handle_validation_request)
        
        # 向协调器注册
        await self.broadcast(
            {
                "action": "register_agent",
                "agent_id": self.config.agent_id,
                "agent_role": "validator",
                "capabilities": self.config.capabilities + ["validation"]
            },
            MessageType.COORDINATION
        )
    
    async def on_stop(self):
        """停止验证器"""
        print(f"ValidatorAgent {self.config.agent_id} stopped")
    
    async def process_task(self, task: SubTask) -> Any:
        """处理验证任务"""
        result_to_validate = task.parameters.get("result")
        validation_types = task.parameters.get("validation_types", ["completeness", "accuracy"])
        criteria = task.parameters.get("criteria", {})
        
        validation_results = {}
        
        for validation_type in validation_types:
            validation_result = await self.validation_engine.validate(
                result_to_validate, validation_type, criteria
            )
            validation_results[validation_type] = {
                "is_valid": validation_result.is_valid,
                "score": validation_result.score,
                "feedback": validation_result.feedback,
                "suggestions": validation_result.suggestions
            }
        
        # 计算综合得分
        overall_score = sum(r["score"] for r in validation_results.values()) / len(validation_results)
        is_valid = overall_score >= criteria.get("overall_threshold", 0.75)
        
        result = {
            "task_id": task.task_id,
            "validation_results": validation_results,
            "overall_score": overall_score,
            "is_valid": is_valid,
            "validated_at": datetime.now().isoformat()
        }
        
        # 记录验证历史
        self._validation_history.append(result)
        
        return result
    
    async def _handle_validation_request(self, message: Message):
        """处理验证请求"""
        content = message.content
        action = content.get("action")
        
        if action == "validate_task":
            task_id = content.get("task_id")
            subtasks_results = content.get("subtasks_results", [])
            
            # 创建验证子任务
            subtask = SubTask(
                parent_task_id=task_id,
                description=f"验证任务结果: {task_id}",
                task_type="validation",
                parameters={
                    "result": subtasks_results,
                    "validation_types": ["completeness", "consistency"]
                }
            )
            
            await self.assign_task(subtask)


class IntegratorAgent(BaseAgent):
    """整合器Agent"""
    
    def __init__(self, config: AgentConfig, message_bus: MessageBus):
        super().__init__(config, message_bus)
        self.integration_engine = IntegrationEngine()
        self._integration_history: List[Dict[str, Any]] = []
        self._pending_validations: Dict[str, Dict[str, Any]] = {}
    
    async def on_start(self):
        """启动整合器"""
        print(f"IntegratorAgent {self.config.agent_id} started")
        self.register_message_handler(MessageType.VALIDATION_RESULT, 
                                      self._handle_validation_result)
        
        # 向协调器注册
        await self.broadcast(
            {
                "action": "register_agent",
                "agent_id": self.config.agent_id,
                "agent_role": "integrator",
                "capabilities": self.config.capabilities + ["integration"]
            },
            MessageType.COORDINATION
        )
    
    async def on_stop(self):
        """停止整合器"""
        print(f"IntegratorAgent {self.config.agent_id} stopped")
    
    async def process_task(self, task: SubTask) -> Any:
        """处理整合任务"""
        results_to_integrate = task.parameters.get("results", [])
        strategy = task.parameters.get("strategy", "merge")
        params = task.parameters.get("params", {})
        
        # 执行整合
        integrated_result = await self.integration_engine.integrate(
            results_to_integrate, strategy, params
        )
        
        result = {
            "task_id": task.task_id,
            "strategy": strategy,
            "input_count": len(results_to_integrate),
            "result": integrated_result,
            "integrated_at": datetime.now().isoformat()
        }
        
        # 记录整合历史
        self._integration_history.append(result)
        
        return result
    
    async def integrate_task_results(self, task_id: str, 
                                     subtasks: List[SubTask],
                                     validation_results: List[ValidationResult] = None) -> Any:
        """整合任务结果"""
        # 收集所有成功的子任务结果
        successful_results = [
            s.result for s in subtasks 
            if s.status == TaskStatus.COMPLETED and s.result
        ]
        
        if not successful_results:
            return {"error": "No successful results to integrate"}
        
        # 根据验证结果选择整合策略
        if validation_results:
            avg_score = sum(v.score for v in validation_results) / len(validation_results)
            if avg_score < 0.6:
                strategy = "select_best"
            elif avg_score < 0.8:
                strategy = "summarize"
            else:
                strategy = "merge"
        else:
            strategy = "merge"
        
        # 创建整合子任务
        subtask = SubTask(
            parent_task_id=task_id,
            description=f"整合任务结果: {task_id}",
            task_type="integration",
            parameters={
                "results": successful_results,
                "strategy": strategy,
                "params": {"unique": True}
            }
        )
        
        await self.assign_task(subtask)
        
        return {"integration_initiated": True, "strategy": strategy}
    
    async def _handle_validation_result(self, message: Message):
        """处理验证结果"""
        content = message.content
        task_id = content.get("task_id")
        validation_results = content.get("validation_results", {})
        
        # 存储验证结果
        if task_id not in self._pending_validations:
            self._pending_validations[task_id] = {
                "validations": [],
                "timestamp": datetime.now()
            }
        
        self._pending_validations[task_id]["validations"].append(validation_results)
        
        # 检查是否可以进行整合
        await self._check_and_integrate(task_id)
    
    async def _check_and_integrate(self, task_id: str):
        """检查并执行整合"""
        pending = self._pending_validations.get(task_id)
        if not pending:
            return
        
        # 这里可以添加更复杂的逻辑，比如等待所有验证完成
        # 简化版：直接触发整合
        
        # 发送整合完成消息
        await self.broadcast(
            {
                "action": "integration_ready",
                "task_id": task_id,
                "validation_count": len(pending["validations"])
            },
            MessageType.COORDINATION
        )
