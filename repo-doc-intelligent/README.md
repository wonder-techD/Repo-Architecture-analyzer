# Repo Doc — Intelligent Documentation Platform

Fully local GitHub repository analyzer that generates multi-language documentation, symbol/import/call graphs, and PDF from a single Markdown source.

## Backend

```bash
cd repo-doc-intelligent/backend
pip install -r requirements.txt
uvicorn main:app --reload
```

API runs at `http://localhost:8000`. Ensure [Ollama](https://ollama.ai) is installed and running: `ollama serve`, `ollama pull qwen2.5-coder:7b` (LLM), and `ollama pull nomic-embed-text` (RAG embeddings).

## Frontend

```bash
cd repo-doc-intelligent/frontend
npm install
npm run dev
```

App runs at `http://localhost:5173`. Set `VITE_API_URL=http://localhost:8000` if the frontend is not using the Vite proxy (e.g. production build).

## Usage

1. Open the app, enter a public GitHub URL (e.g. `https://github.com/owner/repo`), click **Generate**.
2. You are redirected to the dashboard with documentation, metadata, and architecture diagram.
3. Use **Download PDF** to get a PDF generated from the same Markdown file shown in the UI.
