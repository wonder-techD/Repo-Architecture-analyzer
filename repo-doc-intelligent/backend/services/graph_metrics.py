"""
Compute graph metrics from the call graph: in-degree, out-degree, combined centrality,
orchestration hubs (high in AND high out), leaf nodes, cycles.
Structure-based explanations: actual call paths, entry flow, hub dominance, boundary crossings.
"""
from collections import defaultdict


def _node_to_short_label(node: str) -> str:
    if "::" in node:
        path, sym = node.rsplit("::", 1)
        base = path.split("/")[-1].replace(".py", "").replace(".ts", "").replace(".js", "")
        return f"{base}.{sym}" if base else sym
    return node[:30]


def _node_file(node: str) -> str:
    return node.rsplit("::", 1)[0] if "::" in node else ""


def _find_cycles(graph: dict) -> list:
    """Detect cycles using Tarjan's SCC algorithm."""
    nodes = set(graph.keys())
    for callees in graph.values():
        nodes.update(callees)
    full_graph = {n: list(graph.get(n, [])) for n in nodes}
    index = {}
    lowlink = {}
    on_stack = {}
    stack = []
    cycles = []
    next_id = [0]

    def strongconnect(v):
        index[v] = lowlink[v] = next_id[0]
        next_id[0] += 1
        on_stack[v] = True
        stack.append(v)
        for w in full_graph.get(v, []):
            if w not in index:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif on_stack.get(w):
                lowlink[v] = min(lowlink[v], index[w])
        if lowlink[v] == index[v]:
            scc = []
            while True:
                w = stack.pop()
                on_stack[w] = False
                scc.append(w)
                if w == v:
                    break
            if len(scc) > 1:
                cycles.append(scc)
            elif len(scc) == 1 and v in full_graph.get(v, []):
                cycles.append(scc)

    for node in nodes:
        if node not in index:
            strongconnect(node)
    return cycles


def compute_call_graph_metrics(
    callgraph: dict,
    entry_points: list = None,
    file_to_layer: dict = None,
) -> dict:
    """
    Compute in-degree, out-degree, combined score; top 5 central nodes;
    orchestration hubs; leaf nodes; cycles.
    When entry_points and file_to_layer are provided, build structure-based explanation.
    """
    in_degree = defaultdict(int)
    out_degree = defaultdict(int)
    for caller, callees in callgraph.items():
        out_degree[caller] = len(callees)
        for callee in callees:
            in_degree[callee] += 1
    all_nodes = set(in_degree.keys()) | set(out_degree.keys())
    for n in all_nodes:
        in_degree.setdefault(n, 0)
        out_degree.setdefault(n, 0)

    total_edges = sum(out_degree.values())
    total_nodes = len(all_nodes)
    combined = {n: in_degree[n] + out_degree[n] for n in all_nodes}
    top5_central = sorted(all_nodes, key=lambda n: -combined[n])[:5]
    top_centrality_nodes = sorted(all_nodes, key=lambda n: -combined[n])[: max(3, min(5, total_nodes))]
    if len(top_centrality_nodes) < 3 and total_nodes >= 1:
        top_centrality_nodes = sorted(all_nodes, key=lambda n: -combined[n])[: min(3, total_nodes)]

    in_vals = [in_degree[n] for n in all_nodes if in_degree[n] > 0]
    out_vals = [out_degree[n] for n in all_nodes if out_degree[n] > 0]
    in_threshold = max(1, (sum(in_vals) / len(in_vals)) * 0.5) if in_vals else 1
    out_threshold = max(1, (sum(out_vals) / len(out_vals)) * 0.5) if out_vals else 1
    orchestration_hubs = [
        n for n in all_nodes
        if in_degree[n] >= in_threshold and out_degree[n] >= out_threshold
    ]
    orchestration_hubs.sort(key=lambda n: -(in_degree[n] + out_degree[n]))
    if not orchestration_hubs and total_nodes > 0:
        orchestration_hubs = top_centrality_nodes[: max(3, total_nodes)]

    leaf_nodes = [n for n in all_nodes if out_degree[n] == 0]
    max_out = max(out_degree.values()) if out_degree else 0
    orch_out_threshold = max(2, max_out * 0.4) if max_out else 2
    orchestrators_high_out = [n for n in all_nodes if out_degree[n] >= orch_out_threshold]
    orchestrators_high_out.sort(key=lambda n: -out_degree[n])

    cycles = _find_cycles(callgraph)
    cycle_count = len(cycles)

    if entry_points is not None and file_to_layer is not None:
        explanation = _build_structure_explanation(
            callgraph, in_degree, out_degree, orchestration_hubs,
            entry_points, file_to_layer,
        )
    else:
        explanation = _build_centrality_explanation_fallback(
            top_centrality_nodes, in_degree, out_degree, orchestration_hubs
        )

    return {
        "in_degree": dict(in_degree),
        "out_degree": dict(out_degree),
        "combined_score": combined,
        "top5_central_nodes": top5_central[:5],
        "top_centrality_nodes": top_centrality_nodes,
        "centrality_explanation": explanation,
        "orchestration_hubs": orchestration_hubs[:20],
        "orchestrators": orchestrators_high_out[:50],
        "leaf_nodes": leaf_nodes[:100],
        "cycles_detected": cycles[:20],
        "cycle_count": cycle_count,
        "node_count": total_nodes,
        "total_nodes": total_nodes,
        "edge_count": total_edges,
        "total_edges": total_edges,
    }


