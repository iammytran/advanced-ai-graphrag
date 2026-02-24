
import os
import pandas as pd
import tiktoken
import nltk
import asyncio
import json
from google import genai

from typing import List, Optional, Any, Callable, Tuple
import uuid

from dotenv import load_dotenv

# 1. Nạp các biến từ tệp .env
load_dotenv()

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
    nltk.download('punkt_tab')


def chunk(text: str,
          encoding_name: str = "cl100k_base",
          chunk_size: int = 1200,
          chunk_overlap: int = 100,
) -> pd.DataFrame :
    encoding = tiktoken.get_encoding(encoding_name)
    # Bước 1: Chia văn bản thành các câu để tránh việc cắt giữa chừng một câu
    sentences = nltk.sent_tokenize(text)

    print(f"sentences: {sentences}")
    
    chunks = []
    current_chunk_sentences = []
    current_tokens = 0
    
    for sentence in sentences:
        sentence_tokens = len(encoding.encode(sentence))
        print(f"cho câu {sentence}, ta có {sentence_tokens} tokens")
        
        # Nếu một câu đơn lẻ dài hơn chunk_size, ta buộc phải cắt theo token
        if sentence_tokens > chunk_size:
            print(f"câu dài hơn chunk_size")
            # Xử lý trường hợp câu quá dài
            if current_chunk_sentences:
                print(f"current_chunk_sentences: {current_chunk_sentences}")
                chunks.append(" ".join(current_chunk_sentences))
                print(f"chunks: {chunks}")
                current_chunk_sentences = []
                current_tokens = 0
            
            # Cắt nhỏ câu quá dài này theo token
            tokens = encoding.encode(sentence)
            for i in range(0, len(tokens), chunk_size - chunk_overlap):
                chunk_tokens = tokens[i : i + chunk_size]
                chunks.append(encoding.decode(chunk_tokens))
            continue

        # Nếu thêm câu này vào mà vượt quá giới hạn, đóng chunk hiện tại
        if current_tokens + sentence_tokens > chunk_size:
            print(f"cộng thêm câu hiện tại vào rổ token mà lớn hơn chunK_size")
            chunks.append(" ".join(current_chunk_sentences))
            
            # Giữ lại một số câu cuối để tạo overlap (tùy chọn đơn giản hóa)
            # Ở đây ta bắt đầu chunk mới
            current_chunk_sentences = [sentence]
            current_tokens = sentence_tokens
        else:
            current_chunk_sentences.append(sentence)
            current_tokens += sentence_tokens

    # Thêm đoạn cuối cùng
    if current_chunk_sentences:
        chunks.append(" ".join(current_chunk_sentences))

    # Chuyển thành định dạng DataFrame giống output của GraphRAG
    output_data = []
    for i, chunk_text in enumerate(chunks):
        output_data.append({
            "id": str(uuid.uuid4()),
            "text": chunk_text,
            "n_tokens": len(encoding.encode(chunk_text))
        })
        
    return pd.DataFrame(output_data)

async def extract_graph(text_units: pd.DataFrame,
    text_column: str,
    id_column: str,
    model_name: str = "gemini-1.5-flash", # Hoặc gemini-1.5-pro
    prompt_template: str = "",
    entity_types: List[str] = ["person", "organization", "location"],
    num_threads: int = 2, # Gemini free tier có giới hạn request/phút thấp, nên để thấp
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    
    # # Khởi tạo model
    # model = genai.GenerativeModel(
    #     model_name=model_name,
    #     generation_config={"response_mime_type": "application/json"}
    # )

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    async def call_gemini(text: str):
        # CHÚ Ý: Dùng .aio để gọi bản bất đồng bộ
        response = await client.aio.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"Extract entities and relationships from: {text}",
            config={
                "response_mime_type": "application/json"
            }
        )
        return response.text

    async def process_row(row):
        text = str(row[text_column]).strip()
        source_id = str(row[id_column])
        try:
            content = await call_gemini(text)
            data = json.loads(content)
            
            entities_list = []
            for e in data.get("entities", []):
                entities_list.append({
                    "title": e.get("name"),
                    "type": e.get("type"),
                    "description": e.get("description"),
                    "source_id": source_id
                })
            
            rels_list = []
            for r in data.get("relationships", []):
                rels_list.append({
                    "source": r.get("source"),
                    "target": r.get("target"),
                    "description": r.get("description"),
                    "weight": r.get("weight", 1),
                    "source_id": source_id
                })
            return pd.DataFrame(entities_list), pd.DataFrame(rels_list)
        except Exception as e:
            print(f"Error at row {source_id}: {e}")
            return pd.DataFrame(), pd.DataFrame()

    # Quản lý luồng bằng Semaphore (Giới hạn số request đồng thời)
    semaphore = asyncio.Semaphore(num_threads)

    async def sem_process(row):
        async with semaphore:
            return await process_row(row)

    tasks = [sem_process(row) for _, row in text_units.iterrows()]
    results = await asyncio.gather(*tasks)

    # Gom kết quả
    entity_dfs = [r[0] for r in results if not r[0].empty]
    relationship_dfs = [r[1] for r in results if not r[1].empty]

    if not entity_dfs: return pd.DataFrame(), pd.DataFrame()

    # Hợp nhất Entities (Merge logic)
    entities = pd.concat(entity_dfs, ignore_index=True)
    entities = entities.groupby(["title", "type"], sort=False).agg({
        "description": lambda x: list(set(x)),
        "source_id": [list, "count"]
    })
    entities.columns = ["description", "text_unit_ids", "frequency"]
    entities = entities.reset_index()

    # Hợp nhất Relationships
    relationships = pd.concat(relationship_dfs, ignore_index=True)
    relationships = relationships.groupby(["source", "target"], sort=False).agg({
        "description": list,
        "source_id": list,
        "weight": "sum"
    }).reset_index()
    relationships.rename(columns={"source_id": "text_unit_ids"}, inplace=True)

    return entities, relationships

# Ví dụ cách chạy indexing
async def main():
    # # Đảm bảo bạn đã tạo file .env ở thư mục backend và có biến GRAPHRAG_API_KEY
    # api_key = os.getenv("GRAPHRAG_API_KEY")
    # if not api_key:
    #     print("Vui lòng tạo file .env trong thư mục backend và cung cấp GRAPHRAG_API_KEY.")
    # else:
    #     print("Bắt đầu quá trình indexing của GraphRAG...")
    #     result = indexing()
    #     print(result)

    try:
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('tokenizers/punkt_tab')
    except LookupError:
        nltk.download('punkt')
        nltk.download('punkt_tab')
    print("setup okay!")

    raw_text = """Nikola Tesla là một nhà phát minh người Mỹ gốc Serbia. 
    Ông nổi tiếng với những đóng góp cho việc thiết kế hệ thống điện xoay chiều (AC) hiện đại. 
    Hệ thống này đã trở thành tiêu chuẩn cho việc truyền tải điện năng trên toàn thế giới."""
    
    df_chunks = chunk(raw_text, chunk_size=20, chunk_overlap=5)
    print(df_chunks)

    # Gọi hàm trích xuất (Sử dụng hàm standalone mà chúng ta đã thảo luận)
    entities, relationships = await extract_graph(
        text_units=df_chunks,
        text_column="text",
        id_column="id",
        model_name="gemini-1.5-flash",
        prompt_template="Extract entities and relationships...",
        entity_types=["person", "organization"]
    )
    
    print(entities)

if __name__ == '__main__':
    asyncio.run(main())
