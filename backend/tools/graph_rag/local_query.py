import pandas as pd
import numpy as np
import asyncio
import json
from typing import List, Dict, Any
from vllm import LLM, SamplingParams
from transformers import AutoTokenizer
from sentence_transformers import SentenceTransformer
import logging
import os
import pickle

logging.basicConfig(level=logging.INFO)

class AdvancedLocalSearch:
    def __init__(self, model_name: str, embedding_model_name: str, artifacts_path: str):
        # 1. Khởi tạo vLLM cho việc trích xuất và tổng hợp
        self.llm = LLM(model=model_name, trust_remote_code=True, gpu_memory_utilization=0.6)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        # 2. Khởi tạo Embedding Model để so sánh meaning
        self.embed_model = SentenceTransformer(embedding_model_name)

        # 2. LOAD ENCODINGS CÓ SẴN (Step My muốn)
        self.entity_name_embeddings=None
        entity_embeddings_path = f"{artifacts_path}/entity_embeddings"
        if os.path.exists(entity_embeddings_path):
            logging.info("🚀 Đang nạp encodings từ file vật lý...")
            self.entity_name_embeddings = np.load(entity_embeddings_path)
        
        # 3. Load Data từ GraphRAG artifacts
        logging.info("📂 Đang nạp cơ sở dữ liệu đồ thị tri thức...")
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

    async def extract_entities_from_query(self, query: str) -> List[str]:
        """Bước 1: Dùng LLM trích xuất các thực thể quan trọng có trong câu hỏi"""
        system_prompt = """Bạn là trợ lý ngôn ngữ học pháp luật. 
        Nhiệm vụ: Trích xuất các danh từ riêng, thuật ngữ pháp lý hoặc đối tượng quan trọng từ câu hỏi của người dùng.
        Trả về kết quả dưới dạng JSON: {"entities": ["THỰC THỂ 1", "THỰC THỂ 2"]}"""
        
        prompt = self.tokenizer.apply_chat_template(
            [{"role": "system", "content": system_prompt}, {"role": "user", "content": f"Câu hỏi: {query}"}],
            tokenize=False, add_generation_prompt=True
        )
        
        outputs = self.llm.generate([prompt], SamplingParams(temperature=0, max_tokens=256))
        try:
            res_text = outputs[0].outputs[0].text
            # Làm sạch JSON và parse
            clean_json = res_text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_json).get("entities", [])
        except:
            return []

    def find_best_matches(self, extracted_entities: List[str], top_k_per_entity: int = 5) -> pd.DataFrame:
        """Bước 2 & 3: Encode thực thể trích xuất và so sánh similarity với entity_df"""
        if not extracted_entities:
            return pd.DataFrame()

        # Encode các thực thể từ query
        query_embeddings = self.embed_model.encode(extracted_entities)
        
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
            self.claims['subject'].isin(names) | 
            self.claims['object'].isin(names)
        ].head(20)
        
        # Lấy báo cáo cộng đồng theo entities mà có trong nodes (Reports)
        reports = []
        node_names_set = set(names)
    
        for community in self.reports:
            # Lấy list nodes của item đó
            entities_in_community = set(community.get("nodes", []))
            # Kiểm tra xem có node nào chung giữa 2 list không (Giao nhau)
            if not entities_in_community.isdisjoint(node_names_set):
                summary = community.get("report_detail", {}).get("report")
                if summary:
                    reports.append(summary)
        
        return matched_entities, rels, claims, reports

    async def query(self, user_query: str):
        """Hàm chính điều phối toàn bộ luồng Local Search"""
        
        # 1. Trích xuất
        extracted_names = await self.extract_entities_from_query(user_query)
        logging.info(f"🔍 Thực thể trích xuất từ query: {extracted_names}")
        
        # 2 & 3. So khớp ngữ nghĩa (Meaning Comparison)
        matched_ents = self.find_best_matches(extracted_names)
        logging.info(f"📍 Đã khớp với {len(matched_ents)} thực thể trong đồ thị.")
        
        # 4. Gom context
        ents, rels, claims, reports = self.get_graph_context(matched_ents)
        
        # Xây dựng context prompt (giống Reduce step của My)
        context_str = "### THỰC THỂ\n" + "\n".join([f"- {r['name']}: {r['description']}" for _, r in ents.iterrows()])
        context_str += "\n\n### QUAN HỆ\n" + "\n".join([f"- {r['source']} -> {r['target']}: {r['description']}" for _, r in rels.iterrows()])
        context_str += "\n\n### 3. QUY ĐỊNH & CHẾ TÀI CHI TIẾT (CLAIMS)\n"
        if not claims.empty:
            claim_lines = []
            for _, r in claims.iterrows():
                # Kết hợp Subject, Loại quy định và Nội dung chi tiết
                line = f"- [{r['claim_type']}] {r['subject']}: {r['description']}"
                
                # Nếu có trích dẫn nguồn, hãy đưa vào để model "grounding" tốt hơn
                if 'source_text' in r and r['source_text'] not in ['NONE', '']:
                    line += f" (Trích dẫn: {r['source_text']})"
                    
                claim_lines.append(line)
            context_str += "\n".join(claim_lines)
        else:
            context_str += "- Không có dữ liệu quy định chi tiết cho cụm này."
        
        context_str += "\n\n### 4. BÁO CÁO TÓM TẮT CỦA CÁC CỤM CON\n"

        report_entries = []
        for r in reports:
            # Lấy phần detail ra để xử lý cho gọn
            detail = r.get('report_detail', {})
            title = detail.get('title', 'Không có tiêu đề')
            summary = detail.get('summary', 'Không có tóm tắt')
            
            # Tạo chuỗi cho mỗi báo cáo
            entry = f"#### {title}\n{summary}"
            
            # Nếu My muốn lấy thêm cả các 'findings' bên trong JSON để context dày hơn:
            findings = detail.get('findings', [])
            if findings:
                finding_texts = "\n".join([f"- Phát hiện: {f['summary']}" for f in findings[:3]]) # Lấy tối đa 3 phát hiện
                entry += f"\n{finding_texts}"
                
            report_entries.append(entry)

        context_str += "\n---\n".join(report_entries)

        # 5. LLM tổng hợp câu trả lời cuối cùng
        system_prompt = "Bạn là chuyên gia luật. Hãy trả lời câu hỏi dựa trên tổng hợp bối cảnh đồ thị tri thức được cung cấp."
        user_content = f"BỐI CẢNH:\n{context_str}\n\nCÂU HỎI: {user_query}\n\nTRẢ LỜI:"
        
        final_prompt = self.tokenizer.apply_chat_template(
            [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}],
            tokenize=False, add_generation_prompt=True
        )
        
        final_output = self.llm.generate([final_prompt], SamplingParams(temperature=0.3, max_tokens=1024))
        return final_output[0].outputs[0].text

# --- CÁCH CHẠY ---
async def run_local_query(query, artifact_path):
    search_engine = AdvancedLocalSearch(
        model_name="Qwen/Qwen2.5-7B-Instruct",
        embedding_model_name="keepitreal/vietnamese-sbert", # Model embedding tiếng Việt xịn
        artifacts_path="artifact_path"
    )
    
    response = await search_engine.query(query)
    return response

if __name__ == "__main__":
    query = "Người cho vay có quyền đòi lại tài sản trước hạn không?"
    asyncio.run(run_local_query(query))