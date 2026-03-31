"""TariffRecommendationService: deterministic tariff recommendation engine (Phase 6 - BILL-05, BILL-06).

All monetary calculations use Decimal arithmetic. The LLM never computes
savings -- this service pre-calculates everything and injects it as context.
"""

import logging
from decimal import ROUND_HALF_UP, Decimal

from app.models.recommendation_schemas import (
    RecommendationResult,
    TariffRecommendation,
    UsageSummary,
)
from app.models.schemas import Bill, Tariff, UsageData
from app.services.billing_context import BillingContextService
from app.services.mock_bss import MockBSSService

logger = logging.getLogger(__name__)

# Tax rates (Turkish telecom)
KDV_RATE = Decimal("0.20")  # Katma Deger Vergisi (VAT)
OIV_RATE = Decimal("0.15")  # Ozel Iletisim Vergisi (Special Communication Tax)

# Overage rates (fallback values)
DATA_OVERAGE_RATE_PER_GB = Decimal("20.00")
VOICE_OVERAGE_RATE_PER_MIN = Decimal("0.50")

_TWO_PLACES = Decimal("0.01")


class TariffRecommendationService:
    """Produces personalized tariff recommendations based on customer usage data.

    Uses MockBSSService for customer, usage, bill, and tariff data.
    All monetary calculations use Decimal to avoid floating-point errors.
    """

    def __init__(self, mock_bss: MockBSSService) -> None:
        self._bss = mock_bss

    def get_recommendations(
        self, customer_id: str, top_n: int = 3
    ) -> RecommendationResult | None:
        """Generate tariff recommendations for a customer.

        Args:
            customer_id: Customer identifier.
            top_n: Maximum number of recommendations to return.

        Returns:
            RecommendationResult with sorted recommendations, or None if customer not found.
        """
        # 1. Get customer
        customer = self._bss.get_customer(customer_id)
        if customer is None:
            return None

        # 2. Get usage
        usage = self._bss.get_customer_usage(customer_id)
        bills = self._bss.get_customer_bills(customer_id)

        # Build usage summary (even with empty data for edge cases)
        if usage is None:
            # No usage data -- return result with empty recommendations
            return RecommendationResult(
                customer_id=customer_id,
                current_tariff_name=customer.tariff.name if customer.tariff else "Bilinmiyor",
                current_effective_cost_tl=Decimal("0.00"),
                recommendations=[],
                usage_summary=UsageSummary(
                    data_used_gb=0.0,
                    data_limit_gb=0,
                    data_percent=0.0,
                    voice_used_minutes=0,
                    voice_limit_minutes=0,
                    voice_percent=0.0,
                    sms_used=0,
                    sms_limit=0,
                    sms_percent=0.0,
                    has_overage=False,
                    overage_cost_tl=Decimal("0.00"),
                ),
            )

        # 3. Get all tariffs
        all_tariffs = self._bss.get_tariffs()

        # 4. Calculate current effective monthly cost from bill history
        current_effective_cost = self._calculate_effective_monthly_cost(bills)

        # 5. Current tariff ID
        current_tariff_id = customer.tariff.id if customer.tariff else None

        # 6. For each active tariff (excluding current), project cost and savings
        recommendations: list[TariffRecommendation] = []
        current_tariff = customer.tariff

        for tariff in all_tariffs:
            if not tariff.is_active:
                continue
            if tariff.id == current_tariff_id:
                continue

            projected_cost = self._project_cost_on_tariff(tariff, usage)
            savings = (current_effective_cost - projected_cost).quantize(
                _TWO_PLACES, rounding=ROUND_HALF_UP
            )

            # Only recommend tariffs that save money
            if savings <= 0:
                continue

            fit_score = self._calculate_fit_score(tariff, usage)
            reasons = self._generate_reasons(
                tariff, usage, current_tariff, savings
            )

            recommendations.append(
                TariffRecommendation(
                    tariff=tariff,
                    monthly_savings_tl=savings,
                    projected_monthly_cost_tl=projected_cost,
                    current_monthly_cost_tl=current_effective_cost,
                    fit_score=fit_score,
                    reasons=reasons,
                )
            )

        # 7. Sort by savings descending, then fit_score descending
        recommendations.sort(
            key=lambda r: (r.monthly_savings_tl, r.fit_score), reverse=True
        )

        # 8. Limit to top_n
        recommendations = recommendations[:top_n]

        # 9. Build usage summary
        usage_summary = self._build_usage_summary(usage, bills)

        return RecommendationResult(
            customer_id=customer_id,
            current_tariff_name=current_tariff.name if current_tariff else "Bilinmiyor",
            current_effective_cost_tl=current_effective_cost,
            recommendations=recommendations,
            usage_summary=usage_summary,
        )

    def _calculate_effective_monthly_cost(self, bills: list[Bill]) -> Decimal:
        """Average of last 3 bills' total_amount_tl.

        Uses Decimal division and quantizes to 2 decimal places.
        """
        if not bills:
            return Decimal("0.00")

        # Sort by period descending to get the most recent bills
        sorted_bills = sorted(bills, key=lambda b: b.period, reverse=True)
        recent_bills = sorted_bills[:3]

        total = sum(b.total_amount_tl for b in recent_bills)
        avg = (total / Decimal(str(len(recent_bills)))).quantize(
            _TWO_PLACES, rounding=ROUND_HALF_UP
        )
        return avg

    def _project_cost_on_tariff(
        self, tariff: Tariff, usage: UsageData
    ) -> Decimal:
        """Project what this customer would pay on a given tariff.

        Applies base price + overage charges + KDV (20%) + OIV (15%).
        """
        base = tariff.monthly_price_tl

        # Data overage
        data_overage = Decimal("0.00")
        if usage.data_used_gb > tariff.data_gb:
            excess_gb = Decimal(str(usage.data_used_gb - tariff.data_gb))
            data_overage = (excess_gb * DATA_OVERAGE_RATE_PER_GB).quantize(
                _TWO_PLACES, rounding=ROUND_HALF_UP
            )

        # Voice overage
        voice_overage = Decimal("0.00")
        if usage.voice_used_minutes > tariff.voice_minutes:
            excess_min = Decimal(
                str(usage.voice_used_minutes - tariff.voice_minutes)
            )
            voice_overage = (excess_min * VOICE_OVERAGE_RATE_PER_MIN).quantize(
                _TWO_PLACES, rounding=ROUND_HALF_UP
            )

        subtotal = base + data_overage + voice_overage

        # Apply taxes
        kdv = (subtotal * KDV_RATE).quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)
        oiv = (subtotal * OIV_RATE).quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)

        return (subtotal + kdv + oiv).quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)

    def _calculate_fit_score(
        self, tariff: Tariff, usage: UsageData
    ) -> float:
        """Calculate how well this tariff fits the customer's usage pattern.

        Weighted score (0.0-1.0):
        - data_fit (0.5 weight): penalizes under-provisioning
        - voice_fit (0.3 weight): penalizes under-provisioning
        - sms_fit (0.2 weight): penalizes under-provisioning
        Over-provisioning penalty: slight reduction if tariff > 2x usage.
        """
        data_used = max(usage.data_used_gb, 1.0)
        voice_used = max(usage.voice_used_minutes, 1)
        sms_used = max(usage.sms_used, 1)

        data_fit = min(1.0, tariff.data_gb / data_used)
        voice_fit = min(1.0, tariff.voice_minutes / voice_used)
        sms_fit = min(1.0, tariff.sms_count / sms_used)

        # Penalize over-provisioning slightly
        if tariff.data_gb > data_used * 2:
            data_fit = max(0.0, data_fit - 0.1)

        score = data_fit * 0.5 + voice_fit * 0.3 + sms_fit * 0.2
        return round(min(1.0, max(0.0, score)), 2)

    def _generate_reasons(
        self,
        tariff: Tariff,
        usage: UsageData,
        current_tariff: Tariff | None,
        savings: Decimal,
    ) -> list[str]:
        """Generate Turkish reason strings explaining why this tariff is recommended."""
        reasons: list[str] = []

        # Data overage elimination
        if current_tariff and usage.data_used_gb > current_tariff.data_gb and tariff.data_gb >= usage.data_used_gb:
            reasons.append(
                f"Veri kullaniminiz ({usage.data_used_gb} GB) mevcut limitinizi "
                f"({current_tariff.data_gb} GB) asiyor, bu tarifede asim olmaz"
            )

        # Voice overage elimination
        if current_tariff and usage.voice_used_minutes > current_tariff.voice_minutes and tariff.voice_minutes >= usage.voice_used_minutes:
            reasons.append(
                f"Arama kullaniminiz ({usage.voice_used_minutes} dk) mevcut limitinizi "
                f"({current_tariff.voice_minutes} dk) asiyor, bu tarifede asim olmaz"
            )

        # Savings
        if savings > 0:
            savings_text = BillingContextService._format_tl(savings)
            reasons.append(f"Aylik {savings_text} tasarruf")

        # More data
        if current_tariff and tariff.data_gb > current_tariff.data_gb:
            diff = tariff.data_gb - current_tariff.data_gb
            reasons.append(
                f"{tariff.data_gb} GB veri, mevcut tarifenizden {diff} GB fazla"
            )

        # Ensure at least one reason
        if not reasons:
            reasons.append(f"{tariff.name} tarifesi kullaniminiza daha uygun")

        return reasons

    def _build_usage_summary(
        self, usage: UsageData, bills: list[Bill]
    ) -> UsageSummary:
        """Build usage summary with percentage calculations."""
        data_percent = (usage.data_used_gb / max(usage.data_limit_gb, 1)) * 100
        voice_percent = (usage.voice_used_minutes / max(usage.voice_limit_minutes, 1)) * 100
        sms_percent = (usage.sms_used / max(usage.sms_limit, 1)) * 100

        has_overage = usage.data_overage_gb > 0 or usage.voice_overage_minutes > 0

        # Get overage cost from latest bill's overage line items
        overage_cost = Decimal("0.00")
        if bills:
            sorted_bills = sorted(bills, key=lambda b: b.period, reverse=True)
            latest_bill = sorted_bills[0]
            for item in latest_bill.line_items:
                if item.category == "overage":
                    overage_cost += item.amount_tl

        return UsageSummary(
            data_used_gb=usage.data_used_gb,
            data_limit_gb=usage.data_limit_gb,
            data_percent=round(data_percent, 1),
            voice_used_minutes=usage.voice_used_minutes,
            voice_limit_minutes=usage.voice_limit_minutes,
            voice_percent=round(voice_percent, 1),
            sms_used=usage.sms_used,
            sms_limit=usage.sms_limit,
            sms_percent=round(sms_percent, 1),
            has_overage=has_overage,
            overage_cost_tl=overage_cost,
        )
