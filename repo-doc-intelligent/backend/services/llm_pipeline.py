"""
Multi-pass LLM documentation pipeline.
Pass 1: Architectural intelligence analysis (static code intelligence engine).
Pass 2–3: Layer breakdown and critical analysis.
"""
import json
import requests
from config import OLLAMA_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT

_ARCHITECTURAL_INTELLIGENCE_SYSTEM = """You are an advanced static code intelligence engine.

Your task is to analyze a repository using the provided structural data:
- AST symbols
- Call graph
- Entry points
- Framework metadata
- Dependency files
- Responsibilities
- Graph metrics
- File structure

This is not a summary task.
This is architectural intelligence analysis.

━━━━━━━━━━━━━━━━━━
STRICT RULES
━━━━━━━━━━━━━━━━━━

1. Do NOT generate a table of contents.
2. Do NOT duplicate section headings.
3. Do NOT fabricate layers, metrics, graph data, or structure.
4. Do NOT output placeholder phrases such as:
   - "unknown"
   - "insufficient data"
   - "appears to be"
   - "likely"
   - "suggests"
   - "no central nodes identified"
5. If structural data is absent, omit discussion of it.
6. Do NOT include empty sections.
7. Do NOT explain the absence of information.
8. Avoid generic architectural advice unless directly supported by structure.
9. Use real file names, classes, components, modules, and functions.
10. Do not repeat the same architectural observation in multiple ways.

If something is not structurally supported, do not mention it.

━━━━━━━━━━━━━━━━━━
FRAMEWORK INTELLIGENCE REQUIREMENT
━━━━━━━━━━━━━━━━━━

If the repository uses a known framework (Angular, React, Next.js, Express, FastAPI, Flask, Spring Boot, Django, etc.):

- Prioritize explaining the framework's execution model.
- Describe its bootstrap lifecycle clearly.
- Explain how framework-specific constructs define structure:
    • Angular: NgModule, bootstrapModule, Components, Services, DI
    • React: root rendering, component tree, hooks, routing
    • Express/FastAPI: route handlers, middleware chain
    • Spring: Controllers, Services, Beans, dependency injection
    • Django: urls.py routing, views, models

Do NOT rely solely on generic call graph analysis for framework-based systems.

Explain how the framework organizes control flow and dependency structure.

━━━━━━━━━━━━━━━━━━
OUTPUT STRUCTURE
━━━━━━━━━━━━━━━━━━

Write a continuous, well-structured architectural explanation
that reads like a technical whitepaper.

Do NOT output a table of contents.

Organize the explanation logically in this order:

1. System Overview
   - What kind of system this is.
   - Primary technologies detected.
   - Structural organization (frontend, API, layered, modular, etc.).

2. Application Bootstrap & Runtime Initialization
   - Identify true entry point(s).
   - Explain how execution begins.
   - Trace real startup chain using actual files and symbols.
   - For frameworks, explain the framework bootstrap clearly.

3. Core Architectural Components
   - Identify major modules, components, controllers, services, classes.
   - Describe their responsibilities using structural relationships.
   - Reference real symbol names.

4. Dependency & Interaction Structure
   - Explain how components interact.
   - Describe real call relationships.
   - Identify orchestration hubs if structurally supported.
   - Explain cross-module dependencies.

5. Data & Control Flow
   - Explain how data moves through the system if visible.
   - Identify where business logic resides.
   - Describe integration points with external libraries or services.

6. Architectural Characteristics
   - Describe dependency direction.
   - Discuss cohesion and coupling using actual metrics.
   - Identify structural strengths supported by graph analysis.
   - Identify structural risks only if metrics justify them.

7. Maintainability & Scalability Implications
   - Base conclusions strictly on structure.
   - Avoid generic statements.
   - Derive insights from module layout and dependency patterns.

━━━━━━━━━━━━━━━━━━
WRITING STYLE
━━━━━━━━━━━━━━━━━━

- Professional and authoritative.
- Concrete and precise.
- No fluff.
- No motivational language.
- No repetition.
- Use inline code formatting for file names and symbols.
- Prefer depth over breadth.
- Explain how the system actually works internally.

You are performing architectural reasoning, not documentation templating.

Now analyze the repository using the provided structural data."""

