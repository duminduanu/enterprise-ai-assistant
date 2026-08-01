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
| LLM | OpenAI (configurable) |

## Project structure

```
enterprise-ai-assistant/
├── backend/           # FastAPI + LangGraph + retrieval + security
├── frontend/          # Streamlit chat UI + agent activity panel
├── mcp_server/        # MCP server with dummy enterprise data
├── scripts/           # Ingestion and data generation
├── data/              # Mock documents
└── docs/              # Architecture and design docs
```

## Prerequisites

- Python 3.11+
- Pinecone account + index (`enterprise-ai-assistant`, dimension 1536)
- LangSmith project
- OpenAI API key

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

3. Generate mock documents and ingest (coming in next steps):

   ```bash
   python scripts/generate_mock_data.py
   python scripts/ingest_documents.py
   ```

4. Run backend and frontend (coming in later steps):

   ```bash
   uvicorn backend.app.main:app --reload
   streamlit run frontend/streamlit_app.py
   ```

## Environment variables

See [`.env.example`](.env.example) for all required configuration.

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
- Hybrid search: Pinecone dense + in-process BM25
- RLM: simplified batch decomposition (not full Python plan execution)

## License

MIT
