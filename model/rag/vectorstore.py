import os
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import DashScopeEmbeddings


def build_or_load_vectorstore(chunks, persist_dir="chroma_db_bge"):
    """
    构建或加载向量库。
    :param chunks: 文档切片列表 (如果库为空，会用这个填充)
    :param persist_dir: 向量库的存储路径 (修复了此处接受参数的问题)
    :return: Chroma 向量库对象
    """
    print(f"🔌 [VectorStore] 连接向量库位置: {persist_dir}")

    # 1. 初始化 Embedding 模型 (必须与存入时一致)
    import os
    if not os.getenv("DASHSCOPE_API_KEY"):
         # 提醒用户设置 KEY，实际上应该在外部设置
         pass

    # 使用阿里云的通用文本向量模型
    embeddings = DashScopeEmbeddings(
        model="text-embedding-v2",  # 这是一个非常强且便宜的中文向量模型
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

            # --- 增加批处理逻辑，防止单条失败导致整体写入失败 ---
            batch_size = 32 # 阿里 API 批量建议不要太大
            total_batches = (len(chunks) + batch_size - 1) // batch_size

            for i in range(0, len(chunks), batch_size):
                batch = chunks[i : i + batch_size]
                try:
                    vectordb.add_documents(documents=batch)
                    print(f"   ⏳ 正在写入批次 {i // batch_size + 1}/{total_batches} (含 {len(batch)} 条数据)...")
                except Exception as batch_e:
                    print(f"   ❌ 批次 {i // batch_size + 1} 写入失败: {batch_e}")
                    # 可选：如果批次失败，可以尝试逐条写入来挽救
                    print(f"   👉 尝试逐条写入该批次...")
                    for doc in batch:
                        try:
                            vectordb.add_documents(documents=[doc])
                        except Exception as single_e:
                            print(f"      ❌ 单条写入失败 (忽略): {str(single_e)[:100]}...")

            print("✅ 数据写入流程结束！")
        else:
            print(f"✅ 向量库加载成功 (当前包含 {count} 条数据)")

    except Exception as e:
        print(f"⚠️ 检查向量库状态时出现警告 (不影响运行): {e}")

    return vectordb
