"""
Clean Mermaid generation: graph LR, subgraphs, shortened labels, max 15 edges when large,
class styling (entry/hub/leaf), no duplicate edges, no self-loops.
Layer Diagram (abstract), Module Dependency Diagram, Representative Call Flow.
"""
import re
from typing import Optional

MAX_NODES_PER_DIAGRAM = 20
MAX_EDGES_CALL_FLOW = 15
MAX_EDGES_WHEN_LARGE = 20


def _clean_label(raw: str) -> str:
    """Convert to clean Mermaid-safe label: no __, no long paths."""
    s = raw.replace("__", ".")
    s = re.sub(r"[^\w.\s-]", " ", s)
    if "::" in s:
        s = s.split("::")[-1]
    if "/" in s:
        s = s.split("/")[-1]
    s = s.replace(".py", "").replace(".ts", "").replace(".js", "")
    s = s.strip()[:25]
    return s or "Node"


def _display_label(full_node: str) -> str:
    """
    Display label only: file basename (no path, no folder prefixes) and symbol.
    Format: Basename::symbol() e.g. StudentsDAO::__construct()
    No normalized ID or path in the label.
    """
    if "::" in full_node:
        path_part, symbol = full_node.rsplit("::", 1)
        base = path_part.replace("\\", "/").split("/")[-1]
        base = re.sub(r"\.(py|ts|tsx|js|jsx|php|java)$", "", base, flags=re.IGNORECASE)
        return f"{base}::{symbol}()"
    base = full_node.replace("\\", "/").split("/")[-1]
    return base or "Node"


def _symbol_name(full_node: str) -> str:
    """Return symbol part only (after ::) or empty."""
    return full_node.rsplit("::", 1)[-1] if "::" in full_node else ""


def _short_display_label(full_node: str, max_len: int = 28) -> str:
    """
    Short display label for diagram: basename::symbol, or symbol() if still too long.
    Full path is kept internally; this is for display only.
    """
    label = _display_label(full_node)
    if len(label) > max_len:
        sym = _symbol_name(full_node)
        return f"{sym}()" if sym else label[:max_len]
    return label


def _second_level_group(full_node: str) -> Optional[str]:
    """
    Return second-level folder (controller, dao, util) if path has at least 2 segments.
    If not (single segment or no path), return None — do not create a single giant subgraph.
    """
    path = full_node.split("::")[0].replace("\\", "/")
    parts = [p for p in path.split("/") if p]
    if len(parts) >= 2:
        return parts[1]
    return None


def _top_level_group(full_node: str) -> tuple[str, str]:
    """
    Return (group_key, subgraph_display_name) for subgraph grouping.
    e.g. apps/web/src/foo.ts -> ("apps/web", "Web"), packages/core -> ("packages/core", "Core").
    """
    path = full_node.split("::")[0].replace("\\", "/")
    parts = [p for p in path.split("/") if p]
    if len(parts) >= 2:
        group_key = f"{parts[0]}/{parts[1]}"
        display = parts[1].capitalize()
    elif len(parts) == 1:
        group_key = parts[0]
        display = parts[0].capitalize()
    else:
        group_key = "root"
        display = "Root"
    return group_key, display


def _to_mermaid_id(prefix: str, index: int) -> str:
    """Node ID only: short stable id, separate from display label. e.g. C0, C1, N0."""
    return f"{prefix}{index}"


def _to_mermaid_id_legacy(label: str, prefix: str, index: int) -> str:
    """Legacy: safe Mermaid node id for layer/module diagrams that need unique ids per label."""
    safe = re.sub(r"[^\w]", "_", label)[:20]
    return f"{prefix}{index}_{safe}"


