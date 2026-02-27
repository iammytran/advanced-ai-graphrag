from pathlib import Path

import pandas as pd
from markitdown import MarkItDown


def read_pdf(file_path):
    """Đọc văn bản từ file PDF."""
    import pymupdf4llm

    text = pymupdf4llm.to_markdown(file_path)
    return text


def read_docx(file_path):
    """Đọc văn bản từ file DOCX."""
    from markitdown import MarkItDown

    md = MarkItDown()
    result = md.convert(file_path)
    return result.text_content


def ingest_documents_to_df(folder_path: str) -> pd.DataFrame:
    """
    Quét folder và lưu file_name, content vào DataFrame.
    """
    data = []
    folder = Path(folder_path)

    # Duyệt qua tất cả các file trong folder
    for file_path in folder.iterdir():
        if file_path.is_file():
            suffix = file_path.suffix.lower()
            content = ""

            try:
                if suffix == ".pdf":
                    content = read_pdf(file_path)
                elif suffix == ".docx":
                    content = read_docx(file_path)
                elif suffix in [".txt", ".md"]:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                else:
                    continue  # Bỏ qua các file không hỗ trợ

                if content.strip():
                    data.append({"file_name": file_path.name, "content": content})
            except Exception as e:
                print(f"Lỗi khi xử lý file {file_path.name}: {e}")

    # Tạo DataFrame
    df = pd.DataFrame(data)
    return df
