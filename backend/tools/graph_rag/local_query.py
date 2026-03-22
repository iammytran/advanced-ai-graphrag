import asyncio
import importlib
import json
import logging
import os
import pickle
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

from dotenv import load_dotenv
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from tqdm.auto import tqdm
from transformers import AutoTokenizer

from backend.config.config import (
    ARTIFACT_FOLDER,
    VN_EMBEDDING_MODEL,
    TOP_K_RETRIEVED
)
from backend.config.prompts.prompt_local_query import ENTITY_EXTRACTION_PROMPT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Tải các biến môi trường từ file .env
load_dotenv()

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
        system_prompt = ENTITY_EXTRACTION_PROMPT
        
        user_content = f"Câu hỏi: {query}"
        prompt = self.processor.apply_template(system_prompt, user_content)
        
        try:
            response = self.processor.generate(prompt, temperature=0, max_tokens=256, response_format="json_object")
            clean_json = response.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_json).get("entities", [])
        except Exception as e:
            logger.warning("Lỗi trích xuất thực thể: %s", e)
            return []

    def find_best_matches(self, extracted_entities: List[str], top_k: int = TOP_K_RETRIEVED) -> pd.DataFrame:
        """Bước 2 & 3: Encode thực thể trích xuất và so sánh similarity với entity_df để lấy top_k tổng thể."""
        if not extracted_entities or self.entity_name_embeddings is None:
            return pd.DataFrame()

        # Encode các thực thể từ query
        query_embeddings = self.embed_model.encode(extracted_entities, show_progress_bar=False)
        
        # Tính Cosine Similarity cho tất cả các cặp (query_embedding, entity_embedding)
        # Shape: (num_query_embeddings, num_entity_embeddings)
        cosine_scores = np.dot(query_embeddings, self.entity_name_embeddings.T) / (
            np.linalg.norm(query_embeddings, axis=1)[:, np.newaxis] * np.linalg.norm(self.entity_name_embeddings, axis=1)
        )

        # Lấy top_k giá trị cao nhất từ toàn bộ ma trận scores
        # np.argsort trả về chỉ số, ta lấy -top_k: để có top k lớn nhất
        # sau đó lấy giá trị của top k score đó
        flat_top_k_indices = np.argsort(cosine_scores.flatten())[-top_k:]
        
        # Chuyển đổi chỉ số phẳng thành chỉ số (hàng, cột)
        row_indices, col_indices = np.unravel_index(flat_top_k_indices, cosine_scores.shape)

        # Lấy các chỉ số entity độc nhất
        matched_indices = np.unique(col_indices)
            
        return self.df_entities.iloc[matched_indices]
    
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
        """Bước 4: Tìm quan hệ và báo cáo cộng đồng xung quanh, đồng thời thu thập chunk_ids"""
        names = matched_entities['name'].unique().tolist()
        print(f"Thực thể được trích xuất:{names}")
        
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
            entities_in_community = set(community.get("nodes", []))
            if not entities_in_community.isdisjoint(node_names_set):
                reports.append(community)
        
        # Thu thập chunk_ids từ tất cả các nguồn
        source_chunk_ids = set()
        if 'chunk_id' in matched_entities.columns:
            source_chunk_ids.update(matched_entities['chunk_id'].dropna().unique())
        if 'chunk_id' in rels.columns:
            source_chunk_ids.update(rels['chunk_id'].dropna().unique())
        if 'chunk_id' in claims.columns:
            source_chunk_ids.update(claims['chunk_id'].dropna().unique())
        for r in reports:
            source_chunk_ids.update(r.get('source_chunk_ids', []))

        return matched_entities, rels, claims, reports, sorted(list(source_chunk_ids))

def run_local_search(query: str, artifacts_path: str, llm=None, provider: str = None):
    """
    Hàm độc lập để thực thi Local Search.
    Hàm này khởi tạo AdvancedLocalSearch và trả về context cùng source IDs.
    """
    # Khởi tạo các model names
    model_name = "Qwen/Qwen2.5-7B-Instruct"
    embedding_model = VN_EMBEDDING_MODEL

    # Khởi tạo searcher
    search_engine = AdvancedLocalSearch(
        model_name, 
        embedding_model, 
        artifacts_path, 
        llm=llm, 
        provider=provider
    )
    
    # 1. Trích xuất
    extracted_names = search_engine.extract_entities_from_query(query)
    logger.info(f"🔍 Thực thể trích xuất từ query: {extracted_names}")
    
    # 2 & 3. So khớp ngữ nghĩa (Meaning Comparison)
    matched_ents = search_engine.find_best_matches(extracted_names)
    logger.info(f"📍 Đã khớp với {len(matched_ents)} thực thể trong đồ thị.")
    if not matched_ents.empty:
        logger.info(f"Các thực thể khớp nhất:\n{matched_ents[['name', 'description']].to_string()}")
    
    # 4. Gom context và chunk_ids
    ents, rels, claims, reports, source_chunk_ids = search_engine.get_graph_context(matched_ents)
    
    # Xây dựng các phần context riêng lẻ
    context_parts = [
        search_engine._process_entities_context(ents),
        # search_engine._process_relations_context(rels),
        # search_engine._process_claims_context(claims),
        search_engine._process_reports_context(reports)
    ]

    print("\nVăn bản lấy về:")
    print(context_parts)
    
    logger.info(f"✅ Đã thu thập xong context và {len(source_chunk_ids)} source chunk IDs.")
    return context_parts, source_chunk_ids

if __name__ == '__main__':
    # Ví dụ cách sử dụng
    artifacts_path = ARTIFACT_FOLDER 
    
    query = "Nội dung chính của điều 182 của bộ luật Hình sự 2015 là gì?"
    # Gọi hàm run_local_search độc lập
    context_parts, chunk_ids = run_local_search(query, artifacts_path, provider="openai")

    print(context_parts)