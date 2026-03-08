import pandas as pd
import asyncio
from unsloth import FastLanguageModel
from tqdm import tqdm
import json
import re


async def  generate_hierarchical_community_reports(
    community_results: dict, # Kết quả từ _compute_leiden_communities
    community_hierarchy: dict, # Mapping cha-con
    entities_df: pd.DataFrame,
    relationships_df: pd.DataFrame,
    client,
    model_name: str
):
    """
    Tạo báo cáo tóm tắt cho từng cộng đồng theo thứ tự phân cấp.
    """
    # 1. Cấu trúc lại dữ liệu để dễ truy vấn
    # Chuyển results thành danh sách phẳng các cộng đồng kèm danh sách nodes
    communities_list = []
    for level, nodes_map in community_results.items():
        # Gom nhóm nodes theo cluster_id trong mỗi level
        clusters = {}
        for node, cluster_id in nodes_map.items():
            if cluster_id not in clusters: clusters[cluster_id] = []
            clusters[cluster_id].append(node)
        
        for cluster_id, nodes in clusters.items():
            communities_list.append({
                "level": level,
                "community_id": cluster_id,
                "nodes": nodes,
                "parent_id": community_hierarchy.get(cluster_id, -1)
            })

    # 2. Sắp xếp Level từ cao nhất (chi tiết nhất) đến 0 (tổng quát nhất)
    # Ví dụ: [2, 1, 0]
    sorted_levels = sorted(community_results.keys(), reverse=True)
    
    final_reports = []
    report_cache = {} # Lưu report của con để làm input cho cha

    # Semaphore để giới hạn request song song (tránh timeout)
    semaphore = asyncio.Semaphore(10)

    async def summarize_single_community(comm):
        async with semaphore:
            level = comm['level']
            cid = comm['community_id']
            nodes = comm['nodes']
            
            # Xây dựng ngữ cảnh (Context)
            if level == max(sorted_levels):
                # LEVEL CHI TIẾT: Dùng mô tả thực thể gốc
                relevant_entities = entities_df[entities_df['name'].isin(nodes)]
                context = "DANH SÁCH ĐIỀU LUẬT & NỘI DUNG:\n"
                context += "\n".join([f"- {row['name']}: {row['description']}" for _, row in relevant_entities.iterrows()])
            else:
                # LEVEL TỔNG QUÁT: Dùng tóm tắt của các con thuộc cụm này
                sub_reports = [report_cache[n] for n in nodes if n in report_cache]
                context = "TÓM TẮT CÁC CỤM CON THUỘC NHÓM NÀY:\n"
                context += "\n---\n".join(list(set(sub_reports)))

            prompt = f"""
            Bạn là chuyên gia luật. Hãy viết báo cáo tóm tắt cho nhóm cộng đồng sau ở Level {level}.
            Nhiệm vụ:
            1. Xác định 'Thông điệp chính' (Main Messages) của toàn nhóm.
            2. Trích xuất các nghĩa vụ, quyền hạn hoặc hành vi bị cấm quan trọng.
            3. Nếu là tầng tổng quát, hãy kết nối các nội dung con thành một bức tranh hệ thống.
            
            Trả về định dạng:
            - Tiêu đề: [Chủ đề chính]
            - Tóm tắt: [Nội dung chi tiết]
            """

            try:
                response = await client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": f"Dữ liệu nguồn:\n{context}"}
                    ],
                    temperature=0
                )
                report = response.choices[0].message.content
                
                # Cập nhật cache cho tầng cha
                for node in nodes:
                    report_cache[node] = report
                
                return {
                    "level": level,
                    "community": cid,
                    "report": report,
                    "nodes": nodes
                }
            except Exception as e:
                print(f"Lỗi tại cụm {cid} level {level}: {e}")
                return None

    # Chạy tuần tự theo level để đảm bảo cha có report của con
    for current_level in sorted_levels:
        print(f"--- Đang tóm tắt Level {current_level} ---")
        level_comms = [c for c in communities_list if c['level'] == current_level]
        tasks = [summarize_single_community(c) for c in level_comms]
        level_results = await asyncio.gather(*tasks)
        final_reports.extend([r for r in level_results if r])

    return final_reports

