import json
import os
import requests
from config import OLLAMA_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT

# Extensions that map to language for line counts (subset of scanner)
_EXT_TO_LANG = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript", ".jsx": "React JSX", ".tsx": "React TSX",
    ".java": "Java", ".go": "Go", ".rs": "Rust", ".c": "C", ".cpp": "C++", ".cs": "C#", ".php": "PHP",
    ".rb": "Ruby", ".html": "HTML", ".css": "CSS", ".vue": "Vue", ".json": "JSON", ".yaml": "YAML", ".yml": "YAML",
}


def _folder_structure(repo_root: str, prefix: str = "", max_depth: int = 4, current: int = 0) -> str:
    if current >= max_depth:
        return ""
    lines = []
    try:
        entries = sorted(os.listdir(repo_root))
    except (OSError, PermissionError):
        return ""
    for name in entries:
        if name.startswith(".") or name in ("node_modules", "__pycache__", "venv", ".git", "build", "dist"):
            continue
        path = os.path.join(repo_root, name)
        if os.path.isdir(path):
            lines.append(prefix + name + "/")
            lines.append(_folder_structure(path, prefix + "  ", max_depth, current + 1))
        else:
            lines.append(prefix + name)
    return "\n".join(lines)


def _repo_name_from_url(repo_url: str) -> str:
    s = (repo_url or "").rstrip("/").replace("https://github.com/", "").replace("http://github.com/", "")
    return s.split("/")[-1] if s else "Repository"


def _compute_metrics_and_excerpts(file_entries: list, entry_points: list, symbol_index: dict):
    """Compute total/line counts and key file excerpts for deeper LLM context."""
    total_lines = 0
    lines_by_lang = {}
    for rel_path, content in file_entries:
        lines = (content or "").splitlines()
        n = len(lines)
        total_lines += n
        ext = os.path.splitext(rel_path)[1].lower()
        lang = _EXT_TO_LANG.get(ext, "Other")
        lines_by_lang[lang] = lines_by_lang.get(lang, 0) + n

    # Key files: entry points first, then files with most symbols (classes + functions)
    key_paths = set(entry_points or [])
    by_symbol_count = sorted(
        symbol_index.items(),
        key=lambda x: len(x[1].get("classes", [])) + len(x[1].get("functions", [])),
        reverse=True,
    )
    for path, _ in by_symbol_count[:12]:
        if len(key_paths) >= 10:
            break
        key_paths.add(path)

    file_content_map = {path: content for path, content in file_entries if content}
    excerpts = []
    max_lines_per_file = 28
    for path in list(key_paths)[:10]:
        content = file_content_map.get(path)
        if not content:
            continue
        lines = content.splitlines()
        head = "\n".join(lines[:max_lines_per_file])
        if len(lines) > max_lines_per_file:
            head += "\n# ... (truncated)"
        excerpts.append(f"---\n**File:** `{path}`\n```\n{head}\n```")
    return total_lines, lines_by_lang, "\n\n".join(excerpts) if excerpts else "No source excerpts available."


def _dependency_files_content(file_entries: list) -> str:
    """Extract content of key dependency/config files for Technology Stack and Configuration sections."""
    want = {"package.json", "requirements.txt", "pom.xml", "go.mod", "Cargo.toml", "package-lock.json"}
    file_content_map = {path: content for path, content in file_entries if content}
    parts = []
    for path, content in file_entries:
        if not content:
            continue
        name = os.path.basename(path)
        if name in want and path.count("/") <= 1:  # root or one level
            head = "\n".join(content.splitlines()[:50])
            if content.count("\n") >= 50:
                head += "\n# ... (truncated)"
            parts.append(f"**{path}:**\n```\n{head}\n```")
    return "\n\n".join(parts) if parts else "No standard dependency files found in root."


