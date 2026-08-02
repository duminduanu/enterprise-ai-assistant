# Enterprise AI Assistant

Enterprise-grade AI assistant for **Commercial Bank** internal knowledge — policies, runbooks, incident reports, architecture docs, and product specifications.

Built for the AI Tech Lead assessment: **LangGraph multi-agent orchestration**, **hybrid RAG**, **LangSmith observability**, **RBAC security**, **SSE streaming**, and a **Streamlit** UI with a live agent activity panel.

## Architecture

```
Streamlit UI → FastAPI (async) → LangGraph agents → Tools / Pinecone / MCP
                                      ↓
                                 LangSmith traces
```

**Agent pipeline:** Supervisor → Retrieval | Research (RLM) → Tools → Response → Validate

Full diagram and design notes: **[docs/architecture.md](docs/architecture.md)**

## Tech stack

| Layer | Technology |
|-------|------------|
| Frontend | Streamlit (chat + agent activity panel) |
| Backend | FastAPI (async) |
| Orchestration | LangGraph |
| Vector DB | Pinecone (dense) + in-process BM25 (sparse) |
| Observability | LangSmith |
| LLM | Google Gemini (`gemini-3.1-flash-lite`) |
| Embeddings | Google Gemini (`gemini-embedding-001`, 768 dims) |
| MCP | In-process enterprise data server |

## Project structure

```
enterprise-ai-assistant/
├── backend/app/       # FastAPI, agents, retrieval, security, tools
├── frontend/          # Streamlit UI + SSE API client
├── mcp_server/        # MCP server with dummy enterprise data
├── scripts/           # Ingestion, mock data, integration tests
├── data/              # Mock documents + processed BM25 corpus
├── docker/            # Backend & frontend Dockerfiles (bonus point)
├── docker-compose.yml # One-command deploy
└── docs/              # Architecture & memory design
```

## Prerequisites

