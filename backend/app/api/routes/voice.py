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
        BINARY: <audio bytes from MediaRecorder (WebM/Opus or WAV)>

      Server -> Client:
        JSON: {"type": "transcription", "text": "..."}
        JSON: {"type": "token", "content": "..."}
        BINARY: <sentence-level TTS audio chunk (MP3)>  -- 0 or more
        JSON: {"type": "response_end", "full_text": "..."}
        JSON: {"type": "audio_done"}
        JSON: {"type": "error", "message": "..."}

    Audio chunks are sent incrementally at sentence boundaries for
    reduced perceived latency. The client queues and plays them in order.
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
                    # Process through streaming voice pipeline
                    # Yields incremental events: transcription, tokens,
                    # audio_chunks (sentence-level TTS), response_end, audio_done
                    async for event in voice_service.process_voice_streaming(
                        audio_bytes, session_id, customer_id
                    ):
                        event_type = event.get("type")

                        if event_type == "transcription":
                            await websocket.send_json(
                                VoiceTranscriptionResponse(text=event["text"]).model_dump()
                            )

                        elif event_type == "token":
                            await websocket.send_json(
                                VoiceTokenResponse(content=event["content"]).model_dump()
                            )

                        elif event_type == "audio_chunk":
                            # Send binary audio chunk for sentence-level TTS
                            await websocket.send_bytes(event["data"])

                        elif event_type == "response_end":
                            await websocket.send_json(
                                VoiceResponseEnd(full_text=event["full_text"]).model_dump()
                            )

                        elif event_type == "audio_done":
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