def build_prompt(
    repo_root: str,
    repo_url: str,
    languages: dict,
    frameworks: list,
    symbol_index: dict,
    importgraph: dict,
    callgraph: dict,
    entry_points: list,
    file_entries: list,
) -> str:
    structure = _folder_structure(repo_root)
    total_lines, lines_by_lang, key_excerpts = _compute_metrics_and_excerpts(file_entries, entry_points, symbol_index)
    dependency_content = _dependency_files_content(file_entries)
    symbol_summary = json.dumps({k: {kk: vv[:20] for kk, vv in v.items()} for k, v in list(symbol_index.items())[:60]}, indent=2)
    import_summary = json.dumps(dict(list(importgraph.items())[:100]), indent=2)
    call_summary = json.dumps(dict(list(callgraph.items())[:100]), indent=2)
    file_count = len(file_entries)
    prompt = f"""You are a senior software architect. Produce a Complete Codebase Documentation report in Markdown. Every section MUST contain substantive, human-readable explanation—no empty sections, no placeholder text, no bare headings.

## Input data

**Repository URL**: {repo_url}

**Detected languages** (file counts):
{json.dumps(languages, indent=2)}

**Total files**: {file_count}
**Total lines of code**: {total_lines}
**Lines by language**:
{json.dumps(lines_by_lang, indent=2)}

**Detected frameworks**:
{json.dumps(frameworks, indent=2)}

**Folder structure**:
{structure}

**Symbol index** (classes, functions, imports per file):
{symbol_summary}

**Import graph** (who imports whom):
{import_summary}

**Call graph** (who calls whom):
{call_summary}

**Entry points** (main/app files):
{json.dumps(entry_points, indent=2)}

**Key file excerpts (first ~30 lines of important files):**
{key_excerpts}

**Dependency / config files (for Technology Stack and Configuration sections):**
{dependency_content}

---

Generate ONE Markdown document. Start with a main title and metadata, then Table of Contents, then ALL numbered sections below. Output ONLY valid Markdown (no preamble).

CRITICAL RULES:
- Do NOT leave any section empty or with only a heading. Every section must have at least 2–4 sentences (or a table/list with real content). If something does not apply, write one short paragraph explaining why (e.g. "This project does not use a custom design system; styling is minimal or framework-default.").
- Write in clear, human-readable prose. Explain what each part does and how it fits together, as if for a developer new to the project. Infer from file names, symbols, imports, and the code excerpts above.
- Use the exact line counts and file counts above in Key Metrics. Describe components/modules by name and role using the symbol index and excerpts.

**Required structure:**

1. `# {{ProjectName}} - Complete Codebase Documentation`
2. Metadata paragraph: **Generated**: (today's date), **Repository**: {repo_url}, **Framework**: (detected), **Key libraries** if relevant. Then `---`.
3. **## Table of Contents** — ordered list with anchor links to each section.
4. **## 1. Executive Summary**
   - ### Project Purpose — 2–4 sentences on what the project does and its main goal.
   - ### Technology Stack — Markdown table: Technology | Version | Purpose (infer versions from excerpts/config if possible).
   - ### Application Features — numbered list of features inferred from structure and code.
   - ### Key Metrics — table: Metric | Count (Total Files, Total Lines, Lines per Language, Components/Services count from symbol index).
   - ### Component / Module Breakdown — bullets: name and one-sentence role for each major file/module.
5. **## 2. Architecture Overview**
   - ### Application Structure — tree or outline of main components and how they connect.
   - ### Data Flow — how data moves (e.g. entry point → services → UI); use code block or bullets.
   - Add subsections if relevant (Dependency Injection, Routing, etc.) with real content.
6. **## 3. Component / Module Analysis** — for each major component: ### Name, then Purpose (1–2 sentences), Location (path), and a short code snippet from the excerpts with one sentence explaining what it does.
7. **## 4. Service Layer Review** — list services (from symbol index/entry points), each with 1–2 sentences on role. If none, say "No dedicated service layer detected; logic may live in components."
8. **## 5. Data Models & Interfaces** — types/interfaces/models found (from symbol index); one line each. If none, one sentence: "No explicit data model files detected; types may be inline."
9. **## 6. Styling & Design System** — describe CSS/styling approach or write: "No custom design system; [brief reason]."
10. **## 7. Configuration Review** — describe package.json / requirements.txt / tsconfig etc. from excerpts; list key settings.
11. **## 8. Code Quality Assessment** — Strengths (2–3 bullets), Areas for Improvement (2–3 bullets), brief metrics (from line counts and structure).
12. **## 9. Key Source Code Listings** — 2–4 important excerpts (from the key files above) with a one-line caption each.
13. **## 10. Recommendations** — Immediate next steps, Short-term improvements, Long-term enhancements; at least 2 bullets per subheading.

Use `##` and `###` headings, Markdown tables, fenced code blocks, and bullet lists. Be professional and thorough. Fill every section with real, human-readable content.
"""
    return prompt


