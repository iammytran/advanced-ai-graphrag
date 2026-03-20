import os
os.environ["PYTORCH_ALLOC_CONF"] = "expandable_segments:True"

import pandas as pd
import asyncio
from tqdm import tqdm
from vllm import LLM, SamplingParams
import json
import re
from transformers import AutoTokenizer
import logging

# Import prompt
from backend.config.prompts.prompt_generate_summary import GENERATE_SUMMARY_PROMPT

# --- Cấu hình Logging ---
# Tạo một logger riêng cho module này
logger = logging.getLogger(__name__)
logger.propagate = False
logger.setLevel(logging.DEBUG)  # Bắt tất cả các level từ DEBUG trở lên

# Tạo handler để ghi ra file
# 'w' để ghi đè file mỗi lần chạy, 'a' để ghi tiếp
file_handler = logging.FileHandler('debug_community_summary.log', mode='w', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)

# Tạo handler để in ra console
# console_handler = logging.StreamHandler()
# console_handler.setLevel(logging.INFO) # Chỉ in ra console những thông tin INFO trở lên

# Định dạng cho log message
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
# console_handler.setFormatter(formatter)

# Thêm handlers vào logger
# Tránh thêm handler nhiều lần nếu module được import lại
if not logger.handlers:
    logger.addHandler(file_handler)
    # logger.addHandler(console_handler)
# --- Kết thúc cấu hình Logging ---


def repair_truncated_json(json_str):
    """Cứu vãn chuỗi JSON bị cắt ngang bằng cách đóng các ngoặc còn thiếu"""
    json_str = json_str.strip()
    
    # Nếu rỗng thì chịu thua
    if not json_str: return None
    
    # Bổ sung dấu ngoặc kép nếu bị cắt ở giữa một chuỗi string
    # Quy tắc: nếu số dấu " là lẻ, nghĩa là đang viết dở string
    if json_str.count('"') % 2 != 0:
        json_str += '"'
    
    # Đóng các tầng ngoặc từ trong ra ngoài
    # Ta dùng stack hoặc đếm đơn giản:
    for bracket_open, bracket_close in [('{', '}'), ('[', ']')]:
        n_open = json_str.count(bracket_open)
        n_close = json_str.count(bracket_close)
        if n_open > n_close:
            json_str += bracket_close * (n_open - n_close)
            
    return json_str

