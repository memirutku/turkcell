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


class VoiceAudioDone(BaseModel):
    """Signal that TTS audio has been sent."""

    type: str = "audio_done"


class VoiceErrorResponse(BaseModel):
    """Error message sent to the client."""

    type: str = "error"
    message: str
