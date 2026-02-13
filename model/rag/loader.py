import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document


def clean_text(text: str) -> str:
    """
    医学 PDF 通用清洗
    """
    text = text.replace("\n", "")
    text = text.replace(" ", "")
    text = text.replace("，，", "，")
    text = text.replace("。。", "。")
    return text.strip()


def load_pdfs_from_dir(dir_path: str):
    """
    读取目录下所有 PDF 文件
    """
    documents = []

    for filename in os.listdir(dir_path):
        if not filename.lower().endswith(".pdf"):
            continue

        pdf_path = os.path.join(dir_path, filename)
        print(f"📄 加载 PDF: {filename}")

        loader = PyPDFLoader(pdf_path)
        pages = loader.load()

        for page in pages:
            cleaned = clean_text(page.page_content)
            if len(cleaned) < 50:
                continue

            documents.append(
                Document(
                    page_content=cleaned,
                    metadata={
                        "source": filename,
                        "page": page.metadata.get("page", -1)
                    }
                )
            )

    print(f"✅ 共加载 {len(documents)} 页医学文档")
    return documents
