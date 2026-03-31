"""Tests for PII masking service and Turkish recognizers.

Covers: SEC-01 (PII masking), SEC-02 (Turkish recognizers), SEC-05 (env security).
"""

import os
from pathlib import Path

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

    registry = RecognizerRegistry()
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
