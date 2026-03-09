import json
import random
import asyncio
import pandas as pd
from tqdm import tqdm
from unsloth import FastLanguageModel
from transformers import AutoTokenizer
import logging
import warnings
from datetime import datetime

# Ẩn các cảnh báo tương lai (FutureWarnings)
warnings.filterwarnings("ignore", category=FutureWarning)

# Giảm mức độ log của transformers xuống chỉ hiện lỗi (ERROR) thay vì cảnh báo (WARNING)
logging.getLogger("transformers").setLevel(logging.ERROR)

def prepare_global_context(query, level, community_reports, tokenizer, context_window=6000):
    """
    Chuẩn bị ngữ cảnh cho Global Search từ các báo cáo cộng đồng.
    """
    # 1. Lọc báo cáo theo đúng level yêu cầu
    # reports = [r for r in community_reports if r['level'] == level]
    # if not reports:
    #     print(f"--- Cảnh báo: Không tìm thấy báo cáo nào ở Level {level} ---")
    #     return []
    reports = community_reports

    # 2. Xáo trộn ngẫu nhiên (chuẩn Paper GraphRAG)
    random.shuffle(reports)

    chunks = []
    current_chunk = ""
    
    # Để an toàn, chúng ta dành ra 500 tokens cho Prompt template và Query
    safe_limit = context_window - 500 

    for r in reports:
        detail = r['report_detail']
        
        # Gộp tóm tắt và các phát hiện chi tiết để không mất thông tin luật
        findings_text = "\n".join([f"- {f['summary']}" for f in detail.get('findings', [])])
        
        report_text = (
            f"\n\n### BÁO CÁO ID: {r['community_id']}\n"
            f"Tiêu đề: {detail['title']}\n"
            f"Điểm quan trọng (0-10): {detail.get('rating', 5)}\n"
            f"Tóm tắt: {detail['summary']}\n"
            f"Các phát hiện chính:\n{findings_text}\n"
            f"---"
        )
        
        # Kiểm tra độ dài token
        # Lưu ý: encode() tốn tài nguyên, nếu số lượng report lớn có thể tối ưu bằng cách ước lượng
        current_total_tokens = len(tokenizer.encode(current_chunk + report_text))
        
        if current_total_tokens < safe_limit:
            current_chunk += report_text
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = report_text
            
    # Thêm chunk cuối cùng
    if current_chunk: 
        chunks.append(current_chunk.strip())
        
    print(f"--- Đã chia {len(reports)} báo cáo Level {level} thành {len(chunks)} chunks ---")
    return chunks

