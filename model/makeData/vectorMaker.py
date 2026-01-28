import os
import pdfplumber
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
# 【修改点1】使用最新版 Chroma 库
from langchain_chroma import Chroma
from langchain.schema import Document

# 【修改点2】使用相对路径，自动定位到当前项目的 Data/documents
# 获取当前脚本所在目录 (makeData)
CURRENT_DIR = Path(__file__).resolve().parent
# 获取项目根目录 (MedLLM)
PROJECT_ROOT = CURRENT_DIR.parent

# 设定数据源目录和向量库存储目录
BASE_DIR = PROJECT_ROOT / "Data" / "documents"
VECTOR_STORE_PATH = PROJECT_ROOT / "chroma_db_unified"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def extract_text_from_pdf(pdf_path: Path) -> str:
    """提取PDF文本"""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text
    except Exception as e:
        print(f"⚠️ 无法读取 {pdf_path.name}: {e}")
    return text.strip()


def collect_pdfs(base_dir: Path):
    """递归收集所有PDF文件路径"""
    if not base_dir.exists():
        print(f"❌ 目录不存在: {base_dir}")
        return []
    return list(base_dir.rglob("*.pdf"))


def build_vector_store():
    """主流程：提取→分块→向量化→持久化"""
    print(f"📂 数据目录: {BASE_DIR}")
    print(f"💾 存储目录: {VECTOR_STORE_PATH}")

    pdf_files = collect_pdfs(BASE_DIR)
    if not pdf_files:
        print(f"❌ 未在 {BASE_DIR} 中找到任何 PDF 文件。")
        return

    print(f"📚 共发现 {len(pdf_files)} 个 PDF 文件，开始处理...\n")
    docs = []

    for pdf_path in pdf_files:
        print(f"正在读取: {pdf_path.name} ...", end="", flush=True)
        text = extract_text_from_pdf(pdf_path)
        if not text:
            print(" [空内容，跳过]")
            continue

        docs.append(Document(
            page_content=text,
            metadata={"source": str(pdf_path.name)}  # 只保留文件名，路径变动不影响引用
        ))
        print(f" [完成] ({len(text)} 字符)")

    if not docs:
        print("❌ 所有 PDF 文本提取均为空，终止。")
        return

    print("\n✂️ 正在分块...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?"]
    )
    chunks = splitter.split_documents(docs)
    print(f"📎 共生成 {len(chunks)} 个文本块。")

    print("\n🔢 正在生成向量并保存 (这需要一些时间)...")

    # ⚠️ 注意：这里使用的是 OpenAI 的 Embedding。
    # 如果你没有设置 OPENAI_API_KEY 环境变量，这里会报错。
    # 确保你的 .env 或系统变量里有 OPENAI_API_KEY。
    embeddings = OpenAIEmbeddings()

    # 构建并保存到磁盘
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(VECTOR_STORE_PATH)
    )

    print(f"🎉 向量库构建完成！已保存至: {VECTOR_STORE_PATH}")


if __name__ == "__main__":
    build_vector_store()

# import os
# from pathlib import Path
# import pdfplumber
# from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain_openai import OpenAIEmbeddings
# from langchain_community.vectorstores import Chroma
#
# # ===== 基本配置 =====
# BASE_DIR = Path(r"D:\pycharmProject\MedicalRAG\Data\documents")  # 根目录
# VECTOR_STORE_PATH = r"D:\pycharmProject\MedicalRAG\chroma_db"  # 向量库存储路径
# CHUNK_SIZE = 1000
# CHUNK_OVERLAP = 200
#
#
# def extract_text_from_pdf(pdf_path: Path) -> str:
#     """提取PDF文本"""
#     text = ""
#     try:
#         with pdfplumber.open(pdf_path) as pdf:
#             for page in pdf.pages:
#                 page_text = page.extract_text() or ""
#                 text += page_text
#     except Exception as e:
#         print(f"⚠️ 无法读取 {pdf_path.name}: {e}")
#     return text.strip()
#
#
# def collect_pdfs(base_dir: Path):
#     """递归收集所有PDF文件路径"""
#     return [p for p in base_dir.rglob("*.pdf")]
#
#
# def build_vector_store():
#     """主流程：提取→分块→向量化→持久化"""
#     pdf_files = collect_pdfs(BASE_DIR)
#     if not pdf_files:
#         print(f"❌ 未在 {BASE_DIR} 中找到任何PDF文件。")
#         return
#
#     print(f"📚 共发现 {len(pdf_files)} 个PDF文件，开始处理...\n")
#     docs = []
#
#     for pdf_path in pdf_files:
#         text = extract_text_from_pdf(pdf_path)
#         if not text:
#             continue
#         docs.append({
#             "page_content": text,
#             "metadata": {"source": str(pdf_path)}
#         })
#         print(f"✅ 提取完成: {pdf_path.name} ({len(text)} 字符)")
#
#     if not docs:
#         print("❌ 所有PDF文本提取均为空，终止。")
#         return
#
#     print("\n✂️ 正在分块...")
#     splitter = RecursiveCharacterTextSplitter(
#         chunk_size=CHUNK_SIZE,
#         chunk_overlap=CHUNK_OVERLAP,
#         separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?"]
#     )
#
#     # 注意：split_documents 需要 LangChain Document 格式
#     from langchain.schema import Document
#     doc_objs = [Document(page_content=d["page_content"], metadata=d["metadata"]) for d in docs]
#     chunks = splitter.split_documents(doc_objs)
#     print(f"📎 共生成 {len(chunks)} 个文本块。")
#
#     print("\n🔢 正在生成向量并保存...")
#     embeddings = OpenAIEmbeddings()
#     vector_store = Chroma.from_documents(chunks, embedding=embeddings, persist_directory=VECTOR_STORE_PATH)
#
#     print(f"🎉 向量库构建完成，已保存至: {VECTOR_STORE_PATH}")
#
#
# if __name__ == "__main__":
#     build_vector_store()