def generate_hierarchical_community_reports(
    community_results: dict,
    community_hierarchy: dict, 
    entities_df: pd.DataFrame,
    relationships_df: pd.DataFrame,
    claims_df: pd.DataFrame,
    model_name: str, # Tên model hoặc path
    folder_for_debug: str,
    llm,
    max_new_tokens=15000,
    context_window=32768 # vLLM thường hỗ trợ context lớn hơn
):
    # 1. Khởi tạo Tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    sampling_params = SamplingParams(
        temperature=0,
        max_tokens=max_new_tokens,
        top_p=0.95
    )

    # 2. Đảo ngược Level để chạy từ dưới (Lá) lên trên (Gốc)
    sorted_levels = sorted([int(k) for k in community_results.keys()], reverse=True)
    
    final_reports = []
    # Cache sẽ lưu tuple: (nội dung tóm tắt, danh sách source_chunk_ids)
    report_cache = {} 

    for current_level in sorted_levels:
        logger.info(f"--- Đang xử lý Level {current_level} ---")
        
        nodes_in_level = community_results[str(current_level) if isinstance(list(community_results.keys())[0], str) else current_level]
        clusters = {}
        for node, cid in nodes_in_level.items():
            if cid not in clusters: clusters[cid] = []
            clusters[cid].append(node)

        level_comms = list(clusters.items())

        batch_size = 16
        
        for i in range(0, len(level_comms), batch_size):
            batch = level_comms[i : i + batch_size]
            prompts_to_generate = []
            batch_cids = []
            batch_nodes = []
            batch_chunk_ids = [] # Lưu chunk_ids cho batch

            for cid, nodes in batch:
                # --- LOGIC CHUẨN BỊ INPUT_TEXT ---
                source_chunk_ids = set()
                if current_level == max(sorted_levels):
                    # Level Lá: Lấy chunk_id trực tiếp từ các DataFrame
                    logger.debug(f"\n[Cụm lá ID: {cid} (Level {current_level})]")
                    relevant_entities = entities_df[entities_df['name'].isin(nodes)]
                    input_text = "THỰC THỂ (Ưu tiên theo độ quan trọng):\n"
                    input_text += "\n".join([f"ID:{idx}, {r['name']}: {r['description']}" for idx, r in relevant_entities.iterrows()])
                    
                    relevant_rel = relationships_df[relationships_df['source'].isin(nodes) | relationships_df['target'].isin(nodes)]
                    sort_col = 'rank' if 'rank' in relevant_rel.columns else 'weight'
                    relevant_rel = relevant_rel.sort_values(by=sort_col, ascending=False)
                    
                    input_text += "\n\nQUAN HỆ:\n"
                    input_text += "\n".join([f"ID:{idx}, {r['source']} -> {r['target']}: {r['description']}" for idx, r in relevant_rel.iterrows()])

                    relevant_claims = claims_df[
                        claims_df['subject'].isin(nodes) | 
                        claims_df['object'].isin(nodes)
                    ]

                    # Thu thập chunk_ids một cách an toàn
                    if 'chunk_id' in relevant_entities.columns:
                        entity_chunks = relevant_entities['chunk_id'].dropna().unique()
                        source_chunk_ids.update(entity_chunks)
                        logger.debug(f"  -> Tìm thấy {len(entity_chunks)} chunk_ids từ Entities.")
                    if 'chunk_id' in relevant_rel.columns:
                        rel_chunks = relevant_rel['chunk_id'].dropna().unique()
                        source_chunk_ids.update(rel_chunks)
                        logger.debug(f"  -> Tìm thấy {len(rel_chunks)} chunk_ids từ Relationships.")
                    if 'chunk_id' in relevant_claims.columns:
                        claim_chunks = relevant_claims['chunk_id'].dropna().unique()
                        source_chunk_ids.update(claim_chunks)
                        logger.debug(f"  -> Tìm thấy {len(claim_chunks)} chunk_ids từ Claims.")
                    
                    logger.debug(f"  -> Tổng số chunk_ids cho cụm lá {cid}: {len(source_chunk_ids)}. IDs: {source_chunk_ids}")

                    if not relevant_claims.empty:
                        input_text += "\n\n### 3. CHI TIẾT QUY ĐỊNH & CHẾ TÀI (CLAIMS):\n"
                        claim_entries = []
                        for idx, r in relevant_claims.iterrows():
                            entry = (f"ID:C{idx}, Chủ thể: {r['subject']}, Loại: {r['claim_type']}, "
                                     f"Trạng thái: {r['status']}\n"
                                     f"   - Nội dung: {r['description']}\n"
                                     f"   - Trích dẫn gốc: {r['source_text']}")
                            claim_entries.append(entry)
                        input_text += "\n".join(claim_entries)
                else:
                    # Level Cha: Tổng hợp từ Summary và chunk_ids của con
                    logger.debug(f"\n[Cụm cha ID: {cid} (Level {current_level})]")
                    sub_comm_ids = [child for child, parent in community_hierarchy.items() if str(parent) == str(cid)]
                    logger.debug(f"  -> Tìm thấy {len(sub_comm_ids)} cụm con: {sub_comm_ids}")
                    
                    sub_reports_content = []
                    for scid in sub_comm_ids:
                        if int(scid) in report_cache:
                            # Lấy cả nội dung và chunk_ids từ cache
                            cached_content, cached_chunk_ids = report_cache[int(scid)]
                            sub_reports_content.append(cached_content)
                            source_chunk_ids.update(cached_chunk_ids)
                            if cached_chunk_ids:
                                logger.debug(f"  -> Lấy được {len(cached_chunk_ids)} chunk_ids từ cache của con ID: {scid}")
                            else:
                                logger.warning(f"  -> !!! Cache của con ID: {scid} không có chunk_ids.")
                        else:
                            logger.warning(f"  -> !!! Không tìm thấy cache cho con ID: {scid}")
                    
                    sub_reports_content.sort(key=len, reverse=True)
                    
                    logger.debug(f"  -> Tổng số chunk_ids kế thừa cho cha {cid}: {len(source_chunk_ids)}. IDs: {source_chunk_ids}")
                    input_text = f"BÁO CÁO TỔNG HỢP CHO CỤM CHA ID: {cid}\n\n"
                    input_text += "DỮ LIỆU TỪ CÁC CỤM CON:\n" + "\n---\n".join(sub_reports_content)

                # Kiểm soát Context Window
                safe_input_limit = 28000 
                tokens = tokenizer.encode(input_text)

                if len(tokens) > safe_input_limit:
                    full_prompt = tokenizer.decode(tokens[:safe_input_limit])
                    logger.warning(f"⚠️ Đã cắt bớt prompt cho cụm vì quá dài ({len(tokens)} tokens)")


                messages = [
                    {"role": "system", "content": GENERATE_SUMMARY_PROMPT},
                    {"role": "user", "content": f"Viết báo cáo cho cụm thực thể sau đây. \n{input_text}"}
                ]
                
                full_prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                prompts_to_generate.append(full_prompt)
                batch_cids.append(cid)
                batch_nodes.append(nodes)
                batch_chunk_ids.append(list(source_chunk_ids)) 

            # --- VLLM GENERATION ---
            outputs = llm.generate(prompts_to_generate, sampling_params)
            
            for idx, output in enumerate(outputs):
                cid = batch_cids[idx]
                nodes = batch_nodes[idx]
                final_source_chunk_ids = batch_chunk_ids[idx] # Lấy chunk_ids cho mục này
                raw_output = output.outputs[0].text
                
                # --- XỬ LÝ JSON ---
                try:
                    match = re.search(r'\{.*', raw_output, re.DOTALL)
                    if match:
                        potential_json = match.group(0)
                        potential_json = re.sub(r'[\x00-\x1F\x7F]', '', potential_json)
                        try:
                            data_json = json.loads(potential_json)
                        except json.JSONDecodeError:
                            repaired_str = repair_truncated_json(potential_json)
                            data_json = json.loads(repaired_str)
                            logger.warning(f"⚠️ Đã cứu thành công dữ liệu bị cắt tại cụm {cid}")
                    else:
                        raise ValueError("No JSON found")
                        
                except Exception as e:
                    logger.error(f"❌ Lỗi parse JSON tại cụm {cid}: {e}")
                    data_json = {
                        "title": f"Báo cáo cụm {cid} (Lỗi định dạng)", 
                        "report": raw_output[:500] + "...",
                        "rating": 0, 
                        "findings": []
                    }

                final_reports.append({
                    "community_id": cid,
                    "level": current_level,
                    "source_chunk_ids": final_source_chunk_ids, # Thêm chunk_ids vào báo cáo cuối cùng
                    "report_detail": data_json,
                    "nodes": nodes
                })
                # Cache cả nội dung tóm tắt và chunk_ids để cấp cha sử dụng
                summary_content = data_json.get('report', raw_output) # Ưu tiên report, fallback về raw
                report_cache[cid] = (summary_content, final_source_chunk_ids)

    return final_reports
