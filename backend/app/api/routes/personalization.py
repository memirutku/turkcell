"""MCP-exposed personalization endpoints.

These REST endpoints are auto-discovered by fastapi-mcp via the "mcp" tag
and exposed as MCP tools for external clients (Claude Desktop, Cursor, etc.).
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

router = APIRouter()


class CustomerRequest(BaseModel):
    customer_id: str
    top_n: int = Field(default=3, ge=1, le=10)


class CustomerIdRequest(BaseModel):
    customer_id: str


class TariffIdRequest(BaseModel):
    tariff_id: str


@router.post("/tariff-recommendations")
async def get_personalized_tariff_recommendations(body: CustomerRequest, request: Request):
    """Musterinin demografik profili, kullanim kaliplari, kayip riski ve
    piyasa verilerine gore kisisellestirilmis tarife onerileri olusturur.
    Basit tarife karsilastirmasinin otesinde, musterinin yasam tarzina en
    uygun tarife seceneklerini coklu faktor analiziyle sirayla sunar."""
    engine = request.app.state.personalization_engine
    result = engine.get_personalized_tariff_recommendations(body.customer_id, body.top_n)
    if not result:
        return JSONResponse(
            status_code=404,
            content={"error": f"Musteri bulunamadi: {body.customer_id}"},
        )
    return result.model_dump()


@router.post("/package-recommendations")
async def get_personalized_package_recommendations(body: CustomerRequest, request: Request):
    """Musterinin kullanim kaliplarina, demografik profiline ve uygulama
    kullanim dagilimina gore kisisellestirilmis ek paket onerileri yapar.
    Ornegin sosyal medya agirlikli kullanan genc musteriye sosyal medya
    paketi, is seyahati yapan profesyonele yurt disi paketi onerir."""
    engine = request.app.state.personalization_engine
    result = engine.get_personalized_package_recommendations(body.customer_id, body.top_n)
    if not result:
        return JSONResponse(
            status_code=404,
            content={"error": f"Musteri bulunamadi: {body.customer_id}"},
        )
    return result.model_dump()


@router.post("/customer-risk-profile")
async def get_customer_risk_profile(body: CustomerIdRequest, request: Request):
    """Musterinin kayip (churn) olasiligini, musteri yasam boyu degerini
    (CLV), sadakat puanini ve ust satim/capraz satis potansiyelini analiz
    eder. Musteri kaybi onleme veya memnuniyet artirma stratejileri icin
    kullanilir."""
    engine = request.app.state.personalization_engine
    result = engine._churn_risk.get_risk_profile(body.customer_id)
    if not result:
        return JSONResponse(
            status_code=404,
            content={"error": f"Musteri bulunamadi: {body.customer_id}"},
        )
    return result.model_dump()


@router.post("/usage-pattern-analysis")
async def get_usage_pattern_analysis(body: CustomerIdRequest, request: Request):
    """Musterinin zaman bazli kullanim kaliplarini analiz eder: hafta ici/
    hafta sonu kullanim farkini, saatlik yogunluk dagilimini, aylik trend
    analizini, en cok kullanilan uygulama kategorilerini ve mevsimsel
    degisimleri raporlar."""
    engine = request.app.state.personalization_engine
    result = engine._usage_pattern.get_usage_pattern(body.customer_id)
    if not result:
        return JSONResponse(
            status_code=404,
            content={"error": f"Musteri bulunamadi veya kullanim verisi yok: {body.customer_id}"},
        )
    return result.model_dump()


@router.post("/market-comparison")
async def get_market_comparison(body: TariffIdRequest, request: Request):
    """Belirtilen Turkcell tarifesini Vodafone ve Turk Telekom'un benzer
    tarifeleriyle karsilastirir. Fiyat, veri, dakika ve SMS limitlerini
    kiyaslayarak Turkcell'in piyasa konumunu gosterir."""
    engine = request.app.state.personalization_engine
    result = engine._market_data.get_market_comparison(body.tariff_id)
    if not result:
        return JSONResponse(
            status_code=404,
            content={"error": f"Tarife bulunamadi: {body.tariff_id}"},
        )
    return result.model_dump()
