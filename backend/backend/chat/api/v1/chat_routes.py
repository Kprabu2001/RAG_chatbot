from fastapi import APIRouter, HTTPException
from backend.chat.schemas.chat_schemas import ChatRequest, ChatResponse
from backend.chat.services.chat_service import ChatService

router = APIRouter(prefix="/v1/chat", tags=["Chat"])
chat_service = ChatService()


@router.post("/ask", response_model=ChatResponse)
async def ask_question(request: ChatRequest):
    if not request.question.strip():
        raise HTTPException(400, "Question cannot be empty")

    answer, sources, cached = chat_service.process_question(request.question, request.session_id, request.memory_enabled)

    return ChatResponse(answer=answer, sources=sources, cached=cached)
