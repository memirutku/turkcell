import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, MagicMock

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


@pytest.fixture
def mock_rag_service():
    """Create a mock RAGService for testing."""
    mock = MagicMock()
    mock.is_available = True
    mock.search = AsyncMock(return_value=[
        {
            "content": "Platinum Esneyebilen 20GB tarife ayda 299 TL.",
            "metadata": {
                "source": "tariff_descriptions.txt",
                "doc_type": "tariff",
                "language": "tr",
            },
            "score": 0.85,
        }
    ])
    return mock