_ROLE = """You are a senior software architect.
You are given deterministic static analysis results.
Do NOT summarize files.
Infer architecture patterns.
Explain dependency direction.
Explain orchestration boundaries.
Critically evaluate design quality.
Avoid generic statements."""


_EXECUTIVE_SUMMARY_SYSTEM = """You are a technical writer. Your only task is to write an Executive Summary for a software repository.

The Executive Summary must explain, in 2–4 clear paragraphs:

1. **What the project is**: Name the kind of application or system (e.g. a bus-tracking web app, a REST API, a CLI tool). Infer from repo name, entry points, and folder structure.

2. **What it does**: Describe the main purpose, core features, and what users or systems get from it. Use entry points, key file names, and structure—do not fabricate features.

3. **Full project context**: Technology stack (frameworks, languages), how the codebase is organized (frontend/backend, layers, modules), and any other context that helps a reader understand the repo at a glance.

Use only the provided repository data. Be direct and specific. No placeholders like "unknown" or "various". Write in continuous prose (paragraphs), not bullets. Output only the Executive Summary text, no heading."""


def generate_executive_summary(
    repo_url: str,
    repo_name: str,
    entry_points: list,
    frameworks: list,
    architecture_summary: dict,
    folder_structure: str,
    file_count: int = 0,
    total_lines: int = 0,
) -> str:
    """
    Generate an Executive Summary that explains what the repo is, what it does, and full project context.
    Used as the first section of the generated documentation.
    """
    ep_list = ", ".join((entry_points or [])[:15]) or "None detected"
    fw_list = ", ".join(frameworks) if frameworks else "None detected"
    style = architecture_summary.get("architecture_style", "")
    layers = ", ".join(architecture_summary.get("layers_detected", [])) or "Not specified"
    prompt = f"""{_EXECUTIVE_SUMMARY_SYSTEM}

## Repository data

- **Repository**: {repo_url}
- **Project name**: {repo_name}
- **Entry points** (main/app bootstrap files): {ep_list}
- **Frameworks detected**: {fw_list}
- **Architecture style**: {style}
- **Layers inferred**: {layers}
- **File count**: {file_count}
- **Total lines of code**: {total_lines}

**Folder structure (excerpt):**
```
{folder_structure[:3000] if folder_structure else "N/A"}
```

---

Write the Executive Summary (2–4 paragraphs) as specified. Output only the paragraphs, no heading."""

    return _call_llm(prompt)


def _call_llm(prompt: str) -> str:
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=OLLAMA_TIMEOUT,
        )
        resp.raise_for_status()
        text = (resp.json().get("response") or "").strip()
        return text
    except requests.ConnectionError:
        raise ConnectionError(
            "Ollama is not running. Start Ollama (e.g. run 'ollama serve' and 'ollama pull qwen2.5-coder:7b') and try again."
        )
    except requests.Timeout:
        raise ConnectionError("Ollama request timed out. Try again or increase OLLAMA_TIMEOUT.")
    except requests.RequestException as e:
        raise ConnectionError(f"Ollama request failed: {e}")


def _abstract_call_graph_for_prompt(callgraph: dict, metrics: dict, max_edges: int = 25) -> list:
    """Produce a short list of (caller, callee) edges for the LLM; no full dump."""
    from services.graph_abstraction import get_representative_call_edges
    edges = get_representative_call_edges(callgraph, metrics, max_edges=max_edges)
    return [f"{a} → {b}" for a, b in edges[:max_edges]]


