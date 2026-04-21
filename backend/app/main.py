import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import agent, chat, health, memory, mock_bss, personalization, rag, voice, voice_live
from app.config import get_settings
from app.logging.pii_filter import PIILoggingFilter
from app.services.agent_service import AgentService
from app.services.billing_context import BillingContextService
from app.services.chat_service import ChatService
from app.services.mock_bss import MockBSSService
from app.services.rag_service import RAGService
from app.services.recommendation_service import TariffRecommendationService
from app.services.stt_service import STTService, MockSTTService
from app.services.tts_service import TTSService, MockTTSService
from app.services.voice_service import VoiceService
from app.services.gemini_live_service import GeminiLiveService
from app.services.memory_service import MemoryService
from app.services.customer_memory_service import CustomerMemoryService
from app.services.personalization_engine import PersonalizationEngine
from app.services.pii_service import PIIMaskingService

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

    # Billing context service (Phase 5)
    billing_context = BillingContextService(mock_service)
    logger.info("BillingContextService initialized")

    # Recommendation service (Phase 6)
    recommendation_service = TariffRecommendationService(mock_service)
    logger.info("TariffRecommendationService initialized")

    # Personalization engine (MCP)
    personalization_engine = PersonalizationEngine(mock_service)
    app.state.personalization_engine = personalization_engine
    logger.info("PersonalizationEngine initialized")

    # Customer memory service (cross-session, Redis-backed)
    customer_memory_service = CustomerMemoryService(
        redis_url=settings.redis_url,
        ttl=settings.customer_memory_ttl,
        max_interactions=settings.customer_memory_max_interactions,
    )
    app.state.customer_memory_service = customer_memory_service
    await customer_memory_service.seed_mock_data()
    logger.info(
        "CustomerMemoryService initialized (TTL: %d days, max: %d)",
        settings.customer_memory_ttl // 86400,
        settings.customer_memory_max_interactions,
    )

    # Chat service (Phase 3) with PII masking (Phase 4), billing context (Phase 5), recommendations (Phase 6)
    if settings.gemini_api_key:
        chat_service = ChatService(
            settings,
            pii_enabled=settings.pii_masking_enabled,
            billing_context=billing_context,
            recommendation_service=recommendation_service,
        )
        app.state.chat_service = chat_service
        logger.info(
            "Chat service initialized (PII masking: %s, billing context: enabled, recommendations: enabled)",
            "enabled" if settings.pii_masking_enabled else "disabled",
        )
    else:
        app.state.chat_service = None
        logger.warning("GEMINI_API_KEY not set -- Chat service disabled")

    # Agent service (Phase 9)
    if settings.gemini_api_key:
        agent_service = AgentService(
            settings=settings,
            mock_bss=mock_service,
            billing_context=billing_context,
            pii_enabled=settings.pii_masking_enabled,
            personalization_engine=personalization_engine,
            customer_memory_service=customer_memory_service,
        )
        app.state.agent_service = agent_service
        logger.info("Agent service initialized (LangGraph workflow)")
    else:
        app.state.agent_service = None
        logger.warning("GEMINI_API_KEY not set -- Agent service disabled")

    # Voice services (Phase 7)
    if settings.gemini_api_key:
        stt_service = STTService(settings)
        logger.info("STT service initialized (Gemini multimodal)")
    else:
        stt_service = MockSTTService()
        logger.warning("GEMINI_API_KEY not set -- using mock STT")

    if settings.aws_access_key_id and settings.aws_secret_access_key:
        tts_service = TTSService(settings)
        tts_backend = "Polly"
        logger.info("TTS service initialized (Polly Burcu neural)")
    else:
        try:
            from app.services.edge_tts_service import EdgeTTSService
            tts_service = EdgeTTSService()
            tts_backend = "EdgeTTS"
            logger.info("TTS service initialized (Edge TTS EmelNeural)")
        except Exception as e:
            tts_service = None
            tts_backend = "disabled"
            logger.warning("AWS credentials not set and edge-tts unavailable -- TTS disabled: %s", e)

    if settings.gemini_api_key and app.state.chat_service:
        app.state.voice_service = VoiceService(
            stt_service=stt_service,
            tts_service=tts_service,
            chat_service=app.state.chat_service,
            agent_service=app.state.agent_service if hasattr(app.state, 'agent_service') else None,
        )
        logger.info(
            "Voice service initialized (STT: %s, TTS: %s, Agent: %s)",
            "Gemini" if isinstance(stt_service, STTService) else "Mock",
            tts_backend,
            "enabled" if hasattr(app.state, 'agent_service') and app.state.agent_service else "disabled",
        )
    else:
        app.state.voice_service = None
        logger.warning("Chat service not available -- Voice service disabled")

    # Gemini Live API service (real-time bidirectional voice)
    if settings.gemini_api_key and settings.gemini_live_enabled:
        pii_svc = PIIMaskingService() if settings.pii_masking_enabled else None
        memory_svc = MemoryService(redis_url=settings.redis_url)
        app.state.gemini_live_service = GeminiLiveService(
            settings=settings,
            mock_bss=mock_service,
            billing_context=billing_context,
            rag_service=app.state.rag,
            pii_service=pii_svc,
            memory_service=memory_svc,
            customer_memory_service=customer_memory_service,
            personalization_engine=personalization_engine,
        )
        logger.info(
            "Gemini Live API service initialized (model: %s, voice: %s)",
            settings.gemini_live_model,
            settings.gemini_live_voice,
        )
    else:
        app.state.gemini_live_service = None
        if not settings.gemini_live_enabled:
            logger.info("Gemini Live API disabled (GEMINI_LIVE_ENABLED=false)")
        else:
            logger.warning("GEMINI_API_KEY not set -- Gemini Live API disabled")

    # MCP Server (Personalization)
    if settings.mcp_enabled:
        from app.mcp.server import create_and_mount_mcp

        mcp_server = create_and_mount_mcp(app)
        app.state.mcp_server = mcp_server
    else:
        logger.info("MCP server disabled (MCP_ENABLED=false)")

    # MCP Server (Customer Memory) — separate endpoint at /mcp/memory
    if settings.customer_memory_mcp_enabled:
        from app.mcp.memory_server import create_and_mount_memory_mcp

        memory_mcp = create_and_mount_memory_mcp(app)
        app.state.memory_mcp_server = memory_mcp
    else:
        logger.info("Customer Memory MCP server disabled (CUSTOMER_MEMORY_MCP_ENABLED=false)")

    yield

    # Cleanup on shutdown
    logger.info("Shutting down Umay AI-Gen API")


app = FastAPI(
    title="Umay AI-Gen API",
    description="Umay AI-Gen Dijital Asistan Backend",
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
app.include_router(voice.router, tags=["voice"])
app.include_router(voice_live.router, tags=["voice-live"])
app.include_router(agent.router, prefix="/api", tags=["agent"])
app.include_router(personalization.router, prefix="/api/mcp", tags=["mcp"])
app.include_router(memory.router, prefix="/api/mcp/memory", tags=["mcp-memory"])
