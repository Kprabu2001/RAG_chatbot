from backend.base.app.server import AppServer
from backend.pdf.api.v1.pdf_routes import router as pdf_router
from backend.chat.api.v1.chat_routes import router as chat_router
from backend.asr.api.v1.voice_routes import router as voice_router

app = AppServer(title="PDF Chat Assistant API", version="1.0.0")

app.include_router(pdf_router)
app.include_router(chat_router)
app.include_router(voice_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
