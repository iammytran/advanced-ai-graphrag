import os

import pandas as pd
from vllm import SamplingParams

# Import prompt từ file config
from backend.config.prompts.prompt_extract_build_graph import EXTRACT_PROMPT
from backend.config.config import (
    VLLM_MODEL,
)

# Định nghĩa danh sách các loại thực thể phù hợp với Luật
# ENTITY_TYPES = "VĂN_BẢN_PHÁP_LUẬT, ĐIỀU_KHOẢN, CHỦ_THỂ, QUYỀN_HẠN, NGHĨA_VỤ, HÀNH_VI_VI_PHẠM, CHẾ_TÀI_PHÁP_LÝ, ĐIỀU_KIỆN_ÁP_DỤNG, THỜI_HẠN_THỜI_HIỆU, QUY_ĐỊNH_CỤ_THỂ"
ENTITY_TYPES = "VĂN_BẢN_PHÁP_LUẬT, ĐIỀU_KHOẢN, CHỦ_THỂ, QUY_ĐỊNH, HÀNH_VI, THỜI_HẠN"

tuple_delimiter="<|>"
completion_delimiter="<|COMPLETE|>"
record_delimiter="##"

def parse_graph_output(raw_text, chunk_id):
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
                    "description": parts[3].strip(),
                    "chunk_id": chunk_id 
                })
            elif "relationship" in tag and len(parts) >= 5:
                relationships.append({
                    "source": parts[1].strip(), 
                    "target": parts[2].strip(), 
                    "description": parts[3].strip(), 
                    "weight": float(parts[4].strip()) if parts[4].strip().replace('.','',1).isdigit() else 1.0,
                    "chunk_id": chunk_id
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
                    "source_text": parts[8].strip(),
                    "chunk_id": chunk_id
                })
        return entities, relationships, claims

def extract_info_from_chunk(text_units, folder_path, llm):    
    # 2. Cấu hình cho vLLM
    sampling_params = SamplingParams(
        temperature=0.1,
        top_p=0.9,
        max_tokens=2048, # max_new_tokens của bạn
        repetition_penalty=1.1,
        stop=[completion_delimiter, "<|im_end|>", "<|endoftext|>"]
    )

    all_prompts = []
    chunk_ids_for_prompts = [] # Store chunk_ids
    
    # 3. Chuẩn bị toàn bộ prompts (Không cần chia batch thủ công ở đây)
    for _, row in text_units.iterrows():
        doc_name = os.path.splitext(row.get('file_name', 'Văn bản gốc'))[0]
        text_content = str(row.get('chunk', '')).replace('\n', ' ').strip()

        messages = [
                {
                    "role": "system", 
                    "content": EXTRACT_PROMPT.format(
                        ENTITY_TYPES=ENTITY_TYPES,
                        doc_name=doc_name,
                        tuple_delimiter=tuple_delimiter,
                        record_delimiter=record_delimiter,
                        completion_delimiter=completion_delimiter
                    )
                },
                {
                    "role": "user", 
                    "content": f"Văn bản gốc: {doc_name}\nNội dung cần trích xuất: {text_content}\n\nOutput:"
                }
            ]
        
        # Sử dụng tokenizer của vLLM để apply template
        prompt = llm.get_tokenizer().apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        chunk_id = row.get('id', 'unknown')
        chunk_ids_for_prompts.append(chunk_id)
        all_prompts.append(prompt)

    # 4. Inference siêu tốc với vLLM
    print(f"Bắt đầu trích xuất {len(all_prompts)} văn bản với vLLM...")
    outputs = llm.generate(all_prompts, sampling_params, use_tqdm=True)

    all_entities = []
    all_relationships = []
    all_claims=[]

    # 5. Parse kết quả
    print("Bắt đầu phân tích kết quả...")
    for i, output in enumerate(outputs):
        actual_gen = output.outputs[0].text

        chunk_id = chunk_ids_for_prompts[i] # Get the corresponding chunk_id
        # print(f"\nCho dòng {i}, chunk_id is {chunk_id}")
        with open(f"{folder_path}/debug_extract_entities.log", "a", encoding="utf-8") as f:
            f.write(f"\nCho dòng {i}, chunk_id is {chunk_id}")
        prompt_sent = output.prompt # Lấy lại prompt đã gửi cho vLLM
        
        # Parse kết quả
        entities, relations, claims = parse_graph_output(actual_gen, chunk_id)
        all_entities.extend(entities)
        all_relationships.extend(relations)
        all_claims.extend(claims)

        debug_step = 10
        
        # UNCOMMENT CÁC DÒNG DƯỚI NÀY NẾU MUỐN XEM KẾT QUẢ CỦA EXTRACT ENTITIES
        # LOG DEBUG: Cứ mỗi 10 mẫu sẽ ghi log 1 lần
        # if i % debug_step == 0:
        #     with open(f"{folder_path}/debug_vllm_log.txt", "a", encoding="utf-8") as f:
        #         f.write("\n" + "="*50)
        #         f.write(f"\n--- DEBUG CỤM BẮT ĐẦU TỪ MẪU {i} ---")
        #         f.write(f"\n[PROMPT CỦA MẪU ĐẠI DIỆN]:\n{prompt_sent}")
        #         f.write("\n" + "-"*30)
        #         f.write(f"\n[OUTPUT CỦA MẪU ĐẠI DIỆN]:\n{actual_gen}")
        #         f.write("\n" + "-"*30)
                
        #         # Thống kê nhanh của mẫu hiện tại
        #         f.write(f"\n[THỐNG KÊ MẪU {i}]: {len(entities)} entities, {len(relations)} relations.")
                
        #         # Nếu muốn xem tổng tích lũy đến hiện tại
        #         f.write(f"\n[TỔNG TÍCH LŨY ĐẾN HIỆN TẠI]: {len(all_entities)} entities, {len(all_relationships)} relations.")
        #         f.write("\n" + "="*50 + "\n")

        # 1. Chuyển sang DataFrame
        df_entities = pd.DataFrame(all_entities)
        df_relationships = pd.DataFrame(all_relationships)
        df_claims = pd.DataFrame(all_claims)

        # 2. Xử lý trùng lặp (Quan trọng cho Knowledge Graph)
        if not df_entities.empty:
            df_entities = df_entities.drop_duplicates(subset=['name'], keep='first')
        
        if not df_relationships.empty:
            df_relationships = df_relationships.drop_duplicates(
                subset=['source', 'target', 'description'], keep='first'
        )
            
        if not df_claims.empty:
            df_claims = df_claims.drop_duplicates(
                subset=['subject', 'object', 'description'], keep='first'
        )

    return df_entities, df_relationships, df_claims

