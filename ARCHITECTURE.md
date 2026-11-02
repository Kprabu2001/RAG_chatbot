# How This Project Works Under the Hood

## The Big Picture

When you upload a PDF and start asking questions - either by typing or speaking - here's what's actually happening behind the scenes.

```
You (Streamlit app on port 8501)
       │
       ▼
FastAPI backend on port 8000
       │
       ├── Valkey cache (remembers similar questions so we don't repeat work)
       ├── Qdrant Cloud (stores chunks of your PDF as vectors for searching)
       └── External services:
           ├── Groq (does the heavy lifting: LLM, speech-to-text)
           ├── fastembed (turns text into numbers locally, no API key needed)
           └── Cloudinary (stores the original PDF file in the cloud)
```

---

## What Happens When You Upload a PDF

```
You pick a PDF in the sidebar → it goes to POST /v1/pdf/upload
   │
   1. Backend saves the file somewhere temporary
   2. Uploads the original PDF to Cloudinary (so it's backed up online)
   3. Reads the PDF text using PyPDFLoader
   4. Splits that text into chunks of ~1000 characters each
      (it tries to break at paragraph breaks first, then sentences, then words)
   5. Converts each chunk into a 384-number vector (embedding) using fastembed
      - This runs on your CPU, no cost, no API key
    6. Stores everything in Qdrant Cloud: the chunk text, its vector, and metadata
      (which PDF it came from, page number, cloudinary link, session ID)
   7. Cleans up the temp file
   │
   └── You get back: filename, how many chunks were created, cloudinary URL
```

So after upload, your PDF is both stored as a file (Cloudinary) and searchable as vectors (Qdrant Cloud).

---

## What Happens When You Type a Question

```
You type: "What is the refund policy?"

POST /v1/chat/ask  →  ChatService.process_question()
   │
   ├── Step 1: Check the Valkey cache
   │     - Convert your question to a vector
   │     - Scan all cached questions, compare them using cosine similarity
   │     - If any cached question is >92% similar → return that answer instantly
   │       (this saves time and API costs)
   │
    └── Step 2 (cache miss): The real RAG pipeline
          │
          a. Convert your question to a vector
          b. Check the Chat Memory toggle:
             - ON (default) → search all PDFs ever uploaded
             - OFF → only search chunks tagged with the current session ID
          c. Search Qdrant Cloud for the 4 most similar chunks
          d. Glue those chunks together as "context"
          e. Send to Groq's GPT-OSS model with a prompt like:
             "Answer based ONLY on this context. If you can't find it, say so."
          f. Get back the answer, clean up any <think> blocks the model might spit out
          g. Save this question + answer in Valkey cache (expires in 1 hour)
         │
         └── Return: answer + list of source files + cached=false
```

---

## What Happens When You Speak a Question

```
You record audio → POST /v1/voice/chat (multipart, .wav file)
   │
   1. Speech-to-text via Groq Whisper
      - Saves audio to temp file
      - Sends to Whisper large-v3 → gets back transcribed text
      - Deletes temp file
   │
   2. Same RAG pipeline as text chat (cache check → memory toggle → Qdrant Cloud → LLM)
   │
   3. Text-to-speech via edge-tts
      - Takes the answer text
      - Converts to speech using Microsoft's edge-tts
      - Returns audio as base64 string
   │
   └── Frontend shows the answer text and auto-plays the audio
```

---

## Project Structure (Quick Tour)

```
chatbot/
├── backend/backend/
│   ├── main.py                     # FastAPI app, just wires up the routers
│   ├── base/
│   │   ├── app/server.py           # Our AppServer with CORS enabled
│   │   ├── config/settings.py      # One place for all config values
│   │   └── schemas/api_response.py # Generic response wrapper
│   ├── pdf/                        # PDF upload & processing
│   │   ├── api/v1/pdf_routes.py
│   │   ├── schemas/pdf_schemas.py
│   │   └── services/
│   │       ├── pdf_service.py      # Loading PDFs and splitting into chunks
│   │       └── cloudinary_service.py # Uploading/downloading from Cloudinary
│   ├── rag/services/               # The brains of the operation
│   │   ├── embedding_service.py    # Turns text into vectors (singleton, loads once)
│   │   ├── vector_service.py       # Talks to Qdrant Cloud
│   │   ├── llm_service.py          # Talks to Groq
│   │   └── cache_service.py        # Talks to Valkey
│   ├── chat/                       # Text chat
│   │   ├── api/v1/chat_routes.py
│   │   ├── schemas/chat_schemas.py
│   │   └── services/chat_service.py # Ties it all together
│   └── asr/                        # Voice (speech-to-text + text-to-speech)
│       ├── api/v1/voice_routes.py
│       ├── schemas/voice_schemas.py
│       └── services/
│           ├── stt_service.py
│           └── tts_service.py
├── frontend/                       # Streamlit UI
│   ├── app.py                      # Main page with tabs
│   ├── components/
│   │   ├── sidebar.py              # Upload form
│   │   ├── chat_tab.py             # Chat interface
│   │   └── voice_tab.py            # Voice recorder
│   ├── api/client.py               # HTTP calls to backend
│   └── utils/audio.py             # Auto-play helper
└── .env                            # Groq/Cloudinary/Valkey/Qdrant config
```

---

## What We're Using

| Part | What | Notes |
|------|------|-------|
| Frontend | Streamlit | Simple Python UI framework |
| Backend | FastAPI + Uvicorn | Standard Python web framework |
| LLM | Groq GPT-OSS 120B | Temperature 0.1 for factual answers |
| Embeddings | fastembed (BGE-small-en-v1.5) | 384 numbers per chunk, runs on CPU, free |
| Vector DB | Qdrant Cloud | Managed vector store (free tier), cosine distance |
| Cache | Valkey 8 | In-memory, TTL 1 hour, threshold 0.92 |
| Speech-to-Text | Groq Whisper large-v3 | |
| Text-to-Speech | edge-tts | Microsoft's engine, returns base64 |
| PDF Storage | Cloudinary | Free tier, stores raw PDFs |
| PDF Parsing | PyPDFLoader | Langchain community |
| Text Splitting | RecursiveCharacterTextSplitter | 1000 chars, 200 overlap |

---

## API Endpoints (Quick Reference)

| Method | Endpoint | What it does |
|--------|----------|-------------|
| GET | `/health` | Is the server alive? |
| POST | `/v1/pdf/upload` | Upload a PDF (multipart) |
| POST | `/v1/chat/ask` | Ask a text question (JSON) |
| POST | `/v1/voice/chat` | Ask with voice (audio file) |

---

## A Few Design Choices Worth Mentioning

- **No OpenAI** — We use Groq for LLM/STT and fastembed for embeddings. No API key needed for embeddings.
- **Cache first, search later** — Checking the semantic cache before hitting Qdrant Cloud saves money and time.
- **Strict cache threshold (0.92)** — We'd rather miss the cache than return a wrong answer.
- **Singleton embedding model** — The ONNX model loads once no matter how many parts of the code use it.
- **Chat Memory toggle** — A sidebar switch controls whether Qdrant Cloud filters by session ID. OFF means answers only from PDFs uploaded in the current session. ON means it searches across everything. Handy when you upload unrelated PDFs at different times and don't want them mixing.
- **Stripping <think> blocks** — Some reasoning models output internal thinking even when told not to. We clean that up before showing the user.
- **Modular structure** — PDF, chat, voice, and RAG each live in their own folder with their own routes, schemas, and services.
