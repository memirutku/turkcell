"""Fixtures for AI evaluation: real Gemini LLM, mock BSS, mocked RAG/memory."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import Settings
from app.services.billing_context import BillingContextService
from app.services.mock_bss import MockBSSService


def _make_eval_settings() -> Settings:
    """Create Settings for eval: temperature=0, real API key."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        pytest.skip("GEMINI_API_KEY not set — cannot run AI evaluation")

    return MagicMock(
        spec=Settings,
        gemini_api_key=api_key,
        gemini_model="gemini-2.5-flash",
        redis_url="redis://localhost:6379/0",
        milvus_host="localhost",
        milvus_port=19530,
        milvus_collection_name="test_eval",
        pii_masking_enabled=False,
        mcp_enabled=True,
        customer_memory_mcp_enabled=False,
        customer_memory_ttl=2592000,
        customer_memory_max_interactions=20,
    )


@pytest.fixture(scope="session")
def eval_mock_bss():
    """Load real mock BSS data."""
    bss = MockBSSService()
    bss.load_data()
    return bss


@pytest.fixture(scope="session")
def eval_billing_context(eval_mock_bss):
    """Create BillingContextService from mock BSS."""
    return BillingContextService(eval_mock_bss)


@pytest.fixture(scope="session")
def eval_settings():
    """Create eval-specific settings with real API key."""
    return _make_eval_settings()


@pytest.fixture(scope="session")
def eval_agent_service(eval_settings, eval_mock_bss, eval_billing_context):
    """Create AgentService with real Gemini LLM (temperature=0).

    Patches:
    - RAGService to return empty results (not evaluating RAG)
    - Temperature override to 0 for reproducibility
    """
    from app.services.agent_service import AgentService
    from app.services.personalization_engine import PersonalizationEngine

    personalization_engine = PersonalizationEngine(eval_mock_bss)

    from langchain_google_genai import ChatGoogleGenerativeAI

    original_init = ChatGoogleGenerativeAI.__init__

    def _temp_zero_init(self, *args, **kwargs):
        kwargs["temperature"] = 0
        return original_init(self, *args, **kwargs)

    # Patch RAGService to avoid Milvus dependency
    # Patch ChatGoogleGenerativeAI to force temperature=0
    with (
        patch("app.services.agent_service.RAGService") as mock_rag_cls,
        patch.object(ChatGoogleGenerativeAI, "__init__", _temp_zero_init),
    ):
        mock_rag = MagicMock()
        mock_rag.search = AsyncMock(return_value=[])
        mock_rag_cls.return_value = mock_rag

        service = AgentService(
            settings=eval_settings,
            mock_bss=eval_mock_bss,
            billing_context=eval_billing_context,
            pii_enabled=False,
            personalization_engine=personalization_engine,
            customer_memory_service=None,
        )

    return service
