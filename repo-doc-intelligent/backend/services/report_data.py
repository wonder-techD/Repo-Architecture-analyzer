"""
Structured data for energent.ai-style report: metrics by type, component units (TS+HTML+CSS), file categories for Section 9.
"""
import os
import re
from collections import defaultdict

# File types for Key Metrics table (report-style)
TYPE_PATTERNS = [
    ("TypeScript", [".ts", ".tsx"]),
    ("JavaScript", [".js", ".jsx"]),
    ("HTML Templates", [".html", ".htm"]),
    ("CSS Stylesheets", [".css", ".scss", ".less"]),
    ("JSON Config", [".json"]),
    ("Python", [".py"]),
    ("Java", [".java"]),
    ("Go", [".go"]),
    ("Other", []),
]


def _ext_to_type(ext: str) -> str:
    ext = ext.lower()
    for label, exts in TYPE_PATTERNS:
        if ext in exts:
            return label
    return "Other"


def compute_metrics(file_entries: list, symbol_index: dict) -> dict:
    """Compute Key Metrics table data: total files, total lines, by-type counts and lines, component/service/interface counts."""
    total_lines = 0
    by_type = defaultdict(lambda: {"count": 0, "lines": 0})
    for rel_path, content in file_entries:
        lines = (content or "").splitlines()
        n = len(lines)
        total_lines += n
        ext = os.path.splitext(rel_path)[1].lower()
        t = _ext_to_type(ext)
        by_type[t]["count"] += 1
        by_type[t]["lines"] += n

    # Component count: files that define a class and look like components (e.g. *.component.ts, or path contains 'component')
    component_count = 0
    service_count = 0
    interface_count = 0
    for path, data in symbol_index.items():
        classes = data.get("classes", [])
        path_lower = path.lower()
        if any("component" in path_lower or "component" in c.lower() for c in classes):
            component_count += 1
        if "service" in path_lower or any("service" in c.lower() for c in classes):
            service_count += 1
        if "interface" in path_lower or path_lower.endswith("interface.ts") or any("interface" in c.lower() for c in classes):
            interface_count += 1
    # If no explicit interface files, count files that only have minimal exports (optional heuristic)
    if interface_count == 0:
        for path, data in symbol_index.items():
            if path.lower().endswith((".ts", ".tsx")) and not data.get("classes") and data.get("functions"):
                interface_count += 1
        interface_count = min(interface_count, 20)  # cap

    return {
        "total_files": len(file_entries),
        "total_lines": total_lines,
        "by_type": dict(by_type),
        "component_count": component_count,
        "service_count": service_count,
        "interface_count": interface_count,
    }


def get_component_units(file_entries: list, symbol_index: dict, repo_root: str) -> list:
    """
    Return list of component units: each has name, ts_path, html_path, css_path, line counts, and full content for TS/HTML/CSS.
    Pairs files by base name (e.g. app.component.ts + app.component.html + app.component.css).
    """
    content_by_path = {path: content for path, content in file_entries if content}
    # Find candidate component main files: .ts/.tsx with a class, and (path contains 'component' or ends with .component.ts)
    candidates = []
    for path in content_by_path:
        ext = os.path.splitext(path)[1].lower()
        if ext not in (".ts", ".tsx", ".js", ".jsx"):
            continue
        data = symbol_index.get(path, {})
        if data.get("classes") or "component" in path.lower():
            candidates.append(path)
    # Build component units: for each candidate, find sibling .html and .css
    units = []
    seen_bases = set()
    for ts_path in sorted(candidates):
        base, _ = os.path.splitext(ts_path)
        dirname = os.path.dirname(ts_path)
        base_name = os.path.basename(base)
        key = (dirname, base_name)
        if key in seen_bases:
            continue
        seen_bases.add(key)
        # Component name for heading (e.g. AppComponent from app.component.ts)
        name = base_name.replace(".", " ").replace("-", " ").title().replace(" ", "") or base_name
        if not name.endswith("Component") and "component" in ts_path.lower():
            name += "Component"
        html_path = None
        css_path = None
        for ext in [".html", ".htm", ".css", ".scss", ".less"]:
            p = base + ext
            if p in content_by_path:
                if ext in (".html", ".htm"):
                    html_path = p
                else:
                    css_path = p
        ts_content = content_by_path.get(ts_path) or ""
        html_content = content_by_path.get(html_path) if html_path else ""
        css_content = content_by_path.get(css_path) if css_path else ""
        ts_lines = len(ts_content.splitlines())
        html_lines = len(html_content.splitlines()) if html_content else 0
        css_lines = len(css_content.splitlines()) if css_content else 0
        units.append({
            "name": name,
            "ts_path": ts_path,
            "html_path": html_path,
            "css_path": css_path,
            "ts_lines": ts_lines,
            "html_lines": html_lines,
            "css_lines": css_lines,
            "ts_content": ts_content,
            "html_content": html_content or "",
            "css_content": css_content or "",
        })
    return units[:30]  # cap for large repos


def get_file_categories(file_entries: list, entry_points: list) -> dict:
    """Categorize files for Section 9 (Complete Source Code Listings). Keys: entry_points, app_config, components, config, other."""
    content_by_path = {path: content for path, content in file_entries if content}
    entry_set = set(entry_points or [])
    categories = {
        "entry_points": [],
        "app_config": [],
        "components": [],
        "config": [],
    }
    config_names = {"package.json", "tsconfig.json", "angular.json", "vite.config.js", "vite.config.ts", "requirements.txt", "pom.xml", "go.mod", "Cargo.toml", "app.config.ts", "app.routes.ts", "main.ts", "index.html"}
    for path in sorted(content_by_path.keys()):
        base = os.path.basename(path).lower()
        if path in entry_set or base in ("main.ts", "main.js", "index.html", "index.ts", "app.py", "main.py"):
            categories["entry_points"].append(path)
        elif base in config_names or "config" in path.lower() or path.endswith((".json", ".yaml", ".yml")) and path.count("/") <= 2:
            categories["app_config"].append(path)
        elif "component" in path.lower() or path.endswith((".component.ts", ".component.html", ".component.css")):
            categories["components"].append(path)
        else:
            categories["config"].append(path)
    # Dedupe and limit per category
    for k in list(categories.keys()):
        seen = set()
        out = []
        for p in categories[k]:
            if p not in seen:
                seen.add(p)
                out.append(p)
        categories[k] = out[:50]
    return categories
