import json
import os
import re
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

import requests
from config import STORAGE_DIR, JOBS_DIR, CORS_ORIGINS, OLLAMA_URL, OLLAMA_CHAT_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT, RAG_TOP_K

MASTER_RAG_SYSTEM_PROMPT = """You are an expert AI repository intelligence assistant.
You answer questions about the analyzed repository using the provided repository context (architecture, modules, frameworks, call flows, symbols, and metadata).

Guidelines:
1. Ground your answers primarily in the provided repository context and technical details.
2. If the user asks about the architecture, tech stack, functionality, entry points, or file structure, synthesize a clear, helpful, and technically accurate explanation.
3. If specific details are not explicitly described in the context, state what is known from the repository structure and mention what is not explicitly documented.
4. Format your responses with clean Markdown (bullet points, code snippets, bold text) for readability.
5. If the question is completely unrelated to software development or this repository, politely invite the user to ask about the codebase."""
from schemas import AnalyzeRequest, AnalyzeResponse, ContentResponse, ContentMetadata, AskRequest, AskResponse, ErrorResponse
from services.analyze_job import run_analyze_job
from services.pdf_service import ensure_pdf
from services.rag_vectors import load_vectors, get_embedding, retrieve_top_sections, split_md_by_sections

app = FastAPI(title="Repo Doc Intelligent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(STORAGE_DIR, exist_ok=True)
os.makedirs(JOBS_DIR, exist_ok=True)


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest):
    job_id = str(uuid.uuid4())
    try:
        run_analyze_job(job_id=job_id, repo_url=request.repo_url)
        return AnalyzeResponse(job_id=job_id, status="completed")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/content/{job_id}", response_model=ContentResponse)
def get_content(job_id: str):
    job_dir = os.path.join(JOBS_DIR, job_id)
    if not os.path.isdir(job_dir):
        raise HTTPException(status_code=404, detail="Job not found")

    doc_path = os.path.join(job_dir, "documentation.md")
    if not os.path.isfile(doc_path):
        raise HTTPException(status_code=404, detail="Documentation not found")

    with open(doc_path, "r", encoding="utf-8", errors="replace") as f:
        markdown = f.read()

    mermaid_path = os.path.join(job_dir, "diagram.mmd")
    mermaid = ""
    if os.path.isfile(mermaid_path):
        with open(mermaid_path, "r", encoding="utf-8", errors="replace") as f:
            mermaid = f.read()

    meta_path = os.path.join(job_dir, "metadata.json")
    metadata = ContentMetadata(file_count=0, languages={}, frameworks=[], entry_points=[])
    if os.path.isfile(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            metadata = ContentMetadata(
                file_count=data.get("file_count", 0),
                languages=data.get("languages", {}),
                frameworks=data.get("frameworks", []),
                entry_points=data.get("entry_points", []),
            )

    callgraph = {}
    cg_path = os.path.join(job_dir, "callgraph.json")
    if os.path.isfile(cg_path):
        with open(cg_path, "r", encoding="utf-8") as f:
            callgraph = json.load(f)

    importgraph = {}
    ig_path = os.path.join(job_dir, "importgraph.json")
    if os.path.isfile(ig_path):
        with open(ig_path, "r", encoding="utf-8") as f:
            importgraph = json.load(f)

    return ContentResponse(
        markdown=markdown,
        mermaid=mermaid,
        metadata=metadata,
        callgraph=callgraph,
        importgraph=importgraph,
    )


@app.get("/download/{job_id}")
def download_pdf(job_id: str):
    job_dir = os.path.join(JOBS_DIR, job_id)
    if not os.path.isdir(job_dir):
        raise HTTPException(status_code=404, detail="Job not found")
    doc_path = os.path.join(job_dir, "documentation.md")
    if not os.path.isfile(doc_path):
        raise HTTPException(status_code=404, detail="Documentation not found")

    pdf_path = os.path.join(job_dir, "final.pdf")
    try:
        ensure_pdf(job_dir)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")
    if not os.path.isfile(pdf_path):
        raise HTTPException(status_code=500, detail="PDF generation failed")

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename="documentation.pdf",
    )


_GREETING_PHRASES = {
    "hi", "hello", "hey", "greetings", "good morning", "good evening", "howdy",
}


def classify_intent(question: str) -> str:
    """Return 'greeting' for plain greetings, otherwise treat as repo question."""
    q = question.lower().strip().rstrip(".!?")
    if q in _GREETING_PHRASES or any(q.startswith(g + " ") for g in _GREETING_PHRASES):
        if len(q.split()) <= 4:
            return "greeting"
    return "repo"


_TECH_STACK_KEYWORDS = (
    "tech stack", "technology stack", "technologies", "technology", "frameworks",
    "framework", "libraries", "library", "stack", "dependencies",
    "languages used", "what languages", "tech stacks", "used in it",
)


def _is_tech_stack_question(question: str) -> bool:
    q = question.strip().lower()
    for kw in _TECH_STACK_KEYWORDS:
        if kw in q:
            return True
    if any(q.startswith(p) for p in ("what tech", "what technologies", "what framework", "what language", "what's the tech")):
        return True
    return False


