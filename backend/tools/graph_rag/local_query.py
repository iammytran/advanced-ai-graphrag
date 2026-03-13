import asyncio
import importlib
import json
import logging
import os
import pickle
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from tqdm.auto import tqdm
from transformers import AutoTokenizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMProcessor:
    """Processor đa provider cho Local Search (vllm, openai, gemini, huggingface)"""
    
    def __init__(self, model_name: str, llm=None, provider: str = None):
        self.llm = llm
        self.provider_name = (
            provider
            or os.getenv("LOCAL_QUERY_PROVIDER")
            or os.getenv("LLM_PROVIDER")
            or "vllm"
        ).strip().lower()
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.hf_model_name = os.getenv("HUGGINGFACE_MODEL", model_name)
        self.openai_model_name = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        self.gemini_model_name = os.getenv("GEMINI_MODEL") or os.getenv("LLM_MODEL", "gemini-1.5-pro")
        self._huggingface_pipeline = None
        self.max_concurrency = int(os.getenv("LOCAL_QUERY_MAX_CONCURRENCY", "4"))
        self.huggingface_batch_size = int(os.getenv("LOCAL_QUERY_HF_BATCH_SIZE", "4"))
        logger.info("local_query: khởi tạo LLMProcessor với provider=%s", self.provider_name)
    
    def apply_template(self, system_prompt: str, user_prompt: str) -> str:
        """Tạo prompt phù hợp với provider hiện tại"""
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
            
            logger.info("local_query: khởi tạo Hugging Face model=%s", self.hf_model_name)
            model = AutoModelForCausalLM.from_pretrained(
                self.hf_model_name,
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
        logger.info("local_query: %s với %s request song song", description, worker_count)

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
    
    def generate(self, prompt: str, temperature: float, max_tokens: int, response_format: str = None) -> str:
        """Sinh văn bản dựa trên provider (single prompt)"""
        
        if self.provider_name == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("Thiếu OPENAI_API_KEY")
            
            return self._generate_openai_single(prompt, temperature, max_tokens, response_format)
        
        if self.provider_name == "gemini":
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("Thiếu GEMINI_API_KEY hoặc GOOGLE_API_KEY")
            
            return self._generate_gemini_single(prompt, temperature, max_tokens, response_format)
        
        if self.provider_name == "huggingface":
            text_generation_pipeline = self._get_huggingface_pipeline()
            do_sample = temperature > 0
            
            outputs = text_generation_pipeline(
                prompt,
                max_new_tokens=max_tokens,
                temperature=temperature,
                do_sample=do_sample,
                top_p=0.9,
                return_full_text=False,
                pad_token_id=self.tokenizer.eos_token_id,
            )
            
            if isinstance(outputs[0], list):
                return outputs[0][0]["generated_text"].strip()
            else:
                return outputs[0]["generated_text"].strip()
        
        # vLLM
        if self.llm is None:
            raise ValueError("llm đang là None khi provider là vllm")
        
        vllm_module = importlib.import_module("vllm")
        sampling_params = vllm_module.SamplingParams(
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=0.9,
            repetition_penalty=1.05,
        )
        outputs = self.llm.generate([prompt], sampling_params)
        return outputs[0].outputs[0].text.strip()

    def generate_batch(
        self,
        prompts: List[str],
        temperature: float,
        max_tokens: int,
        response_format: str = None,
    ) -> List[str]:
        """Sinh văn bản cho nhiều prompts với batch/parallel inference"""
        
        if not prompts:
            return []
        
        if self.provider_name == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            logger.info(
                "local_query: dùng OpenAI, trạng thái OPENAI_API_KEY: %s",
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
                "local_query: dùng Gemini, trạng thái API key: %s",
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
                "local_query: chạy batch Hugging Face với %s prompts, batch_size=%s",
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

        # vLLM batch
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

class AdvancedLocalSearch:
    def __init__(self, model_name: str, embedding_model_name: str, artifacts_path: str, llm=None, provider: str = None):
        # 1. Khởi tạo LLM Processor cho việc trích xuất và tổng hợp
        self.processor = LLMProcessor(model_name, llm=llm, provider=provider)
        self.tokenizer = self.processor.tokenizer
        self.artifact_paths = artifacts_path
        
        # 2. Khởi tạo Embedding Model để so sánh meaning
        self.embed_model = SentenceTransformer(embedding_model_name)

        # 3. LOAD ENCODINGS CÓ SẴN
        self.entity_name_embeddings=None
        entity_embeddings_path = f"{artifacts_path}/entity_embeddings.npy"
        if os.path.exists(entity_embeddings_path):
            logger.info("🚀 Đang nạp encodings từ file vật lý...")
            self.entity_name_embeddings = np.load(entity_embeddings_path)
        
        # 4. Load Data từ GraphRAG artifacts
        logger.info("📂 Đang nạp cơ sở dữ liệu đồ thị tri thức...")
        self.df_entities_path = f"{artifacts_path}/entities.pkl"
        self.df_relationships_path = f"{artifacts_path}/relationships.pkl"
        self.df_claims_path = f"{artifacts_path}/claims.pkl"
        self.reports_path =f"{artifacts_path}/community_summaries.json"

        self.df_entities=None
        self.df_relationships=None
        self.df_claims=None
        self.reports=None
        with open(self.df_entities_path, 'rb') as f:
            self.df_entities = pickle.load(f)
        with open(self.df_relationships_path, 'rb') as f:
            self.df_relationships = pickle.load(f)
        with open(self.df_claims_path, 'rb') as f:
            self.df_claims = pickle.load(f)
        with open(self.reports_path, 'r', encoding='utf-8') as f:
            self.reports = json.load(f)

    def extract_entities_from_query(self, query: str) -> List[str]:
        """Bước 1: Dùng LLM trích xuất các thực thể quan trọng có trong câu hỏi"""
        system_prompt = """Bạn là trợ lý ngôn ngữ học pháp luật. 
        Nhiệm vụ: Trích xuất các danh từ riêng, thuật ngữ pháp lý hoặc đối tượng quan trọng từ câu hỏi của người dùng.
        Trả về kết quả dưới dạng JSON: {"entities": ["THỰC THỂ 1", "THỰC THỂ 2"]}"""
        
        user_content = f"Câu hỏi: {query}"
        prompt = self.processor.apply_template(system_prompt, user_content)
        
        try:
            response = self.processor.generate(prompt, temperature=0, max_tokens=256, response_format="json_object")
            clean_json = response.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_json).get("entities", [])
        except Exception as e:
            logger.warning("Lỗi trích xuất thực thể: %s", e)
            return []

    def find_best_matches(self, extracted_entities: List[str], top_k_per_entity: int = 10) -> pd.DataFrame:
        """Bước 2 & 3: Encode thực thể trích xuất và so sánh similarity với entity_df"""
        if not extracted_entities:
            return pd.DataFrame()

        # Encode các thực thể từ query
        query_embeddings = self.embed_model.encode(extracted_entities)
        # logging.info(f"query_embeddings: {query_embeddings}")
        
        matched_indices = []
        for q_emb in query_embeddings:
            # Tính Cosine Similarity
            scores = np.dot(self.entity_name_embeddings, q_emb) / (
                np.linalg.norm(self.entity_name_embeddings, axis=1) * np.linalg.norm(q_emb)
            )
            # Lấy top_k thực thể giống nhất trong đồ thị
            top_idx = np.argsort(scores)[-top_k_per_entity:]
            matched_indices.extend(top_idx)
            
        return self.df_entities.iloc[list(set(matched_indices))]
    
    def _process_entities_context(self, ents_df) -> str:
        if ents_df.empty:
            return "### THỰC THỂ\n- Không tìm thấy thực thể liên quan."
        lines = [f"- {r['name']}: {r['description']}" for _, r in ents_df.iterrows()]
        return "### THỰC THỂ\n" + "\n".join(lines)
    
    def _process_relations_context(self, rels_df) -> str:
        if rels_df.empty:
            return "### QUAN HỆ\n- Không tìm thấy quan hệ liên quan."
        lines = [f"- {r['source']} -> {r['target']}: {r['description']}" for _, r in rels_df.iterrows()]
        return "### QUAN HỆ\n" + "\n".join(lines)
    
    def _process_claims_context(self, claims_df) -> str:
        header = "### QUY ĐỊNH & CHẾ TÀI CHI TIẾT\n"
        if claims_df.empty:
            return header + "- Không có dữ liệu quy định chi tiết cho cụm này."
        
        claim_lines = []
        for _, r in claims_df.iterrows():
            line = f"- [Loại quy định: {r['claim_type']}], đối tượng {r['subject']} có mô tả: {r['description']}"
            # Grounding: Thêm trích dẫn nguồn nếu có
            if 'source_text' in r and r['source_text'] not in ['NONE', '']:
                line += f" (Trích dẫn: {r['source_text']})"
            claim_lines.append(line)
            
        return header + "\n".join(claim_lines)
    
    def _process_reports_context(self, reports_list) -> str:
        header = "### BÁO CÁO TÓM TẮT CỦA CÁC CỤM\n"
        if not reports_list:
            return header + "- Không có báo cáo tóm tắt."

        report_entries = []
        for r in reports_list:
            detail = r.get('report_detail', {})
            title = detail.get('title', 'Không có tiêu đề')
            summary = detail.get('summary', 'Không có tóm tắt')
            
            entry = f"#### {title}\n{summary}"
            
            # Lấy tối đa 3 phát hiện quan trọng
            findings = detail.get('findings', [])
            if findings:
                finding_texts = "\n".join([f"- Phát hiện: {f['summary']}" for f in findings[:3]])
                entry += f"\n{finding_texts}"
                
            report_entries.append(entry)

        return header + "\n---\n".join(report_entries)

    def get_graph_context(self, matched_entities: pd.DataFrame):
        """Bước 4: Tìm quan hệ và báo cáo cộng đồng xung quanh"""
        names = matched_entities['name'].unique().tolist()
        
        # Lấy quan hệ (Edges)
        rels = self.df_relationships[
            self.df_relationships['source'].isin(names) | 
            self.df_relationships['target'].isin(names)
        ].sort_values(by='weight', ascending=False).head(20)

        # Lấy quy định (Claims)
        claims = self.df_claims[
            self.df_claims['subject'].isin(names) | 
            self.df_claims['object'].isin(names)
        ].head(20)
        
        # Lấy báo cáo cộng đồng theo entities mà có trong nodes (Reports)
        reports = []
        node_names_set = set(names)
    
        for community in self.reports:
            # Lấy list nodes của item đó
            entities_in_community = set(community.get("nodes", []))
            
            # Kiểm tra xem có node nào chung giữa 2 list không
            if not entities_in_community.isdisjoint(node_names_set):
                reports.append(community)
                
                return matched_entities, rels, claims, reports

    def query(self, user_query: str):
        """Hàm chính điều phối toàn bộ luồng Local Search"""
        
        # 1. Trích xuất
        extracted_names = self.extract_entities_from_query(user_query)
        logger.info(f"🔍 Thực thể trích xuất từ query: {extracted_names}")
        
        # 2 & 3. So khớp ngữ nghĩa (Meaning Comparison)
        matched_ents = self.find_best_matches(extracted_names)
        logger.info(f"📍 Đã khớp với {len(matched_ents)} thực thể trong đồ thị.")
        logger.info(f"📍 Các thực thể khớp: {matched_ents}")
        
        # 4. Gom context
        ents, rels, claims, reports = self.get_graph_context(matched_ents)
        
        # Xây dựng context prompt
        context_str = "### THỰC THỂ\n" + "\n".join([f"- {r['name']}: {r['description']}" for _, r in ents.iterrows()])
        context_str += "\n\n### QUAN HỆ\n" + "\n".join([f"- {r['source']} -> {r['target']}: {r['description']}" for _, r in rels.iterrows()])
        context_str += "\n\n### QUY ĐỊNH & CHẾ TÀI CHI TIẾT \n"
        if not claims.empty:
            claim_lines = []
            for _, r in claims.iterrows():
                # Kết hợp Subject, Loại quy định và Nội dung chi tiết
                line = f"- [Loại quy định: {r['claim_type']}], đối tượng {r['subject']} có mô tả: {r['description']}"
                
                # Nếu có trích dẫn nguồn, hãy đưa vào để model "grounding" tốt hơn
                if 'source_text' in r and r['source_text'] not in ['NONE', '']:
                    line += f" (Trích dẫn: {r['source_text']})"
                    
                claim_lines.append(line)
            context_str += "\n".join(claim_lines)
        else:
            context_str += "- Không có dữ liệu quy định chi tiết cho cụm này."
        
        context_str += "\n\n### BÁO CÁO TÓM TẮT CỦA CÁC CỤM\n"

        report_entries = []
        for r in reports:
            # Lấy phần detail ra để xử lý cho gọn
            detail = r.get('report_detail', {})
            title = detail.get('title', 'Không có tiêu đề')
            summary = detail.get('summary', 'Không có tóm tắt')
            
            # Tạo chuỗi cho mỗi báo cáo
            entry = f" ####{title}\n{summary}"
            
            # Nếu muốn lấy thêm cả các 'findings' bên trong JSON để context dày hơn:
            findings = detail.get('findings', [])
            if findings:
                finding_texts = "\n".join([f"- Phát hiện: {f['summary']}" for f in findings[:3]]) # Lấy tối đa 3 phát hiện
                entry += f"\n{finding_texts}"
                
            report_entries.append(entry)

        context_str += "\n---\n".join(report_entries)

        # 5. LLM tổng hợp câu trả lời cuối cùng
        system_prompt = "Bạn là chuyên gia luật. Hãy trả lời câu hỏi dựa trên tổng hợp bối cảnh đồ thị tri thức được cung cấp."
        user_content = f"BỐI CẢNH:\n{context_str}\n\nCÂU HỎI: {user_query}\n\nTRẢ LỜI:"
        
        final_prompt = self.processor.apply_template(system_prompt, user_content)
        
        try:
            response = self.processor.generate(final_prompt, temperature=0.3, max_tokens=1024)
            return response
        except Exception as e:
            logger.exception("Lỗi sinh câu trả lời cuối cùng: %s", e)
            return ""
    
    def get_relevant_resources(self, user_query:str):
        # 1. Trích xuất
        extracted_names = self.extract_entities_from_query(user_query)
        logger.info(f"🔍 Thực thể trích xuất từ query: {extracted_names}")
        
        # 2 & 3. So khớp ngữ nghĩa (Meaning Comparison)
        matched_ents = self.find_best_matches(extracted_names)
        logger.info(f"📍 Đã khớp với {len(matched_ents)} thực thể trong đồ thị.")
        logger.info(f"📍 Các thực thể khớp: {matched_ents}")
        
        # 4. Gom context
        ents, rels, claims, reports = self.get_graph_context(matched_ents)

        context_parts = [
            self._process_entities_context(ents),
            self._process_relations_context(rels),
            self._process_claims_context(claims),
            self._process_reports_context(reports)
        ]

        return context_parts

# --- CÁCH CHẠY ---
def run_local_search(query, artifact_path, llm=None, provider: str = None):
    search_engine = AdvancedLocalSearch(
        model_name="Qwen/Qwen2.5-7B-Instruct",
        embedding_model_name="keepitreal/vietnamese-sbert", 
        artifacts_path=artifact_path,
        llm=llm,
        provider=provider
    )
    
    response = search_engine.get_relevant_resources(query)
    return response

if __name__ == "__main__":
    query = "Người cho vay có quyền đòi lại tài sản trước hạn không?"
    asyncio.run(run_local_search(query, "outputs_20260312_001744"))