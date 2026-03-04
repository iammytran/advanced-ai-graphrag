
import os
import pandas as pd
import tiktoken
import nltk
import asyncio
import json
from google import genai
from openai import AsyncOpenAI
import networkx as nx
import matplotlib.pyplot as plt
import fitz  # PyMuPDF
from pathlib import Path
from pypdf import PdfReader
from glob import glob
from docx import Document
import re
from tqdm import tqdm
import pickle
import graspologic_native as gn
import html
from collections import defaultdict
from typing import List, Optional, Any, Callable, Tuple
from graspologic.partition import hierarchical_leiden
import uuid
from dotenv import load_dotenv
from unsloth import FastLanguageModel
import torch
import logging
import transformers
from datetime import datetime

# 1. Nạp các biến từ tệp .env
load_dotenv()

# 1. Tắt log của transformers để tránh cái warning gây crash kia
transformers.logging.set_verbosity_error()

# 2. Hoặc cấu hình lại logger cơ bản để bỏ qua các tham số thừa
logging.basicConfig(level=logging.ERROR)

Communities = list[tuple[int, int, int, list[str]]]

# Định nghĩa danh sách các loại thực thể phù hợp với Luật
ENTITY_TYPES = "VĂN BẢN QUY PHẠM, ĐIỀU KHOẢN, HÀNH VI CẤM, NGHĨA VỤ, QUYỀN HẠN, ĐỐI TƯỢNG ÁP DỤNG"

GRAPH_PROMPT = f"""
-MỤC TIÊU-
Bạn là một chuyên gia phân tích hệ thống pháp luật. Nhiệm vụ của bạn là trích xuất một Đồ thị tri thức (Knowledge Graph) cực kỳ chi tiết từ văn bản luật được cung cấp. 
KHÔNG ĐƯỢC tóm tắt chung chung. Hãy trích xuất đến cấp độ chi tiết nhất (từng Điều, từng Khoản).

-CÁC BƯỚC THỰC HIỆN-

1. XÁC ĐỊNH THỰC THỂ (ENTITIES):
Duyệt qua văn bản và trích xuất:
- entity_name: Tên thực thể, viết hoa toàn bộ. 
  QUY TẮC QUAN TRỌNG: Đối với các ĐIỀU, KHOẢN, MỤC, chương, phải đính kèm mã hiệu văn bản trong ngoặc đơn.
  Định dạng: "ĐIỀU [Số] ({{doc_name_context}})" hoặc "KHOẢN [Số] ĐIỀU [Số] ({{doc_name_context}})".
  Định dạng: "ĐIỀU [Số] ([Mã hiệu văn bản])"
  Ví dụ: Nếu nguồn là 'Thông tư 01/2020', thực thể phải là "ĐIỀU 1 (TT 01/2020)".
- entity_type: Chọn một trong: [{ENTITY_TYPES}]
- entity_description: Mô tả chi tiết nội dung quy định hoặc chức năng của thực thể đó trong ngữ cảnh văn bản.

Định dạng: ("entity"<|><entity_name><|><entity_type><|><entity_description>)

2. XÁC ĐỊNH MỐI QUAN HỆ (RELATIONSHIPS):
Xác định tất cả các cặp thực thể có liên quan logic. Đặc biệt chú trọng:
- Quan hệ Phân cấp: (KHOẢN 1) thuộc (ĐIỀU 11).
- Quan hệ Trách nhiệm: (CỤC CẢNH SÁT) có trách nhiệm (THEO DÕI VIỆC THI HÀNH).
- Quan hệ Căn cứ: (THÔNG TƯ X) căn cứ vào (LUẬT Y).
- Quan hệ Đối tượng: (ĐIỀU 12) áp dụng cho (CÔNG AN TỈNH).

Định dạng: ("relationship"<|><source_entity><|><target_entity><|><description><|><strength>)
(Strength: thang điểm 1-10 dựa trên độ rõ ràng của mối quan hệ).

3. ĐỊNH DẠNG ĐẦU RA:
- Trả về danh sách duy nhất, các phần tử cách nhau bởi dấu ##.
- Ngôn ngữ: TIẾNG VIỆT hoàn toàn.
- Kết thúc bằng: <|COMPLETE|>

-VÍ DỤ MẪU-
("entity"<|>ĐIỀU 12<|>ĐIỀU KHOẢN<|>Quy định về trách nhiệm thi hành của các đơn vị trực thuộc Bộ)
##
("entity"<|>CỤC CẢNH SÁT QUẢN LÝ TẠM GIỮ<|>CƠ QUAN PHÁP LUẬT<|>Đơn vị chịu trách nhiệm theo dõi, hướng dẫn việc thực hiện thông tư)
##
("relationship"<|>CỤC CẢNH SÁT QUẢN LÝ TẠM GIỮ<|>ĐIỀU 12<|>Cục Cảnh sát quản lý tạm giữ chịu trách nhiệm thực hiện nội dung tại Điều 12<|>9)
<|COMPLETE|>
"""

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
    nltk.download('punkt_tab')

def read_pdf(file_path):
    """Đọc văn bản từ file PDF."""
    text = ""
    with fitz.open(file_path) as doc:
        for page in doc:
            text += page.get_text()
    return text

def read_docx(file_path):
    """Đọc văn bản từ file DOCX."""
    doc = Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])

def ingest_documents_to_df(folder_path: str) -> pd.DataFrame:
    """
    Quét folder và lưu file_name, content vào DataFrame.
    """
    data = []
    folder = Path(folder_path)
    
    # Duyệt qua tất cả các file trong folder
    for file_path in folder.iterdir():
        if file_path.is_file():
            suffix = file_path.suffix.lower()
            content = ""
            
            try:
                if suffix == '.pdf':
                    content = read_pdf(file_path)
                elif suffix == '.docx':
                    content = read_docx(file_path)
                elif suffix in ['.txt', '.md']:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                else:
                    continue # Bỏ qua các file không hỗ trợ
                
                if content.strip():
                    data.append({
                        "file_name": file_path.name,
                        "content": content
                    })
            except Exception as e:
                print(f"Lỗi khi xử lý file {file_path.name}: {e}")

    # Tạo DataFrame
    df = pd.DataFrame(data)
    return df

def get_law_texts():
    scorpus_dir = 'dataset/scorpus'
    df_documents = ingest_documents_to_df(scorpus_dir)

    # Hiển thị kết quả
    print(f"Đã nạp {len(df_documents)} tài liệu.")
    return df_documents

