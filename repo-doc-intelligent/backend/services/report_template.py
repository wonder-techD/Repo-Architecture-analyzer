"""
Build report Markdown: Code Wiki-style (flowing narrative) or legacy section-based.
"""
import os


def _repo_name_from_url(repo_url: str) -> str:
    s = (repo_url or "").rstrip("/").replace("https://github.com/", "").replace("http://github.com/", "")
    return s.split("/")[-1] if s else "Repository"


def build_code_wiki_markdown(
    repo_url: str,
    gen_date: str,
    llm_content: str,
) -> str:
    """
    Wrap Code Wiki-style LLM output with minimal metadata. No rigid sections.
    """
    repo_name = _repo_name_from_url(repo_url)
    # Ensure content starts cleanly; add repo link if not present
    header = f"**Repository**: [{repo_url}]({repo_url}) · **Generated**: {gen_date}\n\n---\n\n"
    # If LLM already has an H1, don't duplicate
    content = llm_content.strip()
    if not content.startswith("#"):
        content = f"# {repo_name}\n\n{content}"
    return header + content


def _parse_pass3_sections(pass3_md: str) -> dict:
    """Extract ## sections from pass3: strengths, weaknesses, maintainability_risks, scalability, recommendations."""
    sections = {}
    current = "strengths"
    lines = []
    for line in pass3_md.split("\n"):
        if line.strip().startswith("## "):
            if current:
                sections[current] = "\n".join(lines).strip()
            title = line.strip().lstrip("#").strip().lower()
            if "strength" in title:
                current = "strengths"
            elif "weakness" in title:
                current = "weaknesses"
            elif "maintainab" in title or "risk" in title:
                current = "maintainability_risks"
            elif "scalab" in title:
                current = "scalability"
            elif "refactor" in title or "recommendation" in title:
                current = "recommendations"
            else:
                current = title.replace(" ", "_")[:40]
            lines = []
        else:
            lines.append(line)
    if current:
        sections[current] = "\n".join(lines).strip()
    return sections


