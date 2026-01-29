from langchain.text_splitter import RecursiveCharacterTextSplitter


def split_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=100,
        separators=["\n\n", "。", "；", "\n"]
    )
    return splitter.split_documents(documents)
