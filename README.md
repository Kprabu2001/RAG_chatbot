# AI Voice & Chat PDF Assistant

Upload a PDF, then ask questions about it — either by typing or by speaking. The app reads the PDF, finds the relevant parts, and answers based on what's actually in the document.

Built with RAG (Retrieval-Augmented Generation), Qdrant Cloud for vector search, Valkey for caching, and Groq for the LLM.

---

## What You Can Do

- **Upload any PDF** — The app reads it, splits it into chunks, converts each chunk to numbers (embeddings), and stores it for searching.
- **Chat about it** — Type a question, get an answer based only on the PDF content.
- **Ask with your voice** — Record audio, get back both text and spoken response.
- **Smart caching** — If you ask something similar to a previous question, it returns the cached answer instantly (saves time and API costs).
- **Chat Memory toggle** — A switch in the sidebar. Turn it ON to search all PDFs ever uploaded. Turn it OFF to get answers only from PDFs you uploaded in this session.

---

## How It Works (In Simple Terms)

**When you upload a PDF:**
1. Text is extracted from the PDF
2. It's split into ~1000-character chunks
3. Each chunk gets converted to a vector (384 numbers) using fastembed — this runs on your CPU, no API key needed
4. Everything is stored in Qdrant Cloud
5. The original PDF is backed up to Cloudinary

**When you ask a question:**
1. Check the Chat Memory toggle first. If it's OFF, only PDFs uploaded in this session will be searched. If ON, everything counts.
2. Then check if a similar question was asked before (Valkey cache, threshold >92% similarity)
3. If cached hit → return instantly
4. If miss → find the 4 most relevant chunks from Qdrant Cloud, send them to Groq's GPT-OSS model as context, get the answer, save it in cache for next time

**When you speak a question:**
1. Audio goes through Groq Whisper (speech-to-text)
2. Same chat pipeline runs on the transcribed text
3. Answer gets converted to speech using edge-tts
4. You see the text AND hear it spoken

---

## What You Need Before Starting

