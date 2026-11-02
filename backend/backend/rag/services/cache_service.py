import json
import logging
import numpy as np
from typing import Optional, Dict, Any
from valkey import Valkey
from backend.base.config.settings import settings
from backend.rag.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class SemanticCacheService:
    def __init__(self):
        self.client = self._build_client()
        self.embedder = EmbeddingService()
        self.threshold = settings.CACHE_SIMILARITY_THRESHOLD
        self.ttl = settings.CACHE_TTL

    @staticmethod
    def _build_client() -> Optional[Valkey]:
        try:
            if settings.VALKEY_URL:
                return Valkey.from_url(
                    settings.VALKEY_URL,
                    db=settings.VALKEY_DB,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )
            kwargs = {
                "host": settings.VALKEY_HOST,
                "port": settings.VALKEY_PORT,
                "db": settings.VALKEY_DB,
                "decode_responses": True,
                "socket_connect_timeout": 2,
                "socket_timeout": 2,
            }
            if settings.VALKEY_PASSWORD:
                kwargs["password"] = settings.VALKEY_PASSWORD
            if settings.VALKEY_SSL:
                kwargs["ssl"] = True
            return Valkey(**kwargs)
        except Exception:
            logger.exception("Failed to configure Valkey client; cache disabled")
            return None

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot_product / (norm_a * norm_b))

    def search(self, question: str) -> Optional[Dict[str, Any]]:
        if self.client is None:
            return None
        try:
            return self._search(question)
        except Exception:
            logger.warning("Semantic cache lookup failed; skipping cache", exc_info=True)
            return None

    def _search(self, question: str) -> Optional[Dict[str, Any]]:
        question_emb = self.embedder.embed_query(question)
        cache_keys = self.client.keys("cache:*")

        best_match = None
        best_score = 0.0

        for key in cache_keys:
            cached_data = self.client.get(key)
            if not cached_data:
                continue
            try:
                entry = json.loads(cached_data)
                cached_emb = np.array(entry["embedding"])
                score = self._cosine_similarity(question_emb, cached_emb)

                if score > best_score:
                    best_score = score
                    best_match = entry
            except (json.JSONDecodeError, KeyError):
                continue

        if best_score >= self.threshold and best_match:
            return {
                "answer": best_match["answer"],
                "similarity": best_score,
                "cached_question": best_match["question"]
            }
        return None

    def store(self, question: str, answer: str):
        if self.client is None:
            return
        try:
            question_emb = self.embedder.embed_query(question)
            cache_key = f"cache:{hash(question)}"

            entry = {
                "question": question,
                "answer": answer,
                "embedding": question_emb.tolist()
            }

            self.client.setex(cache_key, self.ttl, json.dumps(entry))
        except Exception:
            logger.warning("Semantic cache write failed; answer not cached", exc_info=True)

    def clear(self):
        if self.client is None:
            return
        try:
            cache_keys = self.client.keys("cache:*")
            if cache_keys:
                self.client.delete(*cache_keys)
        except Exception:
            logger.warning("Semantic cache clear failed", exc_info=True)