def chunk(text: str,
          encoding_name: str = "cl100k_base",
          chunk_size: int = 1200,
          chunk_overlap: int = 100,
) -> pd.DataFrame :
    encoding = tiktoken.get_encoding(encoding_name)
    # Bước 1: Chia văn bản thành các câu để tránh việc cắt giữa chừng một câu
    sentences = nltk.sent_tokenize(text)

    print(f"sentences: {sentences}")
    
    chunks = []
    current_chunk_sentences = []
    current_tokens = 0
    
    for sentence in sentences:
        sentence_tokens = len(encoding.encode(sentence))
        print(f"cho câu {sentence}, ta có {sentence_tokens} tokens")
        
        # Nếu một câu đơn lẻ dài hơn chunk_size, ta buộc phải cắt theo token
        if sentence_tokens > chunk_size:
            print(f"câu dài hơn chunk_size")
            # Xử lý trường hợp câu quá dài
            if current_chunk_sentences:
                print(f"current_chunk_sentences: {current_chunk_sentences}")
                chunks.append(" ".join(current_chunk_sentences))
                print(f"chunks: {chunks}")
                current_chunk_sentences = []
                current_tokens = 0
            
            # Cắt nhỏ câu quá dài này theo token
            tokens = encoding.encode(sentence)
            for i in range(0, len(tokens), chunk_size - chunk_overlap):
                chunk_tokens = tokens[i : i + chunk_size]
                chunks.append(encoding.decode(chunk_tokens))
            continue

        # Nếu thêm câu này vào mà vượt quá giới hạn, đóng chunk hiện tại
        if current_tokens + sentence_tokens > chunk_size:
            print(f"cộng thêm câu hiện tại vào rổ token mà lớn hơn chunK_size")
            chunks.append(" ".join(current_chunk_sentences))
            
            # Giữ lại một số câu cuối để tạo overlap (tùy chọn đơn giản hóa)
            # Ở đây ta bắt đầu chunk mới
            current_chunk_sentences = [sentence]
            current_tokens = sentence_tokens
        else:
            current_chunk_sentences.append(sentence)
            current_tokens += sentence_tokens

    # Thêm đoạn cuối cùng
    if current_chunk_sentences:
        chunks.append(" ".join(current_chunk_sentences))

    # Chuyển thành định dạng DataFrame giống output của GraphRAG
    output_data = []
    for i, chunk_text in enumerate(chunks):
        output_data.append({
            "id": str(uuid.uuid4()),
            "text": chunk_text,
            "n_tokens": len(encoding.encode(chunk_text))
        })
        
    return pd.DataFrame(output_data)

def vietnamese_legal_chunk(
    legal_df: pd.DataFrame,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
    encoding_name: str = "cl100k_base"
) -> pd.DataFrame:
    encoding = tiktoken.get_encoding(encoding_name)

    text = legal_df['content']
    file_name = legal_df['file_name']
    
    # 1. Tiền xử lý: Chuẩn hóa xuống dòng để tránh các dòng trống vô nghĩa
    text = re.sub(r'\n\s*\n', '\n', text)
    
    # 2. Thay vì dùng nltk, ta dùng Regex để tách theo các dấu hiệu phân đoạn luật
    # Tách theo dấu chấm câu hoặc các tiêu đề "Điều ...", "Chương ..."
    paragraphs = re.split(r'(?<=[.!?])\s+(?=[A-ZÀÁẢÃẠÈÉẺẼẸÌÍỈĨỊÒÓỎÕỌÙÚỦŨỤ])|(?=\nĐiều )', text)
    
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        # Kiểm tra độ dài token của đoạn hiện tại + đoạn mới
        combined_text = (current_chunk + " " + para).strip()
        tokens_count = len(encoding.encode(combined_text))
        
        if tokens_count <= chunk_size:
            current_chunk = combined_text
        else:
            # Lưu chunk hiện tại
            if current_chunk:
                chunks.append(current_chunk)
            
            # Xử lý overlap: Lấy một phần cuối của chunk cũ nối vào chunk mới
            # (Đơn giản hóa: lấy 200 ký tự cuối để giữ ngữ cảnh)
            overlap_text = current_chunk[-chunk_overlap:] if len(current_chunk) > chunk_overlap else ""
            current_chunk = (overlap_text + " " + para).strip()
            
            # Nếu bản thân paragraph đó vẫn quá dài sau khi thêm overlap
            if len(encoding.encode(current_chunk)) > chunk_size:
                # Buộc phải cắt cứng theo token
                tokens = encoding.encode(current_chunk)
                for i in range(0, len(tokens), chunk_size - chunk_overlap):
                    chunk_tokens = tokens[i : i + chunk_size]
                    chunks.append(encoding.decode(chunk_tokens))
                current_chunk = ""

    # Thêm đoạn cuối cùng
    if current_chunk:
        chunks.append(current_chunk)

    # Đóng gói vào DataFrame
    output_data = [{
        "id": str(uuid.uuid4()),
        "text": chunk_text,
        "file_name": file_name,
        "n_tokens": len(encoding.encode(chunk_text))
    } for chunk_text in chunks if len(chunk_text.strip()) > 5] # Loại bỏ các chunk rác quá ngắn
        
    return pd.DataFrame(output_data)

