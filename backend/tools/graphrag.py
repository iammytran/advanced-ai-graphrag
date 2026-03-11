
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
from pathlib import Path

from backend.tools.graph_rag.chunking import get_law_texts as get_law_texts_external, chunk_civil_code_markdown
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
ENTITY_TYPES = "VĂN_BẢN_PHÁP_LUẬT, ĐIỀU_KHOẢN, CHỦ_THỂ, QUYỀN_HẠN, NGHĨA_VỤ, HÀNH_VI_VI_PHẠM, CHẾ_TÀI_PHÁP_LÝ, ĐIỀU_KIỆN_ÁP_DỤNG, THỜI_HẠN_THỜI_HIỆU, QUY_ĐỊNH_CỤ_THỂ"

tuple_delimiter="<|>"
completion_delimiter="<|COMPLETE|>"
record_delimiter="##"

GRAPH_PROMPT = """
    ### MỤC TIÊU
    Bạn là chuyên gia phân tích dữ liệu pháp luật. Hãy trích xuất các thực thể và mối quan hệ từ văn bản luật được cung cấp để xây dựng một đồ thị tri thức (Knowledge Graph) chính xác và có tính liên kết cao.

    ### QUY TẮC TRÍCH XUẤT

    #### 1. Cấu trúc văn bản (Phân cấp & Claims)
    - Thực thể Gốc: Tạo 01 thực thể đại diện cho tiêu đề văn bản (Ví dụ: "Điều 15 Luật Đất đai").
    - Các thực thể đích: Trích xuất các nội dung pháp lý trong văn bản đó thành các thực thể loại "QUY_ĐỊNH_CỤ_THỂ" theo quy tắc sau:
        - entity_name: Phải là một câu khẳng định đầy đủ ý nghĩa, diễn giải chi tiết (Ví dụ: "Cá nhân có nghĩa vụ đăng ký đất đai tại cơ quan có thẩm quyền").
        - entity_description: Lặp lại hoặc diễn giải chi tiết hơn câu khẳng định đó để tăng cường ngữ nghĩa.
        - entity_type: Bắt buộc là "QUY_ĐỊNH_CỤ_THỂ".
    - Liên kết: Thiết lập quan hệ "quy định" từ Thực thể Gốc đến các QUY_ĐỊNH_CỤ_THỂ này.

    #### 2. Trích xuất thực thể (Entities):
    Trích xuất mọi thực thể quan trọng xuất hiện trong văn bản thuộc danh sách: [{ENTITY_TYPES}].
    - entity_name: Tên của thực thể (ví dụ: Tên cơ quan, Tên điều luật, Tên hành vi). Lưu ý viết hoa toàn bộ. 
        + QUY TẮC QUAN TRỌNG: Đối với các ĐIỀU, KHOẢN, MỤC, chương, phải đính kèm mã hiệu văn bản trong ngoặc đơn.
        Định dạng: "ĐIỀU [Số] ({{doc_name}})" hoặc "KHOẢN [Số] ĐIỀU [Số] ({{doc_name}})".
        Định dạng: "ĐIỀU [Số] ([Mã hiệu văn bản])"
        Ví dụ: Nếu nguồn là 'Thông tư 01/2020', thực thể phải là "ĐIỀU 1 (TT 01/2020)".
	- entity_type: Một trong các loại sau: [{ENTITY_TYPES}]
	- entity_description: Mô tả chi tiết về chức năng, quyền hạn, nghĩa vụ hoặc nội dung quy định của thực thể đó trong ngữ cảnh văn bản. Tuyệt đối không sử dụng các đại từ chỉ định hoặc từ thay thế (như: đây, đó, này, họ, nó, quy định ấy...). Thay vào đó, phải lặp lại chính xác tên thực thể hoặc nội 	dung cụ thể để đảm bảo mỗi mô tả đều có ý nghĩa độc lập.

	Định dạng mỗi thực thể là: ("entity"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_type>{tuple_delimiter}<entity_description>){record_delimiter}


    #### 3. Trích xuất quan hệ (Relationships)
 	- Từ các thực thể ở bước 2, xác định các cặp (source_entity, target_entity) (thẩm quyền, căn cứ, hình phạt, đối tượng tác động...).
    - Đối với mỗi cặp, trích xuất:
		- source_entity: Tên thực thể nguồn (từ bước 1).
		- target_entity: Tên thực thể đích (từ bước 1).
		- relationship_description: Giải thích rõ lý do tại sao hai thực thể này có quan hệ (ví dụ: "Cơ quan A ban hành Quy định B", "Điều X quy định hình phạt cho Hành vi Y"). Tuyệt đối không sử dụng các đại từ chỉ định hoặc từ thay thế (như: đây, đó, này, họ, nó, quy định 	ấy...). Thay vào đó, phải lặp lại chính xác tên thực thể hoặc nội dung cụ thể để đảm bảo mỗi mô tả đều có ý nghĩa độc lập.
		- relationship_strength: Điểm số từ 1-10 thể hiện mức độ chặt chẽ của mối liên kết pháp lý.
    - Đặc biệt: Cho mọi trường hợp văn bản nhắc đến một Điều, Khoản hoặc Văn bản luật khác (kể cả dẫn chiếu nội bộ), bắt buộc tạo quan hệ "dẫn chiếu tới"

	Định dạng mỗi quan hệ là: ("relationship"{tuple_delimiter}<source_entity>{tuple_delimiter}<target_entity>{tuple_delimiter}<relationship_description>{tuple_delimiter}<relationship_strength>){record_delimiter}

    ---

    ### ĐỊNH DẠNG ĐẦU RA (JSON BẮT BUỘC)
	- Trả về danh sách duy nhất, các phần tử cách nhau bởi dấu ##.
	- Ngôn ngữ: TIẾNG VIỆT hoàn toàn.
	- Kết thúc bằng: {completion_delimiter}

    ######################
	-Ví dụ-
    Text: Chính phủ ban hành Nghị định 123/2024/NĐ-CP. Theo đó, người điều khiển xe máy điện không đội mũ bảo hiểm sẽ bị phạt tiền từ 400.000 đến 600.000 đồng. 
    ######################
    Output: 
    ("entity"{tuple_delimiter}NGHỊ ĐỊNH 123/2024/NĐ-CP{tuple_delimiter}VĂN_BẢN_PHÁP_LUẬT{tuple_delimiter}Nghị định 123/2024/NĐ-CP quy định về xử phạt vi phạm hành chính trong lĩnh vực giao thông đường bộ) {record_delimiter} 
    (“entity"{tuple_delimiter}KHÔNG ĐỘI MŨ BẢO HIỂM{tuple_delimiter}HÀNH_VI_VI_PHẠM{tuple_delimiter}Hành vi người điều khiển xe máy điện không đội mũ bảo hiểm cho người đi mô tô, xe máy) {record_delimiter}
    ("entity"{tuple_delimiter}PHẠT TIỀN TỪ 400.000 ĐẾN 600.000 ĐỒNG{tuple_delimiter}CHẾ_TÀI_PHÁP_LÝ{tuple_delimiter}Mức phạt tiền từ 400.000 đồng đến 600.000 đồng áp dụng cho hành vi vi phạm giao thông cụ thể) {record_delimiter} 
    ("relationship"{tuple_delimiter}NGHỊ ĐỊNH 123/2024/NĐ-CP{tuple_delimiter}KHÔNG ĐỘI MŨ BẢO HIỂM{tuple_delimiter}Nghị định 123/2024/NĐ-CP xác định hành vi không đội mũ bảo hiểm là hành vi vi phạm pháp luật{tuple_delimiter}9) {record_delimiter} 
    ("relationship"{tuple_delimiter}KHÔNG ĐỘI MŨ BẢO HIỂM{tuple_delimiter}PHẠT TIỀN TỪ 400.000 ĐẾN 600.000 ĐỒNG{tuple_delimiter}Hành vi không đội mũ bảo hiểm dẫn đến hình thức xử phạt tiền từ 400.000 đến 600.000 đồng{tuple_delimiter}10) {completion_delimiter}
	######################
	-Dữ liệu thực tế-
	######################
	Entity_types: {ENTITY_TYPES}
	Text: {input_text}
	######################
	Output:"""


