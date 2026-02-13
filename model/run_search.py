from rag.loader import load_pdfs_from_dir
from rag.splitter import split_documents
from rag.vectorstore import build_or_load_vectorstore
from rag.retriever import HybridRetriever


def main():
    docs_dir = r"D:\pycharmProject\MedLLM\Data\documents"

    # 1. 加载所有 PDF
    docs = load_pdfs_from_dir(docs_dir)

    # 2. 切分
    chunks = split_documents(docs)
    print(f"✂️ 切分得到 {len(chunks)} 个 chunk")

    # 3. 向量库
    vectordb = build_or_load_vectorstore(chunks)

    # 4. Hybrid Retriever
    retriever = HybridRetriever(vectordb, chunks, k=5)

    # 5. 查询
    query = "脑梗死出血转化的处理原则是什么？"
    results = retriever.get_relevant_documents(query)

    for i, doc in enumerate(results, 1):
        print(f"\n[{i}] ({doc.metadata['source']} - p{doc.metadata['page']})")
        print(doc.page_content[:300])


if __name__ == "__main__":
    main()
