"""ChatService: orchestrates Gemini LLM streaming with RAG context and conversation memory."""

import logging
from collections.abc import AsyncIterator
from typing import Union

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import Settings
from app.models.recommendation_schemas import RecommendationResult
from app.prompts.billing_prompts import (
    BILLING_SYSTEM_PROMPT,
    RECOMMENDATION_CONTEXT_SECTION,
)
from app.prompts.system_prompt import SYSTEM_PROMPT
from app.services.billing_context import BillingContextService
from app.services.personalization_engine import get_conversation_style
from app.services.memory_service import MemoryService
from app.services.pii_service import PIIMaskingService
from app.services.rag_service import RAGService
from app.services.recommendation_service import TariffRecommendationService

logger = logging.getLogger(__name__)

# Empty-context fallback message for when RAG returns 0 results
_NO_CONTEXT_FALLBACK = "Bu konuda bilgi kaynaklarinda ilgili bilgi bulunamadi."


class ChatService:
    """Orchestrates RAG-augmented chat with Gemini LLM streaming.

    Workflow per request:
    1. Retrieve relevant documents from Milvus via RAGService
    2. Load conversation history from Redis via MemoryService
    2b. Generate tariff recommendations if customer context available (Phase 6)
    3. Construct messages with system prompt (incl. RAG context + recommendations) + history + user message
    4. Stream tokens from Gemini via astream()
    5. Save the exchange to conversation history
    6. Yield structured recommendation data for rich UI (Phase 6)
    """

    def __init__(
        self,
        settings: Settings,
        pii_enabled: bool = True,
        billing_context: BillingContextService | None = None,
        recommendation_service: TariffRecommendationService | None = None,
    ) -> None:
        self._llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.gemini_api_key,
            temperature=0.3,
            max_output_tokens=2048,
        )
        self._rag = RAGService(settings)
        self._memory = MemoryService(redis_url=settings.redis_url)
        self._pii_service = PIIMaskingService() if pii_enabled else None
        self._billing_context = billing_context
        self._recommendation = recommendation_service

    async def stream_response(
        self, message: str, session_id: str, customer_id: str | None = None
    ) -> AsyncIterator[Union[str, dict]]:
        """Stream LLM response tokens for a user message.

        Args:
            message: User's message in Turkish.
            session_id: Session ID for conversation memory.
            customer_id: Optional customer ID for billing context enrichment.

        Yields:
            String tokens from the Gemini LLM response, followed by an optional
            dict with structured recommendation data (type="structured").
        """
        # 0. Mask PII in user message BEFORE any processing
        masked_message = self._pii_service.mask(message) if self._pii_service else message
        logger.debug(
            "PII masking applied: original_len=%d masked_len=%d",
            len(message),
            len(masked_message),
        )

        # 1. RAG retrieval (uses masked message)
        rag_results = await self._rag.search(masked_message, top_k=5)
        if rag_results:
            context = "\n\n".join(r["content"] for r in rag_results)
        else:
            context = _NO_CONTEXT_FALLBACK

        # 2. Billing context enrichment (Phase 5)
        customer_context = ""
        if customer_id and self._billing_context:
            customer_context = self._billing_context.get_customer_context(customer_id) or ""

        # 2b. Recommendation context enrichment (Phase 6)
        recommendation_context = ""
        recommendation_result = None
        if customer_id and self._recommendation:
            recommendation_result = self._recommendation.get_recommendations(customer_id)
            if recommendation_result and recommendation_result.recommendations:
                recommendation_context = self._format_recommendation_context(recommendation_result)

        # 3. Load conversation history (last 20 messages = 10 turns)
        past_messages = self._memory.get_history(session_id)

        # 4. Build message list with conditional prompt selection
        conversation_style = get_conversation_style()
        if customer_id and self._billing_context:
            segment, contract_type = self._billing_context.get_customer_segment_info(customer_id)
            conversation_style = get_conversation_style(segment, contract_type)

        if customer_context:
            system_content = BILLING_SYSTEM_PROMPT.format(
                customer_context=customer_context,
                rag_context=context,
                recommendation_context=recommendation_context,
                conversation_style=conversation_style,
            )
        else:
            system_content = SYSTEM_PROMPT.format(
                context=context,
                conversation_style=conversation_style,
            )

        messages = [
            SystemMessage(content=system_content),
            *past_messages[-20:],
            HumanMessage(content=masked_message),
        ]

        # 5. Stream from Gemini
        full_response = ""
        async for chunk in self._llm.astream(messages):
            token = chunk.content
            if token:
                full_response += token
                yield token

        # 6. Save masked message to conversation history (not raw)
        self._memory.add_messages(session_id, masked_message, full_response)

        # 7. Yield structured data for rich UI (Phase 6)
        if recommendation_result and recommendation_result.recommendations:
            yield {
                "type": "structured",
                "data": {
                    "type": "recommendation",
                    "payload": {
                        "current_tariff": recommendation_result.current_tariff_name,
                        "current_cost": str(recommendation_result.current_effective_cost_tl),
                        "usage_summary": {
                            "data_used_gb": recommendation_result.usage_summary.data_used_gb,
                            "data_limit_gb": recommendation_result.usage_summary.data_limit_gb,
                            "data_percent": recommendation_result.usage_summary.data_percent,
                            "voice_used_minutes": recommendation_result.usage_summary.voice_used_minutes,
                            "voice_limit_minutes": recommendation_result.usage_summary.voice_limit_minutes,
                            "voice_percent": recommendation_result.usage_summary.voice_percent,
                            "sms_used": recommendation_result.usage_summary.sms_used,
                            "sms_limit": recommendation_result.usage_summary.sms_limit,
                            "sms_percent": recommendation_result.usage_summary.sms_percent,
                            "has_overage": recommendation_result.usage_summary.has_overage,
                            "overage_cost": str(recommendation_result.usage_summary.overage_cost_tl),
                        },
                        "recommendations": [
                            {
                                "tariff_name": r.tariff.name,
                                "monthly_price": str(r.tariff.monthly_price_tl),
                                "projected_cost": str(r.projected_monthly_cost_tl),
                                "savings": str(r.monthly_savings_tl),
                                "data_gb": r.tariff.data_gb,
                                "voice_minutes": r.tariff.voice_minutes,
                                "sms_count": r.tariff.sms_count,
                                "fit_score": r.fit_score,
                                "reasons": r.reasons,
                            }
                            for r in recommendation_result.recommendations
                        ],
                    },
                },
            }

    def _format_recommendation_context(self, result: RecommendationResult) -> str:
        """Format recommendation results as LLM context text."""
        lines = []
        lines.append(f"Mevcut Tarife: {result.current_tariff_name}")
        lines.append(
            f"Mevcut Ortalama Aylik Maliyet: {BillingContextService._format_tl(result.current_effective_cost_tl)}"
        )
        lines.append("")

        for i, rec in enumerate(result.recommendations, 1):
            lines.append(f"### Oneri {i}: {rec.tariff.name}")
            lines.append(f"- Aylik Ucret: {BillingContextService._format_tl(rec.tariff.monthly_price_tl)}")
            lines.append(
                f"- Tahmini Aylik Maliyet: {BillingContextService._format_tl(rec.projected_monthly_cost_tl)}"
            )
            savings_text = BillingContextService._format_tl(rec.monthly_savings_tl)
            if rec.monthly_savings_tl > 0:
                lines.append(f"- Aylik Tasarruf: {savings_text}")
            else:
                lines.append(f"- Aylik Fark: +{savings_text} (daha pahali)")
            lines.append(
                f"- Veri: {rec.tariff.data_gb} GB | Arama: {rec.tariff.voice_minutes} dk | SMS: {rec.tariff.sms_count}"
            )
            lines.append(f"- Uygunluk Skoru: {rec.fit_score}")
            for reason in rec.reasons:
                lines.append(f"  - {reason}")
            lines.append("")

        recommendation_text = "\n".join(lines)
        return RECOMMENDATION_CONTEXT_SECTION.format(recommendation_text=recommendation_text)