def _build_symbol_summary(symbol_index: dict, file_categories: dict) -> str:
    """Build a short text summary of services, components, and types for the LLM prompt."""
    lines = []
    # Services: files with 'service' in path or in class names
    services = []
    for path, data in symbol_index.items():
        path_lower = path.lower()
        classes = data.get("classes", [])
        if "service" in path_lower or any("service" in c.lower() for c in classes):
            services.append((path, classes))
    if services:
        lines.append("**Services (path and class names):**")
        for path, classes in services[:25]:
            lines.append(f"  - {path}: {', '.join(classes) or '(no classes)'}")
        lines.append("")
    # Component files (from categories or path contains 'component')
    comp_paths = set(file_categories.get("components", []))
    for path in symbol_index:
        if "component" in path.lower():
            comp_paths.add(path)
    if comp_paths:
        lines.append("**Component files (path and class names):**")
        for path in sorted(comp_paths)[:30]:
            classes = symbol_index.get(path, {}).get("classes", [])
            lines.append(f"  - {path}: {', '.join(classes) or '(component)'}")
        lines.append("")
    # Interfaces / types: path or class with 'interface' or 'model' or 'type'
    interfaces = []
    for path, data in symbol_index.items():
        path_lower = path.lower()
        classes = data.get("classes", [])
        if "interface" in path_lower or "model" in path_lower or ".types" in path_lower:
            interfaces.append((path, classes))
        else:
            for c in classes:
                if "interface" in c.lower() or "model" in c.lower():
                    interfaces.append((path, classes))
                    break
    if interfaces:
        lines.append("**Interfaces / types (path and class names):**")
        seen = set()
        for path, classes in interfaces[:20]:
            key = (path, tuple(classes))
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"  - {path}: {', '.join(classes)}")
    return "\n".join(lines) if lines else "No symbol summary available."


