"""Voice pipeline orchestration: STT -> Chat -> TTS."""

import asyncio
import io
import logging
import re
from collections.abc import AsyncIterator

from pydub import AudioSegment

from app.services.chat_service import ChatService
from app.services.stt_service import MockSTTService, STTService
from app.services.tts_service import MockTTSService, TTSService

logger = logging.getLogger(__name__)

# Split at sentence boundaries (after . ! ?) followed by whitespace
SENTENCE_BOUNDARY = re.compile(r'(?<=[.!?])\s+')


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

    async def process_voice_streaming(
        self,
        audio_bytes: bytes,
        session_id: str,
        customer_id: str | None = None,
    ) -> AsyncIterator[dict]:
        """Process voice with sentence-level TTS streaming.

        Instead of waiting for the full LLM response before TTS,
        this method synthesizes audio at sentence boundaries and
        yields audio_chunk events incrementally.

        Yields dicts with types:
            - transcription: STT result text
            - token: individual LLM streaming token
            - audio_chunk: sentence-level TTS audio bytes (data key)
            - response_end: full LLM response text
            - audio_done: signal that all audio has been sent
        """
        # 1. Convert to WAV (auto-detects WAV input)
        wav_bytes = await asyncio.to_thread(self._convert_to_wav, audio_bytes)

        # 2. Transcribe via STT
        transcribed_text = await self._stt.transcribe(wav_bytes)
        logger.info("STT result: %d chars", len(transcribed_text))
        yield {"type": "transcription", "text": transcribed_text}

        # 3. Stream LLM response with sentence-level TTS
        buffer = ""
        full_response = ""
        async for item in self._chat.stream_response(
            transcribed_text, session_id, customer_id
        ):
            if isinstance(item, str):
                buffer += item
                full_response += item
                yield {"type": "token", "content": item}

                # Check for sentence boundaries
                sentences = SENTENCE_BOUNDARY.split(buffer)
                if len(sentences) > 1:
                    completed = " ".join(sentences[:-1])
                    buffer = sentences[-1]
                    if self._tts and completed.strip():
                        try:
                            audio = await self._tts.synthesize(completed)
                            if audio:
                                yield {"type": "audio_chunk", "data": audio}
                        except Exception:
                            logger.exception("Sentence TTS failed, skipping chunk")

        # 4. Synthesize remaining buffer
        if self._tts and buffer.strip():
            try:
                audio = await self._tts.synthesize(buffer)
                if audio:
                    yield {"type": "audio_chunk", "data": audio}
            except Exception:
                logger.exception("Final sentence TTS failed, skipping chunk")

        yield {"type": "response_end", "full_text": full_response}
        yield {"type": "audio_done"}

    @staticmethod
    def _convert_to_wav(audio_bytes: bytes) -> bytes:
        """Convert audio to WAV format for Gemini.

        If input is already WAV (RIFF header), return as-is.
        Otherwise, convert from WebM/Opus using pydub/ffmpeg.

        Args:
            audio_bytes: Raw audio bytes (WAV or WebM/Opus format).

        Returns:
            Audio bytes in WAV format (16kHz, mono).
        """
        if len(audio_bytes) >= 12 and audio_bytes[:4] == b"RIFF" and audio_bytes[8:12] == b"WAVE":
            return audio_bytes
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="webm")
        audio = audio.set_frame_rate(16000).set_channels(1)
        buffer = io.BytesIO()
        audio.export(buffer, format="wav")
        return buffer.getvalue()
