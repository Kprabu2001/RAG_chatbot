import numpy as np
from fastembed import TextEmbedding


class EmbeddingService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
            cls._instance.dimension = 384
        return cls._instance

    def embed_query(self, text: str) -> np.ndarray:
        return list(self.model.embed(text))[0]

    def embed_documents(self, texts: list[str]) -> list[np.ndarray]:
        return list(self.model.embed(texts))