# def extract_entities_unsloth(
#     text_units: pd.DataFrame,
#     model,
#     tokenizer,
#     prompt_template: str,
#     entity_types: str,
#     folder_name: str,
#     stop_token_ids,
#     batch_size: int = 4, # Điều chỉnh dựa trên VRAM (4, 8, 16...)
#     max_seq_length: int = 4096,
#     max_new_tokens: int = 1500
# ):
    
#     FastLanguageModel.for_inference(model)
#     tokenizer.padding_side = 'left'
#     all_entities = []
#     all_relationships = []

#     # Hàm parse nội bộ
#     def parse_graph_output(raw_text):
#         entities, relationships = [], []
#         segments = raw_text.split("##")
#         for seg in segments:
#             parts = seg.strip("() ").split("<|>")
#             tag = parts[0].replace('"', '').strip().lower()
#             if tag == "entity" and len(parts) >= 4:
#                 entities.append({
#                     "name": parts[1].strip(), 
#                     "type": parts[2].strip(), 
#                     "description": parts[3].strip()
#                 })
#             elif tag == "relationship" and len(parts) >= 5:
#                 relationships.append({
#                     "source": parts[1].strip(), 
#                     "target": parts[2].strip(), 
#                     "description": parts[3].strip(), 
#                     "weight": float(parts[4].strip()) if parts[4].strip().replace('.','',1).isdigit() else 1.0
#                 })
#         return entities, relationships

