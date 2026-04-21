"""LangChain tool definitions for Umay telecom agent.

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
        """Müşteri için ek paket aktifleştirir. Paket tanımlama işlemi yapar.
        Kullanıcı paket tanımlamak istediğinde veya önerilen paketi onayladığında
        ('olur', 'yapalım', 'tamam', 'evet' gibi) bu aracı kullan."""
        result = await mock_bss.activate_package(customer_id, package_id)
        return json.dumps(result, ensure_ascii=False)

    @tool("change_tariff", args_schema=ChangeTariffInput)
    async def change_tariff_tool(customer_id: str, new_tariff_id: str) -> str:
        """Müşterinin mevcut tarifesini değiştirir. Tarife değişikliği işlemi yapar.
        Kullanıcı tarifesini değiştirmek istediğinde veya önerilen tarife değişikliğini
        onayladığında ('olur', 'yapalım', 'tamam', 'evet' gibi) bu aracı kullan."""
        result = await mock_bss.change_tariff(customer_id, new_tariff_id)
        return json.dumps(result, ensure_ascii=False)

    @tool("lookup_customer_bill", args_schema=LookupBillInput)
    async def lookup_customer_bill_tool(customer_id: str) -> str:
        """Müşterinin fatura bilgilerini sorgular. Fatura detaylarını, tutarlarını ve ödeme durumunu gösterir."""
        customer = mock_bss.get_customer(customer_id)
        if not customer:
            return json.dumps(
                {"error": f"Müşteri bulunamadı: {customer_id}"},
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
        """Mevcut ek paketleri listeler. Tüm aktif paketlerin adını, fiyatını ve özelliklerini gösterir."""
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
        """Mevcut tarifeleri listeler. Tüm aktif tarifelerin adını, fiyatını, veri/arama/SMS limitlerini gösterir."""
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
        """Müşterinin kullanım ve fatura verilerine göre en uygun tarife önerisi yapar.
        Son 3 ayın aşım ücretlerini ve güncel kullanımını analiz ederek tasarruf
        sağlayacak tarifeleri sırayla önerir. Müşteri tarife değişikliği veya
        tasarruf hakkında sorular sorduğunda bu aracı kullan."""
        result = mock_bss.recommend_tariff(customer_id)
        return json.dumps(result, ensure_ascii=False)

    @tool("compare_bills", args_schema=CompareBillsInput)
    def compare_bills_tool(customer_id: str) -> str:
        """Müşterinin son 2 faturasını karşılaştırır. Toplam tutar değişimini,
        aşım ücretlerindeki farkı ve artış/azalış nedenlerini gösterir.
        Müşteri fatura değişimini, artışını veya azalışını sorduğunda kullan."""
        result = mock_bss.compare_bills(customer_id)
        return json.dumps(result, ensure_ascii=False)

    @tool("check_usage_alerts", args_schema=CheckUsageAlertsInput)
    def check_usage_alerts_tool(customer_id: str) -> str:
        """Müşterinin kullanım durumunu kontrol eder: ödenmemiş fatura, veri/konuşma
        aşımı, limite yakın kullanım gibi uyarıları listeler. Müşteri hesap durumunu,
        kullanımını veya uyarıları sorduğunda kullan."""
        alerts = mock_bss.get_proactive_alerts(customer_id)
        return json.dumps({"customer_id": customer_id, "alerts": alerts}, ensure_ascii=False)

    @tool("recommend_package", args_schema=RecommendPackageInput)
    def recommend_package_tool(customer_id: str) -> str:
        """Müşterinin kullanımına göre uygun ek paket önerir. Veri aşımı veya yüksek
        kullanım durumunda tasarruf sağlayacak paketleri sırayla sunar.
        Müşteri paket önerisi veya ek paket sorduğunda kullan."""
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
            """Müşterinin demografik profili, kullanım kalıpları, kayıp riski ve piyasa
            verilerine göre çoklu faktör analiziyle kişiselleştirilmiş tarife önerileri yapar.
            Detaylı analiz, profil bazlı öneri veya 'tüm faktörleri değerlendir' gibi
            isteklerde bu aracı kullan. Basit tarife önerisi için recommend_tariff yeterli."""
            result = pe.get_personalized_tariff_recommendations(customer_id, top_n)
            if not result:
                return json.dumps({"error": f"Müşteri bulunamadı: {customer_id}"}, ensure_ascii=False)
            return result.model_dump_json()

        @tool("get_personalized_package_recommendations", args_schema=PersonalizedPackageRecommendationInput)
        def get_personalized_package_recommendations_tool(customer_id: str, top_n: int = 3) -> str:
            """Müşterinin kullanım kalıplarına, demografik profiline ve uygulama kullanım
            dağılımına göre kişiselleştirilmiş ek paket önerileri yapar. Örneğin sosyal
            medya ağırlıklı kullanan genç müşteriye sosyal medya paketi, iş seyahati
            yapan profesyonele yurt dışı paketi önerir."""
            result = pe.get_personalized_package_recommendations(customer_id, top_n)
            if not result:
                return json.dumps({"error": f"Müşteri bulunamadı: {customer_id}"}, ensure_ascii=False)
            return result.model_dump_json()

        @tool("get_customer_risk_profile", args_schema=CustomerRiskProfileInput)
        def get_customer_risk_profile_tool(customer_id: str) -> str:
            """Müşterinin kayıp (churn) olasılığını, müşteri yaşam boyu değerini (CLV),
            sadakat puanını ve üst satım/çapraz satış potansiyelini analiz eder.
            Müşteri kaybı önleme veya memnuniyet artırma stratejileri için kullanılır."""
            result = pe._churn_risk.get_risk_profile(customer_id)
            if not result:
                return json.dumps({"error": f"Müşteri bulunamadı: {customer_id}"}, ensure_ascii=False)
            return result.model_dump_json()

        @tool("get_usage_pattern_analysis", args_schema=UsagePatternAnalysisInput)
        def get_usage_pattern_analysis_tool(customer_id: str) -> str:
            """Müşterinin zaman bazlı kullanım kalıplarını analiz eder: hafta içi/hafta sonu
            kullanım farkını, saatlik yoğunluk dağılımını, aylık trend analizini, en çok
            kullanılan uygulama kategorilerini ve mevsimsel değişimleri raporlar."""
            result = pe._usage_pattern.get_usage_pattern(customer_id)
            if not result:
                return json.dumps(
                    {"error": f"Müşteri bulunamadı veya kullanım verisi yok: {customer_id}"},
                    ensure_ascii=False,
                )
            return result.model_dump_json()

        @tool("get_market_comparison", args_schema=MarketComparisonInput)
        def get_market_comparison_tool(tariff_id: str) -> str:
            """Belirtilen Umay tarifesini rakip operatörlerin benzer tarifeleriyle
            karşılaştırır. Fiyat, veri, dakika ve SMS limitlerini kıyaslayarak Umay'in
            piyasa konumunu gösterir."""
            result = pe._market_data.get_market_comparison(tariff_id)
            if not result:
                return json.dumps({"error": f"Tarife bulunamadı: {tariff_id}"}, ensure_ascii=False)
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
            """Müşterinin önceki etkileşim hafızasını getirir. Müşteri tekrar
            aradığında önceki konuşmalardan öğrenilen tercihleri, çözülmemiş
            sorunları ve yapılan işlemleri gösterir. Müşteri ile konuşmaya
            başlarken bu aracı kullanarak önceki deneyimi hatırla."""
            result = await cms.get_memory(customer_id)
            if not result:
                return json.dumps(
                    {"message": f"Müşteri {customer_id} için önceki etkileşim kaydı bulunamadı."},
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
            sentiment: str = "nötr",
        ) -> str:
            """Müşteri ile yapılan konuşmanın özetini kaydeder. Konuşulan konuları,
            gerçekleştirilen işlemleri, çözülmemiş sorunları ve öğrenilen tercihleri
            saklar. Anlamlı konuşmalar sonrasında otomatik olarak çağrılmalıdır."""
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
