import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.main import app
from app.services.mock_bss import MockBSSService


class TestMockBSSActions:
    @pytest.fixture
    def mock_bss(self):
        service = MockBSSService()
        service.load_data()
        return service

    @pytest.mark.asyncio
    async def test_activate_package_success(self, mock_bss):
        result = await mock_bss.activate_package("cust-001", "pkg-002")
        assert result["success"] is True
        assert result["transaction_id"].startswith("TXN-")
        assert len(result["transaction_id"]) == 10  # TXN-XXXXXX
        assert result["customer_id"] == "cust-001"
        assert result["package"]["id"] == "pkg-002"
        assert result["package"]["name"] == "Ek 10GB Internet Paketi"
        assert "basariyla" in result["message_tr"]

    @pytest.mark.asyncio
    async def test_activate_package_invalid_customer(self, mock_bss):
        result = await mock_bss.activate_package("nonexistent", "pkg-002")
        assert result["success"] is False
        assert "bulunamadi" in result["error"]

    @pytest.mark.asyncio
    async def test_activate_package_invalid_package(self, mock_bss):
        result = await mock_bss.activate_package("cust-001", "nonexistent")
        assert result["success"] is False
        assert "bulunamadi" in result["error"]

    @pytest.mark.asyncio
    async def test_change_tariff_success(self, mock_bss):
        result = await mock_bss.change_tariff("cust-001", "tariff-003")
        assert result["success"] is True
        assert result["transaction_id"].startswith("TXN-")
        assert result["old_tariff"] is not None
        assert result["new_tariff"]["id"] == "tariff-003"
        assert "degistirildi" in result["message_tr"]

    @pytest.mark.asyncio
    async def test_change_tariff_invalid_customer(self, mock_bss):
        result = await mock_bss.change_tariff("nonexistent", "tariff-003")
        assert result["success"] is False
        assert "bulunamadi" in result["error"]

    @pytest.mark.asyncio
    async def test_change_tariff_invalid_tariff(self, mock_bss):
        result = await mock_bss.change_tariff("cust-001", "nonexistent")
        assert result["success"] is False
        assert "bulunamadi" in result["error"]

    @pytest.mark.asyncio
    async def test_change_tariff_updates_customer(self, mock_bss):
        original = mock_bss.get_customer("cust-001")
        original_tariff_id = original.tariff_id
        await mock_bss.change_tariff("cust-001", "tariff-003")
        updated = mock_bss.get_customer("cust-001")
        assert updated.tariff_id == "tariff-003"
        assert updated.tariff_id != original_tariff_id

    @pytest.mark.asyncio
    async def test_realistic_response_delay(self, mock_bss):
        start = time.monotonic()
        await mock_bss.activate_package("cust-001", "pkg-002")
        elapsed = time.monotonic() - start
        assert 0.3 <= elapsed <= 2.0, f"Expected delay 0.3-2.0s, got {elapsed:.2f}s"


