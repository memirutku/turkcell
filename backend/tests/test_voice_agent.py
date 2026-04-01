"""Tests for voice-agent integration: confirmation parsing and routing logic."""
import pytest
from app.services.voice_service import parse_voice_confirmation


class TestParseVoiceConfirmation:
    """Test Turkish yes/no intent detection."""

    @pytest.mark.parametrize("text,expected", [
        ("evet", True),
        ("tamam", True),
        ("onayliyorum", True),
        ("onayla", True),
        ("kabul", True),
        ("olsun", True),
        ("Evet, tanimla", True),
        ("Tamam onayliyorum", True),
    ])
    def test_confirm_words(self, text, expected):
        assert parse_voice_confirmation(text) == expected

    @pytest.mark.parametrize("text,expected", [
        ("hayir", False),
        ("vazgec", False),
        ("iptal", False),
        ("istemiyorum", False),
        ("olmaz", False),
        ("Hayir istemiyorum", False),
    ])
    def test_reject_words(self, text, expected):
        assert parse_voice_confirmation(text) == expected

    @pytest.mark.parametrize("text", [
        "belki",
        "bilmiyorum",
        "ne demek",
        "",
        "hmmm",
    ])
    def test_ambiguous_returns_none(self, text):
        assert parse_voice_confirmation(text) is None

    def test_case_insensitive(self):
        assert parse_voice_confirmation("EVET") is True
        assert parse_voice_confirmation("HAYIR") is False

    def test_with_extra_whitespace(self):
        assert parse_voice_confirmation("  evet  ") is True
        assert parse_voice_confirmation("  hayir  ") is False
