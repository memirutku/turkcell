import asyncio
import json
import logging
import random
from datetime import datetime
from pathlib import Path

from app.models.schemas import (
    Bill,
    Campaign,
    Customer,
    CustomerDetail,
    Package,
    Tariff,
    UsageData,
)

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "mock"


class MockBSSService:
    """
    Mock BSS/OSS service that loads telecom data from JSON files.
    Designed to be replaced with real BSS/OSS integration in v2.
    """

    def __init__(self):
        self._customers: dict[str, Customer] = {}
        self._bills: dict[str, list[Bill]] = {}       # customer_id -> bills
        self._usage: dict[str, UsageData] = {}         # customer_id -> usage
        self._tariffs: dict[str, Tariff] = {}
        self._packages: dict[str, Package] = {}
        self._campaigns: dict[str, Campaign] = {}
        self._customer_profiles: dict[str, dict] = {}  # customer_id -> profile
        self._usage_patterns: dict[str, dict] = {}     # customer_id -> usage pattern
        self._market_data: dict = {}                    # market data
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def customer_count(self) -> int:
        return len(self._customers)

    @property
    def tariff_count(self) -> int:
        return len(self._tariffs)

    def load_data(self) -> None:
        """Load all mock data from JSON files."""
        # Load tariffs
        with open(DATA_DIR / "tariffs.json", encoding="utf-8") as f:
            for item in json.load(f):
                tariff = Tariff(**item)
                self._tariffs[tariff.id] = tariff

        # Load packages
        with open(DATA_DIR / "packages.json", encoding="utf-8") as f:
            for item in json.load(f):
                pkg = Package(**item)
                self._packages[pkg.id] = pkg

        # Load campaigns
        with open(DATA_DIR / "campaigns.json", encoding="utf-8") as f:
            for item in json.load(f):
                campaign = Campaign(**item)
                self._campaigns[campaign.id] = campaign

        # Load customers (with embedded bills and usage)
        with open(DATA_DIR / "customers.json", encoding="utf-8") as f:
            for item in json.load(f):
                bills_data = item.pop("bills", [])
                usage_data = item.pop("usage", None)

                customer = Customer(**item)
                self._customers[customer.id] = customer

                self._bills[customer.id] = [Bill(**b) for b in bills_data]

                if usage_data:
                    self._usage[customer.id] = UsageData(**usage_data)

        # Load customer profiles (demographics)
        profiles_path = DATA_DIR / "customer_profiles.json"
        if profiles_path.exists():
            with open(profiles_path, encoding="utf-8") as f:
                for item in json.load(f):
                    cid = item["customer_id"]
                    self._customer_profiles[cid] = item
                    # Merge demographic fields into Customer model if present
                    if cid in self._customers:
                        customer = self._customers[cid]
                        if item.get("birth_date"):
                            customer.birth_date = datetime.strptime(
                                item["birth_date"], "%Y-%m-%d"
                            ).date()
                        customer.occupation = item.get("occupation")
                        customer.segment = item.get("segment")
                        customer.contract_type = item.get("contract_type", "bireysel")

        # Load usage patterns
        patterns_path = DATA_DIR / "usage_patterns.json"
        if patterns_path.exists():
            with open(patterns_path, encoding="utf-8") as f:
                for item in json.load(f):
                    self._usage_patterns[item["customer_id"]] = item

        # Load market data
        market_path = DATA_DIR / "market_data.json"
        if market_path.exists():
            with open(market_path, encoding="utf-8") as f:
                self._market_data = json.load(f)

        self._loaded = True
        logger.info(
            "Mock data loaded: %d customers, %d tariffs, %d packages, %d campaigns, "
            "%d profiles, %d usage patterns",
            len(self._customers),
            len(self._tariffs),
            len(self._packages),
            len(self._campaigns),
            len(self._customer_profiles),
            len(self._usage_patterns),
        )

    # --- Customer methods ---

    def get_customer(self, customer_id: str) -> CustomerDetail | None:
        customer = self._customers.get(customer_id)
        if not customer:
            return None
        tariff = self._tariffs.get(customer.tariff_id)
        return CustomerDetail(**customer.model_dump(), tariff=tariff)

    def get_customer_bills(self, customer_id: str) -> list[Bill]:
        return self._bills.get(customer_id, [])

    def get_customer_bill(self, customer_id: str, bill_id: str) -> Bill | None:
        bills = self._bills.get(customer_id, [])
        return next((b for b in bills if b.id == bill_id), None)

    def get_customer_usage(self, customer_id: str) -> UsageData | None:
        return self._usage.get(customer_id)

    # --- Tariff methods ---

    def get_tariffs(self) -> list[Tariff]:
        return list(self._tariffs.values())

    def get_tariff(self, tariff_id: str) -> Tariff | None:
        return self._tariffs.get(tariff_id)

    # --- Package methods ---

    def get_packages(self) -> list[Package]:
        return list(self._packages.values())

    def get_package(self, package_id: str) -> Package | None:
        return self._packages.get(package_id)

    # --- Campaign methods ---

    def get_campaigns(self) -> list[Campaign]:
        return list(self._campaigns.values())

    # --- Personalization data accessors ---

    def get_customer_profile(self, customer_id: str) -> dict | None:
        return self._customer_profiles.get(customer_id)

    def get_usage_pattern(self, customer_id: str) -> dict | None:
        return self._usage_patterns.get(customer_id)

    def get_market_data(self) -> dict:
        return self._market_data

    # --- Action methods (async, with realistic delays) ---

    async def activate_package(self, customer_id: str, package_id: str) -> dict:
        """Activate an add-on package for a customer. Simulates BSS processing delay."""
        await asyncio.sleep(random.uniform(0.5, 1.5))

        customer = self._customers.get(customer_id)
        if not customer:
            return {"success": False, "error": f"Musteri bulunamadi: {customer_id}"}

        package = self._packages.get(package_id)
        if not package:
            return {"success": False, "error": f"Paket bulunamadi: {package_id}"}

        return {
            "success": True,
            "transaction_id": f"TXN-{random.randint(100000, 999999)}",
            "timestamp": datetime.now().isoformat(),
            "customer_id": customer_id,
            "package": {
                "id": package.id,
                "name": package.name,
                "price_tl": str(package.price_tl),
                "duration_days": package.duration_days,
            },
            "message_tr": (
                f"{package.name} basariyla aktiflestirildi. "
                f"Ucret: {package.price_tl} TL, Sure: {package.duration_days} gun."
            ),
        }

    def recommend_tariff(self, customer_id: str) -> dict:
        """Analyze customer usage/billing and recommend the best tariff.

        Looks at:
        - Last 3 months overage charges
        - Current usage (data, voice, SMS)
        - All available tariffs
        Returns top recommendations with savings estimate.
        """
        customer = self._customers.get(customer_id)
        if not customer:
            return {"error": f"Musteri bulunamadi: {customer_id}"}

        current_tariff = self._tariffs.get(customer.tariff_id)
        if not current_tariff:
            return {"error": "Mevcut tarife bulunamadi"}

        bills = self._bills.get(customer_id, [])
        usage = self._usage.get(customer_id)

        # Calculate average monthly overage from bills
        overage_totals = []
        for bill in bills[-3:]:
            overage = sum(
                float(item.amount_tl)
                for item in bill.line_items
                if item.category == "overage"
            )
            overage_totals.append(overage)

        avg_overage = sum(overage_totals) / len(overage_totals) if overage_totals else 0.0
        current_effective_cost = float(current_tariff.monthly_price_tl) + avg_overage

        # Estimate actual usage needs from current usage + overage pattern
        avg_data_need = float(usage.data_used_gb) if usage else float(current_tariff.data_gb)
        avg_voice_need = float(usage.voice_used_minutes) if usage else float(current_tariff.voice_minutes)
        avg_sms_need = float(usage.sms_used) if usage else float(current_tariff.sms_count)

        # Score each tariff
        recommendations = []
        for tariff in self._tariffs.values():
            if not tariff.is_active or tariff.id == current_tariff.id:
                continue

            tariff_price = float(tariff.monthly_price_tl)

            # Estimate overage on this tariff
            data_overage_gb = max(0, avg_data_need - tariff.data_gb)
            voice_overage_min = max(0, avg_voice_need - tariff.voice_minutes)
            # Rough overage pricing: ~25 TL/GB data, ~0.5 TL/min voice
            estimated_overage = data_overage_gb * 25.0 + voice_overage_min * 0.5
            estimated_cost = tariff_price + estimated_overage

            savings = current_effective_cost - estimated_cost
            covers_data = tariff.data_gb >= avg_data_need
            covers_voice = tariff.voice_minutes >= avg_voice_need
            covers_sms = tariff.sms_count >= avg_sms_need

            recommendations.append({
                "tariff_id": tariff.id,
                "tariff_name": tariff.name,
                "monthly_price_tl": str(tariff.monthly_price_tl),
                "data_gb": tariff.data_gb,
                "voice_minutes": tariff.voice_minutes,
                "sms_count": tariff.sms_count,
                "estimated_monthly_cost_tl": f"{estimated_cost:.2f}",
                "estimated_monthly_savings_tl": f"{savings:.2f}",
                "covers_data_need": covers_data,
                "covers_voice_need": covers_voice,
                "covers_sms_need": covers_sms,
            })

        # Sort: best savings first, but prioritize tariffs that cover all needs
        recommendations.sort(
            key=lambda r: (
                not (r["covers_data_need"] and r["covers_voice_need"]),
                -float(r["estimated_monthly_savings_tl"]),
            )
        )

        return {
            "customer_id": customer_id,
            "customer_name": customer.name,
            "current_tariff": {
                "id": current_tariff.id,
                "name": current_tariff.name,
                "monthly_price_tl": str(current_tariff.monthly_price_tl),
                "data_gb": current_tariff.data_gb,
                "voice_minutes": current_tariff.voice_minutes,
            },
            "avg_monthly_overage_tl": f"{avg_overage:.2f}",
            "current_effective_monthly_cost_tl": f"{current_effective_cost:.2f}",
            "usage_summary": {
                "avg_data_gb": round(avg_data_need, 1),
                "avg_voice_minutes": round(avg_voice_need),
                "avg_sms": round(avg_sms_need),
            },
            "recommendations": recommendations[:2],
        }

    def get_proactive_alerts(self, customer_id: str) -> list[dict]:
        """Check for proactive alerts: unpaid bills, overages, near-limit usage."""
        customer = self._customers.get(customer_id)
        if not customer:
            return []

        alerts: list[dict] = []

        # Unpaid bills
        bills = self._bills.get(customer_id, [])
        unpaid = [b for b in bills if not b.is_paid]
        for bill in unpaid:
            alerts.append({
                "type": "unpaid_bill",
                "severity": "high",
                "message": (
                    f"{bill.period} donemi faturaniz ({bill.total_amount_tl} TL) "
                    f"henuz odenmedi. Son odeme tarihi: {bill.due_date}."
                ),
            })

        # Usage alerts
        usage = self._usage.get(customer_id)
        if usage:
            # Data overage
            if usage.data_overage_gb > 0:
                alerts.append({
                    "type": "data_overage",
                    "severity": "high",
                    "message": (
                        f"Veri limitinizi {usage.data_overage_gb} GB astiniz. "
                        f"Kullanim: {usage.data_used_gb}/{usage.data_limit_gb} GB."
                    ),
                })
            # Data near limit (>80%)
            elif usage.data_limit_gb > 0:
                pct = usage.data_used_gb / usage.data_limit_gb * 100
                if pct >= 80:
                    alerts.append({
                        "type": "data_near_limit",
                        "severity": "medium",
                        "message": (
                            f"Veri kullaniminiz %{pct:.0f} seviyesinde. "
                            f"{usage.data_used_gb}/{usage.data_limit_gb} GB kullandiniz."
                        ),
                    })

            # Voice overage
            if usage.voice_overage_minutes > 0:
                alerts.append({
                    "type": "voice_overage",
                    "severity": "high",
                    "message": (
                        f"Konusma limitinizi {usage.voice_overage_minutes} dakika astiniz."
                    ),
                })
            elif usage.voice_limit_minutes > 0:
                pct = usage.voice_used_minutes / usage.voice_limit_minutes * 100
                if pct >= 80:
                    alerts.append({
                        "type": "voice_near_limit",
                        "severity": "medium",
                        "message": (
                            f"Konusma kullaniminiz %{pct:.0f} seviyesinde. "
                            f"{usage.voice_used_minutes}/{usage.voice_limit_minutes} dakika."
                        ),
                    })

        return alerts

    def compare_bills(self, customer_id: str) -> dict:
        """Compare the last 2 bills: total change, overage change, reasons."""
        customer = self._customers.get(customer_id)
        if not customer:
            return {"error": f"Musteri bulunamadi: {customer_id}"}

        bills = self._bills.get(customer_id, [])
        sorted_bills = sorted(bills, key=lambda b: b.period, reverse=True)

        if len(sorted_bills) < 2:
            return {"error": "Karsilastirma icin en az 2 fatura gerekli."}

        current = sorted_bills[0]
        previous = sorted_bills[1]

        curr_total = float(current.total_amount_tl)
        prev_total = float(previous.total_amount_tl)
        diff = curr_total - prev_total
        pct_change = (diff / prev_total * 100) if prev_total > 0 else 0

        def sum_by_category(bill, cat):
            return sum(float(i.amount_tl) for i in bill.line_items if i.category == cat)

        curr_overage = sum_by_category(current, "overage")
        prev_overage = sum_by_category(previous, "overage")

        # Identify change reasons
        reasons = []
        overage_diff = curr_overage - prev_overage
        if abs(overage_diff) > 0.01:
            if overage_diff > 0:
                reasons.append(f"Asim ucretleri {overage_diff:.2f} TL artti")
            else:
                reasons.append(f"Asim ucretleri {abs(overage_diff):.2f} TL azaldi")

        # Check for new line items in current that weren't in previous
        prev_descs = {i.description for i in previous.line_items}
        for item in current.line_items:
            if item.description not in prev_descs and item.category != "tax":
                reasons.append(f"Yeni kalem: {item.description} ({item.amount_tl} TL)")

        return {
            "customer_id": customer_id,
            "current_period": current.period,
            "previous_period": previous.period,
            "current_total_tl": f"{curr_total:.2f}",
            "previous_total_tl": f"{prev_total:.2f}",
            "difference_tl": f"{diff:+.2f}",
            "percent_change": f"{pct_change:+.1f}%",
            "current_overage_tl": f"{curr_overage:.2f}",
            "previous_overage_tl": f"{prev_overage:.2f}",
            "change_reasons": reasons if reasons else ["Onemli bir degisiklik yok"],
            "current_is_paid": current.is_paid,
            "previous_is_paid": previous.is_paid,
        }

    def recommend_package(self, customer_id: str) -> dict:
        """Recommend add-on packages based on customer usage patterns."""
        customer = self._customers.get(customer_id)
        if not customer:
            return {"error": f"Musteri bulunamadi: {customer_id}"}

        usage = self._usage.get(customer_id)
        bills = self._bills.get(customer_id, [])

        # Calculate average overage from recent bills
        overage_totals = []
        for bill in bills[-3:]:
            overage = sum(
                float(item.amount_tl)
                for item in bill.line_items
                if item.category == "overage"
            )
            overage_totals.append(overage)
        avg_overage = sum(overage_totals) / len(overage_totals) if overage_totals else 0.0

        recommendations = []

        # Data-related packages
        has_data_issue = (
            (usage and usage.data_overage_gb > 0)
            or (usage and usage.data_limit_gb > 0 and usage.data_used_gb / usage.data_limit_gb >= 0.8)
        )

        if has_data_issue:
            for pkg in self._packages.values():
                if not pkg.is_active or pkg.category not in ("ek_data", "sosyal_medya"):
                    continue
                pkg_price = float(pkg.price_tl)
                reason = ""
                savings = 0.0
                if pkg.category == "ek_data" and avg_overage > 0:
                    savings = avg_overage - pkg_price
                    reason = (
                        f"Aylik ortalama {avg_overage:.0f} TL asim ucretiniz var. "
                        f"Bu paketle tahmini {max(0, savings):.0f} TL tasarruf edebilirsiniz."
                    )
                elif pkg.category == "sosyal_medya":
                    reason = (
                        "Sosyal medya kullaniminiz tarifenizden yemez, "
                        "veri kullaniminizi azaltabilir."
                    )
                recommendations.append({
                    "package_id": pkg.id,
                    "package_name": pkg.name,
                    "price_tl": str(pkg.price_tl),
                    "duration_days": pkg.duration_days,
                    "category": pkg.category,
                    "reason": reason,
                    "estimated_savings_tl": f"{max(0, savings):.2f}",
                })

        # Sort: highest savings first
        recommendations.sort(key=lambda r: -float(r["estimated_savings_tl"]))

        return {
            "customer_id": customer_id,
            "has_data_issue": has_data_issue,
            "avg_monthly_overage_tl": f"{avg_overage:.2f}",
            "usage_summary": (
                {
                    "data_used_gb": usage.data_used_gb,
                    "data_limit_gb": usage.data_limit_gb,
                    "data_overage_gb": usage.data_overage_gb,
                }
                if usage
                else None
            ),
            "recommendations": recommendations[:2],
        }

    async def change_tariff(self, customer_id: str, new_tariff_id: str) -> dict:
        """Change a customer's tariff plan. Simulates BSS processing delay."""
        await asyncio.sleep(random.uniform(0.5, 1.5))

        customer = self._customers.get(customer_id)
        if not customer:
            return {"success": False, "error": f"Musteri bulunamadi: {customer_id}"}

        new_tariff = self._tariffs.get(new_tariff_id)
        if not new_tariff:
            return {"success": False, "error": f"Tarife bulunamadi: {new_tariff_id}"}

        old_tariff = self._tariffs.get(customer.tariff_id)

        # Update customer's tariff in-place
        customer.tariff_id = new_tariff_id

        return {
            "success": True,
            "transaction_id": f"TXN-{random.randint(100000, 999999)}",
            "timestamp": datetime.now().isoformat(),
            "customer_id": customer_id,
            "old_tariff": (
                {
                    "id": old_tariff.id,
                    "name": old_tariff.name,
                    "monthly_price_tl": str(old_tariff.monthly_price_tl),
                }
                if old_tariff
                else None
            ),
            "new_tariff": {
                "id": new_tariff.id,
                "name": new_tariff.name,
                "monthly_price_tl": str(new_tariff.monthly_price_tl),
            },
            "message_tr": f"Tarifiniz {new_tariff.name} olarak basariyla degistirildi.",
        }
