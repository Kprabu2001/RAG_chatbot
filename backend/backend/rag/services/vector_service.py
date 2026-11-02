import logging
import os
import uuid
from typing import List, Tuple
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)
from langchain_core.documents import Document
from backend.base.config.settings import settings
from backend.pdf.services.pdf_service import PDFService
from backend.rag.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class VectorService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.embedder = EmbeddingService()
        self.client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
        )
        self.collection = settings.QDRANT_COLLECTION
        self.pdf_service = PDFService(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )
        self._collection_ready = False
        try:
            self._ensure_collection()
        except Exception:
            # Retry lazily on first use so startup does not hard-fail if Qdrant is briefly unavailable.
            logger.exception("Qdrant collection setup failed; will retry on first use")

    def _ensure_collection(self):
        if self._collection_ready:
            return
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(
                    size=self.embedder.dimension,
                    distance=Distance.COSINE
                )
            )
            try:
                self.client.create_payload_index(
                    collection_name=self.collection,
                    field_name="session_id",
                    field_schema=PayloadSchemaType.KEYWORD
                )
            except Exception:
                pass
        self._collection_ready = True

    def ingest_pdf(self, file_path: str, cloudinary_url: str = "", session_id: str = "default") -> Tuple[str, int]:
        self._ensure_collection()
        chunks = self.pdf_service.process_pdf(file_path)
        if not chunks:
            return os.path.basename(file_path), 0

        filename = os.path.basename(file_path)
        texts = [chunk.page_content for chunk in chunks]
        embeddings = self.embedder.embed_documents(texts)

        points = []
        for index, (text, embedding, chunk) in enumerate(zip(texts, embeddings, chunks)):
            payload = dict(chunk.metadata or {})
            payload["text"] = text
            payload["cloudinary_url"] = cloudinary_url
            payload["session_id"] = session_id
            payload.setdefault("source", filename)

            point_id = str(uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"{session_id}:{filename}:{index}:{text}"
            ))
            points.append(PointStruct(
                id=point_id,
                vector=embedding.tolist(),
                payload=payload
            ))

        self.client.upsert(
            collection_name=self.collection,
            points=points,
            wait=True
        )

        return filename, len(chunks)

    def search_similar(self, question: str, k: int = None, session_id: str = None, memory_enabled: bool = True) -> List[Document]:
        self._ensure_collection()
        if k is None:
            k = settings.K_RETRIEVED_DOCS

        question_emb = self.embedder.embed_query(question).tolist()

        query_filter = None
        if not memory_enabled and session_id:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="session_id",
                        match=MatchValue(value=session_id)
                    )
                ]
            )

        results = self.client.query_points(
            collection_name=self.collection,
            query=question_emb,
            query_filter=query_filter,
            limit=k,
            with_payload=True
        ).points

        docs = []
        for point in results:
            payload = point.payload or {}
            text = payload.get("text", "")
            metadata = {key: value for key, value in payload.items() if key != "text"}
            docs.append(Document(page_content=text, metadata=metadata))

        return docs

    def get_context(self, question: str, session_id: str = None, memory_enabled: bool = True) -> Tuple[str, List[Document]]:
        docs = self.search_similar(question, session_id=session_id, memory_enabled=memory_enabled)
        context = "\n\n".join([doc.page_content for doc in docs])
        return context, docs

    def reset_collection(self):
        self.client.delete_collection(self.collection)
        self._collection_ready = False
        self._ensure_collection()