- Python 3.11+
- [Google AI Studio](https://aistudio.google.com/apikey) API key (Gemini)
- [Pinecone](https://www.pinecone.io/) account + serverless index (**768 dimensions**, cosine)
- [LangSmith](https://smith.langchain.com/) project (optional but recommended for demo)

## Setup

### 1. Clone and install

```bash
git clone <your-repo-url>
cd enterprise-ai-assistant
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r backend/requirements.txt
```

### 2. Configure environment

```bash
copy .env.example .env          # Windows
# cp .env.example .env          # macOS/Linux
```

Fill in at minimum:

| Variable | Required |
|----------|----------|
| `GOOGLE_API_KEY` | Yes — LLM + embeddings |
| `PINECONE_API_KEY` | Yes — dense retrieval |
| `PINECONE_INDEX_NAME` | Yes — default `enterprise-ai-assistant-gemini` |
| `JWT_SECRET` | Yes for auth |
| `LANGSMITH_API_KEY` | Recommended for tracing demo |

See [`.env.example`](.env.example) for the full list.

### 3. Create Pinecone index

Create a **serverless** index:

- **Name:** `enterprise-ai-assistant-gemini`
- **Dimensions:** 768
- **Metric:** cosine

### 4. Generate and ingest documents

```bash
python scripts/generate_mock_data.py
python scripts/ingest_documents.py
```

This creates ~41 mock Commercial Bank markdown docs and upserts ~355 vectors to Pinecone plus a BM25 corpus at `data/processed/bm25_corpus.json`.

### 5. Run the backend

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

> **Windows note:** If port 8000 fails with `[WinError 10013]`, Windows may have reserved that port (Hyper-V/WSL). Use `--port 8080` and set `API_BASE_URL=http://127.0.0.1:8080` in `.env` and the Streamlit sidebar.

Verify:

```bash
curl http://127.0.0.1:8000/health
```

### 6. Run the Streamlit UI

```bash
streamlit run frontend/streamlit_app.py
```

Open the URL shown (default `http://localhost:8501`). Sign in with a demo account (below) or use dev mode (viewer role via header when `AUTH_REQUIRED=false`).

### 7. Run with Docker Compose (bonus)

Containerized deployment for demos and evaluators who prefer not to install Python locally.

**Prerequisites:** Docker Desktop (or Docker Engine + Compose v2), `.env` configured, and BM25 corpus generated:

```bash
python scripts/ingest_documents.py   # once, if data/processed/bm25_corpus.json is missing
```

**Start:**

```bash
docker compose up --build
```

| Service | URL |
|---------|-----|
| Streamlit UI | http://localhost:8501 |
| FastAPI API | http://localhost:8000 |
| Health check | http://localhost:8000/health |
| Swagger | http://localhost:8000/docs |

The frontend container uses `API_BASE_URL=http://backend:8000` on the internal Docker network. Your local `.env` `API_BASE_URL` is only for non-Docker runs.

**Stop:**

```bash
docker compose down
```

Files: `docker-compose.yml`, `docker/backend.Dockerfile`, `docker/frontend.Dockerfile`.

## Demo users

| Email | Password | Role |
|-------|----------|------|
| `viewer@commercialbank.com` | `viewer123` | viewer |
| `analyst@commercialbank.com` | `analyst123` | analyst |
| `admin@commercialbank.com` | `admin123` | admin |

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health + dependency status |
| POST | `/api/v1/auth/login` | JWT login |
| GET | `/api/v1/auth/me` | Current user profile |
| POST | `/api/v1/chat` | Multi-agent chat (JSON response) |
| POST | `/api/v1/chat/stream` | SSE stream (tokens + agent events) |
| POST | `/api/v1/search` | Direct hybrid search (debug) |

### Example: chat

```bash
curl -X POST http://127.0.0.1:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-User-Role: viewer" \
  -d "{\"message\": \"What is the password reset policy?\"}"
```

### Example: login + restricted search (admin)

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@commercialbank.com","password":"admin123"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -X POST http://127.0.0.1:8000/api/v1/search \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "restricted fraud investigation"}'
```

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `GOOGLE_API_KEY` | — | Gemini LLM + embeddings |
| `LLM_MODEL` | `gemini-3.1-flash-lite` | Chat model |
| `EMBEDDING_MODEL` | `gemini-embedding-001` | Embedding model |
| `EMBEDDING_DIMENSION` | `768` | Must match Pinecone index |
| `PINECONE_API_KEY` | — | Pinecone API key |
| `PINECONE_INDEX_NAME` | `enterprise-ai-assistant-gemini` | Index name |
| `HYBRID_ALPHA` | `0.7` | Dense vs sparse weight (1.0 = dense only) |
| `RETRIEVAL_TOP_K` | `5` | Results returned to agent |
| `LANGSMITH_TRACING` | `true` | Enable LangSmith traces |
| `LANGSMITH_PROJECT` | `enterprise-ai-assistant` | LangSmith project name |
| `JWT_SECRET` | — | JWT signing secret |
| `AUTH_REQUIRED` | `false` | Require Bearer token (dev: use `X-User-Role`) |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | `20` | Per-user token bucket |
| `SESSION_MEMORY_MAX_TURNS` | `10` | Conversation pairs per session |
| `AGENT_TIMEOUT_SECONDS` | `120` | Max agent run duration |
| `API_BASE_URL` | `http://127.0.0.1:8000` | Streamlit → backend URL |

## Model selection rationale

**Google Gemini** was chosen for this POC because:

- **Free tier** via Google AI Studio (no paid OpenAI credits required)
- **Single provider** for LLM and embeddings
- **`gemini-3.1-flash-lite`** — GA replacement for deprecated 2.x/2.5 models; new Google accounts cannot use `gemini-2.5-flash-lite` (404). Match `LLM_MODEL` to a model listed on your AI Studio rate-limit page.
- **`gemini-embedding-001`** — 768-dim vectors matching Pinecone index

**Trade-offs:**

- Pinecone index must be **768 dimensions** (not OpenAI's 1536)
- Free tier rate limits apply; ingestion uses batched embeds with backoff
- When LLM quota is exhausted, chat degrades to **retrieval-only fallback**
- Production would add multi-provider fallback and paid-tier SLAs

Provider factory: `backend/app/llm/provider.py`

## Security

| Control | Implementation |
|---------|----------------|
| **RBAC** | viewer / analyst / admin — tools, research route, restricted docs |
| **JWT auth** | `POST /api/v1/auth/login` with hardcoded demo users |
| **Prompt injection** | Input blocklist on chat + search; untrusted doc wrapping in prompts |
| **Rate limiting** | Token bucket per user (`RATE_LIMIT_REQUESTS_PER_MINUTE`) |
| **Guardrails** | Validate node: citation check, brand safety, tool audit |
| **Tool validation** | Pydantic schemas before tool execution |

Details: [docs/architecture.md#security-architecture](docs/architecture.md#security-architecture)

## Testing

Integration test scripts (run from project root with venv active):

```bash
python scripts/test_retrieval.py
python scripts/test_agent.py "Summarize payment outage reports"
python scripts/test_rbac.py
python scripts/test_security.py
python scripts/test_streaming.py
python scripts/test_session_memory.py
python scripts/test_error_handling.py
python scripts/test_multi_agent_collaboration.py
```

## Documentation

| Doc                                                                    | Description                                                                                        |
|------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------|
| [docs/architecture.md](docs/architecture.md)                           | System diagram, agent graph, security, RLM                                                         |
| [docs/memory-design.md](docs/memory-design.md)                         | Session memory design                                                                              |
| [docs/multi-agent-collaboration.md](docs/multi-agent-collaboration.md) | **bonus points:** shared state, handoffs, failure chains, butterfly effect                         |
| [docs/demo-video-guide.pdf](docs/demo-video-script.md)                 | **Demo:** demo video guide ([PDF](docs/demo-video-guide.pdf)) |

## Bonus features

### Multi-agent collaboration

Agents collaborate through shared **`AgentState`**: handoff notes, per-node status, failure chains, and butterfly-effect containment (retrieval escalation, tool circuit breaker, validation self-correction). See [docs/multi-agent-collaboration.md](docs/multi-agent-collaboration.md).

```bash
python scripts/test_multi_agent_collaboration.py
```

### Docker Compose (containerized deployment)

Run the full stack (FastAPI + Streamlit) with one command. See [Setup §7](#7-run-with-docker-compose-bonus).

```bash
docker compose up --build
```

## Assumptions & trade-offs

| Decision | POC choice | Production alternative |
|----------|------------|------------------------|
| Company context | Commercial Bank mock data, no real PII | Real CMDB + doc connectors |
| Auth | Hardcoded users + JWT | SSO / OIDC |
| Hybrid search | Pinecone dense + in-process BM25 | OpenSearch hybrid |
| RLM | LLM-planned batches with heuristic fallback | Full recursive plan execution |
| Memory | In-process per session | Redis / Postgres |
| MCP | In-process client | Sidecar MCP over stdio/SSE |
| Streaming | SSE from `/chat/stream` | WebSocket + CDN |
| Deployment | Local venv or **Docker Compose** | Kubernetes / managed PaaS |

## Demo video

<!-- Add your public demo URL here after recording -->
**Demo video:** _[Link to walkthrough — architecture, code, live demo, LangSmith traces]_

**Preparation:** [PDF](docs/demo-video-guide.pdf)

Suggested demo flow:

1. Architecture overview (`docs/architecture.md`)
2. Live Streamlit chat with agent activity panel
3. Complex RLM query: *"Summarize payment failure outages and recurring root causes"*
4. RBAC: viewer vs admin restricted doc access
5. LangSmith trace walkthrough
6. Security: injection blocked, rate limit
7. Assumptions and production next steps

## License

MIT
