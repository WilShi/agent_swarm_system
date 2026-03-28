class AgentSwarmException(Exception):
    """基础异常"""
    pass


class ClassificationError(AgentSwarmException):
    """任务分类错误"""
    pass


class HarnessError(AgentSwarmException):
    """Harness 错误"""
    pass


class HarnessInitError(HarnessError):
    """Harness 初始化错误"""
    pass


class SwarmExecutionError(AgentSwarmException):
    """Swarm 执行错误"""
    pass


class ConfirmationTimeoutError(AgentSwarmException):
    """确认超时错误"""
    pass


class ValidationError(AgentSwarmException):
    """验证错误"""
    pass