async def extract_entities(text_units: pd.DataFrame,
    text_column: str,
    id_column: str,
    model_name: str = "gemini-1.5-flash", # Hoặc gemini-1.5-pro
    prompt_template: str = "",
    entity_types: List[str] = ["person", "organization", "location"],
    num_threads: int = 100, # Gemini free tier có giới hạn request/phút thấp, nên để thấp
) -> Tuple[pd.DataFrame, pd.DataFrame]:

    # client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    async def call_gemini(text: str):
        # CHÚ Ý: Dùng .aio để gọi bản bất đồng bộ
        response = await client.aio.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"Extract entities and relationships from: {text}",
            config={
                "response_mime_type": "application/json"
            }
        )
        return response.text
    
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    # async def call_gpt(text: str) -> str:
    #     response = await client.responses.create(
    #         model='gpt-5.2',
    #         instructions='Extract entities and relationships of text below. Assign the entities with one of the entity_types. Return output in JSON format: ',
    #         input=f'Entity Types: {entity_types}\nText: {text}',
    #         # response_format={ "type": "json_object" } # Ép GPT trả về JSON chuẩn
    #     )
    #     return response.output_text

    async def call_gpt(text: str, system_prompt, user_content) -> str:
        response = await client.chat.completions.create(
            model='gpt-4o', 
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
        )
        return response.choices[0].message.content
    
    def parse_graph_output(raw_text):
        entities = []
        relationships = []
        
        # Tách theo dấu ##
        segments = raw_text.replace("<|COMPLETE|>", "").split("##")
        
        for seg in segments:
            seg = seg.strip()
            if not seg: continue
            
            # Loại bỏ dấu ngoặc đơn và tách phần tử
        parts = seg.strip("() ").split("<|>")
        
        # Chuẩn hóa tag (loại bỏ dấu nháy kép nếu có)
        tag = parts[0].replace('"', '').strip().lower()

        # Kiểm tra thực thể (cần ít nhất 4 phần tử: tag, name, type, desc)
        if tag == "entity" and len(parts) >= 4:
            entities.append({
                "name": parts[1].strip(),
                "type": parts[2].strip(),
                "description": parts[3].strip()
            })
            
        # Kiểm tra quan hệ (cần ít nhất 5 phần tử: tag, src, tgt, desc, weight)
        elif tag == "relationship" and len(parts) >= 5:
            relationships.append({
                "source": parts[1].strip(),
                "target": parts[2].strip(),
                "description": parts[3].strip(),
                "weight": float(parts[4].strip()) if parts[4].strip().replace('.','',1).isdigit() else 1.0
            })
        else:
            print(f"⚠️ Bỏ qua dòng lỗi định dạng: {seg}")
                
        return entities, relationships

    all_entities = []
    all_relationships = []

    async def sem_process(row):
        async with semaphore:
            text_content = row['text']
            source_id = row['id']
            # Lấy tên văn bản gốc của chunk này (ví dụ: "Thông tư 01/2020/TT-BCA")
            doc_name = row.get('file_name', 'Văn bản gốc') 
            current_system_prompt = GRAPH_PROMPT.replace("{doc_name_context}", doc_name)
            
            # Tiêm tên văn bản vào User Prompt để AI không quên nguồn
            user_content = f"NGUỒN VĂN BẢN: {doc_name}\n\nNỘI DUNG CẦN TRÍCH XUẤT:\n{text_content}"
            print(f"current_system_prompt: {current_system_prompt}")
            print(f"user content: {user_content}")
            
            raw_output = await call_gpt(text_content, current_system_prompt, user_content)
            print(f"raw_output: {raw_output}")
            entities, relations = parse_graph_output(raw_output)
            print(f"entities: {entities}")
            print(f"relations: {relations}")

            
            # Gán source_id để biết thực thể/quan hệ này đến từ chunk nào
            # for e in entities: 
            #     e['source_id'] = source_id
            # for r in relations: 
            #     r['source_id'] = source_id
            
            return entities, relations

    # Chạy song song các task
    semaphore = asyncio.Semaphore(num_threads)
    tasks = [sem_process(row) 
             for _, row in tqdm(text_units.iterrows(),total=len(text_units), desc="Processing chunks")
            ]
    results = await asyncio.gather(*tasks)

    # Gom tất cả kết quả từ các task vào list tổng
    for entities, relations in results:
        all_entities.extend(entities)
        all_relationships.extend(relations)

    # Trả về dưới dạng DataFrame để dễ merge/xử lý sau này
    return all_entities, all_relationships

def detect_communities_leiden(graph: nx.Graph, max_cluster_size: int = 10):
    """
    Phân cụm đồ thị theo phương pháp phân cấp Leiden.
    """
    from graspologic.partition import hierarchical_leiden
    
    # Thực hiện phân cụm
    community_mapping = hierarchical_leiden(graph, max_cluster_size=max_cluster_size)
    
    community_data = []
    
    # SỬA TẠI ĐÂY:
    # community_mapping thường trả về một object có thuộc tính .node_to_community
    # hoặc bạn có thể iterate trực tiếp tùy phiên bản, nhưng an toàn nhất là check attributes
    
    # Thử lấy mapping dictionary từ object trả về
    mapping_dict = {}
    if hasattr(community_mapping, 'node_to_community'):
        mapping_dict = community_mapping.node_to_community
    elif isinstance(community_mapping, dict):
        mapping_dict = community_mapping
    else:
        # Trong một số phiên bản, nó trả về list các cấp độ
        print("Cấu trúc mapping lạ, đang thử convert...")
        # community_mapping có thể được truy cập như một dict trong một số bản cũ hơn 
        # nhưng ở bản mới bạn cần xem nó lưu ở đâu. Thường là:
        mapping_dict = community_mapping

    for node_id, levels in mapping_dict.items():
        # levels thường là một list/tuple chứa community_id của từng cấp độ
        # ví dụ: [comm_level_0, comm_level_1, ...]
        for level, community_id in enumerate(levels):
            community_data.append({
                "node": node_id,
                "community": community_id,
                "level": level
            })
            
    df_communities = pd.DataFrame(community_data)
    
    # Gom nhóm các nodes thuộc cùng một cộng đồng
    communities_summary = df_communities.groupby(['level', 'community'])['node'].apply(list).reset_index()
    
    return communities_summary

def hierarchical_leiden(
    edges: list[tuple[str, str, float]],
    max_cluster_size: int = 10,
    random_seed: int | None = 0xDEADBEEF,
) -> list[gn.HierarchicalCluster]:
    """Run hierarchical leiden on an edge list."""
    return gn.hierarchical_leiden(
        edges=edges,
        max_cluster_size=max_cluster_size,
        seed=random_seed,
        starting_communities=None,
        resolution=1.0,
        randomness=0.001,
        use_modularity=True,
        iterations=1,
    )


def first_level_hierarchical_clustering(
    hcs: list[gn.HierarchicalCluster],
) -> dict[Any, int]:
    """Return the initial leiden clustering as a dict of node id to community id.

    Returns
    -------
    dict[Any, int]
        The initial leiden algorithm clustering results as a dictionary
        of node id to community id.
    """
    return {entry.node: entry.cluster for entry in hcs if entry.level == 0}


def final_level_hierarchical_clustering(
    hcs: list[gn.HierarchicalCluster],
) -> dict[Any, int]:
    """Return the final leiden clustering as a dict of node id to community id.

    Returns
    -------
    dict[Any, int]
        The last leiden algorithm clustering results as a dictionary
        of node id to community id.
    """
    return {entry.node: entry.cluster for entry in hcs if entry.is_final_cluster}

def cluster_graph(
    edges: pd.DataFrame,
    max_cluster_size: int,
    use_lcc: bool,
    seed: int | None = None,
) -> Communities:
    """Apply a hierarchical clustering algorithm to a relationships DataFrame."""
    node_id_to_community_map, parent_mapping = _compute_leiden_communities(
        edges=edges,
        max_cluster_size=max_cluster_size,
        use_lcc=use_lcc,
        seed=seed,
    )

    levels = sorted(node_id_to_community_map.keys())

    clusters: dict[int, dict[int, list[str]]] = {}
    for level in levels:
        result: dict[int, list[str]] = defaultdict(list)
        clusters[level] = result
        for node_id, community_id in node_id_to_community_map[level].items():
            result[community_id].append(node_id)

    results: Communities = []
    for level in clusters:
        for cluster_id, nodes in clusters[level].items():
            results.append((level, cluster_id, parent_mapping[cluster_id], nodes))
    return results


