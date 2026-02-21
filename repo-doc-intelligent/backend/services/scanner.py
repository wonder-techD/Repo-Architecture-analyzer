import os
from config import EXCLUDE_DIRS

TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".c", ".h", ".cpp", ".hpp",
    ".cs", ".php", ".rb", ".swift", ".kt", ".scala", ".r", ".sql", ".sh", ".bash", ".yaml",
    ".yml", ".json", ".toml", ".md", ".txt", ".xml", ".html", ".css", ".vue", ".svelte",
}


def scan_repo(repo_root: str):
    results = []
    for root, dirs, files in os.walk(repo_root, topdown=True):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        rel_root = os.path.relpath(root, repo_root)
        if rel_root == ".":
            rel_root = ""
        for name in files:
            ext = os.path.splitext(name)[1].lower()
            if ext not in TEXT_EXTENSIONS:
                continue
            path = os.path.join(root, name)
            rel_path = os.path.join(rel_root, name) if rel_root else name
            rel_path = rel_path.replace("\\", "/")
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except Exception:
                content = None
            results.append((rel_path, content))
    return results
