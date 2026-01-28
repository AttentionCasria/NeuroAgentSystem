import os
from pathlib import Path
import pdfplumber
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

# ===== 基本配置 =====
BASE_DIR = Path(r"D:\pycharmProject\MedicalRAG\Data\documents")  # 根目录
VECTOR_STORE_PATH = r"D:\pycharmProject\MedicalRAG\chroma_db_unified"  # 向量库存储路径
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def extract_text_from_pdf(pdf_path: Path) -> str:
    """提取PDF文本"""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text += page_text
    except Exception as e:
        print(f"⚠️ 无法读取 {pdf_path.name}: {e}")
    return text.strip()


def collect_pdfs(base_dir: Path):
    """递归收集所有PDF文件路径"""
    return [p for p in base_dir.rglob("*.pdf")]


def build_vector_store():
    """主流程：提取→分块→向量化→持久化"""
    pdf_files = collect_pdfs(BASE_DIR)
    if not pdf_files:
        print(f"❌ 未在 {BASE_DIR} 中找到任何PDF文件。")
        return

    print(f"📚 共发现 {len(pdf_files)} 个PDF文件，开始处理...\n")
    docs = []

    for pdf_path in pdf_files:
        text = extract_text_from_pdf(pdf_path)
        if not text:
            continue
        docs.append({
            "page_content": text,
            "metadata": {"source": str(pdf_path)}
        })
        print(f"✅ 提取完成: {pdf_path.name} ({len(text)} 字符)")

    if not docs:
        print("❌ 所有PDF文本提取均为空，终止。")
        return

    print("\n✂️ 正在分块...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?"]
    )

    # 注意：split_documents 需要 LangChain Document 格式
    from langchain.schema import Document
    doc_objs = [Document(page_content=d["page_content"], metadata=d["metadata"]) for d in docs]
    chunks = splitter.split_documents(doc_objs)
    print(f"📎 共生成 {len(chunks)} 个文本块。")

    print("\n🔢 正在生成向量并保存...")
    embeddings = OpenAIEmbeddings()
    vector_store = Chroma.from_documents(chunks, embedding=embeddings, persist_directory=VECTOR_STORE_PATH)

    print(f"🎉 向量库构建完成，已保存至: {VECTOR_STORE_PATH}")


if __name__ == "__main__":
    build_vector_store()
