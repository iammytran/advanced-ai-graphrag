
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
import torch
import logging
import transformers
from datetime import datetime
from langchain.tools import tool
from langchain_chroma import Chroma
from datetime import datetime
from pathlib import Path
from vllm import LLM, SamplingParams
from sentence_transformers import SentenceTransformer
import numpy as np

from backend.tools.graph_rag.chunking import get_law_texts as get_law_texts_external, chunk_civil_code_markdown
from backend.tools.graph_rag.compute_leiden_communities import _compute_leiden_communities
from backend.tools.graph_rag.generate_community_summary import generate_hierarchical_community_reports
from backend.tools.graph_rag.global_query_vllm import run_global_search

# 1. Nạp các biến từ tệp .env
load_dotenv()

# 1. Tắt log của transformers để tránh cái warning gây crash kia
transformers.logging.set_verbosity_error()

# 2. Hoặc cấu hình lại logger cơ bản để bỏ qua các tham số thừa
logging.basicConfig(level=logging.ERROR)

Communities = list[tuple[int, int, int, list[str]]]

# Định nghĩa danh sách các loại thực thể phù hợp với Luật
# ENTITY_TYPES = "VĂN_BẢN_PHÁP_LUẬT, ĐIỀU_KHOẢN, CHỦ_THỂ, QUYỀN_HẠN, NGHĨA_VỤ, HÀNH_VI_VI_PHẠM, CHẾ_TÀI_PHÁP_LÝ, ĐIỀU_KIỆN_ÁP_DỤNG, THỜI_HẠN_THỜI_HIỆU, QUY_ĐỊNH_CỤ_THỂ"
ENTITY_TYPES = "VĂN_BẢN_PHÁP_LUẬT, ĐIỀU_KHOẢN, CHỦ_THỂ, QUY_ĐỊNH, HÀNH_VI, THỜI_HẠN"

tuple_delimiter="<|>"
completion_delimiter="<|COMPLETE|>"
record_delimiter="##"

def parse_graph_output(raw_text):
        entities, relationships, claims = [], [], []
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
            
            # 3. Parse Claim (Quy định) - 8 trường dữ liệu
            elif "claim" in tag and len(parts) >= 9:
                claims.append({
                    "subject": parts[1].strip(),
                    "object": parts[2].strip(),
                    "claim_type": parts[3].strip(),
                    "status": parts[4].strip(),
                    "start_date": parts[5].strip(),
                    "end_date": parts[6].strip(),
                    "description": parts[7].strip(),
                    "source_text": parts[8].strip()
                })
        return entities, relationships, claims

