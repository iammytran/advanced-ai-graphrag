from pathlib import Path

BASE_DIR = Path(__file__).parent
CHROMA_DB_PATH = str(BASE_DIR.parent / "chroma")

import sys

sys.path.append(str(BASE_DIR.parent))

from langchain.tools import tool
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.config.config import EMBEDDING_MODEL

embeddings = OpenAIEmbeddings(
    base_url="https://openrouter.ai/api/v1",
    model=EMBEDDING_MODEL,
)


def indexing():
    pdf_path = str(
        BASE_DIR.parent.parent.joinpath("dataset", "pdf", "100_2015_QH13_296661.pdf")
    )
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
    )
    chunks = text_splitter.split_documents(documents)

    vector_db = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_DB_PATH,
        collection_name="docs",
    )


@tool
def rag_retrieval(query: str) -> str:
    """
    CHỈ SỬ DỤNG công cụ này khi người dùng hỏi về:
    - Các quy định pháp luật, điều luật.
    - Mức xử phạt vi phạm hành chính (ví dụ: đánh bài phạt bao nhiêu, vượt đèn đỏ...).
    - Các thông tin cần trích dẫn chính xác từ văn bản luật pháp.

    KHÔNG SỬ DỤNG công cụ này nếu:
    - Người dùng chỉ đang chào hỏi (Xin chào, bạn là ai...).
    - Người dùng yêu cầu tóm tắt lại câu trả lời trước đó.
    """
    vector_db = Chroma(
        persist_directory=CHROMA_DB_PATH,
        collection_name="docs",
        embedding_function=embeddings,
    )

    retriever = vector_db.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": 5,  # Số lượng chunk cuối cùng trả về cho LLM
            "fetch_k": 20,  # Số lượng chunk lấy ra ban đầu để lọc MMR
            "lambda_mult": 0.5,  # Cân bằng giữa độ tương đồng (1.0) và độ đa dạng (0.0)
        },
    )

    print(f"\n[Tool Execution] Đang tìm kiếm thông tin cho: '{query}'...")

    retrieved_docs = retriever.invoke(query)

    formatted_context = ""
    for i, doc in enumerate(retrieved_docs):
        formatted_context += f"--- Tài liệu {i+1} ---\n{doc.page_content}\n\n"

    if not retrieved_docs:
        return "Không tìm thấy thông tin tài chính nào liên quan đến câu hỏi trong cơ sở dữ liệu."

    print(formatted_context)
    return formatted_context


if __name__ == "__main__":
    indexing()
    print(rag_retrieval.invoke({"query": "đánh bài phạt bao nhiêu tiền?"}))
    pass
