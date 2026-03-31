"""WebSocket /ws/voice endpoint for voice input/output pipeline."""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.models.voice_schemas import (
    VoiceTranscriptionResponse,
    VoiceTokenResponse,
    VoiceResponseEnd,
    VoiceAudioDone,
    VoiceErrorResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    """Handle voice interaction over WebSocket.

    Protocol:
      Client -> Server:
        JSON: {"type": "init", "session_id": "...", "customer_id": "..."}
        BINARY: <audio bytes from MediaRecorder (WebM/Opus)>

      Server -> Client:
        JSON: {"type": "transcription", "text": "..."}
        JSON: {"type": "token", "content": "..."}
        JSON: {"type": "response_end", "full_text": "..."}
        BINARY: <TTS audio bytes (MP3)>
        JSON: {"type": "audio_done"}
        JSON: {"type": "error", "message": "..."}
    """
    await websocket.accept()
    voice_service = websocket.app.state.voice_service

    if voice_service is None:
        await websocket.send_json(
            VoiceErrorResponse(
                message="Ses servisi kullanilamiyor. Lutfen daha sonra tekrar deneyin."
            ).model_dump()
        )
        await websocket.close(code=1011)
        return

    session_id: str | None = None
    customer_id: str | None = None

    try:
        while True:
            data = await websocket.receive()

            # Handle WebSocket disconnect message
            if data.get("type") == "websocket.disconnect":
                break

            if "text" in data:
                # JSON control message
                try:
                    msg = json.loads(data["text"])
                except json.JSONDecodeError:
                    await websocket.send_json(
                        VoiceErrorResponse(message="Gecersiz JSON mesaji.").model_dump()
                    )
                    continue

                if msg.get("type") == "init":
                    session_id = msg.get("session_id")
                    customer_id = msg.get("customer_id")
                    logger.info(
                        "Voice session initialized: session=%s customer=%s",
                        session_id,
                        customer_id,
                    )
                    continue

            elif "bytes" in data:
                # Binary frame = audio data from MediaRecorder
                audio_bytes = data["bytes"]

                if not session_id:
                    await websocket.send_json(
                        VoiceErrorResponse(
                            message="Oturum baslatilmadi. Lutfen sayfayi yenileyip tekrar deneyin."
                        ).model_dump()
                    )
                    continue

                if len(audio_bytes) < 100:
                    await websocket.send_json(
                        VoiceErrorResponse(
                            message="Ses algilanamadi. Lutfen mikrofonunuza yakin konusun ve tekrar deneyin."
                        ).model_dump()
                    )
                    continue

                try:
                    # Process through voice pipeline
                    result = await voice_service.process_voice(
                        audio_bytes, session_id, customer_id
                    )

                    # 1. Send transcription
                    await websocket.send_json(
                        VoiceTranscriptionResponse(
                            text=result["transcribed_text"]
                        ).model_dump()
                    )

                    # 2. Stream tokens
                    for token in result["tokens"]:
                        await websocket.send_json(
                            VoiceTokenResponse(content=token).model_dump()
                        )

                    # 3. Send response end
                    await websocket.send_json(
                        VoiceResponseEnd(
                            full_text=result["response_text"]
                        ).model_dump()
                    )

                    # 4. Send TTS audio if available
                    if result["audio_response"]:
                        await websocket.send_bytes(result["audio_response"])

                    # 5. Signal completion
                    await websocket.send_json(
                        VoiceAudioDone().model_dump()
                    )

                except Exception as e:
                    logger.exception("Voice pipeline error: %s", e)
                    await websocket.send_json(
                        VoiceErrorResponse(
                            message="Sesiniz islenirken bir hata olustu. Lutfen tekrar deneyin."
                        ).model_dump()
                    )

    except WebSocketDisconnect:
        logger.info("Voice WebSocket disconnected: session=%s", session_id)