def extract_info_from_chunk(text_units, folder_path, model_path, entity_types, tuple_delimiter, record_delimiter, completion_delimiter):
    # 1. Khởi tạo model vLLM (Thay thế cho model.generate truyền thống)
    # vLLM tự động quản lý bộ nhớ cực tốt
    llm = LLM(model=model_path, trust_remote_code=True, tensor_parallel_size=2, gpu_memory_utilization=0.7) 
    
    # 2. Cấu hình "Kỷ luật thép" cho vLLM
    sampling_params = SamplingParams(
        temperature=0.1,
        top_p=0.9,
        max_tokens=2048, # max_new_tokens của bạn
        repetition_penalty=1.1,
        stop=[completion_delimiter, "<|im_end|>", "<|endoftext|>"]
    )

    all_prompts = []
    
    # 3. Chuẩn bị toàn bộ prompts (Không cần chia batch thủ công ở đây)
    for _, row in text_units.iterrows():
        doc_name = os.path.splitext(row.get('file_name', 'Văn bản gốc'))[0]
        text_content = str(row.get('chunk', '')).replace('\n', ' ').strip()

        messages = [
                {
                    "role": "system", 
                    "content": f"""Bạn là chuyên gia phân tích dữ liệu pháp luật. Hãy trích xuất các thực thể và mối quan hệ từ văn bản luật được cung cấp để xây dựng một đồ thị tri thức (Knowledge Graph) chính xác và có tính liên kết cao.

                        ## QUY TẮC TRÍCH XUẤT THỰC THỂ (ENTITIES)
                            Trích xuất mọi thực thể quan trọng thuộc danh mục: [{entity_types}].
                            Cho phần này hãy trả về:
                                + Tên thực thể (entity_name): VIẾT HOA TOÀN BỘ.
                                + Loại thực thể (entity_type): 1 trong những lọai sau:[{entity_types}]
                                + Mô tả (entity_description): Mô tả chi tiết về chức năng, quyền hạn, nghĩa vụ hoặc nội dung quy định của thực thể đó trong ngữ cảnh văn bản. Tuyệt đối không sử dụng các đại từ chỉ định hoặc từ thay thế (như: đây, đó, này, họ, nó, quy định ấy...). Thay vào đó, phải lặp lại chính xác tên thực thể hoặc nội 	dung cụ thể để đảm bảo mỗi mô tả đều có ý nghĩa độc lập.

                            Lưu ý trường hợp đặc biệt sau:
                                + Với thực thể liên quan đến Điều/Khoản: Phải kèm mã hiệu trong ngoặc. VD: "ĐIỀU 1 ({doc_name})".                                
                        ## QUY TẮC TRÍCH XUẤT QUAN HỆ (RELATIONSHIPS)
                            Xác định các mối liên kết giữa các thực thể đã trích xuất. Cho phần này, hãy trả về:
                                + source_entity: Tên thực thể nguồn (từ bước 1)
                                + target_entity: Tên thực thể đích (từ bước 1)
                                + relationship_description: Giải thích rõ lý do tại sao hai thực thể này có quan hệ (ví dụ: "Cơ quan A ban hành Quy định B", "Điều X quy định hình phạt cho Hành vi Y"). Tuyệt đối không sử dụng các đại từ chỉ định hoặc từ thay thế (như: đây, đó, này, họ, nó, quy định 	ấy...). Thay vào đó, phải lặp lại chính xác tên thực thể hoặc nội dung cụ thể để đảm bảo mỗi mô tả đều có ý nghĩa độc lập.
                                + relationship_strength: Điểm số từ 1-10 thể hiện mức độ chặt chẽ của mối liên kết pháp lý.
                            Đặc biệt: Cho mọi trường hợp văn bản nhắc đến một Điều, Khoản hoặc Văn bản luật khác (kể cả dẫn chiếu nội bộ), bắt buộc tạo quan hệ "dẫn chiếu tới"

                        ## QUY TẮC TRÍCH XUẤT QUY ĐỊNH (CLAIMS)
                            Trích xuất nội dung quy định: Với mỗi thực thể đã trích xuất, trích xuất các quy định liên quan mà thực thể đó là "Chủ thể thực hiện".
                            Với mỗi quy định, trích xuất:
                                + Chủ thể (Subject): Tên đối tượng/nhóm đối tượng phải thực thi quy định (VIẾT HOA).
                                + Đối tượng liên quan (Object): Cơ quan quản lý, hoặc bên chịu tác động của quy định này. Nếu không có, dùng **NONE**.
                                + Loại quy định (Claim Type): Phân loại (ví dụ: NGHĨA VỤ, QUYỀN HẠN, ĐIỀU KIỆN, HÀNH VI CẤM).
                                + Trạng thái (Claim Status): **TRUE** (Đang có hiệu lực), **SUSPECTED** (Cần kiểm tra văn bản sửa đổi).
                                - Mô tả chi tiết (Claim Description): Nội dung cụ thể của quy định, các điều kiện kèm theo và hệ quả pháp lý.
                                - Thời điểm (Claim Date): Khoảng thời gian (Ngày bắt đầu, Ngày kết thúc) theo định dạng ISO-8601. Nếu chỉ có một mốc thời gian, dùng mốc đó cho cả hai. Nếu không rõ, dùng **NONE**.
                                - Trích dẫn (Claim Source Text): Danh sách **tất cả** các câu trích nguyên văn từ văn bản gốc có liên quan đến quy định này. Gộp các câu trích dẫn thành 1 chuỗi ký tự.

                        ## ĐỊNH DẠNG ĐẦU RA (BẮT BUỘC)
                            Trả về danh sách các phần tử cách nhau bởi dấu ##. Mỗi phần tử tuân thủ cấu trúc sau:
                                + Thực thể: ("entity"<|><entity_name><|><entity_type><|><entity_description>)
                                + Quan hệ: ("relationship"<|><source_entity><|><target_entity><|><relationship_description><|><relationship_strength>)
                                + Quy định: ("claim"{tuple_delimiter}<subject_entity>{tuple_delimiter}<object_entity>{tuple_delimiter}<claim_type>{tuple_delimiter}<claim_status>{tuple_delimiter}<claim_start_date>{tuple_delimiter}<claim_end_date>{tuple_delimiter}<claim_description>{tuple_delimiter}<claim_source>) 
                                + Kết thúc bằng: {completion_delimiter}
                            NGÔN NGỮ: Chỉ sử dụng Tiếng Việt hoàn chỉnh. Tuyệt đối không sử dụng tiếng Trung, tiếng Anh hay bất kỳ ngôn ngữ nào khác.
                            ĐỊNH DẠNG: Chỉ trả về dữ liệu trích xuất, không giải thích thêm bằng tiếng Trung.

                        ## VÍ DỤ MẪU ĐỂ BẠN LÀM THEO:
                        Text: Chính phủ ban hành Nghị định 123/2024/NĐ-CP. Theo đó, người điều khiển xe máy điện không đội mũ bảo hiểm sẽ bị phạt tiền từ 400.000 đến 600.000 đồng. 
                        Output: 
                        ("entity"{tuple_delimiter}NGHỊ ĐỊNH 123/2024/NĐ-CP{tuple_delimiter}VĂN_BẢN_PHÁP_LUẬT{tuple_delimiter}Nghị định 123/2024/NĐ-CP quy định về xử phạt vi phạm hành chính trong lĩnh vực giao thông đường bộ) {record_delimiter} 
                        (“entity"{tuple_delimiter}KHÔNG ĐỘI MŨ BẢO HIỂM{tuple_delimiter}HÀNH_VI_VI_PHẠM{tuple_delimiter}Hành vi người điều khiển xe máy điện không đội mũ bảo hiểm cho người đi mô tô, xe máy) {record_delimiter}
                        ("entity"{tuple_delimiter}PHẠT TIỀN TỪ 400.000 ĐẾN 600.000 ĐỒNG{tuple_delimiter}CHẾ_TÀI_PHÁP_LÝ{tuple_delimiter}Mức phạt tiền từ 400.000 đồng đến 600.000 đồng áp dụng cho hành vi vi phạm giao thông cụ thể) {record_delimiter} 
                        ("relationship"{tuple_delimiter}NGHỊ ĐỊNH 123/2024/NĐ-CP{tuple_delimiter}KHÔNG ĐỘI MŨ BẢO HIỂM{tuple_delimiter}Nghị định 123/2024/NĐ-CP xác định hành vi không đội mũ bảo hiểm là hành vi vi phạm pháp luật{tuple_delimiter}9) {record_delimiter} 
                        ("relationship"{tuple_delimiter}KHÔNG ĐỘI MŨ BẢO HIỂM{tuple_delimiter}PHẠT TIỀN TỪ 400.000 ĐẾN 600.000 ĐỒNG{tuple_delimiter}Hành vi không đội mũ bảo hiểm dẫn đến hình thức xử phạt tiền từ 400.000 đến 600.000 đồng{tuple_delimiter}10) {completion_delimiter}
                        ("claim"{tuple_delimiter}NGƯỜI ĐIỀU KHIỂN XE MÁY ĐIỆN{tuple_delimiter}NGHỊ ĐỊNH 123/2024/NĐ-CP{tuple_delimiter}HÀNH VI BỊ NGHIÊM CẤM{tuple_delimiter}TRUE{tuple_delimiter}2024-01-01{tuple_delimiter}NONE{tuple_delimiter}Không đội mũ bảo hiểm bị xử phạt hành chính mức 400.000 - 600.000 VNĐ.{tuple_delimiter}"người điều khiển xe máy điện không đội mũ bảo hiểm sẽ bị phạt tiền từ 400.000 đến 600.000 đồng")                        
"""
                },
                {
                    "role": "user", 
                    "content": f"Văn bản gốc: {doc_name}\nNội dung cần trích xuất: {text_content}\n\nOutput:"
                }
            ]
        
        # Sử dụng tokenizer của vLLM để apply template
        prompt = llm.get_tokenizer().apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        all_prompts.append(prompt)

    # 4. Inference siêu tốc với vLLM
    print(f"Bắt đầu trích xuất {len(all_prompts)} văn bản với vLLM...")
    outputs = llm.generate(all_prompts, sampling_params, use_tqdm=True)

    all_entities = []
    all_relationships = []
    all_claims=[]

    # 5. Parse kết quả
    print(f"Bắt đầu phân tích kết quả...")
    for i, output in enumerate(outputs):
        actual_gen = output.outputs[0].text
        prompt_sent = output.prompt # Lấy lại prompt đã gửi cho vLLM
        
        # Parse kết quả
        entities, relations, claims = parse_graph_output(actual_gen)
        all_entities.extend(entities)
        all_relationships.extend(relations)
        all_claims.extend(claims)

        debug_step = 10
        
        # LOG DEBUG: Cứ mỗi 10 mẫu sẽ ghi log 1 lần
        if i % debug_step == 0:
            with open(f"{folder_path}/debug_vllm_log.txt", "a", encoding="utf-8") as f:
                f.write(f"\n" + "="*50)
                f.write(f"\n--- DEBUG CỤM BẮT ĐẦU TỪ MẪU {i} ---")
                f.write(f"\n[PROMPT CỦA MẪU ĐẠI DIỆN]:\n{prompt_sent}")
                f.write(f"\n" + "-"*30)
                f.write(f"\n[OUTPUT CỦA MẪU ĐẠI DIỆN]:\n{actual_gen}")
                f.write(f"\n" + "-"*30)
                
                # Thống kê nhanh của mẫu hiện tại
                f.write(f"\n[THỐNG KÊ MẪU {i}]: {len(entities)} entities, {len(relations)} relations.")
                
                # Nếu muốn xem tổng tích lũy đến hiện tại
                f.write(f"\n[TỔNG TÍCH LŨY ĐẾN HIỆN TẠI]: {len(all_entities)} entities, {len(all_relationships)} relations.")
                f.write(f"\n" + "="*50 + "\n")

        # 1. Chuyển sang DataFrame
        df_entities = pd.DataFrame(all_entities)
        df_relationships = pd.DataFrame(all_relationships)
        df_claims = pd.DataFrame(all_claims)

        # 2. Xử lý trùng lặp (Quan trọng cho Knowledge Graph)
        # Vì nhiều Điều luật có thể nhắc đến cùng 1 thực thể, My nên gộp chúng lại
        if not df_entities.empty:
            df_entities = df_entities.drop_duplicates(subset=['name'], keep='first')
        
        if not df_relationships.empty:
            df_relationships = df_relationships.drop_duplicates(
                subset=['source', 'target', 'description'], keep='first'
        )
            
        if not df_claims.empty:
            df_claims = df_claims.drop_duplicates(
                subset=['source', 'target', 'description'], keep='first'
        )

    return df_entities, df_relationships, df_claims

