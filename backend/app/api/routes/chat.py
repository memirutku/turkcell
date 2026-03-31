"""POST /api/chat SSE streaming endpoint for Turkcell AI assistant."""

import json
import logging

from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from app.models.chat_schemas import ChatRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat")
async def chat_stream(body: ChatRequest, request: Request):
    """Stream a chat response from the Turkcell AI assistant via SSE.

    Accepts a user message and session ID, then streams LLM response tokens
    as Server-Sent Events with event types: token, done, error.
    """
    chat_service = request.app.state.chat_service
    if chat_service is None:
        raise HTTPException(
            status_code=503,
            detail="Chat servisi kullanilamiyor. Lutfen daha sonra tekrar deneyin.",
        )

    async def event_generator():
        try:
            async for token in chat_service.stream_response(
                body.message, body.session_id
            ):
                yield {
                    "event": "token",
                    "data": json.dumps({"content": token}, ensure_ascii=False),
                }
            yield {
                "event": "done",
                "data": json.dumps({"status": "complete"}, ensure_ascii=False),
            }
        except Exception as e:
            logger.error("Chat stream error: %s", e)
            yield {
                "event": "error",
                "data": json.dumps(
                    {"message": "Bir hata olustu. Lutfen tekrar deneyin."},
                    ensure_ascii=False,
                ),
            }

    return EventSourceResponse(event_generator())
