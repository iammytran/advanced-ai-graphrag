import asyncio
import json
import logging
import multiprocessing
import pickle
from pathlib import Path
from threading import Lock

import numpy as np
import pandas as pd
import transformers
from dotenv import load_dotenv
from langchain.tools import tool
from sentence_transformers import SentenceTransformer

# Ép dùng spawn trước khi import vllm
try:
    multiprocessing.set_start_method('spawn', force=True)
except RuntimeError:
    pass


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

# 1. Nạp các biến từ tệp .env
load_dotenv()

# 1. Tắt log của transformers để tránh cái warning gây crash kia
transformers.logging.set_verbosity_error()

# 2. Hoặc cấu hình lại logger cơ bản để bỏ qua các tham số thừa
logging.basicConfig(level=logging.ERROR)

_llm = None
_lock = Lock()

def get_llm():
    global _llm
    if _llm is None:
        with _lock:
            if _llm is None:
                from vllm import LLM, SamplingParams
                _llm = LLM(
                    model="Qwen/Qwen2.5-14B-Instruct",
                    tensor_parallel_size=1,
                    gpu_memory_utilization=0.6,
                    trust_remote_code=True,
                )
    return _llm

def graphrag_manager(query: str, llm):
    """
    Sử dụng thư viện vLLM để xác định loại query cho GraphRAG.
    """
    # Thiết lập tham số lấy mẫu
    sampling_params = SamplingParams(
        temperature=0.0,  # Để kết quả ổn định nhất cho việc phân loại
        max_tokens=200,
        stop=["}"],       # Dừng ngay khi đóng JSON
    )

    prompt_template = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
    Bạn là một chuyên gia điều phối hệ thống GraphRAG. Bạn chỉ được phép trả về định dạng JSON.
    Nhiệm vụ: Xác định câu hỏi dùng 'local' hay 'global' search.
    - 'local': Hỏi về thực thể cụ thể, người, vật, địa điểm, chi tiết sâu.
    - 'global': Hỏi về chủ đề chung, tóm tắt toàn bộ dữ liệu, xu hướng.
    Trả về JSON: {{"search_type": "local" | "global", "reason": "giải thích"}}<|eot_id|>
    <|start_header_id|>user<|end_header_id|>
    Câu hỏi người dùng: "{query}"<|message_end|>
    <|start_header_id|>assistant<|end_header_id|>
    """

    # Thực hiện inference
    outputs = llm.generate([prompt_template], sampling_params)
    
    # Xử lý kết quả trả về
    generated_text = outputs[0].outputs[0].text + "}" # Thêm lại dấu ngoặc do stop word
    
    try:
        # Làm sạch chuỗi nếu model trả về thừa ký tự
        start_idx = generated_text.find('{')
        end_idx = generated_text.rfind('}') + 1
        json_str = generated_text[start_idx:end_idx]
        
        decision = json.loads(json_str)
        return decision
    except Exception as e:
        print(f"Lỗi parse JSON: {e}. Raw: {generated_text}")
        return {"search_type": "local", "reason": "error fallback"}

async def indexing(output_folder):
    # llm = get_llm()

    # new_folder_name = output_folder
    # # 5. Chunking
    # print("Chunking...")
    # law_texts_df = get_law_texts_external()
    # law_texts_df["chunk"] = law_texts_df["content"].apply(chunk_civil_code_markdown)

    # new_df = law_texts_df.explode('chunk', ignore_index=True)

    # # 6. (Tùy chọn) Nếu bạn muốn bung các key trong dict của chunk 
    # # (như 'chuong', 'dieu') ra thành các cột riêng biệt:
    # chunk_details = pd.json_normalize(new_df['chunk'])

    # # 7. Đổi tên cột 'content' thành 'chunk' (nếu trong dict key là 'content')
    # chunk_details = chunk_details.rename(columns={'content': 'chunk'})

    # final_df = pd.concat([new_df[['file_name']], chunk_details], axis=1)
    # print("Ready for extracting entities and relationships...")

    # # Đường dẫn model (vLLM hỗ trợ load trực tiếp từ HuggingFace hoặc thư mục local)
    # model_path = "Qwen/Qwen2.5-7B-Instruct"

    # # Gọi hàm xử lý
    # entities_df, relationships_df, claims_df = extract_info_from_chunk(
    #     text_units = final_df,    
    #     folder_path = new_folder_name,
    #     model_path = model_path,
    #     llm=llm
    # )

    # # 9. Lưu entities và relations sang pickle file
    # with open(f'{new_folder_name}/entities.pkl', 'wb') as f:
    #     pickle.dump(entities_df, f)
    # with open(f'{new_folder_name}/relationships.pkl', 'wb') as f:
    #     pickle.dump(relationships_df, f)
    # with open(f'{new_folder_name}/claims.pkl', 'wb') as f:
    #     pickle.dump(claims_df, f)
    # print("Lưu entities, relationships và claims thành công!")

    # # 10. Encode các entities
    # print("Embed các entities...")
    # entity_embeddings_folder_name = f"{new_folder_name}/entity_embeddings"
    # embedding_model_name="keepitreal/vietnamese-sbert"
    # embed_model = SentenceTransformer(embedding_model_name)
    # entity_name_embeddings = embed_model.encode(entities_df['name'].tolist(), show_progress_bar=True, convert_to_numpy=True)
    # # 4. Lưu lại
    # np.save(entity_embeddings_folder_name, entity_name_embeddings)
    # logging.info(f"Đã lưu embeddings của entities tại: {entity_embeddings_folder_name}")

    # # 10. Vẽ đồ thị
    # # print("creating graphs...")
    # # graph = nx.from_pandas_edgelist(relationships_df, edge_attr=["description", "weight"])
    # # # graphml = "\n".join(nx.generate_graphml(graph))
    # # # nx.write_graphml(graph, "graph.graphml", encoding="utf-8", prettyprint=True)
    # # # Cách 2: Nếu bạn muốn lấy chuỗi string để xử lý tiếp
    # # graphml_string = "\n".join(nx.generate_graphml(graph))
    # # if not graphml_string.startswith("<?xml"):
    # #     header = '<?xml version="1.0" encoding="utf-8"?>\n'
    # #     graphml_string = header + graphml_string

    # # with open("graph.graphml", "w", encoding="utf-8") as f:
    # #     f.write(graphml_string)
    # # print("Done creating graphs!")

    # # # # Thiết lập kích thước hình vẽ
    # # # plt.figure(figsize=(10, 8))
    # # # pos = nx.spring_layout(graph) # Thuật toán sắp xếp vị trí các nút
    # # # nx.draw(graph, pos, with_labels=True, node_color='lightblue', 
    # # #         edge_color='gray', node_size=2000, font_size=10)

    # # # # Vẽ trọng số (weight) lên cạnh
    # # # labels = nx.get_edge_attributes(graph, 'weight')
    # # # nx.draw_networkx_edge_labels(graph, pos, edge_labels=labels)
    # # plt.show()

    # # 10. Compute leiden communities
    # result, hierarchy = _compute_leiden_communities(relationships_df, max_cluster_size=10, use_lcc=False)
    # total_communities = len(hierarchy)

    # full_context = {
    #     "total_communities": total_communities,
    #     "community_mapping": result, # {level: {node: cluster_id}}
    #     "community_hierarchy": hierarchy # {cluster_id: parent_id}
    # }

    # communities_file_name = f"{new_folder_name}/communities.json"
    # with open(communities_file_name, 'w', encoding='utf-8') as f:
    #     json.dump(full_context, f, ensure_ascii=False, indent=4)

    # # 11. Tạo community summary
    # reports = generate_hierarchical_community_reports(
    #     community_results=result,
    #     community_hierarchy=hierarchy,
    #     entities_df=entities_df,
    #     relationships_df=relationships_df,
    #     claims_df=claims_df,
    #     model_name=model_path,
    #     folder_for_debug=new_folder_name,
    #     llm=llm
    # )

    # summaries_path = f"{new_folder_name}/community_summaries.json"
    # with open(summaries_path, "w", encoding="utf-8") as f:
    #     json.dump(reports, f, ensure_ascii=False, indent=4)
    # print("Extract community summaries thành công!")
    # summaries_path = "outputs_20260312_001744/community_summaries.json"

    print("Run global search...\n")
    # # print(run_global_search("Nội dung chính của điều 182 của bộ luật Hình sự 2015 là gì?", summaries_path, 5))

    # # print("Run local search...\n")
    # # print(run_local_search("Đang hưởng án treo có được thay đổi nơi cư trú không?", "outputs_20260312_001744"))


@tool
def graphrag_retrieval(query: str, output_folder: str) -> str:
    """Retrieves information using the GraphRAG system."""
    graphrag_manager = get_llm()
    result = graphrag_manager(query, graphrag_manager)

    print(f"Query: {query}")
    print(f"Quyết định: {result['search_type'].upper()}")
    print(f"Lý do: {result['reason']}")

    # Tích hợp gọi GraphRAG
    response = None
    if result['search_type'] == "local":
        response = run_local_search(query, output_folder, graphrag_manager)
    else:
        summaries_path = f"{output_folder}/community_summaries.json"
        response = run_global_search(query, summaries_path, 10, graphrag_manager)
    return response
    
if __name__ == '__main__':
    # 0. Create output_folder
    output_folder = "outputs_20260312_001744"
    Path(output_folder).mkdir(parents=True, exist_ok=True)

    # asyncio.run(indexing(output_folder))

    query = "Nội dung chính của điều 182 của bộ luật Hình sự 2015 là gì?"
    print(graphrag_retrieval.invoke({"query": f"{query}", "output_folder": f"{output_folder}"}))