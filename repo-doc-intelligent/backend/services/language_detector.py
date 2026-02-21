import os
from collections import defaultdict

EXT_TO_LANG = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".jsx": "React JSX",
    ".tsx": "React TSX",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".c": "C",
    ".h": "C",
    ".cpp": "C++",
    ".hpp": "C++",
    ".cs": "C#",
    ".php": "PHP",
    ".rb": "Ruby",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".scala": "Scala",
    ".r": "R",
    ".sql": "SQL",
    ".sh": "Shell",
    ".bash": "Bash",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".json": "JSON",
    ".toml": "TOML",
    ".md": "Markdown",
    ".txt": "Text",
    ".xml": "XML",
    ".html": "HTML",
    ".css": "CSS",
    ".vue": "Vue",
    ".svelte": "Svelte",
}


def detect_languages(file_entries):
    counts = defaultdict(int)
    for rel_path, _ in file_entries:
        ext = os.path.splitext(rel_path)[1].lower()
        lang = EXT_TO_LANG.get(ext, "Other")
        counts[lang] += 1
    return dict(counts)