def pass1_architecture_reasoning(
    architecture_summary: dict,
    metrics: dict,
    entry_points: list,
    repo_url: str,
    repo_name: str,
    symbol_index: dict = None,
    callgraph: dict = None,
    frameworks: list = None,
    responsibilities: dict = None,
    structure_explanation: str = None,
) -> str:
    """
    PASS 1 — Architectural intelligence analysis.
    Input: full structural data (symbols, call graph abstract, entry points, frameworks,
           responsibilities, metrics, structure_explanation).
    Output: Single continuous whitepaper (7 sections), no TOC, no placeholders.
    """
    total_nodes = metrics.get("total_nodes", metrics.get("node_count", 0))
    total_edges = metrics.get("total_edges", metrics.get("edge_count", 0))
    cycle_count = metrics.get("cycle_count", len(metrics.get("cycles_detected", [])))
    top_central = metrics.get("top_centrality_nodes", metrics.get("top5_central_nodes", []))[:10]
    if len(top_central) < 3 and total_nodes >= 1:
        combined = metrics.get("combined_score", {})
        top_central = sorted(combined.keys(), key=lambda n: -combined.get(n, 0))[: max(3, total_nodes)]

    payload = {
        "repository": repo_url,
        "project": repo_name,
        "entry_points": entry_points or [],
        "frameworks": frameworks or [],
        "architecture_style": architecture_summary.get("architecture_style"),
        "layer_order": architecture_summary.get("layer_order"),
        "layers_detected": architecture_summary.get("layers_detected"),
        "layer_files": {k: v[:12] for k, v in architecture_summary.get("layer_files", {}).items()},
        "dependency_direction": architecture_summary.get("dependency_direction"),
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "cycle_count": cycle_count,
        "top_centrality_nodes": top_central,
        "orchestration_hubs": architecture_summary.get("orchestration_hubs", [])[:15],
        "in_degree_sample": {k: v for k, v in list(metrics.get("in_degree", {}).items())[:15]},
        "out_degree_sample": {k: v for k, v in list(metrics.get("out_degree", {}).items())[:15]},
    }
    if structure_explanation:
        payload["structure_explanation"] = structure_explanation
    else:
        payload["centrality_explanation"] = metrics.get("centrality_explanation", "")

    if symbol_index:
        preview = {}
        for k, v in list(symbol_index.items())[:40]:
            if k == "_by_name":
                continue
            preview[k] = {
                "classes": (v.get("classes") or [])[:8],
                "functions": (v.get("functions") or [])[:8],
                "methods": (v.get("methods") or [])[:12],
            }
        payload["symbol_index"] = preview

    if callgraph and total_edges > 0:
        payload["call_graph_edges_sample"] = _abstract_call_graph_for_prompt(callgraph, metrics)

    if responsibilities:
        role_counts = {}
        for node, role in list(responsibilities.items())[:50]:
            role_counts[role] = role_counts.get(role, 0) + 1
        payload["responsibility_counts"] = role_counts
        payload["responsibility_sample"] = dict(list(responsibilities.items())[:25])

    prompt = f"""{_ARCHITECTURAL_INTELLIGENCE_SYSTEM}

━━━━━━━━━━━━━━━━━━
STRUCTURAL DATA (use only this; do not fabricate)
━━━━━━━━━━━━━━━━━━

{json.dumps(payload, indent=2)}

---

Output one continuous architectural whitepaper with exactly the 7 sections listed in your instructions, in order. Use real file names and symbol names from the data above. No table of contents. No placeholder phrases. Valid Markdown only."""

    return _call_llm(prompt)


def pass2_structural_deep_dive(
    symbol_index: dict,
    architecture_summary: dict,
    module_dependency_abstract: dict,
    repo_name: str,
) -> str:
    """
    PASS 2 — Structural Deep Dive.
    Input: symbol index (summary), module dependency / layer structure — NOT full call graph.
    Output: Layer Breakdown, Module Responsibilities, Call Flow Explanation, Orchestration Analysis.
    """
    symbol_preview = {}
    for k, v in list(symbol_index.items())[:25]:
        symbol_preview[k] = {kk: (vv[:10] if isinstance(vv, list) else vv) for kk, vv in v.items()}
    layer_order = architecture_summary.get("layer_order", [])
    layer_files = {k: v[:8] for k, v in architecture_summary.get("layer_files", {}).items()}
    hubs = architecture_summary.get("orchestration_hubs", [])[:10]

    prompt = f"""{_ROLE}

## Input (structured analysis only — no raw adjacency dump)

**Symbol index (per-file: classes, methods, functions — summary only):**
{json.dumps(symbol_preview, indent=2)}

**Layer order (dependency direction):**
{json.dumps(layer_order, indent=2)}

**Layer → key files:**
{json.dumps(layer_files, indent=2)}

**Orchestration hubs (high in- and out-degree):**
{json.dumps(hubs, indent=2)}

**Module dependency (abstract):**
{json.dumps(module_dependency_abstract, indent=2)}

---

Write ONLY these four sections. Use the exact headings. Do NOT list every function. Explain structure and responsibilities.

## Layer Breakdown
[What each layer is responsible for; key modules per layer.]

## Module Responsibilities
[High-level role of each major module/layer; no file-by-file listing.]

## Call Flow Explanation
[How execution moves from entry points through orchestrators to leaf modules. One representative path.]

## Orchestration Analysis
[Why the identified hubs are coordination points; how they affect the architecture.]

Output valid Markdown only. No preamble."""

    return _call_llm(prompt)


