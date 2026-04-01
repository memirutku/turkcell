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
    VoiceActionProposal,
    VoiceActionResult,
    VoiceConfirmationPrompt,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    """Handle voice interaction over WebSocket with agent action support.

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
        JSON: {"type": "action_proposal", "action_type": "...", "description": "...", "details": {...}, "thread_id": "..."}
        JSON: {"type": "action_result", "success": bool, "action_type": "...", "description": "...", "details": {...}}
        JSON: {"type": "confirmation_prompt", "text": "..."}
        JSON: {"type": "error", "message": "..."}

    Audio chunks are sent incrementally at sentence boundaries for
    reduced perceived latency. The client queues and plays them in order.

    Agent action flow:
    1. VoiceService detects action proposal from AgentService
    2. Server sends action_proposal + confirmation_prompt + TTS audio
    3. Client sends next audio as confirmation (evet/hayir)
    4. Server routes through process_voice_confirmation()
    5. Server sends action_result + TTS result description
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
    pending_proposal: dict | None = None
    retry_count: int = 0

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
                    pending_proposal = None
                    retry_count = 0
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
                    # Choose pipeline based on confirmation state
                    if pending_proposal is not None:
                        # Awaiting confirmation -- route through confirmation handler
                        event_iter = voice_service.process_voice_confirmation(
                            audio_bytes, session_id, pending_proposal, retry_count
                        )
                    else:
                        # Normal voice processing (routes to agent if customer_id set)
                        event_iter = voice_service.process_voice_streaming(
                            audio_bytes, session_id, customer_id
                        )

                    async for event in event_iter:
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

                        elif event_type == "action_proposal":
                            proposal_data = event.get("data", {})
                            pending_proposal = proposal_data
                            retry_count = 0
                            await websocket.send_json(
                                VoiceActionProposal(
                                    action_type=proposal_data.get("action_type", ""),
                                    description=proposal_data.get("description", ""),
                                    details=proposal_data.get("details", {}),
                                    thread_id=proposal_data.get("thread_id", ""),
                                ).model_dump()
                            )

                        elif event_type == "action_result":
                            result_data = event.get("data", {})
                            pending_proposal = None
                            retry_count = 0
                            # Build ActionResult-compatible response
                            success = result_data.get("success", result_data.get("status") == "success")
                            action_type = result_data.get("action_type", "")
                            description = result_data.get("message_tr", result_data.get("description", ""))
                            details = {k: str(v) for k, v in result_data.items()
                                       if k not in ("success", "status", "action_type", "message_tr", "description", "error")}
                            await websocket.send_json(
                                VoiceActionResult(
                                    success=bool(success),
                                    action_type=action_type,
                                    description=description,
                                    details=details,
                                ).model_dump()
                            )

                        elif event_type == "confirmation_prompt":
                            await websocket.send_json(
                                VoiceConfirmationPrompt(text=event["text"]).model_dump()
                            )

                        elif event_type == "retry":
                            retry_count = event.get("retry_count", retry_count + 1)
                            # Keep pending_proposal -- still awaiting confirmation

                        elif event_type == "error":
                            pending_proposal = None
                            retry_count = 0
                            await websocket.send_json(
                                VoiceErrorResponse(
                                    message=event.get("message", "Bir hata olustu.")
                                ).model_dump()
                            )

                except Exception as e:
                    logger.exception("Voice pipeline error: %s", e)
                    pending_proposal = None
                    retry_count = 0
                    await websocket.send_json(
                        VoiceErrorResponse(
                            message="Sesiniz islenirken bir hata olustu. Lutfen tekrar deneyin."
                        ).model_dump()
                    )

    except WebSocketDisconnect:
        logger.info("Voice WebSocket disconnected: session=%s", session_id)
