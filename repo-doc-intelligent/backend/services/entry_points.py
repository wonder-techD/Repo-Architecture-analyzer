"""
Deterministic entry point detection per language and framework.
JS/TS: main.ts, index.ts, ReactDOM.render, createRoot, app.listen.
Python: if __name__ == "__main__", FastAPI, Flask, uvicorn.run.
Java: public static void main.
Framework-specific route entry detection (Express, FastAPI, Flask).
"""
import os
import re
from services.ast_analysis import analyze_file

# Canonical entry file names per language
ENTRY_FILES = {
    "main.py", "app.py", "manage.py", "main.js", "index.js", "index.ts", "main.ts",
    "server.js", "server.ts", "main.go", "main.rs", "Program.cs", "Main.java",
    "index.php", "app.ts", "app.tsx",
}

# Patterns: (pattern, description)
PYTHON_ENTRY_PATTERNS = [
    (re.compile(r"if\s+__name__\s*==\s*[\"']__main__[\"']", re.M), "main guard"),
    (re.compile(r"FastAPI\s*\(\s*\)"), "FastAPI app"),
    (re.compile(r"Flask\s*\(\s*__name__\s*\)"), "Flask app"),
    (re.compile(r"uvicorn\.run\s*\("), "uvicorn run"),
    (re.compile(r"app\.run\s*\("), "Flask/Starlette run"),
]
JS_TS_ENTRY_PATTERNS = [
    (re.compile(r"ReactDOM\.render\s*\("), "ReactDOM.render"),
    (re.compile(r"createRoot\s*\("), "React createRoot"),
    (re.compile(r"app\.listen\s*\("), "Express listen"),
    (re.compile(r"\.listen\s*\(\s*\d+"), "listen(port)"),
    (re.compile(r"createServer\s*\("), "Node createServer"),
]
JAVA_ENTRY_PATTERNS = [
    re.compile(r"public\s+static\s+void\s+main\s*\(\s*String"),
]
ROUTE_ENTRY_PATTERNS = [
    (re.compile(r"@app\.route\s*\(|@router\.(get|post|put|delete|patch)\s*\("), "Python route"),
    (re.compile(r"app\.(get|post|put|delete|patch)\s*\(\s*[\"']/"), "Express route"),
    (re.compile(r"router\.(get|post|put|delete|patch)\s*\("), "Express router"),
    (re.compile(r"@(get|post|put|delete)\s*\([\"']/"), "Decorator route"),
]


def _path_lang(rel_path: str) -> str:
    ext = (os.path.splitext(rel_path)[1] or "").lower()
    if ext in (".py",):
        return "python"
    if ext in (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"):
        return "js"
    if ext in (".java",):
        return "java"
    if ext in (".go", ".rs", ".c", ".cpp", ".cs"):
        return "native"
    return ""


def detect_entry_points(repo_root: str, file_entries: list, symbol_index: dict) -> list:
    entry_points = []
    for rel_path, content in file_entries:
        base = os.path.basename(rel_path)
        if base in ENTRY_FILES:
            entry_points.append(rel_path)

        if not content:
            continue
        lang = _path_lang(rel_path)
        result = analyze_file(rel_path, content)

        if lang == "python":
            if result.get("has_main_guard"):
                entry_points.append(rel_path)
            for pat, _ in PYTHON_ENTRY_PATTERNS:
                if pat.search(content):
                    entry_points.append(rel_path)
                    break
        elif lang == "js":
            for pat, _ in JS_TS_ENTRY_PATTERNS:
                if pat.search(content):
                    entry_points.append(rel_path)
                    break
        elif lang == "java":
            for pattern in JAVA_ENTRY_PATTERNS:
                if pattern.search(content):
                    entry_points.append(rel_path)
                    break

        for pat, _ in ROUTE_ENTRY_PATTERNS:
            if pat.search(content):
                entry_points.append(rel_path)
                break

    return list(dict.fromkeys(entry_points))
