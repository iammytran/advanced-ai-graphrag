import argparse
import asyncio
import json
import logging
import multiprocessing
import os
import pickle
import shutil
import sys
from pathlib import Path
from threading import Lock
import torch

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from langchain.tools import tool
from sklearn.metrics.pairwise import cosine_similarity

from vllm import LLM, SamplingParams

from backend.config.config import (
    ARTIFACT_FOLDER,
    VLLM_MODEL,
    EMBEDDING_MODEL
)

from backend.tools.graph_rag.compute_leiden_communities import (
    _compute_leiden_communities,
)
from backend.tools.graph_rag.extract_build_graph import extract_info_from_chunk
from backend.tools.graph_rag.generate_community_summary import (
    generate_hierarchical_community_reports,
)
from backend.tools.graph_rag.global_query import run_global_search
from backend.tools.graph_rag.local_query import run_local_search
from backend.tools.graph_rag.query_classifier import query_type_classifier

# 1. Nạp các biến từ tệp .env
load_dotenv()

# 2. Hoặc cấu hình lại logger cơ bản để bỏ qua các tham số thừa
logging.basicConfig(level=logging.ERROR)

_llm = None
_lock = Lock()
# Tự động lấy số GPU khả dụng
num_gpus = torch.cuda.device_count()

def get_llm():
    global _llm
    if _llm is None:
        with _lock:
            if _llm is None:
                # 1. Ép sử dụng kiến trúc V0 (Vô cùng quan trọng)
                os.environ["VLLM_USE_V1"] = "0"
                # 2. Đảm bảo biến môi trường chỉ định rõ 2 GPU
                os.environ["CUDA_VISIBLE_DEVICES"] = "0,1"
                from vllm import LLM
                # 3. Khởi tạo vLLM trên GPU 0
                _llm = LLM(
                    model=VLLM_MODEL,
                    tensor_parallel_size=num_gpus if num_gpus else 1,
                    gpu_memory_utilization=0.8,
                    trust_remote_code=True,
                    distributed_executor_backend="mp",
                    # max_model_len=4096,
                )
    return _llm

def get_embedding_model():
    # Chỉ khởi tạo khi tiến trình chính (Main) gọi đến
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBEDDING_MODEL, device='cuda:1')

async def indexing(output_folder):
    llm = get_llm()

    new_folder_name = output_folder
    # 5. Chunking
    print("Đọc chunks từ file JSON...")
    final_df = None
    try:
        final_df = pd.read_json("dataset/chunking_result.json", orient="records")
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy file chunking_result.json trong {output_folder}. Vui lòng chạy lại bước chunking trước.")
        return
    
    print("Ready for extracting entities and relationships...")

    # Gọi hàm xử lý
    entities_df, relationships_df, claims_df = extract_info_from_chunk(
        text_units = final_df,    
        folder_path = new_folder_name,
        llm=llm
    )

    # 9. Lưu entities và relations sang pickle file
    with open(f'{new_folder_name}/entities.pkl', 'wb') as f:
        pickle.dump(entities_df, f)
    with open(f'{new_folder_name}/relationships.pkl', 'wb') as f:
        pickle.dump(relationships_df, f)
    with open(f'{new_folder_name}/claims.pkl', 'wb') as f:
        pickle.dump(claims_df, f)
    print("Lưu entities, relationships và claims thành công!")

    # 10. Encode các entities
    print("Embed các entities...")
    entity_embeddings_folder_name = f"{new_folder_name}/entity_embeddings"
    embed_model = get_embedding_model()
    entity_name_embeddings = embed_model.encode(entities_df['name'].tolist(), show_progress_bar=True, convert_to_numpy=True)
    # 4. Lưu lại
    np.save(entity_embeddings_folder_name, entity_name_embeddings)
    logging.info(f"Đã lưu embeddings của entities tại: {entity_embeddings_folder_name}")

    # 10. Compute leiden communities
    result, hierarchy = _compute_leiden_communities(relationships_df, max_cluster_size=10, use_lcc=False)
    total_communities = len(hierarchy)

    full_context = {
        "total_communities": total_communities,
        "community_mapping": result, # {level: {node: cluster_id}}
        "community_hierarchy": hierarchy # {cluster_id: parent_id}
    }

    communities_file_name = f"{new_folder_name}/communities.json"
    with open(communities_file_name, 'w', encoding='utf-8') as f:
        json.dump(full_context, f, ensure_ascii=False, indent=4)

    # 11. Tạo community summary
    reports = generate_hierarchical_community_reports(
        community_results=result,
        community_hierarchy=hierarchy,
        entities_df=entities_df,
        relationships_df=relationships_df,
        claims_df=claims_df,
        model_name=VLLM_MODEL,
        folder_for_debug=new_folder_name,
        llm=llm
    )

    summaries_path = f"{new_folder_name}/community_summaries.json"
    with open(summaries_path, "w", encoding="utf-8") as f:
        json.dump(reports, f, ensure_ascii=False, indent=4)
    print("Extract community summaries thành công!")


