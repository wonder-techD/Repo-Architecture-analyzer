"""
Responsibility classification: assign each symbol a role using structural metrics and naming heuristics.
Roles: orchestrator, coordinator, adapter, service, utility, boundary.
"""
from collections import defaultdict


def _node_file(path_symbol: str) -> str:
    if "::" in path_symbol:
        return path_symbol.rsplit("::", 1)[0]
    return ""


def _node_symbol(path_symbol: str) -> str:
    if "::" in path_symbol:
        return path_symbol.rsplit("::", 1)[1]
    return path_symbol


def _path_layer(path: str, file_to_layer: dict) -> str:
    return file_to_layer.get(path, "other")


def _crosses_boundary(caller_path: str, callee_path: str, file_to_layer: dict) -> bool:
    return _path_layer(caller_path, file_to_layer) != _path_layer(callee_path, file_to_layer)


def classify_responsibilities(
    callgraph: dict,
    in_degree: dict,
    out_degree: dict,
    entry_point_files: list,
    file_to_layer: dict,
    symbol_index: dict,
) -> dict:
    """
    Return dict path::symbol -> role.
    Roles: orchestrator, coordinator, adapter, service, utility, boundary.
    """
    entry_set = set(entry_point_files or [])
    roles = {}
    all_nodes = set(callgraph.keys()) | set(in_degree.keys()) | set(out_degree.keys())

    # Boundary crossers: call or are called from another layer
    boundary_callees = set()
    boundary_callers = set()
    for caller, callees in callgraph.items():
        cp = _node_file(caller)
        for callee in callees:
            cep = _node_file(callee)
            if _crosses_boundary(cp, cep, file_to_layer):
                boundary_callers.add(caller)
                boundary_callees.add(callee)

    in_vals = [in_degree.get(n, 0) for n in all_nodes if in_degree.get(n, 0) > 0]
    out_vals = [out_degree.get(n, 0) for n in all_nodes if out_degree.get(n, 0) > 0]
    in_avg = sum(in_vals) / len(in_vals) if in_vals else 0
    out_avg = sum(out_vals) / len(out_vals) if out_vals else 0
    in_hi = max(1, in_avg * 1.5)
    out_hi = max(1, out_avg * 1.5)

    for node in all_nodes:
        path = _node_file(node)
        sym = _node_symbol(node).lower()
        inn = in_degree.get(node, 0)
        out = out_degree.get(node, 0)
        is_entry_file = path in entry_set
        is_boundary_node = node in boundary_callers or node in boundary_callees

        if is_entry_file and (inn > 0 or out > 0):
            roles[node] = "boundary"
        elif is_boundary_node and (inn >= in_hi or out >= out_hi):
            roles[node] = "adapter"
        elif inn >= in_hi and out >= out_hi:
            roles[node] = "orchestrator"
        elif out >= out_hi:
            roles[node] = "coordinator"
        elif "service" in path or "service" in sym or "/service" in path:
            roles[node] = "service"
        elif any(x in sym for x in ("util", "helper", "format", "parse", "validate")):
            roles[node] = "utility"
        elif inn + out <= 2 and any(x in sym for x in ("get", "set", "handle", "on_")):
            roles[node] = "boundary"
        elif is_boundary_node:
            roles[node] = "adapter"
        elif inn + out <= 1:
            roles[node] = "utility"
        else:
            roles[node] = "service"
    return roles
