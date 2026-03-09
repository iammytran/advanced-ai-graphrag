
import os
import pandas as pd
import tiktoken
import nltk
import asyncio
import json
from google import genai
from openai import AsyncOpenAI
import networkx as nx
import matplotlib.pyplot as plt
import fitz  # PyMuPDF
from pathlib import Path
from pypdf import PdfReader
from glob import glob
from docx import Document
import re
from tqdm import tqdm
import pickle
import graspologic_native as gn
import html
from collections import defaultdict
from typing import List, Optional, Any, Callable, Tuple
# from graspologic.partition import hierarchical_leiden
import uuid
from dotenv import load_dotenv
from unsloth import FastLanguageModel
import torch
import logging
import transformers
from datetime import datetime
from langchain.tools import tool
from langchain_chroma import Chroma
from datetime import datetime

from backend.tools.graph_rag.compute_leiden_communities import _compute_leiden_communities
from backend.tools.graph_rag.generate_community_summary import generate_hierarchical_community_reports_unsloth
from backend.tools.graph_rag.generate_community_summary import save_full_graph_context

# 1. Nạp các biến từ tệp .env
load_dotenv()

# 1. Tắt log của transformers để tránh cái warning gây crash kia
transformers.logging.set_verbosity_error()

# 2. Hoặc cấu hình lại logger cơ bản để bỏ qua các tham số thừa
logging.basicConfig(level=logging.ERROR)

Communities = list[tuple[int, int, int, list[str]]]

# Định nghĩa danh sách các loại thực thể phù hợp với Luật
ENTITY_TYPES = "VĂN BẢN QUY PHẠM, ĐIỀU KHOẢN, HÀNH VI CẤM, NGHĨA VỤ, QUYỀN HẠN, ĐỐI TƯỢNG ÁP DỤNG"

GRAPH_PROMPT = f"""
-MỤC TIÊU-
Bạn là một chuyên gia phân tích hệ thống pháp luật. Nhiệm vụ của bạn là trích xuất một Đồ thị tri thức (Knowledge Graph) cực kỳ chi tiết từ văn bản luật được cung cấp. 
KHÔNG ĐƯỢC tóm tắt chung chung. Hãy trích xuất đến cấp độ chi tiết nhất (từng Điều, từng Khoản).

-CÁC BƯỚC THỰC HIỆN-

1. XÁC ĐỊNH THỰC THỂ (ENTITIES):
Duyệt qua văn bản và trích xuất:
- entity_name: Tên thực thể, viết hoa toàn bộ. 
  QUY TẮC QUAN TRỌNG: Đối với các ĐIỀU, KHOẢN, MỤC, chương, phải đính kèm mã hiệu văn bản trong ngoặc đơn.
  Định dạng: "ĐIỀU [Số] ({{doc_name_context}})" hoặc "KHOẢN [Số] ĐIỀU [Số] ({{doc_name_context}})".
  Định dạng: "ĐIỀU [Số] ([Mã hiệu văn bản])"
  Ví dụ: Nếu nguồn là 'Thông tư 01/2020', thực thể phải là "ĐIỀU 1 (TT 01/2020)".
- entity_type: Chọn một trong: [{ENTITY_TYPES}]
- entity_description: Mô tả chi tiết nội dung quy định hoặc chức năng của thực thể đó trong ngữ cảnh văn bản.

Định dạng: ("entity"<|><entity_name><|><entity_type><|><entity_description>)

2. XÁC ĐỊNH MỐI QUAN HỆ (RELATIONSHIPS):
Xác định tất cả các cặp thực thể có liên quan logic. Đặc biệt chú trọng:
- Quan hệ Phân cấp: (KHOẢN 1) thuộc (ĐIỀU 11).
- Quan hệ Trách nhiệm: (CỤC CẢNH SÁT) có trách nhiệm (THEO DÕI VIỆC THI HÀNH).
- Quan hệ Căn cứ: (THÔNG TƯ X) căn cứ vào (LUẬT Y).
- Quan hệ Đối tượng: (ĐIỀU 12) áp dụng cho (CÔNG AN TỈNH).

Định dạng: ("relationship"<|><source_entity><|><target_entity><|><description><|><strength>)
(Strength: thang điểm 1-10 dựa trên độ rõ ràng của mối quan hệ).

3. ĐỊNH DẠNG ĐẦU RA:
- Trả về danh sách duy nhất, các phần tử cách nhau bởi dấu ##.
- Ngôn ngữ: TIẾNG VIỆT hoàn toàn.
- Kết thúc bằng: <|COMPLETE|>

-VÍ DỤ MẪU-
("entity"<|>ĐIỀU 12<|>ĐIỀU KHOẢN<|>Quy định về trách nhiệm thi hành của các đơn vị trực thuộc Bộ)
##
("entity"<|>CỤC CẢNH SÁT QUẢN LÝ TẠM GIỮ<|>CƠ QUAN PHÁP LUẬT<|>Đơn vị chịu trách nhiệm theo dõi, hướng dẫn việc thực hiện thông tư)
##
("relationship"<|>CỤC CẢNH SÁT QUẢN LÝ TẠM GIỮ<|>ĐIỀU 12<|>Cục Cảnh sát quản lý tạm giữ chịu trách nhiệm thực hiện nội dung tại Điều 12<|>9)
<|COMPLETE|>
"""

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
    nltk.download('punkt_tab')

