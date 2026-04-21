"""Gemini Live API tool declarations and dispatcher.

Translates existing LangChain @tool definitions into google.genai FunctionDeclaration
format for use with the Live API's native function calling.
"""

import json
import logging
from typing import Any

from google.genai import types

from app.services.mock_bss import MockBSSService
from app.services.personalization_engine import PersonalizationEngine
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

# Tool names requiring user confirmation before execution
ACTION_TOOLS = {"activate_package", "change_tariff"}

# Tool names that are safe to auto-execute
SAFE_TOOLS = {
    "search_knowledge_base",
    "lookup_customer_bill",
    "get_available_packages",
    "get_available_tariffs",
    "recommend_tariff",
    "compare_bills",
    "check_usage_alerts",
    "recommend_package",
    "get_personalized_recommendations",
    "get_personalized_package_recommendations",
    "get_customer_risk_profile",
    "get_usage_pattern_analysis",
    "get_market_comparison",
    "get_customer_memory",
    "save_customer_memory",
    "propose_action",
}


def get_live_tool_declarations() -> list[types.FunctionDeclaration]:
    """Return FunctionDeclaration list for Gemini Live API config."""
    return [
        types.FunctionDeclaration(
            name="search_knowledge_base",
            description=(
                "Umay bilgi tabanında arama yapar. Tarife, paket, kampanya, "
                "teknik destek konularında detaylı bilgi bulmak için kullan."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "query": types.Schema(
                        type=types.Type.STRING,
                        description="Türkçe arama sorgusu",
                    ),
                },
                required=["query"],
            ),
        ),
        types.FunctionDeclaration(
            name="lookup_customer_bill",
            description=(
                "Müşterinin fatura bilgilerini sorgular. Fatura detaylarını, "
                "tutarlarını ve ödeme durumunu gösterir."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "customer_id": types.Schema(
                        type=types.Type.STRING,
                        description="Müşteri ID'si (örnek: cust-001)",
                    ),
                },
                required=["customer_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="get_available_packages",
            description=(
                "Mevcut ek paketleri listeler. Tüm aktif paketlerin adını, "
                "fiyatını ve özelliklerini gösterir."
            ),
        ),
        types.FunctionDeclaration(
            name="get_available_tariffs",
            description=(
                "Mevcut tarifeleri listeler. Tüm aktif tarifelerin adını, fiyatını, "
                "veri/arama/SMS limitlerini gösterir."
            ),
        ),
        types.FunctionDeclaration(
            name="recommend_tariff",
            description=(
                "Müşterinin kullanım ve fatura verilerine göre en uygun tarife önerisi yapar. "
                "Son 3 ayın aşım ücretlerini ve güncel kullanımını analiz ederek tasarruf "
                "sağlayacak tarifeleri sırayla önerir. Müşteri tarife değişikliği veya "
                "tasarruf hakkında sorular sorduğunda bu aracı kullan."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "customer_id": types.Schema(
                        type=types.Type.STRING,
                        description="Müşteri ID'si (örnek: cust-001)",
                    ),
                },
                required=["customer_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="compare_bills",
            description=(
                "Müşterinin son 2 faturasını karşılaştırır. Toplam tutar değişimini, "
                "aşım ücretlerindeki farkı ve artış/azalış nedenlerini gösterir. "
                "Müşteri fatura değişimini, artışını veya azalışını sorduğunda kullan."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "customer_id": types.Schema(
                        type=types.Type.STRING,
                        description="Müşteri ID'si (örnek: cust-001)",
                    ),
                },
                required=["customer_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="check_usage_alerts",
            description=(
                "Müşterinin kullanım durumunu kontrol eder: ödenmemiş fatura, veri/konuşma "
                "aşımı, limite yakın kullanım gibi uyarıları listeler. Müşteri hesap durumunu, "
                "kullanımını veya uyarıları sorduğunda kullan."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "customer_id": types.Schema(
                        type=types.Type.STRING,
                        description="Müşteri ID'si (örnek: cust-001)",
                    ),
                },
                required=["customer_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="recommend_package",
            description=(
                "Müşterinin kullanımına göre uygun ek paket önerir. Veri aşımı veya yüksek "
                "kullanım durumunda tasarruf sağlayacak paketleri sırayla sunar. "
                "Müşteri paket önerisi veya ek paket sorduğunda kullan."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "customer_id": types.Schema(
                        type=types.Type.STRING,
                        description="Müşteri ID'si (örnek: cust-001)",
                    ),
                },
                required=["customer_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="activate_package",
            description=(
                "Müşteri için ek paket aktifleştirir. Paket tanımlama işlemi yapar. "
                "Kullanıcı paket tanımlamak istediğinde veya önerilen paketi onayladığında "
                "('olur', 'yapalım', 'tamam', 'evet' gibi) bu aracı kullan."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "customer_id": types.Schema(
                        type=types.Type.STRING,
                        description="Müşteri ID'si (örnek: cust-001)",
                    ),
                    "package_id": types.Schema(
                        type=types.Type.STRING,
                        description="Aktif edilecek paket ID'si (örnek: pkg-002)",
                    ),
                },
                required=["customer_id", "package_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="change_tariff",
            description=(
                "Müşterinin mevcut tarifesini değiştirir. Tarife değişikliği işlemi yapar. "
                "Kullanıcı tarifesini değiştirmek istediğinde veya önerilen tarife değişikliğini "
                "onayladığında ('olur', 'yapalım', 'tamam', 'evet' gibi) bu aracı kullan."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "customer_id": types.Schema(
                        type=types.Type.STRING,
                        description="Müşteri ID'si",
                    ),
                    "new_tariff_id": types.Schema(
                        type=types.Type.STRING,
                        description="Yeni tarife ID'si (örnek: tariff-003)",
                    ),
                },
                required=["customer_id", "new_tariff_id"],
            ),
        ),
        # --- MCP-backed personalization tools ---
        types.FunctionDeclaration(
            name="get_personalized_recommendations",
            description=(
                "Müşterinin demografik profili, kullanım kalıpları, kayıp riski ve piyasa "
                "verilerine göre çoklu faktör analiziyle kişiselleştirilmiş tarife önerileri yapar. "
                "Detaylı analiz, profil bazlı öneri veya 'tüm faktörleri değerlendir' gibi "
                "isteklerde bu aracı kullan."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "customer_id": types.Schema(
                        type=types.Type.STRING,
                        description="Müşteri ID'si (örnek: cust-001)",
                    ),
                    "top_n": types.Schema(
                        type=types.Type.INTEGER,
                        description="En fazla kaç öneri döneceği (varsayılan: 3)",
                    ),
                },
                required=["customer_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="get_personalized_package_recommendations",
            description=(
                "Müşterinin kullanım kalıplarına, demografik profiline ve uygulama kullanım "
                "dağılımına göre kişiselleştirilmiş ek paket önerileri yapar."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "customer_id": types.Schema(
                        type=types.Type.STRING,
                        description="Müşteri ID'si (örnek: cust-001)",
                    ),
                    "top_n": types.Schema(
                        type=types.Type.INTEGER,
                        description="En fazla kaç öneri döneceği (varsayılan: 3)",
                    ),
                },
                required=["customer_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="get_customer_risk_profile",
            description=(
                "Müşterinin kayıp (churn) olasılığını, müşteri yaşam boyu değerini (CLV), "
                "sadakat puanını ve üst satım/çapraz satış potansiyelini analiz eder."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "customer_id": types.Schema(
                        type=types.Type.STRING,
                        description="Müşteri ID'si (örnek: cust-001)",
                    ),
                },
                required=["customer_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="get_usage_pattern_analysis",
            description=(
                "M��şterinin zaman bazlı kullanım kalıplarını analiz eder: hafta içi/hafta sonu "
                "kullanım farkı, saatlik yoğunluk, aylık trend, uygulama kategorileri."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "customer_id": types.Schema(
                        type=types.Type.STRING,
                        description="Müşteri ID'si (örnek: cust-001)",
                    ),
                },
                required=["customer_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="get_market_comparison",
            description=(
                "Belirtilen Umay tarifesini rakip operatörlerin benzer "
                "tarifeleriyle karşılaştırır. Fiyat, veri, dakika ve SMS limitlerini kıyaslar."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "tariff_id": types.Schema(
                        type=types.Type.STRING,
                        description="Tarife ID'si (örnek: tariff-001)",
                    ),
                },
                required=["tariff_id"],
            ),
        ),
        # --- Propose action (visual info card before voice confirmation) ---
        types.FunctionDeclaration(
            name="propose_action",
            description=(
                "Müşteriye tarife veya paket değişikliği önermeden ÖNCE bu aracı çağır. "
                "Ekranda bilgi kartı gösterir. Bu aracı çağırdıktan sonra müşteriye sesli "
                "olarak onay sorusunu sor. Müşteri onaylarsa ilgili işlem aracını çağır."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "action_type": types.Schema(
                        type=types.Type.STRING,
                        description="İşlem türü: 'tariff_change' veya 'package_activation'",
                    ),
                    "name": types.Schema(
                        type=types.Type.STRING,
                        description="Tarife veya paket adı",
                    ),
                    "price": types.Schema(
                        type=types.Type.STRING,
                        description="Fiyat bilgisi (örnek: '299 TL/ay')",
                    ),
                    "features": types.Schema(
                        type=types.Type.STRING,
                        description="Kısa özellik özeti (örnek: '50GB internet, 1000dk konuşma')",
                    ),
                },
                required=["action_type", "name", "price"],
            ),
        ),
        # --- Customer memory tools ---
        types.FunctionDeclaration(
            name="get_customer_memory",
            description=(
                "Müşterinin önceki etkileşim hafızasını getirir. Önceki konuşmalardan "
                "öğrenilen tercihleri, çözülmemiş sorunları ve yapılan işlemleri gösterir. "
                "Müşteri ile konuşmaya başlarken bu aracı kullanarak önceki deneyimi hatırla."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "customer_id": types.Schema(
                        type=types.Type.STRING,
                        description="Müşteri ID'si (örnek: cust-001)",
                    ),
                },
                required=["customer_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="save_customer_memory",
            description=(
                "Müşteri ile yapılan konuşmanın özetini kaydeder. Konuşulan konuları, "
                "gerçekleştirilen işlemleri, çözülmemiş sorunları ve öğrenilen tercihleri "
                "saklar. Anlamlı konuşmalar sonrasında otomatik olarak çağrılmalıdır."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "customer_id": types.Schema(
                        type=types.Type.STRING,
                        description="Müşteri ID'si (örnek: cust-001)",
                    ),
                    "summary": types.Schema(
                        type=types.Type.STRING,
                        description="Etkileşim özeti (Türkçe)",
                    ),
                    "topics": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(type=types.Type.STRING),
                        description="Konuşulan konular",
                    ),
                    "actions_taken": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(type=types.Type.STRING),
                        description="Gerçekleştirilen işlemler",
                    ),
                    "unresolved_issues": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(type=types.Type.STRING),
                        description="Çözülmemiş sorunlar",
                    ),
                    "preferences_learned": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(type=types.Type.STRING),
                        description="Öğrenilen tercihler",
                    ),
                    "sentiment": types.Schema(
                        type=types.Type.STRING,
                        description="Müşteri duygu durumu: olumlu/nötr/olumsuz",
                    ),
                },
                required=["customer_id", "summary"],
            ),
        ),
    ]


def is_action_tool(name: str) -> bool:
    """Check if a tool requires user confirmation."""
    return name in ACTION_TOOLS


async def dispatch_tool(
    name: str,
    args: dict[str, Any],
    mock_bss: MockBSSService,
    rag_service: RAGService | None = None,
    personalization_engine: PersonalizationEngine | None = None,
    customer_memory_service=None,
) -> str:
    """Execute a tool call and return the JSON result string.

    For ACTION_TOOLS, this should only be called after user confirmation.
    """
    if name == "search_knowledge_base":
        if rag_service is None:
            return json.dumps({"error": "RAG servisi mevcut değil"}, ensure_ascii=False)
        query = args.get("query", "")
        results = await rag_service.search(query, top_k=5)
        return json.dumps(
            {"results": [{"content": r["content"], "source": r.get("metadata", {}).get("source", "")}
                         for r in results]},
            ensure_ascii=False,
        )

    if name == "lookup_customer_bill":
        customer_id = args.get("customer_id", "")
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
            "current_tariff": customer.tariff.name if customer.tariff else "Bilinmiyor",
            "bills": [
                {
                    "period": b.period,
                    "total_amount_tl": str(b.total_amount_tl),
                    "is_paid": b.is_paid,
                    "due_date": b.due_date.isoformat(),
                }
                for b in bills[:3]
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

    if name == "get_available_packages":
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

    if name == "get_available_tariffs":
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

    if name == "recommend_tariff":
        customer_id = args.get("customer_id", "")
        result = mock_bss.recommend_tariff(customer_id)
        return json.dumps(result, ensure_ascii=False)

    if name == "compare_bills":
        customer_id = args.get("customer_id", "")
        result = mock_bss.compare_bills(customer_id)
        return json.dumps(result, ensure_ascii=False)

    if name == "check_usage_alerts":
        customer_id = args.get("customer_id", "")
        alerts = mock_bss.get_proactive_alerts(customer_id)
        return json.dumps({"customer_id": customer_id, "alerts": alerts}, ensure_ascii=False)

    if name == "recommend_package":
        customer_id = args.get("customer_id", "")
        result = mock_bss.recommend_package(customer_id)
        return json.dumps(result, ensure_ascii=False)

    if name == "activate_package":
        customer_id = args.get("customer_id", "")
        package_id = args.get("package_id", "")
        result = await mock_bss.activate_package(customer_id, package_id)
        return json.dumps(result, ensure_ascii=False)

    if name == "change_tariff":
        customer_id = args.get("customer_id", "")
        new_tariff_id = args.get("new_tariff_id", "")
        result = await mock_bss.change_tariff(customer_id, new_tariff_id)
        return json.dumps(result, ensure_ascii=False)

    # --- MCP-backed personalization tools ---
    _personalization_tools = {
        "get_personalized_recommendations",
        "get_personalized_package_recommendations",
        "get_customer_risk_profile",
        "get_usage_pattern_analysis",
        "get_market_comparison",
    }
    if name in _personalization_tools:
        if personalization_engine is None:
            return json.dumps(
                {"error": "Kişiselleştirme servisi şu an kullanılamıyor. Basit öneri araçlarını deneyin."},
                ensure_ascii=False,
            )
        pe = personalization_engine
        if name == "get_personalized_recommendations":
            customer_id = args.get("customer_id", "")
            top_n = args.get("top_n", 3)
            result = pe.get_personalized_tariff_recommendations(customer_id, top_n)
            if not result:
                return json.dumps({"error": f"Müşteri bulunamadı: {customer_id}"}, ensure_ascii=False)
            return result.model_dump_json()

        if name == "get_personalized_package_recommendations":
            customer_id = args.get("customer_id", "")
            top_n = args.get("top_n", 3)
            result = pe.get_personalized_package_recommendations(customer_id, top_n)
            if not result:
                return json.dumps({"error": f"Müşteri bulunamadı: {customer_id}"}, ensure_ascii=False)
            return result.model_dump_json()

        if name == "get_customer_risk_profile":
            customer_id = args.get("customer_id", "")
            result = pe._churn_risk.get_risk_profile(customer_id)
            if not result:
                return json.dumps({"error": f"Müşteri bulunamadı: {customer_id}"}, ensure_ascii=False)
            return result.model_dump_json()

        if name == "get_usage_pattern_analysis":
            customer_id = args.get("customer_id", "")
            result = pe._usage_pattern.get_usage_pattern(customer_id)
            if not result:
                return json.dumps({"error": f"Kullanım verisi yok: {customer_id}"}, ensure_ascii=False)
            return result.model_dump_json()

        if name == "get_market_comparison":
            tariff_id = args.get("tariff_id", "")
            result = pe._market_data.get_market_comparison(tariff_id)
            if not result:
                return json.dumps({"error": f"Tarife bulunamadı: {tariff_id}"}, ensure_ascii=False)
            return result.model_dump_json()

    # --- Propose action (info card only, no execution) ---
    if name == "propose_action":
        return json.dumps(
            {"status": "proposed", "message": "Öneri kartı kullanıcıya gösterildi."},
            ensure_ascii=False,
        )

    # --- Customer memory tools ---
    _memory_tools = {"get_customer_memory", "save_customer_memory"}
    if name in _memory_tools:
        if customer_memory_service is None:
            return json.dumps(
                {"error": "Müşteri hafıza servisi şu an kullanılamıyor."},
                ensure_ascii=False,
            )
        if name == "get_customer_memory":
            customer_id = args.get("customer_id", "")
            result = await customer_memory_service.get_memory(customer_id)
            if not result:
                return json.dumps(
                    {"message": f"Müşteri {customer_id} için önceki etkileşim kaydı bulunamadı."},
                    ensure_ascii=False,
                )
            return result.model_dump_json()

        if name == "save_customer_memory":
            import uuid
            from datetime import datetime, timezone

            from app.models.customer_memory_schemas import InteractionRecord

            customer_id = args.get("customer_id", "")
            record = InteractionRecord(
                interaction_id=str(uuid.uuid4()),
                session_id="live",
                timestamp=datetime.now(timezone.utc),
                summary=args.get("summary", ""),
                topics=args.get("topics", []),
                actions_taken=args.get("actions_taken", []),
                unresolved_issues=args.get("unresolved_issues", []),
                preferences_learned=args.get("preferences_learned", []),
                sentiment=args.get("sentiment", "nötr"),
            )
            result = await customer_memory_service.save_interaction(customer_id, record)
            return result.model_dump_json()

    return json.dumps({"error": f"Bilinmeyen araç: {name}"}, ensure_ascii=False)


def build_action_description(name: str, args: dict[str, Any], mock_bss: MockBSSService) -> str:
    """Build a human-readable Turkish description for an action tool call."""
    if name == "activate_package":
        package_id = args.get("package_id", "")
        package = mock_bss.get_package(package_id) if hasattr(mock_bss, "get_package") else None
        if package:
            return (
                f"{package.name} paketi ({package.price_tl} TL, "
                f"{package.duration_days} gün) tanımlanacak."
            )
        return f"Paket {package_id} tanımlanacak."

    if name == "change_tariff":
        tariff_id = args.get("new_tariff_id", "")
        tariff = mock_bss.get_tariff(tariff_id) if hasattr(mock_bss, "get_tariff") else None
        if tariff:
            return (
                f"Tarife {tariff.name} ({tariff.monthly_price_tl} TL/ay) "
                f"olarak değiştirilecek."
            )
        return f"Tarife {tariff_id} olarak değiştirilecek."

    return f"{name} işlemi gerçekleştirilecek."