def _get_metadata_context(job_dir: str) -> str:
    meta_path = os.path.join(job_dir, "metadata.json")
    if not os.path.isfile(meta_path):
        return ""
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return ""
    frameworks = data.get("frameworks") or []
    languages = data.get("languages") or {}
    parts = []
    if frameworks:
        parts.append("Frameworks: " + ", ".join(frameworks))
    if languages:
        lang_list = [f"{k} ({v} files)" if isinstance(v, int) else f"{k}" for k, v in list(languages.items())[:15]]
        parts.append("Languages (file counts): " + ", ".join(str(x) for x in lang_list))
    if not parts:
        return ""
    return "## Technology Stack (from repository metadata)\n\n" + "\n\n".join(parts)


def _keyword_retrieve_sections(job_dir: str, question: str, top_k: int = 5) -> list[dict]:
    doc_path = os.path.join(job_dir, "documentation.md")
    if not os.path.isfile(doc_path):
        return []
    with open(doc_path, "r", encoding="utf-8", errors="replace") as f:
        md = f.read()
    sections = split_md_by_sections(md)
    if not sections:
        return [{"title": "Overview", "content": md[:4000]}]

    stop_words = {
        "the", "a", "an", "is", "in", "it", "of", "and", "or", "to", "for",
        "with", "on", "at", "by", "this", "that", "how", "what", "where",
        "when", "why", "which", "who", "can", "you", "does", "do", "tell", "me",
    }
    words = [w for w in re.findall(r"\w+", question.lower()) if len(w) > 2 and w not in stop_words]

    scored = []
    for s in sections:
        title_lower = s["title"].lower()
        content_lower = s["content"].lower()
        title_matches = sum(title_lower.count(w) * 3 for w in words)
        content_matches = sum(content_lower.count(w) for w in words)
        score = title_matches + content_matches
        scored.append((score, s))

    scored.sort(key=lambda x: -x[0])
    top = [s for score, s in scored[:top_k]]
    return top


def get_available_ollama_model() -> str:
    """Return preferred model if available, else best installed model in Ollama."""
    try:
        base_url = OLLAMA_CHAT_URL.split("/api/")[0]
        r = requests.get(f"{base_url}/api/tags", timeout=2)
        if r.status_code == 200:
            models = [m.get("name", "") for m in r.json().get("models", [])]
            if OLLAMA_MODEL in models or any(m.startswith(OLLAMA_MODEL.split(":")[0]) for m in models):
                return OLLAMA_MODEL
            priority = ["qwen2.5-coder", "qwen2.5", "llama3", "llama3.2", "mistral", "gemma"]
            for p in priority:
                for m in models:
                    if p in m:
                        return m
            if models:
                return models[0]
    except Exception:
        pass
    return OLLAMA_MODEL


@app.post("/ask/{job_id}", response_model=AskResponse)
def ask(job_id: str, body: AskRequest):
    intent = classify_intent(body.question)
    if intent == "greeting":
        return AskResponse(
            answer="Hi! I am your repository assistant. Feel free to ask about this project's architecture, design patterns, dependencies, entry points, or implementation details.",
            sources=[],
        )

    job_dir = os.path.join(JOBS_DIR, job_id)
    if not os.path.isdir(job_dir):
        raise HTTPException(status_code=404, detail="Job not found")
    doc_path = os.path.join(job_dir, "documentation.md")
    if not os.path.isfile(doc_path):
        raise HTTPException(status_code=404, detail="Documentation not found")

    top = []
    # 1. Try vector retrieval if vectors exist and embedding succeeds
    try:
        vectors = load_vectors(job_dir)
        if vectors:
            query_embedding = get_embedding(body.question)
            if query_embedding:
                top = retrieve_top_sections(vectors, query_embedding, top_k=min(RAG_TOP_K, 5))
    except Exception:
        top = []

    # 2. Fall back to keyword section retrieval
    if not top:
        top = _keyword_retrieve_sections(job_dir, body.question, top_k=min(RAG_TOP_K, 5))

    context_blocks = []
    meta_ctx = _get_metadata_context(job_dir)
    if meta_ctx and (_is_tech_stack_question(body.question) or len(top) < 3):
        context_blocks.append(meta_ctx)
    for s in top:
        context_blocks.append(f"## {s['title']}\n{s['content']}")
    context_text = "\n\n".join(context_blocks)
    sources = (["Technology Stack (from repository metadata)"] if (meta_ctx and _is_tech_stack_question(body.question)) else []) + [s["title"] for s in top]

    question_with_context = f"""Repository context:

{context_text}

---

Question: {body.question}"""

    messages = [
        {"role": "system", "content": MASTER_RAG_SYSTEM_PROMPT},
        {"role": "user", "content": question_with_context},
    ]

    selected_model = get_available_ollama_model()

    try:
        r = requests.post(
            OLLAMA_CHAT_URL,
            json={"model": selected_model, "messages": messages, "stream": False},
            timeout=OLLAMA_TIMEOUT,
        )
        r.raise_for_status()
        answer = (r.json().get("message", {}).get("content") or "").strip()
    except requests.ConnectionError:
        raise HTTPException(status_code=503, detail="Ollama is not running. Please start Ollama with 'ollama serve'.")
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=str(e))
    return AskResponse(answer=answer, sources=sources)
