import json
import random
import asyncio
from typing import List, Dict
from tqdm.asyncio import tqdm
from vllm import LLM, SamplingParams
from transformers import AutoTokenizer
import logging
import warnings
from datetime import datetime
import os

# Cấu hình log và cảnh báo
warnings.filterwarnings("ignore", category=FutureWarning)
logging.basicConfig(level=logging.INFO)

class VLLMProcessor:
    def __init__(self, model_name: str, max_model_len: int = 16384):
        # Khởi tạo vLLM engine
        self.llm = LLM(
            model=model_name,
            max_model_len=max_model_len,
            trust_remote_code=True,
            gpu_memory_utilization=0.85, # Điều chỉnh tùy theo VRAM của bạn
            enforce_eager=True # Giảm overhead cho các model nhỏ nếu cần
        )
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)

    def apply_template(self, system_prompt: str, user_prompt: str) -> str:
        """Chuyển đổi sang Chat Template chuẩn của model."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        return self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    async def generate_batch(self, prompts: List[str], temperature: float, max_tokens: int) -> List[str]:
        sampling_params = SamplingParams(
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=0.9,
            repetition_penalty=1.05
        )
        # vLLM xử lý Batch song song ở đây
        outputs = self.llm.generate(prompts, sampling_params, use_tqdm=True)
        return [output.outputs[0].text.strip() for output in outputs]

def prepare_global_context(query, community_reports, tokenizer, context_window=6000):
    random.shuffle(community_reports)
    chunks = []
    current_chunk = ""
    safe_limit = context_window - 500 

    for r in community_reports:
        detail = r.get('report_detail', {})
        findings = "\n".join([f"- {f['summary']}" for f in detail.get('findings', [])])
        
        report_text = (
            f"\n\n### BÁO CÁO ID: {r['community_id']}\n"
            f"Tiêu đề: {detail.get('title', 'N/A')}\n"
            f"Tóm tắt: {detail.get('report', '')}\n"
            f"Phát hiện: {findings}\n---"
        )
        
        if len(tokenizer.encode(current_chunk + report_text)) < safe_limit:
            current_chunk += report_text
        else:
            if current_chunk: chunks.append(current_chunk.strip())
            current_chunk = report_text
            
    if current_chunk: chunks.append(current_chunk.strip())
    return chunks

async def run_map_step(query, chunks, max_new_tokens, processor: VLLMProcessor):
    system_prompt = f"""
---Vai trò---
Bạn là một chuyên gia phân tích pháp luật và trợ lý AI thông minh. 
Nhiệm vụ: trả lời các câu hỏi dựa trên dữ liệu từ các bảng báo cáo cộng đồng pháp lý được cung cấp.

---Mục tiêu---
Tạo một câu trả lời bao gồm danh sách các điểm chính (key points) để trả lời câu hỏi của người dùng, tóm tắt tất cả các thông tin có liên quan trong các bảng dữ liệu đầu vào.
Bạn phải sử dụng dữ liệu được cung cấp trong các bảng dưới đây làm ngữ cảnh chính để tạo câu trả lời. 
Nếu bạn không biết câu trả lời hoặc nếu dữ liệu đầu vào không chứa đủ thông tin, hãy trả lời là bạn không đủ dữ liệu. Tuyệt đối không tự bịa đặt thông tin.

Mỗi điểm chính trong câu trả lời phải bao gồm các thành phần sau:
- Description (Mô tả): Một bản mô tả toàn diện về luận điểm pháp lý hoặc thông tin trích xuất được.
- Importance Score (Điểm quan trọng): Một số nguyên từ 0-100 thể hiện mức độ hữu ích của điểm đó trong việc trả lời câu hỏi. Câu trả lời kiểu "Tôi không biết" phải có điểm là 0.

---ĐỊNH DẠNG ĐẦU RA (JSON)---
Bạn PHẢI trả về JSON duy nhất theo cấu trúc:
{{
    "points": [
        {{"description": "Mô tả về luận điểm 1 [Data: Báo cáo (id báo cáo)]", "score": giá_trị_điểm}},
        {{"description": "Mô tả về luận điểm 2 [Data: Báo cáo (id báo cáo)]", "score": giá_trị_điểm}}
    ]
}}

---QUY TẮC PHÁP LÝ---
1. Sử dụng chính xác trợ động từ: "phải", "được", "có thể", "không được", "chịu trách nhiệm".
2. Trích dẫn ID báo cáo: "Mô tả nội dung... [Data: Báo cáo (1, 2, 3, 4, 5, +more)]". Không liệt kê quá 5 ID trong một cụm.
3. Tuyệt đối không tự bịa đặt thông tin ngoài ngữ cảnh.
4. Độ dài tối đa: {max_new_tokens} từ."""

    prompts = []
    for chunk in chunks:
        user_content = f"Dựa trên dữ liệu: {chunk}\n\nCâu hỏi: {query}"
        prompts.append(processor.apply_template(system_prompt, user_content))

    print(f"🚀 Giai đoạn Map: Đang xử lý {len(prompts)} chunks song song...")
    raw_responses = await processor.generate_batch(prompts, temperature=0.1, max_tokens=1024)
    # print(f"raw_responses: {raw_responses}")
    
    results = []
    for res in raw_responses:
        try:
            # 1. Làm sạch chuỗi
            clean_res = res.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_res)

            # Giả sử bạn muốn lưu từng response của LLM để kiểm tra
            with open('debug_llm_response.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            
            # 2. Thay vì chỉ lấy "points", hãy lấy toàn bộ object 
            # để giữ lại "score" (hoặc "rating") cho bước Reduce sau này
            if isinstance(data, dict):
                # Đảm bảo object có score để không bị lỗi khi sort
                if 'score' not in data and 'rating' in data:
                    data['score'] = data['rating'] # Đồng bộ hóa tên khóa
                
                results.append(data) 
            elif isinstance(data, list):
                results.extend(data)
                
        except Exception as e:
            print(f"Lỗi parse JSON: {e}")
            continue

    return results

async def run_reduce_step(query, map_results, max_new_tokens, processor: VLLMProcessor):
    print(f"DEBUG: map_results type: {type(map_results)}, value: {map_results}")
    # Lấy top các luận điểm chất lượng nhất
    sorted_results = sorted(map_results, key=lambda x: x.get('score', 0), reverse=True)[:15]
    
    context = "\n".join([f"- {r['description']}" for r in sorted_results])
    
    system_prompt = f"""
    ---Vai trò---