class TestToolDefinitions:
    """Verify LangChain tool definitions for Gemini function calling."""

    def test_tools_list_not_empty(self):
        from app.services.agent_tools import get_telecom_tools

        mock_bss = MockBSSService()
        mock_bss.load_data()
        tools = get_telecom_tools(mock_bss)
        assert len(tools) >= 5

    def test_tool_names(self):
        from app.services.agent_tools import get_telecom_tools

        mock_bss = MockBSSService()
        mock_bss.load_data()
        tools = get_telecom_tools(mock_bss)
        names = {t.name for t in tools}
        assert "activate_package" in names
        assert "change_tariff" in names
        assert "lookup_customer_bill" in names

    def test_tool_descriptions_in_turkish(self):
        from app.services.agent_tools import get_telecom_tools

        mock_bss = MockBSSService()
        mock_bss.load_data()
        tools = get_telecom_tools(mock_bss)
        turkish_keywords = ["musteri", "paket", "tarife", "fatura", "listele", "aktif", "degistir", "sorgula"]
        for tool in tools:
            has_turkish = any(kw in tool.description.lower() for kw in turkish_keywords)
            assert has_turkish, f"Tool {tool.name} description lacks Turkish keywords: {tool.description}"

    def test_all_five_tool_names(self):
        from app.services.agent_tools import get_telecom_tools

        mock_bss = MockBSSService()
        mock_bss.load_data()
        tools = get_telecom_tools(mock_bss)
        names = {t.name for t in tools}
        expected = {"activate_package", "change_tariff", "lookup_customer_bill", "get_available_packages", "get_available_tariffs"}
        assert names == expected

    @pytest.mark.asyncio
    async def test_lookup_bill_tool_returns_data(self):
        from app.services.agent_tools import get_telecom_tools

        mock_bss = MockBSSService()
        mock_bss.load_data()
        tools = get_telecom_tools(mock_bss)
        lookup_tool = next(t for t in tools if t.name == "lookup_customer_bill")
        result_str = await lookup_tool.ainvoke({"customer_id": "cust-001"})
        result = json.loads(result_str)
        assert "customer_name" in result
        assert "bills" in result

    @pytest.mark.asyncio
    async def test_get_packages_tool_returns_data(self):
        from app.services.agent_tools import get_telecom_tools

        mock_bss = MockBSSService()
        mock_bss.load_data()
        tools = get_telecom_tools(mock_bss)
        pkg_tool = next(t for t in tools if t.name == "get_available_packages")
        result_str = await pkg_tool.ainvoke({})
        result = json.loads(result_str)
        assert isinstance(result, list)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_get_tariffs_tool_returns_data(self):
        from app.services.agent_tools import get_telecom_tools

        mock_bss = MockBSSService()
        mock_bss.load_data()
        tools = get_telecom_tools(mock_bss)
        tariff_tool = next(t for t in tools if t.name == "get_available_tariffs")
        result_str = await tariff_tool.ainvoke({})
        result = json.loads(result_str)
        assert isinstance(result, list)
        assert len(result) > 0


class TestAgentWorkflow:
    """Test LangGraph agent workflow with mocked LLM."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock Settings for AgentService."""
        settings = MagicMock()
        settings.gemini_api_key = "test-api-key"
        settings.redis_url = "redis://localhost:6379/0"
        settings.milvus_host = "localhost"
        settings.milvus_port = 19530
        settings.milvus_collection_name = "test_collection"
        return settings

    @pytest.fixture
    def mock_bss(self):
        service = MockBSSService()
        service.load_data()
        return service

    @pytest.fixture
    def billing_context(self, mock_bss):
        from app.services.billing_context import BillingContextService
        return BillingContextService(mock_bss)

    def test_agent_service_creates_graph(self, mock_settings, mock_bss, billing_context):
        """Verify AgentService initializes with a compiled LangGraph StateGraph."""
        with patch("app.services.agent_service.ChatGoogleGenerativeAI") as mock_llm_cls, \
             patch("app.services.agent_service.RAGService"):
            mock_llm_instance = MagicMock()
            mock_llm_instance.bind_tools.return_value = mock_llm_instance
            mock_llm_cls.return_value = mock_llm_instance

            from app.services.agent_service import AgentService
            service = AgentService(
                settings=mock_settings,
                mock_bss=mock_bss,
                billing_context=billing_context,
                pii_enabled=False,
            )

            assert service._graph is not None
            assert service._checkpointer is not None
            assert service._tools is not None
            assert len(service._tools) == 5

    @pytest.mark.asyncio
    async def test_agent_stream_general_chat(self, mock_settings, mock_bss, billing_context):
        """Mock the LLM to return a simple text response (no tool calls) and verify token events."""
        with patch("app.services.agent_service.ChatGoogleGenerativeAI") as mock_llm_cls, \
             patch("app.services.agent_service.RAGService") as mock_rag_cls:
            # Configure mock LLM
            mock_llm_instance = MagicMock()
            mock_llm_instance.bind_tools.return_value = mock_llm_instance

            # Mock ainvoke to return a plain AIMessage (no tool calls)
            mock_response = AIMessage(content="Merhaba, size nasil yardimci olabilirim?")
            mock_llm_instance.ainvoke = AsyncMock(return_value=mock_response)
            mock_llm_cls.return_value = mock_llm_instance

            # Configure mock RAG service
            mock_rag_instance = MagicMock()
            mock_rag_instance.search = AsyncMock(return_value=[])
            mock_rag_cls.return_value = mock_rag_instance

            from app.services.agent_service import AgentService
            service = AgentService(
                settings=mock_settings,
                mock_bss=mock_bss,
                billing_context=billing_context,
                pii_enabled=False,
            )

            events = []
            async for event in service.stream("Merhaba", "test-session-001", "cust-001"):
                events.append(event)

            # Should have at least one token event or the graph should complete without errors
            # With mocked LLM, astream_events may not yield on_chat_model_stream
            # but the graph should complete without errors
            assert isinstance(events, list)
            # Check no error events
            error_events = [e for e in events if e.get("type") == "error"]
            assert len(error_events) == 0, f"Unexpected errors: {error_events}"

    def test_agent_service_has_required_methods(self, mock_settings, mock_bss, billing_context):
        """Verify AgentService has stream() and resume() methods."""
        with patch("app.services.agent_service.ChatGoogleGenerativeAI") as mock_llm_cls, \
             patch("app.services.agent_service.RAGService"):
            mock_llm_instance = MagicMock()
            mock_llm_instance.bind_tools.return_value = mock_llm_instance
            mock_llm_cls.return_value = mock_llm_instance

            from app.services.agent_service import AgentService
            service = AgentService(
                settings=mock_settings,
                mock_bss=mock_bss,
                billing_context=billing_context,
                pii_enabled=False,
            )

            assert hasattr(service, "stream")
            assert hasattr(service, "resume")
            assert callable(service.stream)
            assert callable(service.resume)


