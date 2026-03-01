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

# 1. Nạp các biến từ tệp .env
load_dotenv()

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
    chunk_size: int = 4096,
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
    model_name: str = "unsloth/qwen2.5-7b-instruct-bnb-4bit",
    prompt_template: str = GRAPH_PROMPT,
    entity_types: List[str] = None, # Sẽ được lấy từ prompt
    batch_size: int = 8, # Số lượng chunk xử lý trong một batch
    num_threads: int = 1, # Không cần nhiều thread vì đã batch
) -> Tuple[pd.DataFrame, pd.DataFrame]:

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name = model_name,
        max_seq_length = 2048,
        load_in_4bit = True,
    )
    FastLanguageModel.for_inference(model)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"

    # Hàm xử lý một batch
    def process_batch(batch_texts, batch_doc_names):
        # 1. Tạo batch prompts
        batch_messages = []
        for text, doc_name in zip(batch_texts, batch_doc_names):
            system_prompt = prompt_template.replace("{doc_name_context}", doc_name)
            user_content = f"NGUỒN VĂN BẢN: {doc_name}\n\nNỘI DUNG CẦN TRÍCH XUẤT:\n{text}"
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ]
            batch_messages.append(messages)

        # 2. Tokenize toàn bộ batch
        inputs = tokenizer.apply_chat_template(
            batch_messages,
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
            return_dict=True,  # <--- BẮT BUỘC PHẢI CÓ DÒNG NÀY
            padding=True,
            truncation=True,
            max_length=2048,
        ).to("cuda")

        # 3. Generate output cho toàn bộ batch
        outputs = model.generate(
            input_ids=inputs.input_ids,
            attention_mask=inputs.attention_mask,
            max_new_tokens=2048, # Tăng lên để chứa đủ output
            use_cache=True,
            pad_token_id=tokenizer.pad_token_id   # Nên thêm để đảm bảo an toàn
        )

        # 4. Decode và tách riêng từng response
        # batch_decode sẽ trả về list các string, mỗi string cho một input trong batch
        decoded_responses = tokenizer.batch_decode(outputs[:, inputs.input_ids.shape[1]:], skip_special_tokens=True)

        return decoded_responses

    def parse_graph_output(raw_text):
        entities = []
        relationships = []
        
        # Tách theo dấu ##
        segments = raw_text.replace("<|COMPLETE|>", "").split("##")
        
        for seg in segments:
            seg = seg.strip()
            if not seg: continue
            
            try:
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
            except (IndexError, ValueError) as e:
                print(f"⚠️ Lỗi parsing dòng: '{seg}'. Lỗi: {e}")
                
        return entities, relationships

    all_entities = []
    all_relationships = []

    # Lặp qua dataframe theo từng batch
    for i in tqdm(range(0, len(text_units), batch_size), desc="Processing batches"):
        batch_df = text_units.iloc[i:i+batch_size]
        
        batch_texts = batch_df[text_column].tolist()
        batch_doc_names = batch_df['file_name'].tolist()

        # Gọi hàm xử lý batch
        raw_outputs = process_batch(batch_texts, batch_doc_names)

        # Parse kết quả cho từng item trong batch
        for raw_output in raw_outputs:
            entities, relations = parse_graph_output(raw_output)
            
            if entities:
                all_entities.extend(entities)
            if relations:
                all_relationships.extend(relations)

    # Trả về dưới dạng DataFrame để dễ merge/xử lý sau này
    return pd.DataFrame(all_entities), pd.DataFrame(all_relationships)

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

async def generate_hierarchical_community_reports(
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

def save_hierarchical_reports(reports, filename="hierarchical_reports.json"):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(reports, f, ensure_ascii=False, indent=4)
    print(f"✅ Đã xuất {len(reports)} báo cáo cộng đồng vào {filename}")

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

    # Gọi hàm trích xuất
    entities, relationships = await extract_entities(
        text_units=df_chunks_final,
        text_column="text",
        id_column="id",
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

    # file_path = "relationships.pkl"
    # relationships = None

    # # Mở và nạp đối tượng
    # with open(file_path, "rb") as f:
    #     relationships = pickle.load(f)

    # # Bây giờ bạn có thể sử dụng đối tượng 'obj'
    # # print(type(obj))
    # relationships_df = pd.DataFrame(relationships)
    # # print(relationships_df)

    # file_path = "entities.pkl"
    # entities = None

    # # Mở và nạp đối tượng
    # with open(file_path, "rb") as f:
    #     entities = pickle.load(f)
    # entities_df = pd.DataFrame(entities)

    # result, hierarchy = _compute_leiden_communities(relationships_df, max_cluster_size=50, use_lcc=False)
    # print(f"result: {result}")
    # print(f"hierarchy: {hierarchy}")
    # total_communities = len(hierarchy)
    # print(f"Tổng số cộng đồng được tạo ra: {total_communities}")
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



    asyncio.run(main())