import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.mock_bss import MockBSSService


@pytest.fixture(scope="session", autouse=True)
def setup_mock_data():
    """Load mock BSS data into app state before tests run."""
    mock_service = MockBSSService()
    mock_service.load_data()
    app.state.mock_bss = mock_service


@pytest.fixture
async def client():
    """Async test client for FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
