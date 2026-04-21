"""Pydantic schemas for the MCP personalization engine."""

from decimal import Decimal

from pydantic import BaseModel


class CustomerProfile(BaseModel):
    """Full demographic + behavioral profile for personalization."""

    customer_id: str
    name: str
    age: int
    occupation: str
    segment: str  # genc, profesyonel, aile, emekli, ogrenci
    city: str
    tenure_months: int
    contract_type: str  # bireysel, kurumsal


class UsagePattern(BaseModel):
    """Time-based usage analysis results."""

    customer_id: str
    period: str
    weekday_avg_data_gb: float
    weekend_avg_data_gb: float
    peak_hour_data_pct: float  # % of data used during 18:00-24:00
    data_trend: str  # "artiyor", "azaliyor", "sabit"
    data_trend_pct: float  # monthly growth/decline %
    voice_trend: str
    voice_trend_pct: float
    top_app_categories: list[str]
    seasonal_factor: str  # "yaz_tatil", "okul_donemi", "bayram", "normal"


class ChurnRiskProfile(BaseModel):
    """Customer risk and value assessment."""

    customer_id: str
    churn_probability: float  # 0.0-1.0
    churn_risk_level: str  # "dusuk", "orta", "yuksek", "kritik"
    risk_factors: list[str]  # Turkish explanations
    clv_tl: Decimal  # Customer Lifetime Value in TL
    loyalty_score: float  # 0.0-1.0
    upsell_potential: str  # "dusuk", "orta", "yuksek"
    cross_sell_categories: list[str]


class CompetitorTariff(BaseModel):
    """Single competitor tariff for market comparison."""

    operator: str
    tariff_name: str
    monthly_price_tl: Decimal
    data_gb: int
    voice_minutes: int
    sms_count: int


class MarketComparison(BaseModel):
    """Competitor pricing comparison for a tariff."""

    tariff_name: str
    umay_price_tl: Decimal
    competitors: list[CompetitorTariff]
    market_position: str  # "ucuz", "ortalama", "pahali"
    price_competitiveness_score: float  # 0.0-1.0


class PersonalizedRecommendation(BaseModel):
    """Enhanced recommendation with multi-factor personalization scores."""

    tariff_id: str
    tariff_name: str
    monthly_price_tl: Decimal
    estimated_savings_tl: Decimal
    # Multi-factor scores (each 0.0-1.0)
    usage_fit_score: float
    demographic_fit_score: float
    behavioral_fit_score: float
    market_competitiveness_score: float
    retention_value_score: float
    # Composite
    overall_score: float
    reasons: list[str]
    personalization_tags: list[str]


class PersonalizedRecommendationResult(BaseModel):
    """Full result from personalized tariff recommendation."""

    customer_id: str
    profile_summary: CustomerProfile
    current_tariff_name: str
    current_monthly_cost_tl: Decimal
    recommendations: list[PersonalizedRecommendation]
    retention_note: str | None = None


class PersonalizedPackageRecommendation(BaseModel):
    """Personalized package recommendation."""

    package_id: str
    package_name: str
    price_tl: Decimal
    category: str
    reason: str
    personalization_tags: list[str]


class PersonalizedPackageResult(BaseModel):
    """Full result from personalized package recommendation."""

    customer_id: str
    recommendations: list[PersonalizedPackageRecommendation]
