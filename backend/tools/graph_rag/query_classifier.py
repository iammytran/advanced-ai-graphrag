import importlib
import json
import logging
import os
import re

# Import prompt
from backend.config.prompts.prompt_query_classifier import QUERY_CLASSIFIER_PROMPT

logger = logging.getLogger(__name__)


def classify_query_mode(query: str, entity_list: list[str] | None = None) -> str | None:
    """Rule-based classifier: return 'local' when strong local signals appear, else None."""
    # Rule 1: Nhận diện mẫu điều/khoản/điểm/văn bản luật kèm số hiệu
    law_pattern = r'(Điều|Khoản|Điểm|Nghị\s*quyết|Luật)\s+\d+'
    if re.search(law_pattern, query, re.IGNORECASE):
        return "local"

    # Rule 2: Nếu query chứa tên thực thể đã index thì ưu tiên local
    if entity_list:
        normalized_query = query.lower()
        for entity in entity_list:
            if not entity:
                continue
            if str(entity).lower() in normalized_query:
                return "local"

    return None


def query_type_classifier(
    query: str,
    entity_list: list[str] | None = None,
    llm=None,
    provider: str = None,
    get_llm_func=None,
):
    """
    Phân loại query type cho GraphRAG với 4 lựa chọn provider:
    - vllm (mặc định, tương thích ngược)
    - openai
    - gemini
    - huggingface

    Provider được lấy theo thứ tự ưu tiên:
    1) tham số provider
    2) QUERY_CLASSIFIER_PROVIDER
    3) LLM_PROVIDER
    4) "vllm"
    """
    # Ưu tiên lớp luật nhanh trước khi gọi LLM để giảm chi phí và độ trễ.
    rule_based_mode = classify_query_mode(query=query, entity_list=entity_list)
    if rule_based_mode is not None:
        return {
            "search_type": rule_based_mode,
            "reason": "được phân loại theo luật (pattern điều luật hoặc khớp thực thể)",
        }

    system_prompt = QUERY_CLASSIFIER_PROMPT
    user_prompt = f'Câu hỏi người dùng: "{query}"'

    provider_name = (
        provider
        or os.getenv("QUERY_CLASSIFIER_PROVIDER")
        or os.getenv("LLM_PROVIDER")
        or "vllm"
    ).strip().lower()

    def _extract_decision(raw_text: str):        
        # 1. Làm sạch text và tìm phạm vi JSON
        clean_text = (raw_text or "").replace("```json", "").replace("```", "").strip()
        start_idx = clean_text.find("{")
        end_idx = clean_text.rfind("}") + 1

        # Mặc định ban đầu
        default_reason = f"được phân loại mặc định (global) do phản hồi không hợp lệ từ {provider_name}"

        # 2. Kiểm tra nếu không tìm thấy cấu trúc JSON {}
        if start_idx < 0 or end_idx <= start_idx:
            return {
                "search_type": "global",
                "reason": f"Không tìm thấy JSON, {default_reason}"
            }

        try:
            # 3. Parse JSON
            decision = json.loads(clean_text[start_idx:end_idx])
            search_type = str(decision.get("search_type", "")).strip().lower()
            reason = str(decision.get("reason", "")).strip()

            # 4. Nếu search_type không nằm trong tập cho phép, trả về global
            if search_type not in {"local", "global"}:
                return {
                    "search_type": "global",
                    "reason": f"search_type '{search_type}' không hợp lệ. {default_reason}"
                }

            return {
                "search_type": search_type,
                "reason": reason or f"được phân loại bởi {provider_name}",
            }

        except (json.JSONDecodeError, Exception) as e:
            # 5. Nếu có lỗi parse JSON, trả về global thay vì raise error
            return {
                "search_type": "global",
                "reason": f"Lỗi parse JSON ({str(e)}). {default_reason}"
            }

    try:
        if provider_name == "openai":
            from openai import OpenAI

            api_key = os.getenv("OPENAI_API_KEY")
            logger.info(
                "query_type_classifier: dùng OpenAI, trạng thái OPENAI_API_KEY: %s",
                "đã tìm thấy" if api_key else "chưa tìm thấy",
            )
            if not api_key:
                raise ValueError("Thiếu OPENAI_API_KEY")

            model_name = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
            client = OpenAI(api_key=api_key)
            completion = client.chat.completions.create(
                model=model_name,
                temperature=0,
                max_tokens=200,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            generated_text = completion.choices[0].message.content or ""
            return _extract_decision(generated_text)

        if provider_name == "gemini":
            import google.generativeai as genai

            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            logger.info(
                "query_type_classifier: dùng Gemini, trạng thái API key: %s",
                "đã tìm thấy" if api_key else "chưa tìm thấy",
            )
            if not api_key:
                raise ValueError("Thiếu GEMINI_API_KEY hoặc GOOGLE_API_KEY")

            model_name = os.getenv("GEMINI_MODEL") or os.getenv("LLM_MODEL", "gemini-1.5-pro")
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(
                [system_prompt, user_prompt],
                generation_config={
                    "temperature": 0,
                    "max_output_tokens": 200,
                    "response_mime_type": "application/json",
                },
            )
            generated_text = getattr(response, "text", "") or ""
            return _extract_decision(generated_text)

        if provider_name == "huggingface":
            from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

            model_name = os.getenv("HUGGINGFACE_MODEL", "Qwen/Qwen2.5-7B-Instruct")
            logger.info("query_type_classifier: dùng Hugging Face model=%s", model_name)

            tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                device_map="auto",
                trust_remote_code=True,
            )
            text_generation_pipeline = pipeline(
                "text-generation",
                model=model,
                tokenizer=tokenizer,
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            prompt = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )

            outputs = text_generation_pipeline(
                prompt,
                max_new_tokens=200,
                temperature=0.0,
                do_sample=False,
                return_full_text=False,
                pad_token_id=tokenizer.eos_token_id,
            )
            generated_text = outputs[0]["generated_text"].strip()
            return _extract_decision(generated_text)

        # Mặc định: vLLM
        if llm is None:
            if get_llm_func is None:
                raise ValueError("llm đang là None và chưa truyền get_llm_func")
            llm = get_llm_func()

        vllm_module = importlib.import_module("vllm")
        SamplingParams = vllm_module.SamplingParams

        sampling_params = SamplingParams(
            temperature=0.0,
            max_tokens=200,
            stop=["}"],
        )
        prompt_template = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
{system_prompt}<|eot_id|>
<|start_header_id|>user<|end_header_id|>
{user_prompt}<|message_end|>
<|start_header_id|>assistant<|end_header_id|>
"""

        outputs = llm.generate([prompt_template], sampling_params)
        generated_text = (outputs[0].outputs[0].text or "") + "}"
        return _extract_decision(generated_text)

    except Exception:
        logger.exception("Lỗi query_type_classifier với provider=%s", provider_name)
        return {"search_type": "local", "reason": f"rơi về nhánh dự phòng ({provider_name})"}
