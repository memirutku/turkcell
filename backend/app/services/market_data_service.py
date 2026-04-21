"""Market data and competitor comparison service."""

import logging
from decimal import Decimal

from app.models.personalization_schemas import CompetitorTariff, MarketComparison
from app.services.mock_bss import MockBSSService

logger = logging.getLogger(__name__)


class MarketDataService:
    """Provides competitor pricing comparison and market position analysis."""

    def __init__(self, mock_bss: MockBSSService):
        self._mock_bss = mock_bss

    def get_market_comparison(self, tariff_id: str) -> MarketComparison | None:
        """Compare a Umay tariff against competitor offerings."""
        tariff = self._mock_bss.get_tariff(tariff_id)
        if not tariff:
            return None

        market_data = self._mock_bss.get_market_data()
        if not market_data or "competitors" not in market_data:
            return None

        umay_price = float(tariff.monthly_price_tl)
        umay_data = tariff.data_gb

        # Find comparable competitor tariffs (within +/-40% data range)
        comparable: list[CompetitorTariff] = []
        for competitor in market_data["competitors"]:
            operator = competitor["operator"]
            for ct in competitor["tariffs"]:
                ct_data = ct["data_gb"]
                if umay_data * 0.6 <= ct_data <= umay_data * 1.4:
                    comparable.append(
                        CompetitorTariff(
                            operator=operator,
                            tariff_name=ct["name"],
                            monthly_price_tl=Decimal(ct["monthly_price_tl"]),
                            data_gb=ct["data_gb"],
                            voice_minutes=ct["voice_minutes"],
                            sms_count=ct["sms_count"],
                        )
                    )

        if not comparable:
            return MarketComparison(
                tariff_name=tariff.name,
                umay_price_tl=tariff.monthly_price_tl,
                competitors=[],
                market_position="ortalama",
                price_competitiveness_score=0.5,
            )

        avg_competitor_price = sum(float(c.monthly_price_tl) for c in comparable) / len(
            comparable
        )

        # Score: 1.0 = cheapest, 0.0 = most expensive
        if avg_competitor_price > 0:
            score = 1.0 - (umay_price - avg_competitor_price) / avg_competitor_price
            score = max(0.0, min(1.0, score))
        else:
            score = 0.5

        if score >= 0.6:
            position = "ucuz"
        elif score >= 0.4:
            position = "ortalama"
        else:
            position = "pahali"

        return MarketComparison(
            tariff_name=tariff.name,
            umay_price_tl=tariff.monthly_price_tl,
            competitors=comparable,
            market_position=position,
            price_competitiveness_score=round(score, 2),
        )

    def calc_market_score(self, tariff_id: str) -> float:
        """Return market competitiveness score (0.0-1.0) for a tariff."""
        comparison = self.get_market_comparison(tariff_id)
        if not comparison:
            return 0.5
        return comparison.price_competitiveness_score
