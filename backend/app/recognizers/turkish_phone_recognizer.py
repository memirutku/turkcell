"""Turkish phone number recognizer.

Matches Turkish mobile phone numbers in various formats:
- International: +90 5XX XXX XX XX
- Local: 05XX XXX XX XX
- Compact: 5XX XXX XX XX
"""

from presidio_analyzer import Pattern, PatternRecognizer


class TurkishPhoneRecognizer(PatternRecognizer):
    """Detect Turkish phone numbers in various formats."""

    PATTERNS = [
        Pattern(
            name="tr_phone_intl",
            regex=r"\b(?:\+90)\s*5\d{2}\s*\d{3}\s*\d{2}\s*\d{2}\b",
            score=0.7,
        ),
        Pattern(
            name="tr_phone_local",
            regex=r"\b0\s*5\d{2}\s*\d{3}\s*\d{2}\s*\d{2}\b",
            score=0.6,
        ),
        Pattern(
            name="tr_phone_compact",
            regex=r"\b5\d{2}\s*\d{3}\s*\d{2}\s*\d{2}\b",
            score=0.3,
        ),
    ]
    CONTEXT = ["telefon", "numara", "cep", "gsm", "hat", "ara", "iletisim"]

    def __init__(self):
        super().__init__(
            supported_entity="TR_PHONE_NUMBER",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="tr",
        )
