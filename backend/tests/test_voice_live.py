"""Tests for Gemini Live API integration: tool dispatch, confirmation flow, service lifecycle."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.live_tools import (
    ACTION_TOOLS,
    SAFE_TOOLS,
    is_action_tool,
    get_live_tool_declarations,
    dispatch_tool,
    build_action_description,
)


# -- Tool classification tests --


class TestToolClassification:
    """Test safe vs action tool classification."""

    def test_action_tools(self):
        assert is_action_tool("activate_package") is True
        assert is_action_tool("change_tariff") is True

    def test_safe_tools(self):
        assert is_action_tool("search_knowledge_base") is False
        assert is_action_tool("lookup_customer_bill") is False
        assert is_action_tool("get_available_packages") is False
        assert is_action_tool("get_available_tariffs") is False

    def test_unknown_tool_is_not_action(self):
        assert is_action_tool("unknown_tool") is False

    def test_sets_are_disjoint(self):
        assert ACTION_TOOLS.isdisjoint(SAFE_TOOLS)


# -- FunctionDeclaration tests --


class TestFunctionDeclarations:
    """Test that tool declarations are well-formed."""

    def test_declaration_count(self):
        decls = get_live_tool_declarations()
        assert len(decls) == 6

    def test_all_tools_have_names(self):
        decls = get_live_tool_declarations()
        names = {d.name for d in decls}
        expected = {
            "search_knowledge_base",
            "lookup_customer_bill",
            "get_available_packages",
            "get_available_tariffs",
            "activate_package",
            "change_tariff",
        }
        assert names == expected

    def test_all_tools_have_descriptions(self):
        decls = get_live_tool_declarations()
        for d in decls:
            assert d.description, f"{d.name} missing description"
            assert len(d.description) > 10, f"{d.name} description too short"


# -- Tool dispatch tests --


class TestToolDispatch:
    """Test tool dispatch to MockBSS."""

    @pytest.fixture
    def mock_bss(self):
        bss = MagicMock()
        customer = MagicMock()
        customer.name = "Test Musteri"
        tariff = MagicMock()
        tariff.name = "Turkcell Gold"
        customer.tariff = tariff
        bss.get_customer.return_value = customer
        bss.get_customer_bills.return_value = []
        bss.get_customer_usage.return_value = None
        bss.get_packages.return_value = []
        bss.get_tariffs.return_value = []
        bss.activate_package = AsyncMock(return_value={"status": "success"})
        bss.change_tariff = AsyncMock(return_value={"status": "success"})
        return bss

    @pytest.mark.asyncio
    async def test_dispatch_lookup_customer_bill(self, mock_bss):
        result = await dispatch_tool(
            "lookup_customer_bill",
            {"customer_id": "cust-001"},
            mock_bss,
        )
        data = json.loads(result)
        assert "customer_name" in data
        mock_bss.get_customer.assert_called_once_with("cust-001")

    @pytest.mark.asyncio
    async def test_dispatch_lookup_customer_not_found(self, mock_bss):
        mock_bss.get_customer.return_value = None
        result = await dispatch_tool(
            "lookup_customer_bill",
            {"customer_id": "bad-id"},
            mock_bss,
        )
        data = json.loads(result)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_dispatch_get_available_packages(self, mock_bss):
        result = await dispatch_tool("get_available_packages", {}, mock_bss)
        data = json.loads(result)
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_dispatch_get_available_tariffs(self, mock_bss):
        result = await dispatch_tool("get_available_tariffs", {}, mock_bss)
        data = json.loads(result)
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_dispatch_activate_package(self, mock_bss):
        result = await dispatch_tool(
            "activate_package",
            {"customer_id": "cust-001", "package_id": "pkg-001"},
            mock_bss,
        )
        data = json.loads(result)
        assert data["status"] == "success"
        mock_bss.activate_package.assert_called_once_with("cust-001", "pkg-001")

    @pytest.mark.asyncio
    async def test_dispatch_change_tariff(self, mock_bss):
        result = await dispatch_tool(
            "change_tariff",
            {"customer_id": "cust-001", "new_tariff_id": "tariff-003"},
            mock_bss,
        )
        data = json.loads(result)
        assert data["status"] == "success"
        mock_bss.change_tariff.assert_called_once_with("cust-001", "tariff-003")

    @pytest.mark.asyncio
    async def test_dispatch_search_knowledge_base_no_rag(self, mock_bss):
        result = await dispatch_tool(
            "search_knowledge_base",
            {"query": "test"},
            mock_bss,
            rag_service=None,
        )
        data = json.loads(result)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_dispatch_search_knowledge_base_with_rag(self, mock_bss):
        rag = MagicMock()
        rag.search = AsyncMock(return_value=[
            {"content": "Turkcell tarife bilgisi", "metadata": {"source": "faq.pdf"}, "score": 0.95}
        ])
        result = await dispatch_tool(
            "search_knowledge_base",
            {"query": "tarife bilgisi"},
            mock_bss,
            rag_service=rag,
        )
        data = json.loads(result)
        assert "results" in data
        assert len(data["results"]) == 1
        rag.search.assert_called_once_with("tarife bilgisi", top_k=5)

    @pytest.mark.asyncio
    async def test_dispatch_unknown_tool(self, mock_bss):
        result = await dispatch_tool("nonexistent", {}, mock_bss)
        data = json.loads(result)
        assert "error" in data


# -- Action description tests --


class TestActionDescription:
    """Test human-readable action descriptions."""

    def test_activate_package_with_details(self):
        mock_bss = MagicMock()
        mock_bss.get_package.return_value = MagicMock(
            name="10GB Ek Paket",
            price_tl=59.90,
            duration_days=30,
        )
        desc = build_action_description(
            "activate_package",
            {"customer_id": "cust-001", "package_id": "pkg-001"},
            mock_bss,
        )
        assert "10GB Ek Paket" in desc
        assert "59.9" in desc

    def test_activate_package_without_details(self):
        mock_bss = MagicMock(spec=[])  # no get_package method
        desc = build_action_description(
            "activate_package",
            {"customer_id": "cust-001", "package_id": "pkg-001"},
            mock_bss,
        )
        assert "pkg-001" in desc

    def test_change_tariff_with_details(self):
        mock_bss = MagicMock()
        mock_bss.get_tariff.return_value = MagicMock(
            name="Turkcell Platinum",
            monthly_price_tl=299.90,
        )
        desc = build_action_description(
            "change_tariff",
            {"customer_id": "cust-001", "new_tariff_id": "tariff-003"},
            mock_bss,
        )
        assert "Turkcell Platinum" in desc

    def test_unknown_action(self):
        mock_bss = MagicMock()
        desc = build_action_description("unknown", {}, mock_bss)
        assert "unknown" in desc


# -- GeminiLiveService tests --


class TestGeminiLiveServiceInit:
    """Test GeminiLiveService construction."""

    def test_service_init(self):
        from app.services.gemini_live_service import GeminiLiveService

        settings = MagicMock()
        settings.gemini_api_key = "test-key"
        settings.gemini_live_model = "gemini-3.1-flash-live-preview"
        settings.gemini_live_voice = "Kore"

        mock_bss = MagicMock()
        billing_ctx = MagicMock()

        with patch("app.services.gemini_live_service.genai.Client"):
            service = GeminiLiveService(
                settings=settings,
                mock_bss=mock_bss,
                billing_context=billing_ctx,
            )
            assert service._model == "gemini-3.1-flash-live-preview"
            assert service._voice == "Kore"


class TestGeminiLiveSession:
    """Test GeminiLiveSession state tracking."""

    def test_session_state(self):
        from app.services.gemini_live_service import GeminiLiveSession

        session = GeminiLiveSession(
            session=MagicMock(),
            session_id="test-session",
            customer_id="cust-001",
        )
        assert not session.is_closed
        assert session.pending_tool_call is None
        assert session.user_transcript == ""
        assert session.model_transcript == ""

    def test_session_close_flag(self):
        from app.services.gemini_live_service import GeminiLiveSession

        session = GeminiLiveSession(
            session=MagicMock(),
            session_id="test-session",
            customer_id=None,
        )
        session._closed = True
        assert session.is_closed