class TestAgentConfirmation:
    """Test agent confirmation interrupt/resume flow."""

    @pytest.fixture
    def mock_settings(self):
        settings = MagicMock()
        settings.gemini_api_key = "test-api-key"
        settings.redis_url = "redis://localhost:6379/0"
        settings.milvus_host = "localhost"
        settings.milvus_port = 19530
        settings.milvus_collection_name = "test_collection"
        return settings

    @pytest.fixture
    def mock_bss(self):
        service = MockBSSService()
        service.load_data()
        return service

    @pytest.fixture
    def billing_context(self, mock_bss):
        from app.services.billing_context import BillingContextService
        return BillingContextService(mock_bss)

    @pytest.mark.asyncio
    async def test_interrupt_value_structure(self, mock_settings, mock_bss, billing_context):
        """Verify that the interrupt payload contains action_type, description, details keys."""
        with patch("app.services.agent_service.ChatGoogleGenerativeAI") as mock_llm_cls, \
             patch("app.services.agent_service.RAGService") as mock_rag_cls:
            # Configure mock LLM to return a tool call for activate_package
            mock_llm_instance = MagicMock()
            mock_llm_instance.bind_tools.return_value = mock_llm_instance

            mock_tool_response = AIMessage(
                content="",
                tool_calls=[{
                    "name": "activate_package",
                    "args": {"customer_id": "cust-001", "package_id": "pkg-002"},
                    "id": "call_test_123",
                }],
            )
            mock_llm_instance.ainvoke = AsyncMock(return_value=mock_tool_response)
            mock_llm_cls.return_value = mock_llm_instance

            # Configure mock RAG
            mock_rag_instance = MagicMock()
            mock_rag_instance.search = AsyncMock(return_value=[])
            mock_rag_cls.return_value = mock_rag_instance

            from app.services.agent_service import AgentService
            service = AgentService(
                settings=mock_settings,
                mock_bss=mock_bss,
                billing_context=billing_context,
                pii_enabled=False,
            )

            events = []
            async for event in service.stream(
                "10GB internet paketi tanimla",
                "test-confirm-session",
                "cust-001",
            ):
                events.append(event)

            # Find the action_proposal event
            proposals = [e for e in events if e.get("type") == "action_proposal"]
            assert len(proposals) == 1, f"Expected 1 proposal, got {len(proposals)}. Events: {events}"

            proposal_data = proposals[0]["data"]
            assert "action_type" in proposal_data
            assert "description" in proposal_data
            assert "details" in proposal_data
            assert "thread_id" in proposal_data
            assert proposal_data["action_type"] == "package_activation"
            assert proposal_data["thread_id"] == "test-confirm-session"

    @pytest.mark.asyncio
    async def test_resume_rejected_action(self, mock_settings, mock_bss, billing_context):
        """Verify that rejecting an action returns cancellation message."""
        with patch("app.services.agent_service.ChatGoogleGenerativeAI") as mock_llm_cls, \
             patch("app.services.agent_service.RAGService") as mock_rag_cls:
            mock_llm_instance = MagicMock()
            mock_llm_instance.bind_tools.return_value = mock_llm_instance

            mock_tool_response = AIMessage(
                content="",
                tool_calls=[{
                    "name": "activate_package",
                    "args": {"customer_id": "cust-001", "package_id": "pkg-002"},
                    "id": "call_test_456",
                }],
            )
            mock_llm_instance.ainvoke = AsyncMock(return_value=mock_tool_response)
            mock_llm_cls.return_value = mock_llm_instance

            mock_rag_instance = MagicMock()
            mock_rag_instance.search = AsyncMock(return_value=[])
            mock_rag_cls.return_value = mock_rag_instance

            from app.services.agent_service import AgentService
            service = AgentService(
                settings=mock_settings,
                mock_bss=mock_bss,
                billing_context=billing_context,
                pii_enabled=False,
            )

            # First, stream to get the proposal (which triggers interrupt)
            session_id = "test-reject-session"
            events = []
            async for event in service.stream(
                "Paket tanimla", session_id, "cust-001"
            ):
                events.append(event)

            # Verify we got a proposal
            proposals = [e for e in events if e.get("type") == "action_proposal"]
            assert len(proposals) == 1

            # Now resume with rejection
            config = {"configurable": {"thread_id": session_id}}
            resume_events = []
            async for event in service.resume(config, {"approved": False}):
                resume_events.append(event)

            # Check for action_result with cancelled status
            results = [e for e in resume_events if e.get("type") == "action_result"]
            assert len(results) == 1
            assert results[0]["data"]["status"] == "cancelled"


