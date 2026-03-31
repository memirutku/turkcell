import time
from typing import Annotated

import redis.asyncio as redis
from fastapi import Depends, Request
from pymilvus import connections, utility

from app.config import Settings, get_settings
from app.services.mock_bss import MockBSSService
from app.services.rag_service import RAGService


async def get_redis_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> redis.Redis:
    """Get async Redis client."""
    return redis.from_url(settings.redis_url, decode_responses=True)


async def check_redis(
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    """Check Redis connectivity and measure latency."""
    try:
        client = redis.from_url(settings.redis_url, decode_responses=True)
        start = time.monotonic()
        await client.ping()
        latency = round((time.monotonic() - start) * 1000, 1)
        await client.aclose()
        return {"status": "connected", "latency_ms": latency}
    except Exception as e:
        return {"status": "disconnected", "error": str(e)}


async def check_milvus(
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    """Check Milvus connectivity and measure latency."""
    try:
        start = time.monotonic()
        connections.connect(
            alias="health_check",
            host=settings.milvus_host,
            port=settings.milvus_port,
            timeout=5,
        )
        utility.list_collections(using="health_check")
        latency = round((time.monotonic() - start) * 1000, 1)
        connections.disconnect("health_check")
        return {"status": "connected", "latency_ms": latency}
    except Exception as e:
        return {"status": "disconnected", "error": str(e)}


def get_mock_bss(request: Request) -> MockBSSService:
    """Get the MockBSSService from app state."""
    return request.app.state.mock_bss


def get_rag_service(request: Request) -> RAGService | None:
    """Get the RAGService from app state. Returns None if not configured."""
    return getattr(request.app.state, "rag", None)