#     # Vòng lặp xử lý theo Batch
#     for i in tqdm(range(0, len(text_units), batch_size), desc="Batch Inferencing"):
#         batch_rows = text_units.iloc[i : i + batch_size]
        
#         prompts = []
#         for _, row in batch_rows.iterrows():
#             # Lấy tên file làm ngữ cảnh
#             doc = row.get('file_name', 'Văn bản gốc')
#             doc_name = os.path.splitext(doc)[0]
#             text_content = row.get('chunk', '') # Đảm bảo key là 'chunk' như code bạn dùng
            
#             full_prompt = prompt_template.format(
#                 ENTITY_TYPES=entity_types,
#                 doc_name=doc_name,
#                 input_text=text_content,
#                 tuple_delimiter=tuple_delimiter,
#                 completion_delimiter=completion_delimiter,
#                 record_delimiter=record_delimiter
#             )

#             prompts.append(full_prompt)
        
#         # messages = [
#         #     {"role": "system", "content": "Bạn là chuyên gia phân tích dữ liệu pháp luật. Trích xuất thực thể theo định dạng (entity<|>...)"},
#         #     {"role": "user", "content": f"Text: {text_content}"}
#         # ]
#         # input_ids = tokenizer.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt").to("cuda")

#         # Tokenize toàn bộ batch
#         inputs = tokenizer(
#             prompts, 
#             return_tensors="pt", 
#             padding=True, 
#             truncation=True, 
#             max_length=max_seq_length - max_new_tokens # Giới hạn context length
#         ).to("cuda")

#         outputs = model.generate(
#             input_ids = inputs.input_ids,
#             attention_mask = inputs.attention_mask, # Truyền rõ ràng mask ở đây
#             max_new_tokens = max_new_tokens,
#             use_cache = True,
#             temperature = 0.1,
#             pad_token_id=tokenizer.pad_token_id,
#             eos_token_id=tokenizer.eos_token_id,
#             do_sample=False
#         )

#         debug_log_path = f"{folder_name}/entities_relations.txt" 
#         decoded_outputs = tokenizer.batch_decode(outputs, skip_special_tokens=True)
#         with open(debug_log_path, "a", encoding="utf-8") as f:
#                 f.write("decoded_outputs:\n")
#                 f.write(f"{decoded_outputs}")
#                 f.write(f"\n{'='*50}\n")

#         print(f"Writing extract outputs or batch {(i // batch_size) + 1} to file...")
#         for idx, actual_gen in enumerate(decoded_outputs):
#             with open(debug_log_path, "a", encoding="utf-8") as f:
#                 f.write(f"\n{'='*50}\n")
#                 f.write(f"PROMPT: {full_prompt}")
#                 f.write(f"\n{'='*20}\n")
#                 f.write(f"BATCH START - INDEX: {i + idx}\n")
#                 f.write(f"{'-'*20} RAW OUTPUT {'-'*20}\n")
#                 f.write(actual_gen)
#                 f.write(f"\n{'='*50}\n")
#             entities, relations = parse_graph_output(actual_gen)
#             all_entities.extend(entities)
#             all_relationships.extend(relations)
            
