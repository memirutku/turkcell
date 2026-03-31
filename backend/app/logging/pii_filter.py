"""PII sanitization filter for Python logging.

Applies regex-based replacement of Turkish PII patterns in log records
to prevent accidental PII leakage through application logs (SEC-03).
"""

import logging
import re


class PIILoggingFilter(logging.Filter):
    """Filter that sanitizes PII from log record messages and arguments.

    Replaces:
    - TC Kimlik numbers -> [TC_KIMLIK]
    - Turkish phone numbers -> [TELEFON]
    - Turkish IBAN -> [IBAN]
    - Email addresses -> [EMAIL]

    This is a lightweight regex-based filter for log sanitization.
    For full NLP-based PII detection, use PIIMaskingService (Presidio).
    """

    PATTERNS: list[tuple[str, str]] = [
        (r"\b[1-9]\d{10}\b", "[TC_KIMLIK]"),
        (r"\b(?:\+90|0)?\s*5\d{2}\s*\d{3}\s*\d{2}\s*\d{2}\b", "[TELEFON]"),
        (r"\bTR\s?\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{2}\b", "[IBAN]"),
        (r"\bTR\d{24}\b", "[IBAN]"),
        (r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", "[EMAIL]"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._compiled = [(re.compile(pattern), replacement) for pattern, replacement in self.PATTERNS]

    def _sanitize(self, text: str) -> str:
        """Apply all PII patterns to sanitize text."""
        for pattern, replacement in self._compiled:
            text = pattern.sub(replacement, text)
        return text

    def filter(self, record: logging.LogRecord) -> bool:
        """Sanitize PII from log record msg and args.

        Returns True always -- never suppresses log records.
        """
        if isinstance(record.msg, str):
            record.msg = self._sanitize(record.msg)

        if record.args and isinstance(record.args, tuple):
            record.args = tuple(
                self._sanitize(str(a)) if isinstance(a, str) else a
                for a in record.args
            )

        return True
