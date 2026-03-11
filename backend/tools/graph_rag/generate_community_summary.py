import pandas as pd
import asyncio
from tqdm import tqdm
from vllm import LLM, SamplingParams
import json
import re
from transformers import AutoTokenizer

def generate_hierarchical_community_reports(
    community_results: dict,
    community_hierarchy: dict, 
    entities_df: pd.DataFrame,
    relationships_df: pd.DataFrame,
    claims_df: pd.DataFrame,
    model_name: str, # Tên model hoặc path
    folder_for_debug: str,
    max_new_tokens=2048,
    context_window=16384 # vLLM thường hỗ trợ context lớn hơn
):
    # 1. Khởi tạo vLLM và Tokenizer
    llm = LLM(model=model_name, gpu_memory_utilization=0.8, tensor_parallel_size=2, trust_remote_code=True)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    sampling_params = SamplingParams(
        temperature=0.1,
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
                    relevant_entities = entities_df[entities_df['name'].isin(nodes)].sort_values(by='degree', ascending=False)
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
                tokens = tokenizer.encode(input_text)
                if len(tokens) > (context_window - 1000):
                    input_text = tokenizer.decode(tokens[:context_window - 1000]) + "..."

                # --- CHUYỂN SANG CHAT TEMPLATE ---
                system_msg = f"""
Bạn là chuyên gia phân tích hệ thống pháp luật Việt Nam. Nhiệm vụ của bạn là trích xuất và đánh giá thông tin từ mạng lưới pháp luật (thực thể, quan hệ, quy định) để viết báo cáo cụm (community report).

### MỤC TIÊU
Hỗ trợ luật sư và người dân hiểu rõ tác động pháp lý. Báo cáo phải bao quát: thực thể chính, thẩm quyền, trách nhiệm, hành vi bị cấm và chế tài.

### QUY TẮC NỘI DUNG (BẮT BUỘC)
1. CHI TIẾT ĐỊNH LƯỢNG: Ghi rõ hành vi vi phạm, mức phạt cụ thể (số tiền, năm tù, thời gian đình chỉ), và cơ quan có thẩm quyền.
2. TÍNH ĐỘC LẬP: Tuyệt đối không dùng đại từ chỉ định (đây, đó, quy định ấy...). Phải lặp lại tên thực thể/nội dung cụ thể để mỗi câu đều có ý nghĩa độc lập.
3. KHÔNG BỊA ĐẶT: Chỉ sử dụng dữ liệu được cung cấp. Nếu dữ liệu nghèo nàn, hãy tập trung vào những gì chắc chắn nhất.

### QUY TẮC TRÍCH DẪN (GROUNDING)
- Mọi luận điểm phải đính kèm tham chiếu: "[Data: Thực thể (id1, id2); Quan hệ (id3, +more)]".
- Giới hạn tối đa 5 ID cho mỗi cụm trích dẫn.

### ĐỊNH DẠNG ĐẦU RA (JSON)
Bạn PHẢI trả về một khối JSON duy nhất với cấu trúc sau:
{{
    "title": "Tiêu đề cụ thể, ví dụ: Các quy định về tội danh tại Điều 182 Bộ luật Hình sự",
    "report": "Tổng hợp toàn bộ nội dung từ các nút dữ liệu",
    "rating": <số thực từ 0-10>,
    "rating_explanation": "Giải thích lý do cho điểm tác động này.",
    "findings": [
        {{
            "summary": "Tóm tắt phát hiện 1",
            "explanation": "Giải thích chi tiết kèm trích dẫn ID dữ liệu [Data: ...]"
        }}
    ]
}}

### LƯU Ý KỸ THUẬT:
- Chỉ trả về JSON. Không viết lời dẫn, không "Dưới đây là báo cáo...", không giải thích sau JSON.
- Không được ý bịa đặt thông tin. Dùng các thông tin được cho để tạo báo cáo cụm pháp lý hoàn chỉnh.
- Tổng độ dài báo cáo tối đa: {max_new_tokens} từ."""
                
                user_msg = f"""Viết báo cáo cho cụm thực thể sau đây. 
Yêu cầu bắt buộc: 
1. Chỉ trả về duy nhất 1 khối JSON.
2. Trích dẫn ID dữ liệu chuẩn xác [Data: Thực thể (id); Quan hệ (id)].
3. Nếu các thực thể có nội dung tương tự nhau, hãy gom nhóm chúng lại thành một phát hiện duy nhất mang tính tổng quát thay vì tách rời.

Dữ liệu thực tế:
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
                    # Tìm nội dung trong cặp ngoặc nhọn { }
                    match = re.search(r'\{.*\}', raw_output, re.DOTALL)
                    if match:
                        clean_json_str = match.group(0)
                        # Loại bỏ các ký tự điều khiển lỗi
                        clean_json_str = re.sub(r'[\x00-\x1F\x7F]', '', clean_json_str)
                        data_json = json.loads(clean_json_str)
                    else:
                        raise ValueError("No JSON found")
                except Exception as e:
                    print(f"Lỗi parse JSON tại cụm {cid}: {e}")
                    data_json = {"title": "Lỗi định dạng", "summary": raw_output, "rating": 0, "findings": []}

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