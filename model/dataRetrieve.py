from pathlib import Path
from chromadb import PersistentClient
from langchain_chroma import Chroma
from langchain.schema import Document
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain_openai import OpenAIEmbeddings
import numpy as np
import os
import time
from typing import List, Dict, Any, Tuple
#from deepseek_reranker import Reranker

# ====== 统一配置部分 ======
# 只保留一个持久化目录
UNIFIED_PERSIST_DIR = "D:/pycharmProject/MedicalRAG/chroma_db_unified"
TOP_K_PER_STORE = 6
TOP_K_FINAL = 6

# 全局 embedding 函数
embedding_function = OpenAIEmbeddings()

# 全局缓存：首次加载时填充，后续复用
VECTOR_STORES: Dict[str, Chroma] = None
# 全局客户端
GLOBAL_CLIENT: PersistentClient = None


def init_global_client():
    """
    初始化全局 Chroma 客户端。
    """
    global GLOBAL_CLIENT
    if GLOBAL_CLIENT is None:
        try:
            persist_path = Path(UNIFIED_PERSIST_DIR).expanduser().resolve()
            if not persist_path.exists():
                raise FileNotFoundError(f"统一向量库目录不存在: {persist_path}")
            GLOBAL_CLIENT = PersistentClient(path=str(persist_path))
        except Exception as e:
            print(f"初始化 Chroma 客户端失败: {e}")
            GLOBAL_CLIENT = None


def load_all_collections() -> Dict[str, Chroma]:
    """
    加载单个 Chroma 实例下的所有 Collection。
    """
    global VECTOR_STORES
    if VECTOR_STORES is not None:
        print("所有 Collection 已从缓存加载。")
        return VECTOR_STORES

    init_global_client()
    if GLOBAL_CLIENT is None:
        return {}

    VECTOR_STORES = {}

    # 从 Chroma 客户端获取所有 Collection 的名称
    try:
        collections = GLOBAL_CLIENT.list_collections()
        collection_names = [col.name for col in collections]
    except Exception as e:
        print(f"无法列出 Chroma Collections: {e}")
        return {}

    for name in collection_names:
        try:
            vector_store = Chroma(
                client=GLOBAL_CLIENT,
                collection_name=name,
                embedding_function=embedding_function,
            )
            VECTOR_STORES[name] = vector_store
            print(f"成功加载 Collection: {name}")
        except Exception as e:
            print(f"加载 Collection '{name}' 时出错: {e}")

    print(f"所有 Collection 已加载完毕，共 {len(VECTOR_STORES)} 个。")
    return VECTOR_STORES


def get_all_collections() -> Dict[str, Chroma]:
    """
    获取所有已加载的 Chroma VectorStore 实例。
    """
    global VECTOR_STORES
    if VECTOR_STORES is None:
        VECTOR_STORES = load_all_collections()
    return VECTOR_STORES


def get_all_retrievers(top_k: int) -> Dict[str, EnsembleRetriever]:
    """
    为所有加载的向量库创建混合检索器。
    """
    retrievers = {}
    vector_stores = get_all_collections()

    for name, vector_store in vector_stores.items():
        try:
            retriever = create_hybrid_retriever_for_store(vector_store, k=top_k * 2)
            retrievers[name] = retriever
        except Exception as e:
            print(f"为 Collection '{name}' 创建混合检索器时出错: {e}")
            retrievers[name] = None

    return retrievers


