"""
任务监控器 - 跟踪任务执行状态和子任务详情
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class TaskStage(Enum):
    """任务阶段"""
    PENDING = "pending"         # 等待中
    DECOMPOSING = "decomposing" # 分解中
    EXECUTING = "executing"     # 执行中
    VALIDATING = "validating"   # 验证中
    INTEGRATING = "integrating" # 整合中
    COMPLETED = "completed"     # 已完成
    FAILED = "failed"           # 失败


@dataclass
class SubTaskInfo:
    """子任务信息"""
    subtask_id: str
    task_type: str
    description: str
    status: str
    assigned_to: Optional[str] = None
    agent_name: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: float = 0.0
    result: Any = None
    error: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)


@dataclass
class TaskExecutionInfo:
    """任务执行信息"""
    task_id: str
    description: str
    task_type: str
    stage: TaskStage
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: float = 0.0
    subtasks: List[SubTaskInfo] = field(default_factory=list)
    current_subtask: Optional[str] = None
    progress: float = 0.0
    result: Any = None
    error: Optional[str] = None


class TaskMonitor:
    """任务监控器"""

    def __init__(self):
        self._tasks: Dict[str, TaskExecutionInfo] = {}
        self._subtask_map: Dict[str, str] = {}  # subtask_id -> task_id

    def register_task(self, task_id: str, description: str, task_type: str):
        """注册任务"""
        self._tasks[task_id] = TaskExecutionInfo(
            task_id=task_id,
            description=description,
            task_type=task_type,
            stage=TaskStage.PENDING,
            start_time=datetime.now()
        )

    def update_stage(self, task_id: str, stage: TaskStage):
        """更新任务阶段"""
        if task_id not in self._tasks:
            return

        task = self._tasks[task_id]
        task.stage = stage

        if stage in [TaskStage.COMPLETED, TaskStage.FAILED]:
            task.end_time = datetime.now()
            task.duration = (task.end_time - task.start_time).total_seconds()

    def register_subtask(self, task_id: str, subtask_id: str, task_type: str,
                        description: str, dependencies: List[str] = None):
        """注册子任务"""
        if task_id not in self._tasks:
            return

        subtask = SubTaskInfo(
            subtask_id=subtask_id,
            task_type=task_type,
            description=description,
            status="pending",
            dependencies=dependencies if dependencies is not None else []
        )

        self._tasks[task_id].subtasks.append(subtask)
        self._subtask_map[subtask_id] = task_id

    def update_subtask_status(self, subtask_id: str, status: str,
                             assigned_to: Optional[str] = None,
                             agent_name: Optional[str] = None):
        """更新子任务状态"""
        if subtask_id not in self._subtask_map:
            return

        task_id = self._subtask_map[subtask_id]
        task = self._tasks[task_id]

        for subtask in task.subtasks:
            if subtask.subtask_id == subtask_id:
                subtask.status = status

                if status == "in_progress":
                    subtask.start_time = datetime.now()
                    subtask.assigned_to = assigned_to
                    subtask.agent_name = agent_name
                    task.current_subtask = subtask_id

                elif status in ["completed", "failed"]:
                    subtask.end_time = datetime.now()
                    if subtask.start_time:
                        subtask.duration = (subtask.end_time - subtask.start_time).total_seconds()

                break

        # 更新整体进度
        self._update_progress(task_id)

    def update_subtask_result(self, subtask_id: str, result: Any,
                             error: Optional[str] = None):
        """更新子任务结果"""
        if subtask_id not in self._subtask_map:
            return

        task_id = self._subtask_map[subtask_id]
        task = self._tasks[task_id]

        for subtask in task.subtasks:
            if subtask.subtask_id == subtask_id:
                subtask.result = result
                subtask.error = error
                break

    def _update_progress(self, task_id: str):
        """更新任务进度"""
        task = self._tasks[task_id]
        total = len(task.subtasks)

        if total == 0:
            task.progress = 0.0
            return

        completed = sum(1 for s in task.subtasks if s.status in ["completed", "failed"])
        task.progress = (completed / total) * 100

    def get_task_info(self, task_id: str) -> Optional[TaskExecutionInfo]:
        """获取任务信息"""
        return self._tasks.get(task_id)

    def get_subtask_info(self, subtask_id: str) -> Optional[SubTaskInfo]:
        """获取子任务信息"""
        if subtask_id not in self._subtask_map:
            return None

        task_id = self._subtask_map[subtask_id]
        task = self._tasks[task_id]

        for subtask in task.subtasks:
            if subtask.subtask_id == subtask_id:
                return subtask
        return None

    def get_active_tasks(self) -> List[TaskExecutionInfo]:
        """获取进行中的任务"""
        return [t for t in self._tasks.values()
                if t.stage not in [TaskStage.COMPLETED, TaskStage.FAILED]]

    def get_completed_tasks(self) -> List[TaskExecutionInfo]:
        """获取已完成的任务"""
        return [t for t in self._tasks.values() if t.stage == TaskStage.COMPLETED]

    def get_task_summary(self, task_id: str) -> Dict[str, Any]:
        """获取任务摘要"""
        task = self._tasks.get(task_id)
        if not task:
            return {}

        return {
            "task_id": task_id,
            "description": task.description,
            "type": task.task_type,
            "stage": task.stage.value,
            "progress": f"{task.progress:.1f}%",
            "duration": f"{task.duration:.1f}s",
            "subtasks": {
                "total": len(task.subtasks),
                "completed": sum(1 for s in task.subtasks if s.status == "completed"),
                "failed": sum(1 for s in task.subtasks if s.status == "failed"),
                "in_progress": sum(1 for s in task.subtasks if s.status == "in_progress"),
                "pending": sum(1 for s in task.subtasks if s.status == "pending")
            }
        }

    def get_all_tasks_summary(self) -> List[Dict[str, Any]]:
        """获取所有任务摘要"""
        return [self.get_task_summary(tid) for tid in self._tasks.keys()]
