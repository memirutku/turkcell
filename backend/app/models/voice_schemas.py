"""Voice WebSocket message schemas for the voice pipeline."""

from pydantic import BaseModel


# Client -> Server (JSON text frames)


class VoiceInitMessage(BaseModel):
    """Initialize a voice session with session and optional customer ID."""

    type: str = "init"
    session_id: str
    customer_id: str | None = None


class VoiceStopMessage(BaseModel):
    """Signal end of voice recording."""

    type: str = "stop"


# Server -> Client (JSON text frames)


class VoiceTranscriptionResponse(BaseModel):
    """STT transcription result sent back to the client."""

    type: str = "transcription"
    text: str


class VoiceResponseStart(BaseModel):
    """Signal that LLM response streaming is beginning."""

    type: str = "response_start"


class VoiceTokenResponse(BaseModel):
    """A single LLM streaming token."""

    type: str = "token"
    content: str


class VoiceResponseEnd(BaseModel):
    """Signal that LLM response streaming is complete."""

    type: str = "response_end"
    full_text: str


class VoiceAudioChunk(BaseModel):
    """A sentence-level TTS audio chunk for incremental playback.

    Note: The actual audio bytes are sent as a separate binary WebSocket
    frame after this JSON signal. This schema documents the protocol type
    used in the streaming generator's yield dict.
    """

    type: str = "audio_chunk"


class VoiceAudioDone(BaseModel):
    """Signal that TTS audio has been sent."""

    type: str = "audio_done"


class VoiceErrorResponse(BaseModel):
    """Error message sent to the client."""

    type: str = "error"
    message: str


# Agent action message types (Phase 10: Voice-Agent integration)


class VoiceActionProposal(BaseModel):
    """Agent action proposal sent to the client for confirmation."""

    type: str = "action_proposal"
    action_type: str
    description: str
    details: dict
    thread_id: str


class VoiceActionResult(BaseModel):
    """Agent action execution result sent to the client."""

    type: str = "action_result"
    success: bool
    action_type: str
    description: str
    details: dict


class VoiceConfirmationPrompt(BaseModel):
    """TTS confirmation prompt text sent to the client."""

    type: str = "confirmation_prompt"
    text: str