def _data_driven_fallbacks(
    metrics: dict,
    folder_structure: str,
    entry_points: list,
    file_categories: dict,
    symbol_index: dict,
    dependency_content: str,
    frameworks: list,
) -> dict:
    """Build substantive narrative fallbacks from actual data when LLM output is missing or generic."""
    fallbacks = {}

    # Architecture: entry points + main folders + component count
    ep = (entry_points or [])[:8]
    comp_count = len(file_categories.get("components", []))
    total = metrics.get("total_files", 0)
    lines_total = metrics.get("total_lines", 0)
    structure_preview = (folder_structure or "").strip().split("\n")[:12]
    structure_line = " ".join(s.strip() for s in structure_preview if s.strip())[:350]
    fallbacks["architecture_overview"] = (
        f"The application has {total} files ({lines_total} lines of code). "
        f"Entry points: {', '.join(ep) if ep else 'main/app files'}. "
        + (f"There are {comp_count} component-related files. " if comp_count else "")
        + f"Top-level structure: {structure_line}."
    )

    # Data flow: entry → components/services
    fallbacks["data_flow"] = (
        f"Data flow starts from entry points ({', '.join(ep[:4]) if ep else 'main modules'}). "
        "Components and services are wired via dependency injection or imports. "
        "User actions typically trigger component methods, which may call services or APIs; results flow back to the template."
    )

    # Service layer: list from symbol index
    services = []
    for path, data in symbol_index.items():
        path_lower = path.lower()
        classes = data.get("classes", [])
        if "service" in path_lower or any("service" in c.lower() for c in classes):
            for c in (classes or ["(service)"]):
                services.append(f"**{c}** (`{path}`)")
    if services:
        fallbacks["service_layer"] = (
            "The following services were detected. Each typically encapsulates API calls, business logic, or shared state.\n\n"
            + "\n".join(f"- {s}" for s in services[:15])
        )
    else:
        fallbacks["service_layer"] = (
            "No dedicated service layer was detected; application logic may live in components or entry modules. "
            "Consider extracting reusable logic into services for testability and clarity."
        )

    # Data models: list interfaces/types
    types_list = []
    for path, data in symbol_index.items():
        path_lower = path.lower()
        classes = data.get("classes", [])
        if "interface" in path_lower or "model" in path_lower or ".types" in path_lower:
            types_list.append(f"`{path}`: {', '.join(classes) or 'types'}")
        else:
            for c in classes:
                if "interface" in c.lower() or "model" in c.lower():
                    types_list.append(f"`{path}`: {', '.join(classes)}")
                    break
    if types_list:
        fallbacks["data_models"] = (
            "Main types and interfaces used in the application:\n\n"
            + "\n".join(f"- {t}" for t in types_list[:20])
        )
    else:
        fallbacks["data_models"] = (
            "No standalone interface or model files were detected. Types may be defined inline in components or services. "
            "Check component and service files for local interfaces and DTOs."
        )

    # Styling: from file counts
    by_type = metrics.get("by_type", {})
    css_lines = by_type.get("CSS Stylesheets", {}).get("lines", 0)
    css_count = by_type.get("CSS Stylesheets", {}).get("count", 0)
    fallbacks["styling"] = (
        f"The project uses {css_count} CSS/SCSS/Less file(s) ({css_lines} lines). "
        "Styling is likely component-scoped (per-component styles) or global (shared styles in a single folder). "
        "Check the components and app folders for stylesheets."
    )

    # Configuration: summarize dependency excerpt (keep readable length)
    dep_preview = (dependency_content or "").strip()[:500]
    if len(dep_preview) > 300:
        dep_preview = dep_preview[:300].rsplit("\n", 1)[0] + "\n..."
    fallbacks["configuration_review"] = (
        "Key configuration is defined in dependency and config files at the project root (e.g. package.json, tsconfig, angular.json). "
        "Scripts, dependencies, and build settings are set there. "
        + (f"Config excerpt:\n{dep_preview}" if dep_preview else "")
    )

    # Code quality: from metrics
    comp_count_metrics = metrics.get("component_count", 0)
    svc_count = metrics.get("service_count", 0)
    fallbacks["code_quality"] = (
        f"**Strengths:** Structured codebase with {total} files; {comp_count_metrics} component(s), {svc_count} service(s) detected. "
        "Clear separation by file type (components, services, config).\n\n"
        "**Areas for improvement:** Add unit tests for services and components; document public APIs; consider lazy loading for large modules."
    )

    # Recommendations
    fallbacks["recommendations"] = (
        "**Immediate:** Run tests and fix any failures; ensure build and lint pass.\n\n"
        "**Short-term:** Add or update README with setup and run instructions; document environment variables and config.\n\n"
        "**Long-term:** Introduce E2E tests; consider CI/CD for builds and deployments."
    )

    return fallbacks


def _is_generic_narrative(text: str) -> bool:
    """True if the narrative is a generic placeholder we should replace with data-driven content."""
    if not text or not text.strip():
        return True
    generic_phrases = [
        "structure derived from",
        "data flow inferred from",
        "see symbol index",
        "see dependency files",
        "inferred from css",
        "assessment based on metrics",
        "review entry points",
        "features inferred from",
    ]
    lower = text.strip().lower()
    return any(p in lower for p in generic_phrases)


