import re

import pandas as pd
from tqdm import tqdm

from backend.tools.graph_rag.read_file import ingest_documents_to_df


def split_long_articles(chunks, max_chars=3000):
    """
    Hàm này duyệt qua các chunks. Nếu chunk nào dài hơn max_chars,
    nó sẽ cắt nhỏ dựa trên các "Khoản" (1., 2., 3.).
    """
    final_chunks = []

    # Regex bắt đầu bằng số, theo sau là dấu chấm và khoảng trắng (VD: "1. ", "2. ")
    khoan_pattern = re.compile(r"^\d+\.\s")

    for chunk in chunks:
        content = chunk["content"]

        # 1. NẾU ĐIỀU NÀY NGẮN: Giữ nguyên và đi tiếp
        if len(content) <= max_chars:
            final_chunks.append(chunk)
            continue

        # 2. NẾU ĐIỀU NÀY QUÁ DÀI: Tiến hành cắt nhỏ
        lines = content.split("\n")

        # Tạo ngữ cảnh gốc bắt buộc phải có ở đầu mỗi đoạn cắt
        # VD: "[Chương I - NHỮNG QUY ĐỊNH CHUNG]\nĐiều 2. Công nhận..."
        context_header = f"[{chunk['chuong']}]\n{chunk['dieu']}\n"

        current_sub_content = []
        current_length = len(context_header)
        part_number = 1

        for line in lines:
            line_stripped = line.strip()

            # Bỏ qua các dòng tiêu đề đã nằm trong context_header để tránh lặp chữ
            if (
                line_stripped == f"[{chunk['chuong']}]"
                or line_stripped == chunk["dieu"]
            ):
                continue

            line_len = len(line) + 1  # +1 cho ký tự xuống dòng (\n)

            # Kiểm tra xem dòng này có phải là bắt đầu một Khoản mới không
            is_new_khoan = khoan_pattern.match(line_stripped)

            # Quyết định cắt chunk khi:
            # - Gặp Khoản mới VÀ chunk hiện tại đã hòm hòm (ví dụ > 500 ký tự)
            # - HOẶC nhét thêm dòng này vào sẽ vượt quá giới hạn max_chars
            if (is_new_khoan and current_length > 500) or (
                current_length + line_len > max_chars
            ):
                if current_sub_content:
                    final_chunks.append(
                        {
                            "chuong": chunk["chuong"],
                            "dieu": f"{chunk['dieu']} (Phần {part_number})",
                            "content": context_header + "\n".join(current_sub_content),
                        }
                    )
                    part_number += 1
                    current_sub_content = []
                    current_length = len(context_header)

            current_sub_content.append(line)
            current_length += line_len

        # Đừng quên lưu phần còn sót lại cuối cùng
        if current_sub_content:
            final_chunks.append(
                {
                    "chuong": chunk["chuong"],
                    "dieu": f"{chunk['dieu']} (Phần {part_number})",
                    "content": context_header + "\n".join(current_sub_content),
                }
            )

    return final_chunks


def chunk_civil_code_markdown(md_text):
    chunks = []

    current_chuong = "Phần mở đầu"
    current_dieu = "Thông tin chung"
    current_content = []

    # Cờ (flag) để theo dõi việc ghép tên Chương bị rớt dòng
    cho_ten_chuong = False

    lines = md_text.split("\n")

    for line in lines:
        line_stripped = line.strip()

        # 1. BỎ QUA DÒNG TRỐNG VÀ RÁC (Header/Footer của PDF)
        if not line_stripped:
            continue

        # Bắt và bỏ qua các dòng chứa chữ "CÔNG BÁO/Số..."
        if "CÔNG BÁO/Số" in line_stripped:
            continue

        # 2. XỬ LÝ CHƯƠNG (Ghép số Chương và Tên Chương)
        if re.match(r"^\*\*Chương\s+[IVXLCDM]+\*\*", line_stripped, re.IGNORECASE):
            if current_content:
                chunks.append(
                    {
                        "chuong": current_chuong,
                        "dieu": current_dieu,
                        "content": "\n".join(current_content),
                    }
                )
            current_content = []
            current_dieu = ""

            current_chuong = line_stripped.replace("*", "")  # Xóa dấu sao
            cho_ten_chuong = True  # Bật cờ để lấy dòng tiếp theo làm tên chương
            continue

        if cho_ten_chuong:
            ten_chuong = line_stripped.replace("*", "")
            current_chuong = f"{current_chuong} - {ten_chuong}"
            cho_ten_chuong = False
            continue

        # 3. XỬ LÝ MỤC
        if re.match(r"^\*\*Mục\s+\d+\*\*", line_stripped, re.IGNORECASE):
            current_content.append(line_stripped.replace("*", ""))
            continue

        # ========================================================
        # 4. XỬ LÝ ĐIỀU (ĐÃ ĐƯỢC CẬP NHẬT REGEX)
        # Regex mới: ^[\s#\*]*Điều\s+\d+
        # Ý nghĩa: Bắt đầu dòng (^) có thể chứa các khoảng trắng, dấu #, hoặc dấu * ([\s#\*]*).
        # Sau đó bắt buộc là chữ "Điều", theo sau là khoảng trắng (\s+) và một con số (\d+)
        # ========================================================
        if re.match(r"^[\s#\*]*Điều\s+\d+", line_stripped, re.IGNORECASE):
            # Lưu chunk cũ lại
            if current_content:
                chunks.append(
                    {
                        "chuong": current_chuong,
                        "dieu": current_dieu,
                        "content": "\n".join(current_content),
                    }
                )

            # Khởi tạo chunk mới
            # Lệnh replace("*", "") và replace("#", "") sẽ dọn sạch mọi định dạng thừa
            clean_dieu = line_stripped.replace("*", "").replace("#", "").strip()
            current_dieu = clean_dieu
            current_content = [clean_dieu]

        # 5. XỬ LÝ NỘI DUNG BÌNH THƯỜNG
        else:
            clean_text = line_stripped.replace("*", "")
            current_content.append(clean_text)

    # Lưu chunk cuối cùng
    if current_content:
        chunks.append(
            {
                "chuong": current_chuong,
                "dieu": current_dieu,
                "content": "\n".join(current_content),
            }
        )

    return chunks


def get_law_texts():
    scorpus_dir = "dataset/scorpus"
    df_documents = ingest_documents_to_df(scorpus_dir)

    # Hiển thị kết quả
    print(f"Đã nạp {len(df_documents)} tài liệu.")
    return df_documents


if __name__ == "__main__":
    law_texts_df = get_law_texts()
    print(f"law_texts_df: {law_texts_df}")

    law_texts_df["chunk"] = law_texts_df["content"].apply(chunk_civil_code_markdown)
    print(f"law_texts_df: {law_texts_df}")
    # law_text = law_texts_df["content"][0]
    # print(f"law_text: {law_text}")
    # df_chunks = chunk_civil_code_markdown(law_text)
    # print(f"df_chunks: {df_chunks}")
