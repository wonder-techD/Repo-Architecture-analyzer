"""
Graph abstraction: never dump full adjacency. If nodes > 25 or edges > 50,
produce layer/module-level abstraction and representative call flow only.
Otherwise limit to top 15 central nodes.
"""
from collections import defaultdict


def should_abstract_call_graph(node_count: int, edge_count: int) -> bool:
    """If nodes > 20: only generate layer diagram, module dependency, single representative call flow; never full call graph."""
    return node_count > 20 or edge_count > 50


def get_top_central_subgraph(callgraph: dict, metrics: dict, max_nodes: int = 15) -> dict:
    """
    Return a simplified call graph containing only the top max_nodes central nodes
    and edges between them. No full adjacency dump.
    """
    top = list(metrics.get("top5_central_nodes", []))
    combined = metrics.get("combined_score", {})
    if not top and combined:
        top = sorted(combined.keys(), key=lambda n: -combined[n])[:max_nodes]
    if not top:
        for k in list(callgraph.keys())[:max_nodes]:
            top.append(k)
    top_set = set(top)
    result = {}
    for node in top:
        if node not in callgraph:
            result[node] = []
            continue
        callees = [c for c in callgraph[node] if c in top_set]
        result[node] = callees[:10]
    return result


def get_abstract_layer_edges(
    importgraph: dict,
    file_to_layer: dict,
) -> list:
    """
    Aggregate file-level imports to layer-to-layer edges. One edge per (src_layer, dst_layer).
    Removes repeated view→form etc.
    """
    layer_edges = set()
    for src_file, deps in importgraph.items():
        src_layer = file_to_layer.get(src_file, "other")
        for dst_file in deps:
            dst_layer = file_to_layer.get(dst_file, "other")
            if src_layer != dst_layer:
                layer_edges.add((src_layer, dst_layer))
    return list(layer_edges)


def get_representative_call_edges(
    callgraph: dict,
    metrics: dict,
    max_edges: int = 18,
) -> list:
    """
    Representative call flow: edges from top central nodes, deduplicated.
    Prefer edges between orchestration hubs and their callees. No repeated view→form.
    """
    hubs = set(metrics.get("orchestration_hubs", [])[:8])
    top = set(metrics.get("top5_central_nodes", [])[:10])
    candidates = hubs | top
    if not candidates:
        candidates = set(list(callgraph.keys())[:10])
    seen_edges = set()
    result = []
    for caller in candidates:
        if caller not in callgraph:
            continue
        for callee in callgraph[caller]:
            edge = (caller, callee)
            if edge not in seen_edges and len(result) < max_edges:
                seen_edges.add(edge)
                result.append(edge)
    if len(result) < max_edges:
        for caller, callees in callgraph.items():
            for callee in callees:
                edge = (caller, callee)
                if edge not in seen_edges and len(result) < max_edges:
                    seen_edges.add(edge)
                    result.append(edge)
    return result