- Python 3.10+
- Valkey running somewhere (Docker is easiest)
- A Qdrant Cloud account (free tier at https://cloud.qdrant.io)
- A Groq API key (free at https://console.groq.com)
- A Cloudinary account (free tier, 25GB storage)

---

## Setup

### 1. Install dependencies

```powershell
python -m venv venv
.\venv\Scripts\Activate

pip install -e "backend\"
pip install -e "frontend\"
```

### 2. Start Valkey (pick one)

```powershell
# Option A: Docker
docker run -p 6379:6379 valkey/valkey

# Option B: Install from https://valkey.io/download
```

### 3. Set up environment variables

Edit `.env` in the project root:

```env
GROQ_API_KEY=gsk_your_groq_api_key
GROQ_MODEL=openai/gpt-oss-120b
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
VALKEY_HOST=localhost
VALKEY_PORT=6379
# Or use a single URL (supports rediss:// for TLS):
# VALKEY_URL=redis://localhost:6379/0
QDRANT_URL=https://your-cluster.aws.cloud.qdrant.io:6333
QDRANT_API_KEY=your_qdrant_api_key
QDRANT_COLLECTION=pdf_docs
```

### 4. Start the backend

```powershell
.\venv\Scripts\uvicorn backend.main:app --reload --port 8000
```

API docs are at `http://localhost:8000/docs`

### 5. Start the frontend (new terminal)

```powershell
.\venv\Scripts\streamlit run frontend/app.py
```

Open `http://localhost:8501` in your browser.

---

## Docker (Run the Backend in Containers)

The backend and Valkey can run in Docker. The frontend still runs on your machine.

```powershell
cd backend
docker compose up -d
```

Then start the frontend separately:

```powershell
streamlit run frontend/app.py
```

To stop:

```powershell
cd backend
docker compose down
```

| Service | What it is | Port |
|---------|-----------|------|
| `app` | FastAPI backend | 8000 |
| `valkey` | Cache server | 6379 |

---

## Deploy on Render (Two Services)

The repo includes a `render.yaml` blueprint that creates three free resources in the `oregon` region:

| Resource | Type | Root |
|----------|------|------|
| `pdf-rag-cache` | Render Key Value | - |
| `pdf-rag-backend` | Docker web service | `backend/` |
| `pdf-rag-frontend` | Python web service | `frontend/` |

### Steps

1. Rotate any keys that were exposed during local debugging (Groq, Cloudinary, Qdrant).
2. Push the repo to GitHub (`.env` is git-ignored; never commit it).
3. In the Render Dashboard: **New → Blueprint**, select the repo, and apply `render.yaml`.
4. When prompted, enter the secret values: `GROQ_API_KEY`, `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`, `QDRANT_URL`, `QDRANT_API_KEY`.
5. Wait for both builds. The backend health check is `/health`; the frontend health check is `/_stcore/health`.
6. If Render gives the backend a different name or URL, update `BACKEND_URL` on the frontend service to `https://<backend-name>.onrender.com` and redeploy the frontend.

### Free-tier behavior

- Both web services spin down after 15 minutes idle; the next request takes about a minute to wake them.
- The workspace gets 750 instance-hours/month total. Two services running 24/7 would exceed this, so avoid keeping them permanently warm.
- The backend has 512 MB RAM. If embeddings cause out-of-memory restarts, upgrade the backend to a paid instance.
- Free Key Value is 25 MB, in-memory, and may restart at any time. The cache is fail-open: if it is unavailable, chat still works.

---

## Tech Stack (One-Liners)

| Part | What We Use |
|------|-------------|
| Frontend | Streamlit |
| Backend | FastAPI + Python |
| AI Model | Groq GPT-OSS 120B (temperature 0.1) |
| Embeddings | fastembed (BGE-small-en-v1.5, local CPU, free) |
| Vector Database | Qdrant Cloud (free tier) |
| Semantic Cache | Valkey (TTL 1 hour) |
| Speech-to-Text | Groq Whisper large-v3 |
| Text-to-Speech | edge-tts (Microsoft) |
| PDF Storage | Cloudinary (free tier) |
| PDF Parsing | PyPDFLoader (langchain) |
| Text Splitting | RecursiveCharacterTextSplitter (1000 chars, 200 overlap) |

---

## Project Structure

```
chatbot/
├── backend/
│   ├── backend/
│   │   ├── main.py                    # FastAPI entry point
│   │   ├── base/                      # Foundation stuff
│   │   │   ├── app/server.py          # FastAPI + CORS setup
│   │   │   ├── config/settings.py     # All config in one spot
│   │   │   └── schemas/api_response.py
│   │   ├── pdf/                       # PDF upload & processing
│   │   │   ├── api/v1/pdf_routes.py
│   │   │   ├── schemas/pdf_schemas.py
│   │   │   └── services/
│   │   │       ├── pdf_service.py      # Reads & splits PDFs
│   │   │       └── cloudinary_service.py
│   │   ├── rag/services/              # The RAG engine
│   │   │   ├── embedding_service.py    # Text → vectors
│   │   │   ├── vector_service.py       # Qdrant Cloud operations
│   │   │   ├── llm_service.py          # Groq LLM calls
│   │   │   └── cache_service.py        # Valkey caching
│   │   ├── chat/                      # Text chat
│   │   │   ├── api/v1/chat_routes.py
│   │   │   ├── schemas/chat_schemas.py
│   │   │   └── services/chat_service.py
│   │   └── asr/                       # Voice
│   │       ├── api/v1/voice_routes.py
│   │       ├── schemas/voice_schemas.py
│   │       └── services/
│   │           ├── stt_service.py      # Speech → text
│   │           └── tts_service.py      # Text → speech
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── docker-compose.yml
├── frontend/
│   ├── app.py                         # Streamlit UI
│   ├── config.py                      # BACKEND_URL resolution
│   ├── api/client.py                  # Backend HTTP client
│   ├── pyproject.toml
│   └── .env.example
├── .env                               # API keys & config (git-ignored)
├── .env.example                       # Local env template
├── render.yaml                        # Render Blueprint (backend + frontend + cache)
└── ARCHITECTURE.md                    # More detailed architecture docs
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/v1/pdf/upload` | Upload a PDF file |
| POST | `/v1/chat/ask` | Ask a text question |
| POST | `/v1/voice/chat` | Ask with voice (audio file) |

---

## Config Values You Can Tweak

| Setting | Default | What it does |
|---------|---------|-------------|
| `CHUNK_SIZE` | 1000 | Characters per text chunk |
| `CHUNK_OVERLAP` | 200 | Overlap between chunks |
| `K_RETRIEVED_DOCS` | 4 | How many chunks to pull for context |
| `CACHE_SIMILARITY_THRESHOLD` | 0.92 | How similar questions must be for cache hit |
| `CACHE_TTL` | 3600 | Cache expiry in seconds (1 hour) |

---

## Why We Built It This Way

- **No OpenAI** — Groq for LLM + STT, fastembed for local embeddings (no API key needed)
- **Cache before search** — Checking Valkey first saves Qdrant queries and LLM calls
- **Strict cache threshold** — Better to miss than to return a wrong answer
- **Local embeddings** — fastembed runs on CPU, zero cost, no external dependency
- **Edge TTS instead of another paid API** — We use `edge-tts` (Microsoft Edge's free TTS engine) for speech output. No extra API key, no cost.
- **Chat Memory toggle** — Every PDF upload gets tagged with a session ID. A toggle in the sidebar lets you decide whether to search all PDFs or just the ones from the current session. Useful when you want to isolate unrelated documents.
- **Modular folders** — Each feature (PDF, chat, voice, RAG) has its own routes, schemas, and services
