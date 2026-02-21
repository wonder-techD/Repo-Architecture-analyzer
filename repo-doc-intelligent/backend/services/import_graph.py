import os


def _resolve_import(imp: str, current_file: str, all_paths: set) -> list:
    resolved = []
    current_dir = os.path.dirname(current_file).replace("\\", "/")
    if not current_dir:
        current_dir = "."
    parts = imp.split(".")
    if current_file.endswith(".py"):
        candidate = os.path.join(current_dir, parts[0].replace(".", os.sep) + ".py").replace("\\", "/")
        if candidate in all_paths:
            resolved.append(candidate)
        candidate_flat = (parts[0] + ".py") if parts else ""
        if candidate_flat in all_paths:
            resolved.append(candidate_flat)
        init = os.path.join(current_dir, parts[0], "__init__.py").replace("\\", "/")
        if init in all_paths:
            resolved.append(init)
    if current_file.endswith((".js", ".ts", ".jsx", ".tsx")):
        base = parts[0]
        for ext in ["", ".js", ".ts", ".jsx", ".tsx", "/index.js", "/index.ts"]:
            c = (os.path.join(current_dir, base + ext)).replace("\\", "/")
            if c in all_paths:
                resolved.append(c)
    return resolved


def build_import_graph(symbol_index: dict, repo_root: str) -> dict:
    all_paths = set(symbol_index.keys())
    graph = {}
    for file_path, data in symbol_index.items():
        imports = data.get("imports", [])
        deps = []
        for imp in imports:
            if imp.startswith(".") or "/" in imp or imp in ("sys", "os", "json", "re", "pathlib"):
                continue
            resolved = _resolve_import(imp, file_path, all_paths)
            for r in resolved:
                if r != file_path and r not in deps:
                    deps.append(r)
        graph[file_path] = deps
    return graph
