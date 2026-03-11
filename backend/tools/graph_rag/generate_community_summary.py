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
    max_new_tokens=3072,
    context_window=32768 # vLLM thường hỗ trợ context lớn hơn
):
    # 1. Khởi tạo vLLM và Tokenizer
    llm = LLM(model=model_name, gpu_memory_utilization=0.7, tensor_parallel_size=2, trust_remote_code=True)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    sampling_params = SamplingParams(
        temperature=0,
        max_tokens=max_new_tokens,
        top_p=0.95
    )

    # 2. Đảo ngược Level để chạy từ dưới (Lá) lên trên (Gốc)
    sorted_levels = sorted([int(k) for k in community_results.keys()], reverse=True)
    
    final_reports = []
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

            for cid, nodes in batch:
                # --- LOGIC CHUẨN BỊ INPUT_TEXT (Giữ nguyên Idea cũ) ---
                if current_level == max(sorted_levels):
                    # Level Lá: Thực thể và Quan hệ
                    relevant_entities = entities_df[entities_df['name'].isin(nodes)]
                    input_text = "THỰC THỂ (Ưu tiên theo độ quan trọng):\n"
                    input_text += "\n".join([f"ID:{idx}, {r['name']}: {r['description']}" for idx, r in relevant_entities.iterrows()])
                    
                    relevant_rel = relationships_df[relationships_df['source'].isin(nodes) | relationships_df['target'].isin(nodes)]
                    sort_col = 'rank' if 'rank' in relevant_rel.columns else 'weight'
                    relevant_rel = relevant_rel.sort_values(by=sort_col, ascending=False)
                    
                    input_text += "\n\nQUAN HỆ:\n"
                    input_text += "\n".join([f"ID:{idx}, {r['source']} -> {r['target']}: {r['description']}" for idx, r in relevant_rel.iterrows()])

                    # 3. THÊM: Lấy Claims (Quy định chi tiết)
                    # Lọc các claim mà chủ thể hoặc đối tượng liên quan nằm trong cụm này
                    relevant_claims = claims_df[
                        claims_df['subject'].isin(nodes) | 
                        claims_df['object'].isin(nodes)
                    ]
                    
                    if not relevant_claims.empty:
                        input_text += "\n\n### 3. CHI TIẾT QUY ĐỊNH & CHẾ TÀI (CLAIMS):\n"
                        claim_entries = []
                        for idx, r in relevant_claims.iterrows():
                            # Tổng hợp thông tin từ description và source_text (câu trích dẫn)
                            entry = (f"ID:C{idx}, Chủ thể: {r['subject']}, Loại: {r['claim_type']}, "
                                     f"Trạng thái: {r['status']}\n"
                                     f"   - Nội dung: {r['description']}\n"
                                     f"   - Trích dẫn gốc: {r['source_text']}")
                            claim_entries.append(entry)
                        input_text += "\n".join(claim_entries)
                else:
                    # Level Cha: Tổng hợp từ Summary của con
                    sub_comm_ids = [child for child, parent in community_hierarchy.items() if str(parent) == str(cid)]
                    sub_reports = [report_cache[int(scid)] for scid in sub_comm_ids if int(scid) in report_cache]
                    sub_reports.sort(key=len, reverse=True)
                    input_text = "BÁO CÁO TÓM TẮT TỪ CÁC CỤM CON:\n" + "\n---\n".join(sub_reports)

                # Kiểm soát Context Window
                # Ví dụ trong vòng lặp chuẩn bị prompt
                safe_input_limit = 28000 # Chừa chỗ cho output
                tokens = tokenizer.encode(input_text)

                if len(tokens) > safe_input_limit:
                    # Nếu dài quá, ta cắt bớt phần Context (danh sách thực thể/quan hệ)
                    full_prompt = tokenizer.decode(tokens[:safe_input_limit])
                    print(f"⚠️ Đã cắt bớt prompt cho cụm vì quá dài ({len(tokens)} tokens)")

                # --- CHUYỂN SANG CHAT TEMPLATE ---
                system_msg = f"""
Bạn là chuyên gia phân tích hệ thống pháp luật Việt Nam. Nhiệm vụ: viết báo cáo cụm (community report) từ mạng lưới thực thể và quan hệ pháp lý.

### QUY TẮC NỘI DUNG (BẮT BUỘC)
1. CHI TIẾT ĐỊNH LƯỢNG: Ghi rõ hành vi, mức phạt (tiền, năm tù), và cơ quan thẩm quyền.
2. TÍNH ĐỘC LẬP: Tuyệt đối không dùng đại từ (đây, đó, ấy). Phải lặp lại tên thực thể/nội dung cụ thể.
3. KHÔNG BỊA ĐẶT: Chỉ sử dụng dữ liệu được cung cấp. 
4. KIỂM SOÁT ĐỘ DÀI: Để tránh lỗi hệ thống, bạn PHẢI viết cực kỳ súc tích.

### QUY TẮC TRÍCH DẪN
- Mọi ý phải kèm: "[Data: Thực thể (id1, id2); Quan hệ (id3)]". Tối đa 3 ID mỗi lần trích dẫn.

### ĐỊNH DẠNG ĐẦU RA (JSON DUY NHẤT)
Bạn PHẢI trả về JSON, không lời dẫn. Giới hạn số lượng mục như sau:
{{
    "title": "Tiêu đề ngắn gọn (< 15 từ) về nội dung của cụm",
    "report": "Tóm tắt tổng hợp thông tin của cụm từ các nguồn thông tin đã cho",
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

            # --- VLLM GENERATION ---
            outputs = llm.generate(prompts_to_generate, sampling_params)
            
            for idx, output in enumerate(outputs):
                cid = batch_cids[idx]
                nodes = batch_nodes[idx]
                raw_output = output.outputs[0].text
                
                # Debug file
                with open(f"{folder_for_debug}/debug_cluster_{cid}.txt", "w", encoding="utf-8") as f:
                    f.write(raw_output)

                # --- XỬ LÝ JSON ---
                try:
                    # 1. Tìm khối văn bản nghi vấn là JSON
                    match = re.search(r'\{.*', raw_output, re.DOTALL) # Tìm từ dấu { đến hết
                    if match:
                        potential_json = match.group(0)
                        
                        # 2. Loại bỏ ký tự điều khiển lỗi
                        potential_json = re.sub(r'[\x00-\x1F\x7F]', '', potential_json)
                        
                        # 3. THÊM BƯỚC REPAIR: Thử parse thẳng, nếu lỗi thì sửa rồi parse lại
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
                    # Nếu hỏng hẳn, My giữ lại raw_output để sau này vẫn xem được text thô
                    data_json = {
                        "title": f"Báo cáo cụm {cid} (Lỗi định dạng)", 
                        "report": raw_output[:500] + "...", # Lấy tạm text thô
                        "rating": 0, 
                        "findings": []
                    }

                final_reports.append({
                    "community_id": cid,
                    "level": current_level,
                    "report_detail": data_json,
                    "nodes": nodes
                })
                report_cache[cid] = data_json.get('summary', raw_output)

    return final_reports


# def save_full_graph_context(result, hierarchy, filename="graph_context_old_prompt.json"):
#     full_context = {
#         "community_mapping": result, # {level: {node: cluster_id}}
#         "community_hierarchy": hierarchy # {cluster_id: parent_id}
#     }
#     with open(filename, 'w', encoding='utf-8') as f:
#         json.dump(full_context, f, ensure_ascii=False, indent=4)