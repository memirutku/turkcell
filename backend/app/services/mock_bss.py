import json
import logging
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

        self._loaded = True
        logger.info(
            "Mock data loaded: %d customers, %d tariffs, %d packages, %d campaigns",
            len(self._customers),
            len(self._tariffs),
            len(self._packages),
            len(self._campaigns),
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