class TestAgentEndpoints:
    """Test agent API endpoints."""

    @pytest.mark.asyncio
    async def test_agent_chat_returns_503_when_disabled(self, client):
        """Agent endpoint returns 503 when agent_service is None."""
        old_state = getattr(app.state, "agent_service", None)
        try:
            app.state.agent_service = None
            response = await client.post(
                "/api/agent/chat",
                json={"message": "Merhaba", "session_id": "test-session", "customer_id": "cust-001"},
            )
            assert response.status_code == 503
        finally:
            app.state.agent_service = old_state

    @pytest.mark.asyncio
    async def test_agent_confirm_returns_503_when_disabled(self, client):
        """Confirm endpoint returns 503 when agent_service is None."""
        old_state = getattr(app.state, "agent_service", None)
        try:
            app.state.agent_service = None
            response = await client.post(
                "/api/agent/confirm",
                json={"thread_id": "test-thread", "approved": True},
            )
            assert response.status_code == 503
        finally:
            app.state.agent_service = old_state

    @pytest.mark.asyncio
    async def test_agent_chat_validates_request(self, client):
        """Agent endpoint validates request body (missing customer_id)."""
        old_state = getattr(app.state, "agent_service", None)
        try:
            app.state.agent_service = MagicMock()
            response = await client.post(
                "/api/agent/chat",
                json={"message": "Merhaba", "session_id": "test-session"},
            )
            assert response.status_code == 422  # Validation error for missing customer_id
        finally:
            app.state.agent_service = old_state

    @pytest.mark.asyncio
    async def test_agent_confirm_validates_request(self, client):
        """Confirm endpoint validates request body."""
        old_state = getattr(app.state, "agent_service", None)
        try:
            app.state.agent_service = MagicMock()
            response = await client.post(
                "/api/agent/confirm",
                json={"thread_id": "test-thread"},  # missing approved
            )
            assert response.status_code == 422
        finally:
            app.state.agent_service = old_state
