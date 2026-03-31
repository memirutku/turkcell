"""Tests for BillingContextService, billing prompts, and billing-related schemas."""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import SystemMessage

from app.main import app
from app.services.mock_bss import MockBSSService


# -- BillingContextService tests --


class TestBillingContext:
    """Test BillingContextService formatting and PII handling."""

    @pytest.fixture
    def billing_service(self):
        """Create BillingContextService using loaded mock data."""
        from app.services.billing_context import BillingContextService

        return BillingContextService(app.state.mock_bss)

    def test_get_customer_context_returns_formatted_text(self, billing_service):
        """get_customer_context returns string with customer name, tariff, data."""
        result = billing_service.get_customer_context("cust-001")
        assert result is not None
        assert "Ahmet" in result
        assert "Platinum" in result
        assert "20GB" in result or "20 GB" in result

    def test_get_customer_context_unknown_customer(self, billing_service):
        """get_customer_context returns None for nonexistent customer."""
        result = billing_service.get_customer_context("nonexistent")
        assert result is None

    def test_format_bills_includes_line_items(self, billing_service):
        """Output contains bill period and each line item description."""
        result = billing_service.get_customer_context("cust-001")
        assert result is not None
        assert "2026-01" in result or "2026-02" in result or "2026-03" in result
        # Check that line item descriptions appear
        assert "Platinum Esneyebilen 20GB Tarife Ucreti" in result

    def test_line_item_categories_turkish(self, billing_service):
        """Output maps 'base' -> 'Ana Ucret', 'overage' -> 'Asim Ucreti', 'tax' -> 'Vergi'."""
        result = billing_service.get_customer_context("cust-001")
        assert result is not None
        assert "Ana Ucret" in result
        assert "Vergi" in result
        # cust-001 has overage in 2026-02
        assert "Asim Ucreti" in result

    def test_currency_formatting(self, billing_service):
        """Amounts formatted with comma decimal separator and TL suffix."""
        result = billing_service.get_customer_context("cust-001")
        assert result is not None
        assert "299,00 TL" in result

    def test_pii_redaction(self, billing_service):
        """Output does NOT contain tc_kimlik_no, phone shows only last 4 digits."""
        result = billing_service.get_customer_context("cust-001")
        assert result is not None
        # tc_kimlik_no should NOT appear
        assert "12345678901" not in result
        # Phone should show only last 4 digits
        assert "***4567" in result
        # Full phone number should NOT appear
        assert "05321234567" not in result

    def test_usage_section_present(self, billing_service):
        """When usage data exists, output contains data/voice/SMS usage info."""
        result = billing_service.get_customer_context("cust-001")
        assert result is not None
        # cust-001 has usage data: 18.5/20 GB, 1250/2000 min, 45/1000 SMS
        assert "18" in result  # data_used_gb
        assert "20" in result  # data_limit_gb
        assert "1250" in result or "1.250" in result  # voice_used_minutes

    def test_no_bills_message(self, billing_service):
        """When customer has no bills, output contains appropriate message."""
        # We need a customer with no bills. Let's test with mock directly.
        from app.services.billing_context import BillingContextService
        from unittest.mock import MagicMock

        mock_bss = MagicMock()
        mock_bss.get_customer.return_value = app.state.mock_bss.get_customer("cust-001")
        mock_bss.get_customer_bills.return_value = []
        mock_bss.get_customer_usage.return_value = None

        service = BillingContextService(mock_bss)
        result = service.get_customer_context("cust-001")
        assert result is not None
        assert "Henuz fatura bilgisi bulunmamaktadir" in result

    def test_bill_payment_status(self, billing_service):
        """Output shows 'Odendi' for is_paid=True, 'Odenmedi' for is_paid=False."""
        result = billing_service.get_customer_context("cust-001")
        assert result is not None
        # cust-001 has paid and unpaid bills
        assert "Odendi" in result
        assert "Odenmedi" in result

    def test_currency_formatting_with_thousands(self, billing_service):
        """Large amounts use period as thousands separator."""
        from app.services.billing_context import BillingContextService

        result = BillingContextService._format_tl(Decimal("1234.56"))
        assert result == "1.234,56 TL"

    def test_currency_formatting_simple(self, billing_service):
        """Simple amounts format correctly."""
        from app.services.billing_context import BillingContextService

        result = BillingContextService._format_tl(Decimal("299.00"))
        assert result == "299,00 TL"


# -- Billing Prompts tests --


