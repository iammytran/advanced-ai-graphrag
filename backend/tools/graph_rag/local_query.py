import pandas as pd
import numpy as np
from typing import List, Dict, Any
import os

class LocalSearchEngine:
    def __init__(self, 
                 path_entities: str, 
                 path_relationships: str, 
                 path_reports: str, 
                 path_text_units: str,
                 path_embeddings: str):
        # 1. Load toàn bộ dữ liệu Parquet từ output GraphRAG
        self.df_entities = pd.read_parquet(path_entities)
        self.df_relationships = pd.read_parquet(path_relationships)
        self.df_reports = pd.read_parquet(path_reports)
        self.df_text_units = pd.read_parquet(path_text_units)
        
        # 2. Load embeddings của thực thể (đã được export ra file npy hoặc parquet)
        # Thông thường GraphRAG lưu embedding của entity description
        self.entity_embeddings = pd.read_parquet(path_embeddings) 
        
    def get_top_entities(self, query_embedding: np.ndarray, top_k: int = 10) -> pd.DataFrame:
        """Tìm các thực thể có mô tả giống với câu hỏi nhất bằng Vector Search"""
        # Tính cosine similarity giữa query và tất cả thực thể
        embeddings = np.stack(self.entity_embeddings['embedding'].values)
        similarities = np.dot(embeddings, query_embedding) / (
            np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_embedding)
        )
        
        self.entity_embeddings['sim'] = similarities
        top_indices = self.entity_embeddings.sort_values(by='sim', ascending=False).head(top_k)['id'].values
        return self.df_entities[self.df_entities['id'].isin(top_indices)]

    def build_local_context(self, top_entities: pd.DataFrame) -> str:
        """Hàm quan trọng nhất: Gom thông tin lân cận của thực thể trên đồ thị"""
        entity_ids = top_entities['id'].tolist()
        entity_names = top_entities['name'].tolist()

        # A. Lấy các quan hệ trực tiếp (Relationships)
        relevant_rels = self.df_relationships[
            self.df_relationships['source'].isin(entity_names) | 
            self.df_relationships['target'].isin(entity_names)
        ].head(20) # Giới hạn để không tràn context

        # B. Lấy báo cáo cộng đồng (Community Reports)
        # Mỗi thực thể thuộc về 1 hoặc nhiều community, ta lấy report của các cụm đó
        community_ids = top_entities['community'].unique()
        relevant_reports = self.df_reports[self.df_reports['community'].isin(community_ids)].head(5)

        # C. Lấy các đoạn văn bản gốc (Text Units) để đối chiếu
        unit_ids = top_entities['text_unit_ids'].explode().unique()
        relevant_texts = self.df_text_units[self.df_text_units['id'].isin(unit_ids)].head(5)

        # D. Lắp ghép thành chuỗi Context khổng lồ
        context = "### CÁC THỰC THỂ LIÊN QUAN\n"
        for _, row in top_entities.iterrows():
            context += f"- {row['name']} ({row['type']}): {row['description']}\n"

        context += "\n### CÁC MỐI QUAN HỆ PHÁP LÝ\n"
        for _, row in relevant_rels.iterrows():
            context += f"- {row['source']} -> {row['target']}: {row['description']} (Trọng số: {row['weight']})\n"

        context += "\n### TÓM TẮT TỪ CỘNG ĐỒNG LUẬT\n"
        for _, row in relevant_reports.iterrows():
            context += f"#### {row['title']}\n{row['summary']}\n"

        context += "\n### TRÍCH DẪN GỐC TỪ VĂN BẢN\n"
        for _, row in relevant_texts.iterrows():
            context += f"[...] {row['text']} [...]\n"

        return context

    def generate_prompt(self, query: str, context: str) -> str:
        """Tạo prompt cuối cùng để gửi cho vLLM"""
        return f"""Bạn là một trợ lý luật sư ảo. Hãy sử dụng bối cảnh (Context) được trích xuất từ đồ thị tri thức dưới đây để trả lời câu hỏi của người dùng. 
        Nếu thông tin không có trong bối cảnh, hãy ưu tiên trả lời dựa trên kiến thức pháp luật của bạn nhưng phải ghi rõ là 'Ngoài bối cảnh'.

        CONTEXT:
        {context}

        CÂU HỎI: {query}
        TRẢ LỜI:"""

# --- HÀM CHẠY ĐỘC LẬP (STAND-ALONE) ---
async def run_local_query(query_text: str, engine: LocalSearchEngine, embedding_model, llm_model):
    # Bước 1: Tạo embedding cho câu hỏi (My dùng mô hình embedding của My nhé)
    query_vector = embedding_model.encode(query_text)
    
    # Bước 2: Tìm thực thể tương đồng nhất
    top_ents = engine.get_top_entities(query_vector, top_k=5)
    
    # Bước 3: Xây dựng bối cảnh từ đồ thị (Logic lõi của Local Search)
    full_context = engine.build_local_context(top_ents)
    
    # Bước 4: Tạo prompt
    final_prompt = engine.generate_prompt(query_text, full_context)
    
    # Bước 5: Gọi vLLM để lấy câu trả lời cuối cùng
    # response = llm_model.generate(final_prompt, sampling_params)
    return final_prompt # Trả về prompt để My xem thử độ dày của context