def generate_layer_diagram_abstract(
    architecture_summary: Optional[dict] = None,
    layer_edges: Optional[list] = None,
) -> Optional[str]:
    """
    Abstract layer diagram: graph LR, subgraph per layer, one edge per layer pair.
    Returns None if no edges exist (hide empty graph).
    """
    if not architecture_summary:
        return None
    layers = architecture_summary.get("layer_order") or architecture_summary.get("layers_detected", [])
    if not layers:
        return None
    if layer_edges is not None and len(layer_edges) == 0:
        return None
    lines = ["graph LR"]
    node_ids = []
    for i, layer in enumerate(layers[:10]):
        lid = _to_mermaid_id_legacy(layer, "L", i)
        node_ids.append(lid)
        label = layer.capitalize()
        lines.append(f"    subgraph {lid}[{label}]")
        lines.append(f"        {lid}_n[{label}]")
        lines.append("    end")
    has_edges = False
    if layer_edges:
        seen = set()
        for (src_l, dst_l) in layer_edges:
            if src_l == dst_l or (src_l, dst_l) in seen:
                continue
            seen.add((src_l, dst_l))
            try:
                si = layers.index(src_l)
                di = layers.index(dst_l)
                lines.append(f"    {node_ids[si]}_n --> {node_ids[di]}_n")
                has_edges = True
            except (ValueError, IndexError):
                pass
    else:
        for i in range(len(node_ids) - 1):
            lines.append(f"    {node_ids[i]}_n --> {node_ids[i+1]}_n")
            has_edges = True
    return "\n".join(lines) if has_edges else None


def generate_module_dependency_clean(
    importgraph: dict,
    file_to_layer: Optional[dict] = None,
    max_nodes: int = MAX_NODES_PER_DIAGRAM,
) -> Optional[str]:
    """
    Module dependency: graph LR, clean labels, max 20 nodes.
    Returns None if no edges exist (hide empty graph).
    """
    if not importgraph:
        return None
    edges = set()
    for src, deps in importgraph.items():
        for d in deps:
            if src != d:
                edges.add((src, d))
    if not edges:
        return None
    if file_to_layer:
        layer_edges = set()
        for src, dst in edges:
            sl, dl = file_to_layer.get(src, "other"), file_to_layer.get(dst, "other")
            if sl != dl:
                layer_edges.add((sl, dl))
        edges = set()
        for sl, dl in layer_edges:
            edges.add((sl, dl))
    if not edges:
        return None
    lines = ["graph LR"]
    nodes = set()
    for e in edges:
        nodes.add(e[0])
        nodes.add(e[1])
    nodes = list(nodes)[:max_nodes]
    node_id = {}
    for i, n in enumerate(nodes):
        node_id[n] = _to_mermaid_id("N", i)
    for n in nodes:
        label = n.replace("\\", "/").split("/")[-1]
        label = re.sub(r"\.(py|ts|tsx|js|jsx|php|java)$", "", label, flags=re.IGNORECASE) or label
        label_escaped = label.replace('"', "#quot;")
        lines.append(f"    {node_id[n]}[\"{label_escaped}\"]")
    seen_e = set()
    for (a, b) in edges:
        if a not in node_id or b not in node_id:
            continue
        key = (node_id[a], node_id[b])
        if key in seen_e:
            continue
        seen_e.add(key)
        lines.append(f"    {node_id[a]} --> {node_id[b]}")
        if len(seen_e) >= max_nodes:
            break
    return "\n".join(lines) if seen_e else None


def _pick_top_edges(
    edges: list,
    metrics: dict,
    max_edges: int,
) -> list:
    """
    When representative_edges > max_edges, keep top max_edges preferring edges
    involving entry points or high centrality nodes. Does not fabricate structure.
    """
    if len(edges) <= max_edges:
        return edges
    entry_set = set(metrics.get("entry_points") or [])
    hubs = set(metrics.get("orchestration_hubs", [])[:10])
    top_central = set(metrics.get("top5_central_nodes", [])[:10])
    preferred = hubs | top_central
    entry_nodes = set()
    for n in set(e[0] for e in edges) | set(e[1] for e in edges):
        path = n.split("::")[0].replace("\\", "/")
        if path in entry_set or any(path.endswith(ep) or ep in path for ep in entry_set):
            entry_nodes.add(n)
    preferred = preferred | entry_nodes

    def score(edge: tuple) -> tuple:
        a, b = edge
        s = 0
        if a in preferred or b in preferred:
            s += 2
        if a in entry_nodes or b in entry_nodes:
            s += 1
        return (-s, edge)

    sorted_edges = sorted(edges, key=score)
    seen = set()
    result = []
    for e in sorted_edges:
        if e[0] == e[1]:
            continue
        if e in seen:
            continue
        seen.add(e)
        result.append(e)
        if len(result) >= max_edges:
            break
    return result


