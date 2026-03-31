"""Tests for PII masking service and Turkish recognizers.

Covers: SEC-01 (PII masking), SEC-02 (Turkish recognizers), SEC-05 (env security).
"""

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider

from app.recognizers.tc_kimlik_recognizer import TcKimlikRecognizer
from app.recognizers.turkish_phone_recognizer import TurkishPhoneRecognizer
from app.recognizers.turkish_iban_recognizer import TurkishIbanRecognizer
from app.services.pii_service import PIIMaskingService


# ---------------------------------------------------------------------------
# Helper: create a single-recognizer analyzer for unit testing
# ---------------------------------------------------------------------------

def _make_analyzer(recognizer):
    """Create an AnalyzerEngine with a single recognizer for isolated unit tests."""
    configuration = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "tr", "model_name": "xx_ent_wiki_sm"}],
    }
    provider = NlpEngineProvider(nlp_configuration=configuration)
    nlp_engine = provider.create_engine()

    registry = RecognizerRegistry(supported_languages=["tr"])
    registry.add_recognizer(recognizer)

    return AnalyzerEngine(
        registry=registry,
        nlp_engine=nlp_engine,
        supported_languages=["tr"],
    )


# ===========================================================================
# TC Kimlik Recognizer Tests
# ===========================================================================

class TestTcKimlikRecognizer:
    """Test TC Kimlik No detection with checksum validation."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.recognizer = TcKimlikRecognizer()
        self.analyzer = _make_analyzer(self.recognizer)

    def test_detects_valid_tc_kimlik(self):
        """Valid TC Kimlik '10000000146' should be detected."""
        text = "TC Kimlik numaram 10000000146"
        results = self.analyzer.analyze(text=text, language="tr")
        tc_results = [r for r in results if r.entity_type == "TC_KIMLIK_NO"]
        assert len(tc_results) >= 1, f"Expected TC_KIMLIK_NO detection, got: {results}"
        detected_text = text[tc_results[0].start:tc_results[0].end]
        assert detected_text == "10000000146"

    def test_rejects_invalid_checksum(self):
        """Invalid 11-digit number '12345678901' should NOT be detected as TC Kimlik."""
        text = "Numara: 12345678901"
        results = self.analyzer.analyze(text=text, language="tr")
        tc_results = [r for r in results if r.entity_type == "TC_KIMLIK_NO"]
        assert len(tc_results) == 0, (
            f"Invalid TC Kimlik should be rejected, but got: {tc_results}"
        )

    def test_context_word_boost(self):
        """TC Kimlik with context words should have higher score."""
        text_with_context = "TC Kimlik numaram 10000000146"
        text_without_context = "Deger: 10000000146"
        results_with = self.analyzer.analyze(text=text_with_context, language="tr")
        results_without = self.analyzer.analyze(text=text_without_context, language="tr")
        tc_with = [r for r in results_with if r.entity_type == "TC_KIMLIK_NO"]
        tc_without = [r for r in results_without if r.entity_type == "TC_KIMLIK_NO"]
        assert len(tc_with) >= 1
        # Both should detect, but context-boosted should have higher score
        if tc_without:
            assert tc_with[0].score >= tc_without[0].score


# ===========================================================================
# Turkish Phone Recognizer Tests
# ===========================================================================

class TestTurkishPhoneRecognizer:
    """Test Turkish phone number detection in various formats."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.recognizer = TurkishPhoneRecognizer()
        self.analyzer = _make_analyzer(self.recognizer)

    def test_detects_international_format(self):
        """+90 5XX format should be detected."""
        text = "Telefon: +90 532 123 45 67"
        results = self.analyzer.analyze(text=text, language="tr")
        phone_results = [r for r in results if r.entity_type == "TR_PHONE_NUMBER"]
        assert len(phone_results) >= 1, f"Expected TR_PHONE_NUMBER, got: {results}"

    def test_detects_local_format(self):
        """0-prefix format should be detected."""
        text = "Telefon numaram 0532 123 45 67"
        results = self.analyzer.analyze(text=text, language="tr")
        phone_results = [r for r in results if r.entity_type == "TR_PHONE_NUMBER"]
        assert len(phone_results) >= 1, f"Expected TR_PHONE_NUMBER, got: {results}"

    def test_detects_compact_format(self):
        """Compact format (no prefix) should be detected."""
        text = "Cep numaram 532 123 45 67"
        results = self.analyzer.analyze(text=text, language="tr")
        phone_results = [r for r in results if r.entity_type == "TR_PHONE_NUMBER"]
        assert len(phone_results) >= 1, f"Expected TR_PHONE_NUMBER, got: {results}"