def read_pdf(file_path):
    """Đọc văn bản từ file PDF."""
    text = ""
    with fitz.open(file_path) as doc:
        for page in doc:
            text += page.get_text()
    return text

def read_docx(file_path):
    """Đọc văn bản từ file DOCX."""
    doc = Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])

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
                if suffix == '.pdf':
                    content = read_pdf(file_path)
                elif suffix == '.docx':
                    content = read_docx(file_path)
                elif suffix in ['.txt', '.md']:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                else:
                    continue # Bỏ qua các file không hỗ trợ
                
                if content.strip():
                    data.append({
                        "file_name": file_path.name,
                        "content": content
                    })
            except Exception as e:
                print(f"Lỗi khi xử lý file {file_path.name}: {e}")

    # Tạo DataFrame
    df = pd.DataFrame(data)
    return df

def get_law_texts():
    scorpus_dir = 'dataset/scorpus'
    df_documents = ingest_documents_to_df(scorpus_dir)

    # Hiển thị kết quả
    print(f"Đã nạp {len(df_documents)} tài liệu.")
    return df_documents

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

def vietnamese_legal_chunk(
    legal_df: pd.DataFrame,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
    encoding_name: str = "cl100k_base"
) -> pd.DataFrame:
    encoding = tiktoken.get_encoding(encoding_name)

    text = legal_df['content']
    file_name = legal_df['file_name']
    
    # 1. Tiền xử lý: Chuẩn hóa xuống dòng để tránh các dòng trống vô nghĩa
    text = re.sub(r'\n\s*\n', '\n', text)
    
    # 2. Thay vì dùng nltk, ta dùng Regex để tách theo các dấu hiệu phân đoạn luật
    # Tách theo dấu chấm câu hoặc các tiêu đề "Điều ...", "Chương ..."
    paragraphs = re.split(r'(?<=[.!?])\s+(?=[A-ZÀÁẢÃẠÈÉẺẼẸÌÍỈĨỊÒÓỎÕỌÙÚỦŨỤ])|(?=\nĐiều )', text)
    
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        # Kiểm tra độ dài token của đoạn hiện tại + đoạn mới
        combined_text = (current_chunk + " " + para).strip()
        tokens_count = len(encoding.encode(combined_text))
        
        if tokens_count <= chunk_size:
            current_chunk = combined_text
        else:
            # Lưu chunk hiện tại
            if current_chunk:
                chunks.append(current_chunk)
            
            # Xử lý overlap: Lấy một phần cuối của chunk cũ nối vào chunk mới
            # (Đơn giản hóa: lấy 200 ký tự cuối để giữ ngữ cảnh)
            overlap_text = current_chunk[-chunk_overlap:] if len(current_chunk) > chunk_overlap else ""
            current_chunk = (overlap_text + " " + para).strip()
            
            # Nếu bản thân paragraph đó vẫn quá dài sau khi thêm overlap
            if len(encoding.encode(current_chunk)) > chunk_size:
                # Buộc phải cắt cứng theo token
                tokens = encoding.encode(current_chunk)
                for i in range(0, len(tokens), chunk_size - chunk_overlap):
                    chunk_tokens = tokens[i : i + chunk_size]
                    chunks.append(encoding.decode(chunk_tokens))
                current_chunk = ""

    # Thêm đoạn cuối cùng
    if current_chunk:
        chunks.append(current_chunk)

    # Đóng gói vào DataFrame
    output_data = [{
        "id": str(uuid.uuid4()),
        "text": chunk_text,
        "file_name": file_name,
        "n_tokens": len(encoding.encode(chunk_text))
    } for chunk_text in chunks if len(chunk_text.strip()) > 5] # Loại bỏ các chunk rác quá ngắn
        
    return pd.DataFrame(output_data)

