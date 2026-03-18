import pandas as pd
import asyncio
from tqdm import tqdm
from vllm import LLM, SamplingParams
import json
import re
from transformers import AutoTokenizer

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
    max_new_tokens=3072,
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
        print(f"--- Đang xử lý Level {current_level} ---")
        
        nodes_in_level = community_results[str(current_level) if isinstance(list(community_results.keys())[0], str) else current_level]
        clusters = {}
        for node, cid in nodes_in_level.items():
            if cid not in clusters: clusters[cid] = []
            clusters[cid].append(node)

        level_comms = list(clusters.items())
        
        # Với vLLM, chúng ta có thể xử lý toàn bộ Level trong 1 Batch nếu VRAM cho phép
        # Hoặc chia batch lớn (ví dụ 32-64)
        batch_size = 32
        
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
                        source_chunk_ids.update(relevant_entities['chunk_id'].dropna().unique())
                    if 'chunk_id' in relevant_rel.columns:
                        source_chunk_ids.update(relevant_rel['chunk_id'].dropna().unique())
                    if 'chunk_id' in relevant_claims.columns:
                        source_chunk_ids.update(relevant_claims['chunk_id'].dropna().unique())
                    
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
                    sub_comm_ids = [child for child, parent in community_hierarchy.items() if str(parent) == str(cid)]
                    
                    sub_reports_content = []
                    for scid in sub_comm_ids:
                        if int(scid) in report_cache:
                            # Lấy cả nội dung và chunk_ids từ cache
                            cached_content, cached_chunk_ids = report_cache[int(scid)]
                            sub_reports_content.append(cached_content)
                            source_chunk_ids.update(cached_chunk_ids)
                    
                    sub_reports_content.sort(key=len, reverse=True)
                    
                    input_text = f"BÁO CÁO TỔNG HỢP CHO CỤM CHA ID: {cid}\n\n"
                    input_text += "DỮ LIỆU TỪ CÁC CỤM CON:\n" + "\n---\n".join(sub_reports_content)

                # Kiểm soát Context Window
                safe_input_limit = 28000 
                tokens = tokenizer.encode(input_text)

                if len(tokens) > safe_input_limit:
                    full_prompt = tokenizer.decode(tokens[:safe_input_limit])
                    print(f"⚠️ Đã cắt bớt prompt cho cụm vì quá dài ({len(tokens)} tokens)")

                # --- CHUYỂN SANG CHAT TEMPLATE ---
                system_msg = f"""
Bạn là chuyên gia phân tích hệ thống pháp luật Việt Nam. Nhiệm vụ của bạn là trích xuất và đánh giá thông tin từ mạng lưới pháp luật (thực thể, quan hệ, quy định) để viết báo cáo cụm (community report)

### MỤC TIÊU
Hỗ trợ luật sư và người dân hiểu rõ tác động pháp lý. Báo cáo phải bao quát: thực thể chính, thẩm quyền, trách nhiệm, hành vi bị cấm và chế tài.

### QUY TẮC NỘI DUNG (BẮT BUỘC)
1. CHI TIẾT ĐỊNH LƯỢNG: Ghi rõ hành vi, mức phạt (tiền, năm tù), và cơ quan thẩm quyền.
2. TÍNH ĐỘC LẬP: Tuyệt đối không dùng đại từ (đây, đó, ấy). Phải lặp lại tên thực thể/nội dung cụ thể.
3. KHÔNG BỊA ĐẶT: Chỉ sử dụng dữ liệu được cung cấp. 
4. KIỂM SOÁT ĐỘ DÀI: Để tránh lỗi hệ thống, bạn PHẢI viết cực kỳ súc tích, dưới {max_new_tokens} từ, nhưng vẫn nên đảm bảo đủ ý.

### QUY TẮC TRÍCH DẪN
- Mọi ý phải kèm: "[Data: Thực thể (id1, id2); Quan hệ (id3)]". Tối đa 3 ID mỗi lần trích dẫn.

### ĐỊNH DẠNG ĐẦU RA (JSON DUY NHẤT)
Bạn PHẢI trả về JSON, không lời dẫn. Giới hạn số lượng mục như sau:
{{
    "title": "Tiêu đề ngắn gọn (< 15 từ) về nội dung của cụm",
    "report": "Tổng hợp thông tin của cụm từ các nguồn thông tin đã cho",
    "rating": <số từ 0-10>,
    "rating_explanation": "1 câu giải thích",
    "findings": [
        {{
            "summary": "Ý chính 1 (Tối đa 5 ý quan trọng nhất)",
            "explanation": "Chi tiết ý 1 trong tối đa 2 câu văn."
        }}
    ],
}}

### CẢNH BÁO KỸ THUẬT:
- CHỈ TRẢ VỀ JSON. Bắt đầu bằng '{{' và kết thúc bằng '}}'.
- Nếu dữ liệu quá lớn, chỉ chọn lọc 5 nội dung quan trọng nhất để trình bày. Tuyệt đối không viết lan man dẫn đến bị cắt ngang văn bản.
- Tổng độ dài mong muốn: dưới {max_new_tokens} từ."""
                
                user_msg = f"""Viết báo cáo cho cụm thực thể sau đây. 
{input_text}"""

                messages = [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg}
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
                            print(f"⚠️ Đã cứu thành công dữ liệu bị cắt tại cụm {cid}")
                    else:
                        raise ValueError("No JSON found")
                        
                except Exception as e:
                    print(f"❌ Lỗi parse JSON tại cụm {cid}: {e}")
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