async def run_map_step(query, chunks, model, tokenizer, max_new_tokens=1024):
    intermediate_results = []
    
    for i, chunk in enumerate(tqdm(chunks, desc="Giai đoạn Map (Phân tích)")):
        map_prompt = f"""
---Vai trò---

Bạn là một chuyên gia phân tích pháp luật và trợ lý AI thông minh. Nhiệm vụ của bạn là trả lời các câu hỏi dựa trên dữ liệu từ các bảng báo cáo cộng đồng pháp lý được cung cấp.

---Mục tiêu---

Tạo một câu trả lời bao gồm danh sách các điểm chính (key points) để trả lời câu hỏi của người dùng, tóm tắt tất cả các thông tin có liên quan trong các bảng dữ liệu đầu vào.

Bạn phải sử dụng dữ liệu được cung cấp trong các bảng dưới đây làm ngữ cảnh chính để tạo câu trả lời. 
Nếu bạn không biết câu trả lời hoặc nếu dữ liệu đầu vào không chứa đủ thông tin, hãy trả lời là bạn không đủ dữ liệu. Tuyệt đối không tự bịa đặt thông tin.

Mỗi điểm chính trong câu trả lời phải bao gồm các thành phần sau:
- Description (Mô tả): Một bản mô tả toàn diện về luận điểm pháp lý hoặc thông tin trích xuất được.
- Importance Score (Điểm quan trọng): Một số nguyên từ 0-100 thể hiện mức độ hữu ích của điểm đó trong việc trả lời câu hỏi. Câu trả lời kiểu "Tôi không biết" phải có điểm là 0.

Câu trả lời phải được định dạng JSON như sau:
{{
    "points": [
        {{"description": "Mô tả về luận điểm 1 [Data: Báo cáo (id báo cáo)]", "score": giá_trị_điểm}},
        {{"description": "Mô tả về luận điểm 2 [Data: Báo cáo (id báo cáo)]", "score": giá_trị_điểm}}
    ]
}}

---Yêu cầu về ngôn ngữ pháp lý---

1. Phải giữ nguyên ý nghĩa gốc và sử dụng chính xác các trợ động từ tình thái trong văn bản luật như: "phải", "được", "có thể", "không được", "chịu trách nhiệm".
2. Các luận điểm được hỗ trợ bởi dữ liệu phải liệt kê các tham chiếu báo cáo như sau:
"Đây là một câu ví dụ về quy định pháp luật được hỗ trợ bởi dữ liệu [Data: Báo cáo (id báo cáo)]"

**Không liệt kê quá 5 ID bản ghi trong một tham chiếu đơn lẻ**. Thay vào đó, hãy liệt kê 5 ID liên quan nhất và thêm "+more" để cho biết còn nhiều hơn thế.

Ví dụ:
"Cơ quan A có thẩm quyền xử phạt đối với hành vi vi phạm về thuế và chịu trách nhiệm trước Chính phủ [Data: Báo cáo (2, 7, 64, 46, 34, +more)]. Cơ quan này cũng có trách nhiệm báo cáo định kỳ cho Bộ Tài chính [Data: Báo cáo (1, 3)]"

Trong đó 1, 2, 3, 7, 34, 46, và 64 đại diện cho ID (không phải index) của báo cáo dữ liệu tương ứng trong bảng được cung cấp.

3. Tuyệt đối không đưa vào thông tin nếu không có bằng chứng hỗ trợ từ dữ liệu nguồn.
4. Giới hạn độ dài câu trả lời trong khoảng {max_new_tokens} từ.

---Bảng dữ liệu ngữ cảnh---

{chunk}

---Câu hỏi của người dùng---

{query}
"""

        inputs = tokenizer([map_prompt], return_tensors="pt").to("cuda")
        outputs = model.generate(**inputs, max_new_tokens=max_new_tokens, temperature=0.1)
        res_raw = tokenizer.batch_decode(outputs, skip_special_tokens=True)[0].split("assistant")[-1].strip()

        try:
            clean_json = res_raw.replace("```json", "").replace("```", "").strip()
            res_json = json.loads(clean_json)
            if res_json.get('score', 0) > 0:
                intermediate_results.append(res_json)
        except:
            continue
            
    return intermediate_results

async def run_reduce_step(query, map_results, model, tokenizer, max_new_tokens=1024):
    # Sắp xếp theo score giảm dần
    sorted_results = sorted(map_results, key=lambda x: x['score'], reverse=True)
    response_type="multiple paragraphs"

    # Lấy Top 10 câu trả lời hữu ích nhất làm ngữ cảnh
    top_results = sorted_results[:10]

    if len(top_results) == 0:
        final_context = "KHÔNG CÓ DỮ LIỆU PHÂN TÍCH PHÙ HỢP."
    else:
        # Thêm số thứ tự và tổng số lượng để AI biết ngữ cảnh đang dày hay mỏng
        final_context = f"TỔNG HỢP CÓ {len(top_results)} LUẬN ĐIỂM QUAN TRỌNG:\n\n"
        final_context += "\n---\n".join([
            f"LUẬN ĐIỂM {i+1}:\n{r['description']}" 
            for i, r in enumerate(top_results)
        ])

    reduce_prompt = f"""
---Vai trò---

Bạn là một chuyên gia pháp lý cao cấp hoặc Thẩm phán có kinh nghiệm. Nhiệm vụ của bạn là tổng hợp các báo cáo phân tích từ nhiều nguồn dữ liệu khác nhau để đưa ra câu trả lời cuối cùng, thống nhất và toàn diện cho người dùng.

---Mục tiêu---

Tạo một văn bản trả lời với độ dài và định dạng yêu cầu để giải đáp câu hỏi của người dùng. Bạn cần tổng hợp các báo cáo từ nhiều phân tích viên vốn tập trung vào các phần khác nhau của bộ dữ liệu pháp luật.

Lưu ý rằng các báo cáo phân tích dưới đây đã được sắp xếp theo **thứ tự tầm quan trọng giảm dần**.

Nếu bạn không thể tìm thấy câu trả lời hoặc nếu các báo cáo được cung cấp không chứa đủ thông tin, hãy trả lời rõ là dữ liệu hiện tại không đủ để giải đáp. Tuyệt đối không tự ý bịa đặt quy định pháp luật.

Câu trả lời cuối cùng cần:
1. Loại bỏ tất cả các thông tin không liên quan từ các báo cáo thành phần.
2. Hợp nhất các thông tin đã được làm sạch thành một câu trả lời chặt chẽ, có giải thích đầy đủ các điểm chính và hệ quả pháp lý phù hợp với định dạng yêu cầu.
3. Chia các phần (sections) và thêm các lời bình luận, dẫn dắt phù hợp để văn bản có cấu trúc logic.
4. Trình bày nội dung bằng định dạng Markdown.

---Yêu cầu về ngôn ngữ pháp lý---

1. Phải giữ nguyên ý nghĩa gốc và sử dụng chính xác các trợ động từ tình thái chuyên dụng trong văn bản luật như: "phải", "được", "có thể", "không được", "chịu trách nhiệm".
2. Giữ lại tất cả các tham chiếu dữ liệu (Data references) đã có trong các báo cáo thành phần, nhưng **không được nhắc đến vai trò của các phân tích viên** hay quá trình tổng hợp trong văn bản cuối cùng.

**Quy tắc trích dẫn:**
- Không liệt kê quá 5 ID bản ghi trong một tham chiếu đơn lẻ. Hãy liệt kê 5 ID liên quan nhất và thêm "+more" nếu còn nhiều hơn.
- Ví dụ: "Hành vi X bị coi là vi phạm quy định về quản lý kinh tế và có thể bị truy cứu trách nhiệm hình sự [Data: Báo cáo (2, 7, 34, 46, 64, +more)]. Hình phạt bổ sung có thể bao gồm cấm đảm nhiệm chức vụ [Data: Báo cáo (1, 3)]".
- Trong đó 1, 2, 3, 7, 34, 46, và 64 đại diện cho ID của báo cáo dữ liệu tương ứng.

3. Tuyệt đối không đưa vào các thông tin không có bằng chứng hỗ trợ từ dữ liệu nguồn.
4. Giới hạn tổng độ dài câu trả lời trong khoảng {max_new_tokens} từ.

---Định dạng và độ dài yêu cầu---

{response_type}

---Danh sách các báo cáo phân tích nguồn---

{final_context}

---Câu hỏi của người dùng---

{query}
"""
    inputs = tokenizer([reduce_prompt], return_tensors="pt").to("cuda")
    outputs = model.generate(**inputs, max_new_tokens=2048, temperature=0.3)
    return tokenizer.batch_decode(outputs, skip_special_tokens=True)[0].split("assistant")[-1].strip()