# ===========================================================================
# Turkish IBAN Recognizer Tests
# ===========================================================================

class TestTurkishIbanRecognizer:
    """Test Turkish IBAN detection."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.recognizer = TurkishIbanRecognizer()
        self.analyzer = _make_analyzer(self.recognizer)

    def test_detects_compact_iban(self):
        """Compact IBAN (no spaces) should be detected."""
        text = "IBAN: TR330006100519786457841326"
        results = self.analyzer.analyze(text=text, language="tr")
        iban_results = [r for r in results if r.entity_type == "TR_IBAN"]
        assert len(iban_results) >= 1, f"Expected TR_IBAN, got: {results}"

    def test_detects_spaced_iban(self):
        """Spaced IBAN should be detected."""
        text = "IBAN numaram TR33 0006 1005 1978 6457 8413 26"
        results = self.analyzer.analyze(text=text, language="tr")
        iban_results = [r for r in results if r.entity_type == "TR_IBAN"]
        assert len(iban_results) >= 1, f"Expected TR_IBAN, got: {results}"


# ===========================================================================
# PIIMaskingService Tests
# ===========================================================================

class TestPIIMaskingService:
    """Test the full PIIMaskingService.mask() method."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.service = PIIMaskingService()

    def test_mask_replaces_tc_kimlik(self):
        """TC Kimlik number should be replaced with [TC_KIMLIK]."""
        text = "TC Kimlik numaram 10000000146"
        result = self.service.mask(text)
        assert "10000000146" not in result
        assert "[TC_KIMLIK]" in result

    def test_mask_replaces_phone(self):
        """Phone number should be replaced with [TELEFON]."""
        text = "Telefon numaram 0532 123 45 67"
        result = self.service.mask(text)
        assert "0532" not in result
        assert "[TELEFON]" in result

    def test_mask_replaces_iban(self):
        """IBAN should be replaced with [IBAN]."""
        text = "IBAN: TR330006100519786457841326"
        result = self.service.mask(text)
        assert "TR330006100519786457841326" not in result
        assert "[IBAN]" in result

    def test_mask_replaces_email(self):
        """Email should be replaced with [EMAIL]."""
        text = "Email adresim ahmet@example.com"
        result = self.service.mask(text)
        assert "ahmet@example.com" not in result
        assert "[EMAIL]" in result

    def test_mask_no_pii_returns_unchanged(self):
        """Text without PII should be returned unchanged."""
        text = "Tarifemi degistirmek istiyorum"
        result = self.service.mask(text)
        assert result == text

    def test_mask_combined_multiple_pii(self):
        """Text with multiple PII types should have all replaced."""
        text = (
            "Ahmet Yilmaz, TC: 10000000146, "
            "tel: 0532 123 45 67, "
            "IBAN: TR330006100519786457841326"
        )
        result = self.service.mask(text)
        assert "10000000146" not in result
        assert "0532" not in result
        assert "TR330006100519786457841326" not in result
        assert "[TC_KIMLIK]" in result
        assert "[TELEFON]" in result
        assert "[IBAN]" in result


# ===========================================================================
# Security Config Tests (SEC-05)
# ===========================================================================

# ===========================================================================
# ChatService PII Integration Tests (Plan 02)
# ===========================================================================

