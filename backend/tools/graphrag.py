# # Bước 1: Ép spawn PHẢI là dòng thực thi đầu tiên
# if __name__ == "__main__":
#     try:
#         multiprocessing.set_start_method('spawn', force=True)
#     except RuntimeError:
#         pass
import asyncio
import json
import logging
import multiprocessing
import os
import pickle
import sys
from pathlib import Path
from threading import Lock
import torch

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from langchain.tools import tool
from sklearn.metrics.pairwise import cosine_similarity

# vLLM import ở đây là ổn vì nó sẽ được quản lý bởi spawn
from vllm import LLM, SamplingParams

from backend.tools.graph_rag.chunking import chunk_civil_code_markdown
from backend.tools.graph_rag.chunking import get_law_texts as get_law_texts_external
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

# # 1. Tắt log của transformers để tránh cái warning gây crash kia
# transformers.logging.set_verbosity_error()

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
                os.environ["CUDA_VISIBLE_DEVICES"] = "0" 
                from vllm import LLM
                # 3. Khởi tạo vLLM trên GPU 0
                _llm = LLM(
                    model="Qwen/Qwen2.5-7B-Instruct",
                    tensor_parallel_size=num_gpus if num_gpus > 0 else 1,
                    gpu_memory_utilization=0.8,
                    trust_remote_code=True,
                    # max_model_len=4096,
                )
    return _llm

def get_embedding_model():
    # Chỉ khởi tạo khi tiến trình chính (Main) gọi đến
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer('keepitreal/vietnamese-sbert', device='cuda:1')

def calculate_similarity(text1, text2):
    """Tính toán độ tương đồng ngữ nghĩa giữa hai văn bản."""
    if not text1 or not text2:
        return 0.0
    
    embed_model = get_embedding_model()
    
    # 1. Chuyển văn bản thành vector
    # Chú ý: .encode() của sentence_transformers trả về numpy array
    embeddings = embed_model.encode([text1, text2])
    
    # 2. Tính Cosine Similarity giữa 2 vector
    sim = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
    return float(sim)

async def indexing(output_folder):
    llm = get_llm()

    new_folder_name = output_folder
    # 5. Chunking
    print("Đọc chunks từ file JSON...")
    final_df = None
    try:
        final_df = pd.read_json(f"{output_folder}/chunking_result.json", orient="records")
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy file chunking_result.json trong {output_folder}. Vui lòng chạy lại bước chunking trước.")
        return
    
    print("Ready for extracting entities and relationships...")

    # Đường dẫn model (vLLM hỗ trợ load trực tiếp từ HuggingFace hoặc thư mục local)
    model_path = "Qwen/Qwen2.5-7B-Instruct"

    # Gọi hàm xử lý
    entities_df, relationships_df, claims_df = extract_info_from_chunk(
        text_units = final_df,    
        folder_path = new_folder_name,
        model_path = model_path,
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
    embedding_model_name="keepitreal/vietnamese-sbert"
    embed_model = get_embedding_model()
    entity_name_embeddings = embed_model.encode(entities_df['name'].tolist(), show_progress_bar=True, convert_to_numpy=True)
    # 4. Lưu lại
    np.save(entity_embeddings_folder_name, entity_name_embeddings)
    logging.info(f"Đã lưu embeddings của entities tại: {entity_embeddings_folder_name}")

    # 10. Vẽ đồ thị
    # print("creating graphs...")
    # graph = nx.from_pandas_edgelist(relationships_df, edge_attr=["description", "weight"])
    # # graphml = "\n".join(nx.generate_graphml(graph))
    # # nx.write_graphml(graph, "graph.graphml", encoding="utf-8", prettyprint=True)
    # # Cách 2: Nếu bạn muốn lấy chuỗi string để xử lý tiếp
    # graphml_string = "\n".join(nx.generate_graphml(graph))
    # if not graphml_string.startswith("<?xml"):
    #     header = '<?xml version="1.0" encoding="utf-8"?>\n'
    #     graphml_string = header + graphml_string

    # with open("graph.graphml", "w", encoding="utf-8") as f:
    #     f.write(graphml_string)
    # print("Done creating graphs!")

    # # # Thiết lập kích thước hình vẽ
    # # plt.figure(figsize=(10, 8))
    # # pos = nx.spring_layout(graph) # Thuật toán sắp xếp vị trí các nút
    # # nx.draw(graph, pos, with_labels=True, node_color='lightblue', 
    # #         edge_color='gray', node_size=2000, font_size=10)

    # # # Vẽ trọng số (weight) lên cạnh
    # # labels = nx.get_edge_attributes(graph, 'weight')
    # # nx.draw_networkx_edge_labels(graph, pos, edge_labels=labels)
    # plt.show()

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
        model_name=model_path,
        folder_for_debug=new_folder_name,
        llm=llm
    )

    summaries_path = f"{new_folder_name}/community_summaries.json"
    with open(summaries_path, "w", encoding="utf-8") as f:
        json.dump(reports, f, ensure_ascii=False, indent=4)
    print("Extract community summaries thành công!")
    # summaries_path = "outputs_20260312_001744/community_summaries.json"

    # # print("Run global search...\n")
    # # print(run_global_search("Nội dung chính của điều 182 của bộ luật Hình sự 2015 là gì?", summaries_path, top_k_sources=5))

    # print("Run local search...\n")
    # print(run_local_search("Đang hưởng án treo có được thay đổi nơi cư trú không?", "outputs_20260312_001744"))


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
    