async def global_query_unsloth(query, level, community_reports, model, tokenizer):
    FastLanguageModel.for_inference(model)
    
    # Bước 1: Prepare
    chunks = prepare_global_context(query, level, community_reports, tokenizer)
    if not chunks:
        return "Không tìm thấy dữ liệu ở level này."
    
    # Bước 2: Map
    map_results = await run_map_step(query, chunks, model, tokenizer)
    if not map_results:
        return "Không tìm thấy thông tin liên quan."
        
    # Bước 3: Reduce
    final_answer = await run_reduce_step(query, map_results, model, tokenizer)
    
    return final_answer

if __name__ == '__main__':
    model_name = "unsloth/meta-llama-3.1-8b-instruct-bnb-4bit"
    max_seq_length = 14000 # Tăng lên 8k để chứa đủ context tóm tắt phân cấp
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name = model_name,
        max_seq_length = max_seq_length,
        load_in_4bit = True, # Giúp chạy nhanh và tiết kiệm VRAM
    )

    # Đừng quên cấu hình padding side cho Batch Inference nếu cần
    tokenizer.padding_side = "left"

    data = None
    file_path = 'community_reports_2026-03-06_00-06-07.json'
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        chunks = prepare_global_context("", 2, data, tokenizer)
        print(len(chunks))
        print(chunks[0])
        # # Bây giờ 'data' là một Python Dictionary (hoặc List)
        # print(data['title']) # Truy cập thử một key
    except FileNotFoundError:
        print("Không tìm thấy file!")
    except json.JSONDecodeError:
        print("File không đúng định dạng JSON!")

    # Bước 2: Map
    query = "Nội dung chính của điều 182 của bộ luật Hình sự 2015 là gì?"
    map_results = asyncio.run(run_map_step(query, chunks, model, tokenizer))
    if not map_results:
        print("Không tìm thấy thông tin liên quan.")
        
    # Bước 3: Reduce
    final_answer = asyncio.run(run_reduce_step(query, map_results, model, tokenizer))
    # Định nghĩa tên file (có thể đặt tên theo câu hỏi hoặc thời gian)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 2. Tạo tên file kết hợp với timestamp
    file_name = f"final_answer_{timestamp}.txt"

    with open(file_name, "w", encoding="utf-8") as f:
        f.write(f"CÂU HỎI: {query}\n")
        f.write("="*50 + "\n")
        f.write(final_answer)

    print(f"Đã lưu câu trả lời vào file: {file_name}")
        # print(final_answer)

    # chunks = prepare_global_context("", 2, data, tokenizer)
    # print(chunks)