# Taken from graph_intelligence & adapted
def _compute_leiden_communities(
    edges: pd.DataFrame,
    max_cluster_size: int,
    use_lcc: bool,
    seed: int | None = None,
) -> tuple[dict[int, dict[str, int]], dict[int, int]]:
    """Return Leiden root communities and their hierarchy mapping."""
    edge_df = edges.copy()

    # Normalize edge direction and deduplicate (undirected graph).
    # NX deduplicates reversed pairs keeping the last row's attributes,
    # so we replicate that by normalizing direction then keeping last.
    lo = edge_df[["source", "target"]].min(axis=1)
    hi = edge_df[["source", "target"]].max(axis=1)
    edge_df["source"] = lo
    edge_df["target"] = hi
    edge_df.drop_duplicates(subset=["source", "target"], keep="last", inplace=True)

    if use_lcc:
        edge_df = stable_lcc(edge_df)

    weights = (
        edge_df["weight"].astype(float)
        if "weight" in edge_df.columns
        else pd.Series(1.0, index=edge_df.index)
    )
    edge_list: list[tuple[str, str, float]] = sorted(
        zip(
            edge_df["source"].astype(str),
            edge_df["target"].astype(str),
            weights,
            strict=True,
        )
    )

    community_mapping = hierarchical_leiden(
        edge_list, max_cluster_size=max_cluster_size, random_seed=seed
    )
    results: dict[int, dict[str, int]] = {}
    hierarchy: dict[int, int] = {}
    for partition in community_mapping:
        results[partition.level] = results.get(partition.level, {})
        results[partition.level][partition.node] = partition.cluster

        hierarchy[partition.cluster] = (
            partition.parent_cluster if partition.parent_cluster is not None else -1
        )

    return results, hierarchy

def connected_components(
    relationships: pd.DataFrame,
    source_column: str = "source",
    target_column: str = "target",
) -> list[set[str]]:
    """Return all connected components as a list of node-title sets.

    Uses union-find on the deduplicated edge list.

    Parameters
    ----------
    relationships : pd.DataFrame
        Edge list with at least source and target columns.
    source_column : str
        Name of the source node column.
    target_column : str
        Name of the target node column.

    Returns
    -------
    list[set[str]]
        Each element is a set of node titles belonging to one component,
        sorted by descending component size.
    """
    edges = relationships.drop_duplicates(subset=[source_column, target_column])

    # Initialize every node as its own parent
    all_nodes = pd.concat(
        [edges[source_column], edges[target_column]], ignore_index=True
    ).unique()
    parent: dict[str, str] = {node: node for node in all_nodes}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]  # path compression
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    # Union each edge
    for src, tgt in zip(edges[source_column], edges[target_column], strict=True):
        union(src, tgt)

    # Group by root
    groups: dict[str, set[str]] = {}
    for node in parent:
        root = find(node)
        groups.setdefault(root, set()).add(node)

    return sorted(groups.values(), key=len, reverse=True)


def largest_connected_component(
    relationships: pd.DataFrame,
    source_column: str = "source",
    target_column: str = "target",
) -> set[str]:
    """Return the node titles belonging to the largest connected component.

    Parameters
    ----------
    relationships : pd.DataFrame
        Edge list with at least source and target columns.
    source_column : str
        Name of the source node column.
    target_column : str
        Name of the target node column.

    Returns
    -------
    set[str]
        The set of node titles in the largest connected component.
    """
    components = connected_components(
        relationships,
        source_column=source_column,
        target_column=target_column,
    )
    if not components:
        return set()
    return components[0]

def stable_lcc(
    relationships: pd.DataFrame,
    source_column: str = "source",
    target_column: str = "target",
) -> pd.DataFrame:
    """Return the relationships DataFrame filtered to a stable largest connected component.

    Parameters
    ----------
    relationships : pd.DataFrame
        Edge list with at least source and target columns.
    source_column : str
        Name of the source node column.
    target_column : str
        Name of the target node column.

    Returns
    -------
    pd.DataFrame
        A copy of the input filtered to the LCC with normalized node names
        and deterministic edge ordering.
    """
    if relationships.empty:
        return relationships.copy()

    # 1. Normalize node names
    edges = relationships.copy()
    edges[source_column] = edges[source_column].apply(_normalize_name)
    edges[target_column] = edges[target_column].apply(_normalize_name)

    # 2. Filter to the largest connected component
    lcc_nodes = largest_connected_component(
        edges, source_column=source_column, target_column=target_column
    )
    edges = edges[
        edges[source_column].isin(lcc_nodes) & edges[target_column].isin(lcc_nodes)
    ]

    # 3. Stabilize edge direction: lesser node always first
    swapped = edges[source_column] > edges[target_column]
    edges.loc[swapped, [source_column, target_column]] = edges.loc[
        swapped, [target_column, source_column]
    ].to_numpy()

    # 4. Deduplicate edges that were reversed pairs in the original data
    edges = edges.drop_duplicates(subset=[source_column, target_column])

    # 5. Sort for deterministic order
    return edges.sort_values([source_column, target_column]).reset_index(drop=True)


def _normalize_name(name: str) -> str:
    """Normalize a node name: HTML unescape, uppercase, strip whitespace."""
    return html.unescape(name).upper().strip()

import pandas as pd
import asyncio
import json
import os

