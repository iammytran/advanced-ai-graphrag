import argparse
import asyncio
import json
import logging
import os
import pickle
import shutil
from pathlib import Path
from threading import Lock
import torch

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from langchain.tools import tool

from backend.config.config import (
    VLLM_MODEL,
    EMBEDDING_MODEL,
    ARTIFACT_FOLDER
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


def _get_embedding_device_candidates() -> list[str]:
    configured_device = os.getenv("EMBEDDING_DEVICE")
    if configured_device:
        return [configured_device]

    if not torch.cuda.is_available() or num_gpus == 0:
        return ["cpu"]

    min_free_gb = float(os.getenv("EMBEDDING_MIN_FREE_GB", "4"))
    min_free_bytes = min_free_gb * 1024**3
    gpu_candidates: list[tuple[int, int]] = []

    for gpu_idx in range(num_gpus):
        try:
            free_bytes, _ = torch.cuda.mem_get_info(gpu_idx)
        except Exception:
            continue
        if free_bytes >= min_free_bytes:
            gpu_candidates.append((gpu_idx, free_bytes))

    gpu_candidates.sort(key=lambda item: item[1], reverse=True)
    devices = [f"cuda:{gpu_idx}" for gpu_idx, _ in gpu_candidates]
    devices.append("cpu")
    return devices

def get_llm():
    global _llm
    if _llm is None:
        with _lock:
            if _llm is None:
                # 1. Ép sử dụng kiến trúc V0 (Vô cùng quan trọng)
                os.environ["VLLM_USE_V1"] = "0"
                # 2. Tôn trọng cấu hình môi trường hiện có
                if not os.getenv("CUDA_VISIBLE_DEVICES") and num_gpus > 0:
                    os.environ["CUDA_VISIBLE_DEVICES"] = ",".join(str(i) for i in range(num_gpus))
                from vllm import LLM
                tensor_parallel_size = int(os.getenv("VLLM_TENSOR_PARALLEL_SIZE", "1"))
                # 3. Khởi tạo vLLM trên GPU 0
                _llm = LLM(
                    model=VLLM_MODEL,
                    tensor_parallel_size=tensor_parallel_size,
                    gpu_memory_utilization=0.8,
                    trust_remote_code=True,
                    distributed_executor_backend="mp",
                    # max_model_len=4096,
                )
    return _llm

def get_embedding_model():
    # Chỉ khởi tạo khi tiến trình chính (Main) gọi đến
    from sentence_transformers import SentenceTransformer

    candidates = _get_embedding_device_candidates()
    last_error = None

    for device in candidates:
        try:
            print(f"Embedding device: {device}")
            return SentenceTransformer(EMBEDDING_MODEL, device=device)
        except RuntimeError as exc:
            is_cuda_error = "CUDA" in str(exc).upper()
            if device.startswith("cuda") and is_cuda_error:
                print(f"{device} không đủ bộ nhớ hoặc đang bận, thử device khác...")
                last_error = exc
                continue
            raise

    if last_error is not None:
        raise last_error
    raise RuntimeError("Không thể khởi tạo embedding model trên bất kỳ device nào.")

async def indexing(output_folder):
    llm = get_llm()

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
        folder_path = output_folder,
        llm=llm
    )

    # 9. Lưu entities và relations sang pickle file
    with open(f'{output_folder}/entities.pkl', 'wb') as f:
        pickle.dump(entities_df, f)
    with open(f'{output_folder}/relationships.pkl', 'wb') as f:
        pickle.dump(relationships_df, f)
    with open(f'{output_folder}/claims.pkl', 'wb') as f:
        pickle.dump(claims_df, f)
    print("Lưu entities, relationships và claims thành công!")

    # 10. Encode các entities
    print("Embed các entities...")
    entity_embeddings_folder_name = f"{output_folder}/entity_embeddings"
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

    communities_file_name = f"{output_folder}/communities.json"
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
        folder_for_debug=output_folder,
        llm=llm
    )

    summaries_path = f"{output_folder}/community_summaries.json"
    with open(summaries_path, "w", encoding="utf-8") as f:
        json.dump(reports, f, ensure_ascii=False, indent=4)
    print("Extract community summaries thành công!")


def format_graphrag_documents(documents) -> str:
    if not documents:
        return ""
    if isinstance(documents, str):
        return documents

    formatted_context = ""
    for i, doc in enumerate(documents):
        formatted_context += f"--- Tài liệu {i+1} ---\n{doc}\n\n"
    return formatted_context


@tool
def graphrag_retrieval(query: str, output_folder: str) -> tuple[list[str], list]:
    """Retrieves information using the GraphRAG system."""
    result = {}
    with open(f'{ARTIFACT_FOLDER}/entities.pkl', 'rb') as f:
        entities_df = pickle.load(f)
    if entities_df is not None:
        entity_name_list = entities_df['name']
        result = query_type_classifier(query, entity_name_list)
    else:
        result = query_type_classifier(query)

    print(f"Query: {query}")
    print(f"Quyết định: {result['search_type'].upper()}")
    print(f"Lý do: {result['reason']}")

    documents = []
    source_chunk_ids = []
    if result['search_type'] == "local":
        documents, source_chunk_ids = run_local_search(query, output_folder)
    else:
        summaries_path = f"{output_folder}/community_summaries.json"
        documents, source_chunk_ids = run_global_search(
            query,
            summaries_path,
            top_k_sources=10,
        )

    normalized_documents = [str(doc) for doc in (documents or [])]
    return normalized_documents, list(source_chunk_ids or [])
    
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