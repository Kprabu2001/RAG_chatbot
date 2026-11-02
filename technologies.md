# Technologies Used

This document describes every major technology in the **AI Voice & Chat PDF Assistant** — what it does, where it lives in the code, and how it is configured.

---

## At a Glance

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| UI | Streamlit | `>=1.38,<1.59` | Browser-based chat and voice interface |
| API | FastAPI | `0.139.x` (`>=0.110,<0.140`) | REST endpoints, request validation |
| ASGI server | Uvicorn | `0.54.x` (via `fastapi[standard]`) | Serves the API on port 8000 |
| Language | Python | 3.12 (`>=3.10`) | Backend and frontend runtime |
| LLM | Groq — `openai/gpt-oss-120b` | `groq` 0.37, `langchain-groq` 1.1.3 | Answer generation over retrieved context |
| Orchestration | LangChain | `langchain` 1.4.7, `langchain-core` 1.7.1 | Prompt templates, runnables, document model |
| Embeddings | fastembed (BGE-small-en-v1.5) | `0.9.1` | Local CPU text → 384-dim vectors |
| Vector store | Qdrant Cloud | `>=1.12,<2` | Managed similarity search for PDF chunks |
| Semantic cache | Valkey | `valkey` 6.2.0 / server `valkey/valkey:8` | Caches Q&A by cosine similarity |
| Numerics | NumPy | `2.5.4` | Cosine similarity math |
| PDF parsing | PyPDFLoader (pypdf) | `pypdf` 6.21.4 | Extract text from uploaded PDFs |
| Text splitting | RecursiveCharacterTextSplitter | `langchain-text-splitters` 1.1.3 | Chunk text for embedding |
| Speech-to-text | Groq Whisper `whisper-large-v3` | `groq` 0.37 | Transcribe recorded audio |
| Text-to-speech | edge-tts (Microsoft) | `7.3.1` | Voice playback of answers |
| File storage | Cloudinary | `1.46.3` | Cloud backup of uploaded PDFs |
| HTTP client | Requests | `>=2.31,<3` | Frontend → backend calls |
| Containers | Docker / Docker Compose | `python:3.12-slim` | Backend + Valkey services |
| Config | python-dotenv | `1.x` | `.env` loading |
| Testing | pytest + pytest-asyncio | `>=8`, `>=0.23` | Backend tests (dev extra) |

---

## 1. Frontend — Streamlit

**Where:** `frontend/app.py`, `frontend/components/`, `frontend/api/client.py`

A pure-Python UI so the whole product can ship without JavaScript.

- `st.tabs` splits the app into **Chat Q&A** and **Voice Q&A** (`app.py:23`).
- `st.file_uploader` + `st.button` drive upload (`components/sidebar.py`).
- `st.chat_message` / `st.chat_input` render the conversation (`components/chat_tab.py`).
- `st.audio_input` records voice questions (`components/voice_tab.py:18`).
- `st.toggle` implements the **Chat Memory** switch (`components/sidebar.py:25`).
- `st.session_state` keeps `chat_history`, `uploaded_pdfs`, a per-browser `session_id` (UUID4), and the memory flag.
- `components/voice_tab.py` hashes each recording with MD5 so Streamlit reruns do not resend the same audio.
- `utils/audio.py` auto-plays the base64 audio returned by the API.

**Config:** `frontend/.env` → `BACKEND_URL` (default `http://localhost:8000`), read in `frontend/config.py`.

**Version pin:** `streamlit>=1.38,<1.59` — the lower bound is required for `st.audio_input`.

---

## 2. Backend — FastAPI + Uvicorn + Pydantic

**Where:** `backend/backend/main.py`, `backend/base/app/server.py`, `backend/*/api/v1/*`