async def  generate_hierarchical_community_reports(
    community_results: dict, # Kết quả từ _compute_leiden_communities
    community_hierarchy: dict, # Mapping cha-con
    entities_df: pd.DataFrame,
    relationships_df: pd.DataFrame,
    client,
    model_name: str
):
    """
    Tạo báo cáo tóm tắt cho từng cộng đồng theo thứ tự phân cấp.
    """
    # 1. Cấu trúc lại dữ liệu để dễ truy vấn
    # Chuyển results thành danh sách phẳng các cộng đồng kèm danh sách nodes
    communities_list = []
    for level, nodes_map in community_results.items():
        # Gom nhóm nodes theo cluster_id trong mỗi level
        clusters = {}
        for node, cluster_id in nodes_map.items():
            if cluster_id not in clusters: clusters[cluster_id] = []
            clusters[cluster_id].append(node)
        
        for cluster_id, nodes in clusters.items():
            communities_list.append({
                "level": level,
                "community_id": cluster_id,
                "nodes": nodes,
                "parent_id": community_hierarchy.get(cluster_id, -1)
            })

    # 2. Sắp xếp Level từ cao nhất (chi tiết nhất) đến 0 (tổng quát nhất)
    # Ví dụ: [2, 1, 0]
    sorted_levels = sorted(community_results.keys(), reverse=True)
    
    final_reports = []
    report_cache = {} # Lưu report của con để làm input cho cha

    # Semaphore để giới hạn request song song (tránh timeout)
    semaphore = asyncio.Semaphore(10)

    async def summarize_single_community(comm):
        async with semaphore:
            level = comm['level']
            cid = comm['community_id']
            nodes = comm['nodes']
            
            # Xây dựng ngữ cảnh (Context)
            if level == max(sorted_levels):
                # LEVEL CHI TIẾT: Dùng mô tả thực thể gốc
                relevant_entities = entities_df[entities_df['name'].isin(nodes)]
                context = "DANH SÁCH ĐIỀU LUẬT & NỘI DUNG:\n"
                context += "\n".join([f"- {row['name']}: {row['description']}" for _, row in relevant_entities.iterrows()])
            else:
                # LEVEL TỔNG QUÁT: Dùng tóm tắt của các con thuộc cụm này
                sub_reports = [report_cache[n] for n in nodes if n in report_cache]
                context = "TÓM TẮT CÁC CỤM CON THUỘC NHÓM NÀY:\n"
                context += "\n---\n".join(list(set(sub_reports)))

            prompt = f"""
            Bạn là chuyên gia luật. Hãy viết báo cáo tóm tắt cho nhóm cộng đồng sau ở Level {level}.
            Nhiệm vụ:
            1. Xác định 'Thông điệp chính' (Main Messages) của toàn nhóm.
            2. Trích xuất các nghĩa vụ, quyền hạn hoặc hành vi bị cấm quan trọng.
            3. Nếu là tầng tổng quát, hãy kết nối các nội dung con thành một bức tranh hệ thống.
            
            Trả về định dạng:
            - Tiêu đề: [Chủ đề chính]
            - Tóm tắt: [Nội dung chi tiết]
            """

            try:
                response = await client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": f"Dữ liệu nguồn:\n{context}"}
                    ],
                    temperature=0
                )
                report = response.choices[0].message.content
                
                # Cập nhật cache cho tầng cha
                for node in nodes:
                    report_cache[node] = report
                
                return {
                    "level": level,
                    "community": cid,
                    "report": report,
                    "nodes": nodes
                }
            except Exception as e:
                print(f"Lỗi tại cụm {cid} level {level}: {e}")
                return None

    # Chạy tuần tự theo level để đảm bảo cha có report của con
    for current_level in sorted_levels:
        print(f"--- Đang tóm tắt Level {current_level} ---")
        level_comms = [c for c in communities_list if c['level'] == current_level]
        tasks = [summarize_single_community(c) for c in level_comms]
        level_results = await asyncio.gather(*tasks)
        final_reports.extend([r for r in level_results if r])

    return final_reports

