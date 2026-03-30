import pytest


@pytest.mark.asyncio
async def test_health_returns_200(client):
    """Health endpoint should return 200 with expected structure."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "services" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_health_has_service_statuses(client):
    """Health response should include all service statuses."""
    response = await client.get("/api/health")
    data = response.json()
    services = data["services"]
    assert "redis" in services
    assert "milvus" in services
    assert "mock_bss" in services


@pytest.mark.asyncio
async def test_health_mock_bss_ready(client):
    """Mock BSS should report ready with correct data counts."""
    response = await client.get("/api/health")
    data = response.json()
    mock_bss = data["services"]["mock_bss"]
    assert mock_bss["status"] == "ready"
    assert mock_bss["customers"] == 3
    assert mock_bss["tariffs"] == 5


@pytest.mark.asyncio
async def test_health_version(client):
    """Health should report the current API version."""
    response = await client.get("/api/health")
    data = response.json()
    assert data["version"] == "0.1.0"
