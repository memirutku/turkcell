import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import chat, health, mock_bss, rag
from app.config import get_settings
from app.logging.pii_filter import PIILoggingFilter
from app.services.chat_service import ChatService
from app.services.mock_bss import MockBSSService
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)

    # Attach PII sanitization filter to root logger (SEC-03)
    pii_filter = PIILoggingFilter()
    logging.getLogger().addFilter(pii_filter)
    logger.info("PII logging filter attached to root logger")

    # Load mock data at startup
    mock_service = MockBSSService()
    mock_service.load_data()
    app.state.mock_bss = mock_service
    logger.info(
        "Mock BSS data loaded: %d customers, %d tariffs",
        mock_service.customer_count,
        mock_service.tariff_count,
    )

    # RAG service (Phase 2)
    if settings.gemini_api_key:
        rag_service = RAGService(settings)
        app.state.rag = rag_service
        logger.info(
            "RAG service initialized (lazy connection, collection: %s)",
            settings.milvus_collection_name,
        )
    else:
        app.state.rag = None
        logger.warning("GEMINI_API_KEY not set -- RAG service disabled")

    # Chat service (Phase 3) with PII masking (Phase 4)
    if settings.gemini_api_key:
        chat_service = ChatService(settings, pii_enabled=settings.pii_masking_enabled)
        app.state.chat_service = chat_service
        logger.info(
            "Chat service initialized (PII masking: %s)",
            "enabled" if settings.pii_masking_enabled else "disabled",
        )
    else:
        app.state.chat_service = None
        logger.warning("GEMINI_API_KEY not set -- Chat service disabled")

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
app.include_router(rag.router, prefix="/api", tags=["rag"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
