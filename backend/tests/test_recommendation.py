"""Tests for TariffRecommendationService - BILL-05 and BILL-06 requirements."""

import pytest
from decimal import Decimal
from unittest.mock import MagicMock

from app.main import app
from app.models.recommendation_schemas import (
    RecommendationResult,
    TariffRecommendation,
    UsageSummary,
)
from app.services.recommendation_service import TariffRecommendationService


class TestRecommendationService:
    """Test recommendation generation for various customers (BILL-05)."""

    @pytest.fixture
    def service(self):
        """Create TariffRecommendationService using loaded mock data."""
        return TariffRecommendationService(app.state.mock_bss)

    def test_cust002_gets_nonempty_recommendations(self, service):
        """cust-002 (Silver 5GB with heavy overages) should get recommendations."""
        result = service.get_recommendations("cust-002")
        assert result is not None
        assert len(result.recommendations) > 0

    def test_cust002_recommendations_have_positive_savings(self, service):
        """Each recommendation for cust-002 should show positive monthly savings."""
        result = service.get_recommendations("cust-002")
        assert result is not None
        for rec in result.recommendations:
            assert rec.monthly_savings_tl > 0, (
                f"{rec.tariff.name} has non-positive savings: {rec.monthly_savings_tl}"
            )

    def test_recommendations_sorted_by_savings_descending(self, service):
        """Recommendations are sorted by savings descending (highest first)."""
        result = service.get_recommendations("cust-002")
        assert result is not None
        assert len(result.recommendations) >= 2
        savings = [r.monthly_savings_tl for r in result.recommendations]
        assert savings == sorted(savings, reverse=True)

    def test_current_tariff_not_in_recommendations(self, service):
        """Current tariff (Silver 5GB, tariff-003) should NOT appear in recommendations."""
        result = service.get_recommendations("cust-002")
        assert result is not None
        for rec in result.recommendations:
            assert rec.tariff.id != "tariff-003", "Current tariff should be excluded"

    def test_unknown_customer_returns_none(self, service):
        """get_recommendations returns None for unknown customer_id."""
        result = service.get_recommendations("nonexistent-999")
        assert result is None

    def test_no_usage_data_returns_empty_recommendations(self, service):
        """get_recommendations returns empty recommendations when no usage data."""
        mock_bss = MagicMock()
        customer = app.state.mock_bss.get_customer("cust-001")
        mock_bss.get_customer.return_value = customer
        mock_bss.get_customer_usage.return_value = None
        mock_bss.get_customer_bills.return_value = []
        mock_bss.get_tariffs.return_value = app.state.mock_bss.get_tariffs()

        svc = TariffRecommendationService(mock_bss)
        result = svc.get_recommendations("cust-001")
        assert result is not None
        assert len(result.recommendations) == 0

    def test_top_n_limits_results(self, service):
        """top_n parameter limits number of returned recommendations."""
        result_2 = service.get_recommendations("cust-002", top_n=2)
        result_1 = service.get_recommendations("cust-002", top_n=1)
        assert result_2 is not None
        assert result_1 is not None
        assert len(result_1.recommendations) == 1
        assert len(result_2.recommendations) <= 2

    def test_fit_score_between_0_and_1(self, service):
        """fit_score should be a float between 0.0 and 1.0."""
        result = service.get_recommendations("cust-002")
        assert result is not None
        for rec in result.recommendations:
            assert isinstance(rec.fit_score, float)
            assert 0.0 <= rec.fit_score <= 1.0, (
                f"fit_score {rec.fit_score} out of range for {rec.tariff.name}"
            )

    def test_reasons_nonempty_turkish(self, service):
        """Each recommendation has non-empty reasons list with Turkish text."""
        result = service.get_recommendations("cust-002")
        assert result is not None
        for rec in result.recommendations:
            assert len(rec.reasons) > 0, f"No reasons for {rec.tariff.name}"
            for reason in rec.reasons:
                assert isinstance(reason, str)
                assert len(reason) > 5  # Not empty/trivial

    def test_recommendation_result_has_customer_info(self, service):
        """RecommendationResult contains customer_id and current tariff name."""
        result = service.get_recommendations("cust-002")
        assert result is not None
        assert result.customer_id == "cust-002"
        assert result.current_tariff_name == "Silver 5GB"


