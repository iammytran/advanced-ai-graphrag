import importlib
import json
import logging
import os
import random
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

from tqdm.auto import tqdm
from transformers import AutoTokenizer

# Cấu hình log và cảnh báo
warnings.filterwarnings("ignore", category=FutureWarning)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMProcessor:
    def __init__(self, model_name: str, llm=None, provider: str = None, max_model_len: int = 16384):
        # Khởi tạo processor đa provider cho Global Search
        self.llm = llm
        self.provider_name = (
            provider
            or os.getenv("GLOBAL_QUERY_PROVIDER")
            or os.getenv("LLM_PROVIDER")
            or "vllm"
        ).strip().lower()
        self.hf_model_name = model_name
        self.huggingface_model_name = os.getenv("HUGGINGFACE_MODEL", model_name)
        tokenizer_model_name = self.huggingface_model_name if self.provider_name == "huggingface" else model_name
        self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_model_name)
        self.openai_model_name = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        self.gemini_model_name = os.getenv("GEMINI_MODEL") or os.getenv("LLM_MODEL", "gemini-1.5-pro")
        self._huggingface_pipeline = None
        self.max_concurrency = int(os.getenv("GLOBAL_QUERY_MAX_CONCURRENCY", "4"))
        self.huggingface_batch_size = int(os.getenv("GLOBAL_QUERY_HF_BATCH_SIZE", "4"))

    def apply_template(self, system_prompt: str, user_prompt: str) -> str:
        """Tạo prompt phù hợp với provider hiện tại."""
        if self.provider_name in {"openai", "gemini"}:
            return (
                f"[HƯỚNG DẪN HỆ THỐNG]\n{system_prompt}\n\n"
                f"[NỘI DUNG NGƯỜI DÙNG]\n{user_prompt}"
            )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        return self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    def _get_huggingface_pipeline(self):
        if self._huggingface_pipeline is None:
            from transformers import AutoModelForCausalLM, pipeline

            logger.info("global_query: khởi tạo Hugging Face model=%s", self.huggingface_model_name)
            model = AutoModelForCausalLM.from_pretrained(
                self.huggingface_model_name,
                device_map="auto",
                trust_remote_code=True,
            )
            self._huggingface_pipeline = pipeline(
                "text-generation",
                model=model,
                tokenizer=self.tokenizer,
            )
        return self._huggingface_pipeline

    def _generate_openai_single(self, prompt: str, temperature: float, max_tokens: int, response_format: str = None) -> str:
        from openai import OpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("Thiếu OPENAI_API_KEY")

        client = OpenAI(api_key=api_key)
        request_kwargs = {
            "model": self.openai_model_name,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if response_format == "json_object":
            request_kwargs["response_format"] = {"type": "json_object"}

        completion = client.chat.completions.create(**request_kwargs)
        return completion.choices[0].message.content or ""

    def _generate_gemini_single(self, prompt: str, temperature: float, max_tokens: int, response_format: str = None) -> str:
        import google.generativeai as genai

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("Thiếu GEMINI_API_KEY hoặc GOOGLE_API_KEY")

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(self.gemini_model_name)
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        if response_format == "json_object":
            generation_config["response_mime_type"] = "application/json"

        response = model.generate_content(
            prompt,
            generation_config=generation_config,
        )
        return getattr(response, "text", "") or ""

    def _run_parallel_inference(self, prompts: List[str], inference_func, description: str) -> List[str]:
        worker_count = max(1, min(self.max_concurrency, len(prompts)))
        logger.info("global_query: %s với %s request song song", description, worker_count)

        responses = [""] * len(prompts)
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_to_index = {
                executor.submit(inference_func, prompt): index
                for index, prompt in enumerate(prompts)
            }
            for future in tqdm(
                as_completed(future_to_index),
                total=len(future_to_index),
                desc=description,
                unit="prompt",
            ):
                index = future_to_index[future]
                responses[index] = future.result()

        return responses

    def generate_batch(
        self,
        prompts: List[str],
        temperature: float,
        max_tokens: int,
        response_format: str = None,
    ) -> List[str]:
        if self.provider_name == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            logger.info(
                "global_query: dùng OpenAI, trạng thái OPENAI_API_KEY: %s",
                "đã tìm thấy" if api_key else "chưa tìm thấy",
            )
            if not api_key:
                raise ValueError("Thiếu OPENAI_API_KEY")

            return self._run_parallel_inference(
                prompts,
                lambda prompt: self._generate_openai_single(
                    prompt,
                    temperature,
                    max_tokens,
                    response_format,
                ),
                description="OpenAI inference",
            )

        if self.provider_name == "gemini":
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            logger.info(
                "global_query: dùng Gemini, trạng thái API key: %s",
                "đã tìm thấy" if api_key else "chưa tìm thấy",
            )
            if not api_key:
                raise ValueError("Thiếu GEMINI_API_KEY hoặc GOOGLE_API_KEY")

            return self._run_parallel_inference(
                prompts,
                lambda prompt: self._generate_gemini_single(
                    prompt,
                    temperature,
                    max_tokens,
                    response_format,
                ),
                description="Gemini inference",
            )

        if self.provider_name == "huggingface":
            text_generation_pipeline = self._get_huggingface_pipeline()
            do_sample = temperature > 0
            logger.info(
                "global_query: chạy batch Hugging Face với %s prompts, batch_size=%s",
                len(prompts),
                self.huggingface_batch_size,
            )
            responses = []
            for batch_start in tqdm(
                range(0, len(prompts), self.huggingface_batch_size),
                desc="Hugging Face inference",
                unit="batch",
            ):
                prompt_batch = prompts[batch_start:batch_start + self.huggingface_batch_size]
                outputs = text_generation_pipeline(
                    prompt_batch,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    do_sample=do_sample,
                    top_p=0.9,
                    return_full_text=False,
                    pad_token_id=self.tokenizer.eos_token_id,
                    batch_size=self.huggingface_batch_size,
                )

                for output in outputs:
                    if isinstance(output, list):
                        responses.append(output[0]["generated_text"].strip())
                    else:
                        responses.append(output["generated_text"].strip())
            return responses

        if self.llm is None:
            raise ValueError("llm đang là None khi provider là vllm")

        vllm_module = importlib.import_module("vllm")
        sampling_params = vllm_module.SamplingParams(
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=0.9,
            repetition_penalty=1.05,
        )
        outputs = self.llm.generate(prompts, sampling_params, use_tqdm=True)
        return [output.outputs[0].text.strip() for output in outputs]


VLLMProcessor = LLMProcessor

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
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = report_text
            
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

def run_map_step(query, chunks, max_new_tokens, processor: LLMProcessor):
    system_prompt = f"""
---Vai trò---
Bạn là một chuyên gia phân tích pháp luật và trợ lý AI thông minh. 
Nhiệm vụ: trả lời các câu hỏi dựa trên dữ liệu từ các bảng báo cáo cộng đồng pháp lý được cung cấp.

---Mục tiêu---
Tạo một câu trả lời bao gồm danh sách các điểm chính (key points) để trả lời câu hỏi của người dùng, tóm tắt tất cả các thông tin có liên quan trong các bảng dữ liệu đầu vào.
Bạn phải sử dụng dữ liệu được cung cấp trong các bảng dưới đây làm ngữ cảnh chính để tạo câu trả lời. 
Nếu bạn không biết câu trả lời hoặc nếu dữ liệu đầu vào không chứa đủ thông tin, hãy trả lời là bạn không đủ dữ liệu. Tuyệt đối không tự bịa đặt thông tin. 
Đặc biệt, phải kiểm soát độ dài để tránh lỗi hệ thống, bạn PHẢI viết cực kỳ súc tích, dưới {max_new_tokens} từ, nhưng vẫn nên đảm bảo đủ ý.


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

    logger.info("Giai đoạn Map: đang xử lý %s chunks", len(prompts))
    raw_responses = processor.generate_batch(
        prompts,
        temperature=0.1,
        max_tokens=1024,
        response_format="json_object",
    )

    # --- BẮT ĐẦU ĐOẠN LƯU DEBUG ---
    log_filename = "debug_global_query.jsonl"
    with open(log_filename, "w", encoding="utf-8") as f:
        for i, res in enumerate(raw_responses):
            debug_entry = {
                "chunk_index": i,
                "prompt_sent": prompts[i], # Lưu luôn prompt để đối chiếu
                "raw_output": res,
            }
            f.write(json.dumps(debug_entry, ensure_ascii=False) + "\n")
    logger.info("Đã lưu output thô vào file: %s", log_filename)
    
    results = []
    for res in raw_responses:
        try:
            clean_res = res.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_res)

            if isinstance(data, dict):
                if "points" in data and isinstance(data["points"], list):
                    results.append(data)
                else:
                    logger.warning("Kết quả map không có trường 'points' hợp lệ")

        except Exception as error:
            logger.warning("Lỗi parse JSON ở giai đoạn Map: %s", error)
            continue

    return results


def _flatten_map_results(map_results):
    all_points = []
    for item in map_results:
        if isinstance(item, dict) and "points" in item:
            points = item.get("points", [])
            if isinstance(points, list):
                all_points.extend(points)
        elif isinstance(item, dict):
            all_points.append(item)
    return all_points

def get_relevant_resources(map_results, top_k_sources):
    if not map_results:
        logger.warning("get_relevant_resources: map_results rỗng, trả về danh sách trống")
        return []
    
    all_points = _flatten_map_results(map_results)
    sorted_list = sorted(all_points, key=lambda x: x.get('score', 0), reverse=True)[:top_k_sources]
    descriptions = [item.get('description', '') for item in sorted_list]
    descriptions_without_sources = [item.split(' [Data:')[0].strip() for item in descriptions]
    return descriptions_without_sources

def run_global_search(query, summaries_path, llm=None, top_k_sources=10, provider: str = None):
    if isinstance(llm, int) and not isinstance(top_k_sources, int):
        llm, top_k_sources = top_k_sources, llm

    model_path = os.getenv("GLOBAL_QUERY_MODEL_PATH", "Qwen/Qwen2.5-7B-Instruct")
    max_new_tokens = 4096
    processor = LLMProcessor(model_path, llm=llm, provider=provider)
    logger.info("run_global_search: dùng provider=%s", processor.provider_name)
    
    try:
        with open(summaries_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as error:
        logger.exception("Lỗi đọc file summaries: %s", error)
        return []
    
    chunks = prepare_global_context(query, data, processor.tokenizer)
    map_results = run_map_step(query, chunks, max_new_tokens, processor)

    sorted_map_output = get_relevant_resources(map_results, top_k_sources)

    return sorted_map_output

if __name__ == '__main__':
    query = "Nội dung chính của điều 182 của bộ luật Hình sự 2015 là gì?"
    run_global_search(query, "outputs_20260312_001744/community_summaries.json")