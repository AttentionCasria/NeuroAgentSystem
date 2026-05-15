from abc import ABC, abstractmethod
from typing import List
from app.agents.schemas.retrieval import RerankResult


class BaseReranker(ABC):
    """重排序基类"""

    @abstractmethod
    def rerank(self, query: str, documents: List[str], top_k: int = 5) -> List[RerankResult]:
        """
        重排序文档

        Args:
            query: 查询文本
            documents: 文档列表
            top_k: 返回前k个结果

        Returns:
            重排序结果列表
        """
        pass
