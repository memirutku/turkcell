"""WebSocket /ws/voice-live endpoint for Gemini Live API real-time voice."""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/voice-live")
async def voice_live_websocket(websocket: WebSocket):
    """Handle real-time voice via Gemini Live API bidirectional session.

    Protocol:
      Client -> Server:
        JSON: {"type": "init", "session_id": "...", "customer_id": "..."}
        BINARY: <PCM16 audio frames (16kHz, mono, 16-bit signed LE)>
        JSON: {"type": "confirmation", "approved": true/false}

      Server -> Client:
        BINARY: <PCM16 audio chunks from Gemini>
        JSON: {"type": "input_transcript", "text": "..."}
        JSON: {"type": "output_transcript", "text": "..."}
        JSON: {"type": "text", "text": "..."}
        JSON: {"type": "turn_complete"}
        JSON: {"type": "interrupted"}
        JSON: {"type": "action_proposal", "action_type": "...", "description": "...", "details": {...}}
        JSON: {"type": "action_result", "success": bool, "action_type": "...", "description": "...", "details": {...}}
        JSON: {"type": "error", "message": "..."}

    Audio flows bidirectionally: browser sends mic PCM16, server forwards to
    Gemini Live API and relays Gemini's audio response back to the browser.
    Two concurrent tasks handle the two directions independently.
    """
    await websocket.accept()
    live_service = websocket.app.state.gemini_live_service

    if live_service is None:
        await websocket.send_json({
            "type": "error",
            "message": "Live API servisi kullanilamiyor. Lutfen daha sonra tekrar deneyin.",
        })
        await websocket.close(code=1011)
        return

    reader_task = None

    try:
        # Wait for init message
        init_data = await websocket.receive_text()
        try:
            init_msg = json.loads(init_data)
        except json.JSONDecodeError:
            await websocket.send_json({"type": "error", "message": "Gecersiz init mesaji."})
            await websocket.close(code=1008)
            return

        if init_msg.get("type") != "init":
            await websocket.send_json({"type": "error", "message": "Ilk mesaj init olmali."})
            await websocket.close(code=1008)
            return

        session_id = init_msg.get("session_id", "")
        customer_id = init_msg.get("customer_id")

        if not session_id:
            await websocket.send_json({"type": "error", "message": "session_id gerekli."})
            await websocket.close(code=1008)
            return

        # Create Gemini Live API session (async context manager)
        try:
            async with live_service.create_session(session_id, customer_id) as live_session:
                # Task: Read Gemini responses and forward to browser
                async def gemini_to_browser():
                    try:
                        async for event in live_service.read_responses(live_session):
                            event_type = event.get("type")

                            if event_type == "audio":
                                await websocket.send_bytes(event["data"])
                            elif event_type in (
                                "text",
                                "input_transcript",
                                "output_transcript",
                                "turn_complete",
                                "interrupted",
                                "action_proposal",
                                "action_result",
                                "error",
                            ):
                                await websocket.send_json(event)
                    except Exception as e:
                        if not live_session.is_closed:
                            logger.exception("Gemini->browser relay error: %s", e)
                    finally:
                        logger.info(
                            "gemini_to_browser task ending: session=%s closed=%s",
                            live_session.session_id,
                            live_session.is_closed,
                        )

                reader_task = asyncio.create_task(gemini_to_browser())

                # Trigger initial greeting so the AI speaks first
                await live_service.send_greeting(live_session)

                # Main loop: Read from browser, forward to Gemini
                try:
                    while True:
                        data = await websocket.receive()

                        if data.get("type") == "websocket.disconnect":
                            break

                        # Health check: ensure reader task is still alive
                        if reader_task and reader_task.done():
                            exc = reader_task.exception() if not reader_task.cancelled() else None
                            if exc:
                                logger.error("Reader task died: %s", exc, exc_info=exc)
                            else:
                                logger.warning("Reader task completed unexpectedly")
                            await websocket.send_json({
                                "type": "error",
                                "message": "Ses yanit okuyucusu beklenmedik sekilde durdu.",
                            })
                            break

                        if "bytes" in data:
                            # Binary frame = PCM16 audio from mic
                            await live_service.send_audio(live_session, data["bytes"])

                        elif "text" in data:
                            # JSON control message
                            try:
                                msg = json.loads(data["text"])
                            except json.JSONDecodeError:
                                continue

                            if msg.get("type") == "confirmation":
                                approved = msg.get("approved", False)
                                async for event in live_service.handle_confirmation(
                                    live_session, approved
                                ):
                                    event_type = event.get("type")
                                    if event_type == "audio":
                                        await websocket.send_bytes(event["data"])
                                    else:
                                        await websocket.send_json(event)
                finally:
                    # Cleanup reader task before exiting context manager
                    if reader_task and not reader_task.done():
                        reader_task.cancel()
                        try:
                            await reader_task
                        except (asyncio.CancelledError, Exception):
                            pass

        except WebSocketDisconnect:
            raise  # Let outer handler deal with disconnect
        except Exception as e:
            logger.exception("Failed to create/run Live API session: %s", e)
            try:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Live API oturumu olusturulamadi: {e}",
                })
                await websocket.close(code=1011)
            except Exception:
                pass  # WebSocket may already be closed
            return

    except WebSocketDisconnect:
        logger.info("Live voice WebSocket disconnected")
    except Exception as e:
        logger.exception("Live voice WebSocket error: %s", e)
