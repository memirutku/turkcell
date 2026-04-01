"""POST /api/agent/chat and POST /api/agent/confirm endpoints for agentic workflows."""

import json
import logging

from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from app.models.agent_schemas import AgentChatRequest, AgentConfirmRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/agent/chat")
async def agent_chat_stream(body: AgentChatRequest, request: Request):
    """Stream an agentic chat response via SSE.

    Handles both simple Q&A and multi-step agent workflows.
    For action-requiring requests, emits action_proposal event and closes stream.
    Frontend then sends POST /api/agent/confirm to resume.

    SSE event types:
    - token: LLM text streaming
    - action_proposal: Agent proposes an action, waiting for confirmation
    - action_result: Action execution result
    - done: Stream complete
    - error: Error occurred
    """
    agent_service = request.app.state.agent_service
    if agent_service is None:
        raise HTTPException(
            status_code=503,
            detail="Agent servisi kullanilamiyor. Lutfen daha sonra tekrar deneyin.",
        )

    async def event_generator():
        try:
            async for event in agent_service.stream(
                body.message, body.session_id, body.customer_id
            ):
                event_type = event.get("type", "unknown")
                if event_type == "token":
                    yield {
                        "event": "token",
                        "data": json.dumps({"content": event["content"]}, ensure_ascii=False),
                    }
                elif event_type == "action_proposal":
                    yield {
                        "event": "action_proposal",
                        "data": json.dumps(event["data"], ensure_ascii=False),
                    }
                elif event_type == "action_result":
                    yield {
                        "event": "action_result",
                        "data": json.dumps(event["data"], ensure_ascii=False),
                    }
                elif event_type == "error":
                    yield {
                        "event": "error",
                        "data": json.dumps(
                            {"message": event["content"]}, ensure_ascii=False
                        ),
                    }
            yield {
                "event": "done",
                "data": json.dumps({"status": "complete"}, ensure_ascii=False),
            }
        except Exception as e:
            logger.error("Agent chat stream error: %s", e)
            yield {
                "event": "error",
                "data": json.dumps(
                    {"message": "Asistan yanit verirken bir sorun olustu. Lutfen tekrar deneyin."},
                    ensure_ascii=False,
                ),
            }

    return EventSourceResponse(event_generator())


@router.post("/agent/confirm")
async def agent_confirm_stream(body: AgentConfirmRequest, request: Request):
    """Resume agent after user confirmation/rejection.

    Opens a new SSE stream for the execution result.
    The thread_id maps to the LangGraph checkpointed state.
    """
    agent_service = request.app.state.agent_service
    if agent_service is None:
        raise HTTPException(
            status_code=503,
            detail="Agent servisi kullanilamiyor. Lutfen daha sonra tekrar deneyin.",
        )

    config = {"configurable": {"thread_id": body.thread_id}}

    async def event_generator():
        try:
            async for event in agent_service.resume(
                config, {"approved": body.approved}
            ):
                event_type = event.get("type", "unknown")
                if event_type == "token":
                    yield {
                        "event": "token",
                        "data": json.dumps({"content": event["content"]}, ensure_ascii=False),
                    }
                elif event_type == "action_result":
                    yield {
                        "event": "action_result",
                        "data": json.dumps(event["data"], ensure_ascii=False),
                    }
                elif event_type == "error":
                    yield {
                        "event": "error",
                        "data": json.dumps(
                            {"message": event["content"]}, ensure_ascii=False
                        ),
                    }
            yield {
                "event": "done",
                "data": json.dumps({"status": "complete"}, ensure_ascii=False),
            }
        except Exception as e:
            logger.error("Agent confirm stream error: %s", e)
            yield {
                "event": "error",
                "data": json.dumps(
                    {"message": "Onay islemi sirasinda bir sorun olustu. Lutfen tekrar deneyin."},
                    ensure_ascii=False,
                ),
            }

    return EventSourceResponse(event_generator())
