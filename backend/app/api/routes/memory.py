"""MCP-exposed customer memory endpoints.

These REST endpoints are auto-discovered by fastapi-mcp via the "mcp-memory" tag
and exposed as MCP tools at /mcp/memory for external clients.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.models.customer_memory_schemas import InteractionRecord

router = APIRouter()


class GetMemoryRequest(BaseModel):
    customer_id: str


class SaveMemoryRequest(BaseModel):
    customer_id: str
    summary: str
    topics: list[str] = Field(default_factory=list)
    actions_taken: list[str] = Field(default_factory=list)
    unresolved_issues: list[str] = Field(default_factory=list)
    preferences_learned: list[str] = Field(default_factory=list)
    sentiment: str = "notr"


@router.post("/get-customer-memory")
async def get_customer_memory(body: GetMemoryRequest, request: Request):
    """Musterinin onceki etkilesim hafizasini getirir. Musteri tekrar
    aradiginda onceki konusmalardan ogreniilen tercihleri, cozulmemis
    sorunlari ve yapilan islemleri gosterir. Musteri ile konusmaya
    baslarken bu araci kullanarak onceki deneyimi hatirla."""
    svc = request.app.state.customer_memory_service
    result = await svc.get_memory(body.customer_id)
    if not result:
        return JSONResponse(
            status_code=404,
            content={"message": f"Musteri {body.customer_id} icin onceki etkilesim kaydi bulunamadi."},
        )
    return result.model_dump()


@router.post("/save-customer-memory")
async def save_customer_memory(body: SaveMemoryRequest, request: Request):
    """Musteri ile yapilan konusmanin ozetini kaydeder. Konusulan konulari,
    gerceklestirilen islemleri, cozulmemis sorunlari ve ogreniilen
    tercihleri saklar. Bir sonraki aramada musteri tanimasi icin kullanilir.
    Anlamli konusmalar sonrasinda otomatik olarak cagrilmalidir."""
    svc = request.app.state.customer_memory_service
    record = InteractionRecord(
        interaction_id=str(uuid.uuid4()),
        session_id="mcp-external",
        timestamp=datetime.now(timezone.utc),
        summary=body.summary,
        topics=body.topics,
        actions_taken=body.actions_taken,
        unresolved_issues=body.unresolved_issues,
        preferences_learned=body.preferences_learned,
        sentiment=body.sentiment,
    )
    result = await svc.save_interaction(body.customer_id, record)
    return result.model_dump()
