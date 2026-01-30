import logging
from pathlib import Path
from typing import List

# 引入你的新 RAG 模块
from rag.loader import load_pdfs_from_dir
from rag.splitter import split_documents
from rag.vectorstore import build_or_load_vectorstore
from rag.retriever import HybridRetriever

logger = logging.getLogger(__name__)

# 配置路径
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG = {
    # 【修改点1】修正为已存在的数据库目录名 (之前叫 chroma_db_bge)
    # 使用绝对路径防止找不到
    "persist_dir": str(PROJECT_ROOT / "chroma_db_bge"),
    "docs_dir": str(PROJECT_ROOT / "Data" / "documents"),
    "top_k_per_store": 6,
    "top_k_final": 6
}


class UnifiedSearchEngine:
    """
    【适配器模式】
    统一检索引擎，连接 Agent 和 底层 RAG 实现。
    """

    def __init__(self, persist_dir: str = None, top_k: int = 6):
        self.logger = logging.getLogger(__name__)
        self.logger.info("🔧 初始化 UnifiedSearchEngine (RAG Adapter)...")

        # 1. 准备数据 (注意: BM25 需要这一步内存构建，不可省略，但很快)
        docs_path = CONFIG["docs_dir"]
        self.logger.info(f"📄 正在加载文档(用于BM25索引构建): {docs_path}")
        docs = load_pdfs_from_dir(docs_path)
        chunks = split_documents(docs)

        # 2. 准备向量库
        # 【修改点2】显式传入数据库路径，确保加载旧库而不是新建
        target_db_path = persist_dir if persist_dir else CONFIG["persist_dir"]
        self.logger.info(f"💾 连接向量库: {target_db_path}")

        # 关键：传入 persist_dir 参数
        vectordb = build_or_load_vectorstore(chunks, persist_dir=target_db_path)

        # 3. 初始化混合检索器
        self.retriever = HybridRetriever(vectordb, chunks, k=top_k)

        self.logger.info("✅ 检索引擎加载完成!")

    def search(self, query: str, top_k_final: int = 4) -> List:
        """
        Agent 需要的标准接口
        """
        self.logger.info(f"🔍 Agent RAG 检索: {query}")
        try:
            # 直接代理给 HybridRetriever
            results = self.retriever.get_relevant_documents(query)
            # 截取最终数量
            final_results = results[:top_k_final]

            # --- 新增日志打印逻辑 ---
            if final_results:
                self.logger.info(f"🏆 检索成功，命中 {len(final_results)} 条相关文档:")
                for i, doc in enumerate(final_results, 1):
                    # 获取元数据中的文件名，预防没有 source 字段的情况
                    source = doc.metadata.get("source", "未知来源")
                    if isinstance(source, str):
                        source = Path(source).name  # 只保留文件名，不打印长路径

                    # 压缩内容中的换行符，防止日志刷屏
                    content_preview = doc.page_content.replace('\n', ' ').strip()
                    # 截取前 150 个字符用于预览
                    preview_text = f"{content_preview[:150]}..." if len(content_preview) > 150 else content_preview

                    self.logger.info(f"  👉 [结果 {i}] (来源: {source}): {preview_text}")
            else:
                self.logger.warning("⚠️ RAG 检索结果为空 (没有找到匹配文档)")
            # ----------------------

            return final_results
        except Exception as e:
            self.logger.error(f"❌ 检索发生错误: {e}", exc_info=True)
            return []
        #     # 截取最终数量
        #     return results[:top_k_final]
        # except Exception as e:
        #     self.logger.error(f"❌ 检索发生错误: {e}")
        #     return []


if __name__ == '__main__':
    # 快速测试
    logging.basicConfig(level=logging.INFO)
    engine = UnifiedSearchEngine()
    res = engine.search("脑梗死出血转化")
    print(f"找到 {len(res)} 条结果")

