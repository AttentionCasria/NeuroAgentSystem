import os
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings


def build_or_load_vectorstore(chunks, persist_dir="chroma_db_bge"):
    """
    构建或加载向量库。
    :param chunks: 文档切片列表 (如果库为空，会用这个填充)
    :param persist_dir: 向量库的存储路径 (修复了此处接受参数的问题)
    :return: Chroma 向量库对象
    """
    print(f"🔌 [VectorStore] 连接向量库位置: {persist_dir}")

    # 1. 初始化 Embedding 模型 (必须与存入时一致)
    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-large-zh-v1.5",
        encode_kwargs={"normalize_embeddings": True}
    )

    # 2. 初始化 Chroma
    # persist_directory 参数决定了数据存在硬盘的哪个文件夹
    vectordb = Chroma(persist_directory=str(persist_dir), embedding_function=embeddings)

    # 3. 智能判断：如果是空库，才执行写入
    # 这样避免了每次重启都重复写入数据，导致数据重复或启动慢
    # Chroma 的 _collection.count() 可以快速获取数量
    try:
        count = vectordb._collection.count()
        if count == 0 and chunks:
            print(f"⚠️ 检测到向量库为空，正在写入 {len(chunks)} 条数据...")
            vectordb.add_documents(documents=chunks)
            print("✅ 数据写入完成！")
        else:
            print(f"✅ 向量库加载成功 (当前包含 {count} 条数据)")

    except Exception as e:
        print(f"⚠️ 检查向量库状态时出现警告 (不影响运行): {e}")

    return vectordb
