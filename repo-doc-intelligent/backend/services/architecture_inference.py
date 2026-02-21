"""
Deterministic architecture inference from graph structure.
Explicit rules: import direction, layer dependency, entry points, framework, cycles, centrality.
Produces architecture_summary.json with justified pattern and assessments.
"""
from collections import defaultdict


def _file_to_layer(path: str, symbol_index: dict) -> str:
    """Infer layer from path and symbols."""
    path_lower = path.lower()
    data = symbol_index.get(path, {})
    classes = data.get("classes", [])
    if "view" in path_lower or "views" in path_lower or any("view" in c.lower() for c in classes):
        return "view"
    if "model" in path_lower or "models" in path_lower or any("model" in c.lower() for c in classes):
        return "model"
    if "controller" in path_lower or "controllers" in path_lower:
        return "controller"
    if "service" in path_lower or any("service" in c.lower() for c in classes):
        return "service"
    if "repository" in path_lower or "repo" in path_lower or "dal" in path_lower:
        return "repository"
    if "migration" in path_lower or "migrations" in path_lower:
        return "migration"
    if "form" in path_lower or "forms" in path_lower:
        return "form"
    if "url" in path_lower and "view" not in path_lower:
        return "routing"
    return "other"


def _build_file_to_layer(importgraph: dict, symbol_index: dict) -> dict:
    all_paths = set(importgraph.keys()) | {d for deps in importgraph.values() for d in deps}
    return {p: _file_to_layer(p, symbol_index) for p in all_paths}


def _routing_imports_views(importgraph: dict, file_to_layer: dict) -> bool:
    for src, deps in importgraph.items():
        if file_to_layer.get(src) != "routing":
            continue
        for d in deps:
            if file_to_layer.get(d) == "view":
                return True
    return False


def _views_import_forms_or_models(importgraph: dict, file_to_layer: dict) -> bool:
    for src, deps in importgraph.items():
        if file_to_layer.get(src) != "view":
            continue
        for d in deps:
            if file_to_layer.get(d) in ("form", "model"):
                return True
    return False


def _models_do_not_import_views(importgraph: dict, file_to_layer: dict) -> bool:
    for src, deps in importgraph.items():
        if file_to_layer.get(src) != "model":
            continue
        for d in deps:
            if file_to_layer.get(d) == "view":
                return False
    return True


def _services_between_api_and_persistence(
    importgraph: dict, file_to_layer: dict, symbol_index: dict
) -> bool:
    has_routing_or_view = any(
        file_to_layer.get(p) in ("routing", "view", "controller") for p in importgraph
    )
    has_model_or_repo = any(
        file_to_layer.get(p) in ("model", "repository") for p in importgraph
    )
    has_service = any(file_to_layer.get(p) == "service" for p in importgraph)
    if not (has_service and (has_routing_or_view or has_model_or_repo)):
        return False
    for src, deps in importgraph.items():
        if file_to_layer.get(src) != "service":
            continue
        imports_model = any(file_to_layer.get(d) == "model" for d in deps)
        imports_repo = any(file_to_layer.get(d) == "repository" for d in deps)
        if imports_model or imports_repo:
            return True
    return False


def _detect_dependency_direction(importgraph: dict, file_to_layer: dict) -> str:
    """Dominant dependency direction from import graph."""
    order = {"routing": 0, "view": 1, "controller": 2, "form": 3, "service": 4, "repository": 5, "model": 6, "migration": 7, "other": 8}
    forward = backward = 0
    for src, deps in importgraph.items():
        src_l = order.get(file_to_layer.get(src, "other"), 9)
        for d in deps:
            dst_l = order.get(file_to_layer.get(d, "other"), 9)
            if src_l < dst_l:
                forward += 1
            elif src_l > dst_l:
                backward += 1
    if forward > backward * 1.2:
        return "top_down"
    if backward > forward * 1.2:
        return "bottom_up"
    return "mixed"


def infer_architecture(
    callgraph: dict,
    importgraph: dict,
    metrics: dict,
    symbol_index: dict,
    entry_points: list,
    frameworks: list,
) -> dict:
    """
    Deterministic inference using explicit rules. Returns architecture_summary.json shape:
    architecture_style, dependency_direction, cycles_detected (bool), orchestration_hubs,
    layer_order, coupling_assessment, scalability_assessment.
    """
    file_to_layer = _build_file_to_layer(importgraph, symbol_index)
    layers_seen = set(file_to_layer.values())
    layer_order = [l for l in ["routing", "view", "controller", "form", "service", "repository", "model", "migration", "other"] if l in layers_seen]

    cycles = list(metrics.get("cycles_detected", []))
    cycles_detected = len(cycles) > 0
    orchestration_hubs = list(metrics.get("orchestration_hubs", [])[:20])

    architecture_style = "Unknown"
    if _routing_imports_views(importgraph, file_to_layer) and _views_import_forms_or_models(importgraph, file_to_layer) and _models_do_not_import_views(importgraph, file_to_layer):
        architecture_style = "Layered MVC Monolith"
    if _services_between_api_and_persistence(importgraph, file_to_layer, symbol_index):
        architecture_style = "Service-Repository Layered Architecture"
    if architecture_style == "Unknown":
        if "view" in layers_seen and "model" in layers_seen and ("Django" in frameworks or "Flask" in frameworks):
            architecture_style = "Layered MVC Monolith"
        elif len(layer_order) >= 2:
            architecture_style = "Layered"
        else:
            architecture_style = "Monolith"

    dependency_direction = _detect_dependency_direction(importgraph, file_to_layer)

    coupling_assessment = (
        "Tight coupling detected: cycles in the call graph indicate circular dependencies between modules. Refactoring should break cycles to improve testability and maintainability."
        if cycles_detected
        else "No cycles detected in the call graph. Dependency direction is consistent; coupling appears manageable."
    )

    entry_count = len(entry_points or [])
    if entry_count <= 1 and metrics.get("node_count", 0) > 20:
        scalability_assessment = "Single entry point with large call graph; vertical scaling of the process. Consider horizontal scaling behind a load balancer if stateless."
    elif entry_count > 3:
        scalability_assessment = "Multiple entry points; possible multi-app or microservice layout. Horizontal scaling per service is feasible if boundaries are clear."
    else:
        scalability_assessment = "Moderate complexity; scalability depends on statefulness and external resources. Review entry points and shared state for horizontal scaling."

    layer_files = defaultdict(list)
    for path, layer in file_to_layer.items():
        layer_files[layer].append(path)

    return {
        "architecture_style": architecture_style,
        "dependency_direction": dependency_direction,
        "cycles_detected": cycles_detected,
        "orchestration_hubs": orchestration_hubs,
        "layer_order": layer_order,
        "layers_detected": layer_order,
        "layer_files": {k: v[:50] for k, v in layer_files.items()},
        "coupling_assessment": coupling_assessment,
        "scalability_assessment": scalability_assessment,
        "cycles_list": cycles[:15],
        "entry_point_count": entry_count,
        "frameworks": frameworks,
    }