def build_architecture_wiki_markdown(
    repo_url: str,
    repo_name: str,
    gen_date: str,
    frameworks: list,
    executive_summary_md: str,
    pass1_architecture_md: str,
    pass2_module_md: str,
    pass3_executive_md: str,
    mermaid_call_flow: str,
    mermaid_module_dependency: str,
    mermaid_layer: str,
    architecture_summary: dict,
    entry_points: list,
    metrics_report: dict,
    graph_metrics: dict = None,
) -> str:
    """
    Build final CodeWiki-level Markdown from multi-pass LLM output and structured data.
    Includes: Executive Summary (deep explanation of the project in plain language—what it is, what it does, who it serves, how it works), Architecture Overview,
    Technology Stack, Architectural Pattern, Layer Breakdown, Call Flow, Entry Points,
    Core Orchestrators, Coupling Analysis, Scalability, Deployment Strategy, Recommendations.
    Mermaid: call flow, module dependency, layer.
    """
    p3 = _parse_pass3_sections(pass3_executive_md)
    exec_md = (executive_summary_md or "").strip()
    if not exec_md:
        exec_md = (
            architecture_summary.get("coupling_assessment", "") + " "
            + architecture_summary.get("scalability_assessment", "")
        ).strip() or (pass1_architecture_md[:1200] if pass1_architecture_md else "")
    strengths_md = p3.get("strengths", "")
    weaknesses_md = p3.get("weaknesses", "")
    maintainability_md = p3.get("maintainability_risks", "")
    scalability_md = p3.get("scalability", "")
    recommendations_md = p3.get("recommendations", "")

    ep_list = "\n".join(f"- `{e}`" for e in (entry_points or [])[:20])
    if not ep_list:
        ep_list = "- No entry points detected from static analysis (e.g. main, app bootstrap)."
    orch = architecture_summary.get("orchestration_hubs", architecture_summary.get("orchestrators", []))
    if not orch and graph_metrics:
        orch = graph_metrics.get("top_centrality_nodes", graph_metrics.get("top5_central_nodes", []))[:5]
    orch = (orch or [])[:15]
    orch_list = "\n".join(f"- `{o}`" for o in orch)
    if not orch_list:
        top = []
        if graph_metrics:
            top = graph_metrics.get("top_centrality_nodes") or graph_metrics.get("top5_central_nodes") or []
        orch_list = "- " + ", ".join(f"`{n}`" for n in top[:3]) if top else "- No central nodes identified (call graph empty or too small)."
    coupling_blurb = architecture_summary.get("coupling_assessment", "Coupling assessment from static analysis.")
    dep_dir = architecture_summary.get("dependency_direction", "mixed")
    tech_stack = " | ".join(frameworks) if frameworks else "See dependency files."
    pattern = architecture_summary.get("architecture_style", "Unknown")

    doc = f"""# {repo_name}

**Repository**: [{repo_url}]({repo_url}) · **Generated**: {gen_date}

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Technology Stack](#technology-stack)
4. [Architectural Pattern](#architectural-pattern)
5. [Layer Breakdown](#layer-breakdown)
6. [Call Flow Explanation](#call-flow-explanation)
7. [Entry Points](#entry-points)
8. [Core Orchestrators](#core-orchestrators)
9. [Coupling Analysis](#coupling-analysis)
10. [Maintainability Risks](#maintainability-risks)
11. [Scalability Discussion](#scalability-discussion)
12. [Deployment Strategy](#deployment-strategy)
13. [Recommendations](#recommendations)

---

## Executive Summary

{exec_md}

---

## Architecture Overview

{pass1_architecture_md}

---

## Technology Stack

{tech_stack}

---

## Architectural Pattern

**Detected pattern**: {pattern}

Layers inferred: {", ".join(architecture_summary.get("layers_detected", []))}.

---

## Layer Breakdown

**What this section is:** The Layer Breakdown describes how the codebase is organized into architectural layers—logical tiers such as presentation, business logic, data access, or infrastructure. Layers are inferred from the call graph, dependency direction, and file/symbol roles (e.g. UI components vs. services vs. repositories).

**Why it matters:** Understanding layers helps you see separation of concerns, find where new code belongs, and spot violations (e.g. UI calling the database directly). It also clarifies test boundaries and where to introduce interfaces.

**How to read it:** Each layer is typically named by responsibility (e.g. "Presentation", "Service", "Adapter"). Files and modules are grouped by their dominant role. The content below is generated from static analysis and, when available, LLM-derived module summaries—use it to map the high-level structure before diving into specific files.

{pass2_module_md}

---

## Call Flow Explanation

{(graph_metrics or {}).get("centrality_explanation") or (graph_metrics or {}).get("structure_explanation") or "Call flow is derived from the static call graph; see diagrams below when available."}

---

"""
    if mermaid_call_flow:
        doc += f"""## Call Flow Diagram

```mermaid
{mermaid_call_flow}
```

---

"""
    if mermaid_module_dependency:
        doc += f"""## Module Dependency Diagram

```mermaid
{mermaid_module_dependency}
```

---

"""
    if mermaid_layer:
        doc += f"""## Layer Diagram

```mermaid
{mermaid_layer}
```

---

"""
    doc += f"""## Entry Points

**What this section is:** Entry points are the symbols (functions, methods, or modules) where execution can begin—e.g. `main`, `app.run()`, CLI handlers, or framework bootstrap hooks. They are detected by static analysis: reachability from known roots (e.g. `main`, `index`, framework entry APIs) and by convention (e.g. `if __name__ == "__main__"`, `@app.route`).

**Why it matters:** Entry points define how the application is started, deployed, and tested. Multiple entry points often indicate multiple runnables (CLI vs. server, worker vs. API). They also anchor the call graph: everything that runs in a process is reachable from at least one entry point.

**How to read it:** Each item below is a symbol (file::symbol or path) that our analysis treats as a possible start of execution. Use this list to understand deployment surface, to find main scripts, and to see whether the repo has one monolith or several distinct entry points.

{ep_list}

---

## Core Orchestrators

**What this section is:** Core orchestrators are symbols that act as coordination hubs: they have high in-degree (many callers or dependents) and high out-degree (they call or depend on many others). They sit at the “middle” of the call graph and often implement workflow coordination, request routing, or aggregation of lower-level services.

**Why it matters:** These nodes are central to control flow and coupling. Changing an orchestrator tends to ripple widely; they are good candidates for tests, documentation, and clear interfaces. Identifying them helps with refactoring, onboarding, and understanding where complexity is concentrated.

**How to read it:** The list below is derived from graph centrality (e.g. degree or betweenness) and/or from responsibility labels (e.g. “orchestrator” in the architecture summary). Each item is a file::symbol or path. Treat them as key coordination points when tracing execution or planning changes.

Orchestration hubs (high in-degree and out-degree — coordination points):

{orch_list}

---

## Coupling Analysis

{coupling_blurb}

Dependency direction: **{dep_dir}**.

---
"""
    if strengths_md or weaknesses_md:
        doc += "## Strengths & Weaknesses\n\n"
        if strengths_md:
            doc += strengths_md + "\n\n"
        if weaknesses_md:
            doc += weaknesses_md + "\n\n---\n\n"
    if maintainability_md:
        doc += "## Maintainability Risks\n\n" + maintainability_md + "\n\n---\n\n"
    doc += f"""## Scalability Discussion

{scalability_md if scalability_md else "Infer from architecture pattern and entry points; consider horizontal scaling if stateless."}

---

## Deployment Strategy

Deployment is driven by entry points and framework: {tech_stack}. Typical strategy: run the main entry (e.g. `manage.py`, `main.js`, or app server); ensure dependencies and environment are configured per framework documentation.

---

## Recommendations

{recommendations_md if recommendations_md else "See refactoring and observations in architecture summary."}
"""
    return doc.strip()