def generate_representative_call_flow(
    callgraph: dict,
    metrics: dict,
    abstracted: bool,
    max_nodes: int = MAX_NODES_PER_DIAGRAM,
    entry_points: Optional[list] = None,
) -> Optional[str]:
    """
    Representative call flow: graph LR, subgraphs by top-level folder, shortened labels,
    max 15 edges when >20, class styling (entry/hub/leaf), no duplicate edges, no self-loops.
    Uses only representative_edges already computed; does not infer layers or invent grouping.
    """
    if abstracted:
        from services.graph_abstraction import get_top_central_subgraph, get_representative_call_edges
        sub = get_top_central_subgraph(callgraph, metrics, max_nodes=max_nodes)
        edges = get_representative_call_edges(callgraph, metrics, max_edges=MAX_EDGES_WHEN_LARGE)
    else:
        sub = dict(list(callgraph.items())[:max_nodes])
        edges = []
        seen = set()
        for c, callees in sub.items():
            for t in callees[:5]:
                if (c, t) not in seen and c != t:
                    edges.append((c, t))
                    seen.add((c, t))
        if not edges:
            for c, callees in sub.items():
                for t in callees:
                    if c != t and (c, t) not in seen:
                        edges.append((c, t))
                        seen.add((c, t))
                    if len(edges) >= max_nodes * 2:
                        break
                if len(edges) >= max_nodes * 2:
                    break

    if not edges:
        return None

    if len(edges) > MAX_EDGES_WHEN_LARGE:
        edges = _pick_top_edges(edges, metrics, MAX_EDGES_CALL_FLOW)

    seen_edges = set()
    unique_edges = []
    for (a, b) in edges:
        if a == b:
            continue
        if (a, b) in seen_edges:
            continue
        seen_edges.add((a, b))
        unique_edges.append((a, b))

    nodes = set()
    for (a, b) in unique_edges:
        nodes.add(a)
        nodes.add(b)
    if not nodes and sub:
        for k in sub:
            nodes.add(k)
            for v in sub[k]:
                nodes.add(v)
    if not nodes:
        return None

    entry_set = set(entry_points or metrics.get("entry_points") or [])
    def _node_in_entry(n: str) -> bool:
        path = n.split("::")[0].replace("\\", "/")
        if path in entry_set:
            return True
        for ep in entry_set:
            ep_n = ep.replace("\\", "/")
            if path == ep_n or path.endswith("/" + ep_n) or ep_n in path:
                return True
        return False

    def _is_construct_only(n: str) -> bool:
        return _symbol_name(n) == "__construct" and not _node_in_entry(n)

    nodes_filtered = {n for n in nodes if not _is_construct_only(n)}
    if nodes_filtered:
        nodes = nodes_filtered
    unique_edges = [(a, b) for (a, b) in unique_edges if a in nodes and b in nodes]
    if not unique_edges and not nodes:
        return None

    nodes = list(nodes)
    if len(nodes) > MAX_NODES_PER_DIAGRAM:
        hubs = set(metrics.get("orchestration_hubs", []) or metrics.get("top5_central_nodes", []))
        entry_nodes_set = {n for n in nodes if _node_in_entry(n)}
        preferred = hubs | entry_nodes_set
        def _node_priority(n: str) -> tuple:
            return (0 if n in preferred else 1, n)
        nodes = sorted(nodes, key=_node_priority)[:MAX_NODES_PER_DIAGRAM]
    else:
        nodes = nodes[:MAX_NODES_PER_DIAGRAM]
    node_set = set(nodes)
    unique_edges = [(a, b) for (a, b) in unique_edges if a in node_set and b in node_set]

    node_id = {}
    for i, n in enumerate(nodes):
        node_id[n] = _to_mermaid_id("C", i)

    group_to_nodes = {}
    for n in nodes:
        gkey = _second_level_group(n)
        group_to_nodes.setdefault(gkey, []).append(n)

    lines = ["graph LR", ""]
    distinct_groups = [k for k in group_to_nodes if k is not None]
    use_subgraphs = len(distinct_groups) >= 2
    if use_subgraphs:
        for gi, gkey in enumerate(distinct_groups):
            group_nodes = group_to_nodes[gkey]
            safe_name = re.sub(r"[^\w]", "_", gkey)[:25]
            sub_id = f"SG_{gi}_{safe_name}"
            display_name = gkey.capitalize()
            lines.append(f"  subgraph {sub_id}[{display_name}]")
            for n in group_nodes:
                if n not in node_id:
                    continue
                label = _display_label(n)
                label_escaped = label.replace('"', "#quot;")
                lines.append(f"    {node_id[n]}[\"{label_escaped}\"]")
            lines.append("  end")
            lines.append("")
        for n in group_to_nodes.get(None, []):
            if n not in node_id:
                continue
            label = _display_label(n)
            label_escaped = label.replace('"', "#quot;")
            lines.append(f"  {node_id[n]}[\"{label_escaped}\"]")
        lines.append("")
    else:
        for n in nodes:
            if n not in node_id:
                continue
            label = _display_label(n)
            label_escaped = label.replace('"', "#quot;")
            lines.append(f"  {node_id[n]}[\"{label_escaped}\"]")
        lines.append("")
    for (a, b) in unique_edges:
        if a not in node_id or b not in node_id:
            continue
        lines.append(f"  {node_id[a]} --> {node_id[b]}")

    out_degree = metrics.get("out_degree") or {}
    entry_nodes = {n for n in nodes if _node_in_entry(n)}
    hub_nodes = set(metrics.get("orchestration_hubs", []) or metrics.get("top5_central_nodes", []))
    hub_nodes = {n for n in nodes if n in hub_nodes}
    leaf_nodes = {n for n in nodes if out_degree.get(n, 0) == 0}

    lines.append("")
    lines.append("  classDef entry fill:#1e293b,stroke:#6366f1,color:#fff;")
    lines.append("  classDef hub fill:#0f172a,stroke:#10b981,color:#fff;")
    lines.append("  classDef leaf fill:#111827,stroke:#64748b,color:#fff;")
    if entry_nodes:
        lines.append("  class " + ",".join(node_id[n] for n in entry_nodes if n in node_id) + " entry")
    if hub_nodes:
        lines.append("  class " + ",".join(node_id[n] for n in hub_nodes if n in node_id) + " hub")
    if leaf_nodes:
        lines.append("  class " + ",".join(node_id[n] for n in leaf_nodes if n in node_id) + " leaf")

    return "\n".join(lines) if (unique_edges or nodes) else None