async def generate_hierarchical_community_reports_unsloth(
    community_results: dict,
    community_hierarchy: dict, 
    entities_df: pd.DataFrame, # Cần có cột 'degree'
    relationships_df: pd.DataFrame, # Cần có cột 'rank' hoặc 'weight' (Combined Degree)
    model,
    tokenizer,
    max_new_tokens=2048,
    context_window=4096 
):
    # 1. Đảo ngược Level để chạy từ dưới (Lá) lên trên (Gốc)
    sorted_levels = sorted([int(k) for k in community_results.keys()], reverse=True)
    print(f"sorted_levels: {sorted_levels}")
    
    final_reports = []
    report_cache = {} 
    
    FastLanguageModel.for_inference(model)

    for current_level in sorted_levels:
        print(f"--- Đang xử lý Level {current_level} ---")
        
        nodes_in_level = community_results[current_level]
        clusters = {}
        for node, cid in nodes_in_level.items():
            if cid not in clusters: clusters[cid] = []
            clusters[cid].append(node)
        # print(f"clusters: {clusters}")

        level_comms = list(clusters.items())
        batch_size = 4 
        input_text = ""
        
        # Xử lý 1 batch gồm 4 cluster
        for i in tqdm(range(0, len(level_comms), batch_size), desc="Tổng hợp batch", unit="batch"):
            batch = level_comms[i : i + batch_size]
            prompts = []
            
            # Xử lý từng batch
            for cid, nodes in batch:
                # --- PHẦN LOGIC ƯU TIÊN THEO ĐỘ QUAN TRỌNG (DEGREE) ---
                # print(f"cid: {cid}")
                # print(f"nodes: {nodes}")
                
                if current_level == max(sorted_levels):
                    # A. Lọc và Sắp xếp Node theo Degree (Thực thể quan trọng nhất đứng đầu)
                    relevant_entities = entities_df[entities_df['name'].isin(nodes)].copy()
                    if 'degree' in relevant_entities.columns:
                        relevant_entities = relevant_entities.sort_values(by='degree', ascending=False)
                    
                    input_text = "THỰC THỂ (Ưu tiên theo độ quan trọng):\n"
                    input_text += "\n".join([
                        f"ID:{idx}, {r['name']}: {r['description']}" 
                        for idx, r in relevant_entities.iterrows()
                    ])
                    
                    # B. Lọc và Sắp xếp Edge theo Combined Degree (Quan hệ quan trọng nhất đứng đầu)
                    relevant_rel = relationships_df[relationships_df['source'].isin(nodes) | relationships_df['target'].isin(nodes)].copy()
                    
                    # Nếu bạn đã tính sẵn cột 'combined_degree' hoặc 'rank' trong lúc indexing
                    if 'rank' in relevant_rel.columns:
                        relevant_rel = relevant_rel.sort_values(by='rank', ascending=False)
                    elif 'weight' in relevant_rel.columns:
                        relevant_rel = relevant_rel.sort_values(by='weight', ascending=False)
                        
                    input_text += "\n\nQUAN HỆ (Sử dụng ID này để trích dẫn):\n"
                    input_text += "\n".join([f"ID:{idx}, {r['source']} -> {r['target']}: {r['description']}" for idx, r in relevant_rel.iterrows()])

                else:
                    # C. Đối với Level cha: Sắp xếp các cụm con theo độ lớn (Tokens)
                    sub_comm_ids = [child for child, parent in community_hierarchy.items() if str(parent) == str(cid)]
                    
                    # Lấy tóm tắt con và sắp xếp (Cụm con nào dài/quan trọng hơn đưa lên trước)
                    sub_reports = []
                    for scid in sub_comm_ids:
                        if int(scid) in report_cache:
                            sub_reports.append(report_cache[int(scid)])
                    
                    # Sắp xếp theo chiều dài văn bản (một cách proxy cho độ quan trọng ở level cao)
                    sub_reports.sort(key=len, reverse=True)
                    
                    input_text = "BÁO CÁO TÓM TẮT TỪ CÁC CỤM CON (Dữ liệu đã nén):\n"
                    input_text += "\n---\n".join(sub_reports)
                # print(f"input_text: {input_text}")

                # D. Kiểm soát Vali (Context Window): Cắt bỏ những phần ít quan trọng ở cuối danh sách
                tokens = tokenizer.encode(input_text)
                if len(tokens) > (context_window - 800):
                    # Chỉ lấy phần đầu (chứa các thực thể/quan hệ có Degree cao nhất đã được sort ở trên)
                    input_text = tokenizer.decode(tokens[:context_window - 800]) + "\n...(Đã lược bỏ các phần ít quan trọng hơn do vượt dung lượng)..."

                full_prompt =f"""
                    Bạn là một trợ lý AI chuyên gia về hệ thống pháp luật Việt Nam, giúp phân tích và khám phá thông tin trong các văn bản quy phạm pháp luật.
                    Nhiệm vụ của bạn là trích xuất và đánh giá các thông tin liên quan đến các thực thể (ví dụ: Cơ quan nhà nước, tổ chức, cá nhân) và các quy định trong mạng lưới pháp luật.

                    # Mục tiêu
                    Viết một báo cáo toàn diện về một "cụm pháp lý" (community), dựa trên danh sách các thực thể thuộc cụm đó cũng như các mối quan hệ và các tuyên bố (claims) liên quan. 
                    Báo cáo này sẽ được sử dụng để hỗ trợ các nhà hoạch định chính sách, luật sư hoặc người dân hiểu rõ về tác động và nội dung của các quy định. 
                    Nội dung báo cáo phải bao quát được: các thực thể chính, sự tuân thủ pháp lý, thẩm quyền, trách nhiệm, các hành vi bị cấm và các chế tài liên quan.

                    # Cấu trúc báo cáo

                    Báo cáo phải bao gồm các phần sau:

                    - TIÊU ĐỀ: Tên của cụm thực thể đại diện cho các nội dung chính - tiêu đề phải ngắn gọn nhưng cụ thể. Nếu có thể, hãy đưa tên các văn bản luật hoặc cơ quan chủ quản vào tiêu đề.
                    - TÓM TẮT: Bản tóm tắt điều hành về cấu trúc tổng thể của cụm pháp lý, cách các thực thể/điều khoản liên quan đến nhau và các điểm quan trọng nhất.
                    - ĐIỂM ĐÁNH GIÁ TÁC ĐỘNG (IMPACT SEVERITY RATING): Một điểm số thực từ 0-10 đại diện cho mức độ quan trọng hoặc tác động pháp lý của các thực thể/quy định trong cụm. (10 là mức độ quan trọng nhất, ví dụ: các quy định hiến pháp hoặc hình sự nghiêm trọng).
                    - GIẢI THÍCH ĐIỂM ĐÁNH GIÁ: Giải thích bằng một câu duy nhất về lý do đưa ra điểm số tác động đó.
                    - CÁC PHÁT HIỆN CHI TIẾT: Danh sách từ 5-10 thông tin chuyên sâu (insights) về cụm pháp lý. Mỗi phát hiện cần có một phần tóm tắt ngắn, sau đó là các đoạn văn giải thích chi tiết được căn cứ chính xác theo quy tắc trích dẫn bên dưới. Hãy trình bày một cách toàn diện và chặt chẽ.

                    Trả về kết quả dưới dạng chuỗi định dạng JSON chuẩn như sau:
                        {{
                            "title": <tieu_de_bao_cao>,
                            "summary": <tom_tat_dieu_hanh>,
                            "rating": <diem_danh_gia_tac_dong>,
                            "rating_explanation": <giai_thich_diem_danh_gia>,
                            "findings": [
                                {{
                                    "summary": <tom_tat_phat_hien_1>,
                                    "explanation": <giai_thich_chi_tiet_phat_hien_1>
                                }},
                                {{
                                    "summary": <tom_tat_phat_hien_2>,
                                    "explanation": <giai_thich_chi_tiet_phat_hien_2>
                                }}
                            ]
                        }}

                    # Quy tắc trích dẫn (Grounding Rules)

                    Các luận điểm được hỗ trợ bởi dữ liệu phải liệt kê các tham chiếu dữ liệu như sau:

                    "Đây là một câu ví dụ được hỗ trợ bởi nhiều tham chiếu dữ liệu [Data: <tên bộ dữ liệu> (id bản ghi); <tên bộ dữ liệu> (id bản ghi)]."

                    Không liệt kê quá 5 ID bản ghi trong một tham chiếu đơn lẻ. Thay vào đó, hãy liệt kê 5 ID liên quan nhất và thêm "+more" để cho biết còn nhiều hơn thế.

                    Ví dụ:
                    "Cơ quan A có thẩm quyền xử phạt đối với hành vi vi phạm về thuế và chịu trách nhiệm trước Chính phủ [Data: Thực thể (5, 7); Quan hệ (23); Tuyên bố (7, 2, 34, 64, 46, +more)]."

                    Trong đó 1, 5, 7, 23, 2, 34, 46 và 64 đại diện cho ID (không phải index) của bản ghi dữ liệu liên quan.

                    Tuyệt đối không đưa vào các thông tin không có bằng chứng hỗ trợ từ dữ liệu đầu vào.

                    Giới hạn tổng độ dài báo cáo trong khoảng {max_new_tokens} từ.

                    # Dữ liệu thực tế

                    Sử dụng văn bản sau đây để trả lời. Không được tự ý bịa đặt thông tin.

                    Văn bản:
                    {input_text}

                    # YÊU CẦU QUAN TRỌNG: 
                    - Chỉ trả về duy nhất một khối JSON hợp lệ.
                    - Không viết thêm lời chào, không viết phần lưu ý hoặc kết luận sau JSON.
                    - Dừng lại ngay sau khi đóng ngoặc nhọn }} của JSON.

                    Output:"""
                tokens = tokenizer.encode(full_prompt)
                print(f"Chiều dài thực tế của Prompt: {len(tokens)} tokens")
                prompts.append(full_prompt)

            # --- Thực thi LLM ---
            inputs = tokenizer(prompts, return_tensors="pt", padding=True).to("cuda")
            outputs = model.generate(
                input_ids = inputs.input_ids,
                attention_mask = inputs.attention_mask, # Truyền rõ ràng mask ở đây
                max_new_tokens = max_new_tokens,
                use_cache = True,
                temperature = 0.1,
                pad_token_id = tokenizer.pad_token_id
            )
            generated_texts = tokenizer.batch_decode(outputs, skip_special_tokens=True)
            
            for idx, (cid, nodes) in enumerate(batch):
                raw_output = generated_texts[idx]
                # Tạo tên file theo ID của cụm

                print(f"Printing raw_output to file...")
                filename = f"debug_output_cluster_{cid}.txt"
                # Tạo tên file theo ID của cụm
                filename = f"debug_output_cluster_{cid}.txt"
                
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(generated_texts[idx])
                    
                clean_json_str = ""
                try:
                    # Cách 1: Tìm vị trí sau chữ Output:
                    if "Output:" in raw_output:
                        text = raw_output.split("Output:", 1)[-1]
                        # print(f"text:{text}") # Removed for cleaner output

                    start_idx = text.find('{')

                    if start_idx != -1:
                        brace_level = 0
                        found_json_end = -1
                        for i in range(start_idx, len(text)):
                            if text[i] == '{':
                                brace_level += 1
                            elif text[i] == '}':
                                brace_level -= 1
                                if brace_level == 0:
                                    found_json_end = i
                                    break # Found the end of the first complete JSON object
                        
                        if found_json_end != -1:
                            clean_json_str = text[start_idx : found_json_end + 1]

                            # Escape unescaped newlines and tabs within the string to make it valid JSON
                            # This regex replaces newlines not preceded by a backslash with an escaped newline.
                            # This specifically targets newlines inside string values that cause 'Invalid control character' errors.
                            clean_json_str = re.sub(r'(?<!\\)\n', '', clean_json_str)
                            # Also handle tabs if they are unescaped
                            clean_json_str = re.sub(r'(?<!\\)\t', '', clean_json_str)

                        # print(f"DEBUG: String passed to json.loads (first 200 chars): {repr(clean_json_str[:200])}")
                        # return json.loads(clean_json_str)
                except Exception as e:
                    print(f"Không thể trích xuất JSON for : {e}")
                        # return json.loads(clean_json)
                # Tách phần trả lời của Assistant
                # raw_output = generated_texts[idx].split("assistant")[-1].strip()
                # # Tạo tên file theo ID của cụm
                # filename = f"debug_output_cluster_{cid}.txt"
                
                # with open(filename, "w", encoding="utf-8") as f:
                #     f.write(generated_texts[idx])
                
                # # Làm sạch chuỗi nếu AI trả về kèm markdown ```json ... ```
                # clean_json = raw_output.replace("```json", "").replace("```", "").strip()
                
                try:
                    # Chuyển đổi chuỗi text thành Dictionary theo đúng cấu trúc bạn mong muốn
                    data_json = json.loads(clean_json_str)
                    
                    # Lấy phần tóm tắt để làm nguyên liệu nén cho Level cha (cấp 0)
                    summary_for_next_level = data_json.get('summary', "")
                except Exception as e:
                    # Trường hợp AI không trả về JSON chuẩn, tạo một dict giả lập để không lỗi code
                    print(f"Lỗi Parse JSON tại cụm {cid}: {e}")
                    data_json = {
                        "title": "Lỗi định dạng",
                        "summary": raw_output, # Lưu tạm text thô vào đây
                        "rating": 0,
                        "rating_explanation": "Không thể parse JSON từ AI",
                        "findings": []
                    }
                    summary_for_next_level = raw_output

                # Lưu vào danh sách kết quả cuối cùng với đúng cấu trúc bạn yêu cầu
                final_reports.append({
                    "community_id": cid,
                    "level": current_level,
                    "report_detail": data_json, # Đây chính là cục JSON: title, summary, rating...
                    "nodes": nodes
                })
                
                # Lưu vào cache để Level 0 (Cha) sử dụng (Substitution logic)
                # Cấp cha sẽ đọc Summary của con để viết báo cáo tổng quát
                report_cache[cid] = summary_for_next_level

    return final_reports