def route_graphrag_query(query: str, llm):
    """
    Sử dụng thư viện vLLM để xác định loại query cho GraphRAG.
    """
    
    # Thiết lập tham số lấy mẫu
    sampling_params = SamplingParams(
        temperature=0.0,  # Để kết quả ổn định nhất cho việc phân loại
        max_tokens=200,
        stop=["}"],       # Dừng ngay khi đóng JSON
    )

    prompt_template = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
    Bạn là một chuyên gia điều phối hệ thống GraphRAG. Bạn chỉ được phép trả về định dạng JSON.
    Nhiệm vụ: Xác định câu hỏi dùng 'local' hay 'global' search.
    - 'local': Hỏi về thực thể cụ thể, người, vật, địa điểm, chi tiết sâu.
    - 'global': Hỏi về chủ đề chung, tóm tắt toàn bộ dữ liệu, xu hướng.
    Trả về JSON: {{"search_type": "local" | "global", "reason": "giải thích"}}<|eot_id|>
    <|start_header_id|>user<|end_header_id|>
    Câu hỏi người dùng: "{query}"<|message_end|>
    <|start_header_id|>assistant<|end_header_id|>
    """

    # Thực hiện inference
    outputs = llm.generate([prompt_template], sampling_params)
    
    # Xử lý kết quả trả về
    generated_text = outputs[0].outputs[0].text + "}" # Thêm lại dấu ngoặc do stop word
    
    try:
        # Làm sạch chuỗi nếu model trả về thừa ký tự
        start_idx = generated_text.find('{')
        end_idx = generated_text.rfind('}') + 1
        json_str = generated_text[start_idx:end_idx]
        
        decision = json.loads(json_str)
        return decision
    except Exception as e:
        print(f"Lỗi parse JSON: {e}. Raw: {generated_text}")
        return {"search_type": "local", "reason": "error fallback"}

# Ví dụ cách chạy indexing
async def main():
    # 0. Create folder contains everything of current timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_folder_name = f"outputs_{timestamp}"
    Path(new_folder_name).mkdir(parents=True, exist_ok=True)

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

    tuple_delimiter = "<|>"
    record_delimiter = " ## "
    completion_delimiter = "<|COMPLETE|>"

    # Đường dẫn model (vLLM hỗ trợ load trực tiếp từ HuggingFace hoặc thư mục local)
    model_path = "Qwen/Qwen2.5-7B-Instruct" # Hoặc bản 14B/32B tùy GPU của My


    # Gọi hàm xử lý
    entities_df, relationships_df, claims_df = extract_info_from_chunk(
        text_units = final_df,    
        folder_path = new_folder_name,
        model_path = model_path, 
        entity_types = ENTITY_TYPES,
        tuple_delimiter = tuple_delimiter,
        record_delimiter = record_delimiter,
        completion_delimiter = completion_delimiter
    )

    # 9. Lưu entities và relations sang pickle file
    with open(f'{new_folder_name}/entities.pkl', 'wb') as f:
        pickle.dump(entities_df, f)
    with open(f'{new_folder_name}/relationships.pkl', 'wb') as f:
        pickle.dump(relationships_df, f)
    with open(f'{new_folder_name}/claims.pkl', 'wb') as f:
        pickle.dump(claims_df, f)
    print("Lưu entities, relationships và claims thành công!")

    # 10. Encode các entities
    entity_embeddings_folder_name = f"{new_folder_name}/entity_embeddings"
    embedding_model_name="keepitreal/vietnamese-sbert"
    embed_model = SentenceTransformer(embedding_model_name)
    entity_name_embeddings = embed_model.encode(entities_df['name'].tolist(), show_progress_bar=True, convert_to_numpy=True)
    # 4. Lưu lại
    np.save(entity_embeddings_folder_name, entity_name_embeddings)
    logging.info(f"Đã lưu embeddings của entities tại: {entity_embeddings_folder_name}")




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
    result, hierarchy = _compute_leiden_communities(relationships_df, max_cluster_size=20, use_lcc=False)
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
    reports = asyncio.run(generate_hierarchical_community_reports(
        community_results=result,
        community_hierarchy=hierarchy,
        entities_df=entities_df,
        relationships_df=relationships_df,
        claims_df=claims_df,
        model_name=model_path,
        folder_for_debug=new_folder_name
    ))

    with open(f"{new_folder_name}/community_summaries.json", "w", encoding="utf-8") as f:
        json.dump(reports, f, ensure_ascii=False, indent=4)
    print("Extract community summaries thành công!")

    print(run_global_search("Nội dung chính của điều 182 của bộ luật Hình sự 2015 là gì?"))


@tool
def graphrag_retrieval(query: str) -> str:
    """Retrieves information using the GraphRAG system."""
    model_path = "Qwen/Qwen2.5-14B-Instruct" 
    graphrag_manager = LLM(model=model_path, tensor_parallel_size=1)
    result = route_graphrag_query(query, graphrag_manager)
    return result

    # print(f"Quyết định: {result['search_type'].upper()}")
    # print(f"Lý do: {result['reason']}")

    # # Tích hợp gọi GraphRAG
    # if result['search_type'] == "local":
    #     run_global_search(user_input)
    # else:
    #     run_global_search(user_input)
    
if __name__ == '__main__':
    asyncio.run(main())