def _build_structure_explanation(
    callgraph: dict,
    in_degree: dict,
    out_degree: dict,
    orchestration_hubs: list,
    entry_points: list,
    file_to_layer: dict,
) -> str:
    """Describe actual call paths, entry flow, hub dominance, boundary crossings."""
    entry_set = set(entry_points or [])
    parts = []

    entry_nodes = [n for n in callgraph.keys() if _node_file(n) in entry_set]
    if entry_nodes:
        reached = set()
        stack = list(entry_nodes)
        while stack:
            n = stack.pop()
            if n in reached:
                continue
            reached.add(n)
            for c in callgraph.get(n, []):
                stack.append(c)
        path_labels = [_node_to_short_label(n) for n in list(reached)[:8]]
        parts.append(f"Entry flow: from entry-point files ({len(entry_nodes)} nodes), {len(reached)} symbols are reachable. Examples: {', '.join(path_labels)}.")

    paths_desc = []
    for en in entry_nodes[:2]:
        path = [en]
        cur = en
        for _ in range(5):
            callees = callgraph.get(cur, [])
            if not callees:
                break
            cur = callees[0]
            path.append(cur)
        if len(path) > 1:
            paths_desc.append(" → ".join(_node_to_short_label(p) for p in path))
    if paths_desc:
        parts.append(f"Call paths: {'; '.join(paths_desc)}.")

    if orchestration_hubs:
        hub_labels = [_node_to_short_label(h) for h in orchestration_hubs[:5]]
        parts.append(f"Hub dominance: {', '.join(hub_labels)} — these nodes both receive and dispatch many calls; they dominate control flow.")

    boundary_edges = []
    for caller, callees in callgraph.items():
        cl = file_to_layer.get(_node_file(caller), "core")
        for callee in callees:
            cr = file_to_layer.get(_node_file(callee), "core")
            if cl != cr:
                boundary_edges.append((_node_to_short_label(caller), _node_to_short_label(callee), cl, cr))
    if boundary_edges:
        sample = boundary_edges[:3]
        crossing_desc = "; ".join(f"{a} ({sl}) → {b} ({dl})" for a, b, sl, dl in sample)
        parts.append(f"Boundary crossings: {crossing_desc}.")

    return " ".join(parts) if parts else "Insufficient graph data for structure-based explanation."


def _build_centrality_explanation_fallback(
    top_nodes: list,
    in_degree: dict,
    out_degree: dict,
    orchestration_hubs: list,
) -> str:
    """Fallback when entry_points/file_to_layer not provided."""
    parts = []
    for i, node in enumerate(top_nodes[:5], 1):
        inn = in_degree.get(node, 0)
        out = out_degree.get(node, 0)
        label = _node_to_short_label(node)
        if inn > 0 and out > 0:
            parts.append(f"{i}. {label}: hub (in={inn}, out={out}).")
        elif out > 0:
            parts.append(f"{i}. {label}: out-degree {out}.")
        elif inn > 0:
            parts.append(f"{i}. {label}: in-degree {inn}.")
    if orchestration_hubs:
        hub_labels = [_node_to_short_label(h) for h in orchestration_hubs[:5]]
        parts.append(f"Hubs: {', '.join(hub_labels)}.")
    return " ".join(parts) if parts else "Insufficient graph data."
