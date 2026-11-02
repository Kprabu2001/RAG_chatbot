## Project Architecture Overview — PDF Chat Assistant

This is a **modular monolith** RAG (Retrieval-Augmented Generation) application with voice support. Users upload PDFs, ask questions via text or voice, and get answers grounded in the document content.

---

### 1. High-Level Architecture

```
Streamlit Frontend (port 8501)
       │
       │ HTTP requests
       ▼
FastAPI Backend (port 8000)
       │
       ├── Valkey (in-memory semantic cache, port 6379)
       ├── Qdrant Cloud (managed vector store)
       └── External:
           ├── Groq Cloud (LLM, STT, TTS)
           ├── fastembed (local CPU embeddings, no API key)
           └── Cloudinary (raw PDF file storage)
```

---

### 2. Project Structure (Key Files)

```
chatbot/
├── backend/backend/
│   ├── main.py                          # FastAPI entry point, mounts routers
│   ├── base/
│   │   ├── app/server.py                # AppServer (FastAPI + CORS)
│   │   ├── config/settings.py           # Centralized config (singleton)
│   │   └── schemas/api_response.py      # Generic ApiResponse[T]
│   ├── pdf/
│   │   ├── api/v1/pdf_routes.py         # POST /v1/pdf/upload
│   │   ├── schemas/pdf_schemas.py       # UploadResponse
│   │   └── services/
│   │       ├── pdf_service.py           # PyPDFLoader + RecursiveCharacterTextSplitter
│   │       └── cloudinary_service.py    # Upload/delete raw PDFs
│   ├── rag/services/
│   │   ├── embedding_service.py         # Singleton: fastembed BGE-small-en-v1.5 (384-dim)
│   │   ├── vector_service.py            # Qdrant Cloud: ingest_pdf(), search_similar(), get_context()
│   │   ├── llm_service.py               # Groq GPT-OSS 120B + RAG prompt + <think> block stripping
│   │   └── cache_service.py             # Valkey: semantic cache via cosine similarity (threshold 0.92)
│   ├── chat/
│   │   ├── api/v1/chat_routes.py        # POST /v1/chat/ask
│   │   ├── schemas/chat_schemas.py      # ChatRequest / ChatResponse
│   │   └── services/chat_service.py     # Orchestrator: cache → vector → LLM → store
│   └── asr/
│       ├── api/v1/voice_routes.py       # POST /v1/voice/chat
│       ├── schemas/voice_schemas.py     # VoiceChatResponse
│       └── services/
│           ├── stt_service.py           # Groq Whisper large-v3
│           └── tts_service.py           # edge-tts (text-to-speech, returns base64)
├── frontend/
│   ├── app.py                           # Streamlit: sidebar + chat tab + voice tab
│   ├── components/
│   │   ├── sidebar.py                   # PDF upload form + file list
│   │   ├── chat_tab.py                  # Chat input + history display
│   │   └── voice_tab.py                 # Audio recorder + auto-play response
│   ├── api/client.py                    # HTTP client (requests) to backend
│   └── utils/audio.py                  # autoplay_audio helper
└── .env                                 # GROQ_API_KEY, Cloudinary creds, Valkey host/port, Qdrant URL/key
```

---

### 3. PDF Upload Flow (`POST /v1/pdf/upload`)

```
User uploads PDF → Streamlit sidebar → FastAPI
  1. Save uploaded bytes to OS temp file
  2. CloudinaryService.upload_pdf() → upload raw PDF to Cloudinary, get secure_url
  3. VectorService.ingest_pdf(file_path, cloudinary_url):
     a. PDFService.process_pdf():
        - PyPDFLoader → extract text pages
        - RecursiveCharacterTextSplitter (chunk_size=1000, overlap=200, separators: \n\n → \n → space → "")
        - Adds chunk_id metadata
     b. EmbeddingService.embed_documents() → 384-dim vectors via fastembed (BGE-small-en-v1.5)
     c. Qdrant upsert(points: UUID id, 384-dim vector, payload)
     d. Payload includes: text, source filename, page number, chunk_id, cloudinary_url, session_id
  4. Delete temp file
  5. Return UploadResponse {filename, chunk_count, cloudinary_url, message}
```

---

### 4. Chat Q&A Flow (`POST /v1/chat/ask`)

```
ChatService.process_question(question):
  1. SemanticCacheService.search(question):
     - Embed question via fastembed → query_vector
     - Scan Valkey "cache:*" keys → load entries → cosine similarity with cached_embedding
     - If best score ≥ 0.92 → return cached answer immediately (cached=true)
  2. On cache miss:
     - VectorService.get_context(question):
       a. embed_query(question) → 384-dim vector
       b. Qdrant query_points(limit=4) → top-4 most similar chunks (cosine)
       c. Concatenate chunks into context string
     - LLMService.generate_answer(question, context):
       a. RAG prompt: "Answer based ONLY on context. If not found, say so."
       b. ChatGroq(model="openai/gpt-oss-120b", temperature=0.1, max_tokens=2048, reasoning_effort="low")
       c. Strip <think>...</think> blocks (defensive against reasoning models)
     - SemanticCacheService.store(question, answer):
       a. key="cache:{hash(question)}", TTL=3600s
       b. Value: {question, answer, embedding}
  3. Return {answer, sources[], cached}
```

