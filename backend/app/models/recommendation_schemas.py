"""Pydantic models for tariff recommendation engine (Phase 6 - BILL-05, BILL-06)."""

from decimal import Decimal

from pydantic import BaseModel

from app.models.schemas import Tariff


class UsageSummary(BaseModel):
    """Summarized usage for UI display."""

    data_used_gb: float
    data_limit_gb: int
    data_percent: float  # (data_used_gb / data_limit_gb) * 100
    voice_used_minutes: int
    voice_limit_minutes: int
    voice_percent: float
    sms_used: int
    sms_limit: int
    sms_percent: float
    has_overage: bool
    overage_cost_tl: Decimal


class TariffRecommendation(BaseModel):
    """A single tariff recommendation with savings analysis."""

    tariff: Tariff
    monthly_savings_tl: Decimal  # Positive = saves money
    projected_monthly_cost_tl: Decimal  # Including taxes
    current_monthly_cost_tl: Decimal
    fit_score: float  # 0.0-1.0
    reasons: list[str]  # Turkish explanation


class RecommendationResult(BaseModel):
    """Full recommendation analysis for a customer."""

    customer_id: str
    current_tariff_name: str
    current_effective_cost_tl: Decimal
    recommendations: list[TariffRecommendation]
    usage_summary: UsageSummary
