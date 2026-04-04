"""Usage pattern analysis service for personalization."""

import logging

from app.models.personalization_schemas import UsagePattern
from app.services.mock_bss import MockBSSService

logger = logging.getLogger(__name__)


class UsagePatternService:
    """Analyzes time-based usage patterns for personalization scoring."""

    def __init__(self, mock_bss: MockBSSService):
        self._mock_bss = mock_bss

    def get_usage_pattern(self, customer_id: str) -> UsagePattern | None:
        """Build a UsagePattern from mock data."""
        raw = self._mock_bss.get_usage_pattern(customer_id)
        if not raw:
            return None

        hourly = raw.get("hourly_data_distribution", {})
        peak_pct = hourly.get("18-24", 0.0)

        data_trend = raw.get("monthly_data_trend", [])
        voice_trend = raw.get("monthly_voice_trend", [])

        data_trend_str, data_trend_pct = self._calc_trend(data_trend)
        voice_trend_str, voice_trend_pct = self._calc_trend(voice_trend)

        return UsagePattern(
            customer_id=customer_id,
            period=raw.get("period", ""),
            weekday_avg_data_gb=raw.get("weekday_avg_data_gb", 0.0),
            weekend_avg_data_gb=raw.get("weekend_avg_data_gb", 0.0),
            peak_hour_data_pct=peak_pct,
            data_trend=data_trend_str,
            data_trend_pct=data_trend_pct,
            voice_trend=voice_trend_str,
            voice_trend_pct=voice_trend_pct,
            top_app_categories=raw.get("top_app_categories", []),
            seasonal_factor=raw.get("seasonal_factor", "normal"),
        )

    def calc_behavioral_fit(self, customer_id: str, tariff_data_gb: int, tariff_features: list[str]) -> float:
        """Calculate behavioral fit score (0.0-1.0) for a tariff."""
        pattern = self.get_usage_pattern(customer_id)
        if not pattern:
            return 0.5  # neutral if no data

        score = 0.5  # baseline

        # Weekend-heavy user + tariff with weekend feature
        if pattern.weekend_avg_data_gb > pattern.weekday_avg_data_gb * 1.5:
            if any("hafta sonu" in f.lower() or "weekend" in f.lower() for f in tariff_features):
                score += 0.15

        # Social media heavy user + social media feature
        if "sosyal_medya" in pattern.top_app_categories:
            if any("sosyal medya" in f.lower() for f in tariff_features):
                score += 0.2

        # Increasing data trend + tariff provides headroom
        usage = self._mock_bss.get_customer_usage(customer_id)
        if pattern.data_trend == "artiyor" and usage:
            headroom = tariff_data_gb / max(usage.data_used_gb, 0.1)
            if headroom >= 1.3:
                score += 0.1

        # Video/streaming user + large data tariff
        if "video" in pattern.top_app_categories and tariff_data_gb >= 15:
            score += 0.1

        return min(1.0, max(0.0, score))

    @staticmethod
    def _calc_trend(values: list[float]) -> tuple[str, float]:
        """Calculate trend direction and percentage from a list of monthly values."""
        if len(values) < 2:
            return "sabit", 0.0

        first = values[0]
        last = values[-1]
        if first == 0:
            return "sabit", 0.0

        pct = ((last - first) / first) * 100
        if pct > 5:
            return "artiyor", round(pct, 1)
        elif pct < -5:
            return "azaliyor", round(pct, 1)
        return "sabit", round(pct, 1)