class TestBillingPrompts:
    """Test BILLING_SYSTEM_PROMPT content and structure."""

    def test_billing_system_prompt_has_placeholders(self):
        """BILLING_SYSTEM_PROMPT contains customer_context and rag_context placeholders."""
        from app.prompts.billing_prompts import BILLING_SYSTEM_PROMPT

        assert "{customer_context}" in BILLING_SYSTEM_PROMPT
        assert "{rag_context}" in BILLING_SYSTEM_PROMPT

    def test_billing_system_prompt_has_analysis_rules(self):
        """BILLING_SYSTEM_PROMPT contains 'Fatura Analiz Kurallari' section."""
        from app.prompts.billing_prompts import BILLING_SYSTEM_PROMPT

        assert "Fatura Analiz Kurallari" in BILLING_SYSTEM_PROMPT

    def test_billing_prompt_prioritizes_customer_data(self):
        """BILLING_SYSTEM_PROMPT contains instruction to prioritize customer data over RAG."""
        from app.prompts.billing_prompts import BILLING_SYSTEM_PROMPT

        assert "musteri bilgilerindeki gercek verileri kullan" in BILLING_SYSTEM_PROMPT

    def test_billing_prompt_has_security_guardrails(self):
        """BILLING_SYSTEM_PROMPT preserves GUVENLIK section from existing prompt."""
        from app.prompts.billing_prompts import BILLING_SYSTEM_PROMPT

        assert "GUVENLIK" in BILLING_SYSTEM_PROMPT

    def test_billing_prompt_has_turkcell_identity(self):
        """BILLING_SYSTEM_PROMPT identifies as Turkcell Asistan."""
        from app.prompts.billing_prompts import BILLING_SYSTEM_PROMPT

        assert "Turkcell Asistan" in BILLING_SYSTEM_PROMPT

    def test_billing_prompt_has_empathy_rules(self):
        """BILLING_SYSTEM_PROMPT includes empathy instructions."""
        from app.prompts.billing_prompts import BILLING_SYSTEM_PROMPT

        assert "empati" in BILLING_SYSTEM_PROMPT


# -- Billing Chat Integration tests (Plan 03) --


