from pydantic import BaseModel


class VoiceChatResponse(BaseModel):
    question: str
    answer: str
    audio_base64: str
    cached: bool = False
