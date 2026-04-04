"""Text-to-speech using Microsoft Edge TTS (free, no credentials required)."""

import io
import logging

import edge_tts

logger = logging.getLogger(__name__)


class EdgeTTSService:
    """Text-to-speech using Microsoft Edge TTS neural voices.

    Uses the same backend as Microsoft Edge's "Read Aloud" feature.
    No API key or credentials required. Produces MP3 audio matching
    the same format as AWS Polly TTSService.
    """

    VOICE = "tr-TR-EmelNeural"
    MAX_CHARS = 5000

    async def synthesize(self, text: str) -> bytes:
        """Convert text to MP3 audio bytes via Edge TTS.

        Args:
            text: Turkish text to synthesize. Truncated at sentence
                  boundary if exceeding character limit.

        Returns:
            MP3 audio bytes.
        """
        if not text or not text.strip():
            return b""

        # Truncate at sentence boundary if needed
        if len(text) > self.MAX_CHARS:
            truncated = text[: self.MAX_CHARS]
            last_period = truncated.rfind(".")
            if last_period > 0:
                truncated = truncated[: last_period + 1]
            text = truncated

        buffer = io.BytesIO()
        communicate = edge_tts.Communicate(text, self.VOICE)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buffer.write(chunk["data"])

        return buffer.getvalue()
