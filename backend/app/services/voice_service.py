"""Voice pipeline orchestration: STT -> Chat -> TTS."""

import asyncio
import io
import logging

from pydub import AudioSegment

from app.services.chat_service import ChatService
from app.services.stt_service import MockSTTService, STTService
from app.services.tts_service import MockTTSService, TTSService

logger = logging.getLogger(__name__)


class VoiceService:
    """Orchestrates the voice pipeline: STT -> Chat -> TTS.

    Processes voice input through three stages:
    1. Convert browser audio (WebM/Opus) to WAV via pydub/ffmpeg
    2. Transcribe WAV to Turkish text via Gemini multimodal STT
    3. Process text through ChatService (RAG + LLM)
    4. Synthesize response text to MP3 via AWS Polly TTS

    All blocking I/O operations use asyncio.to_thread() to avoid
    blocking the event loop.
    """

    def __init__(
        self,
        stt_service: STTService | MockSTTService,
        tts_service: TTSService | MockTTSService | None,
        chat_service: ChatService,
    ) -> None:
        self._stt = stt_service
        self._tts = tts_service
        self._chat = chat_service

    async def process_voice(
        self,
        audio_bytes: bytes,
        session_id: str,
        customer_id: str | None = None,
    ) -> dict:
        """Process voice input through the full pipeline.

        Args:
            audio_bytes: Raw audio bytes from the browser (WebM/Opus format).
            session_id: Session ID for conversation memory.
            customer_id: Optional customer ID for billing context.

        Returns:
            Dict with keys:
                - transcribed_text: STT result
                - response_text: Full LLM response text
                - tokens: List of individual LLM streaming tokens
                - audio_response: MP3 bytes from TTS, or None
        """
        # 1. Convert WebM/Opus to WAV
        wav_bytes = await asyncio.to_thread(self._convert_to_wav, audio_bytes)

        # 2. Transcribe via Gemini
        transcribed_text = await self._stt.transcribe(wav_bytes)
        logger.info("STT result: %d chars", len(transcribed_text))

        # 3. Process through chat pipeline (collect full text from stream)
        full_response = ""
        tokens = []
        async for item in self._chat.stream_response(
            transcribed_text, session_id, customer_id
        ):
            if isinstance(item, str):
                full_response += item
                tokens.append(item)

        # 4. Synthesize response audio via Polly (if TTS available)
        audio_response = None
        if self._tts and full_response:
            try:
                audio_response = await self._tts.synthesize(full_response)
            except Exception:
                logger.exception("TTS synthesis failed, returning text only")

        return {
            "transcribed_text": transcribed_text,
            "response_text": full_response,
            "tokens": tokens,
            "audio_response": audio_response,
        }

    @staticmethod
    def _convert_to_wav(audio_bytes: bytes) -> bytes:
        """Convert WebM/Opus audio to WAV format for Gemini.

        Args:
            audio_bytes: Raw audio bytes in WebM/Opus format.

        Returns:
            Audio bytes in WAV format (16kHz, mono).
        """
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="webm")
        audio = audio.set_frame_rate(16000).set_channels(1)
        buffer = io.BytesIO()
        audio.export(buffer, format="wav")
        return buffer.getvalue()