- `FastAPI` app is created by a thin subclass `AppServer` that only adds **CORS** (`base/app/server.py:5`).
- CORS origins come from `CORS_ORIGINS` (comma-separated, default `*`) because the Streamlit client runs on a different origin.
- Routers are mounted per feature: `pdf_router`, `chat_router`, `voice_router` (`main.py:8-10`).
- **Pydantic 2** models validate requests/responses (`*/schemas/*.py`).
- Endpoints:
  - `GET /health`
  - `POST /v1/pdf/upload` (multipart)
  - `POST /v1/chat/ask` (JSON)
  - `POST /v1/voice/chat` (multipart audio)
- Interactive docs are auto-generated at `/docs`.

**Architecture pattern:** each feature folder (`pdf/`, `chat/`, `asr/`, `rag/`) is split into `api/v1` (routes), `schemas` (contracts), and `services` (logic). Routes stay thin; services hold behavior.

**Server:** Uvicorn ASGI, started by the container as:
```
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

---

## 3. LLM — Groq + LangChain

**Where:** `backend/backend/rag/services/llm_service.py`

- `ChatGroq` from **langchain-groq** wraps the **Groq** inference API.
- Model: **`openai/gpt-oss-120b`** (configurable via `GROQ_MODEL` env var, default in `base/config/settings.py:12`).
- Generation settings: `temperature=0.1`, `max_tokens=2048`, `reasoning_effort="low"`. GPT-OSS does not support `reasoning_format`.
- Prompting: a `ChatPromptTemplate` (`RAG_PROMPT`) instructs the model to answer **only** from supplied context and to refuse otherwise.
- Chain: `self.prompt | self.llm` (LangChain Runnable composition).
- Output hygiene: `_strip_thinking()` removes any `<think>...</think>` reasoning block with a compiled regex before returning text (`llm_service.py:19,43`).
- Low temperature is deliberate: factual extraction from documents, not creative writing.

**Why Groq:** very low latency for both chat and Whisper transcription, and one API key covers both.

---

## 4. Embeddings — fastembed (BGE-small-en-v1.5)

**Where:** `backend/backend/rag/services/embedding_service.py`

- `TextEmbedding()` from **fastembed** runs the **BAAI/bge-small-en-v1.5** ONNX model locally on CPU.
- Produces **384-dimensional** vectors; no API key, no per-token cost, no network dependency at query time.
- Implemented as a **singleton** (`__new__` guard) so the ONNX model loads once per process and is shared by the vector service and the cache service.
- The Docker build pre-downloads the model (`Dockerfile:6`) so the first request is not penalized.
- Runtime deps pulled in: `onnxruntime` 1.31, `tokenizers` 0.23, `huggingface-hub` 1.33.

---

## 5. Vector Store — Qdrant Cloud

**Where:** `backend/backend/rag/services/vector_service.py`

- `QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)` — vectors live in a managed Qdrant Cloud cluster.
- Collection: **`pdf_docs`** (`settings.QDRANT_COLLECTION`), created on first use with `VectorParams(size=384, distance=Distance.COSINE)`.
- Ingest: each chunk becomes a `PointStruct` with a deterministic UUID5 id, its 384-dim vector, and a payload (`text`, `source`, `page`, `chunk_id`, `cloudinary_url`, `session_id`).
- Query: `client.query_points(...)` returns the top **4** nearest chunks (`K_RETRIEVED_DOCS`).
- Chat Memory OFF adds a payload filter:
  ```python
  Filter(must=[FieldCondition(key="session_id", match=MatchValue(value=session_id))])
  ```
- `VectorService` is a process-wide singleton, so every route shares one client.
- `reset_collection()` deletes and recreates the collection.
- Free tier: 1 GB RAM / 4 GB disk, single node; unused clusters suspend after 1 week and are deleted after 4 weeks.

**Chat Memory semantics:** `memory_enabled=True` searches every document; `False` filters Qdrant by the current browser session ID.

---

## 6. Semantic Cache — Valkey

**Where:** `backend/backend/rag/services/cache_service.py`

- Client: **`valkey`** Python package (Redis-compatible), server image `valkey/valkey:8`.
- Keys: `cache:<hash(question)>`.
- Values: JSON `{question, answer, embedding}` stored with `SETEX` and **TTL 3600 s**.
- Lookup is *semantic*, not exact: the question is embedded, then compared with every cached embedding using **cosine similarity** (NumPy).
- Hit threshold: **0.92**. The best match above it is returned immediately; otherwise the RAG pipeline runs.
- Because it precomputes the embedding once per request, the cache check is cheap.
- `clear()` deletes all `cache:*` keys.

**Why the cache comes first:** it skips Qdrant queries and LLM calls, cutting latency and cost. The strict 0.92 threshold prefers a miss over a wrong answer.

---

## 7. PDF Processing — PyPDFLoader + RecursiveCharacterTextSplitter

**Where:** `backend/backend/pdf/services/pdf_service.py`

- `PyPDFLoader` (langchain-community, backed by **pypdf**) extracts page text and page metadata.
- `RecursiveCharacterTextSplitter` with:
  - `chunk_size=1000` characters
  - `chunk_overlap=200`
  - separator priority `["\n\n", "\n", " ", ""]` — paragraphs, then lines, then words.
- Each chunk gets a sequential `chunk_id` in metadata.
- `process_pdf()` = load → split, returning `Document` objects ready for embedding.

---

## 8. Speech-to-Text — Groq Whisper

**Where:** `backend/backend/asr/services/stt_service.py`

- Uses the **Groq** SDK directly (`client.audio.transcriptions.create`).
- Model: **`whisper-large-v3`**, `response_format="text"`.
- Audio bytes are written to a temp `.wav` file, transcribed, and the file is removed in a `finally` block.

---

## 9. Text-to-Speech — edge-tts

**Where:** `backend/backend/asr/services/tts_service.py`

- **edge-tts** streams audio from Microsoft's Edge TTS engine — free, no API key.
- Voice: **`en-IN-NeerjaNeural`** (`settings.EDGE_TTS_VOICE`).
- The streamed MP3 bytes are base64-encoded and returned in the JSON response; the browser plays them without a file download.
- `async for` chunk streaming keeps memory usage flat.

---

## 10. File Storage — Cloudinary

**Where:** `backend/backend/pdf/services/cloudinary_service.py`

- Uploads the original PDF with `resource_type="raw"` under `pdf_chat_assistant/`.
- Returns a `secure_url` that is: (a) returned to the client, and (b) stored in every chunk's metadata.
- Credentials come from environment variables (`CLOUDINARY_*`).
- `delete_pdf()` reconstructs the `public_id` from the URL.

---

## 11. Infrastructure — Docker & Docker Compose

**Where:** `backend/Dockerfile`, `backend/docker-compose.yml`

| Service | Image | Port | Notes |
|---------|-------|------|-------|
| `app` | built from `Dockerfile` | 8000 | `python:3.12-slim`, installs the package, pre-fetches the embedding model |
| `valkey` | `valkey/valkey:8` | 6379 | Healthchecked with `valkey-cli ping`; named volume `valkey_data` |

- `app` waits for Valkey to be healthy (`depends_on: condition: service_healthy`).
- `../.env` is injected via `env_file`.
- Vector data lives in Qdrant Cloud, so the container needs no persistent volume for vectors.
- `restart: unless-stopped` for both services.
- `.dockerignore` excludes `venv/`, `__pycache__/`, `*.pyc`, `.env`.

**Local (non-Docker) alternative:** `uvicorn backend.main:app --reload --port 8000`, with Valkey running separately on `localhost:6379`.

---

## 12. Configuration, Security & Observability

**Where:** `backend/backend/base/config/settings.py`, `.env`, `.env.example`

- A single `Settings` class centralizes configuration; values come from `os.getenv` with sane defaults.
- `python-dotenv` loads the root `.env` at import time.
- Secrets (Groq key, Cloudinary credentials) live only in `.env` (git-ignored) — never in code.
- Tunable knobs: `CHUNK_SIZE`, `CHUNK_OVERLAP`, `K_RETRIEVED_DOCS`, `CACHE_TTL`, `CACHE_SIMILARITY_THRESHOLD`, `GROQ_MODEL`.
- Logging is Uvicorn's default access/error log to stdout (captured by `docker logs`).
- Health endpoint `/health` exists for probes.

---

## 13. Testing — pytest

**Where:** dev extra in `backend/pyproject.toml`

- `pytest>=8`, `pytest-asyncio>=0.23`, `asyncio_mode = "auto"`.
- Test discovery: `test_*.py` under `backend/`.

---

## 14. Data Flow (Technology View)

```
Streamlit (8501)
   │  requests
   ▼