def _parse_narrative_sections(text: str) -> dict:
    """Parse LLM response with sections like 'Section: PROJECT_PURPOSE\\nContent:\\n...' into a dict."""
    result = {}
    current_key = None
    current_lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        is_section = stripped.upper().startswith("SECTION:") or (stripped.startswith("## ") and ":" not in stripped[:20])
        if is_section and stripped.upper().startswith("SECTION:"):
            if current_key:
                result[current_key] = "\n".join(current_lines).strip()
            rest = line.split(":", 1)[-1].strip()
            current_key = rest.upper().replace(" ", "_").replace("-", "_")[:80]
            if current_key in ("CONTENT", "SECTION"):
                current_key = None
            current_lines = []
            continue
        if is_section and stripped.startswith("## "):
            if current_key:
                result[current_key] = "\n".join(current_lines).strip()
            current_key = stripped.replace("##", "").strip().upper().replace(" ", "_").replace("-", "_")[:80]
            current_lines = []
            continue
        if current_key:
            current_lines.append(line)
    if current_key:
        result[current_key] = "\n".join(current_lines).strip()
    # Map to template keys
    key_map = {
        "PROJECT_PURPOSE": "project_purpose",
        "APPLICATION_FEATURES": "application_features",
        "TECHNOLOGY_STACK_TABLE": "technology_stack_table",
        "TECHNOLOGY_STACK": "technology_stack_table",
        "ARCHITECTURE_OVERVIEW": "architecture_overview",
        "APPLICATION_STRUCTURE": "architecture_overview",
        "DATA_FLOW": "data_flow",
        "SERVICE_LAYER": "service_layer",
        "SERVICE_LAYER_REVIEW": "service_layer",
        "DATA_MODELS": "data_models",
        "DATA_MODELS_INTERFACES": "data_models",
        "STYLING": "styling",
        "STYLING_DESIGN_SYSTEM": "styling",
        "CONFIGURATION_REVIEW": "configuration_review",
        "CODE_QUALITY": "code_quality",
        "CODE_QUALITY_ASSESSMENT": "code_quality",
        "RECOMMENDATIONS": "recommendations",
        "COMPONENT_PURPOSES": "component_purposes_raw",
        "FRAMEWORK_SUMMARY": "framework_summary",
        "KEY_LIBRARIES": "key_libraries",
    }
    out = {}
    for k, v in result.items():
        norm = key_map.get(k, k.lower())
        if norm == "component_purposes_raw":
            # Parse "ComponentName: one sentence" into dict
            purposes = {}
            for part in (v or "").split("\n"):
                if ":" in part:
                    name, _, sent = part.partition(":")
                    purposes[name.strip()] = sent.strip()
            out["component_purposes"] = purposes
        else:
            out[norm] = v
    return out


