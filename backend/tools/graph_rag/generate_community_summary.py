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

logger = logging.getLogger(__name__)


def _configure_summary_logger(folder_for_debug: str) -> logging.Logger:
    """Configure module logger to write debug log into the given output folder."""
    os.makedirs(folder_for_debug, exist_ok=True)
    logger.propagate = False
    logger.setLevel(logging.DEBUG)

    log_path = os.path.abspath(
        os.path.join(folder_for_debug, "debug_community_summary.log")
    )

    # Keep only the file handler for current output folder.
    for handler in list(logger.handlers):
        if isinstance(handler, logging.FileHandler):
            current_path = os.path.abspath(getattr(handler, "baseFilename", ""))
            if current_path != log_path:
                logger.removeHandler(handler)
                handler.close()

    has_target_handler = any(
        isinstance(handler, logging.FileHandler)
        and os.path.abspath(getattr(handler, "baseFilename", "")) == log_path
        for handler in logger.handlers
    )

    if not has_target_handler:
        file_handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


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


def _build_capped_prompt(tokenizer, input_text: str, context_window: int) -> str:
    """Build chat prompt and cap it to leave space for model output."""
    safety_margin = int(os.getenv("SUMMARY_PROMPT_SAFETY_MARGIN", "256"))
    reserved_output_tokens = int(os.getenv("SUMMARY_RESERVED_OUTPUT_TOKENS", "2048"))
    max_prompt_tokens = max(1024, context_window - reserved_output_tokens - safety_margin)

    messages = [
        {"role": "system", "content": GENERATE_SUMMARY_PROMPT},
        {"role": "user", "content": f"Viết báo cáo cho cụm thực thể sau đây.\n{input_text}"},
    ]
    full_prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    prompt_tokens = len(tokenizer.encode(full_prompt))

    while prompt_tokens > max_prompt_tokens and len(input_text) > 0:
        trim_ratio = max_prompt_tokens / prompt_tokens
        new_len = int(len(input_text) * max(0.6, min(0.95, trim_ratio)))
        if new_len >= len(input_text):
            new_len = len(input_text) - 1
        input_text = input_text[:max(0, new_len)]
        messages[1]["content"] = f"Viết báo cáo cho cụm thực thể sau đây.\n{input_text}"
        full_prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        prompt_tokens = len(tokenizer.encode(full_prompt))

    if prompt_tokens > max_prompt_tokens:
        logger.warning(
            f"⚠️ Prompt vẫn dài ({prompt_tokens}), ép cắt token còn {max_prompt_tokens}."
        )
        prompt_ids = tokenizer.encode(full_prompt)[:max_prompt_tokens]
        full_prompt = tokenizer.decode(prompt_ids, skip_special_tokens=True)

    return full_prompt


def _continue_if_truncated(llm, sampling_params, raw_output: str, finish_reason: str | None) -> str:
    """If model stopped due to token limit, ask it to continue a few rounds."""
    if finish_reason != "length":
        return raw_output

    if os.getenv("SUMMARY_CONTINUE_ON_TRUNCATION", "1") != "1":
        return raw_output

    max_rounds = int(os.getenv("SUMMARY_MAX_CONTINUATION_ROUNDS", "2"))
    tail_chars = int(os.getenv("SUMMARY_CONTINUATION_TAIL_CHARS", "5000"))
    combined = raw_output

    for round_idx in range(max_rounds):
        tail = combined[-tail_chars:]
        continuation_prompt = (
            "Bạn đang viết dở báo cáo JSON vì hết token. "
            "Hãy tiếp tục NGAY SAU phần cuối dưới đây, không lặp lại nội dung đã viết, "
            "không bắt đầu lại từ đầu.\n\n"
            f"PHẦN CUỐI HIỆN CÓ:\n{tail}\n\n"
            "Hãy tiếp tục chính xác phần còn thiếu:"
        )
        continuation_output = llm.generate([continuation_prompt], sampling_params)[0].outputs[0]
        continuation_text = continuation_output.text
        if not continuation_text.strip():
            break
        combined += continuation_text
        next_finish_reason = getattr(continuation_output, "finish_reason", None)
        if next_finish_reason != "length":
            break
        logger.warning(f"⚠️ Summary vẫn bị cắt, tiếp tục round {round_idx + 1}/{max_rounds}")

    return combined

def generate_hierarchical_community_reports(
    community_results: dict,
    community_hierarchy: dict, 
    entities_df: pd.DataFrame,
    relationships_df: pd.DataFrame,
    claims_df: pd.DataFrame,
    model_name: str, # Tên model hoặc path
    llm,
    folder_for_debug,
    max_new_tokens=15000,
    context_window=32768 # vLLM thường hỗ trợ context lớn hơn
):
    logger = _configure_summary_logger(folder_for_debug)
    # DEBUG: In ra các cột của DataFrame để kiểm tra sự tồn tại của 'chunk_id'
    logger.info(f"Các cột trong entities_df: {entities_df.columns.tolist()}")
    logger.info(f"Các cột trong relationships_df: {relationships_df.columns.tolist()}")
    logger.info(f"Các cột trong claims_df: {claims_df.columns.tolist()}")
    
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

                    input_text = ""
                    relevant_claims = claims_df[
                        claims_df['subject'].isin(nodes) | 
                        claims_df['object'].isin(nodes)
                    ]

                    if not relevant_claims.empty:
                        input_text += "\n\n### 1. CHI TIẾT QUY ĐỊNH:\n"
                        claim_entries = []
                        for idx, r in relevant_claims.iterrows():
                            entry = (f"ID:C{idx}, Chủ thể: {r['subject']}, Loại: {r['claim_type']}, "
                                     f"   - Nội dung: {r['description']}\n"
                                     f"   - Trích dẫn gốc: {r['source_text']}")
                            claim_entries.append(entry)
                        input_text += "\n".join(claim_entries)

                    relevant_rel = relationships_df[relationships_df['source'].isin(nodes) | relationships_df['target'].isin(nodes)]
                    sort_col = 'rank' if 'rank' in relevant_rel.columns else 'weight'
                    relevant_rel = relevant_rel.sort_values(by=sort_col, ascending=False)
                    
                    input_text += "\n\n ### 2. QUAN HỆ:\n"
                    input_text += "\n".join([f"ID:{idx}, {r['source']} có quan hệ với {r['target']} với mô tả: {r['description']}" for idx, r in relevant_rel.iterrows()])

                    relevant_entities = entities_df[entities_df['name'].isin(nodes)]
                    input_text += "\n\n### 3. THỰC THỂ:\n"
                    input_text += "\n".join([f"ID:{idx}, {r['name']} với mô tả: {r['description']}" for idx, r in relevant_entities.iterrows()])
                    
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

                full_prompt = _build_capped_prompt(tokenizer, input_text, context_window)
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
                first_output = output.outputs[0]
                raw_output = first_output.text
                finish_reason = getattr(first_output, "finish_reason", None)
                raw_output = _continue_if_truncated(llm, sampling_params, raw_output, finish_reason)
                
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