---

### 5. Voice Q&A Flow (`POST /v1/voice/chat`)

```
Voice route (multipart audio/wav):
  1. Read audio bytes from upload
  2. STTService.speech_to_text():
     - Save bytes to temp .wav file
     - Groq().audio.transcriptions.create(model="whisper-large-v3") → transcribed text
     - Delete temp file
  3. Same RAG pipeline as Chat:
     - Semantic cache check → if hit: use cached answer
     - Qdrant retrieval → LLM generation → store in cache
  4. TTSService.text_to_speech(answer):
     - edge_tts.Communicate(text, voice="en-IN-NeerjaNeural")
     - Stream audio chunks, concatenate → base64 encode
  5. Return VoiceChatResponse {question, answer, audio_base64, cached}
```

---

### 6. Tech Stack & Key Config

| Component | Technology | Detail |
|-----------|-----------|--------|
| Frontend | Streamlit | Port 8501 |
| Backend | FastAPI + Uvicorn | Port 8000 |
| LLM | Groq GPT-OSS 120B | temp=0.1, max_tokens=2048, reasoning_effort=low |
| Embeddings | fastembed BGE-small-en-v1.5 | 384-dim, local CPU, no API key |
| Vector DB | Qdrant Cloud (QdrantClient) | Managed free-tier cluster, 384-dim cosine |
| Cache | Valkey 8 | TTL=3600s, similarity threshold=0.92 |
| STT | Groq Whisper large-v3 | via `groq` Python SDK |
| TTS | edge-tts (Neerja Neural voice) | base64 audio returned to frontend |
| PDF Store | Cloudinary | resource_type="raw", folder="pdf_chat_assistant" |
| PDF Parsing | PyPDFLoader | langchain-community |
| Text Splitting | RecursiveCharacterTextSplitter | 1000 chars, 200 overlap |

---

### 7. Data Flow Summary

```
                    ┌─────────────────┐
                    │ Streamlit UI     │
                    │ (app.py)        │
                    └────┬──────┬─────┘
                         │      ▲
                   HTTP  │      │ HTTP
                         ▼      │
                    ┌─────────────────┐
                    │ FastAPI Routes  │
                    │ (pdf/chat/voice)│
                    └────┬──────┬─────┘
                         │      │
                    ┌────▼──────▼─────┐
                    │  ChatService    │
                    │ (orchestrator)  │
                    └────┬──────┬─────┘
                         │      │
               ┌─────────▼┐  ┌─▼──────────┐
                │ Valkey   │  │ Qdrant     │
               │ Cache    │  │ Vectors    │
               └──────────┘  └─┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │ Groq LLM            │
                    │ (answer generation) │
                    └─────────────────────┘
```

---

### 8. Design Decisions

- **No OpenAI** — Groq for LLM/STT/TTS + fastembed for local embeddings
- **Semantic cache before vector retrieval** — avoids unnecessary Qdrant queries and LLM calls for similar questions
- **Singleton EmbeddingService** — the ONNX model loads once regardless of how many services import it
- **`<think>` block stripping** — reasoning models can emit thinking blocks; regex strips them defensively
- **Cosine similarity threshold 0.92** — strict to avoid false cache hits
- **edge-tts instead of Groq TTS** — free, local TTS; no API key required
- **Modular monolith** — each domain (pdf, asr, chat, rag) has independent api/schemas/services layers

---

### 9. Key Endpoints

| Method | Endpoint | Request | Response |
|--------|----------|---------|----------|
| GET | `/health` | — | `{"status": "ok"}` |
| POST | `/v1/pdf/upload` | `file: PDF (multipart)` | `{filename, chunk_count, cloudinary_url, message}` |
| POST | `/v1/chat/ask` | `{question, session_id}` | `{answer, sources[], cached}` |
| POST | `/v1/voice/chat` | `file: audio/wav (multipart)` | `{question, answer, audio_base64, cached}` |

---

### 10. Docker Deployment

- `docker-compose.yml` defines two services: `app` (FastAPI) and `valkey` (cache)
- Valkey has health checks; the `app` service waits for `service_healthy`
- Vector data lives in Qdrant Cloud, so no persistent disk or bind mount is needed
- Fastembed model downloads on Docker build (`RUN python -c "from fastembed import TextEmbedding; TextEmbedding()"`)
- Frontend runs separately on host (`streamlit run frontend/app.py`)
