import json
import os
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

import requests
from config import STORAGE_DIR, JOBS_DIR, CORS_ORIGINS, OLLAMA_URL, OLLAMA_CHAT_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT, RAG_TOP_K

MASTER_RAG_SYSTEM_PROMPT = """You are a repository intelligence assistant.

You answer questions ONLY about the analyzed repository using the provided context.

Rules:

1. Use ONLY the provided repository context.
2. Do not use outside knowledge.
3. Do not speculate.
4. Do not fabricate file names, symbols, or frameworks.
5. If the answer is not present in the context, respond exactly with:

   "Not present in the provided repository context."

6. If the user question is unrelated to the repository,
   politely guide them to ask about repository architecture,
   files, or execution flow.

Use a friendly but precise tone.
Keep responses technically clear and grounded."""
from schemas import AnalyzeRequest, AnalyzeResponse, ContentResponse, ContentMetadata, AskRequest, AskResponse, ErrorResponse
from services.analyze_job import run_analyze_job
from services.pdf_service import ensure_pdf
from services.rag_vectors import load_vectors, get_embedding, retrieve_top_sections

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
    "hi", "hello", "hey", "thanks", "thank you", "ok", "okay", "cool", "great", "help",
}

_REPO_KEYWORDS = (
    "repo", "repository", "code", "file", "function", "class",
    "bootstrap", "entry", "call", "dependency", "architecture",
    "framework", "tech stack", "module", "route", "controller",
    "service", "component", "database",
)


def classify_intent(question: str) -> str:
    """Return one of: 'greeting', 'repo', 'non_repo'."""
    q = question.lower().strip()
    if q in _GREETING_PHRASES:
        return "greeting"
    for kw in _REPO_KEYWORDS:
        if kw in q:
            return "repo"
    return "non_repo"


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


@app.post("/ask/{job_id}", response_model=AskResponse)
def ask(job_id: str, body: AskRequest):
    intent = classify_intent(body.question)
    if intent == "greeting":
        return AskResponse(
            answer="Hi! You can ask me about this repository's architecture, execution flow, dependencies, or specific files.",
            sources=[],
        )
    if intent == "non_repo":
        return AskResponse(
            answer="I'm designed to answer questions about this analyzed repository. Please ask about its architecture, files, dependencies, or execution flow.",
            sources=[],
        )

    job_dir = os.path.join(JOBS_DIR, job_id)
    if not os.path.isdir(job_dir):
        raise HTTPException(status_code=404, detail="Job not found")
    doc_path = os.path.join(job_dir, "documentation.md")
    if not os.path.isfile(doc_path):
        raise HTTPException(status_code=404, detail="Documentation not found")

    vectors = load_vectors(job_dir)
    if not vectors:
        raise HTTPException(
            status_code=503,
            detail="RAG not available for this job. Re-run analysis with Ollama and an embedding model (e.g. ollama pull nomic-embed-text).",
        )

    query_embedding = get_embedding(body.question)
    if not query_embedding:
        raise HTTPException(
            status_code=503,
            detail="Could not embed question. Ensure Ollama is running and an embedding model is available (e.g. ollama pull nomic-embed-text).",
        )

    top = retrieve_top_sections(vectors, query_embedding, top_k=min(RAG_TOP_K, 5))
    if not top:
        raise HTTPException(status_code=503, detail="No sections could be retrieved.")

    context_blocks = []
    meta_ctx = _get_metadata_context(job_dir) if _is_tech_stack_question(body.question) else ""
    if meta_ctx:
        context_blocks.append(meta_ctx)
    for s in top:
        context_blocks.append(f"## {s['title']}\n{s['content']}")
    context_text = "\n\n".join(context_blocks)
    sources = (["Technology Stack (from repository metadata)"] if meta_ctx else []) + [s["title"] for s in top]

    question_with_context = f"""Repository context:

{context_text}

---

Question: {body.question}"""

    messages = [
        {"role": "system", "content": MASTER_RAG_SYSTEM_PROMPT},
        {"role": "user", "content": question_with_context},
    ]

    try:
        r = requests.post(
            OLLAMA_CHAT_URL,
            json={"model": OLLAMA_MODEL, "messages": messages, "stream": False},
            timeout=OLLAMA_TIMEOUT,
        )
        r.raise_for_status()
        answer = (r.json().get("message", {}).get("content") or "").strip()
    except requests.ConnectionError:
        raise HTTPException(status_code=503, detail="Ollama is not running. Start with: ollama serve && ollama pull qwen2.5-coder:7b")
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=str(e))
    return AskResponse(answer=answer, sources=sources)
