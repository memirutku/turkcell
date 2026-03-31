"""Tests for Chat service, MemoryService, system prompt, and Pydantic schemas."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessageChunk, HumanMessage, AIMessage, SystemMessage


# -- ChatRequest schema tests --


class TestChatRequest:
    """Test ChatRequest Pydantic model validation."""

    def test_valid_request(self):
        from app.models.chat_schemas import ChatRequest

        req = ChatRequest(message="Fatura bilgilerim nedir?")
        assert req.message == "Fatura bilgilerim nedir?"
        assert req.session_id  # should have a default UUID

    def test_message_min_length(self):
        from app.models.chat_schemas import ChatRequest

        with pytest.raises(Exception):  # ValidationError
            ChatRequest(message="")

    def test_message_max_length(self):
        from app.models.chat_schemas import ChatRequest

        with pytest.raises(Exception):  # ValidationError
            ChatRequest(message="a" * 2001)

    def test_session_id_default_factory(self):
        from app.models.chat_schemas import ChatRequest

        req1 = ChatRequest(message="test")
        req2 = ChatRequest(message="test")
        # Each should get a unique uuid
        assert req1.session_id != req2.session_id
        # Should be valid UUID format (36 chars with dashes)
        assert len(req1.session_id) == 36

    def test_custom_session_id(self):
        from app.models.chat_schemas import ChatRequest

        req = ChatRequest(message="test", session_id="my-session-123")
        assert req.session_id == "my-session-123"


# -- System Prompt tests --


class TestSystemPrompt:
    """Test that the system prompt contains required elements."""

    def test_contains_context_placeholder(self):
        from app.prompts.system_prompt import SYSTEM_PROMPT

        assert "{context}" in SYSTEM_PROMPT

    def test_contains_turkcell_brand(self):
        from app.prompts.system_prompt import SYSTEM_PROMPT

        assert "Turkcell" in SYSTEM_PROMPT

    def test_contains_grounding_rule(self):
        from app.prompts.system_prompt import SYSTEM_PROMPT

        assert "SADECE" in SYSTEM_PROMPT

    def test_contains_anti_hallucination(self):
        from app.prompts.system_prompt import SYSTEM_PROMPT

        assert "ASLA" in SYSTEM_PROMPT

    def test_contains_empathy_instructions(self):
        from app.prompts.system_prompt import SYSTEM_PROMPT

        assert "Sizi anliyorum" in SYSTEM_PROMPT

    def test_contains_pii_protection(self):
        from app.prompts.system_prompt import SYSTEM_PROMPT

        assert "TC Kimlik" in SYSTEM_PROMPT

    def test_contains_fallback_directive(self):
        from app.prompts.system_prompt import SYSTEM_PROMPT

        assert "musteri hizmetleri" in SYSTEM_PROMPT

    def test_format_with_context(self):
        from app.prompts.system_prompt import SYSTEM_PROMPT

        context = "Platinum 20GB tarife ayda 299 TL."
        formatted = SYSTEM_PROMPT.format(context=context)
        assert context in formatted
        assert "{context}" not in formatted


# -- MemoryService tests --


class TestMemoryService:
    """Test MemoryService with mocked Redis."""

    def test_get_history_returns_messages(self):
        from app.services.memory_service import MemoryService

        service = MemoryService(redis_url="redis://localhost:6379/0")

        with patch(
            "app.services.memory_service.RedisChatMessageHistory"
        ) as MockHistory:
            mock_instance = MagicMock()
            mock_instance.messages = [
                HumanMessage(content="Merhaba"),
                AIMessage(content="Size nasil yardimci olabilirim?"),
            ]
            MockHistory.return_value = mock_instance

            history = service.get_history("test-session")
            assert len(history) == 2
            assert isinstance(history[0], HumanMessage)
            assert isinstance(history[1], AIMessage)

    def test_add_messages_stores_in_redis(self):
        from app.services.memory_service import MemoryService

        service = MemoryService(redis_url="redis://localhost:6379/0")

        with patch(
            "app.services.memory_service.RedisChatMessageHistory"
        ) as MockHistory:
            mock_instance = MagicMock()
            MockHistory.return_value = mock_instance

            service.add_messages(
                "test-session", "Fatura sorgula", "Faturaniz 150 TL."
            )
            mock_instance.add_user_message.assert_called_once_with(
                "Fatura sorgula"
            )
            mock_instance.add_ai_message.assert_called_once_with(
                "Faturaniz 150 TL."
            )


# -- ChatService tests --


class TestChatService:
    """Test ChatService orchestration with mocked dependencies."""

    def _make_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.gemini_api_key = "test-api-key"
        settings.redis_url = "redis://localhost:6379/0"
        settings.milvus_host = "localhost"
        settings.milvus_port = 19530
        settings.milvus_collection_name = "test_collection"
        return settings

    @patch("app.services.chat_service.MemoryService")
    @patch("app.services.chat_service.RAGService")
    @patch("app.services.chat_service.ChatGoogleGenerativeAI")
    def test_init_creates_llm(self, MockLLM, MockRAG, MockMemory):
        from app.services.chat_service import ChatService

        settings = self._make_settings()
        service = ChatService(settings, pii_enabled=False)

        MockLLM.assert_called_once()
        call_kwargs = MockLLM.call_args
        assert call_kwargs.kwargs["model"] == "gemini-2.0-flash"
        assert call_kwargs.kwargs["temperature"] == 0.3

    @patch("app.services.chat_service.MemoryService")
    @patch("app.services.chat_service.RAGService")
    @patch("app.services.chat_service.ChatGoogleGenerativeAI")
    async def test_stream_response_calls_rag_search(
        self, MockLLM, MockRAG, MockMemory
    ):
        from app.services.chat_service import ChatService

        settings = self._make_settings()

        # Setup mocks
        mock_rag = AsyncMock()
        mock_rag.search = AsyncMock(
            return_value=[{"content": "Test content", "metadata": {}, "score": 0.9}]
        )
        MockRAG.return_value = mock_rag

        mock_memory = MagicMock()
        mock_memory.get_history = MagicMock(return_value=[])
        mock_memory.add_messages = MagicMock()
        MockMemory.return_value = mock_memory

        mock_llm = AsyncMock()
        mock_chunk = MagicMock(spec=AIMessageChunk)
        mock_chunk.content = "Merhaba"

        async def mock_astream(*args, **kwargs):
            yield mock_chunk

        mock_llm.astream = mock_astream
        MockLLM.return_value = mock_llm

        service = ChatService(settings, pii_enabled=False)
        tokens = []
        async for token in service.stream_response("test query", "session-1"):
            tokens.append(token)

        mock_rag.search.assert_called_once_with("test query", top_k=5)

    @patch("app.services.chat_service.MemoryService")
    @patch("app.services.chat_service.RAGService")
    @patch("app.services.chat_service.ChatGoogleGenerativeAI")
    async def test_stream_response_calls_memory_get_history(
        self, MockLLM, MockRAG, MockMemory
    ):
        from app.services.chat_service import ChatService

        settings = self._make_settings()

        mock_rag = AsyncMock()
        mock_rag.search = AsyncMock(return_value=[])
        MockRAG.return_value = mock_rag

        mock_memory = MagicMock()
        mock_memory.get_history = MagicMock(return_value=[])
        mock_memory.add_messages = MagicMock()
        MockMemory.return_value = mock_memory

        mock_llm = AsyncMock()
        mock_chunk = MagicMock(spec=AIMessageChunk)
        mock_chunk.content = "Response"

        async def mock_astream(*args, **kwargs):
            yield mock_chunk

        mock_llm.astream = mock_astream
        MockLLM.return_value = mock_llm

        service = ChatService(settings, pii_enabled=False)
        async for _ in service.stream_response("test", "session-1"):
            pass

        mock_memory.get_history.assert_called_once_with("session-1")

    @patch("app.services.chat_service.MemoryService")
    @patch("app.services.chat_service.RAGService")
    @patch("app.services.chat_service.ChatGoogleGenerativeAI")
    async def test_stream_response_calls_astream_with_correct_messages(
        self, MockLLM, MockRAG, MockMemory
    ):
        from app.services.chat_service import ChatService

        settings = self._make_settings()

        mock_rag = AsyncMock()
        mock_rag.search = AsyncMock(
            return_value=[{"content": "Tarife bilgisi", "metadata": {}, "score": 0.8}]
        )
        MockRAG.return_value = mock_rag

        mock_memory = MagicMock()
        mock_memory.get_history = MagicMock(
            return_value=[
                HumanMessage(content="Onceki soru"),
                AIMessage(content="Onceki cevap"),
            ]
        )
        mock_memory.add_messages = MagicMock()
        MockMemory.return_value = mock_memory

        captured_messages = []

        async def mock_astream(messages):
            captured_messages.extend(messages)
            chunk = MagicMock(spec=AIMessageChunk)
            chunk.content = "Yanit"
            yield chunk

        mock_llm = MagicMock()
        mock_llm.astream = mock_astream
        MockLLM.return_value = mock_llm

        service = ChatService(settings, pii_enabled=False)
        async for _ in service.stream_response("Yeni soru", "session-1"):
            pass

        # Should have: SystemMessage, past history, HumanMessage
        assert len(captured_messages) == 4  # System + 2 history + Human
        assert isinstance(captured_messages[0], SystemMessage)
        assert isinstance(captured_messages[1], HumanMessage)
        assert isinstance(captured_messages[2], AIMessage)
        assert isinstance(captured_messages[3], HumanMessage)
        assert captured_messages[3].content == "Yeni soru"

    @patch("app.services.chat_service.MemoryService")
    @patch("app.services.chat_service.RAGService")
    @patch("app.services.chat_service.ChatGoogleGenerativeAI")
    async def test_stream_response_yields_tokens(
        self, MockLLM, MockRAG, MockMemory
    ):
        from app.services.chat_service import ChatService

        settings = self._make_settings()

        mock_rag = AsyncMock()
        mock_rag.search = AsyncMock(return_value=[])
        MockRAG.return_value = mock_rag

        mock_memory = MagicMock()
        mock_memory.get_history = MagicMock(return_value=[])
        mock_memory.add_messages = MagicMock()
        MockMemory.return_value = mock_memory

        async def mock_astream(messages):
            for text in ["Merhaba", " ", "nasilsiniz"]:
                chunk = MagicMock(spec=AIMessageChunk)
                chunk.content = text
                yield chunk

        mock_llm = MagicMock()
        mock_llm.astream = mock_astream
        MockLLM.return_value = mock_llm

        service = ChatService(settings, pii_enabled=False)
        tokens = []
        async for token in service.stream_response("test", "session-1"):
            tokens.append(token)

        assert tokens == ["Merhaba", " ", "nasilsiniz"]

    @patch("app.services.chat_service.MemoryService")
    @patch("app.services.chat_service.RAGService")
    @patch("app.services.chat_service.ChatGoogleGenerativeAI")
    async def test_stream_response_saves_messages_after_streaming(
        self, MockLLM, MockRAG, MockMemory
    ):
        from app.services.chat_service import ChatService

        settings = self._make_settings()

        mock_rag = AsyncMock()
        mock_rag.search = AsyncMock(return_value=[])
        MockRAG.return_value = mock_rag

        mock_memory = MagicMock()
        mock_memory.get_history = MagicMock(return_value=[])
        mock_memory.add_messages = MagicMock()
        MockMemory.return_value = mock_memory

        async def mock_astream(messages):
            for text in ["Hello", " world"]:
                chunk = MagicMock(spec=AIMessageChunk)
                chunk.content = text
                yield chunk

        mock_llm = MagicMock()
        mock_llm.astream = mock_astream
        MockLLM.return_value = mock_llm

        service = ChatService(settings, pii_enabled=False)
        async for _ in service.stream_response("user msg", "session-1"):
            pass

        mock_memory.add_messages.assert_called_once_with(
            "session-1", "user msg", "Hello world"
        )

    @patch("app.services.chat_service.MemoryService")
    @patch("app.services.chat_service.RAGService")
    @patch("app.services.chat_service.ChatGoogleGenerativeAI")
    async def test_stream_response_includes_rag_context_in_system_message(
        self, MockLLM, MockRAG, MockMemory
    ):
        from app.services.chat_service import ChatService

        settings = self._make_settings()

        mock_rag = AsyncMock()
        mock_rag.search = AsyncMock(
            return_value=[
                {"content": "Platinum 20GB ayda 299 TL", "metadata": {}, "score": 0.9}
            ]
        )
        MockRAG.return_value = mock_rag

        mock_memory = MagicMock()
        mock_memory.get_history = MagicMock(return_value=[])
        mock_memory.add_messages = MagicMock()
        MockMemory.return_value = mock_memory

        captured_messages = []

        async def mock_astream(messages):
            captured_messages.extend(messages)
            chunk = MagicMock(spec=AIMessageChunk)
            chunk.content = "Ok"
            yield chunk

        mock_llm = MagicMock()
        mock_llm.astream = mock_astream
        MockLLM.return_value = mock_llm

        service = ChatService(settings, pii_enabled=False)
        async for _ in service.stream_response("tarife sorgula", "session-1"):
            pass

        system_msg = captured_messages[0]
        assert isinstance(system_msg, SystemMessage)
        assert "Platinum 20GB ayda 299 TL" in system_msg.content

    @patch("app.services.chat_service.MemoryService")
    @patch("app.services.chat_service.RAGService")
    @patch("app.services.chat_service.ChatGoogleGenerativeAI")
    async def test_stream_response_empty_rag_results_fallback(
        self, MockLLM, MockRAG, MockMemory
    ):
        from app.services.chat_service import ChatService

        settings = self._make_settings()

        mock_rag = AsyncMock()
        mock_rag.search = AsyncMock(return_value=[])
        MockRAG.return_value = mock_rag

        mock_memory = MagicMock()
        mock_memory.get_history = MagicMock(return_value=[])
        mock_memory.add_messages = MagicMock()
        MockMemory.return_value = mock_memory

        captured_messages = []

        async def mock_astream(messages):
            captured_messages.extend(messages)
            chunk = MagicMock(spec=AIMessageChunk)
            chunk.content = "Ok"
            yield chunk

        mock_llm = MagicMock()
        mock_llm.astream = mock_astream
        MockLLM.return_value = mock_llm

        service = ChatService(settings, pii_enabled=False)
        async for _ in service.stream_response("bilinmeyen konu", "session-1"):
            pass

        system_msg = captured_messages[0]
        assert isinstance(system_msg, SystemMessage)
        assert "bilgi bulunamadi" in system_msg.content.lower() or \
               "bilgi kaynaklarinda" in system_msg.content.lower()


# -- Endpoint (integration) tests --


class TestChatEndpoint:
    """Test POST /api/chat SSE streaming endpoint."""

    async def test_chat_endpoint_returns_sse(self, client, mock_chat_service):
        from app.main import app

        original = getattr(app.state, "chat_service", None)
        try:
            app.state.chat_service = mock_chat_service
            response = await client.post(
                "/api/chat",
                json={"message": "Merhaba", "session_id": "test-session"},
            )
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")
        finally:
            app.state.chat_service = original

    async def test_chat_endpoint_503_when_no_service(self, client):
        from app.main import app

        original = getattr(app.state, "chat_service", None)
        try:
            app.state.chat_service = None
            response = await client.post(
                "/api/chat",
                json={"message": "Merhaba", "session_id": "test-session"},
            )
            assert response.status_code == 503
            assert "Chat servisi kullanilamiyor" in response.json()["detail"]
        finally:
            app.state.chat_service = original

    async def test_chat_endpoint_validates_empty_message(self, client, mock_chat_service):
        from app.main import app

        original = getattr(app.state, "chat_service", None)
        try:
            app.state.chat_service = mock_chat_service
            response = await client.post(
                "/api/chat",
                json={"message": "", "session_id": "test-session"},
            )
            assert response.status_code == 422
        finally:
            app.state.chat_service = original

    async def test_chat_endpoint_sse_format(self, client, mock_chat_service):
        from app.main import app

        original = getattr(app.state, "chat_service", None)
        try:
            app.state.chat_service = mock_chat_service
            response = await client.post(
                "/api/chat",
                json={"message": "Tarife bilgisi", "session_id": "test-session"},
            )
            assert response.status_code == 200
            body = response.text
            assert "event: token" in body
            assert "event: done" in body
        finally:
            app.state.chat_service = original

    async def test_chat_endpoint_error_event_on_failure(self, client):
        from app.main import app

        # Create a chat service that raises an error during streaming
        error_service = MagicMock()

        async def error_stream(*args, **kwargs):
            raise RuntimeError("Test error")
            yield  # noqa: E305 - make it an async generator

        error_service.stream_response = error_stream

        original = getattr(app.state, "chat_service", None)
        try:
            app.state.chat_service = error_service
            response = await client.post(
                "/api/chat",
                json={"message": "test", "session_id": "test-session"},
            )
            assert response.status_code == 200
            body = response.text
            assert "event: error" in body
            assert "Bir hata olustu" in body
        finally:
            app.state.chat_service = original
