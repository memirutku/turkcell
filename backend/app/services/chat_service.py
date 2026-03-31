"""ChatService: orchestrates Gemini LLM streaming with RAG context and conversation memory."""

import logging
from collections.abc import AsyncIterator

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import Settings
from app.prompts.system_prompt import SYSTEM_PROMPT
from app.services.memory_service import MemoryService
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

# Empty-context fallback message for when RAG returns 0 results
_NO_CONTEXT_FALLBACK = "Bu konuda bilgi kaynaklarinda ilgili bilgi bulunamadi."


class ChatService:
    """Orchestrates RAG-augmented chat with Gemini LLM streaming.

    Workflow per request:
    1. Retrieve relevant documents from Milvus via RAGService
    2. Load conversation history from Redis via MemoryService
    3. Construct messages with system prompt (incl. RAG context) + history + user message
    4. Stream tokens from Gemini via astream()
    5. Save the exchange to conversation history
    """

    def __init__(self, settings: Settings) -> None:
        self._llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=settings.gemini_api_key,
            temperature=0.3,
            max_output_tokens=2048,
        )
        self._rag = RAGService(settings)
        self._memory = MemoryService(redis_url=settings.redis_url)

    async def stream_response(
        self, message: str, session_id: str
    ) -> AsyncIterator[str]:
        """Stream LLM response tokens for a user message.

        Args:
            message: User's message in Turkish.
            session_id: Session ID for conversation memory.

        Yields:
            String tokens from the Gemini LLM response.
        """
        # 1. RAG retrieval
        rag_results = await self._rag.search(message, top_k=5)
        if rag_results:
            context = "\n\n".join(r["content"] for r in rag_results)
        else:
            context = _NO_CONTEXT_FALLBACK

        # 2. Load conversation history (last 20 messages = 10 turns)
        past_messages = self._memory.get_history(session_id)

        # 3. Build message list
        system_content = SYSTEM_PROMPT.format(context=context)
        messages = [
            SystemMessage(content=system_content),
            *past_messages[-20:],
            HumanMessage(content=message),
        ]

        # 4. Stream from Gemini
        full_response = ""
        async for chunk in self._llm.astream(messages):
            token = chunk.content
            if token:
                full_response += token
                yield token

        # 5. Save to conversation history
        self._memory.add_messages(session_id, message, full_response)
