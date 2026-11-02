from fastapi import APIRouter, UploadFile, File, Form
from backend.asr.schemas.voice_schemas import VoiceChatResponse
from backend.asr.services.stt_service import STTService
from backend.asr.services.tts_service import TTSService
from backend.rag.services.vector_service import VectorService
from backend.rag.services.cache_service import SemanticCacheService
from backend.rag.services.llm_service import LLMService

router = APIRouter(prefix="/v1/voice", tags=["Voice"])

stt_service = STTService()
tts_service = TTSService()
vector_service = VectorService()
cache_service = SemanticCacheService()
llm_service = LLMService()


@router.post("/chat", response_model=VoiceChatResponse)
async def voice_chat(
    file: UploadFile = File(...),
    session_id: str = Form("default"),
    memory_enabled: str = Form("true"),
):
    memory_on = memory_enabled.lower() == "true"
    audio_bytes = await file.read()

    question = stt_service.speech_to_text(audio_bytes)

    cached = cache_service.search(question)
    if cached:
        audio_base64 = await tts_service.text_to_speech(cached["answer"])
        return VoiceChatResponse(
            question=question,
            answer=cached["answer"],
            audio_base64=audio_base64,
            cached=True
        )

    context, docs = vector_service.get_context(question, session_id=session_id, memory_enabled=memory_on)
    if not context.strip():
        text_response = "No documents uploaded yet. Please upload a PDF first."
        audio_base64 = await tts_service.text_to_speech(text_response)
        return VoiceChatResponse(question=question, answer=text_response, audio_base64=audio_base64)

    answer = llm_service.generate_answer(question, context)

    cache_service.store(question, answer)

    audio_base64 = await tts_service.text_to_speech(answer)

    return VoiceChatResponse(question=question, answer=answer, audio_base64=audio_base64, cached=False)