class TestChatServicePIIIntegration:
    """Test that ChatService integrates with PIIMaskingService."""

    @patch("app.services.chat_service.MemoryService")
    @patch("app.services.chat_service.RAGService")
    @patch("app.services.chat_service.ChatGoogleGenerativeAI")
    def test_init_creates_pii_service_when_enabled(self, MockLLM, MockRAG, MockMemory):
        """ChatService should create PIIMaskingService when pii_enabled=True."""
        from app.services.chat_service import ChatService

        settings = MagicMock()
        settings.gemini_api_key = "test-key"
        settings.redis_url = "redis://localhost:6379/0"
        settings.milvus_host = "localhost"
        settings.milvus_port = 19530
        settings.milvus_collection_name = "test"

        with patch("app.services.chat_service.PIIMaskingService") as MockPII:
            service = ChatService(settings, pii_enabled=True)
            MockPII.assert_called_once()
            assert service._pii_service is not None

    @patch("app.services.chat_service.MemoryService")
    @patch("app.services.chat_service.RAGService")
    @patch("app.services.chat_service.ChatGoogleGenerativeAI")
    def test_init_no_pii_service_when_disabled(self, MockLLM, MockRAG, MockMemory):
        """ChatService should set _pii_service=None when pii_enabled=False."""
        from app.services.chat_service import ChatService

        settings = MagicMock()
        settings.gemini_api_key = "test-key"
        settings.redis_url = "redis://localhost:6379/0"
        settings.milvus_host = "localhost"
        settings.milvus_port = 19530
        settings.milvus_collection_name = "test"

        service = ChatService(settings, pii_enabled=False)
        assert service._pii_service is None

    @patch("app.services.chat_service.MemoryService")
    @patch("app.services.chat_service.RAGService")
    @patch("app.services.chat_service.ChatGoogleGenerativeAI")
    async def test_stream_response_masks_message_before_rag(self, MockLLM, MockRAG, MockMemory):
        """ChatService should mask PII before passing message to RAG search."""
        from app.services.chat_service import ChatService

        settings = MagicMock()
        settings.gemini_api_key = "test-key"
        settings.redis_url = "redis://localhost:6379/0"
        settings.milvus_host = "localhost"
        settings.milvus_port = 19530
        settings.milvus_collection_name = "test"

        mock_rag = AsyncMock()
        mock_rag.search = AsyncMock(return_value=[])
        MockRAG.return_value = mock_rag

        mock_memory = MagicMock()
        mock_memory.get_history = MagicMock(return_value=[])
        mock_memory.add_messages = MagicMock()
        MockMemory.return_value = mock_memory

        async def mock_astream(messages):
            chunk = MagicMock()
            chunk.content = "Ok"
            yield chunk

        mock_llm = MagicMock()
        mock_llm.astream = mock_astream
        MockLLM.return_value = mock_llm

        with patch("app.services.chat_service.PIIMaskingService") as MockPII:
            mock_pii = MagicMock()
            mock_pii.mask = MagicMock(return_value="masked_query")
            MockPII.return_value = mock_pii

            service = ChatService(settings, pii_enabled=True)
            async for _ in service.stream_response("TC: 10000000146", "session-1"):
                pass

            mock_pii.mask.assert_called_once_with("TC: 10000000146")
            mock_rag.search.assert_called_once_with("masked_query", top_k=5)

    @patch("app.services.chat_service.MemoryService")
    @patch("app.services.chat_service.RAGService")
    @patch("app.services.chat_service.ChatGoogleGenerativeAI")
    async def test_stream_response_stores_masked_in_history(self, MockLLM, MockRAG, MockMemory):
        """ChatService should store masked message (not original) in history."""
        from app.services.chat_service import ChatService

        settings = MagicMock()
        settings.gemini_api_key = "test-key"
        settings.redis_url = "redis://localhost:6379/0"
        settings.milvus_host = "localhost"
        settings.milvus_port = 19530
        settings.milvus_collection_name = "test"

        mock_rag = AsyncMock()
        mock_rag.search = AsyncMock(return_value=[])
        MockRAG.return_value = mock_rag

        mock_memory = MagicMock()
        mock_memory.get_history = MagicMock(return_value=[])
        mock_memory.add_messages = MagicMock()
        MockMemory.return_value = mock_memory

        async def mock_astream(messages):
            chunk = MagicMock()
            chunk.content = "Response"
            yield chunk

        mock_llm = MagicMock()
        mock_llm.astream = mock_astream
        MockLLM.return_value = mock_llm

        with patch("app.services.chat_service.PIIMaskingService") as MockPII:
            mock_pii = MagicMock()
            mock_pii.mask = MagicMock(return_value="masked_message")
            MockPII.return_value = mock_pii

            service = ChatService(settings, pii_enabled=True)
            async for _ in service.stream_response("raw message with PII", "session-1"):
                pass

            mock_memory.add_messages.assert_called_once_with(
                "session-1", "masked_message", "Response"
            )

    @patch("app.services.chat_service.MemoryService")
    @patch("app.services.chat_service.RAGService")
    @patch("app.services.chat_service.ChatGoogleGenerativeAI")
    async def test_stream_response_skips_masking_when_disabled(self, MockLLM, MockRAG, MockMemory):
        """ChatService with pii_enabled=False should pass raw message through."""
        from app.services.chat_service import ChatService

        settings = MagicMock()
        settings.gemini_api_key = "test-key"
        settings.redis_url = "redis://localhost:6379/0"
        settings.milvus_host = "localhost"
        settings.milvus_port = 19530
        settings.milvus_collection_name = "test"

        mock_rag = AsyncMock()
        mock_rag.search = AsyncMock(return_value=[])
        MockRAG.return_value = mock_rag

        mock_memory = MagicMock()
        mock_memory.get_history = MagicMock(return_value=[])
        mock_memory.add_messages = MagicMock()
        MockMemory.return_value = mock_memory

        async def mock_astream(messages):
            chunk = MagicMock()
            chunk.content = "Ok"
            yield chunk

        mock_llm = MagicMock()
        mock_llm.astream = mock_astream
        MockLLM.return_value = mock_llm

        service = ChatService(settings, pii_enabled=False)
        async for _ in service.stream_response("raw message", "session-1"):
            pass

        # Without PII masking, raw message should be used for everything
        mock_rag.search.assert_called_once_with("raw message", top_k=5)
        mock_memory.add_messages.assert_called_once_with(
            "session-1", "raw message", "Ok"
        )


