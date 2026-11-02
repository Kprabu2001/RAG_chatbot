from typing import List, Tuple
from backend.rag.services.vector_service import VectorService
from backend.rag.services.cache_service import SemanticCacheService
from backend.rag.services.llm_service import LLMService


class ChatService:
    def __init__(self):
        self.vector_service = VectorService()
        self.cache_service = SemanticCacheService()
        self.llm_service = LLMService()

    def process_question(self, question: str, session_id: str = "default", memory_enabled: bool = True) -> Tuple[str, List[str], bool]:
        cached = self.cache_service.search(question)
        if cached:
            return cached["answer"], [], True

        context, docs = self.vector_service.get_context(question, session_id=session_id, memory_enabled=memory_enabled)
        if not context.strip():
            return "No documents uploaded yet. Please upload a PDF first.", [], False

        answer = self.llm_service.generate_answer(question, context)

        self.cache_service.store(question, answer)

        sources = list(set(
            doc.metadata.get("source", "unknown") for doc in docs
        ))

        return answer, sources, False
