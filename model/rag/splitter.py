from langchain.text_splitter import RecursiveCharacterTextSplitter


def split_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=512,  # 稍微增大一点，适配 embedding-v2 的能力 (最高2048，保守设 512)
        chunk_overlap=128,
        # ⚠️ 关键修正：必须包含 "" (空字符串) 作为最后的 fallback
        # 否则遇到超长且无标点的文本(如表格转文字)，splitter 无法切割，导致超过 API 限制报错
        separators=["\n\n", "。", "；", "\n", " ", ""]
    )
    return splitter.split_documents(documents)