def generate_narratives(
    repo_url: str,
    repo_name: str,
    metrics: dict,
    frameworks: list,
    component_units: list,
    file_categories: dict,
    folder_structure: str,
    entry_points: list,
    dependency_content: str,
    symbol_index: dict | None = None,
) -> dict:
    """
    Call Ollama once with focused context; ask for structured narrative sections.
    Returns a dict suitable for report_template.build_report_markdown narratives=.
    When symbol_index is provided, prompt is enriched and data-driven fallbacks fill any missing or generic sections.
    """
    component_names = [u["name"] for u in component_units]
    symbol_summary = ""
    if symbol_index:
        symbol_summary = _build_symbol_summary(symbol_index, file_categories)
    data_fallbacks = {}
    if symbol_index is not None:
        data_fallbacks = _data_driven_fallbacks(
            metrics, folder_structure, entry_points, file_categories,
            symbol_index, dependency_content, frameworks,
        )

    prompt = f"""You are a senior software architect. Based on the following codebase summary, write ONLY the narrative sections requested. Use the exact section headers and format below so your response can be parsed.

## Codebase summary

- **Repository**: {repo_url}
- **Project name**: {repo_name}
- **Total files**: {metrics.get('total_files', 0)}, **Total lines**: {metrics.get('total_lines', 0)}
- **Frameworks detected**: {', '.join(frameworks) if frameworks else 'None'}
- **Components**: {', '.join(component_names[:25]) if component_names else 'None'}
- **Entry points**: {', '.join((entry_points or [])[:10])}
- **Folder structure** (excerpt):
{folder_structure[:2000]}

**Symbol summary (services, component files, interfaces):**
{symbol_summary[:2500] if symbol_summary else 'Not available.'}

**Dependency/config excerpt**:
{dependency_content[:1800]}

---

Output your response using EXACTLY this format. Use the section headers as given.
For every section: explain the ESSENTIAL INFORMATION a reader must know—clear, concise prose. No placeholders; no "see below." Write 2-5 sentences or a short table/list per section. Be specific and human-readable.

Section: PROJECT_PURPOSE
Content:
[2-4 sentences: what this project does, who it is for, and its main goal. Essential takeaway only.]

Section: APPLICATION_FEATURES
Content:
[Numbered list of 4-8 features: what the app actually does from a user or business perspective.]

Section: TECHNOLOGY_STACK_TABLE
Content:
[Markdown table: Technology | Version | Purpose. Use dependency excerpt for versions.]

Section: FRAMEWORK_SUMMARY
Content:
[One short line for metadata, e.g. "Angular 18 with Standalone Components"]

Section: KEY_LIBRARIES
Content:
[One short line, e.g. "PrimeNG, Chart.js"]

Section: ARCHITECTURE_OVERVIEW
Content:
[2-4 sentences: essential structure—main layers, entry points, how components and modules connect. Optionally a short tree in a code block.]

Section: DATA_FLOW
Content:
[2-4 sentences: how data moves (e.g. user action → service → API → UI). Essential path only.]

Section: SERVICE_LAYER
Content:
[For each service: 1-2 sentences on what it does and why it matters. If none: "No dedicated service layer; logic lives in components."]

Section: DATA_MODELS
Content:
[Essential types/interfaces: name and one-line purpose each. If inline: "Types are defined inline in components; main shapes are ..."]

Section: STYLING
Content:
[2-3 sentences: how styling is done (global vs component, framework, design system or ad-hoc). Essential only.]

Section: CONFIGURATION_REVIEW
Content:
[2-4 sentences: which config files matter and the most important settings (build, env, API base).]

Section: CODE_QUALITY
Content:
[Strengths (2-3 bullets), Areas for improvement (2-3 bullets). Be specific, not generic.]

Section: RECOMMENDATIONS
Content:
[Immediate next steps, Short-term, Long-term; 2+ bullets each. Concrete actions.]

Section: COMPONENT_PURPOSES
Content:
[One line per component: "ComponentName: One sentence on what it does and why it matters." for each: {', '.join(component_names[:20])}]
"""
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=OLLAMA_TIMEOUT,
        )
        resp.raise_for_status()
        text = (resp.json().get("response") or "").strip()
    except requests.ConnectionError:
        raise ConnectionError(
            "Ollama is not running. Start Ollama (e.g. run 'ollama serve' and 'ollama pull qwen2.5-coder:7b') and try again."
        )
    except requests.Timeout:
        raise ConnectionError("Ollama request timed out. Try again or increase OLLAMA_TIMEOUT.")
    except requests.RequestException as e:
        raise ConnectionError(f"Ollama request failed: {e}")

    narratives = _parse_narrative_sections(text)
    # Use data-driven fallbacks for any missing or generic section (so PDF has real content)
    soft_defaults = {
        "project_purpose": "This codebase has been analyzed for structure and dependencies.",
        "application_features": "- Features inferred from project structure and entry points.",
        "technology_stack_table": "| Technology | Version | Purpose |\n| --- | --- | --- |",
        "framework_summary": "",
        "key_libraries": "",
        "component_purposes": {},
    }
    for k, v in soft_defaults.items():
        if k not in narratives or not str(narratives.get(k, "")).strip():
            narratives[k] = v
    # Sections that must have substantive content: use data-driven fallbacks when missing or generic
    for key in ("architecture_overview", "data_flow", "service_layer", "data_models", "styling", "configuration_review", "code_quality", "recommendations"):
        val = narratives.get(key) or ""
        if not str(val).strip() or _is_generic_narrative(str(val)):
            if key in data_fallbacks:
                narratives[key] = data_fallbacks[key]
    return narratives


