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
    """Müşterinin demografik profili, kullanım kalıpları, kayıp riski ve
    piyasa verilerine göre kişiselleştirilmiş tarife önerileri oluşturur.
    Basit tarife karşılaştırmasının ötesinde, müşterinin yaşam tarzına en
    uygun tarife seçeneklerini çoklu faktör analiziyle sırayla sunar."""
    engine = request.app.state.personalization_engine
    result = engine.get_personalized_tariff_recommendations(body.customer_id, body.top_n)
    if not result:
        return JSONResponse(
            status_code=404,
            content={"error": f"Müşteri bulunamadı: {body.customer_id}"},
        )
    return result.model_dump()


@router.post("/package-recommendations")
async def get_personalized_package_recommendations(body: CustomerRequest, request: Request):
    """Müşterinin kullanım kalıplarına, demografik profiline ve uygulama
    kullanım dağılımına göre kişiselleştirilmiş ek paket önerileri yapar.
    Örneğin sosyal medya ağırlıklı kullanan genç müşteriye sosyal medya
    paketi, iş seyahati yapan profesyonele yurt dışı paketi önerir."""
    engine = request.app.state.personalization_engine
    result = engine.get_personalized_package_recommendations(body.customer_id, body.top_n)
    if not result:
        return JSONResponse(
            status_code=404,
            content={"error": f"Müşteri bulunamadı: {body.customer_id}"},
        )
    return result.model_dump()


@router.post("/customer-risk-profile")
async def get_customer_risk_profile(body: CustomerIdRequest, request: Request):
    """Müşterinin kayıp (churn) olasılığını, müşteri yaşam boyu değerini
    (CLV), sadakat puanını ve üst satım/çapraz satış potansiyelini analiz
    eder. Müşteri kaybı önleme veya memnuniyet artırma stratejileri için
    kullanılır."""
    engine = request.app.state.personalization_engine
    result = engine._churn_risk.get_risk_profile(body.customer_id)
    if not result:
        return JSONResponse(
            status_code=404,
            content={"error": f"Müşteri bulunamadı: {body.customer_id}"},
        )
    return result.model_dump()


@router.post("/usage-pattern-analysis")
async def get_usage_pattern_analysis(body: CustomerIdRequest, request: Request):
    """Müşterinin zaman bazlı kullanım kalıplarını analiz eder: hafta içi/
    hafta sonu kullanım farkını, saatlik yoğunluk dağılımını, aylık trend
    analizini, en çok kullanılan uygulama kategorilerini ve mevsimsel
    değişimleri raporlar."""
    engine = request.app.state.personalization_engine
    result = engine._usage_pattern.get_usage_pattern(body.customer_id)
    if not result:
        return JSONResponse(
            status_code=404,
            content={"error": f"Müşteri bulunamadı veya kullanım verisi yok: {body.customer_id}"},
        )
    return result.model_dump()


@router.post("/market-comparison")
async def get_market_comparison(body: TariffIdRequest, request: Request):
    """Belirtilen Umay tarifesini rakip operatörlerin benzer
    tarifeleriyle karşılaştırır. Fiyat, veri, dakika ve SMS limitlerini
    kıyaslayarak Umay'in piyasa konumunu gösterir."""
    engine = request.app.state.personalization_engine
    result = engine._market_data.get_market_comparison(body.tariff_id)
    if not result:
        return JSONResponse(
            status_code=404,
            content={"error": f"Tarife bulunamadı: {body.tariff_id}"},
        )
    return result.model_dump()
