from typing import List
from sentence_transformers import CrossEncoder
from langchain_core.documents import Document


class BGEReranker:
    """
    使用 BAAI bge-reranker-base 对候选文档进行重排序
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-base", top_k: int = 5):
        print("🔥 加载 BGE Reranker 模型...")
        self.model = CrossEncoder(model_name)
        self.top_k = top_k

    def rerank(self, query: str, docs: List[Document]) -> List[Document]:
        if not docs:
            return []

        # 构造 (query, document) 对
        pairs = [(query, doc.page_content) for doc in docs]

        # 计算相关性分数
        scores = self.model.predict(pairs)

        # 按分数排序
        ranked = sorted(
            zip(docs, scores),
            key=lambda x: x[1],
            reverse=True
        )

        # 返回 Top-K 文档
        return [doc for doc, _ in ranked[: self.top_k]]
