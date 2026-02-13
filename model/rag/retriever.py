from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from rag.reranker import BGEReranker


class HybridRetriever:

    def __init__(self, vectordb, documents, k=20):
        self.vectordb = vectordb
        self.k = k

        # BM25
        self.bm25 = BM25Retriever.from_documents(documents)
        self.bm25.k = k

        # Vector
        self.vector_retriever = vectordb.as_retriever(search_kwargs={"k": k})

        # 🔥 Reranker
        self.reranker = BGEReranker(top_k=5)

    def get_relevant_documents(self, query: str):
        # 1. 多路召回
        bm25_docs = self.bm25.invoke(query)
        vector_docs = self.vector_retriever.invoke(query)

        # 2. 去重
        seen = {}
        for doc in bm25_docs + vector_docs:
            seen[doc.page_content] = doc

        candidates = list(seen.values())

        print(f"🔍 初始召回 {len(candidates)} 条，开始 rerank...")

        # 3. 🔥 rerank
        final_docs = self.reranker.rerank(query, candidates)

        return final_docs