def pass3_critical_analysis(
    architecture_summary: dict,
    metrics: dict,
    repo_name: str,
    repo_url: str,
) -> str:
    """
    PASS 3 — Critical Analysis.
    Input: structural metrics (total_nodes, total_edges, cycle_count), centrality, coupling.
    Output: Strengths, Weaknesses, Maintainability, Scalability, Refactoring. Reference real metrics.
    """
    total_nodes = metrics.get("total_nodes", metrics.get("node_count", 0))
    total_edges = metrics.get("total_edges", metrics.get("edge_count", 0))
    cycle_count = metrics.get("cycle_count", len(metrics.get("cycles_detected", [])))
    top_central = metrics.get("top_centrality_nodes", metrics.get("top5_central_nodes", []))[:5]
    structural_metrics = {
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "cycle_count": cycle_count,
        "top_centrality_nodes": top_central,
        "dependency_direction": architecture_summary.get("dependency_direction"),
    }
    arch = {
        "architecture_style": architecture_summary.get("architecture_style"),
        "cycles_detected": architecture_summary.get("cycles_detected"),
        "coupling_assessment": architecture_summary.get("coupling_assessment"),
        "scalability_assessment": architecture_summary.get("scalability_assessment"),
        "orchestration_hubs": architecture_summary.get("orchestration_hubs", [])[:5],
    }

    prompt = f"""{_ROLE}

## Input (deterministic analysis — cite these numbers)

**Structural metrics:**
{json.dumps(structural_metrics, indent=2)}

**Architecture and coupling:**
{json.dumps(arch, indent=2)}

**Centrality explanation:**
{metrics.get("centrality_explanation", "")}

---

Write ONLY these five sections. Use the exact headings. Reference total_nodes, total_edges, cycle_count, and top_centrality_nodes in your reasoning. Avoid generic advice; use evidence-based conclusions.

## Strengths
[2–4 bullets derived from structure: clear layers, single entry, testable boundaries, etc.]

## Weaknesses
[2–4 bullets: cycles, tight coupling, missing layers, orchestration bottlenecks.]

## Maintainability Risks
[1–2 paragraphs: what makes changes risky given the current structure.]

## Scalability Concerns
[1–2 paragraphs: horizontal/vertical implications from entry points and coupling.]

## Refactoring Suggestions
[2–4 concrete suggestions: break cycles, introduce boundaries, extract services.]

Output valid Markdown only. No preamble."""

    return _call_llm(prompt)


def run_multi_pass_pipeline(
    repo_url: str,
    repo_name: str,
    architecture_summary: dict,
    metrics: dict,
    symbol_index: dict,
    callgraph: dict,
    importgraph: dict,
    entry_points: list,
    frameworks: list,
    responsibilities: dict = None,
) -> dict:
    """
    Run all three passes. Pass 1 uses architectural intelligence prompt and full structural data.
    Returns {"pass1": md, "pass2": md, "pass3": md}.
    """
    from services.architecture_inference import _build_file_to_layer
    from services.graph_abstraction import get_abstract_layer_edges

    file_to_layer = _build_file_to_layer(importgraph, symbol_index)
    layer_edges = get_abstract_layer_edges(importgraph, file_to_layer)
    module_dependency_abstract = {
        "layer_order": architecture_summary.get("layer_order", []),
        "layer_edges": layer_edges,
    }

    p1 = pass1_architecture_reasoning(
        architecture_summary,
        metrics,
        entry_points,
        repo_url,
        repo_name,
        symbol_index=symbol_index,
        callgraph=callgraph,
        frameworks=frameworks,
        responsibilities=responsibilities,
        structure_explanation=metrics.get("structure_explanation") or metrics.get("centrality_explanation"),
    )
    p2 = pass2_structural_deep_dive(
        symbol_index, architecture_summary, module_dependency_abstract, repo_name
    )
    p3 = pass3_critical_analysis(architecture_summary, metrics, repo_name, repo_url)
    return {"pass1": p1, "pass2": p2, "pass3": p3}