def format_graphrag_documents(documents: list[str]) -> str:
    formatted_context = ""
    for i, doc in enumerate(documents):
        formatted_context += f"--- Tài liệu {i+1} ---\n{doc}\n\n"
    return formatted_context


@tool
def graphrag_retrieval(query: str, output_folder: str) -> list[str]:
    """Retrieves information using the GraphRAG system."""
    result = query_type_classifier(query)

    print(f"Query: {query}")
    print(f"Quyết định: {result['search_type'].upper()}")
    print(f"Lý do: {result['reason']}")

    if result['search_type'] == "local":
        response = run_local_search(query, output_folder)
    else:
        summaries_path = f"{output_folder}/community_summaries.json"
        response = run_global_search(
            query,
            summaries_path,
            top_k_sources=10,
        )

    return [str(doc) for doc in response]
    
def is_indexing_complete(folder: str) -> bool:
    """Kiểm tra xem các file artifacts cần thiết đã tồn tại hay chưa."""
    if not os.path.exists(folder):
        return False
    
    required_files = [
        'entities.pkl',
        'relationships.pkl',
        'claims.pkl',
        'entity_embeddings.npy',
        'communities.json',
        'community_summaries.json'
    ]
    
    for filename in required_files:
        if not os.path.exists(os.path.join(folder, filename)):
            print(f"Kiểm tra thấy thiếu file index: {filename}")
            return False
            
    return True

if __name__ == '__main__':
    # Thiết lập argparse để xử lý tham số dòng lệnh
    parser = argparse.ArgumentParser(description="GraphRAG Indexing and Querying")
    parser.add_argument(
        '--force-index-from-scratch',
        action='store_true',
        help="Xóa thư mục đầu ra và chạy lại indexing từ đầu."
    )
    parser.add_argument(
        '--output-folder', '-o',
        type=str,
        default='artifacts',
        help="Chỉ định thư mục đầu ra cho indexing. Mặc định là 'artifacts'."
    )
    args = parser.parse_args()

    output_folder = args.output_folder

    # Logic xử lý dựa trên tham số
    if args.force_index_from_scratch:
        print(f"Tham số --force-index-from-scratch được bật cho thư mục '{output_folder}'.")
        if os.path.exists(output_folder):
            print(f"Đang xóa thư mục '{output_folder}'...")
            shutil.rmtree(output_folder)
            print("Đã xóa xong.")
        
        # Tạo lại thư mục và chạy indexing
        Path(output_folder).mkdir(parents=True, exist_ok=True)
        print("Bắt đầu quá trình indexing từ đầu...")
        asyncio.run(indexing(output_folder))
        print(f"Hoàn tất indexing cho '{output_folder}'.")

    else:
        print(f"Kiểm tra trạng thái indexing cho thư mục '{output_folder}'...")
        if is_indexing_complete(output_folder):
            print(f"=> Indexing tại '{output_folder}' đã hoàn thiện. Bỏ qua bước indexing.")
        else:
            print(f"=> Indexing tại '{output_folder}' chưa hoàn thiện hoặc thiếu file. Tự động chạy lại indexing...")
            Path(output_folder).mkdir(parents=True, exist_ok=True)
            asyncio.run(indexing(output_folder))
            print(f"Hoàn tất indexing cho '{output_folder}'.")

    print(f"\nSẵn sàng để query trên bộ index tại: '{output_folder}'")