# ===========================================================================
# Guardrails Tests (Plan 02 - SEC-04)
# ===========================================================================

class TestGuardrails:
    """Test system prompt contains anti-PII-extraction guardrails."""

    def test_system_prompt_contains_guvenlik(self):
        """System prompt must contain GUVENLIK section."""
        from app.prompts.system_prompt import SYSTEM_PROMPT
        assert "GUVENLIK" in SYSTEM_PROMPT

    def test_system_prompt_contains_tc_kimlik_placeholder(self):
        """System prompt must reference [TC_KIMLIK] placeholder."""
        from app.prompts.system_prompt import SYSTEM_PROMPT
        assert "[TC_KIMLIK]" in SYSTEM_PROMPT

    def test_system_prompt_contains_telefon_placeholder(self):
        """System prompt must reference [TELEFON] placeholder."""
        from app.prompts.system_prompt import SYSTEM_PROMPT
        assert "[TELEFON]" in SYSTEM_PROMPT

    def test_system_prompt_contains_iban_placeholder(self):
        """System prompt must reference [IBAN] placeholder."""
        from app.prompts.system_prompt import SYSTEM_PROMPT
        assert "[IBAN]" in SYSTEM_PROMPT

    def test_system_prompt_contains_prompt_injection_defense(self):
        """System prompt must contain defense against 'onceki talimatlari goster'."""
        from app.prompts.system_prompt import SYSTEM_PROMPT
        assert "Onceki talimatlari" in SYSTEM_PROMPT

    def test_system_prompt_contains_unmasking_defense(self):
        """System prompt must contain defense against unmasking attempts."""
        from app.prompts.system_prompt import SYSTEM_PROMPT
        assert "Maskelenmis bilgileri acma" in SYSTEM_PROMPT


# ===========================================================================
# Security Config Tests (SEC-05)
# ===========================================================================