from .report_data import compute_metrics, get_component_units, get_file_categories


def _default_tech_table() -> str:
    """Default Technology Stack table when narrative omits it (no backslash in f-string)."""
    return "| Technology | Version | Purpose |\n| --- | --- | --- |"


def _key_metrics_table(metrics: dict) -> str:
    """Render Key Metrics as Markdown table."""
    rows = [
        ("Total Files", str(metrics["total_files"])),
        ("Total Lines of Code", str(metrics["total_lines"])),
    ]
    for label, data in sorted(metrics.get("by_type", {}).items(), key=lambda x: -x[1]["lines"]):
        if data["count"] > 0:
            rows.append((f"{label}", f"{data['count']} ({data['lines']} lines)"))
    rows.append(("Components", str(metrics.get("component_count", 0))))
    rows.append(("Services", str(metrics.get("service_count", 0))))
    rows.append(("Interfaces", str(metrics.get("interface_count", 0))))
    lines = ["| Metric | Count |", "| --- | --- |"]
    for a, b in rows:
        lines.append(f"| {a} | {b} |")
    return "\n".join(lines)


def _component_breakdown_list(component_units: list) -> str:
    """Executive Summary component breakdown: **Name**: N lines."""
    items = []
    for u in component_units:
        total = u["ts_lines"] + u["html_lines"] + u["css_lines"] or u["ts_lines"]
        items.append(f"- **{u['name']}**: {total} lines")
    return "\n".join(items) if items else "- (No components detected)"


_MAX_S3_LINES = 12
_TRUNC_NOTE = "\n# ... (see repository for full source)"