def get_llm():
    global _llm
    if _llm is None:
        with _lock:
            if _llm is None:
                # 1. Ép sử dụng kiến trúc V0 (Vô cùng quan trọng)
                os.environ["VLLM_USE_V1"] = "0"
                # 2. Đảm bảo biến môi trường chỉ định rõ 2 GPU
                os.environ["CUDA_VISIBLE_DEVICES"] = "0,1"
                from vllm import LLM
                # 3. Khởi tạo vLLM trên GPU 0
                _llm = LLM(
                    model=VLLM_MODEL,
                    tensor_parallel_size=num_gpus if num_gpus else 1,
                    gpu_memory_utilization=0.8,
                    trust_remote_code=True,
                    distributed_executor_backend="mp",
                    # max_model_len=4096,
                )
    return _llm

from threading import Lock
import torch
import pickle

_llm = None
_lock = Lock()
# Tự động lấy số GPU khả dụng
num_gpus = torch.cuda.device_count()

if __name__ == '__main__':
    
    final_df = None
    output_folder = "artifacts_v7"
    try:
        final_df = pd.read_json("dataset/chunking_result.json", orient="records")
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy file chunking_result.json trong {output_folder}. Vui lòng chạy lại bước chunking trước.")
    
    print("Ready for extracting entities and relationships...")

    # Gọi hàm xử lý
    entities_df, relationships_df, claims_df = extract_info_from_chunk(
        text_units = final_df,    
        folder_path = output_folder,
        llm=get_llm()
    )

    # 9. Lưu entities và relations sang pickle file
    with open(f'entities.pkl', 'wb') as f:
        pickle.dump(entities_df, f)
    with open(f'relationships.pkl', 'wb') as f:
        pickle.dump(relationships_df, f)
    with open(f'claims.pkl', 'wb') as f:
        pickle.dump(claims_df, f)
    print("Lưu entities, relationships và claims thành công!")

