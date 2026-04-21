"""Agent-specific Pydantic models and TypedDict state for LangGraph agent workflow."""

import uuid
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class AgentState(TypedDict):
    """State for the Umay agent workflow."""

    messages: Annotated[list[BaseMessage], add_messages]
    customer_id: str | None
    session_id: str
    intent: (
        Literal["general_chat", "package_activation", "tariff_change", "bill_inquiry"]
        | None
    )
    proposed_action: dict | None
    action_result: dict | None
    rag_context: str
    customer_context: str


class AgentChatRequest(BaseModel):
    """Request body for the agent chat endpoint."""

    message: str = Field(
        ..., min_length=1, max_length=2000, description="User message in Turkish"
    )
    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Session ID"
    )
    customer_id: str = Field(
        ...,
        description="Customer ID (required for agent actions, e.g., 'cust-001')",
    )


class AgentConfirmRequest(BaseModel):
    """Request body for confirming/rejecting an agent action."""

    thread_id: str = Field(
        ..., description="LangGraph thread ID for the pending action"
    )
    approved: bool = Field(..., description="True to confirm, False to reject")


class ActionProposal(BaseModel):
    """Proposed action awaiting user confirmation."""

    action_type: Literal["package_activation", "tariff_change"]
    description: str
    details: dict[str, str]
    thread_id: str


class ActionResult(BaseModel):
    """Result of an executed or cancelled action."""

    success: bool
    action_type: Literal["package_activation", "tariff_change"]
    description: str
    details: dict[str, str]


# Tool input schemas
class ActivatePackageInput(BaseModel):
    customer_id: str = Field(description="Musteri ID'si (ornek: cust-001)")
    package_id: str = Field(description="Aktif edilecek paket ID'si (ornek: pkg-002)")


class ChangeTariffInput(BaseModel):
    customer_id: str = Field(description="Musteri ID'si")
    new_tariff_id: str = Field(
        description="Yeni tarife ID'si (ornek: tariff-003)"
    )


class LookupBillInput(BaseModel):
    customer_id: str = Field(description="Fatura sorgulanacak musteri ID'si")


class RecommendTariffInput(BaseModel):
    customer_id: str = Field(description="Tarife onerisi yapilacak musteri ID'si")


class CompareBillsInput(BaseModel):
    customer_id: str = Field(description="Fatura karsilastirmasi yapilacak musteri ID'si")


class CheckUsageAlertsInput(BaseModel):
    customer_id: str = Field(description="Kullanim uyarilari kontrol edilecek musteri ID'si")


class RecommendPackageInput(BaseModel):
    customer_id: str = Field(description="Paket onerisi yapilacak musteri ID'si")


# MCP-backed personalization tool schemas
class PersonalizedRecommendationInput(BaseModel):
    customer_id: str = Field(description="Kisisellestirilmis tarife onerisi yapilacak musteri ID'si")
    top_n: int = Field(default=3, description="En fazla kac oneri donecegi (varsayilan: 3)")


class PersonalizedPackageRecommendationInput(BaseModel):
    customer_id: str = Field(description="Kisisellestirilmis paket onerisi yapilacak musteri ID'si")
    top_n: int = Field(default=3, description="En fazla kac oneri donecegi (varsayilan: 3)")


class CustomerRiskProfileInput(BaseModel):
    customer_id: str = Field(description="Kayip riski analiz edilecek musteri ID'si")


class UsagePatternAnalysisInput(BaseModel):
    customer_id: str = Field(description="Kullanim kaliplari analiz edilecek musteri ID'si")


class MarketComparisonInput(BaseModel):
    tariff_id: str = Field(description="Piyasa ile karsilastirilacak tarife ID'si (ornek: tariff-001)")