if __name__ == '__main__':
    # 0. Create output_folder
    output_folder = "artifacts"
    Path(output_folder).mkdir(parents=True, exist_ok=True)

    asyncio.run(indexing(output_folder))
    # query = "Được gia hạn tạm giam tối đa bao nhiêu lần để tiến hành điều tra?"
    # query_type, answer = graphrag_retrieval.invoke({
    #             "query": query, 
    #             "output_folder": output_folder
    #         })
    # print(f"For {query}, run {query_type}...")
    # print(f"Answer: {answer}")

# # 2. Đường dẫn file
#     input_questions_path = "dataset/qa.json"
#     output_results_path = f"{output_folder}/final_results_with_qa.json"

#     try:
#         with open(input_questions_path, "r", encoding="utf-8") as f:
#             questions_list = json.load(f)
#     except FileNotFoundError:
#         print(f"❌ Không tìm thấy file {input_questions_path}")
#         questions_list = []

#     final_outputs = []

#     # 4. Lặp qua từng câu hỏi
#     print(f"🚀 Bắt đầu xử lý {len(questions_list)} câu hỏi...")
    
#     for item in questions_list:
#         question = item.get("original_question")
#         gold_answer = item.get("answer", "")
#         gold_truth_references = item.get("references", [])
#         print(f"👉 Đang xử lý: {question}")
        
#         try:
#             # Gọi hàm retrieval
#             # Lưu ý: invoke trả về kết quả cuối cùng từ LLM
#             query_type, answer = graphrag_retrieval.invoke({
#                 "query": question, 
#                 "output_folder": output_folder
#             })

#             # 2. Tính độ tương đồng với gold_answer
#             similarity_score = 0.0
#             if gold_answer:
#                 similarity_score = calculate_similarity(gold_answer, answer)
#                 print(f"📊 Similarity Score: {similarity_score:.4f}")
            
#             # Lưu kết quả vào list
#             final_outputs.append({
#                 "question": question,
#                 "query_type": query_type,
#                 "answer": answer,
#                 "gold_answer": gold_answer,
#                 "gold_truth_references": gold_truth_references,
#                 "similarity_score": round(similarity_score, 4)
#             })
#         except Exception as e:
#             print(f"❌ Lỗi khi xử lý câu hỏi '{question}': {e}")

#     # 5. Lưu toàn bộ kết quả vào file mới
#     with open(output_results_path, "w", encoding="utf-8") as f:
#         json.dump(final_outputs, f, ensure_ascii=False, indent=4)

#     print(f"✅ Hoàn thành! Kết quả đã được lưu tại: {output_results_path}")