def retrieve_candidates(query: str, all_retrievers: Dict[str, EnsembleRetriever], top_k: int) -> List[Dict[str, Any]]:
    """
    从所有检索器中获取初始候选文档。
    """
    candidates = []

    for collection_name, retriever in all_retrievers.items():
        if retriever is None:
            continue
        try:
            # 确保获取的文档是唯一的
            unique_docs = set()
            docs = []

            # 使用 get_relevant_documents 获取文档
            retrieved_docs = retriever.get_relevant_documents(query)

            for doc in retrieved_docs:
                # 使用文档内容作为唯一标识
                if doc.page_content not in unique_docs:
                    unique_docs.add(doc.page_content)
                    docs.append(doc)

            # 只保留每个库的前 k 个候选
            for doc in docs[:top_k]:
                candidates.append({"collection": collection_name, "document": doc})

            print(f"第一阶段混合检索 {collection_name} 结果共 {len(docs)} 条。")
        except Exception as e:
            print(f"第一阶段混合检索 {collection_name} 时出错: {e}")

    print(f"第一阶段候选共 {len(candidates)} 条（每库最多 {top_k} 条）。")
    return candidates

# from deepseek_reranker import Reranker

def create_hybrid_retriever_for_store(vector_store: Chroma, k: int):
    """
    给定单个 Chroma Collection，创建 BM25 + 向量检索混合检索器。
    """
    # Step 1: 尝试获取所有文档
    try:
        docs_data = vector_store._collection.get(include=["documents", "metadatas"])
        documents = docs_data.get("documents", [])
        metadatas = docs_data.get("metadatas", [])
    except Exception as e:
        print(f"⚠️ 无法从 Collection '{vector_store._collection.name}' 获取文档，跳过向量检索: {e}")
        documents = []
        metadatas = []

    # 构造 BM25Retriever（只用文本和 metadata）
    bm25_docs = [Document(page_content=doc, metadata=meta) for doc, meta in zip(documents, metadatas)]
    bm25_retriever = BM25Retriever.from_documents(bm25_docs)
    bm25_retriever.k = k

    # 尝试创建向量检索器
    try:
        vector_retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": k}
        )
        retrievers = [bm25_retriever, vector_retriever]
        weights = [0.4, 0.6]
    except Exception as e:
        print(f"⚠️ Collection '{vector_store._collection.name}' 向量检索不可用，仅使用 BM25: {e}")
        retrievers = [bm25_retriever]
        weights = [1.0]

    return EnsembleRetriever(retrievers=retrievers, weights=weights)


def rerank_candidates(candidates: List[Dict[str, Any]], query: str, top_k: int) -> List[Dict[str, Any]]:
    # 目前不使用 reranker，所有文档 score = 0
    for item in candidates:
        item["score"] = 0
    return sorted(candidates, key=lambda x: x["score"], reverse=True)[:top_k]



def multi_collection_rag_retrieval(query: str) -> List[Document]:
    """
    跨 Collection RAG 检索。
    """
    print(f"\nRAG在查询: '{query}'")
    all_retrievers = get_all_retrievers(top_k=TOP_K_PER_STORE)
    candidates = retrieve_candidates(query, all_retrievers, top_k=TOP_K_PER_STORE)
    reranked_docs = rerank_candidates(candidates, query, top_k=TOP_K_FINAL)

    if not reranked_docs:
        print("未找到相关文档，返回空列表。")
        return []

    print(f"\n最终候选（rerank 后）共 {len(reranked_docs)} 条:")
    for i, item in enumerate(reranked_docs, 1):
        doc = item["document"]
        score = item.get("score", 0)
        source = doc.metadata.get("source", "未知来源")
        collection = item.get("collection", "未知集合")
        content = (getattr(doc, "page_content", "") or "")[:200].replace("\n", " ").strip()
        print(f"📄 结果 #{i} | 相关性: {score:.4f} | 来源: {source} | 集合: {collection}")
        print(f"内容摘要: {content}...")

    return [item["document"] for item in reranked_docs]


if __name__ == '__main__':
    # 示例用法
    print("开始测试...")

    # 确保所有 Collection 都已加载
    _ = get_all_collections()

    # 模拟用户查询
    query = "I am foaming at the mouth; what disease is this?"

    # 执行多库 RAG 检索
    final_docs = multi_collection_rag_retrieval(query)

    print("\n---")
    print("检索完成。")