"""
RAG: split documentation by ## sections, embed via Ollama, store vectors, retrieve by similarity.
"""
import json
import re
import os
import requests
from typing import Any

from config import (
    JOBS_DIR,
    OLLAMA_EMBED_URL,
    OLLAMA_EMBED_MODEL,
    OLLAMA_EMBED_TIMEOUT,
    RAG_TOP_K,
)


def split_md_by_sections(markdown: str) -> list[dict[str, str]]:
    """Split markdown by ## headings. Returns list of {title, content} (content includes optional intro before first ##)."""
    sections: list[dict[str, str]] = []
    # Split on lines that are exactly ## ... (with optional leading/trailing spaces)
    parts = re.split(r"^##\s+(.+)$", markdown.strip(), flags=re.MULTILINE)
    if not parts:
        return sections
    # parts[0] can be intro before first ##; then alternating: title, content, title, content...
    first = parts[0].strip()
    if first:
        sections.append({"title": "Introduction", "content": first})
    for i in range(1, len(parts) - 1, 2):
        title = parts[i].strip()
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if not title:
            continue
        sections.append({"title": title, "content": content})
    return sections


def get_embedding(text: str) -> list[float]:
    """Call Ollama embeddings API; return single embedding vector. Supports both /api/embeddings (prompt) and /api/embed (input)."""
    if not text or not text.strip():
        return []
    # Prefer prompt/embedding (older Ollama); fallback to input/embeddings (newer)
    try:
        r = requests.post(
            OLLAMA_EMBED_URL,
            json={"model": OLLAMA_EMBED_MODEL, "prompt": text.strip()},
            timeout=OLLAMA_EMBED_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        if "embedding" in data:
            return data["embedding"]
        if "embeddings" in data and data["embeddings"]:
            return data["embeddings"][0]
    except requests.RequestException:
        pass
    # Try /api/embed style (input -> embeddings)
    try:
        r = requests.post(
            OLLAMA_EMBED_URL,
            json={"model": OLLAMA_EMBED_MODEL, "input": text.strip()},
            timeout=OLLAMA_EMBED_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        if "embeddings" in data and data["embeddings"]:
            return data["embeddings"][0]
        if "embedding" in data:
            return data["embedding"]
    except requests.RequestException:
        pass
    return []


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def build_and_save_vectors(job_dir: str) -> None:
    """Read documentation.md, split by ##, embed each section, save to job_dir/vectors.json."""
    doc_path = os.path.join(job_dir, "documentation.md")
    if not os.path.isfile(doc_path):
        return
    with open(doc_path, "r", encoding="utf-8", errors="replace") as f:
        markdown = f.read()
    sections = split_md_by_sections(markdown)
    if not sections:
        return
    vectors: list[dict[str, Any]] = []
    for s in sections:
        text = f"{s['title']}\n\n{s['content']}".strip()
        emb = get_embedding(text)
        if not emb:
            continue
        vectors.append({
            "title": s["title"],
            "content": s["content"],
            "embedding": emb,
        })
    if not vectors:
        return
    out_path = os.path.join(job_dir, "vectors.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(vectors, f, ensure_ascii=False, indent=0)


def load_vectors(job_dir: str) -> list[dict[str, Any]]:
    """Load vectors.json from job dir. Returns list of {title, content, embedding}."""
    path = os.path.join(job_dir, "vectors.json")
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def retrieve_top_sections(
    vectors: list[dict[str, Any]],
    query_embedding: list[float],
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    """Return top_k sections by cosine similarity (title + content only, no embedding)."""
    k = top_k if top_k is not None else min(RAG_TOP_K, max(1, len(vectors)))
    if not query_embedding or not vectors:
        return []
    scored = [
        (cosine_similarity(v["embedding"], query_embedding), v)
        for v in vectors
    ]
    scored.sort(key=lambda x: -x[0])
    return [v for _, v in scored[:k]]
