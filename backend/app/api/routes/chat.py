"""POST /api/chat SSE streaming endpoint for Umay AI assistant."""

import json
import logging

from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from app.models.chat_schemas import ChatRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat")
async def chat_stream(body: ChatRequest, request: Request):
    """Stream a chat response from the Umay AI assistant via SSE.

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
            async for item in chat_service.stream_response(
                body.message, body.session_id, body.customer_id
            ):
                if isinstance(item, str):
                    yield {
                        "event": "token",
                        "data": json.dumps({"content": item}, ensure_ascii=False),
                    }
                elif isinstance(item, dict) and item.get("type") == "structured":
                    yield {
                        "event": "structured",
                        "data": json.dumps(item["data"], ensure_ascii=False),
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
