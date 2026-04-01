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
    LookupBillInput,
)
from app.services.mock_bss import MockBSSService


def get_telecom_tools(mock_bss: MockBSSService) -> list:
    """Create tool instances bound to a MockBSSService instance.

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

    return [
        activate_package_tool,
        change_tariff_tool,
        lookup_customer_bill_tool,
        get_available_packages_tool,
        get_available_tariffs_tool,
    ]
