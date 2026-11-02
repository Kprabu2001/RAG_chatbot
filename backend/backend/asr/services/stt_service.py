import os
import tempfile
from groq import Groq
from backend.base.config.settings import settings


class STTService:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)

    def speech_to_text(self, audio_bytes: bytes) -> str:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_path = tmp_file.name

        try:
            with open(tmp_path, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    file=(os.path.basename(tmp_path), audio_file.read()),
                    model="whisper-large-v3",
                    response_format="text"
                )
            return transcription
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