# import logging
# from pathlib import Path
# from typing import List, Dict, Any, Optional
#
# from chromadb import PersistentClient
# from langchain_chroma import Chroma
# from langchain_core.documents import Document
# from langchain_community.retrievers import BM25Retriever
# from langchain_openai import OpenAIEmbeddings
#
# # 配置日志记录器
# logger = logging.getLogger(__name__)
#
#
# # ====== 自定义混合检索器 ======
# class SimpleEnsembleRetriever:
#     """简单的混合检索器，替代 EnsembleRetriever"""
#
#     def __init__(self, retrievers: List, weights: List[float] = None):
#         self.retrievers = retrievers
#         self.weights = weights or [1.0 / len(retrievers)] * len(retrievers)
#
#     def invoke(self, query: str) -> List[Document]:
#         """执行检索并合并结果"""
#         all_docs = []
#         seen_contents = set()
#
#         for idx, retriever in enumerate(self.retrievers):
#             try:
#                 docs = retriever.invoke(query)
#                 for doc in docs:
#                     # 基于内容简单去重
#                     if doc.page_content not in seen_contents:
#                         seen_contents.add(doc.page_content)
#                         all_docs.append(doc)
#             except Exception as e:
#                 logger.warning(f"⚠️ 自定义检索器 (索引 {idx}) 调用失败: {e}")
#                 continue
#
#         return all_docs
#
#
# # ====== 配置常量 ======
# CONFIG = {
#     "persist_dir": "D:/pycharmProject/MedLLM/chroma_db_unified",
#     "top_k_per_store": 6,
#     "top_k_final": 6
# }
#
#
# class UnifiedSearchEngine:
#     """
#     统一的多集合 RAG 检索引擎。
#     封装了 Chroma 客户端管理、混合检索器构建及缓存。
#     """
#
#     def __init__(self, persist_dir: str, top_k: int):
#         self.persist_dir = Path(persist_dir).expanduser().resolve()
#         self.top_k = top_k
#         self.embedding_fn = OpenAIEmbeddings()
#         self._client: Optional[PersistentClient] = None
#         self._retrievers: Dict[str, SimpleEnsembleRetriever] = {}  # 缓存检索器
#
#     @property
#     def client(self) -> PersistentClient:
#         """懒加载 Chroma 客户端"""
#         if self._client is None:
#             if not self.persist_dir.exists():
#                 logger.error(f"❌ 向量库目录不存在: {self.persist_dir}")
#                 raise FileNotFoundError(f"向量库目录不存在: {self.persist_dir}")
#             try:
#                 self._client = PersistentClient(path=str(self.persist_dir))
#             except Exception as e:
#                 logger.error(f"❌ 初始化 Chroma 客户端失败: {e}")
#                 raise
#         return self._client
#
#     def _get_hybrid_retriever(self, collection_name: str) -> Optional[SimpleEnsembleRetriever]:
#         """构建单个集合的混合检索器 (BM25 + Vector)"""
#         try:
#             vector_store = Chroma(
#                 client=self.client,
#                 collection_name=collection_name,
#                 embedding_function=self.embedding_fn,
#             )
#
#             # Step 1: 提取所有文档构建 BM25
#             data = vector_store._collection.get(include=["documents", "metadatas"])
#             docs = data.get("documents", [])
#             metas = data.get("metadatas", [])
#
#             if not docs:
#                 return None
#
#             bm25_docs = [Document(page_content=d, metadata=m or {}) for d, m in zip(docs, metas)]
#             bm25 = BM25Retriever.from_documents(bm25_docs)
#             bm25.k = self.top_k * 2
#
#             # Step 2: 构建向量检索器
#             vector_retriever = vector_store.as_retriever(
#                 search_type="similarity", search_kwargs={"k": self.top_k * 2}
#             )
#
#             # Step 3: 组合
#             return SimpleEnsembleRetriever(
#                 retrievers=[bm25, vector_retriever],
#                 weights=[0.4, 0.6]
#             )
#
#         except Exception as e:
#             logger.warning(f"⚠️ 集合 '{collection_name}' 初始化混合检索器失败: {e}")
#             return None
#
#     def _ensure_retrievers_loaded(self):
#         """加载并缓存所有集合的检索器"""
#         if self._retrievers:
#             return
#
#         try:
#             collections = self.client.list_collections()
#             logger.info(f"📚 发现 {len(collections)} 个 Chroma 集合，正在初始化...")
#
#             for col in collections:
#                 if retriever := self._get_hybrid_retriever(col.name):
#                     self._retrievers[col.name] = retriever
#                     logger.info(f"✅ [Load] 集合已就绪: {col.name}")
#
#         except Exception as e:
#             logger.error(f"❌ 加载集合列表失败: {e}")
#
#     def search(self, query: str, top_k_final: int = 6) -> List[Document]:
#         """执行跨集合 RAG 检索主流程"""
#         # 使用 logger.info 清晰展示检索动作
#         logger.info(f"🔍 [UnifiedSearch] 正在检索: '{query[:50]}...'")
#         self._ensure_retrievers_loaded()
#
#         candidates = []
#
#         # 1. 第一阶段：多路召回
#         for name, retriever in self._retrievers.items():
#             try:
#                 raw_docs = retriever.invoke(query)
#
#                 # 去重 (使用 dict key 特性)
#                 unique_docs = {doc.page_content: doc for doc in raw_docs}
#                 current_candidates = list(unique_docs.values())[:self.top_k]
#
#                 for doc in current_candidates:
#                     candidates.append({"collection": name, "document": doc, "score": 0})
#
#                 if current_candidates:
#                     logger.info(f"  ➜ [{name}] 召回 {len(current_candidates)} 条文档")
#             except Exception as e:
#                 logger.error(f"  ❌ [{name}] 检索出错: {e}")
#
#         # 2. 第二阶段：排序 (简单截断，实际可接入 Rerank)
#         reranked = candidates[:top_k_final]
#
#         if not reranked:
#             logger.warning("⚠️ 未找到任何相关文档。")
#             return []
#
#         # 3. 结果汇总
#         logger.info(f"🏆 [UnifiedSearch] 最终筛选出 {len(reranked)} 条文档")
#         results = [item["document"] for item in reranked]
#         return results
#
#
# # ====== 使用示例 ======
# if __name__ == '__main__':
#     # 设置本地测试的日志格式
#     logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
#
#     engine = UnifiedSearchEngine(
#         persist_dir=CONFIG["persist_dir"],
#         top_k=CONFIG["top_k_per_store"]
#     )
#
#     query_text = "I am foaming at the mouth; what disease is this?"
#     final_docs = engine.search(query=query_text, top_k_final=CONFIG["top_k_final"])
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
# # from pathlib import Path
# # from typing import List, Dict, Any, Optional
# #
# # from chromadb import PersistentClient
# # from langchain_chroma import Chroma
# # from langchain_core.documents import Document
# # from langchain_community.retrievers import BM25Retriever
# # from langchain_openai import OpenAIEmbeddings
# #
# #
# # # ====== 自定义混合检索器 ======
# # class SimpleEnsembleRetriever:
# #     """简单的混合检索器，替代 EnsembleRetriever"""
# #
# #     def __init__(self, retrievers: List, weights: List[float] = None):
# #         self.retrievers = retrievers
# #         self.weights = weights or [1.0 / len(retrievers)] * len(retrievers)
# #
# #     def invoke(self, query: str) -> List[Document]:
# #         """执行检索并合并结果"""
# #         all_docs = []
# #         seen_contents = set()
# #
# #         for retriever in self.retrievers:
# #             try:
# #                 docs = retriever.invoke(query)
# #                 for doc in docs:
# #                     # 基于内容去重
# #                     if doc.page_content not in seen_contents:
# #                         seen_contents.add(doc.page_content)
# #                         all_docs.append(doc)
# #             except Exception as e:
# #                 print(f"⚠️ 检索器调用失败: {e}")
# #                 continue
# #
# #         return all_docs
# #
# #
# # # ====== 配置常量 ======
# # CONFIG = {
# #     "persist_dir": "D:/pycharmProject/MedLLM/chroma_db_unified",
# #     "top_k_per_store": 6,
# #     "top_k_final": 6
# # }
# #
# #
# # class UnifiedSearchEngine:
# #     """
# #     统一的多集合 RAG 检索引擎。
# #     封装了 Chroma 客户端管理、混合检索器构建及缓存。
# #     """
# #
# #     def __init__(self, persist_dir: str, top_k: int):
# #         self.persist_dir = Path(persist_dir).expanduser().resolve()
# #         self.top_k = top_k
# #         self.embedding_fn = OpenAIEmbeddings()
# #         self._client: Optional[PersistentClient] = None
# #         self._retrievers: Dict[str, SimpleEnsembleRetriever] = {}  # 缓存检索器
# #
# #     @property
# #     def client(self) -> PersistentClient:
# #         """懒加载 Chroma 客户端"""
# #         if self._client is None:
# #             if not self.persist_dir.exists():
# #                 raise FileNotFoundError(f"向量库目录不存在: {self.persist_dir}")
# #             try:
# #                 self._client = PersistentClient(path=str(self.persist_dir))
# #             except Exception as e:
# #                 print(f"❌ 初始化客户端失败: {e}")
# #                 raise
# #         return self._client
# #
# #     def _get_hybrid_retriever(self, collection_name: str) -> Optional[SimpleEnsembleRetriever]:
# #         """构建单个集合的混合检索器 (BM25 + Vector)"""
# #         try:
# #             vector_store = Chroma(
# #                 client=self.client,
# #                 collection_name=collection_name,
# #                 embedding_function=self.embedding_fn,
# #             )
# #
# #             # Step 1: 提取所有文档构建 BM25
# #             data = vector_store._collection.get(include=["documents", "metadatas"])
# #             docs = data.get("documents", [])
# #             metas = data.get("metadatas", [])
# #
# #             if not docs:
# #                 return None
# #
# #             bm25_docs = [Document(page_content=d, metadata=m or {}) for d, m in zip(docs, metas)]
# #             bm25 = BM25Retriever.from_documents(bm25_docs)
# #             bm25.k = self.top_k * 2
# #
# #             # Step 2: 构建向量检索器
# #             vector_retriever = vector_store.as_retriever(
# #                 search_type="similarity", search_kwargs={"k": self.top_k * 2}
# #             )
# #
# #             # Step 3: 组合 (权重可根据需求调整)
# #             return SimpleEnsembleRetriever(
# #                 retrievers=[bm25, vector_retriever],
# #                 weights=[0.4, 0.6]
# #             )
# #
# #         except Exception as e:
# #             print(f"⚠️ 为集合 '{collection_name}' 创建检索器失败: {e}")
# #             return None
# #
# #     def _ensure_retrievers_loaded(self):
# #         """加载并缓存所有集合的检索器"""
# #         if self._retrievers:
# #             return
# #
# #         try:
# #             collections = self.client.list_collections()
# #             print(f"发现 {len(collections)} 个集合，正在初始化混合检索器...")
# #
# #             for col in collections:
# #                 if retriever := self._get_hybrid_retriever(col.name):
# #                     self._retrievers[col.name] = retriever
# #                     print(f"✅ 已加载集合: {col.name}")
# #
# #         except Exception as e:
# #             print(f"❌ 加载集合列表失败: {e}")
# #
# #     def search(self, query: str, top_k_final: int = 6) -> List[Document]:
# #         """执行跨集合 RAG 检索主流程"""
# #         print(f"\n🔍 开始检索: '{query}'")
# #         self._ensure_retrievers_loaded()
# #
# #         candidates = []
# #
# #         # 1. 第一阶段：多路召回
# #         for name, retriever in self._retrievers.items():
# #             try:
# #                 raw_docs = retriever.invoke(query)
# #
# #                 # 去重 (使用 dict key 特性)
# #                 unique_docs = {doc.page_content: doc for doc in raw_docs}
# #                 current_candidates = list(unique_docs.values())[:self.top_k]
# #
# #                 for doc in current_candidates:
# #                     candidates.append({"collection": name, "document": doc, "score": 0})
# #
# #                 print(f"  ➜ [{name}] 召回 {len(current_candidates)} 条")
# #             except Exception as e:
# #                 print(f"  ❌ [{name}] 检索出错: {e}")
# #
# #         # 2. 第二阶段：排序
# #         reranked = candidates[:top_k_final]
# #
# #         if not reranked:
# #             print("⚠️ 未找到相关文档。")
# #             return []
# #
# #         # 3. 输出结果演示
# #         print(f"\n🏆 最终结果 ({len(reranked)} 条):")
# #         results = []
# #         for i, item in enumerate(reranked, 1):
# #             doc = item["document"]
# #             results.append(doc)
# #             content_preview = doc.page_content[:100].replace('\n', ' ')
# #             print(f"  {i}. [{item['collection']}] {content_preview}...")
# #
# #         return results
# #
# #
# # # ====== 使用示例 ======
# # if __name__ == '__main__':
# #     engine = UnifiedSearchEngine(
# #         persist_dir=CONFIG["persist_dir"],
# #         top_k=CONFIG["top_k_per_store"]
# #     )
# #
# #     query_text = "I am foaming at the mouth; what disease is this?"
# #     final_docs = engine.search(query=query_text, top_k_final=CONFIG["top_k_final"])
# #
# #
