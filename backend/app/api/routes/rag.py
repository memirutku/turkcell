from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter()


class SearchRequest(BaseModel):
    """Request body for RAG search endpoint."""

    query: str = Field(..., min_length=1, max_length=1000, description="Turkish search query")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results")


class SearchResult(BaseModel):
    """A single search result from the RAG pipeline."""

    content: str
    metadata: dict
    score: float


class SearchResponse(BaseModel):
    """Response from the RAG search endpoint."""

    results: list[SearchResult]
    query: str
    total: int


@router.post("/rag/search", response_model=SearchResponse)
async def rag_search(body: SearchRequest, request: Request):
    """
    Umay dokuman havuzunda semantik arama yapar.

    Turkce sorguyu Gemini embedding ile vektorlestirip Milvus'ta
    en yakin dokuman parcalarini dondurur.
    """
    rag = request.app.state.rag
    if rag is None:
        raise HTTPException(
            status_code=503,
            detail="RAG servisi kullanilamiyor -- GEMINI_API_KEY ayarlanmamis",
        )
    results = await rag.search(body.query, top_k=body.top_k)
    return SearchResponse(
        results=[SearchResult(**r) for r in results],
        query=body.query,
        total=len(results),
    )
