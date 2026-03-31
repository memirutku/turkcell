"""Turkish TC Kimlik No recognizer with checksum validation.

TC Kimlik No is an 11-digit national identification number where:
- First digit is non-zero
- 10th digit = ((d1+d3+d5+d7+d9)*7 - (d2+d4+d6+d8)) % 10
- 11th digit = sum(d1..d10) % 10
"""

from presidio_analyzer import Pattern, PatternRecognizer


class TcKimlikRecognizer(PatternRecognizer):
    """Detect and validate Turkish national ID numbers (TC Kimlik No)."""

    PATTERNS = [
        Pattern(
            name="tc_kimlik_no",
            regex=r"\b[1-9]\d{10}\b",
            score=0.4,
        ),
    ]
    CONTEXT = ["tc", "kimlik", "numara", "tckn", "kimlik no", "tc no", "vatandas"]

    def __init__(self):
        super().__init__(
            supported_entity="TC_KIMLIK_NO",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="tr",
        )

    def validate_result(self, pattern_text: str) -> bool:
        """Apply TC Kimlik No checksum validation."""
        if len(pattern_text) != 11 or not pattern_text.isdigit():
            return False
        if pattern_text[0] == "0":
            return False
        d = [int(c) for c in pattern_text]
        # 10th digit check
        chk10 = (
            (d[0] + d[2] + d[4] + d[6] + d[8]) * 7 - (d[1] + d[3] + d[5] + d[7])
        ) % 10
        if chk10 != d[9]:
            return False
        # 11th digit check
        if sum(d[:10]) % 10 != d[10]:
            return False
        return True
