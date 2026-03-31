"""Turkish IBAN recognizer.

Turkish IBAN format: TR + 2 check digits + 22 digits = 26 characters total.
Matches both compact (TR330006100519786457841326) and spaced formats.
"""

from presidio_analyzer import Pattern, PatternRecognizer


class TurkishIbanRecognizer(PatternRecognizer):
    """Detect Turkish IBAN numbers."""

    PATTERNS = [
        Pattern(
            name="tr_iban",
            regex=r"\bTR\s?\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{2}\b",
            score=0.7,
        ),
        Pattern(
            name="tr_iban_compact",
            regex=r"\bTR\d{24}\b",
            score=0.85,
        ),
    ]
    CONTEXT = ["iban", "hesap", "banka", "havale", "eft", "transfer"]

    def __init__(self):
        super().__init__(
            supported_entity="TR_IBAN",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="tr",
        )