FastAPI/Uvicorn (8000)
   │
   ├─ Upload:  PyPDFLoader → RecursiveCharacterTextSplitter
   │           → fastembed (384-d) → Qdrant Cloud
   │           → Cloudinary (raw file backup)
   │
   ├─ Ask:     Valkey semantic cache (cosine ≥ 0.92)
   │           → Qdrant Cloud top-4 → ChatGroq (openai/gpt-oss-120b)
   │           → store answer in Valkey
   │
   └─ Voice:   Groq Whisper (STT) → same Ask pipeline → edge-tts (base64 audio)
```

---

## 15. Design Rationale

| Decision | Why |
|----------|-----|
| Groq for LLM + STT | One key, very low latency for both chat and transcription |
| fastembed instead of a hosted embedding API | Free, local CPU, no rate limits or API key |
| Qdrant Cloud | Managed, no disk to maintain, fast payload filtering, free tier |
| Valkey for cache | In-memory speed, TTL, Redis-compatible tooling |
| Cache check before retrieval | Saves vector queries and LLM tokens on repeated/similar questions |
| 0.92 similarity threshold | False cache hits are worse than a cache miss |
| 1000/200 chunking | Balances context richness with retrieval precision |
| `temperature=0.1` | Deterministic, document-grounded answers |
| `<think>` stripping | Reasoning models may leak chain-of-thought even when suppressed |
| edge-tts | No extra API key or billing for speech output |
| Streamlit | Entire UI in Python; no separate JS build step |
| Modular feature folders | Routes, schemas, and services isolated per domain |

---

## 16. Package Version Reference

Backend (resolved in the container image):

| Package | Version |
|---------|---------|
| fastapi | 0.139.2 |
| starlette | 1.10.0 |
| pydantic | 2.14.1 |
| uvicorn | 0.54.0 |
| langchain | 1.4.7 |
| langchain-core | 1.7.1 |
| langchain-groq | 1.1.3 |
| langchain-community | 0.4.2 |
| langchain-text-splitters | 1.1.3 |
| qdrant-client | 1.12+ |
| fastembed | 0.9.1 |
| groq | 0.37.1 |
| edge-tts | 7.3.1 |
| pypdf | 6.21.4 |
| cloudinary | 1.46.3 |
| valkey | 6.2.0 |
| numpy | 2.5.4 |
| onnxruntime | 1.31.1 |

Frontend:

| Package | Constraint |
|---------|-----------|
| streamlit | `>=1.35.0,<1.59.0` |
| requests | `>=2.31.0,<3.0.0` |
| python-dotenv | `>=1.0.0,<2.0.0` |

Infrastructure:

| Component | Version |
|-----------|---------|
| Python base image | `python:3.12-slim` |
| Valkey server | `valkey/valkey:8` |

---

## Note on Documentation Drift

The live default in `backend/base/config/settings.py:12` is **`openai/gpt-oss-120b`** (overridable with `GROQ_MODEL`). Treat the code as the source of truth.
