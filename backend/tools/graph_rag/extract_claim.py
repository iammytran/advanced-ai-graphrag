
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


# Định nghĩa danh sách các loại thực thể phù hợp với Luật
# ENTITY_TYPES = "VĂN_BẢN_PHÁP_LUẬT, ĐIỀU_KHOẢN, CHỦ_THỂ, QUYỀN_HẠN, NGHĨA_VỤ, HÀNH_VI_VI_PHẠM, CHẾ_TÀI_PHÁP_LÝ, ĐIỀU_KIỆN_ÁP_DỤNG, THỜI_HẠN_THỜI_HIỆU, QUY_ĐỊNH_CỤ_THỂ"
ENTITY_TYPES = "VĂN_BẢN_PHÁP_LUẬT, ĐIỀU_KHOẢN, CHỦ_THỂ, QUY_ĐỊNH, HÀNH_VI, THỜI_HẠN"
tuple_delimiter="<|>"
completion_delimiter="<|COMPLETE|>"
record_delimiter="##"

def parse_claim_output(raw_text):
        claims = []
        # Tách theo record_delimiter (##)
        segments = raw_text.split(record_delimiter)
        for seg in segments:
            clean_seg = seg.strip().strip("()")
            if not clean_seg or completion_delimiter in clean_seg:
                continue
                
            parts = clean_seg.split(tuple_delimiter)
            # Một claim hợp lệ theo định dạng yêu cầu có 8 trường
            if len(parts) >= 8:
                claims.append({
                    "subject": parts[0].strip(),
                    "object": parts[1].strip(),
                    "type": parts[2].strip(),
                    "status": parts[3].strip(),
                    "start_date": parts[4].strip(),
                    "end_date": parts[5].strip(),
                    "description": parts[6].strip(),
                    "source_text": parts[7].strip()
                })
        return claims

