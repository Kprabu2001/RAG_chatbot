from pydantic import BaseModel
from typing import List


class ChatRequest(BaseModel):
    question: str
    session_id: str = "default"
    memory_enabled: bool = True


class ChatResponse(BaseModel):
    answer: str
    sources: List[str] = []
    cached: bool = False