#         # Giải phóng bộ nhớ tạm sau mỗi batch (tùy chọn nhưng an toàn cho GPU)
#         del inputs, outputs
#         torch.cuda.empty_cache()

#     return all_entities, all_relationships

def extract_entities_unsloth(
    text_units: pd.DataFrame,
    model,
    tokenizer,
    entity_types: str,
    folder_name: str,
    stop_token_ids,
    batch_size: int = 4, # Giảm batch_size xuống để tăng độ tập trung cho bản 4-bit
    max_seq_length: int = 8192,
    max_new_tokens: int = 1500
):
    # from unsloth import FastLanguageModel
    FastLanguageModel.for_inference(model)
    
    all_entities = []
    all_relationships = []
    
    # Cấu hình Tokenizer BẮT BUỘC
    tokenizer.padding_side = "left" 
    if tokenizer.pad_token is None:
        tokenizer.pad_token = "<|reserved_special_token_0|>"

    def parse_graph_output(raw_text):
        entities, relationships = [], []
        # Tách theo record_delimiter đã định nghĩa là ##
        segments = raw_text.split("##")
        for seg in segments:
            # Làm sạch các ký tự rác xung quanh
            parts = seg.strip("() \n\t").split("<|>")
            if not parts or len(parts) < 1: 
                continue
            
            tag = parts[0].replace('"', '').replace('“', '').replace('”', '').strip().lower()
            
            if "entity" in tag and len(parts) >= 4:
                entities.append({
                    "name": parts[1].strip(), 
                    "type": parts[2].strip(), 
                    "description": parts[3].strip()
                })
            elif "relationship" in tag and len(parts) >= 5:
                relationships.append({
                    "source": parts[1].strip(), 
                    "target": parts[2].strip(), 
                    "description": parts[3].strip(), 
                    "weight": float(parts[4].strip()) if parts[4].strip().replace('.','',1).isdigit() else 1.0
                })
        return entities, relationships

    for i in tqdm(range(0, len(text_units), batch_size), desc="Batch Inferencing"):
        batch_rows = text_units.iloc[i : i + batch_size]
        batch_messages = []
        
        for _, row in batch_rows.iterrows():
            doc_name = os.path.splitext(row.get('file_name', 'Văn bản gốc'))[0]
            # Làm sạch text đầu vào: loại bỏ xuống dòng thừa gây nhiễu
            text_content = str(row.get('chunk', '')).replace('\n', ' ').strip()

            # Chat Template với lệnh cấm đếm số
            messages = [
                {
                    "role": "system", 
                    "content": f"""Bạn là chuyên gia phân tích dữ liệu pháp luật. Hãy trích xuất các thực thể và mối quan hệ từ văn bản luật được cung cấp để xây dựng một đồ thị tri thức (Knowledge Graph) chính xác và có tính liên kết cao.

                        ### QUY TẮC TRÍCH XUẤT

                        #### 1. Cấu trúc văn bản (Phân cấp & Claims)
                        - Thực thể Gốc: Tạo 01 thực thể đại diện cho tiêu đề văn bản (Ví dụ: "Điều 15 Luật Đất đai").
                        - Các thực thể đích: Trích xuất các nội dung pháp lý trong văn bản đó thành các thực thể loại "QUY_ĐỊNH_CỤ_THỂ" theo quy tắc sau:
                            - entity_name: Phải là một câu khẳng định đầy đủ ý nghĩa, diễn giải chi tiết (Ví dụ: "Cá nhân có nghĩa vụ đăng ký đất đai tại cơ quan có thẩm quyền").
                            - entity_description: Lặp lại hoặc diễn giải chi tiết hơn câu khẳng định đó để tăng cường ngữ nghĩa.
                            - entity_type: Bắt buộc là "QUY_ĐỊNH_CỤ_THỂ".
                        - Liên kết: Thiết lập quan hệ "quy định" từ Thực thể Gốc đến các QUY_ĐỊNH_CỤ_THỂ này.

                        #### 2. Trích xuất thực thể (Entities):
                        Trích xuất mọi thực thể quan trọng xuất hiện trong văn bản thuộc danh sách: [{ENTITY_TYPES}].
                        - entity_name: Tên của thực thể (ví dụ: Tên cơ quan, Tên điều luật, Tên hành vi). Lưu ý viết hoa toàn bộ. 
                            + QUY TẮC QUAN TRỌNG: Đối với các ĐIỀU, KHOẢN, MỤC, chương, phải đính kèm mã hiệu văn bản trong ngoặc đơn.
                            Định dạng: "ĐIỀU [Số] ({{doc_name}})" hoặc "KHOẢN [Số] ĐIỀU [Số] ({{doc_name}})".
                            Định dạng: "ĐIỀU [Số] ([Mã hiệu văn bản])"
                            Ví dụ: Nếu nguồn là 'Thông tư 01/2020', thực thể phải là "ĐIỀU 1 (TT 01/2020)".
                        - entity_type: Một trong các loại sau: [{ENTITY_TYPES}]
                        - entity_description: Mô tả chi tiết về chức năng, quyền hạn, nghĩa vụ hoặc nội dung quy định của thực thể đó trong ngữ cảnh văn bản. Tuyệt đối không sử dụng các đại từ chỉ định hoặc từ thay thế (như: đây, đó, này, họ, nó, quy định ấy...). Thay vào đó, phải lặp lại chính xác tên thực thể hoặc nội 	dung cụ thể để đảm bảo mỗi mô tả đều có ý nghĩa độc lập.

                        Định dạng mỗi thực thể là: ("entity"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_type>{tuple_delimiter}<entity_description>){record_delimiter}


                        #### 3. Trích xuất quan hệ (Relationships)
                        - Từ các thực thể ở bước 2, xác định các cặp (source_entity, target_entity) (thẩm quyền, căn cứ, hình phạt, đối tượng tác động...).
                        - Đối với mỗi cặp, trích xuất:
                            - source_entity: Tên thực thể nguồn (từ bước 1).
                            - target_entity: Tên thực thể đích (từ bước 1).
                            - relationship_description: Giải thích rõ lý do tại sao hai thực thể này có quan hệ (ví dụ: "Cơ quan A ban hành Quy định B", "Điều X quy định hình phạt cho Hành vi Y"). Tuyệt đối không sử dụng các đại từ chỉ định hoặc từ thay thế (như: đây, đó, này, họ, nó, quy định 	ấy...). Thay vào đó, phải lặp lại chính xác tên thực thể hoặc nội dung cụ thể để đảm bảo mỗi mô tả đều có ý nghĩa độc lập.
                            - relationship_strength: Điểm số từ 1-10 thể hiện mức độ chặt chẽ của mối liên kết pháp lý.
                        - Đặc biệt: Cho mọi trường hợp văn bản nhắc đến một Điều, Khoản hoặc Văn bản luật khác (kể cả dẫn chiếu nội bộ), bắt buộc tạo quan hệ "dẫn chiếu tới"

                        Định dạng mỗi quan hệ là: ("relationship"{tuple_delimiter}<source_entity>{tuple_delimiter}<target_entity>{tuple_delimiter}<relationship_description>{tuple_delimiter}<relationship_strength>){record_delimiter}

                        ---

                        ### ĐỊNH DẠNG ĐẦU RA (JSON BẮT BUỘC)
                        - Trả về danh sách duy nhất, các phần tử cách nhau bởi dấu ##.
                        - Ngôn ngữ: TIẾNG VIỆT hoàn toàn.
                        - Kết thúc bằng: {completion_delimiter}

                        ### VÍ DỤ MẪU ĐỂ BẠN LÀM THEO:
                        Text: Chính phủ ban hành Nghị định 123/2024/NĐ-CP. Theo đó, người điều khiển xe máy điện không đội mũ bảo hiểm sẽ bị phạt tiền từ 400.000 đến 600.000 đồng. 
                        Output: 
                        ("entity"{tuple_delimiter}NGHỊ ĐỊNH 123/2024/NĐ-CP{tuple_delimiter}VĂN_BẢN_PHÁP_LUẬT{tuple_delimiter}Nghị định 123/2024/NĐ-CP quy định về xử phạt vi phạm hành chính trong lĩnh vực giao thông đường bộ) {record_delimiter} 
                        (“entity"{tuple_delimiter}KHÔNG ĐỘI MŨ BẢO HIỂM{tuple_delimiter}HÀNH_VI_VI_PHẠM{tuple_delimiter}Hành vi người điều khiển xe máy điện không đội mũ bảo hiểm cho người đi mô tô, xe máy) {record_delimiter}
                        ("entity"{tuple_delimiter}PHẠT TIỀN TỪ 400.000 ĐẾN 600.000 ĐỒNG{tuple_delimiter}CHẾ_TÀI_PHÁP_LÝ{tuple_delimiter}Mức phạt tiền từ 400.000 đồng đến 600.000 đồng áp dụng cho hành vi vi phạm giao thông cụ thể) {record_delimiter} 
                        ("relationship"{tuple_delimiter}NGHỊ ĐỊNH 123/2024/NĐ-CP{tuple_delimiter}KHÔNG ĐỘI MŨ BẢO HIỂM{tuple_delimiter}Nghị định 123/2024/NĐ-CP xác định hành vi không đội mũ bảo hiểm là hành vi vi phạm pháp luật{tuple_delimiter}9) {record_delimiter} 
                        ("relationship"{tuple_delimiter}KHÔNG ĐỘI MŨ BẢO HIỂM{tuple_delimiter}PHẠT TIỀN TỪ 400.000 ĐẾN 600.000 ĐỒNG{tuple_delimiter}Hành vi không đội mũ bảo hiểm dẫn đến hình thức xử phạt tiền từ 400.000 đến 600.000 đồng{tuple_delimiter}10) {completion_delimiter}
                        """
                },
                {
                    "role": "user", 
                    "content": f"Văn bản gốc: {doc_name}\nNội dung cần trích xuất: {text_content}\n\nOutput:"
                }
            ]
            
            prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            print(prompt)
            batch_messages.append(prompt)

        inputs = tokenizer(batch_messages, return_tensors="pt", padding=True, truncation=True, max_length=max_seq_length-max_new_tokens).to("cuda")

        # GENERATION CONFIG - KỶ LUẬT THÉP
        outputs = model.generate(
            input_ids = inputs.input_ids,
            attention_mask = inputs.attention_mask, # Truyền rõ ràng mask ở đây
            max_new_tokens = max_new_tokens,
            use_cache = True,
            temperature = 0.1,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
            do_sample=False
       )

        input_len = inputs.input_ids.shape[1]
        decoded_outputs = tokenizer.batch_decode(outputs[:, input_len:], skip_special_tokens=True)

        # Lưu Log để debug
        os.makedirs(folder_name, exist_ok=True)
        debug_log_path = os.path.join(folder_name, "debug_log.txt")
        
        for idx, actual_gen in enumerate(decoded_outputs):
            with open(debug_log_path, "a", encoding="utf-8") as f:
                f.write(f"\n--- BATCH {i+idx} ---\n{actual_gen}\n{'-'*30}\n")
            
            entities, relations = parse_graph_output(actual_gen)
            all_entities.extend(entities)
            all_relationships.extend(relations)

        del inputs, outputs
        torch.cuda.empty_cache()

    return all_entities, all_relationships