async def generate_hierarchical_community_reports_unsloth(
    community_results: dict,
    community_hierarchy: dict, 
    entities_df: pd.DataFrame, # Cần có cột 'degree'
    relationships_df: pd.DataFrame, # Cần có cột 'rank' hoặc 'weight' (Combined Degree)
    model,
    tokenizer,
    max_new_tokens=2048,
    context_window=4096 
):
    # 1. Đảo ngược Level để chạy từ dưới (Lá) lên trên (Gốc)
    sorted_levels = sorted([int(k) for k in community_results.keys()], reverse=True)
    print(f"sorted_levels: {sorted_levels}")
    
    final_reports = []
    report_cache = {} 
    
    FastLanguageModel.for_inference(model)

    for current_level in sorted_levels:
        print(f"--- Đang xử lý Level {current_level} ---")
        
        nodes_in_level = community_results[current_level]
        clusters = {}
        for node, cid in nodes_in_level.items():
            if cid not in clusters: clusters[cid] = []
            clusters[cid].append(node)
        # print(f"clusters: {clusters}")

        level_comms = list(clusters.items())
        batch_size = 4 
        input_text = ""
        
        # Xử lý 1 batch gồm 4 cluster
        for i in tqdm(range(0, len(level_comms), batch_size), desc="Tổng hợp batch", unit="batch"):
            batch = level_comms[i : i + batch_size]
            prompts = []
            
            # Xử lý từng batch
            for cid, nodes in batch:
                # --- PHẦN LOGIC ƯU TIÊN THEO ĐỘ QUAN TRỌNG (DEGREE) ---
                # print(f"cid: {cid}")
                # print(f"nodes: {nodes}")
                
                if current_level == max(sorted_levels):
                    # A. Lọc và Sắp xếp Node theo Degree (Thực thể quan trọng nhất đứng đầu)
                    relevant_entities = entities_df[entities_df['name'].isin(nodes)].copy()
                    if 'degree' in relevant_entities.columns:
                        relevant_entities = relevant_entities.sort_values(by='degree', ascending=False)
                    
                    input_text = "THỰC THỂ (Ưu tiên theo độ quan trọng):\n"
                    input_text += "\n".join([
                        f"ID:{idx}, {r['name']}: {r['description']}" 
                        for idx, r in relevant_entities.iterrows()
                    ])
                    
                    # B. Lọc và Sắp xếp Edge theo Combined Degree (Quan hệ quan trọng nhất đứng đầu)
                    relevant_rel = relationships_df[relationships_df['source'].isin(nodes) | relationships_df['target'].isin(nodes)].copy()
                    
                    # Nếu bạn đã tính sẵn cột 'combined_degree' hoặc 'rank' trong lúc indexing
                    if 'rank' in relevant_rel.columns:
                        relevant_rel = relevant_rel.sort_values(by='rank', ascending=False)
                    elif 'weight' in relevant_rel.columns:
                        relevant_rel = relevant_rel.sort_values(by='weight', ascending=False)
                        
                    input_text += "\n\nQUAN HỆ (Sử dụng ID này để trích dẫn):\n"
                    input_text += "\n".join([f"ID:{idx}, {r['source']} -> {r['target']}: {r['description']}" for idx, r in relevant_rel.iterrows()])

                else:
                    # C. Đối với Level cha: Sắp xếp các cụm con theo độ lớn (Tokens)
                    sub_comm_ids = [child for child, parent in community_hierarchy.items() if str(parent) == str(cid)]
                    
                    # Lấy tóm tắt con và sắp xếp (Cụm con nào dài/quan trọng hơn đưa lên trước)
                    sub_reports = []
                    for scid in sub_comm_ids:
                        if int(scid) in report_cache:
                            sub_reports.append(report_cache[int(scid)])
                    
                    # Sắp xếp theo chiều dài văn bản (một cách proxy cho độ quan trọng ở level cao)
                    sub_reports.sort(key=len, reverse=True)
                    
                    input_text = "BÁO CÁO TÓM TẮT TỪ CÁC CỤM CON (Dữ liệu đã nén):\n"
                    input_text += "\n---\n".join(sub_reports)
                # print(f"input_text: {input_text}")

                # D. Kiểm soát Vali (Context Window): Cắt bỏ những phần ít quan trọng ở cuối danh sách
                tokens = tokenizer.encode(input_text)
                if len(tokens) > (context_window - 800):
                    # Chỉ lấy phần đầu (chứa các thực thể/quan hệ có Degree cao nhất đã được sort ở trên)
                    input_text = tokenizer.decode(tokens[:context_window - 800]) + "\n...(Đã lược bỏ các phần ít quan trọng hơn do vượt dung lượng)..."

                full_prompt =f"""
                    Bạn là một trợ lý AI chuyên gia về hệ thống pháp luật Việt Nam, giúp phân tích và khám phá thông tin trong các văn bản quy phạm pháp luật.
                    Nhiệm vụ của bạn là trích xuất và đánh giá các thông tin liên quan đến các thực thể (ví dụ: Cơ quan nhà nước, tổ chức, cá nhân) và các quy định trong mạng lưới pháp luật.

                    # Mục tiêu
                    Viết một báo cáo toàn diện về một "cụm pháp lý" (community), dựa trên danh sách các thực thể thuộc cụm đó cũng như các mối quan hệ và các tuyên bố (claims) liên quan. 
                    Báo cáo này sẽ được sử dụng để hỗ trợ các nhà hoạch định chính sách, luật sư hoặc người dân hiểu rõ về tác động và nội dung của các quy định. 
                    Nội dung báo cáo phải bao quát được: các thực thể chính, sự tuân thủ pháp lý, thẩm quyền, trách nhiệm, các hành vi bị cấm và các chế tài liên quan.

                    # Cấu trúc báo cáo

                    Báo cáo phải bao gồm các phần sau:

                    - TIÊU ĐỀ: Tên của cụm thực thể đại diện cho các nội dung chính - tiêu đề phải ngắn gọn nhưng cụ thể. Nếu có thể, hãy đưa tên các văn bản luật hoặc cơ quan chủ quản vào tiêu đề.
                    - TÓM TẮT: Bản tóm tắt điều hành về cấu trúc tổng thể của cụm pháp lý, cách các thực thể/điều khoản liên quan đến nhau và các điểm quan trọng nhất.
                    - ĐIỂM ĐÁNH GIÁ TÁC ĐỘNG (IMPACT SEVERITY RATING): Một điểm số thực từ 0-10 đại diện cho mức độ quan trọng hoặc tác động pháp lý của các thực thể/quy định trong cụm. (10 là mức độ quan trọng nhất, ví dụ: các quy định hiến pháp hoặc hình sự nghiêm trọng).
                    - GIẢI THÍCH ĐIỂM ĐÁNH GIÁ: Giải thích bằng một câu duy nhất về lý do đưa ra điểm số tác động đó.
                    - CÁC PHÁT HIỆN CHI TIẾT: Danh sách từ 5-10 thông tin chuyên sâu (insights) về cụm pháp lý. 
                        * QUAN TRỌNG: Chỉ trích xuất những thông tin thực sự có trong dữ liệu. Nếu dữ liệu nghèo nàn, bạn có thể viết ít hơn 5 phát hiện (nhưng tối thiểu phải có 2-3 nếu có thể).
                        * TÍNH DUY NHẤT: Mỗi phát hiện phải là một khía cạnh pháp lý khác biệt. Tuyệt đối không lặp lại nội dung đã viết ở các mục trước bằng cách thay đổi từ ngữ.
                        * CẤU TRÚC: Mỗi phát hiện cần có một phần tóm tắt ngắn, sau đó là đoạn văn giải thích chi tiết có trích dẫn ID dữ liệu chuẩn xác.

                    Trả về kết quả dưới dạng chuỗi định dạng JSON chuẩn như sau:
                        {{
                            "title": <tieu_de_bao_cao>,
                            "summary": <tom_tat_dieu_hanh>,
                            "rating": <diem_danh_gia_tac_dong>,
                            "rating_explanation": <giai_thich_diem_danh_gia>,
                            "findings": [
                                {{
                                    "summary": <tom_tat_phat_hien_1>,
                                    "explanation": <giai_thich_chi_tiet_phat_hien_1>
                                }},
                                {{
                                    "summary": <tom_tat_phat_hien_2>,
                                    "explanation": <giai_thich_chi_tiet_phat_hien_2>
                                }}
                            ]
                        }}

                    # Quy tắc trích dẫn (Grounding Rules)

                    Các luận điểm được hỗ trợ bởi dữ liệu phải liệt kê các tham chiếu dữ liệu như sau:

                    "Đây là một câu ví dụ được hỗ trợ bởi nhiều tham chiếu dữ liệu [Data: <tên bộ dữ liệu> (id bản ghi); <tên bộ dữ liệu> (id bản ghi)]."

                    Không liệt kê quá 5 ID bản ghi trong một tham chiếu đơn lẻ. Thay vào đó, hãy liệt kê 5 ID liên quan nhất và thêm "+more" để cho biết còn nhiều hơn thế.

                    Ví dụ:
                    "Cơ quan A có thẩm quyền xử phạt đối với hành vi vi phạm về thuế và chịu trách nhiệm trước Chính phủ [Data: Thực thể (5, 7); Quan hệ (23); Tuyên bố (7, 2, 34, 64, 46, +more)]."

                    Trong đó 1, 5, 7, 23, 2, 34, 46 và 64 đại diện cho ID (không phải index) của bản ghi dữ liệu liên quan.

                    Tuyệt đối không đưa vào các thông tin không có bằng chứng hỗ trợ từ dữ liệu đầu vào.

                    Giới hạn tổng độ dài báo cáo trong khoảng {max_new_tokens} từ.

                    # Dữ liệu thực tế

                    Sử dụng văn bản sau đây để trả lời. Không được tự ý bịa đặt thông tin.

                    Văn bản:
                    {input_text}

                    # YÊU CẦU QUAN TRỌNG: 
                    - Chỉ trả về duy nhất một khối JSON hợp lệ.
                    - Không cố gắng bịa thêm thông tin hoặc lặp lại các quy định giống nhau để làm dài danh sách findings.
                    - Không viết thêm lời chào, không viết phần lưu ý hoặc kết luận sau JSON.
                    - Nếu các thực thể có nội dung tương tự nhau, hãy gom nhóm chúng lại thành một phát hiện duy nhất mang tính tổng quát thay vì tách rời.
                    - Dừng lại ngay khi hết thông tin hữu ích.
                    - Dừng lại ngay sau khi đóng ngoặc nhọn }} của JSON.

                    Output:"""
                tokens = tokenizer.encode(full_prompt)
                print(f"Chiều dài thực tế của Prompt: {len(tokens)} tokens")
                prompts.append(full_prompt)

            # --- Thực thi LLM ---
            inputs = tokenizer(prompts, return_tensors="pt", padding=True).to("cuda")
            outputs = model.generate(
                input_ids = inputs.input_ids,
                attention_mask = inputs.attention_mask, # Truyền rõ ràng mask ở đây
                max_new_tokens = max_new_tokens,
                use_cache = True,
                temperature = 0.1,
                pad_token_id = tokenizer.pad_token_id
            )
            generated_texts = tokenizer.batch_decode(outputs, skip_special_tokens=True)
            
            for idx, (cid, nodes) in enumerate(batch):
                raw_output = generated_texts[idx]
                # Tạo tên file theo ID của cụm

                print(f"Printing raw_output to file...")
                filename = f"debug_output_cluster_{cid}.txt"
                # Tạo tên file theo ID của cụm
                filename = f"debug_output_cluster_{cid}.txt"
                
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(generated_texts[idx])
                    
                clean_json_str = ""
                try:
                    # Cách 1: Tìm vị trí sau chữ Output:
                    if "Output:" in raw_output:
                        text = raw_output.split("Output:", 1)[-1]
                        # print(f"text:{text}") # Removed for cleaner output

                    start_idx = text.find('{')

                    if start_idx != -1:
                        brace_level = 0
                        found_json_end = -1
                        for i in range(start_idx, len(text)):
                            if text[i] == '{':
                                brace_level += 1
                            elif text[i] == '}':
                                brace_level -= 1
                                if brace_level == 0:
                                    found_json_end = i
                                    break # Found the end of the first complete JSON object
                        
                        if found_json_end != -1:
                            clean_json_str = text[start_idx : found_json_end + 1]

                            # Escape unescaped newlines and tabs within the string to make it valid JSON
                            # This regex replaces newlines not preceded by a backslash with an escaped newline.
                            # This specifically targets newlines inside string values that cause 'Invalid control character' errors.
                            clean_json_str = re.sub(r'(?<!\\)\n', '', clean_json_str)
                            # Also handle tabs if they are unescaped
                            clean_json_str = re.sub(r'(?<!\\)\t', '', clean_json_str)

                        # print(f"DEBUG: String passed to json.loads (first 200 chars): {repr(clean_json_str[:200])}")
                        # return json.loads(clean_json_str)
                except Exception as e:
                    print(f"Không thể trích xuất JSON for : {e}")
                        # return json.loads(clean_json)
                # Tách phần trả lời của Assistant
                # raw_output = generated_texts[idx].split("assistant")[-1].strip()
                # # Tạo tên file theo ID của cụm
                # filename = f"debug_output_cluster_{cid}.txt"
                
                # with open(filename, "w", encoding="utf-8") as f:
                #     f.write(generated_texts[idx])
                
                # # Làm sạch chuỗi nếu AI trả về kèm markdown ```json ... ```
                # clean_json = raw_output.replace("```json", "").replace("```", "").strip()
                
                try:
                    # Chuyển đổi chuỗi text thành Dictionary theo đúng cấu trúc bạn mong muốn
                    data_json = json.loads(clean_json_str)
                    
                    # Lấy phần tóm tắt để làm nguyên liệu nén cho Level cha (cấp 0)
                    summary_for_next_level = data_json.get('summary', "")
                except Exception as e:
                    # Trường hợp AI không trả về JSON chuẩn, tạo một dict giả lập để không lỗi code
                    print(f"Lỗi Parse JSON tại cụm {cid}: {e}")
                    data_json = {
                        "title": "Lỗi định dạng",
                        "summary": raw_output, # Lưu tạm text thô vào đây
                        "rating": 0,
                        "rating_explanation": "Không thể parse JSON từ AI",
                        "findings": []
                    }
                    summary_for_next_level = raw_output

                # Lưu vào danh sách kết quả cuối cùng với đúng cấu trúc bạn yêu cầu
                final_reports.append({
                    "community_id": cid,
                    "level": current_level,
                    "report_detail": data_json, # Đây chính là cục JSON: title, summary, rating...
                    "nodes": nodes
                })
                
                # Lưu vào cache để Level 0 (Cha) sử dụng (Substitution logic)
                # Cấp cha sẽ đọc Summary của con để viết báo cáo tổng quát
                report_cache[cid] = summary_for_next_level

    return final_reports

def save_hierarchical_reports(reports, filename="hierarchical_reports.json"):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(reports, f, ensure_ascii=False, indent=4)
#     print(f"✅ Đã xuất {len(reports)} báo cáo cộng đồng vào {filename}")

def save_full_graph_context(result, hierarchy, filename="graph_context_old_prompt.json"):
    full_context = {
        "community_mapping": result, # {level: {node: cluster_id}}
        "community_hierarchy": hierarchy # {cluster_id: parent_id}
    }
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(full_context, f, ensure_ascii=False, indent=4)