def generate_mermaid(callgraph: dict, importgraph: dict = None) -> str:
    """Legacy: single combined diagram; use abstracted/simplified data."""
    from services.graph_metrics import compute_call_graph_metrics
    from services.graph_abstraction import should_abstract_call_graph
    metrics = compute_call_graph_metrics(callgraph)
    abstracted = should_abstract_call_graph(metrics["node_count"], metrics["edge_count"])
    return generate_representative_call_flow(callgraph, metrics, abstracted, max_nodes=15)


def generate_call_flow_diagram(callgraph: dict, max_edges: int = 80) -> str:
    """Deprecated: use generate_representative_call_flow via analyze_job."""
    return generate_representative_call_flow(callgraph, {}, False, max_nodes=15)


def generate_module_dependency_diagram(importgraph: dict, max_edges: int = 60) -> str:
    """Deprecated: use generate_module_dependency_clean."""
    return generate_module_dependency_clean(importgraph, None, max_nodes=MAX_NODES_PER_DIAGRAM)


def generate_layer_diagram(
    architecture_summary: Optional[dict] = None,
    importgraph: Optional[dict] = None,
    symbol_index: Optional[dict] = None,
) -> str:
    """Produce abstract layer diagram with subgraphs."""
    layer_edges = None
    if architecture_summary and importgraph:
        from services.graph_abstraction import get_abstract_layer_edges
        from services.architecture_inference import _build_file_to_layer
        sym = symbol_index or architecture_summary.get("symbol_index") or {}
        file_to_layer = _build_file_to_layer(importgraph, sym)
        layer_edges = get_abstract_layer_edges(importgraph, file_to_layer)
    return generate_layer_diagram_abstract(architecture_summary, layer_edges)