class TestBillingChatIntegration:
    """Test ChatService integration with BillingContextService."""

    def test_chat_request_optional_customer_id(self):
        """ChatRequest works with and without customer_id."""
        from app.models.chat_schemas import ChatRequest

        # Without customer_id
        req1 = ChatRequest(message="test")
        assert req1.message == "test"

        # With customer_id
        req2 = ChatRequest(message="test", customer_id="cust-001")
        assert req2.customer_id == "cust-001"

    def test_chat_request_customer_id_none_default(self):
        """ChatRequest.customer_id defaults to None."""
        from app.models.chat_schemas import ChatRequest

        req = ChatRequest(message="test")
        assert req.customer_id is None

    @patch("app.services.chat_service.MemoryService")
    @patch("app.services.chat_service.RAGService")
    @patch("app.services.chat_service.ChatGoogleGenerativeAI")
    def test_chat_service_init_with_billing_context(
        self, MockLLM, MockRAG, MockMemory
    ):
        """ChatService accepts optional billing_context parameter."""
        from app.services.chat_service import ChatService
        from app.services.billing_context import BillingContextService

        settings = MagicMock()
        settings.gemini_api_key = "test-key"
        settings.redis_url = "redis://localhost:6379/0"
        settings.milvus_host = "localhost"
        settings.milvus_port = 19530
        settings.milvus_collection_name = "test"

        mock_bss = MagicMock()
        billing_ctx = BillingContextService(mock_bss)

        service = ChatService(settings, pii_enabled=False, billing_context=billing_ctx)
        assert service._billing_context is billing_ctx

    @patch("app.services.chat_service.MemoryService")
    @patch("app.services.chat_service.RAGService")
    @patch("app.services.chat_service.ChatGoogleGenerativeAI")
    def test_chat_service_init_without_billing_context(
        self, MockLLM, MockRAG, MockMemory
    ):
        """ChatService still works without billing_context (backward compatible)."""
        from app.services.chat_service import ChatService

        settings = MagicMock()
        settings.gemini_api_key = "test-key"
        settings.redis_url = "redis://localhost:6379/0"
        settings.milvus_host = "localhost"
        settings.milvus_port = 19530
        settings.milvus_collection_name = "test"

        service = ChatService(settings, pii_enabled=False)
        assert service._billing_context is None

    @patch("app.services.chat_service.MemoryService")
    @patch("app.services.chat_service.RAGService")
    @patch("app.services.chat_service.ChatGoogleGenerativeAI")
    async def test_chat_service_with_customer_id_uses_billing_prompt(
        self, MockLLM, MockRAG, MockMemory
    ):
        """When stream_response called with customer_id, system prompt contains 'Musteri Bilgileri'."""
        from app.services.chat_service import ChatService
        from app.services.billing_context import BillingContextService

        settings = MagicMock()
        settings.gemini_api_key = "test-key"
        settings.redis_url = "redis://localhost:6379/0"
        settings.milvus_host = "localhost"
        settings.milvus_port = 19530
        settings.milvus_collection_name = "test"

        # Mock RAG
        mock_rag = AsyncMock()
        mock_rag.search = AsyncMock(return_value=[{"content": "RAG content", "metadata": {}, "score": 0.9}])
        MockRAG.return_value = mock_rag

        # Mock Memory
        mock_memory = MagicMock()
        mock_memory.get_history = MagicMock(return_value=[])
        mock_memory.add_messages = MagicMock()
        MockMemory.return_value = mock_memory

        # Capture messages sent to LLM
        captured_messages = []

        async def mock_astream(messages):
            captured_messages.extend(messages)
            chunk = MagicMock()
            chunk.content = "Yanit"
            yield chunk

        mock_llm = MagicMock()
        mock_llm.astream = mock_astream
        MockLLM.return_value = mock_llm

        # Real BillingContextService with mock BSS data
        billing_ctx = BillingContextService(app.state.mock_bss)

        service = ChatService(settings, pii_enabled=False, billing_context=billing_ctx)
        async for _ in service.stream_response("Faturam neden yuksek?", "session-1", customer_id="cust-001"):
            pass

        # System prompt should contain billing context
        system_msg = captured_messages[0]
        assert isinstance(system_msg, SystemMessage)
        assert "Musteri Bilgileri" in system_msg.content
        assert "Fatura Analiz Kurallari" in system_msg.content

    @patch("app.services.chat_service.MemoryService")
    @patch("app.services.chat_service.RAGService")
    @patch("app.services.chat_service.ChatGoogleGenerativeAI")
    async def test_chat_service_without_customer_id_uses_standard_prompt(
        self, MockLLM, MockRAG, MockMemory
    ):
        """When stream_response called without customer_id, uses standard SYSTEM_PROMPT."""
        from app.services.chat_service import ChatService
        from app.services.billing_context import BillingContextService

        settings = MagicMock()
        settings.gemini_api_key = "test-key"
        settings.redis_url = "redis://localhost:6379/0"
        settings.milvus_host = "localhost"
        settings.milvus_port = 19530
        settings.milvus_collection_name = "test"

        mock_rag = AsyncMock()
        mock_rag.search = AsyncMock(return_value=[{"content": "RAG content", "metadata": {}, "score": 0.9}])
        MockRAG.return_value = mock_rag

        mock_memory = MagicMock()
        mock_memory.get_history = MagicMock(return_value=[])
        mock_memory.add_messages = MagicMock()
        MockMemory.return_value = mock_memory

        captured_messages = []

        async def mock_astream(messages):
            captured_messages.extend(messages)
            chunk = MagicMock()
            chunk.content = "Yanit"
            yield chunk

        mock_llm = MagicMock()
        mock_llm.astream = mock_astream
        MockLLM.return_value = mock_llm

        billing_ctx = BillingContextService(app.state.mock_bss)
        service = ChatService(settings, pii_enabled=False, billing_context=billing_ctx)

        # No customer_id
        async for _ in service.stream_response("Merhaba", "session-1"):
            pass

        system_msg = captured_messages[0]
        assert isinstance(system_msg, SystemMessage)
        assert "Bilgi Kaynaklari" in system_msg.content
        assert "Musteri Bilgileri" not in system_msg.content

    @patch("app.services.chat_service.MemoryService")
    @patch("app.services.chat_service.RAGService")
    @patch("app.services.chat_service.ChatGoogleGenerativeAI")
    async def test_chat_service_unknown_customer_falls_back(
        self, MockLLM, MockRAG, MockMemory
    ):
        """When customer_id is unknown, falls back to standard prompt."""
        from app.services.chat_service import ChatService
        from app.services.billing_context import BillingContextService

        settings = MagicMock()
        settings.gemini_api_key = "test-key"
        settings.redis_url = "redis://localhost:6379/0"
        settings.milvus_host = "localhost"
        settings.milvus_port = 19530
        settings.milvus_collection_name = "test"

        mock_rag = AsyncMock()
        mock_rag.search = AsyncMock(return_value=[{"content": "RAG content", "metadata": {}, "score": 0.9}])
        MockRAG.return_value = mock_rag

        mock_memory = MagicMock()
        mock_memory.get_history = MagicMock(return_value=[])
        mock_memory.add_messages = MagicMock()
        MockMemory.return_value = mock_memory

        captured_messages = []

        async def mock_astream(messages):
            captured_messages.extend(messages)
            chunk = MagicMock()
            chunk.content = "Yanit"
            yield chunk

        mock_llm = MagicMock()
        mock_llm.astream = mock_astream
        MockLLM.return_value = mock_llm

        billing_ctx = BillingContextService(app.state.mock_bss)
        service = ChatService(settings, pii_enabled=False, billing_context=billing_ctx)

        # Unknown customer_id
        async for _ in service.stream_response("test", "session-1", customer_id="nonexistent"):
            pass

        system_msg = captured_messages[0]
        assert isinstance(system_msg, SystemMessage)
        # Should fall back to standard prompt (no billing context)
        assert "Musteri Bilgileri" not in system_msg.content
