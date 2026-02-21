"""
Call graph: function-to-function and method ownership, cross-file symbol resolution.
Nodes: path::symbol (symbol = function name or Class.method). Edges: caller -> callees.
Computes in-degree, out-degree, and centrality; returns graph plus metrics.
"""
from collections import defaultdict

from services.ast_analysis import analyze_file
from services.symbol_index import resolve_symbol


def build_call_graph(file_entries, symbol_index: dict = None) -> dict:
    """
    Build call graph with nodes path::symbol (function or Class.method).
    Uses symbol_calls when available for function-to-function edges; resolves callees
    via symbol_index for cross-file resolution. Falls back to file-level call matching.
    """
    file_to_data = {}
    for rel_path, content in file_entries:
        result = analyze_file(rel_path, content)
        symbols = list(result.get("functions", [])) + list(result.get("methods", []))
        file_to_data[rel_path] = {
            "functions": result.get("functions", []),
            "methods": result.get("methods", []),
            "symbols": symbols,
            "calls": result.get("calls", []),
            "symbol_calls": result.get("symbol_calls", []),
        }

    graph = {}
    # Ensure every symbol is a node
    for rel_path, data in file_to_data.items():
        for s in data["symbols"]:
            key = f"{rel_path}::{s}"
            graph[key] = []

    for rel_path, data in file_to_data.items():
        symbol_calls = data.get("symbol_calls") or []
        if symbol_calls and symbol_index:
            for caller, callee_name in symbol_calls:
                caller_key = f"{rel_path}::{caller}"
                if caller_key not in graph:
                    graph[caller_key] = []
                resolved = resolve_symbol(callee_name, symbol_index)
                for path, full_symbol in resolved:
                    callee_key = f"{path}::{full_symbol}"
                    if callee_key != caller_key and callee_key not in graph.get(caller_key, []):
                        graph[caller_key].append(callee_key)
        elif symbol_calls:
            for caller, callee_name in symbol_calls:
                caller_key = f"{rel_path}::{caller}"
                if caller_key not in graph:
                    graph[caller_key] = []
                for other_path, other_data in file_to_data.items():
                    if callee_name in other_data["symbols"]:
                        callee_key = f"{other_path}::{callee_name}"
                        if callee_key != caller_key and callee_key not in graph.get(caller_key, []):
                            graph[caller_key].append(callee_key)
                        break
        else:
            for sym in data["symbols"]:
                caller_key = f"{rel_path}::{sym}"
                if caller_key not in graph:
                    graph[caller_key] = []
                for callee_name in data["calls"]:
                    if symbol_index:
                        resolved = resolve_symbol(callee_name, symbol_index)
                        for path, full_symbol in resolved:
                            callee_key = f"{path}::{full_symbol}"
                            if callee_key != caller_key and callee_key not in graph.get(caller_key, []):
                                graph[caller_key].append(callee_key)
                    else:
                        for other_path, other_data in file_to_data.items():
                            if callee_name in other_data["symbols"]:
                                callee_key = f"{other_path}::{callee_name}"
                                if callee_key != caller_key and callee_key not in graph.get(caller_key, []):
                                    graph[caller_key].append(callee_key)
                                break
    return graph


def compute_degree_metrics(callgraph: dict) -> dict:
    """Compute in_degree, out_degree, combined (centrality) for each node."""
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
    combined = {n: in_degree[n] + out_degree[n] for n in all_nodes}
    return {
        "in_degree": dict(in_degree),
        "out_degree": dict(out_degree),
        "combined_score": combined,
        "all_nodes": list(all_nodes),
    }
