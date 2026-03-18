import os

import pandas as pd
from vllm import SamplingParams

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

def extract_info_from_chunk(text_units, folder_path, model_path, llm):    
    # 2. Cấu hình "Kỷ luật thép" cho vLLM
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
                    "content": f"""Bạn là chuyên gia phân tích dữ liệu pháp luật. Hãy trích xuất các thực thể và mối quan hệ từ văn bản luật được cung cấp để xây dựng một đồ thị tri thức (Knowledge Graph) chính xác và có tính liên kết cao.

                        ## QUY TẮC TRÍCH XUẤT THỰC THỂ (ENTITIES)
                            Trích xuất mọi thực thể quan trọng thuộc danh mục: [{ENTITY_TYPES}].
                            Cho phần này hãy trả về:
                                + Tên thực thể (entity_name): VIẾT HOA TOÀN BỘ.
                                + Loại thực thể (entity_type): 1 trong những lọai sau:[{ENTITY_TYPES}]
                                + Mô tả (entity_description): Mô tả chi tiết về chức năng, quyền hạn, nghĩa vụ hoặc nội dung quy định của thực thể đó trong ngữ cảnh văn bản. Tuyệt đối không sử dụng các đại từ chỉ định hoặc từ thay thế (như: đây, đó, này, họ, nó, quy định ấy...). Thay vào đó, phải lặp lại chính xác tên thực thể hoặc nội dung cụ thể để đảm bảo mỗi mô tả đều có ý nghĩa độc lập.

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
                                + Thực thể: ("entity"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_type>{tuple_delimiter}<entity_description>) {record_delimiter}
                                + Quan hệ: ("relationship"{tuple_delimiter}<source_entity>{tuple_delimiter}<target_entity>{tuple_delimiter}<relationship_description>{tuple_delimiter}<relationship_strength>) {record_delimiter}
                                + Quy định: ("claim"{tuple_delimiter}<subject_entity>{tuple_delimiter}<object_entity>{tuple_delimiter}<claim_type>{tuple_delimiter}<claim_status>{tuple_delimiter}<claim_start_date>{tuple_delimiter}<claim_end_date>{tuple_delimiter}<claim_description>{tuple_delimiter}<claim_source>) {record_delimiter}
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
        chunk_ids_for_prompts.append(row.get('id', 'unknown'))
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
        prompt_sent = output.prompt # Lấy lại prompt đã gửi cho vLLM
        
        # Parse kết quả
        entities, relations, claims = parse_graph_output(actual_gen, chunk_id)
        all_entities.extend(entities)
        all_relationships.extend(relations)
        all_claims.extend(claims)

        debug_step = 10
        
        # LOG DEBUG: Cứ mỗi 10 mẫu sẽ ghi log 1 lần
        if i % debug_step == 0:
            with open(f"{folder_path}/debug_vllm_log.txt", "a", encoding="utf-8") as f:
                f.write("\n" + "="*50)
                f.write(f"\n--- DEBUG CỤM BẮT ĐẦU TỪ MẪU {i} ---")
                f.write(f"\n[PROMPT CỦA MẪU ĐẠI DIỆN]:\n{prompt_sent}")
                f.write("\n" + "-"*30)
                f.write(f"\n[OUTPUT CỦA MẪU ĐẠI DIỆN]:\n{actual_gen}")
                f.write("\n" + "-"*30)
                
                # Thống kê nhanh của mẫu hiện tại
                f.write(f"\n[THỐNG KÊ MẪU {i}]: {len(entities)} entities, {len(relations)} relations.")
                
                # Nếu muốn xem tổng tích lũy đến hiện tại
                f.write(f"\n[TỔNG TÍCH LŨY ĐẾN HIỆN TẠI]: {len(all_entities)} entities, {len(all_relationships)} relations.")
                f.write("\n" + "="*50 + "\n")

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