def save_hierarchical_reports(reports, filename="hierarchical_reports.json"):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(reports, f, ensure_ascii=False, indent=4)
#     print(f"✅ Đã xuất {len(reports)} báo cáo cộng đồng vào {filename}")

def save_full_graph_context(result, hierarchy, filename="graph_context_old_prompt.json"):
    full_context = {
        "community_mapping": result, # {level: {node: cluster_id}}
        "community_hierarchy": hierarchy # {cluster_id: parent_id}
    }
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(full_context, f, ensure_ascii=False, indent=4)


# Ví dụ cách chạy indexing
async def main():
    # # Đảm bảo bạn đã tạo file .env ở thư mục backend và có biến GRAPHRAG_API_KEY
    # api_key = os.getenv("GRAPHRAG_API_KEY")
    # if not api_key:
    #     print("Vui lòng tạo file .env trong thư mục backend và cung cấp GRAPHRAG_API_KEY.")
    # else:
    #     print("Bắt đầu quá trình indexing của GraphRAG...")
    #     result = indexing()
    #     print(result)

    try:
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('tokenizers/punkt_tab')
    except LookupError:
        nltk.download('punkt')
        nltk.download('punkt_tab')
    print("setup okay!")

    # raw_text = """Nikola Tesla là một nhà phát minh người Mỹ gốc Serbia. 
    # Ông nổi tiếng với những đóng góp cho việc thiết kế hệ thống điện xoay chiều (AC) hiện đại. 
    # Hệ thống này đã trở thành tiêu chuẩn cho việc truyền tải điện năng trên toàn thế giới."""

    law_texts_df = get_law_texts()
    print(f"law_texts_df: {law_texts_df}")
    df_chunks_final = pd.DataFrame()
    for index, text_df in tqdm(law_texts_df.iterrows(), total=len(law_texts_df), desc="Chunking law texts"):
        print(f"text_df: {text_df}")
        df_chunks = vietnamese_legal_chunk(text_df, chunk_size=1000, chunk_overlap=100)
        df_chunks_final = pd.concat([df_chunks_final, df_chunks], ignore_index=True)
    #df_chunks = chunk(raw_text, chunk_size=50, chunk_overlap=10)
    print(f"df_chunks: {df_chunks_final}")

    # Gọi hàm trích xuất (Sử dụng hàm standalone mà chúng ta đã thảo luận)
    entities, relationships = await extract_entities(
        text_units=df_chunks_final,
        text_column="text",
        id_column="id",
        model_name="gemini-1.5-flash",
        prompt_template="Extract entities and relationships...",
        entity_types=["person", "organization"]
    )
    
    # print(f"entities: {entities}")
    # print(f"relationships: {relationships}")

    relationships_df = pd.DataFrame(relationships)
    print(f"relationships_df: {relationships_df}")

    print("creating graphs...")
    graph = nx.from_pandas_edgelist(relationships_df, edge_attr=["description", "weight"])
    with open('graph.pkl', 'wb') as file:
        pickle.dump(graph, file)
    print("graph saved successfully.")

    with open('entities.pkl', 'wb') as file:
        pickle.dump(entities, file)
    print("entities saved successfully.")

    with open('relationships.pkl', 'wb') as file:
        pickle.dump(relationships, file)
    print("relationships saved successfully.")
    # graphml = "\n".join(nx.generate_graphml(graph))
    # nx.write_graphml(graph, "graph.graphml", encoding="utf-8", prettyprint=True)
    # Cách 2: Nếu bạn muốn lấy chuỗi string để xử lý tiếp
    graphml_string = "\n".join(nx.generate_graphml(graph))
    if not graphml_string.startswith("<?xml"):
        header = '<?xml version="1.0" encoding="utf-8"?>\n'
        graphml_string = header + graphml_string

    with open("graph.graphml", "w", encoding="utf-8") as f:
        f.write(graphml_string)
    print("Done creating graphs!")

    # # Thiết lập kích thước hình vẽ
    # plt.figure(figsize=(10, 8))

    # # Vẽ đồ thị
    # pos = nx.spring_layout(graph) # Thuật toán sắp xếp vị trí các nút
    # nx.draw(graph, pos, with_labels=True, node_color='lightblue', 
    #         edge_color='gray', node_size=2000, font_size=10)

    # # Vẽ trọng số (weight) lên cạnh
    # labels = nx.get_edge_attributes(graph, 'weight')
    # nx.draw_networkx_edge_labels(graph, pos, edge_labels=labels)


    # result, hierarchy = detect_communities_leiden(graph)

    result, hierarchy = _compute_leiden_communities(relationships_df, max_cluster_size=10, use_lcc=False)
    print(f"result: {result}")
    print(f"hierarchy: {hierarchy}")
    total_communities = len(hierarchy)
    print(f"Tổng số cộng đồng được tạo ra: {total_communities}")
    save_full_graph_context(result, hierarchy)



    plt.show()

    
