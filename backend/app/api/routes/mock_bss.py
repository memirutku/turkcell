from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_mock_bss
from app.models.schemas import Bill, Campaign, CustomerDetail, Package, Tariff, UsageData
from app.services.mock_bss import MockBSSService

router = APIRouter()


# --- Customer endpoints ---


@router.get("/customers/{customer_id}", response_model=CustomerDetail)
async def get_customer(customer_id: str, bss: MockBSSService = Depends(get_mock_bss)):
    """Musteri profil bilgilerini getirir."""
    customer = bss.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail=f"Musteri bulunamadi: {customer_id}")
    return customer


@router.get("/customers/{customer_id}/bills", response_model=list[Bill])
async def get_customer_bills(customer_id: str, bss: MockBSSService = Depends(get_mock_bss)):
    """Musteri fatura gecmisini getirir."""
    if not bss.get_customer(customer_id):
        raise HTTPException(status_code=404, detail=f"Musteri bulunamadi: {customer_id}")
    return bss.get_customer_bills(customer_id)


@router.get("/customers/{customer_id}/bills/{bill_id}", response_model=Bill)
async def get_customer_bill(
    customer_id: str, bill_id: str, bss: MockBSSService = Depends(get_mock_bss)
):
    """Belirli bir faturanin detaylarini getirir."""
    bill = bss.get_customer_bill(customer_id, bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail=f"Fatura bulunamadi: {bill_id}")
    return bill


@router.get("/customers/{customer_id}/usage", response_model=UsageData)
async def get_customer_usage(customer_id: str, bss: MockBSSService = Depends(get_mock_bss)):
    """Musterinin guncel kullanim verilerini getirir."""
    usage = bss.get_customer_usage(customer_id)
    if not usage:
        raise HTTPException(status_code=404, detail=f"Kullanim verisi bulunamadi: {customer_id}")
    return usage


# --- Tariff endpoints ---


@router.get("/tariffs", response_model=list[Tariff])
async def get_tariffs(bss: MockBSSService = Depends(get_mock_bss)):
    """Tum mevcut tarifeleri listeler."""
    return bss.get_tariffs()


@router.get("/tariffs/{tariff_id}", response_model=Tariff)
async def get_tariff(tariff_id: str, bss: MockBSSService = Depends(get_mock_bss)):
    """Belirli bir tarifenin detaylarini getirir."""
    tariff = bss.get_tariff(tariff_id)
    if not tariff:
        raise HTTPException(status_code=404, detail=f"Tarife bulunamadi: {tariff_id}")
    return tariff


# --- Package endpoints ---


@router.get("/packages", response_model=list[Package])
async def get_packages(bss: MockBSSService = Depends(get_mock_bss)):
    """Tum ek paketleri listeler."""
    return bss.get_packages()


@router.get("/packages/{package_id}", response_model=Package)
async def get_package(package_id: str, bss: MockBSSService = Depends(get_mock_bss)):
    """Belirli bir paketin detaylarini getirir."""
    pkg = bss.get_package(package_id)
    if not pkg:
        raise HTTPException(status_code=404, detail=f"Paket bulunamadi: {package_id}")
    return pkg


# --- Campaign endpoints ---


@router.get("/campaigns", response_model=list[Campaign])
async def get_campaigns(bss: MockBSSService = Depends(get_mock_bss)):
    """Aktif kampanyalari listeler."""
    return bss.get_campaigns()