async def extract_entities(text_units: pd.DataFrame,
    text_column: str,
    id_column: str,
    model_name: str = "gemini-1.5-flash", # Hoặc gemini-1.5-pro
    prompt_template: str = "",
    entity_types: List[str] = ["person", "organization", "location"],
    num_threads: int = 100, # Gemini free tier có giới hạn request/phút thấp, nên để thấp
) -> Tuple[pd.DataFrame, pd.DataFrame]:

    # client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

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
    
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    # async def call_gpt(text: str) -> str:
    #     response = await client.responses.create(
    #         model='gpt-5.2',
    #         instructions='Extract entities and relationships of text below. Assign the entities with one of the entity_types. Return output in JSON format: ',
    #         input=f'Entity Types: {entity_types}\nText: {text}',
    #         # response_format={ "type": "json_object" } # Ép GPT trả về JSON chuẩn
    #     )
    #     return response.output_text

    async def call_gpt(text: str, system_prompt, user_content) -> str:
        response = await client.chat.completions.create(
            model='gpt-4o', 
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
        )
        return response.choices[0].message.content
    
    def parse_graph_output(raw_text):
        entities = []
        relationships = []
        
        # Tách theo dấu ##
        segments = raw_text.replace("<|COMPLETE|>", "").split("##")
        
        for seg in segments:
            seg = seg.strip()
            if not seg: continue
            
            # Loại bỏ dấu ngoặc đơn và tách phần tử
        parts = seg.strip("() ").split("<|>")
        
        # Chuẩn hóa tag (loại bỏ dấu nháy kép nếu có)
        tag = parts[0].replace('"', '').strip().lower()

        # Kiểm tra thực thể (cần ít nhất 4 phần tử: tag, name, type, desc)
        if tag == "entity" and len(parts) >= 4:
            entities.append({
                "name": parts[1].strip(),
                "type": parts[2].strip(),
                "description": parts[3].strip()
            })
            
        # Kiểm tra quan hệ (cần ít nhất 5 phần tử: tag, src, tgt, desc, weight)
        elif tag == "relationship" and len(parts) >= 5:
            relationships.append({
                "source": parts[1].strip(),
                "target": parts[2].strip(),
                "description": parts[3].strip(),
                "weight": float(parts[4].strip()) if parts[4].strip().replace('.','',1).isdigit() else 1.0
            })
        else:
            print(f"⚠️ Bỏ qua dòng lỗi định dạng: {seg}")
                
        return entities, relationships

    all_entities = []
    all_relationships = []

    async def sem_process(row):
        async with semaphore:
            text_content = row['text']
            source_id = row['id']
            # Lấy tên văn bản gốc của chunk này (ví dụ: "Thông tư 01/2020/TT-BCA")
            doc_name = row.get('file_name', 'Văn bản gốc') 
            current_system_prompt = GRAPH_PROMPT.replace("{doc_name_context}", doc_name)
            
            # Tiêm tên văn bản vào User Prompt để AI không quên nguồn
            user_content = f"NGUỒN VĂN BẢN: {doc_name}\n\nNỘI DUNG CẦN TRÍCH XUẤT:\n{text_content}"
            print(f"current_system_prompt: {current_system_prompt}")
            print(f"user content: {user_content}")
            
            raw_output = await call_gpt(text_content, current_system_prompt, user_content)
            print(f"raw_output: {raw_output}")
            entities, relations = parse_graph_output(raw_output)
            print(f"entities: {entities}")
            print(f"relations: {relations}")

            
            # Gán source_id để biết thực thể/quan hệ này đến từ chunk nào
            # for e in entities: 
            #     e['source_id'] = source_id
            # for r in relations: 
            #     r['source_id'] = source_id
            
            return entities, relations

    # Chạy song song các task
    semaphore = asyncio.Semaphore(num_threads)
    tasks = [sem_process(row) 
             for _, row in tqdm(text_units.iterrows(),total=len(text_units), desc="Processing chunks")
            ]
    results = await asyncio.gather(*tasks)

    # Gom tất cả kết quả từ các task vào list tổng
    for entities, relations in results:
        all_entities.extend(entities)
        all_relationships.extend(relations)

    # Trả về dưới dạng DataFrame để dễ merge/xử lý sau này
    return all_entities, all_relationships