class TestSavingsCalculation:
    """Test exact savings calculations with Decimal arithmetic (BILL-06)."""

    @pytest.fixture
    def service(self):
        return TariffRecommendationService(app.state.mock_bss)

    def test_effective_monthly_cost_cust001(self, service):
        """_calculate_effective_monthly_cost averages last 3 bills for cust-001.

        cust-001 bills: 403.65 + 471.15 + 403.65 = 1278.45 / 3 = 426.15
        """
        bills = app.state.mock_bss.get_customer_bills("cust-001")
        cost = service._calculate_effective_monthly_cost(bills)
        assert cost == Decimal("426.15")

    def test_effective_monthly_cost_cust002(self, service):
        """_calculate_effective_monthly_cost averages last 3 bills for cust-002.

        cust-002 bills: 241.65 + 309.15 + 255.15 = 805.95 / 3 = 268.65
        """
        bills = app.state.mock_bss.get_customer_bills("cust-002")
        cost = service._calculate_effective_monthly_cost(bills)
        assert cost == Decimal("268.65")

    def test_project_cost_no_overage(self, service):
        """_project_cost_on_tariff returns base + taxes when no overage.

        Gold 10GB (199 TL) with cust-002 usage (8.2 GB data, 320 min voice):
        - No data overage (10 >= 8.2)
        - No voice overage (1000 >= 320)
        - subtotal = 199.00
        - KDV = 199.00 * 0.20 = 39.80
        - OIV = 199.00 * 0.15 = 29.85
        - Total = 199.00 + 39.80 + 29.85 = 268.65
        """
        tariff = app.state.mock_bss.get_tariff("tariff-002")  # Gold 10GB
        usage = app.state.mock_bss.get_customer_usage("cust-002")
        cost = service._project_cost_on_tariff(tariff, usage)
        assert cost == Decimal("268.65")

    def test_project_cost_with_data_overage(self, service):
        """_project_cost_on_tariff calculates data overage correctly.

        Ekonomik 3GB (79 TL) with cust-002 usage (8.2 GB data):
        - Data overage: 8.2 - 3 = 5.2 GB * 20.00 = 104.00
        - Voice overage: 320 - 300 = 20 min * 0.50 = 10.00
        - subtotal = 79.00 + 104.00 + 10.00 = 193.00
        - KDV = 193.00 * 0.20 = 38.60
        - OIV = 193.00 * 0.15 = 28.95
        - Total = 193.00 + 38.60 + 28.95 = 260.55
        """
        tariff = app.state.mock_bss.get_tariff("tariff-005")  # Ekonomik 3GB
        usage = app.state.mock_bss.get_customer_usage("cust-002")
        cost = service._project_cost_on_tariff(tariff, usage)
        assert cost == Decimal("260.55")

    def test_savings_are_decimal_two_places(self, service):
        """Savings amounts use Decimal with exactly 2 decimal places."""
        result = service.get_recommendations("cust-002")
        assert result is not None
        for rec in result.recommendations:
            assert isinstance(rec.monthly_savings_tl, Decimal)
            # Check it has exactly 2 decimal places
            assert rec.monthly_savings_tl == rec.monthly_savings_tl.quantize(
                Decimal("0.01")
            )

    def test_projected_cost_is_decimal(self, service):
        """Projected costs are Decimal values."""
        result = service.get_recommendations("cust-002")
        assert result is not None
        for rec in result.recommendations:
            assert isinstance(rec.projected_monthly_cost_tl, Decimal)
            assert isinstance(rec.current_monthly_cost_tl, Decimal)


class TestUsageSummary:
    """Test UsageSummary percentage calculations."""

    @pytest.fixture
    def service(self):
        return TariffRecommendationService(app.state.mock_bss)

    def test_usage_summary_data_percent(self, service):
        """UsageSummary data_percent = data_used_gb / data_limit_gb * 100.

        cust-002: 8.2 / 5 * 100 = 164.0
        """
        result = service.get_recommendations("cust-002")
        assert result is not None
        summary = result.usage_summary
        expected_percent = 8.2 / 5 * 100  # 164.0
        assert abs(summary.data_percent - expected_percent) < 0.01

    def test_usage_summary_voice_percent(self, service):
        """UsageSummary voice_percent = voice_used / voice_limit * 100.

        cust-002: 320 / 500 * 100 = 64.0
        """
        result = service.get_recommendations("cust-002")
        assert result is not None
        summary = result.usage_summary
        expected_percent = 320 / 500 * 100  # 64.0
        assert abs(summary.voice_percent - expected_percent) < 0.01

    def test_usage_summary_sms_percent(self, service):
        """UsageSummary sms_percent = sms_used / sms_limit * 100.

        cust-002: 15 / 250 * 100 = 6.0
        """
        result = service.get_recommendations("cust-002")
        assert result is not None
        summary = result.usage_summary
        expected_percent = 15 / 250 * 100  # 6.0
        assert abs(summary.sms_percent - expected_percent) < 0.01

    def test_usage_summary_has_overage(self, service):
        """cust-002 has data overage (3.2 GB), so has_overage should be True."""
        result = service.get_recommendations("cust-002")
        assert result is not None
        assert result.usage_summary.has_overage is True

    def test_usage_summary_no_overage(self, service):
        """cust-001 has no overage, so has_overage should be False."""
        result = service.get_recommendations("cust-001")
        assert result is not None
        assert result.usage_summary.has_overage is False

    def test_usage_summary_overage_cost(self, service):
        """cust-002 overage cost from latest bill's overage line items."""
        result = service.get_recommendations("cust-002")
        assert result is not None
        # Latest bill (2026-03) has 3GB overage at 60.00 TL
        assert result.usage_summary.overage_cost_tl == Decimal("60.00")
