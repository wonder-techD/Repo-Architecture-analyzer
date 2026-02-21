import os

STORAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage")
JOBS_DIR = os.path.join(STORAGE_DIR, "jobs")

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_CHAT_URL = os.environ.get("OLLAMA_CHAT_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b")
OLLAMA_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "300"))
OLLAMA_EMBED_URL = os.environ.get("OLLAMA_EMBED_URL", "http://localhost:11434/api/embeddings")
OLLAMA_EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_EMBED_TIMEOUT = int(os.environ.get("OLLAMA_EMBED_TIMEOUT", "60"))
RAG_TOP_K = int(os.environ.get("RAG_TOP_K", "5"))

EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    "venv",
    ".venv",
    "build",
    "dist",
    ".next",
    "target",
}

CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