# Ví dụ cách chạy indexing
async def main():
    try:
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('tokenizers/punkt_tab')
    except LookupError:
        nltk.download('punkt')
        nltk.download('punkt_tab')
    print("setup okay!")

    # raw_text = """Nikola Tesla là một nhà phát minh người Mỹ gốc Serbia. 
    # Ông nổi tiếng với những đóng góp cho việc thiết kế hệ thống điện xoay chiều (AC) hiện đại. 
    # Hệ thống này đã trở thành tiêu chuẩn cho việc truyền tải điện năng trên toàn thế giới."""

    law_texts_df = get_law_texts()
    print(f"law_texts_df: {law_texts_df}")
    df_chunks_final = pd.DataFrame()
    for index, text_df in tqdm(law_texts_df.iterrows(), total=len(law_texts_df), desc="Chunking law texts"):
        print(f"text_df: {text_df}")
        df_chunks = vietnamese_legal_chunk(text_df, chunk_size=1000, chunk_overlap=100)
        df_chunks_final = pd.concat([df_chunks_final, df_chunks], ignore_index=True)
    #df_chunks = chunk(raw_text, chunk_size=50, chunk_overlap=10)
    print(f"df_chunks: {df_chunks_final}")

    # Gọi hàm trích xuất (Sử dụng hàm standalone mà chúng ta đã thảo luận)
    entities, relationships = await extract_entities(
        text_units=df_chunks_final,
        text_column="text",
        id_column="id",
        model_name="gemini-1.5-flash",
        prompt_template="Extract entities and relationships...",
        entity_types=["person", "organization"]
    )
    
    # print(f"entities: {entities}")
    # print(f"relationships: {relationships}")

    relationships_df = pd.DataFrame(relationships)
    print(f"relationships_df: {relationships_df}")

    print("creating graphs...")
    graph = nx.from_pandas_edgelist(relationships_df, edge_attr=["description", "weight"])
    with open('graph.pkl', 'wb') as file:
        pickle.dump(graph, file)
    print("graph saved successfully.")

    with open('entities.pkl', 'wb') as file:
        pickle.dump(entities, file)
    print("entities saved successfully.")

    with open('relationships.pkl', 'wb') as file:
        pickle.dump(relationships, file)
    print("relationships saved successfully.")
    # graphml = "\n".join(nx.generate_graphml(graph))
    # nx.write_graphml(graph, "graph.graphml", encoding="utf-8", prettyprint=True)
    # Cách 2: Nếu bạn muốn lấy chuỗi string để xử lý tiếp
    graphml_string = "\n".join(nx.generate_graphml(graph))
    if not graphml_string.startswith("<?xml"):
        header = '<?xml version="1.0" encoding="utf-8"?>\n'
        graphml_string = header + graphml_string

    with open("graph.graphml", "w", encoding="utf-8") as f:
        f.write(graphml_string)
    print("Done creating graphs!")

    # # Thiết lập kích thước hình vẽ
    # plt.figure(figsize=(10, 8))

    # # Vẽ đồ thị
    # pos = nx.spring_layout(graph) # Thuật toán sắp xếp vị trí các nút
    # nx.draw(graph, pos, with_labels=True, node_color='lightblue', 
    #         edge_color='gray', node_size=2000, font_size=10)

    # # Vẽ trọng số (weight) lên cạnh
    # labels = nx.get_edge_attributes(graph, 'weight')
    # nx.draw_networkx_edge_labels(graph, pos, edge_labels=labels)


    # result, hierarchy = detect_communities_leiden(graph)

    result, hierarchy = _compute_leiden_communities(relationships_df, max_cluster_size=10, use_lcc=False)
    print(f"result: {result}")
    print(f"hierarchy: {hierarchy}")
    total_communities = len(hierarchy)
    print(f"Tổng số cộng đồng được tạo ra: {total_communities}")
    save_full_graph_context(result, hierarchy)



    plt.show()

