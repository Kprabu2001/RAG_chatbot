import base64
import edge_tts
from backend.base.config.settings import settings


class TTSService:
    def __init__(self):
        self.voice = settings.EDGE_TTS_VOICE

    async def text_to_speech(self, text: str) -> str:
        communicate = edge_tts.Communicate(text, self.voice)
        audio_bytes = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_bytes += chunk["data"]
        if not audio_bytes:
            return ""
        return base64.b64encode(audio_bytes).decode("utf-8")
