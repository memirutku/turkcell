"""Churn risk and customer lifetime value analysis service."""

import logging
from datetime import date
from decimal import Decimal

from app.models.personalization_schemas import ChurnRiskProfile
from app.services.mock_bss import MockBSSService

logger = logging.getLogger(__name__)

# Expected remaining months by segment (used for CLV calculation)
SEGMENT_EXPECTED_MONTHS = {
    "genc": 18,
    "profesyonel": 36,
    "aile": 48,
    "emekli": 60,
    "ogrenci": 18,
}


class ChurnRiskService:
    """Calculates churn probability, CLV, loyalty, and upsell potential."""

    def __init__(self, mock_bss: MockBSSService):
        self._mock_bss = mock_bss

    def get_risk_profile(self, customer_id: str) -> ChurnRiskProfile | None:
        """Build a full churn risk profile for a customer."""
        customer = self._mock_bss.get_customer(customer_id)
        if not customer:
            return None

        bills = self._mock_bss.get_customer_bills(customer_id)
        usage = self._mock_bss.get_customer_usage(customer_id)
        profile = self._mock_bss.get_customer_profile(customer_id)

        segment = (profile or {}).get("segment", customer.segment or "profesyonel")
        tenure = self._calc_tenure_months(customer.registration_date)

        churn_prob, risk_factors = self._calc_churn(bills, usage, tenure)
        risk_level = self._risk_level(churn_prob)
        clv = self._calc_clv(bills, churn_prob, segment)
        loyalty = self._calc_loyalty(tenure, bills, churn_prob)
        upsell, cross_sell = self._calc_upsell(usage, segment, bills)

        return ChurnRiskProfile(
            customer_id=customer_id,
            churn_probability=round(churn_prob, 2),
            churn_risk_level=risk_level,
            risk_factors=risk_factors,
            clv_tl=Decimal(str(round(clv, 2))),
            loyalty_score=round(loyalty, 2),
            upsell_potential=upsell,
            cross_sell_categories=cross_sell,
        )

    def calc_retention_value(self, customer_id: str) -> float:
        """Calculate retention value score (0.0-1.0) for recommendation weighting."""
        profile = self.get_risk_profile(customer_id)
        if not profile:
            return 0.3

        high_churn = profile.churn_probability >= 0.5
        high_clv = float(profile.clv_tl) >= 5000

        if high_churn and high_clv:
            return 1.0
        elif high_churn:
            return 0.7
        elif high_clv:
            return 0.5
        return 0.3

    def _calc_churn(
        self, bills: list, usage, tenure: int
    ) -> tuple[float, list[str]]:
        """Deterministic churn probability based on observable signals."""
        prob = 0.05  # baseline
        factors: list[str] = []

        # Unpaid bills
        unpaid = sum(1 for b in bills if not b.is_paid)
        if unpaid > 0:
            prob += 0.15 * unpaid
            factors.append(f"{unpaid} adet odenmemis fatura")

        # Consistent data overage (from bills)
        overage_months = 0
        for bill in bills[-3:]:
            has_overage = any(
                item.category == "overage" for item in bill.line_items
            )
            if has_overage:
                overage_months += 1
        if overage_months >= 2:
            prob += 0.20
            factors.append("Son 3 ayda surekli asim (tarifesi yetersiz)")

        # Low tenure
        if tenure < 12:
            prob += 0.10
            factors.append("Dusuk kidem (12 aydan az)")

        # High tenure with no variety
        if tenure > 36 and overage_months == 0 and unpaid == 0:
            prob += 0.05
            factors.append("Uzun suredir tarife degisikligi yok (durgunluk)")

        # Increasing bill trend
        if len(bills) >= 2:
            totals = [float(b.total_amount_tl) for b in sorted(bills, key=lambda b: b.period)]
            if len(totals) >= 2 and totals[-1] > totals[-2] * 1.1:
                prob += 0.10
                factors.append("Fatura tutari artis egiliminde")

        return min(0.95, prob), factors

    @staticmethod
    def _risk_level(prob: float) -> str:
        if prob >= 0.7:
            return "kritik"
        elif prob >= 0.5:
            return "yuksek"
        elif prob >= 0.3:
            return "orta"
        return "dusuk"

    @staticmethod
    def _calc_tenure_months(registration_date: date) -> int:
        today = date.today()
        return (today.year - registration_date.year) * 12 + (
            today.month - registration_date.month
        )

    @staticmethod
    def _calc_clv(bills: list, churn_prob: float, segment: str) -> float:
        """CLV = avg_monthly_bill * expected_remaining_months * (1 - churn)."""
        if not bills:
            return 0.0
        avg_bill = sum(float(b.total_amount_tl) for b in bills) / len(bills)
        expected_months = SEGMENT_EXPECTED_MONTHS.get(segment, 36)
        return avg_bill * expected_months * (1 - churn_prob)

    @staticmethod
    def _calc_loyalty(tenure: int, bills: list, churn_prob: float) -> float:
        """Loyalty score (0.0-1.0) based on tenure, payment history, churn."""
        score = 0.0
        # Tenure contribution (up to 0.4)
        score += min(0.4, tenure / 60 * 0.4)
        # Payment history (up to 0.3)
        if bills:
            paid_ratio = sum(1 for b in bills if b.is_paid) / len(bills)
            score += paid_ratio * 0.3
        # Inverse churn (up to 0.3)
        score += (1 - churn_prob) * 0.3
        return min(1.0, score)

    @staticmethod
    def _calc_upsell(usage, segment: str, bills: list) -> tuple[str, list[str]]:
        """Determine upsell potential and cross-sell categories."""
        cross_sell: list[str] = []

        # Data overage -> upsell to bigger tariff or data package
        if usage and usage.data_overage_gb > 0:
            cross_sell.append("ek_data")

        # Segment-based cross-sell
        if segment in ("genc", "ogrenci"):
            cross_sell.append("sosyal_medya")
            cross_sell.append("muzik")
        elif segment == "profesyonel":
            cross_sell.append("yurt_disi")
            cross_sell.append("bulut_depolama")
        elif segment == "aile":
            cross_sell.append("eglence")
            cross_sell.append("egitim")
        elif segment == "emekli":
            cross_sell.append("saglik")

        # Upsell potential based on overage frequency
        overage_count = 0
        for bill in bills[-3:]:
            if any(i.category == "overage" for i in bill.line_items):
                overage_count += 1

        if overage_count >= 2:
            potential = "yuksek"
        elif overage_count == 1 or (usage and usage.data_used_gb / max(usage.data_limit_gb, 1) >= 0.8):
            potential = "orta"
        else:
            potential = "dusuk"

        return potential, cross_sell
