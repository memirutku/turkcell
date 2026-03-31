"""Tests for BillingContextService, billing prompts, and billing-related schemas."""

import pytest
from decimal import Decimal

from app.main import app
from app.services.mock_bss import MockBSSService


# -- BillingContextService tests --


class TestBillingContext:
    """Test BillingContextService formatting and PII handling."""

    @pytest.fixture
    def billing_service(self):
        """Create BillingContextService using loaded mock data."""
        from app.services.billing_context import BillingContextService

        return BillingContextService(app.state.mock_bss)

    def test_get_customer_context_returns_formatted_text(self, billing_service):
        """get_customer_context returns string with customer name, tariff, data."""
        result = billing_service.get_customer_context("cust-001")
        assert result is not None
        assert "Ahmet" in result
        assert "Platinum" in result
        assert "20GB" in result or "20 GB" in result

    def test_get_customer_context_unknown_customer(self, billing_service):
        """get_customer_context returns None for nonexistent customer."""
        result = billing_service.get_customer_context("nonexistent")
        assert result is None

    def test_format_bills_includes_line_items(self, billing_service):
        """Output contains bill period and each line item description."""
        result = billing_service.get_customer_context("cust-001")
        assert result is not None
        assert "2026-01" in result or "2026-02" in result or "2026-03" in result
        # Check that line item descriptions appear
        assert "Platinum Esneyebilen 20GB Tarife Ucreti" in result

    def test_line_item_categories_turkish(self, billing_service):
        """Output maps 'base' -> 'Ana Ucret', 'overage' -> 'Asim Ucreti', 'tax' -> 'Vergi'."""
        result = billing_service.get_customer_context("cust-001")
        assert result is not None
        assert "Ana Ucret" in result
        assert "Vergi" in result
        # cust-001 has overage in 2026-02
        assert "Asim Ucreti" in result

    def test_currency_formatting(self, billing_service):
        """Amounts formatted with comma decimal separator and TL suffix."""
        result = billing_service.get_customer_context("cust-001")
        assert result is not None
        assert "299,00 TL" in result

    def test_pii_redaction(self, billing_service):
        """Output does NOT contain tc_kimlik_no, phone shows only last 4 digits."""
        result = billing_service.get_customer_context("cust-001")
        assert result is not None
        # tc_kimlik_no should NOT appear
        assert "12345678901" not in result
        # Phone should show only last 4 digits
        assert "***4567" in result
        # Full phone number should NOT appear
        assert "05321234567" not in result

    def test_usage_section_present(self, billing_service):
        """When usage data exists, output contains data/voice/SMS usage info."""
        result = billing_service.get_customer_context("cust-001")
        assert result is not None
        # cust-001 has usage data: 18.5/20 GB, 1250/2000 min, 45/1000 SMS
        assert "18" in result  # data_used_gb
        assert "20" in result  # data_limit_gb
        assert "1250" in result or "1.250" in result  # voice_used_minutes

    def test_no_bills_message(self, billing_service):
        """When customer has no bills, output contains appropriate message."""
        # We need a customer with no bills. Let's test with mock directly.
        from app.services.billing_context import BillingContextService
        from unittest.mock import MagicMock

        mock_bss = MagicMock()
        mock_bss.get_customer.return_value = app.state.mock_bss.get_customer("cust-001")
        mock_bss.get_customer_bills.return_value = []
        mock_bss.get_customer_usage.return_value = None

        service = BillingContextService(mock_bss)
        result = service.get_customer_context("cust-001")
        assert result is not None
        assert "Henuz fatura bilgisi bulunmamaktadir" in result

    def test_bill_payment_status(self, billing_service):
        """Output shows 'Odendi' for is_paid=True, 'Odenmedi' for is_paid=False."""
        result = billing_service.get_customer_context("cust-001")
        assert result is not None
        # cust-001 has paid and unpaid bills
        assert "Odendi" in result
        assert "Odenmedi" in result

    def test_currency_formatting_with_thousands(self, billing_service):
        """Large amounts use period as thousands separator."""
        from app.services.billing_context import BillingContextService

        result = BillingContextService._format_tl(Decimal("1234.56"))
        assert result == "1.234,56 TL"

    def test_currency_formatting_simple(self, billing_service):
        """Simple amounts format correctly."""
        from app.services.billing_context import BillingContextService

        result = BillingContextService._format_tl(Decimal("299.00"))
        assert result == "299,00 TL"


# -- Billing Prompts tests --


class TestBillingPrompts:
    """Test BILLING_SYSTEM_PROMPT content and structure."""

    def test_billing_system_prompt_has_placeholders(self):
        """BILLING_SYSTEM_PROMPT contains customer_context and rag_context placeholders."""
        from app.prompts.billing_prompts import BILLING_SYSTEM_PROMPT

        assert "{customer_context}" in BILLING_SYSTEM_PROMPT
        assert "{rag_context}" in BILLING_SYSTEM_PROMPT

    def test_billing_system_prompt_has_analysis_rules(self):
        """BILLING_SYSTEM_PROMPT contains 'Fatura Analiz Kurallari' section."""
        from app.prompts.billing_prompts import BILLING_SYSTEM_PROMPT

        assert "Fatura Analiz Kurallari" in BILLING_SYSTEM_PROMPT

    def test_billing_prompt_prioritizes_customer_data(self):
        """BILLING_SYSTEM_PROMPT contains instruction to prioritize customer data over RAG."""
        from app.prompts.billing_prompts import BILLING_SYSTEM_PROMPT

        assert "musteri bilgilerindeki gercek verileri kullan" in BILLING_SYSTEM_PROMPT

    def test_billing_prompt_has_security_guardrails(self):
        """BILLING_SYSTEM_PROMPT preserves GUVENLIK section from existing prompt."""
        from app.prompts.billing_prompts import BILLING_SYSTEM_PROMPT

        assert "GUVENLIK" in BILLING_SYSTEM_PROMPT

    def test_billing_prompt_has_turkcell_identity(self):
        """BILLING_SYSTEM_PROMPT identifies as Turkcell Asistan."""
        from app.prompts.billing_prompts import BILLING_SYSTEM_PROMPT

        assert "Turkcell Asistan" in BILLING_SYSTEM_PROMPT

    def test_billing_prompt_has_empathy_rules(self):
        """BILLING_SYSTEM_PROMPT includes empathy instructions."""
        from app.prompts.billing_prompts import BILLING_SYSTEM_PROMPT

        assert "empati" in BILLING_SYSTEM_PROMPT