# Ví dụ cách chạy indexing
async def main():
    # 0. Create folder contains everything of current timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_folder_name = f"outputs_{timestamp}"
    Path(new_folder_name).mkdir(parents=True, exist_ok=True)

    # 1. Cấu hình thông số
    model_name = "unsloth/meta-llama-3.1-8b-instruct-bnb-4bit"
    max_seq_length = 8192
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
    tokenizer.pad_token = "<|reserved_special_token_0|>" 
    tokenizer.padding_side = "left" # Bắt buộc phải là left cho decoder-only model như Llama
    # Tập hợp các biển báo dừng "quyền lực" nhất
    stop_words = ["<|end_of_text|>", "<|eot_id|>", "<|COMPLETE|>"]
    stop_token_ids = [tokenizer.convert_tokens_to_ids(word) for word in stop_words]

    # Lọc bỏ các None nếu token không tồn tại trong vocab
    stop_token_ids = [ids for ids in stop_token_ids if ids is not None]

    # 5. Chunking
    print("Chunking...")
    law_texts_df = get_law_texts_external()
    law_texts_df["chunk"] = law_texts_df["content"].apply(chunk_civil_code_markdown)

    new_df = law_texts_df.explode('chunk', ignore_index=True)

    # 6. (Tùy chọn) Nếu bạn muốn bung các key trong dict của chunk 
    # (như 'chuong', 'dieu') ra thành các cột riêng biệt:
    chunk_details = pd.json_normalize(new_df['chunk'])

    # 7. Đổi tên cột 'content' thành 'chunk' (nếu trong dict key là 'content')
    chunk_details = chunk_details.rename(columns={'content': 'chunk'})

    final_df = pd.concat([new_df[['file_name']], chunk_details], axis=1)
    print("Ready for extracting entities and relationships...")

    # 8. Gọi hàm trích xuất (Sử dụng hàm standalone mà chúng ta đã thảo luận)
    entities_df, relationships_df = extract_entities_unsloth(
        text_units=final_df,
        model=model,
        tokenizer=tokenizer,
        # prompt_template=GRAPH_PROMPT,
        entity_types=ENTITY_TYPES, # Biến bạn đã định nghĩa ở trên,
        folder_name=new_folder_name,
        stop_token_ids=stop_token_ids,
        max_seq_length = max_seq_length,
        max_new_tokens=max_new_tokens
    )
    print("Extract entities và relationships thành công!")

    # 9. Lưu entities và relations sang pickle file
    with open(f'{new_folder_name}/entities.pkl', 'wb') as f:
        pickle.dump(entities_df, f)
    with open(f'{new_folder_name}/relationships.pkl', 'wb') as f:
        pickle.dump(relationships_df, f)
    print("Lưu entities và relationships thành công!")

    # 10. Vẽ đồ thị
    # print("creating graphs...")
    # graph = nx.from_pandas_edgelist(relationships_df, edge_attr=["description", "weight"])
    # # graphml = "\n".join(nx.generate_graphml(graph))
    # # nx.write_graphml(graph, "graph.graphml", encoding="utf-8", prettyprint=True)
    # # Cách 2: Nếu bạn muốn lấy chuỗi string để xử lý tiếp
    # graphml_string = "\n".join(nx.generate_graphml(graph))
    # if not graphml_string.startswith("<?xml"):
    #     header = '<?xml version="1.0" encoding="utf-8"?>\n'
    #     graphml_string = header + graphml_string

    # with open("graph.graphml", "w", encoding="utf-8") as f:
    #     f.write(graphml_string)
    # print("Done creating graphs!")

    # # # Thiết lập kích thước hình vẽ
    # # plt.figure(figsize=(10, 8))
    # # pos = nx.spring_layout(graph) # Thuật toán sắp xếp vị trí các nút
    # # nx.draw(graph, pos, with_labels=True, node_color='lightblue', 
    # #         edge_color='gray', node_size=2000, font_size=10)

    # # # Vẽ trọng số (weight) lên cạnh
    # # labels = nx.get_edge_attributes(graph, 'weight')
    # # nx.draw_networkx_edge_labels(graph, pos, edge_labels=labels)
    # plt.show()

    # 10. Compute leiden communities
    result, hierarchy = _compute_leiden_communities(relationships_df, max_cluster_size=10, use_lcc=False)
    total_communities = len(hierarchy)

    full_context = {
        "total_communities": total_communities,
        "community_mapping": result, # {level: {node: cluster_id}}
        "community_hierarchy": hierarchy # {cluster_id: parent_id}
    }

    communities_file_name = f"{new_folder_name}/communities.txt"
    with open(communities_file_name, 'w', encoding='utf-8') as f:
        json.dump(full_context, f, ensure_ascii=False, indent=4)


    # 11. Tạo community summary
    reports = asyncio.run(generate_hierarchical_community_reports_unsloth(
        community_results=result,
        community_hierarchy=hierarchy,
        entities_df=entities_df,
        relationships_df=relationships_df,
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=max_new_tokens,
        context_window=max_seq_length,
        folder_for_debug=new_folder_name
    ))

    with open(f"{new_folder_name}/community_summaries.json", "w", encoding="utf-8") as f:
        json.dump(reports, f, ensure_ascii=False, indent=4)
    print("Extract community summaries thành công!")

    
if __name__ == '__main__':
    asyncio.run(main())