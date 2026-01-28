from chromadb import PersistentClient
import os

# ===== 配置 =====
OLD_DB_ROOT = "D:/pycharmProject/MedicalRAG/chroma_db"        # 旧的根目录
NEW_DB_DIR = "D:/pycharmProject/MedicalRAG/chroma_db_unified" # 新的统一库目录
BATCH_SIZE = 2000  # 每次写入的最大条数，避免超过 ChromaDB 限制


def migrate_all_collections():
    # 创建新库客户端
    os.makedirs(NEW_DB_DIR, exist_ok=True)
    new_client = PersistentClient(path=NEW_DB_DIR)

    print("🚀 开始迁移旧的 Chroma 库到统一库")
    print(f"旧库路径: {OLD_DB_ROOT}")
    print(f"新库路径: {NEW_DB_DIR}\n")

    # 遍历旧库下的所有子目录
    for name in os.listdir(OLD_DB_ROOT):
        subdir = os.path.join(OLD_DB_ROOT, name)
        if not os.path.isdir(subdir):
            continue

        sqlite_path = os.path.join(subdir, "chroma.sqlite3")
        if not os.path.exists(sqlite_path):
            continue

        print(f"🔎 检查旧 Collection: {name}")

        # 连接旧子库
        old_client = PersistentClient(path=subdir)
        old_collections = old_client.list_collections()
        if not old_collections:
            print(f"  ⚠️ {name} 没有找到任何 Collection，跳过。\n")
            continue

        # 一般只有一个 Collection
        old_col = old_collections[0]
        old_collection = old_client.get_collection(old_col.name)

        # 读取旧数据
        results = old_collection.get(include=["documents", "embeddings", "metadatas"])
        documents = results.get("documents", [])
        embeddings = results.get("embeddings", [])
        metadatas = results.get("metadatas", [])
        ids = results.get("ids", [])

        print(f"  -> 文档数: {len(documents)}")

        if not documents:
            print("  ⚠️ 没有数据，跳过。\n")
            continue

        # 在新库创建同名 Collection
        new_collection = new_client.get_or_create_collection(name=name)

        # 分批写入
        total = len(documents)
        for i in range(0, total, BATCH_SIZE):
            new_collection.add(
                documents=documents[i:i+BATCH_SIZE],
                embeddings=embeddings[i:i+BATCH_SIZE],
                metadatas=metadatas[i:i+BATCH_SIZE],
                ids=ids[i:i+BATCH_SIZE],
            )
            print(f"    ✅ 批次 {i//BATCH_SIZE+1}: 已迁移 {min(i+BATCH_SIZE, total)}/{total}")

        print(f"  🎯 完成迁移 {total} 条数据到 unified/{name}\n")

    print("🎉 所有迁移完成！")
    print(f"统一后的数据库路径: {NEW_DB_DIR}")


if __name__ == "__main__":
    migrate_all_collections()