def _section3_fallback_from_categories(
    file_categories: dict, symbol_index: dict, content_by_path: dict
) -> str:
    """When no paired component units exist, list component files with role and short excerpt."""
    paths = file_categories.get("components", [])
    if not paths:
        return "No component files were detected in this codebase."
    # Prefer .ts/.tsx component files; dedupe by base name (one entry per logical component)
    seen_bases = set()
    entries = []
    for path in sorted(paths):
        base = path.lower()
        if not (base.endswith(".component.ts") or base.endswith(".component.tsx") or (".component." in base and base.split(".")[-1] in ("ts", "tsx"))):
            continue
        # e.g. src/app/app.component.ts -> (dir, app.component)
        dirname, fname = os.path.dirname(path), os.path.basename(path)
        base_name = fname.rsplit(".", 2)[0] if ".component." in base else fname  # app.component
        key = (dirname, base_name)
        if key in seen_bases:
            continue
        seen_bases.add(key)
        classes = symbol_index.get(path, {}).get("classes", [])
        name = (classes[0] if classes else base_name.replace(".", " ").title().replace(" ", "") + "Component")
        content = (content_by_path.get(path) or "").strip().splitlines()
        excerpt = "\n".join(content[:_MAX_S3_LINES])
        if len(content) > _MAX_S3_LINES:
            excerpt += _TRUNC_NOTE
        entries.append((name, path, classes, excerpt))
    if not entries:
        # Fallback: any file in components list
        for path in sorted(paths)[:15]:
            classes = symbol_index.get(path, {}).get("classes", [])
            name = os.path.basename(path).replace(".", " ").title().replace(" ", "")
            content = (content_by_path.get(path) or "").strip().splitlines()
            excerpt = "\n".join(content[:_MAX_S3_LINES])
            if len(content) > _MAX_S3_LINES:
                excerpt += _TRUNC_NOTE
            entries.append((name, path, classes, excerpt))
    intro = "This section lists **component files** and their roles. Code snippets are short excerpts for context; see the repository for full source.\n\n"
    parts = [intro]
    for name, path, classes, excerpt in entries:
        parts.append(f"### {name}\n")
        parts.append(f"**Location:** `{path}`")
        if classes:
            parts.append(f" · **Classes:** {', '.join(classes)}\n")
        else:
            parts.append("\n")
        parts.append("**Key code (excerpt):**\n\n```\n" + excerpt + "\n```\n\n")
    return "\n".join(parts).strip()


def _section3_component_analysis(
    component_units: list,
    purpose_by_name: dict,
    content_by_path: dict,
    file_categories: dict | None = None,
    symbol_index: dict | None = None,
) -> str:
    """Section 3: Essential role of each component; minimal code for context only."""
    if component_units:
        intro = "This section explains **what each component does** and where it lives. Code snippets are short excerpts for context only; see the repository for full source.\n\n"
        parts = [intro]
        for u in component_units:
            name = u["name"]
            purpose = purpose_by_name.get(name) or f"Component defined in {u['ts_path']}."
            parts.append(f"### {name}\n")
            parts.append(f"**What it does:** {purpose}\n")
            parts.append(f"**Location:** `{u['ts_path']}` · **Size:** {u['ts_lines']} lines (TS) + {u.get('html_lines', 0)} (template) + {u.get('css_lines', 0)} (styles)\n")
            ts = (u["ts_content"] or "").strip().splitlines()
            if ts:
                ts_excerpt = "\n".join(ts[:_MAX_S3_LINES])
                if len(ts) > _MAX_S3_LINES:
                    ts_excerpt += _TRUNC_NOTE
                parts.append("**Key code (excerpt):**\n\n```\n" + ts_excerpt + "\n```\n")
            parts.append("")
        return "\n".join(parts).strip()
    if file_categories and symbol_index is not None:
        return _section3_fallback_from_categories(file_categories, symbol_index, content_by_path)
    return "No component units were detected (e.g. no paired .ts + .html/.css with component in path or name)."


_MAX_S9_FILES = 5
_MAX_S9_LINES = 15


def _section9_complete_listings(file_categories: dict, content_by_path: dict) -> str:
    """Section 9: Essential files and very short excerpts for reference only."""
    category_titles = {
        "entry_points": "Main Entry Points",
        "app_config": "Application Configuration",
        "components": "Components",
        "config": "Configuration Files",
    }
    parts = ["This section lists the most important files by category with a short excerpt each. Use it as a quick reference; full source is in the repository.\n\n"]
    for cat_key, title in category_titles.items():
        paths = file_categories.get(cat_key, [])
        if not paths:
            continue
        parts.append(f"### {title}\n")
        for path in paths[:_MAX_S9_FILES]:
            content = content_by_path.get(path)
            if not content:
                continue
            lines = content.strip().splitlines()
            excerpt = "\n".join(lines[:_MAX_S9_LINES])
            if len(lines) > _MAX_S9_LINES:
                excerpt += _TRUNC_NOTE
            parts.append(f"**{path}**\n\n```\n{excerpt}\n```\n\n")
        parts.append("")
    return "\n".join(parts).strip()