if __name__ == '__main__':
    # text = get_law_texts()[0]
    # chunks = vietnamese_legal_chunk(text, chunk_size=8000, chunk_overlap=100)
    # print(chunks['text'].tolist()[0])

    # law_texts_df = get_law_texts()
    # df_chunks = []
    # for text in tqdm(law_texts_df):
    #     chunks = vietnamese_legal_chunk(text, chunk_size=8000, chunk_overlap=100)
    #     df_chunks.append(chunks)
    # print(df_chunks)

    # law_texts_df = get_law_texts()
    # print(f"law_texts_df: {law_texts_df}")
    # df_chunks_final = pd.DataFrame()
    # for index, text_df in tqdm(law_texts_df.iterrows(), total=len(law_texts_df), desc="Chunking law texts"):
    #     print(f"text_df: {text_df}")
    #     df_chunks = vietnamese_legal_chunk(text_df, chunk_size=500, chunk_overlap=100)
    #     df_chunks_final = pd.concat([df_chunks_final, df_chunks], ignore_index=True)
    # #df_chunks = chunk(raw_text, chunk_size=50, chunk_overlap=10)
    # print(f"df_chunks: {df_chunks_final}")
    # Đường dẫn đến file pkl của bạn

    # file_path = "graph.pkl"
    # graph = None

    # # Mở và nạp đối tượng
    # with open(file_path, "rb") as f:
    #     graph = pickle.load(f)

    # # Đếm số lượng node không có cạnh nối (degree = 0)
    # isolated_nodes = [node for node, degree in graph.degree() if degree == 0]
    # print(f"Số lượng node bị cô lập: {len(isolated_nodes)}")

    # components = list(nx.connected_components(graph))
    # print(f"Số lượng mảnh rời rạc (Connected Components): {len(components)}")

    # # Xem kích thước của 10 mảnh lớn nhất
    # component_sizes = sorted([len(c) for c in components], reverse=True)
    # print(f"Kích thước các mảnh lớn nhất: {component_sizes[:10]}")

    file_path = "new_prompt_results/relationships.pkl"
    relationships = None

    # Mở và nạp đối tượng
    with open(file_path, "rb") as f:
        relationships = pickle.load(f)

    # Bây giờ bạn có thể sử dụng đối tượng 'obj'
    # print(type(obj))
    relationships_df = pd.DataFrame(relationships)
    # print(relationships_df)

    file_path = "new_prompt_results/entities.pkl"
    entities = None
     # Mở và nạp đối tượng
    with open(file_path, "rb") as f:
        entities = pickle.load(f)

    # Bây giờ bạn có thể sử dụng đối tượng 'obj'
    # print(type(obj))
    relationships_df = pd.DataFrame(relationships)
    entities_df = pd.DataFrame(entities)
    # print(relationships_df.head())
    # print(entities_df.head())

    result, hierarchy = _compute_leiden_communities(relationships_df, max_cluster_size=10, use_lcc=False)
    print(f"result: {result}")
    print(f"hierarchy: {hierarchy}")
    total_communities = len(hierarchy)
    print(f"Tổng số cộng đồng được tạo ra: {total_communities}")

    # 1. Cấu hình thông số
    model_name = "unsloth/meta-llama-3.1-8b-instruct-bnb-4bit"
    max_seq_length = 8192 # Tăng lên 8k để chứa đủ context tóm tắt phân cấp
    max_new_tokens=2048

    # 2. Load model và tokenizer
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name = model_name,
        max_seq_length = max_seq_length,
        load_in_4bit = True, # Giúp chạy nhanh và tiết kiệm VRAM
    )

    # 3. Tối ưu cho Inference
    FastLanguageModel.for_inference(model)

    # 4. Cấu hình Tokenizer để chạy Batch
    tokenizer.padding_side = "left"
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    reports = asyncio.run(generate_hierarchical_community_reports_unsloth(
        community_results=result,
        community_hierarchy=hierarchy,
        entities_df=entities_df,
        relationships_df=relationships_df,
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=max_new_tokens
    ))
    
    # Lưu kết quả ra file JSON để làm dữ liệu cho HippoRAG
    import json
    formatted_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    with open(f"community_reports_{formatted_time}.json", "w", encoding="utf-8") as f:
        json.dump(reports, f, ensure_ascii=False, indent=4)
    # client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # reports = asyncio.run(generate_hierarchical_community_reports(
    #     community_results=result,
    #     community_hierarchy=hierarchy,
    #     entities_df=entities_df,
    #     relationships_df=relationships_df,
    #     client=client,
    #     model_name="gpt-4o"
    # ))

    # # Lưu kết quả ra file JSON
    # with open("community_summaries.json", "w", encoding="utf-8") as f:
    #     json.dump(reports, f, ensure_ascii=False, indent=4)



    # asyncio.run(main())