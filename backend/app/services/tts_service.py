"""Text-to-speech using AWS Polly with Burcu neural Turkish voice."""

import asyncio
import logging

import boto3

from app.config import Settings

logger = logging.getLogger(__name__)


class TTSService:
    """Text-to-speech using AWS Polly Burcu neural voice.

    Converts Turkish text responses to natural-sounding MP3 audio
    using the Burcu neural voice, which provides high-quality
    Turkish speech synthesis with natural prosody.
    """

    POLLY_MAX_CHARS = 2500  # Leave buffer under 3000 char Polly limit

    def __init__(self, settings: Settings) -> None:
        self._client = boto3.client(
            "polly",
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region,
        )

    async def synthesize(self, text: str) -> bytes:
        """Convert text to MP3 audio bytes via AWS Polly Burcu neural.

        Args:
            text: Turkish text to synthesize. Truncated at sentence
                  boundary if exceeding Polly's character limit.

        Returns:
            MP3 audio bytes.
        """
        # Truncate to Polly limit if needed (split at sentence boundary)
        if len(text) > self.POLLY_MAX_CHARS:
            truncated = text[: self.POLLY_MAX_CHARS]
            last_period = truncated.rfind(".")
            if last_period > 0:
                truncated = truncated[: last_period + 1]
            text = truncated

        response = await asyncio.to_thread(
            self._client.synthesize_speech,
            Text=text,
            OutputFormat="mp3",
            VoiceId="Burcu",
            Engine="neural",
            LanguageCode="tr-TR",
        )
        audio_stream = response["AudioStream"]
        return await asyncio.to_thread(audio_stream.read)


class MockTTSService:
    """Mock TTS for development without AWS credentials."""

    async def synthesize(self, text: str) -> bytes | None:
        """Return None -- no audio in mock mode."""
        return None