def _build_code_wiki_context(
    repo_url: str,
    repo_name: str,
    metrics: dict,
    frameworks: list,
    component_units: list,
    file_categories: dict,
    folder_structure: str,
    entry_points: list,
    dependency_content: str,
    symbol_index: dict,
    content_by_path: dict,
    key_excerpts: str,
) -> str:
    """Build rich context for Code Wiki-style document generation."""
    symbol_summary = _build_symbol_summary(symbol_index, file_categories)
    component_names = [u["name"] for u in component_units]
    return f"""## Repository

**URL**: {repo_url}
**Name**: {repo_name}
**Files**: {metrics.get('total_files', 0)}, **Lines**: {metrics.get('total_lines', 0)}
**Frameworks**: {', '.join(frameworks) if frameworks else 'None'}
**Entry points**: {', '.join((entry_points or [])[:12])}
**Components**: {', '.join(component_names[:30]) if component_names else 'None'}

## Folder structure

{folder_structure[:2500]}

## Symbol summary (services, components, interfaces)

{symbol_summary[:3000]}

## Dependency and config files

{dependency_content[:2000]}

## Key file excerpts (for deep explanation)

{key_excerpts[:6000]}
"""


def generate_code_wiki_document(
    repo_url: str,
    repo_name: str,
    metrics: dict,
    frameworks: list,
    component_units: list,
    file_categories: dict,
    folder_structure: str,
    entry_points: list,
    dependency_content: str,
    symbol_index: dict,
    file_entries: list,
) -> str:
    """
    Generate a Code Wiki-style document: one flowing narrative, deep explanations,
    natural topic organization (no numbered sections). Inspired by codewiki.google.
    """
    _, _, key_excerpts = _compute_metrics_and_excerpts(file_entries, entry_points, symbol_index)
    content_by_path = {path: content for path, content in file_entries if content}
    context = _build_code_wiki_context(
        repo_url, repo_name, metrics, frameworks, component_units,
        file_categories, folder_structure, entry_points, dependency_content,
        symbol_index, content_by_path, key_excerpts,
    )

    prompt = f"""You are an expert technical writer creating documentation like Google Code Wiki (https://codewiki.google). Your goal is to write a DEEP, FLOWING explanation of this codebase—not a checklist or section-by-section report.

## Codebase context

{context}

---

## Instructions

Write ONE Markdown document that reads like a well-crafted technical article or wiki page. 

**STYLE (match Code Wiki):**
- Start with a single H1 title (the project/repo name).
- Open with 2–4 sentences that capture what this project is and why it exists.
- Organize content by NATURAL TOPICS, not numbered sections. Use headings like "Overview", "Architecture", "How It Works", "Key Components", "Data and Types", "Configuration", "Development Notes" — whatever fits the codebase.
- Write in flowing prose. Explain the WHY and HOW, not just lists. Connect ideas. Describe how parts relate.
- Reference files with backticks when discussing code (e.g. `src/app/main.ts`).
- When explaining code, quote short relevant snippets inline and explain what they do.
- Be comprehensive but readable. A developer new to the project should understand it deeply after reading.
- NO "Section 1", "Section 2", "Essential information:", or rigid report structure.
- NO bullet-point dumps. Prefer paragraphs and short lists only when they aid clarity.
- If the project has components, services, or modules—explain each in context, with purpose and relationships.

**OUTPUT:** Valid Markdown only. Start directly with the H1. No preamble or meta-commentary.
"""
    return generate_documentation(prompt)


def generate_documentation(prompt: str) -> str:
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=OLLAMA_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data.get("response", "")
        if not text:
            return "# Documentation\n\nNo content generated. Ensure Ollama is running and qwen2.5-coder:7b is available (ollama pull qwen2.5-coder:7b)."
        return text.strip()
    except requests.ConnectionError:
        raise ConnectionError(
            "Ollama is not running. Start Ollama (e.g. run 'ollama serve' and 'ollama pull qwen2.5-coder:7b') and try again."
        )
    except requests.Timeout:
        raise ConnectionError("Ollama request timed out. Try again or increase OLLAMA_TIMEOUT.")
    except requests.RequestException as e:
        raise ConnectionError(f"Ollama request failed: {e}")