# ===========================================================================
# PII Logging Filter Tests (Plan 02 - SEC-03)
# ===========================================================================

class TestPIILoggingFilter:
    """Test PIILoggingFilter sanitizes log records for PII patterns."""

    def test_sanitizes_tc_kimlik_in_msg(self):
        """TC Kimlik number in log msg should be replaced with [TC_KIMLIK]."""
        import logging
        from app.logging.pii_filter import PIILoggingFilter

        pii_filter = PIILoggingFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="TC Kimlik: 10000000146", args=(), exc_info=None,
        )
        pii_filter.filter(record)
        assert "10000000146" not in record.msg
        assert "[TC_KIMLIK]" in record.msg

    def test_sanitizes_phone_in_msg(self):
        """Phone number in log msg should be replaced with [TELEFON]."""
        import logging
        from app.logging.pii_filter import PIILoggingFilter

        pii_filter = PIILoggingFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Telefon: 0532 123 45 67", args=(), exc_info=None,
        )
        pii_filter.filter(record)
        assert "0532" not in record.msg
        assert "[TELEFON]" in record.msg

    def test_sanitizes_iban_in_msg(self):
        """IBAN in log msg should be replaced with [IBAN]."""
        import logging
        from app.logging.pii_filter import PIILoggingFilter

        pii_filter = PIILoggingFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="IBAN: TR330006100519786457841326", args=(), exc_info=None,
        )
        pii_filter.filter(record)
        assert "TR330006100519786457841326" not in record.msg
        assert "[IBAN]" in record.msg

    def test_sanitizes_email_in_msg(self):
        """Email in log msg should be replaced with [EMAIL]."""
        import logging
        from app.logging.pii_filter import PIILoggingFilter

        pii_filter = PIILoggingFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Email: ahmet@turkcell.com.tr", args=(), exc_info=None,
        )
        pii_filter.filter(record)
        assert "ahmet@turkcell.com.tr" not in record.msg
        assert "[EMAIL]" in record.msg

    def test_sanitizes_args_tuple(self):
        """PII in record.args should be sanitized."""
        import logging
        from app.logging.pii_filter import PIILoggingFilter

        pii_filter = PIILoggingFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="User %s", args=("10000000146",), exc_info=None,
        )
        pii_filter.filter(record)
        assert "10000000146" not in record.args[0]
        assert "[TC_KIMLIK]" in record.args[0]

    def test_filter_returns_true(self):
        """Filter should always return True (never suppress records)."""
        import logging
        from app.logging.pii_filter import PIILoggingFilter

        pii_filter = PIILoggingFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Some log message", args=(), exc_info=None,
        )
        assert pii_filter.filter(record) is True

    def test_no_pii_passes_unchanged(self):
        """Text without PII should pass through unchanged."""
        import logging
        from app.logging.pii_filter import PIILoggingFilter

        pii_filter = PIILoggingFilter()
        original_msg = "Tarife degisikligi talebi alindi"
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg=original_msg, args=(), exc_info=None,
        )
        pii_filter.filter(record)
        assert record.msg == original_msg


# ===========================================================================
# Security Config Tests (SEC-05)
# ===========================================================================

class TestSecurityConfig:
    """Verify SEC-05: .env in .gitignore, .env.example exists."""

    def test_gitignore_contains_env(self):
        """.gitignore should contain .env to prevent secret leaks."""
        project_root = Path(__file__).resolve().parent.parent.parent
        gitignore_path = project_root / ".gitignore"
        assert gitignore_path.exists(), f".gitignore not found at {gitignore_path}"
        content = gitignore_path.read_text()
        # Check that .env is listed (as a standalone line, not just part of another pattern)
        lines = [line.strip() for line in content.splitlines()]
        assert ".env" in lines, ".env should be listed in .gitignore"

    def test_env_example_exists(self):
        """.env.example should exist as a template for environment variables."""
        project_root = Path(__file__).resolve().parent.parent.parent
        env_example_path = project_root / ".env.example"
        assert env_example_path.exists(), (
            f".env.example not found at {env_example_path}"
        )
