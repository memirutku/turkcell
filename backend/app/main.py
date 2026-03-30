import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, mock_bss
from app.config import get_settings
from app.services.mock_bss import MockBSSService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)

    # Load mock data at startup
    mock_service = MockBSSService()
    mock_service.load_data()
    app.state.mock_bss = mock_service
    logger.info(
        "Mock BSS data loaded: %d customers, %d tariffs",
        mock_service.customer_count,
        mock_service.tariff_count,
    )

    yield

    # Cleanup on shutdown
    logger.info("Shutting down Turkcell AI-Gen API")


app = FastAPI(
    title="Turkcell AI-Gen API",
    description="Turkcell AI-Gen Dijital Asistan Backend",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(mock_bss.router, prefix="/api/mock", tags=["mock-bss"])
