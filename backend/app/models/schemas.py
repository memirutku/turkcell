from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class Tariff(BaseModel):
    id: str
    name: str
    data_gb: int
    voice_minutes: int
    sms_count: int
    monthly_price_tl: Decimal
    description: str
    features: list[str]
    is_active: bool = True


class Package(BaseModel):
    id: str
    name: str
    category: str
    price_tl: Decimal
    duration_days: int
    description: str
    features: list[str]
    is_active: bool = True


class BillLineItem(BaseModel):
    description: str
    amount_tl: Decimal
    category: str


class Bill(BaseModel):
    id: str
    customer_id: str
    period: str
    billing_date: date
    due_date: date
    base_amount_tl: Decimal
    kdv_amount_tl: Decimal
    oiv_amount_tl: Decimal
    total_amount_tl: Decimal
    line_items: list[BillLineItem]
    is_paid: bool


class UsageData(BaseModel):
    customer_id: str
    period: str
    data_used_gb: float
    data_limit_gb: int
    voice_used_minutes: int
    voice_limit_minutes: int
    sms_used: int
    sms_limit: int
    data_overage_gb: float = 0.0
    voice_overage_minutes: int = 0


class Customer(BaseModel):
    id: str
    name: str
    tc_kimlik_no: str
    phone_number: str
    email: str
    tariff_id: str
    registration_date: date
    address_city: str


class Campaign(BaseModel):
    id: str
    name: str
    description: str
    discount_percent: int | None = None
    bonus_data_gb: int | None = None
    valid_until: date
    eligible_tariffs: list[str]
    is_active: bool = True


# Response models
class CustomerDetail(Customer):
    tariff: Tariff | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    services: dict
    timestamp: str
