"""BillingContextService: formats customer billing/tariff data as structured Turkish text for LLM context injection."""

from decimal import Decimal

from app.models.schemas import Bill, CustomerDetail, Tariff, UsageData
from app.services.mock_bss import MockBSSService

# Category mapping: internal key -> Turkish display label
CATEGORY_MAP: dict[str, str] = {
    "base": "Ana Ücret",
    "overage": "Aşım Ücreti",
    "tax": "Vergi",
}


class BillingContextService:
    """Transforms raw customer data from MockBSSService into human-readable
    Turkish context that the LLM can reason about."""

    def __init__(self, mock_bss: MockBSSService) -> None:
        self._bss = mock_bss

    def get_customer_context(self, customer_id: str) -> str | None:
        """Load customer data from MockBSSService, format as Turkish text.
        Returns None if customer not found."""
        customer = self._bss.get_customer(customer_id)
        if customer is None:
            return None

        bills = self._bss.get_customer_bills(customer_id)
        usage = self._bss.get_customer_usage(customer_id)

        sections: list[str] = []
        sections.append(self._format_customer_profile(customer))

        if customer.tariff:
            sections.append(self._format_current_tariff(customer.tariff))

        sections.append(self._format_bills(bills))

        if usage:
            sections.append(self._format_usage(usage))

        return "\n\n".join(sections)

    def get_customer_segment_info(self, customer_id: str) -> tuple[str, str]:
        """Return (segment, contract_type) for a customer. Defaults if not found."""
        customer = self._bss.get_customer(customer_id)
        if customer is None:
            return ("default", "bireysel")
        return (customer.segment or "default", customer.contract_type or "bireysel")

    # -- Private formatting methods --

    def _format_customer_profile(self, customer: CustomerDetail) -> str:
        """Format customer profile with PII redacted."""
        # Show first name + initial only for privacy
        name_parts = customer.name.split()
        display_name = name_parts[0]
        if len(name_parts) > 1:
            display_name += " " + name_parts[1][0] + "."

        # Redact phone: show only last 4 digits
        phone_masked = "***" + customer.phone_number[-4:]

        lines = [
            "## Musteri Bilgileri",
            f"- Müşteri ID: {customer.id}",
            f"- Ad: {display_name}",
            f"- Telefon: {phone_masked}",
            f"- Şehir: {customer.address_city}",
            f"- Kayıt Tarihi: {customer.registration_date}",
        ]
        return "\n".join(lines)

    def _format_current_tariff(self, tariff: Tariff) -> str:
        """Format current tariff details."""
        lines = [
            "## Mevcut Tarife",
            f"- Tarife ID: {tariff.id}",
            f"- Tarife: {tariff.name}",
            f"- Internet: {tariff.data_gb}GB",
            f"- Konusma: {tariff.voice_minutes} dakika",
            f"- SMS: {tariff.sms_count} adet",
            f"- Aylık Ücret: {self._format_tl(tariff.monthly_price_tl)}",
        ]
        return "\n".join(lines)

    def _format_bills(self, bills: list[Bill]) -> str:
        """Format bill history sorted by period descending."""
        if not bills:
            return "## Faturalar\nHenuz fatura bilgisi bulunmamaktadir."

        # Sort by period descending (most recent first)
        sorted_bills = sorted(bills, key=lambda b: b.period, reverse=True)

        lines = ["## Faturalar"]
        for bill in sorted_bills:
            status = "Odendi" if bill.is_paid else "Odenmedi"
            lines.append(
                f"\n### Donem: {bill.period} | Durum: {status} | "
                f"Toplam: {self._format_tl(bill.total_amount_tl)}"
            )
            lines.append(f"- Fatura Tarihi: {bill.billing_date}")
            lines.append(f"- Son Odeme Tarihi: {bill.due_date}")
            lines.append("- Kalemler:")
            for item in bill.line_items:
                category_label = CATEGORY_MAP.get(item.category, item.category)
                lines.append(
                    f"  - [{category_label}] {item.description}: "
                    f"{self._format_tl(item.amount_tl)}"
                )
        return "\n".join(lines)

    def _format_usage(self, usage: UsageData) -> str:
        """Format current period usage data."""
        lines = [
            "## Guncel Kullanim",
            f"- Donem: {usage.period}",
            f"- Internet: {usage.data_used_gb}/{usage.data_limit_gb} GB",
            f"- Konusma: {usage.voice_used_minutes}/{usage.voice_limit_minutes} dakika",
            f"- SMS: {usage.sms_used}/{usage.sms_limit} adet",
        ]

        # Highlight overages with cause explanation
        if usage.data_overage_gb > 0:
            lines.append(
                f"- **İnternet Aşımı: {usage.data_overage_gb} GB** "
                f"(Tarifenizde {usage.data_limit_gb}GB internet var, "
                f"bu dönem {usage.data_used_gb}GB kullandınız → "
                f"{usage.data_overage_gb}GB aşım)"
            )
        if usage.voice_overage_minutes > 0:
            lines.append(
                f"- **Konuşma Aşımı: {usage.voice_overage_minutes} dakika** "
                f"(Tarifenizde {usage.voice_limit_minutes} dakika var, "
                f"bu dönem {usage.voice_used_minutes} dakika kullandınız → "
                f"{usage.voice_overage_minutes} dakika aşım)"
            )

        return "\n".join(lines)

    @staticmethod
    def _format_tl(amount: Decimal) -> str:
        """Format a Decimal as Turkish currency string.

        Examples:
            Decimal("299.00") -> "299,00 TL"
            Decimal("1234.56") -> "1.234,56 TL"
        """
        # Ensure 2 decimal places
        amount = amount.quantize(Decimal("0.01"))

        # Split into integer and decimal parts
        str_amount = str(amount)
        if "." in str_amount:
            int_part, dec_part = str_amount.split(".")
        else:
            int_part = str_amount
            dec_part = "00"

        # Handle negative numbers
        negative = False
        if int_part.startswith("-"):
            negative = True
            int_part = int_part[1:]

        # Add Turkish thousands separator (period)
        if len(int_part) > 3:
            groups = []
            while int_part:
                groups.append(int_part[-3:])
                int_part = int_part[:-3]
            int_part = ".".join(reversed(groups))

        # Use comma as decimal separator
        result = f"{int_part},{dec_part} TL"
        if negative:
            result = "-" + result
        return result
