import asyncio
import json
import logging
import random
from datetime import datetime
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

    # --- Action methods (async, with realistic delays) ---

    async def activate_package(self, customer_id: str, package_id: str) -> dict:
        """Activate an add-on package for a customer. Simulates BSS processing delay."""
        await asyncio.sleep(random.uniform(0.5, 1.5))

        customer = self._customers.get(customer_id)
        if not customer:
            return {"success": False, "error": f"Musteri bulunamadi: {customer_id}"}

        package = self._packages.get(package_id)
        if not package:
            return {"success": False, "error": f"Paket bulunamadi: {package_id}"}

        return {
            "success": True,
            "transaction_id": f"TXN-{random.randint(100000, 999999)}",
            "timestamp": datetime.now().isoformat(),
            "customer_id": customer_id,
            "package": {
                "id": package.id,
                "name": package.name,
                "price_tl": str(package.price_tl),
                "duration_days": package.duration_days,
            },
            "message_tr": (
                f"{package.name} basariyla aktiflestirildi. "
                f"Ucret: {package.price_tl} TL, Sure: {package.duration_days} gun."
            ),
        }

    async def change_tariff(self, customer_id: str, new_tariff_id: str) -> dict:
        """Change a customer's tariff plan. Simulates BSS processing delay."""
        await asyncio.sleep(random.uniform(0.5, 1.5))

        customer = self._customers.get(customer_id)
        if not customer:
            return {"success": False, "error": f"Musteri bulunamadi: {customer_id}"}

        new_tariff = self._tariffs.get(new_tariff_id)
        if not new_tariff:
            return {"success": False, "error": f"Tarife bulunamadi: {new_tariff_id}"}

        old_tariff = self._tariffs.get(customer.tariff_id)

        # Update customer's tariff in-place
        customer.tariff_id = new_tariff_id

        return {
            "success": True,
            "transaction_id": f"TXN-{random.randint(100000, 999999)}",
            "timestamp": datetime.now().isoformat(),
            "customer_id": customer_id,
            "old_tariff": (
                {
                    "id": old_tariff.id,
                    "name": old_tariff.name,
                    "monthly_price_tl": str(old_tariff.monthly_price_tl),
                }
                if old_tariff
                else None
            ),
            "new_tariff": {
                "id": new_tariff.id,
                "name": new_tariff.name,
                "monthly_price_tl": str(new_tariff.monthly_price_tl),
            },
            "message_tr": f"Tarifiniz {new_tariff.name} olarak basariyla degistirildi.",
        }
