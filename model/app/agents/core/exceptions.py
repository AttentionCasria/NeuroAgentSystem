"""自定义异常类"""


class AgentException(Exception):
    """Agent 基础异常"""
    pass


class RetrievalException(AgentException):
    """检索异常"""
    pass


class RerankException(AgentException):
    """重排序异常"""
    pass


class LLMException(AgentException):
    """LLM 调用异常"""
    pass


class PipelineException(AgentException):
    """Pipeline 执行异常"""
    pass
