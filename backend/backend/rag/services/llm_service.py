import re
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from backend.base.config.settings import settings

RAG_PROMPT = """You are a helpful PDF assistant. Answer the question based ONLY on the provided context.
If the context doesn't contain the answer, say "I couldn't find that information in the uploaded documents."

Context:
{context}

Question: {question}

Answer concisely and accurately:"""

# Some reasoning models can still emit a <think>...</think> block. Strip it
# defensively so it never reaches the user, regardless of model/provider behavior.
THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


class LLMService:
    def __init__(self):
        self.llm = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model=settings.GROQ_MODEL,
            temperature=0.1,
            max_tokens=2048,
            # GPT-OSS supports only low/medium/high ("none" is Qwen-only) and
            # does not support the reasoning_format parameter.
            reasoning_effort="low"
        )
        self.prompt = ChatPromptTemplate.from_template(RAG_PROMPT)

    def generate_answer(self, question: str, context: str) -> str:
        chain = self.prompt | self.llm
        response = chain.invoke({
            "question": question,
            "context": context
        })
        return self._strip_thinking(response.content)

    @staticmethod
    def _strip_thinking(text: str) -> str:
        cleaned = THINK_BLOCK_RE.sub("", text)
        return cleaned.strip()