"""Interactive CLI for the RAG Chatbot"""

import sys
from pathlib import Path

# Add the project root to the path
sys.path.append(str(Path(__file__).parent / "backend"))

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.src.vector_db import VectorDBManager


def load_initial_documents():
    """Load initial documents if vector store is empty"""
    pdf_dir = "dataset/pdf"
    documents = []
    loader = PyPDFLoader("./dataset/pdf/100_2015_QH13_296661.pdf")
    documents = loader.load()

    # if os.path.exists(pdf_dir):
    #     print(f"Loading PDFs from {pdf_dir}...")
    #     for filename in os.listdir(pdf_dir):
    #         if filename.endswith(".pdf"):
    #             file_path = os.path.join(pdf_dir, filename)
    #             print(f"  - Loading {filename}...")
    #             try:
    #                 loader = PyPDFLoader(file_path)
    #                 documents.extend(loader.load())
    #             except Exception as e:
    #                 print(f"Error loading {filename}: {e}")
    # else:
    #     print(f"Directory {pdf_dir} not found.")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

    if documents:
        splits = text_splitter.split_documents(documents)
        print(f"Số chunk sau khi chia: {len(splits)}")

        # Add documents to vector store
        db = VectorDBManager()
        db.add_documents(splits)

        print(f"✓ Loaded {len(documents)} documents ({len(splits)} chunks)")
    else:
        print("No documents loaded.")
        db = VectorDBManager()

    return db


def main():
    db = load_initial_documents()
    info = db.get_store_info()
    print(f"\n📚 Vector Store Status: {info['document_count']} documents loaded")


if __name__ == "__main__":
    main()
