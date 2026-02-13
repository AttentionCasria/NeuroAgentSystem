import os
from typing import List
from langchain_core.documents import Document
import dashscope
from http import HTTPStatus
import json


class BGEReranker:
    """
    【API版】使用阿里云 DashScope 的 GTE-Rerank 接口进行重排序
    注意：这不需要本地算力，不占内存。
    """

    def __init__(self, top_k: int = 5):
        # 1. 自动读取环境变量中的 DASHSCOPE_API_KEY
        self.api_key = os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            # 如果环境变量没配，也可以在这里硬编码 (不推荐)
            # self.api_key = "sk-你的key"
            print("⚠️ 警告: 未找到 DASHSCOPE_API_KEY，Rerank 可能无法使用")

        self.top_k = top_k
        # 使用阿里云的重排序模型 (效果对标 BGE)
        self.model = "gte-rerank"

    def rerank(self, query: str, docs: List[Document]) -> List[Document]:
        """
        保持函数签名不变，这样 retrieve.py 不需要改代码
        """
        if not docs:
            return []

        # 提取纯文本列表供 API 使用
        doc_contents = [doc.page_content for doc in docs]

        try:
            # 2. 调用阿里云 API
            resp = dashscope.TextReRank.call(
                model=self.model,
                query=query,
                documents=doc_contents,
                top_n=self.top_k,
                return_documents=True,
                api_key=self.api_key,
            )

            # 3. 处理返回结果
            if resp.status_code == HTTPStatus.OK:
                reranked_docs = []
                # API 返回的是排序后的索引 (index) 和相关度分数
                for item in resp.output.results:
                    # 根据索引找到原始文档
                    original_doc = docs[item.index]
                    # 把分数存进去（方便调试查看）
                    original_doc.metadata["relevance_score"] = item.relevance_score
                    reranked_docs.append(original_doc)

                print(
                    f"✅ API Rerank 完成，从 {len(docs)} 条精选出 {len(reranked_docs)} 条"
                )
                return reranked_docs
            else:
                print(f"❌ Rerank API 请求失败: {resp.code} - {resp.message}")
                # 如果接口挂了，降级为返回前 top_k 个原始文档
                return docs[: self.top_k]

        except Exception as e:
            print(f"❌ Rerank 发生异常: {e}")
            # 出错时保底返回
            return docs[: self.top_k]