Bạn là một chuyên gia pháp lý cao cấp hoặc Thẩm phán có kinh nghiệm. 
Nhiệm vụ: tổng hợp các báo cáo phân tích từ nhiều nguồn dữ liệu khác nhau để đưa ra câu trả lời cuối cùng, thống nhất và toàn diện cho người dùng.

---Mục tiêu---
Tạo một văn bản trả lời với độ dài và định dạng yêu cầu để giải đáp câu hỏi của người dùng. Bạn cần tổng hợp các báo cáo từ nhiều phân tích viên vốn tập trung vào các phần khác nhau của bộ dữ liệu pháp luật.
Lưu ý rằng các báo cáo phân tích dưới đây đã được sắp xếp theo **thứ tự tầm quan trọng giảm dần**.
Nếu bạn không thể tìm thấy câu trả lời hoặc nếu các báo cáo được cung cấp không chứa đủ thông tin, hãy trả lời rõ là dữ liệu hiện tại không đủ để giải đáp. Tuyệt đối không tự ý bịa đặt quy định pháp luật.

---ĐỊNH DẠNG ĐẦU RA (Markdown)---
1. Loại bỏ tất cả các thông tin không liên quan từ các báo cáo thành phần.
2. Hợp nhất các thông tin đã được làm sạch thành một câu trả lời chặt chẽ, có giải thích đầy đủ các điểm chính và hệ quả pháp lý phù hợp với định dạng yêu cầu.
3. Chia các phần (sections) và thêm các lời bình luận, dẫn dắt phù hợp để văn bản có cấu trúc logic.
4. Trình bày nội dung bằng định dạng Markdown.

---QUY TẮC PHÁP LÝ---
1. Phải giữ nguyên ý nghĩa gốc và sử dụng chính xác các trợ động từ tình thái chuyên dụng trong văn bản luật như: "phải", "được", "có thể", "không được", "chịu trách nhiệm".
2. Giữ lại tất cả các tham chiếu dữ liệu (Data references) đã có trong các báo cáo thành phần, nhưng **không được nhắc đến vai trò của các phân tích viên** hay quá trình tổng hợp trong văn bản cuối cùng.

---QUY TẮC TRÍCH DẪN---
- Không liệt kê quá 5 ID bản ghi trong một tham chiếu đơn lẻ. Hãy liệt kê 5 ID liên quan nhất và thêm "+còn nữa" nếu còn nhiều hơn.
- Ví dụ: "Hành vi X bị coi là vi phạm quy định về quản lý kinh tế và có thể bị truy cứu trách nhiệm hình sự [Data: Báo cáo (2, 7, 34, 46, 64, +more)]. Hình phạt bổ sung có thể bao gồm cấm đảm nhiệm chức vụ [Data: Báo cáo (1, 3)]".
- Trong đó 1, 2, 3, 7, 34, 46, và 64 đại diện cho ID của báo cáo dữ liệu tương ứng.
- Tuyệt đối không đưa vào các thông tin không có bằng chứng hỗ trợ từ dữ liệu nguồn.
- Giới hạn tổng độ dài câu trả lời trong khoảng {max_new_tokens} từ."""
    
    user_content = f"Các luận điểm nguồn:\n{context}\n\nCâu hỏi: {query}\n\nTrả lời chi tiết:"
    
    prompt = processor.apply_template(system_prompt, user_content)
    
    print("📝 Giai đoạn Reduce: Đang tổng hợp kết quả cuối cùng...")
    responses = await processor.generate_batch([prompt], temperature=0.3, max_tokens=2048)
    return responses[0]

async def run_global_search(query, summaries_path):
    # Cấu hình
    MODEL_PATH = "Qwen/Qwen2.5-7B-Instruct"
    max_new_tokens = 4096
    
    processor = VLLMProcessor(MODEL_PATH)
    
    # Load Data
    try:
        with open(summaries_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Lỗi đọc file: {e}")
        return
    
    # 1. Chia chunk
    chunks = prepare_global_context(query, data, processor.tokenizer)
    
    # 2. Map
    map_results = await run_map_step(query, chunks, max_new_tokens, processor)
    
    # 3. Reduce
    final_answer = await run_reduce_step(query, max_new_tokens, map_results, processor)
    return final_answer

    # # Lưu kết quả
    # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # with open(f"final_answer_{timestamp}.txt", "w", encoding="utf-8") as f:
    #     f.write(f"CÂU HỎI: {query}\n" + "="*50 + "\n" + final_answer)
    
    # print(f"✅ Hoàn thành! File lưu tại final_answer_{timestamp}.txt")

if __name__ == '__main__':
    query = "Nội dung chính của điều 182 của bộ luật Hình sự 2015 là gì?"
    asyncio.run(run_global_search(query))