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
}


def get_live_tool_declarations() -> list[types.FunctionDeclaration]:
    """Return FunctionDeclaration list for Gemini Live API config."""
    return [
        types.FunctionDeclaration(
            name="search_knowledge_base",
            description=(
                "Turkcell bilgi tabaninda arama yapar. Tarife, paket, kampanya, "
                "teknik destek konularinda detayli bilgi bulmak icin kullan."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "query": types.Schema(
                        type=types.Type.STRING,
                        description="Turkce arama sorgusu",
                    ),
                },
                required=["query"],
            ),
        ),
        types.FunctionDeclaration(
            name="lookup_customer_bill",
            description=(
                "Musterinin fatura bilgilerini sorgular. Fatura detaylarini, "
                "tutarlarini ve odeme durumunu gosterir."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "customer_id": types.Schema(
                        type=types.Type.STRING,
                        description="Musteri ID'si (ornek: cust-001)",
                    ),
                },
                required=["customer_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="get_available_packages",
            description=(
                "Mevcut ek paketleri listeler. Tum aktif paketlerin adini, "
                "fiyatini ve ozelliklerini gosterir."
            ),
        ),
        types.FunctionDeclaration(
            name="get_available_tariffs",
            description=(
                "Mevcut tarifeleri listeler. Tum aktif tarifelerin adini, fiyatini, "
                "veri/arama/SMS limitlerini gosterir."
            ),
        ),
        types.FunctionDeclaration(
            name="recommend_tariff",
            description=(
                "Musterinin kullanim ve fatura verilerine gore en uygun tarife onerisi yapar. "
                "Son 3 ayin asim ucretlerini ve guncel kullanimini analiz ederek tasarruf "
                "saglayacak tarifeleri sirayla onerir. Musteri tarife degisikligi veya "
                "tasarruf hakkinda sorular sordigunda bu araci kullan."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "customer_id": types.Schema(
                        type=types.Type.STRING,
                        description="Musteri ID'si (ornek: cust-001)",
                    ),
                },
                required=["customer_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="compare_bills",
            description=(
                "Musterinin son 2 faturasini karsilastirir. Toplam tutar degisimini, "
                "asim ucretlerindeki farki ve artis/azalis nedenlerini gosterir. "
                "Musteri fatura degisimini, artisini veya azalisini sordugunda kullan."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "customer_id": types.Schema(
                        type=types.Type.STRING,
                        description="Musteri ID'si (ornek: cust-001)",
                    ),
                },
                required=["customer_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="check_usage_alerts",
            description=(
                "Musterinin kullanim durumunu kontrol eder: odenmemis fatura, veri/konusma "
                "asimi, limite yakin kullanim gibi uyarilari listeler. Musteri hesap durumunu, "
                "kullanimini veya uyarilari sordugunda kullan."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "customer_id": types.Schema(
                        type=types.Type.STRING,
                        description="Musteri ID'si (ornek: cust-001)",
                    ),
                },
                required=["customer_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="recommend_package",
            description=(
                "Musterinin kullanimina gore uygun ek paket onerir. Veri asimi veya yuksek "
                "kullanim durumunda tasarruf saglayacak paketleri sirayla sunar. "
                "Musteri paket onerisi veya ek paket sordugunda kullan."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "customer_id": types.Schema(
                        type=types.Type.STRING,
                        description="Musteri ID'si (ornek: cust-001)",
                    ),
                },
                required=["customer_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="activate_package",
            description=(
                "Musteri icin ek paket aktiflestirir. Paket tanimlama islemi yapar. "
                "Bu araci SADECE kullanici acikca bir paket tanimlamak istediginde kullan."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "customer_id": types.Schema(
                        type=types.Type.STRING,
                        description="Musteri ID'si (ornek: cust-001)",
                    ),
                    "package_id": types.Schema(
                        type=types.Type.STRING,
                        description="Aktif edilecek paket ID'si (ornek: pkg-002)",
                    ),
                },
                required=["customer_id", "package_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="change_tariff",
            description=(
                "Musterinin mevcut tarifesini degistirir. Tarife degisikligi islemi yapar. "
                "Bu araci SADECE kullanici acikca tarifesini degistirmek istediginde kullan."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "customer_id": types.Schema(
                        type=types.Type.STRING,
                        description="Musteri ID'si",
                    ),
                    "new_tariff_id": types.Schema(
                        type=types.Type.STRING,
                        description="Yeni tarife ID'si (ornek: tariff-003)",
                    ),
                },
                required=["customer_id", "new_tariff_id"],
            ),
        ),
        # --- MCP-backed personalization tools ---
        types.FunctionDeclaration(
            name="get_personalized_recommendations",
            description=(
                "Musterinin demografik profili, kullanim kaliplari, kayip riski ve piyasa "
                "verilerine gore coklu faktor analiziyle kisisellestirilmis tarife onerileri yapar. "
                "Detayli analiz, profil bazli oneri veya 'tum faktorleri degerlendir' gibi "
                "isteklerde bu araci kullan."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "customer_id": types.Schema(
                        type=types.Type.STRING,
                        description="Musteri ID'si (ornek: cust-001)",
                    ),
                    "top_n": types.Schema(
                        type=types.Type.INTEGER,
                        description="En fazla kac oneri donecegi (varsayilan: 3)",
                    ),
                },
                required=["customer_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="get_personalized_package_recommendations",
            description=(
                "Musterinin kullanim kaliplarina, demografik profiline ve uygulama kullanim "
                "dagilimina gore kisisellestirilmis ek paket onerileri yapar."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "customer_id": types.Schema(
                        type=types.Type.STRING,
                        description="Musteri ID'si (ornek: cust-001)",
                    ),
                    "top_n": types.Schema(
                        type=types.Type.INTEGER,
                        description="En fazla kac oneri donecegi (varsayilan: 3)",
                    ),
                },
                required=["customer_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="get_customer_risk_profile",
            description=(
                "Musterinin kayip (churn) olasiligini, musteri yasam boyu degerini (CLV), "
                "sadakat puanini ve ust satim/capraz satis potansiyelini analiz eder."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "customer_id": types.Schema(
                        type=types.Type.STRING,
                        description="Musteri ID'si (ornek: cust-001)",
                    ),
                },
                required=["customer_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="get_usage_pattern_analysis",
            description=(
                "Musterinin zaman bazli kullanim kaliplarini analiz eder: hafta ici/hafta sonu "
                "kullanim farki, saatlik yogunluk, aylik trend, uygulama kategorileri."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "customer_id": types.Schema(
                        type=types.Type.STRING,
                        description="Musteri ID'si (ornek: cust-001)",
                    ),
                },
                required=["customer_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="get_market_comparison",
            description=(
                "Belirtilen Turkcell tarifesini Vodafone ve Turk Telekom'un benzer "
                "tarifeleriyle karsilastirir. Fiyat, veri, dakika ve SMS limitlerini kiyaslar."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "tariff_id": types.Schema(
                        type=types.Type.STRING,
                        description="Tarife ID'si (ornek: tariff-001)",
                    ),
                },
                required=["tariff_id"],
            ),
        ),
        # --- Customer memory tools ---
        types.FunctionDeclaration(
            name="get_customer_memory",
            description=(
                "Musterinin onceki etkilesim hafizasini getirir. Onceki konusmalardan "
                "ogreniilen tercihleri, cozulmemis sorunlari ve yapilan islemleri gosterir. "
                "Musteri ile konusmaya baslarken bu araci kullanarak onceki deneyimi hatirla."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "customer_id": types.Schema(
                        type=types.Type.STRING,
                        description="Musteri ID'si (ornek: cust-001)",
                    ),
                },
                required=["customer_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="save_customer_memory",
            description=(
                "Musteri ile yapilan konusmanin ozetini kaydeder. Konusulan konulari, "
                "gerceklestirilen islemleri, cozulmemis sorunlari ve ogreniilen tercihleri "
                "saklar. Anlamli konusmalar sonrasinda otomatik olarak cagrilmalidir."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "customer_id": types.Schema(
                        type=types.Type.STRING,
                        description="Musteri ID'si (ornek: cust-001)",
                    ),
                    "summary": types.Schema(
                        type=types.Type.STRING,
                        description="Etkilesim ozeti (Turkce)",
                    ),
                    "topics": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(type=types.Type.STRING),
                        description="Konusulan konular",
                    ),
                    "actions_taken": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(type=types.Type.STRING),
                        description="Gerceklestirilen islemler",
                    ),
                    "unresolved_issues": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(type=types.Type.STRING),
                        description="Cozulmemis sorunlar",
                    ),
                    "preferences_learned": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(type=types.Type.STRING),
                        description="Ogreniilen tercihler",
                    ),
                    "sentiment": types.Schema(
                        type=types.Type.STRING,
                        description="Musteri duygu durumu: olumlu/notr/olumsuz",
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
            return json.dumps({"error": "RAG servisi mevcut degil"}, ensure_ascii=False)
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
                {"error": f"Musteri bulunamadi: {customer_id}"},
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
    if personalization_engine is not None:
        pe = personalization_engine
        if name == "get_personalized_recommendations":
            customer_id = args.get("customer_id", "")
            top_n = args.get("top_n", 3)
            result = pe.get_personalized_tariff_recommendations(customer_id, top_n)
            if not result:
                return json.dumps({"error": f"Musteri bulunamadi: {customer_id}"}, ensure_ascii=False)
            return result.model_dump_json()

        if name == "get_personalized_package_recommendations":
            customer_id = args.get("customer_id", "")
            top_n = args.get("top_n", 3)
            result = pe.get_personalized_package_recommendations(customer_id, top_n)
            if not result:
                return json.dumps({"error": f"Musteri bulunamadi: {customer_id}"}, ensure_ascii=False)
            return result.model_dump_json()

        if name == "get_customer_risk_profile":
            customer_id = args.get("customer_id", "")
            result = pe._churn_risk.get_risk_profile(customer_id)
            if not result:
                return json.dumps({"error": f"Musteri bulunamadi: {customer_id}"}, ensure_ascii=False)
            return result.model_dump_json()

        if name == "get_usage_pattern_analysis":
            customer_id = args.get("customer_id", "")
            result = pe._usage_pattern.get_usage_pattern(customer_id)
            if not result:
                return json.dumps({"error": f"Kullanim verisi yok: {customer_id}"}, ensure_ascii=False)
            return result.model_dump_json()

        if name == "get_market_comparison":
            tariff_id = args.get("tariff_id", "")
            result = pe._market_data.get_market_comparison(tariff_id)
            if not result:
                return json.dumps({"error": f"Tarife bulunamadi: {tariff_id}"}, ensure_ascii=False)
            return result.model_dump_json()

    # --- Customer memory tools ---
    if customer_memory_service is not None:
        if name == "get_customer_memory":
            customer_id = args.get("customer_id", "")
            result = await customer_memory_service.get_memory(customer_id)
            if not result:
                return json.dumps(
                    {"message": f"Musteri {customer_id} icin onceki etkilesim kaydi bulunamadi."},
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
                sentiment=args.get("sentiment", "notr"),
            )
            result = await customer_memory_service.save_interaction(customer_id, record)
            return result.model_dump_json()

    return json.dumps({"error": f"Bilinmeyen arac: {name}"}, ensure_ascii=False)


def build_action_description(name: str, args: dict[str, Any], mock_bss: MockBSSService) -> str:
    """Build a human-readable Turkish description for an action tool call."""
    if name == "activate_package":
        package_id = args.get("package_id", "")
        package = mock_bss.get_package(package_id) if hasattr(mock_bss, "get_package") else None
        if package:
            return (
                f"{package.name} paketi ({package.price_tl} TL, "
                f"{package.duration_days} gun) tanimlanacak."
            )
        return f"Paket {package_id} tanimlanacak."

    if name == "change_tariff":
        tariff_id = args.get("new_tariff_id", "")
        tariff = mock_bss.get_tariff(tariff_id) if hasattr(mock_bss, "get_tariff") else None
        if tariff:
            return (
                f"Tarife {tariff.name} ({tariff.monthly_price_tl} TL/ay) "
                f"olarak degistirilecek."
            )
        return f"Tarife {tariff_id} olarak degistirilecek."

    return f"{name} islemi gerceklestirilecek."
