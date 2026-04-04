"""LangChain tool definitions for Turkcell telecom agent.

Tools are decorated with @tool and use Pydantic schemas for argument validation.
Turkish descriptions are critical -- Gemini needs Turkish context to route Turkish
queries to correct tools.
"""

import json

from langchain_core.tools import tool

from app.models.agent_schemas import (
    ActivatePackageInput,
    ChangeTariffInput,
    CheckUsageAlertsInput,
    CompareBillsInput,
    LookupBillInput,
    PersonalizedRecommendationInput,
    PersonalizedPackageRecommendationInput,
    CustomerRiskProfileInput,
    UsagePatternAnalysisInput,
    MarketComparisonInput,
    RecommendPackageInput,
    RecommendTariffInput,
)
from app.models.customer_memory_schemas import CustomerMemoryInput, GetCustomerMemoryInput
from app.services.mock_bss import MockBSSService


def get_telecom_tools(
    mock_bss: MockBSSService,
    personalization_engine=None,
    customer_memory_service=None,
) -> list:
    """Create tool instances bound to a MockBSSService instance.

    If *personalization_engine* is provided, includes 5 additional MCP-backed
    personalized recommendation tools.

    Returns a list of LangChain tool functions that can be passed to
    ChatGoogleGenerativeAI.bind_tools() and ToolNode().
    """

    @tool("activate_package", args_schema=ActivatePackageInput)
    async def activate_package_tool(customer_id: str, package_id: str) -> str:
        """Musteri icin ek paket aktiflestirir. Paket tanimlama islemi yapar.
        Bu araci SADECE kullanici acikca bir paket tanimlamak istediginde kullan."""
        result = await mock_bss.activate_package(customer_id, package_id)
        return json.dumps(result, ensure_ascii=False)

    @tool("change_tariff", args_schema=ChangeTariffInput)
    async def change_tariff_tool(customer_id: str, new_tariff_id: str) -> str:
        """Musterinin mevcut tarifesini degistirir. Tarife degisikligi islemi yapar.
        Bu araci SADECE kullanici acikca tarifesini degistirmek istediginde kullan."""
        result = await mock_bss.change_tariff(customer_id, new_tariff_id)
        return json.dumps(result, ensure_ascii=False)

    @tool("lookup_customer_bill", args_schema=LookupBillInput)
    async def lookup_customer_bill_tool(customer_id: str) -> str:
        """Musterinin fatura bilgilerini sorgular. Fatura detaylarini, tutarlarini ve odeme durumunu gosterir."""
        customer = mock_bss.get_customer(customer_id)
        if not customer:
            return json.dumps(
                {"error": f"Musteri bulunamadi: {customer_id}"},
                ensure_ascii=False,
            )
        bills = mock_bss.get_customer_bills(customer_id)
        usage = mock_bss.get_customer_usage(customer_id)
        result = {
            "customer_name": customer.name,
            "current_tariff": (
                customer.tariff.name if customer.tariff else "Bilinmiyor"
            ),
            "bills": [
                {
                    "period": b.period,
                    "total_amount_tl": str(b.total_amount_tl),
                    "is_paid": b.is_paid,
                    "due_date": b.due_date.isoformat(),
                }
                for b in bills[:3]  # Last 3 bills
            ],
            "usage": (
                {
                    "data_used_gb": usage.data_used_gb,
                    "data_limit_gb": usage.data_limit_gb,
                    "voice_used_minutes": usage.voice_used_minutes,
                    "voice_limit_minutes": usage.voice_limit_minutes,
                }
                if usage
                else None
            ),
        }
        return json.dumps(result, ensure_ascii=False)

    @tool("get_available_packages")
    def get_available_packages_tool() -> str:
        """Mevcut ek paketleri listeler. Tum aktif paketlerin adini, fiyatini ve ozelliklerini gosterir."""
        packages = mock_bss.get_packages()
        result = [
            {
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "price_tl": str(p.price_tl),
                "duration_days": p.duration_days,
                "description": p.description,
            }
            for p in packages
            if p.is_active
        ]
        return json.dumps(result, ensure_ascii=False)

    @tool("get_available_tariffs")
    def get_available_tariffs_tool() -> str:
        """Mevcut tarifeleri listeler. Tum aktif tarifelerin adini, fiyatini, veri/arama/SMS limitlerini gosterir."""
        tariffs = mock_bss.get_tariffs()
        result = [
            {
                "id": t.id,
                "name": t.name,
                "monthly_price_tl": str(t.monthly_price_tl),
                "data_gb": t.data_gb,
                "voice_minutes": t.voice_minutes,
                "sms_count": t.sms_count,
            }
            for t in tariffs
            if t.is_active
        ]
        return json.dumps(result, ensure_ascii=False)

    @tool("recommend_tariff", args_schema=RecommendTariffInput)
    def recommend_tariff_tool(customer_id: str) -> str:
        """Musterinin kullanim ve fatura verilerine gore en uygun tarife onerisi yapar.
        Son 3 ayin asim ucretlerini ve guncel kullanimini analiz ederek tasarruf
        saglayacak tarifeleri sirayla onerir. Musteri tarife degisikligi veya
        tasarruf hakkinda sorular sordigunda bu araci kullan."""
        result = mock_bss.recommend_tariff(customer_id)
        return json.dumps(result, ensure_ascii=False)

    @tool("compare_bills", args_schema=CompareBillsInput)
    def compare_bills_tool(customer_id: str) -> str:
        """Musterinin son 2 faturasini karsilastirir. Toplam tutar degisimini,
        asim ucretlerindeki farki ve artis/azalis nedenlerini gosterir.
        Musteri fatura degisimini, artisini veya azalisini sordugunda kullan."""
        result = mock_bss.compare_bills(customer_id)
        return json.dumps(result, ensure_ascii=False)

    @tool("check_usage_alerts", args_schema=CheckUsageAlertsInput)
    def check_usage_alerts_tool(customer_id: str) -> str:
        """Musterinin kullanim durumunu kontrol eder: odenmemis fatura, veri/konusma
        asimi, limite yakin kullanim gibi uyarilari listeler. Musteri hesap durumunu,
        kullanimini veya uyarilari sordugunda kullan."""
        alerts = mock_bss.get_proactive_alerts(customer_id)
        return json.dumps({"customer_id": customer_id, "alerts": alerts}, ensure_ascii=False)

    @tool("recommend_package", args_schema=RecommendPackageInput)
    def recommend_package_tool(customer_id: str) -> str:
        """Musterinin kullanimina gore uygun ek paket onerir. Veri asimi veya yuksek
        kullanim durumunda tasarruf saglayacak paketleri sirayla sunar.
        Musteri paket onerisi veya ek paket sordugunda kullan."""
        result = mock_bss.recommend_package(customer_id)
        return json.dumps(result, ensure_ascii=False)

    tools = [
        activate_package_tool,
        change_tariff_tool,
        lookup_customer_bill_tool,
        get_available_packages_tool,
        get_available_tariffs_tool,
        recommend_tariff_tool,
        compare_bills_tool,
        check_usage_alerts_tool,
        recommend_package_tool,
    ]

    # --- MCP-backed personalization tools (optional) ---
    if personalization_engine is not None:
        pe = personalization_engine

        @tool("get_personalized_recommendations", args_schema=PersonalizedRecommendationInput)
        def get_personalized_recommendations_tool(customer_id: str, top_n: int = 3) -> str:
            """Musterinin demografik profili, kullanim kaliplari, kayip riski ve piyasa
            verilerine gore coklu faktor analiziyle kisisellestirilmis tarife onerileri yapar.
            Detayli analiz, profil bazli oneri veya 'tum faktorleri degerlendir' gibi
            isteklerde bu araci kullan. Basit tarife onerisi icin recommend_tariff yeterli."""
            result = pe.get_personalized_tariff_recommendations(customer_id, top_n)
            if not result:
                return json.dumps({"error": f"Musteri bulunamadi: {customer_id}"}, ensure_ascii=False)
            return result.model_dump_json()

        @tool("get_personalized_package_recommendations", args_schema=PersonalizedPackageRecommendationInput)
        def get_personalized_package_recommendations_tool(customer_id: str, top_n: int = 3) -> str:
            """Musterinin kullanim kaliplarina, demografik profiline ve uygulama kullanim
            dagilimina gore kisisellestirilmis ek paket onerileri yapar. Ornegin sosyal
            medya agirlikli kullanan genc musteriye sosyal medya paketi, is seyahati
            yapan profesyonele yurt disi paketi onerir."""
            result = pe.get_personalized_package_recommendations(customer_id, top_n)
            if not result:
                return json.dumps({"error": f"Musteri bulunamadi: {customer_id}"}, ensure_ascii=False)
            return result.model_dump_json()

        @tool("get_customer_risk_profile", args_schema=CustomerRiskProfileInput)
        def get_customer_risk_profile_tool(customer_id: str) -> str:
            """Musterinin kayip (churn) olasiligini, musteri yasam boyu degerini (CLV),
            sadakat puanini ve ust satim/capraz satis potansiyelini analiz eder.
            Musteri kaybi onleme veya memnuniyet artirma stratejileri icin kullanilir."""
            result = pe._churn_risk.get_risk_profile(customer_id)
            if not result:
                return json.dumps({"error": f"Musteri bulunamadi: {customer_id}"}, ensure_ascii=False)
            return result.model_dump_json()

        @tool("get_usage_pattern_analysis", args_schema=UsagePatternAnalysisInput)
        def get_usage_pattern_analysis_tool(customer_id: str) -> str:
            """Musterinin zaman bazli kullanim kaliplarini analiz eder: hafta ici/hafta sonu
            kullanim farkini, saatlik yogunluk dagilimini, aylik trend analizini, en cok
            kullanilan uygulama kategorilerini ve mevsimsel degisimleri raporlar."""
            result = pe._usage_pattern.get_usage_pattern(customer_id)
            if not result:
                return json.dumps(
                    {"error": f"Musteri bulunamadi veya kullanim verisi yok: {customer_id}"},
                    ensure_ascii=False,
                )
            return result.model_dump_json()

        @tool("get_market_comparison", args_schema=MarketComparisonInput)
        def get_market_comparison_tool(tariff_id: str) -> str:
            """Belirtilen Turkcell tarifesini Vodafone ve Turk Telekom'un benzer tarifeleriyle
            karsilastirir. Fiyat, veri, dakika ve SMS limitlerini kiyaslayarak Turkcell'in
            piyasa konumunu gosterir."""
            result = pe._market_data.get_market_comparison(tariff_id)
            if not result:
                return json.dumps({"error": f"Tarife bulunamadi: {tariff_id}"}, ensure_ascii=False)
            return result.model_dump_json()

        tools.extend([
            get_personalized_recommendations_tool,
            get_personalized_package_recommendations_tool,
            get_customer_risk_profile_tool,
            get_usage_pattern_analysis_tool,
            get_market_comparison_tool,
        ])

    # --- Customer memory tools (optional) ---
    if customer_memory_service is not None:
        import uuid
        from datetime import datetime, timezone

        from app.models.customer_memory_schemas import InteractionRecord

        cms = customer_memory_service

        @tool("get_customer_memory", args_schema=GetCustomerMemoryInput)
        async def get_customer_memory_tool(customer_id: str) -> str:
            """Musterinin onceki etkilesim hafizasini getirir. Musteri tekrar
            aradiginda onceki konusmalardan ogreniilen tercihleri, cozulmemis
            sorunlari ve yapilan islemleri gosterir. Musteri ile konusmaya
            baslarken bu araci kullanarak onceki deneyimi hatirla."""
            result = await cms.get_memory(customer_id)
            if not result:
                return json.dumps(
                    {"message": f"Musteri {customer_id} icin onceki etkilesim kaydi bulunamadi."},
                    ensure_ascii=False,
                )
            return result.model_dump_json()

        @tool("save_customer_memory", args_schema=CustomerMemoryInput)
        async def save_customer_memory_tool(
            customer_id: str,
            summary: str,
            topics: list[str] | None = None,
            actions_taken: list[str] | None = None,
            unresolved_issues: list[str] | None = None,
            preferences_learned: list[str] | None = None,
            sentiment: str = "notr",
        ) -> str:
            """Musteri ile yapilan konusmanin ozetini kaydeder. Konusulan konulari,
            gerceklestirilen islemleri, cozulmemis sorunlari ve ogreniilen tercihleri
            saklar. Anlamli konusmalar sonrasinda otomatik olarak cagrilmalidir."""
            record = InteractionRecord(
                interaction_id=str(uuid.uuid4()),
                session_id="agent",
                timestamp=datetime.now(timezone.utc),
                summary=summary,
                topics=topics or [],
                actions_taken=actions_taken or [],
                unresolved_issues=unresolved_issues or [],
                preferences_learned=preferences_learned or [],
                sentiment=sentiment,
            )
            result = await cms.save_interaction(customer_id, record)
            return result.model_dump_json()

        tools.extend([get_customer_memory_tool, save_customer_memory_tool])

    return tools
