"""Voice pipeline orchestration: STT -> Chat -> TTS."""

import asyncio
import io
import logging
import re
from collections.abc import AsyncIterator

from pydub import AudioSegment

from app.services.agent_service import AgentService
from app.services.chat_service import ChatService
from app.services.stt_service import MockSTTService, STTService
from app.services.tts_service import MockTTSService, TTSService

logger = logging.getLogger(__name__)

# Split at sentence boundaries (after . ! ?) followed by whitespace
SENTENCE_BOUNDARY = re.compile(r'(?<=[.!?])\s+')

# Turkish yes/no intent detection for voice confirmation
CONFIRM_WORDS = {"evet", "tamam", "onayliyorum", "onayla", "kabul", "olsun"}
REJECT_WORDS = {"hayir", "vazgec", "iptal", "istemiyorum", "olmaz"}


def parse_voice_confirmation(text: str) -> bool | None:
    """Parse Turkish confirmation/rejection from transcribed text.

    Returns True for confirm, False for reject, None for ambiguous.
    Strips punctuation from words before matching to handle STT output
    like "Evet, tanimla" where comma attaches to the word.
    """
    # Strip punctuation from each word for robust matching
    words = set(
        w.strip(".,!?;:") for w in text.lower().strip().split()
    )
    if words & CONFIRM_WORDS:
        return True
    if words & REJECT_WORDS:
        return False
    return None


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
        agent_service: AgentService | None = None,
    ) -> None:
        self._stt = stt_service
        self._tts = tts_service
        self._chat = chat_service
        self._agent = agent_service

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
        # Route to agent pipeline if agent available and customer context set
        if self._agent and customer_id:
            async for event in self.process_voice_streaming_with_agent(
                audio_bytes, session_id, customer_id
            ):
                yield event
            return

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

    async def process_voice_streaming_with_agent(
        self,
        audio_bytes: bytes,
        session_id: str,
        customer_id: str,
    ) -> AsyncIterator[dict]:
        """Process voice through agent pipeline with action support.

        Extends process_voice_streaming to handle:
        - AgentService.stream() for agent-capable responses
        - action_proposal events with TTS confirmation prompts
        - Waits for next audio input as confirmation (evet/hayir)
        - AgentService.resume() for action execution

        The confirmation flow is stateful: after yielding action_proposal +
        confirmation_prompt, this generator returns. The WebSocket handler
        manages the confirmation round-trip by calling
        process_voice_confirmation() with the next audio input.

        Yields same types as process_voice_streaming plus:
        - action_proposal: agent wants to perform an action
        - confirmation_prompt: TTS text for user to confirm
        - action_result: action execution result
        """
        # 1. Convert to WAV
        wav_bytes = await asyncio.to_thread(self._convert_to_wav, audio_bytes)

        # 2. Transcribe
        transcribed_text = await self._stt.transcribe(wav_bytes)
        logger.info("STT result (agent): %d chars", len(transcribed_text))
        yield {"type": "transcription", "text": transcribed_text}

        # 3. Stream through AgentService
        buffer = ""
        full_response = ""
        pending_proposal = None

        async for event in self._agent.stream(transcribed_text, session_id, customer_id):
            event_type = event.get("type")

            if event_type == "token":
                content = event.get("content", "")
                buffer += content
                full_response += content
                yield {"type": "token", "content": content}

                # Sentence-level TTS (same pattern as process_voice_streaming)
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
                            logger.exception("Sentence TTS failed in agent flow")

            elif event_type == "action_proposal":
                pending_proposal = event.get("data", {})

            elif event_type == "action_result":
                result_data = event.get("data", {})
                yield {"type": "action_result", "data": result_data}

            elif event_type == "error":
                yield {"type": "error", "message": event.get("content", "Bir hata olustu.")}

        # 4. Synthesize remaining buffer
        if self._tts and buffer.strip():
            try:
                audio = await self._tts.synthesize(buffer)
                if audio:
                    yield {"type": "audio_chunk", "data": audio}
            except Exception:
                logger.exception("Final sentence TTS failed in agent flow")

        # 5. If we got an action proposal, emit it + TTS confirmation prompt
        if pending_proposal:
            yield {"type": "response_end", "full_text": full_response}

            description = pending_proposal.get("description", "")
            prompt_text = f"{description} Onaylamak icin evet, iptal etmek icin hayir deyin."

            yield {
                "type": "action_proposal",
                "data": pending_proposal,
            }
            yield {
                "type": "confirmation_prompt",
                "text": prompt_text,
            }

            # Synthesize the confirmation prompt as TTS
            if self._tts:
                try:
                    audio = await self._tts.synthesize(prompt_text)
                    if audio:
                        yield {"type": "audio_chunk", "data": audio}
                except Exception:
                    logger.exception("Confirmation prompt TTS failed")

            yield {"type": "audio_done"}
            # Generator returns here -- WebSocket handler manages confirmation
            return

        # 6. Normal completion (no action proposal)
        yield {"type": "response_end", "full_text": full_response}
        yield {"type": "audio_done"}

    async def process_voice_confirmation(
        self,
        audio_bytes: bytes,
        session_id: str,
        proposal: dict,
        retry_count: int = 0,
    ) -> AsyncIterator[dict]:
        """Process voice confirmation for a pending action proposal.

        Args:
            audio_bytes: Audio from user saying evet/hayir.
            session_id: Session ID (used as LangGraph thread_id).
            proposal: The pending action proposal dict.
            retry_count: Number of retries so far (max 2).

        Yields:
            transcription, token, action_result, audio_chunk, audio_done,
            or retry (if ambiguous).
        """
        # 1. Transcribe the confirmation audio
        wav_bytes = await asyncio.to_thread(self._convert_to_wav, audio_bytes)
        transcribed_text = await self._stt.transcribe(wav_bytes)
        logger.info("Confirmation STT: '%s' (retry %d)", transcribed_text, retry_count)
        yield {"type": "transcription", "text": transcribed_text}

        # 2. Parse confirmation
        confirmed = parse_voice_confirmation(transcribed_text)

        if confirmed is None:
            # Ambiguous
            if retry_count < 2:
                retry_text = "Anlayamadim. Islemi onaylamak icin evet, iptal etmek icin hayir deyin."
                yield {"type": "confirmation_prompt", "text": retry_text}
                if self._tts:
                    try:
                        audio = await self._tts.synthesize(retry_text)
                        if audio:
                            yield {"type": "audio_chunk", "data": audio}
                    except Exception:
                        logger.exception("Retry prompt TTS failed")
                yield {"type": "audio_done"}
                yield {"type": "retry", "retry_count": retry_count + 1}
                return
            else:
                # Max retries -- cancel
                cancel_text = "Islem iptal edildi. Yazili olarak devam edebilirsiniz."
                yield {"type": "confirmation_prompt", "text": cancel_text}
                if self._tts:
                    try:
                        audio = await self._tts.synthesize(cancel_text)
                        if audio:
                            yield {"type": "audio_chunk", "data": audio}
                    except Exception:
                        logger.exception("Cancel prompt TTS failed")
                confirmed = False

        # 3. Resume agent with confirmation
        config = {"configurable": {"thread_id": session_id}}
        user_response = {"approved": confirmed}

        buffer = ""
        full_response = ""

        async for event in self._agent.resume(config, user_response):
            event_type = event.get("type")

            if event_type == "token":
                content = event.get("content", "")
                buffer += content
                full_response += content
                yield {"type": "token", "content": content}

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
                            logger.exception("Confirmation result TTS failed")

            elif event_type == "action_result":
                result_data = event.get("data", {})
                yield {"type": "action_result", "data": result_data}

                # TTS the result description
                if self._tts and result_data.get("success"):
                    result_desc = result_data.get("message_tr", result_data.get("description", ""))
                    if result_desc:
                        try:
                            audio = await self._tts.synthesize(result_desc)
                            if audio:
                                yield {"type": "audio_chunk", "data": audio}
                        except Exception:
                            logger.exception("Result description TTS failed")

            elif event_type == "error":
                yield {"type": "error", "message": event.get("content", "Bir hata olustu.")}

        # Final buffer
        if self._tts and buffer.strip():
            try:
                audio = await self._tts.synthesize(buffer)
                if audio:
                    yield {"type": "audio_chunk", "data": audio}
            except Exception:
                logger.exception("Final buffer TTS failed in confirmation")

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
