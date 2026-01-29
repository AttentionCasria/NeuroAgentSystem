# rag/search_tool.py
from typing import List
from langchain_core.documents import Document
from makeData.Retrieve import UnifiedSearchEngine

class MedicalSearchTool:
    """
    Agent 专用的医学文档搜索工具
    """

    def __init__(self):
        self.engine = UnifiedSearchEngine(
            persist_dir="chroma_db_bge",
            top_k=20
        )

    def search(self, query: str) -> str:
        """
        给 Agent 用的统一搜索接口
        返回：整理后的文本（而不是 Document 对象）
        """
        docs: List[Document] = self.engine.search(
            query=query,
            top_k_final=6
        )

        if not docs:
            return "未在医学文档中检索到相关内容。"

        context_blocks = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "未知来源")
            page = doc.metadata.get("page", "?")
            content = doc.page_content.strip()

            context_blocks.append(
                f"[{i}] 来源: {source} (第 {page} 页)\n{content}"
            )

        return "\n\n".join(context_blocks)
