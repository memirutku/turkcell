"""Speech-to-text using Gemini multimodal audio understanding."""

import asyncio
import logging

from google import genai

from app.config import Settings

logger = logging.getLogger(__name__)


class STTService:
    """Speech-to-text using Gemini multimodal audio understanding.

    Uses Gemini's native multimodal capability to transcribe audio
    directly, bypassing the need for a dedicated STT service like
    AWS Transcribe. This simplifies the architecture and leverages
    Gemini's strong Turkish language understanding.
    """

    def __init__(self, settings: Settings) -> None:
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = "gemini-2.0-flash"

    async def transcribe(self, wav_bytes: bytes) -> str:
        """Transcribe WAV audio to Turkish text using Gemini.

        Args:
            wav_bytes: Audio data in WAV format (16kHz, mono).

        Returns:
            Transcribed Turkish text.
        """
        response = await asyncio.to_thread(
            self._client.models.generate_content,
            model=self._model,
            contents=[
                "Bu ses kaydini Turkce olarak metne cevir. "
                "Sadece konusan kisinin soylediklerini yaz, "
                "baska bir sey ekleme.",
                {"mime_type": "audio/wav", "data": wav_bytes},
            ],
        )
        return response.text.strip()


class MockSTTService:
    """Mock STT for development without Gemini API key."""

    async def transcribe(self, wav_bytes: bytes) -> str:
        """Return a fixed Turkish text for testing."""
        return "Bu bir test ses kaydidir"
