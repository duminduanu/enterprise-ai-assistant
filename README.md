# Enterprise AI Assistant

Enterprise-grade AI assistant for **Commercial Bank** internal knowledge — policies, runbooks, incident reports, architecture docs, and product specifications.

Built for the AI Tech Lead assessment: LangGraph multi-agent orchestration, hybrid RAG, observability, security controls, and production-ready async patterns.

## Architecture (planned)

```
Streamlit UI → FastAPI (async) → LangGraph agents → Tools / Pinecone / MCP
                                      ↓
                                 LangSmith traces
```

**Agents:** Supervisor → Retrieval → Research (RLM) → Response → Validation

## Tech stack

| Layer | Technology |
|-------|------------|
| Frontend | Streamlit |
| Backend | FastAPI (async) |
| Orchestration | LangGraph |
| Vector DB | Pinecone (hybrid: dense + BM25) |
| Observability | LangSmith |
| LLM | Google Gemini (`gemini-2.0-flash`) |
| Embeddings | Google Gemini (`gemini-embedding-001`, 768 dims) |

## Project structure

```
enterprise-ai-assistant/
├── backend/           # FastAPI + LangGraph + retrieval + security
│   └── app/llm/       # Gemini LLM + embedding provider factory
├── frontend/          # Streamlit chat UI + agent activity panel
├── mcp_server/        # MCP server with dummy enterprise data
├── scripts/           # Ingestion and data generation
├── data/              # Mock documents
└── docs/              # Architecture and design docs
```

## Prerequisites

- Python 3.11+
- [Google AI Studio](https://aistudio.google.com/apikey) API key (Gemini)
- Pinecone account + index (`enterprise-ai-assistant-gemini`, **dimension 768**)
- LangSmith project

## Setup

1. Clone the repository and create a virtual environment:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate        # Windows
   pip install -r backend/requirements.txt
   ```

2. Copy environment template and fill in values:

   ```bash
   copy .env.example .env
   ```

3. Create a Pinecone **serverless** index named `enterprise-ai-assistant-gemini` with:
   - **Dimension:** 768
   - **Metric:** cosine

4. Generate mock documents and ingest:

   ```bash
   python scripts/generate_mock_data.py
   python scripts/ingest_documents.py
   ```

5. Run the API server:

   ```bash
   uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
   ```

   Test endpoints:
   - `GET http://localhost:8000/health`
   - `POST http://localhost:8000/api/v1/chat` — body: `{"message": "What is the password reset policy?"}`
   - `POST http://localhost:8000/api/v1/search` — body: `{"query": "payment failure outage"}`

6. Run frontend (coming in later steps):

   ```bash
   streamlit run frontend/streamlit_app.py
   ```

## Environment variables

See [`.env.example`](.env.example) for all required configuration.

Key variables:

| Variable | Purpose |
|----------|---------|
| `GOOGLE_API_KEY` | Gemini LLM + embeddings |
| `LLM_MODEL` | Chat model (default: `gemini-2.0-flash`) |
| `EMBEDDING_MODEL` | Embedding model (default: `gemini-embedding-001`) |
| `EMBEDDING_DIMENSION` | Must match Pinecone index (768) |
| `PINECONE_INDEX_NAME` | Pinecone index for dense vectors |

## Model selection rationale

**Google Gemini** was chosen for this POC because:

- **Free tier** available via Google AI Studio (no paid OpenAI credits required)
- **Single provider** for both LLM and embeddings simplifies integration
- **`gemini-2.0-flash`** offers strong speed/quality balance for multi-agent orchestration
- **`gemini-embedding-001`** provides 768-dimensional vectors (matches Pinecone index)

**Trade-offs:**

- Pinecone index must use **768 dimensions** (not OpenAI's 1536)
- Free tier rate limits apply — ingestion uses batched requests with backoff
- Production would evaluate multi-provider fallback and paid tier SLAs

Provider configuration is centralized in `backend/app/llm/provider.py`.

## Security

- RBAC: Viewer, Analyst, Administrator roles
- Prompt injection protection and input validation
- Rate limiting (token bucket per user)
- Document access filtered by role and metadata

## Documentation

- Architecture diagram: `docs/architecture.md` (coming soon)
- Memory design: `docs/memory-design.md` (coming soon)

## Assumptions & trade-offs

- Company context: Commercial Bank (mock data, no real PII)
- Auth: hardcoded users (Option A) for POC speed
- Hybrid search: Pinecone dense (Gemini embeddings) + in-process BM25
- RLM: simplified batch decomposition (not full Python plan execution)

## License

MIT
