from services.ast_analysis import analyze_file
from collections import defaultdict


def build_symbol_index(file_entries) -> dict:
    index = {}
    for rel_path, content in file_entries:
        result = analyze_file(rel_path, content)
        data = {
            "classes": result.get("classes", []),
            "methods": result.get("methods", []),
            "functions": result.get("functions", []),
            "imports": result.get("imports", []),
        }
        data["symbols"] = list(data["functions"]) + list(data["methods"])
        index[rel_path] = data
    index["_by_name"] = _build_by_name(index)
    return index


def _build_by_name(index: dict) -> dict:
    """Build name -> [(path, full_symbol)] for cross-file resolution. Exclude key _by_name."""
    by_name = defaultdict(list)
    for path, data in index.items():
        if path == "_by_name":
            continue
        for f in data.get("functions", []):
            by_name[f].append((path, f))
        for m in data.get("methods", []):
            by_name[m].append((path, m))
            short = m.split(".")[-1] if "." in m else m
            if short != m:
                by_name[short].append((path, m))
    return dict(by_name)


def resolve_symbol(callee_name: str, symbol_index: dict) -> list:
    """Resolve callee name to list of (path, full_symbol). Prefer exact match (e.g. Class.method), then short name."""
    by_name = symbol_index.get("_by_name") or _build_by_name({k: v for k, v in symbol_index.items() if k != "_by_name" and isinstance(v, dict)})
    exact = by_name.get(callee_name, [])
    if exact:
        return exact
    return []
