import networkx as nx
import pandas as pd
import graspologic_native as gn
from typing import Any
from collections import defaultdict
import html

Communities = list[tuple[int, int, int, list[str]]]

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