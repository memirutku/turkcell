import pytest


# --- Tariffs ---


@pytest.mark.asyncio
async def test_get_tariffs(client):
    """Should return all 5 tariffs."""
    response = await client.get("/api/mock/tariffs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5


@pytest.mark.asyncio
async def test_get_tariff_detail(client):
    """Should return Platinum tariff with correct details."""
    response = await client.get("/api/mock/tariffs/tariff-001")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Platinum Esneyebilen 20GB"
    assert data["monthly_price_tl"] == "299.00"
    assert data["data_gb"] == 20


@pytest.mark.asyncio
async def test_get_tariff_not_found(client):
    """Should return 404 for nonexistent tariff."""
    response = await client.get("/api/mock/tariffs/nonexistent")
    assert response.status_code == 404


# --- Customers ---


@pytest.mark.asyncio
async def test_get_customer(client):
    """Should return customer with tariff info."""
    response = await client.get("/api/mock/customers/cust-001")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Ahmet Yılmaz"
    assert data["phone_number"] == "05321234567"
    assert data["tariff"] is not None
    assert data["tariff"]["name"] is not None  # Tariff name loaded from mock data


@pytest.mark.asyncio
async def test_get_customer_not_found(client):
    """Should return 404 for nonexistent customer."""
    response = await client.get("/api/mock/customers/nonexistent")
    assert response.status_code == 404


# --- Bills ---


@pytest.mark.asyncio
async def test_get_customer_bills(client):
    """Should return 3 months of bills for customer."""
    response = await client.get("/api/mock/customers/cust-001/bills")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


@pytest.mark.asyncio
async def test_get_customer_bill_detail_with_overage(client):
    """Should return bill with overage charges and tax breakdown."""
    response = await client.get("/api/mock/customers/cust-001/bills/bill-001-202602")
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "2026-02"
    # This bill has an overage charge
    categories = [item["category"] for item in data["line_items"]]
    assert "overage" in categories
    assert "tax" in categories
    assert "base" in categories


@pytest.mark.asyncio
async def test_get_customer_bill_has_kdv_oiv(client):
    """Bills should have separate KDV and OIV tax amounts."""
    response = await client.get("/api/mock/customers/cust-001/bills/bill-001-202601")
    assert response.status_code == 200
    data = response.json()
    assert "kdv_amount_tl" in data
    assert "oiv_amount_tl" in data
    assert float(data["kdv_amount_tl"]) > 0
    assert float(data["oiv_amount_tl"]) > 0


# --- Usage ---


@pytest.mark.asyncio
async def test_get_customer_usage(client):
    """Should return usage data with overage for customer 2."""
    response = await client.get("/api/mock/customers/cust-002/usage")
    assert response.status_code == 200
    data = response.json()
    assert data["data_used_gb"] > data["data_limit_gb"]  # Elif exceeds her limit
    assert data["data_overage_gb"] > 0


# --- Packages ---


@pytest.mark.asyncio
async def test_get_packages(client):
    """Should return all 5 add-on packages."""
    response = await client.get("/api/mock/packages")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5


@pytest.mark.asyncio
async def test_get_package_detail(client):
    """Should return package detail with Turkish content."""
    response = await client.get("/api/mock/packages/pkg-001")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Akıllı Yurt Dışı Paketi"
    assert data["price_tl"] == "149.00"


# --- Campaigns ---


@pytest.mark.asyncio
async def test_get_campaigns(client):
    """Should return all 3 active campaigns."""
    response = await client.get("/api/mock/campaigns")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


@pytest.mark.asyncio
async def test_campaigns_have_eligible_tariffs(client):
    """Campaigns should specify which tariffs they apply to."""
    response = await client.get("/api/mock/campaigns")
    data = response.json()
    for campaign in data:
        assert "eligible_tariffs" in campaign
        assert len(campaign["eligible_tariffs"]) > 0