def build_report_markdown(
    repo_url: str,
    gen_date: str,
    metrics: dict,
    component_units: list,
    file_categories: dict,
    content_by_path: dict,
    narratives: dict,
    symbol_index: dict | None = None,
) -> str:
    """
    Build full report Markdown. narratives dict must contain:
    project_purpose, application_features, technology_stack_table, architecture_overview, data_flow,
    service_layer, data_models, styling, configuration_review, code_quality, recommendations.
    And optionally purpose_<ComponentName> for each component, or component_purposes (dict name -> purpose).
    When symbol_index is provided and component_units is empty, Section 3 is built from file_categories and symbol_index.
    """
    repo_name = _repo_name_from_url(repo_url)
    purpose_by_name = narratives.get("component_purposes") or {}
    for u in component_units:
        if u["name"] not in purpose_by_name:
            key = "purpose_" + u["name"].replace(" ", "_")
            if key in narratives:
                purpose_by_name[u["name"]] = narratives[key]
    key_metrics_md = _key_metrics_table(metrics)
    component_breakdown_md = _component_breakdown_list(component_units)
    section3_md = _section3_component_analysis(
        component_units, purpose_by_name, content_by_path,
        file_categories=file_categories, symbol_index=symbol_index,
    )
    section9_md = _section9_complete_listings(file_categories, content_by_path)

    doc = f"""# {repo_name} - Complete Codebase Documentation

**Generated**: {gen_date}
**Repository**: {repo_url}
**Framework**: {narratives.get('framework_summary', 'See Technology Stack below')}
**Key libraries**: {narratives.get('key_libraries', 'See Technology Stack below')}

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [Component Analysis](#3-component-analysis)
4. [Service Layer Review](#4-service-layer-review)
5. [Data Models & Interfaces](#5-data-models--interfaces)
6. [Styling & Design System](#6-styling--design-system)
7. [Configuration Review](#7-configuration-review)
8. [Code Quality Assessment](#8-code-quality-assessment)
9. [Key Source Excerpts (Reference)](#9-key-source-excerpts-reference)
10. [Recommendations](#10-recommendations)

---

## 1. Executive Summary

**Essential information:** High-level purpose, technology stack, main features, and key metrics at a glance.

### Project Purpose

{narratives.get('project_purpose', 'This codebase has been analyzed for structure, components, and dependencies.')}

### Technology Stack

{narratives.get('technology_stack_table', _default_tech_table())}

### Application Features

{narratives.get('application_features', '- Features inferred from project structure and entry points.')}

### Key Metrics

{key_metrics_md}

### Component Breakdown

{component_breakdown_md}

---

## 2. Architecture Overview

**Essential information:** How the application is structured and how data flows between entry points, services, and UI.

### Application Structure

{narratives.get('architecture_overview', 'The application structure is derived from the folder layout and component hierarchy.')}

### Data Flow

{narratives.get('data_flow', 'Data flow can be inferred from the import and call graphs.')}

---

## 3. Component Analysis

**Essential information:** What each major component does, where it lives, and a minimal code excerpt for context.

{section3_md}

---

## 4. Service Layer Review

**Essential information:** Which services exist, what each one is responsible for, and how they are used.

{narratives.get('service_layer', 'Services are identified from the symbol index and entry points.')}

---

## 5. Data Models & Interfaces

**Essential information:** Main types, interfaces, and data structures used across the application.

{narratives.get('data_models', 'Data models and interfaces are extracted from type definitions and symbol index.')}

---

## 6. Styling & Design System

**Essential information:** How styling is organized (global vs component, frameworks, design tokens).

{narratives.get('styling', 'Styling approach is inferred from CSS/SCSS files and component styles.')}

---

## 7. Configuration Review

**Essential information:** Key config files (e.g. package.json, tsconfig) and important settings.

{narratives.get('configuration_review', 'Configuration is derived from package.json, tsconfig, and other config files.')}

---

## 8. Code Quality Assessment

**Essential information:** Strengths, areas for improvement, and a brief assessment of structure and conventions.

{narratives.get('code_quality', 'Assessment based on structure, metrics, and conventions.')}

---

## 9. Key Source Excerpts (Reference)

**Essential information:** Short excerpts from the most important files for quick reference; full source is in the repository.

{section9_md}

---

## 10. Recommendations

**Essential information:** Suggested next steps—immediate, short-term, and long-term—to improve or extend the codebase.

{narratives.get('recommendations', 'Recommendations for improvement based on codebase analysis.')}
"""
    return doc.strip()
