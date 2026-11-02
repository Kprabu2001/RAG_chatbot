import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    CLOUDINARY_CLOUD_NAME: str = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY: str = os.getenv("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET: str = os.getenv("CLOUDINARY_API_SECRET", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    EDGE_TTS_VOICE: str = "en-IN-NeerjaNeural"

    QDRANT_URL: str = os.getenv("QDRANT_URL", "")
    QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")
    QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "pdf_docs")

    VALKEY_URL: str = os.getenv("VALKEY_URL", "")
    VALKEY_HOST: str = os.getenv("VALKEY_HOST", "localhost")
    VALKEY_PORT: int = int(os.getenv("VALKEY_PORT", "6379"))
    VALKEY_DB: int = int(os.getenv("VALKEY_DB", "0"))
    VALKEY_PASSWORD: str = os.getenv("VALKEY_PASSWORD", "")
    VALKEY_SSL: bool = os.getenv("VALKEY_SSL", "false").lower() in ("1", "true", "yes")
    CACHE_TTL: int = 3600
    CACHE_SIMILARITY_THRESHOLD: float = 0.92

    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    K_RETRIEVED_DOCS: int = 4

    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")




settings = Settings()