def extract_claims(
    text_units: pd.DataFrame,
    model_path: str,          # Đường dẫn tới model (HuggingFace ID hoặc Local Path)
    entity_specs: str,
    claim_description: str,
    folder_name: str,
    record_delimiter: str = "##",
    tuple_delimiter: str = "<|>",
    completion_delimiter: str = "<|COMPLETE|>",
    gpu_memory_utilization: float = 0.8, # Giới hạn vRAM cho vLLM
    max_model_len: int = 8192,
    temperature: float = 0.1,
    max_tokens: int = 1500
):
    # 1. Khởi tạo vLLM engine
    llm = LLM(
        model=model_path,
        gpu_memory_utilization=gpu_memory_utilization,
        max_model_len=max_model_len,
        trust_remote_code=True
    )
    
    # Cấu hình tham số lấy mẫu (giống với config "kỷ luật thép" trước đó)
    sampling_params = SamplingParams(
        temperature=temperature,
        top_p=0.9,
        max_tokens=max_tokens,
        repetition_penalty=1.1,
        stop=[completion_delimiter] # vLLM sẽ dừng ngay khi gặp token này
    )

    all_claims = []

    # 2. Chuẩn bị danh sách prompts (vLLM xử lý batch cực tốt nên không cần chia nhỏ batch thủ công)
    prompts = []
    tokenizer = llm.get_tokenizer()

    for _, row in text_units.iterrows():
        text_content = str(row.get('chunk', '')).replace('\n', ' ').strip()
        
        messages = [
                {
                    "role": "system", 
                    "content": f"""
                    ### Hoạt động mục tiêu
                    Bạn là một trợ lý ảo thông minh hỗ trợ chuyên gia phân tích pháp lý rà soát các cáo buộc/hành vi vi phạm đối với các đối tượng cụ thể trong văn bản pháp luật hoặc hồ sơ vụ án.

                    ### Quy tắc trích xuất
                    Dựa trên văn bản được cung cấp, danh mục thực thể và mô tả loại hành vi, hãy trích xuất tất cả các thực thể khớp với mô tả và mọi cáo buộc/vi phạm liên quan đến thực thể đó.

                    ### Các bước thực hiện
                    1. Trích xuất thực thể: Tìm tất cả các thực thể có tên cụ thể khớp với danh mục được cung cấp (danh sách tên hoặc loại thực thể).
                    2. Trích xuất cáo buộc: Với mỗi thực thể tìm được, trích xuất tất cả các cáo buộc liên quan. Cáo buộc phải khớp với mô tả hành vi được yêu cầu và thực thể đó phải là "Chủ thể" thực hiện hành vi.
                        Với mỗi cáo buộc, trích xuất các thông tin sau:
                        - Chủ thể (Subject): Tên cá nhân/tổ chức thực hiện hành vi (VIẾT HOA). Phải là thực thể đã tìm thấy ở bước 1.
                        - Đối tượng liên quan (Object): Tên thực thể bị tác động hoặc cơ quan xử lý/báo cáo hành vi (VIẾT HOA). Nếu không rõ, dùng **NONE**.
                        - Loại hành vi (Claim Type): Danh mục vi phạm tổng quát (VIẾT HOA). Đặt tên sao cho có thể tái sử dụng cho các văn bản khác (ví dụ: THÔNG THẦU, TRỐN THUẾ, VI PHẠM QUY ĐỊNH ĐẤU THẦU).
                        - Trạng thái (Claim Status): **TRUE** (đã xác định/có kết luận), **FALSE** (đã bác bỏ), hoặc **SUSPECTED** (đang nghi vấn/chưa xác minh).
                        - Mô tả chi tiết (Claim Description): Mô tả kỹ lý lẽ pháp lý, tình tiết vi phạm và các bằng chứng/tham chiếu liên quan có trong văn bản.
                        - Thời điểm (Claim Date): Khoảng thời gian (Ngày bắt đầu, Ngày kết thúc) theo định dạng ISO-8601. Nếu chỉ có một mốc thời gian, dùng mốc đó cho cả hai. Nếu không rõ, dùng **NONE**.
                        - Trích dẫn (Claim Source Text): Danh sách **tất cả** các câu trích nguyên văn từ văn bản gốc có liên quan đến cáo buộc này.

                        ## Định dạng đầu ra:
                        (<subject_entity>{tuple_delimiter}<object_entity>{tuple_delimiter}<claim_type>{tuple_delimiter}<claim_status>{tuple_delimiter}<claim_start_date>{tuple_delimiter}<claim_end_date>{tuple_delimiter}<claim_description>{tuple_delimiter}<claim_source>)

                    3. Kết quả trả về bằng tiếng Việt, dưới dạng một danh sách duy nhất chứa tất cả các cáo buộc tìm thấy. Sử dụng **{record_delimiter}** để ngăn cách giữa các bản ghi.
                    4. Khi hoàn thành, kết thúc bằng **{completion_delimiter}**."""
                },
                {
                    "role": "user", 
                    "content": f"""### DANH MỤC THỰC THỂ CẦN RÀ SOÁT:
                        {entity_specs}

                        ### MÔ TẢ LOẠI HÀNH VI:
                        {claim_description}

                        ### VÍ DỤ MẪU:
                        Văn bản: "Ông Nguyễn Văn A đã nhận hối lộ 2 tỷ đồng vào tháng 5/2024."
                        Kết quả: (NGUYỄN VĂN A|NONE|NHẬN HỐI LỘ|TRUE|2024-05-01|2024-05-31|Nhận hối lộ số tiền 2 tỷ đồng.|"Ông Nguyễn Văn A đã nhận hối lộ 2 tỷ đồng")

                        ### VĂN BẢN PHÁP LÝ CẦN PHÂN TÍCH:
                        {text_content}"""
                }
            ]
        
        # Sử dụng chat template của tokenizer
        prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        prompts.append(prompt)

    # 3. Chạy Inference tập trung (vLLM tự tối ưu hóa throughput)
    print(f"Đang xử lý {len(prompts)} đoạn văn bản với vLLM...")
    outputs = llm.generate(prompts, sampling_params)

    # 4. Parse kết quả
    for output in outputs:
        generated_text = output.outputs[0].text
        claims = parse_claim_output(generated_text)
        all_claims.extend(claims)
    
    all_claims_df = pd.DataFrame(all_claims)
    return all_claims_df