# @tool
# def graphrag_retrieval(query: str) -> str:
#     """
#     CHỈ SỬ DỤNG công cụ này khi người dùng hỏi về:
#     - Các quy định pháp luật, điều luật.
#     - Mức xử phạt vi phạm hành chính (ví dụ: đánh bài phạt bao nhiêu, vượt đèn đỏ...).
#     - Các thông tin cần trích dẫn chính xác từ văn bản luật pháp.

#     KHÔNG SỬ DỤNG công cụ này nếu:
#     - Người dùng chỉ đang chào hỏi (Xin chào, bạn là ai...).
#     - Người dùng yêu cầu tóm tắt lại câu trả lời trước đó.
#     """
#     vector_db = Chroma(
#         persist_directory=CHROMA_DB_PATH,
#         collection_name="docs",
#         embedding_function=embeddings,
#     )

#     retriever = vector_db.as_retriever(
#         search_type="mmr",
#         search_kwargs={
#             "k": 5,  # Số lượng chunk cuối cùng trả về cho LLM
#             "fetch_k": 20,  # Số lượng chunk lấy ra ban đầu để lọc MMR
#             "lambda_mult": 0.5,  # Cân bằng giữa độ tương đồng (1.0) và độ đa dạng (0.0)
#         },
#     )

#     print(f"\n[Tool Execution] Đang tìm kiếm thông tin cho: '{query}'...")

#     retrieved_docs = retriever.invoke(query)

#     formatted_context = ""
#     for i, doc in enumerate(retrieved_docs):
#         formatted_context += f"--- Tài liệu {i+1} ---\n{doc.page_content}\n\n"

#     if not retrieved_docs:
#         return "Không tìm thấy thông tin tài chính nào liên quan đến câu hỏi trong cơ sở dữ liệu."

#     print(formatted_context)
#     return formatted_context

    
if __name__ == '__main__':
    file_path = "new_prompt_results/relationships.pkl"
    relationships = None

    # Mở và nạp đối tượng
    with open(file_path, "rb") as f:
        relationships = pickle.load(f)

    # Bây giờ bạn có thể sử dụng đối tượng 'obj'
    # print(type(obj))
    relationships_df = pd.DataFrame(relationships)
    # print(relationships_df)

    file_path = "new_prompt_results/entities.pkl"
    entities = None
     # Mở và nạp đối tượng
    with open(file_path, "rb") as f:
        entities = pickle.load(f)

    # Bây giờ bạn có thể sử dụng đối tượng 'obj'
    # print(type(obj))
    relationships_df = pd.DataFrame(relationships)
    entities_df = pd.DataFrame(entities)
    # print(relationships_df.head())
    # print(entities_df.head())

    result, hierarchy = _compute_leiden_communities(relationships_df, max_cluster_size=10, use_lcc=False)
    print(f"result: {result}")
    print(f"hierarchy: {hierarchy}")
    total_communities = len(hierarchy)
    print(f"Tổng số cộng đồng được tạo ra: {total_communities}")

    # 1. Cấu hình thông số
    model_name = "unsloth/meta-llama-3.1-8b-instruct-bnb-4bit"
    max_seq_length = 14000 # Tăng lên 8k để chứa đủ context tóm tắt phân cấp
    max_new_tokens=2048

    # 2. Load model và tokenizer
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name = model_name,
        max_seq_length = max_seq_length,
        load_in_4bit = True, # Giúp chạy nhanh và tiết kiệm VRAM
    )

    # 3. Tối ưu cho Inference
    FastLanguageModel.for_inference(model)

    # 4. Cấu hình Tokenizer để chạy Batch
    tokenizer.padding_side = "left"
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    reports = asyncio.run(generate_hierarchical_community_reports_unsloth(
        community_results=result,
        community_hierarchy=hierarchy,
        entities_df=entities_df,
        relationships_df=relationships_df,
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=max_new_tokens
    ))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Lưu kết quả ra file JSON
    with open(f"community_summaries_{timestamp}.json", "w", encoding="utf-8") as f:
        json.dump(reports, f, ensure_ascii=False, indent=4)

    # asyncio.run(main())