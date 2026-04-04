"""Pydantic schemas for per-customer interaction memory."""

from datetime import datetime

from pydantic import BaseModel, Field


class InteractionRecord(BaseModel):
    """Single interaction summary stored in customer memory."""

    interaction_id: str = Field(description="Benzersiz etkilesim ID'si (UUID)")
    session_id: str = Field(description="Etkilesimin gerceklestigi oturum ID'si")
    timestamp: datetime = Field(description="Etkilesim zamani")
    summary: str = Field(description="Etkilesim ozeti (Turkce)")
    topics: list[str] = Field(
        default_factory=list,
        description="Konusulan konular (ornek: fatura_sorgulama, tarife_degisikligi)",
    )
    actions_taken: list[str] = Field(
        default_factory=list,
        description="Gerceklestirilen islemler (ornek: tarife_degisikligi: tariff-003)",
    )
    unresolved_issues: list[str] = Field(
        default_factory=list,
        description="Cozulmemis sorunlar",
    )
    preferences_learned: list[str] = Field(
        default_factory=list,
        description="Ogreniilen musteri tercihleri",
    )
    sentiment: str = Field(
        default="notr",
        description="Musteri duygu durumu: olumlu / notr / olumsuz",
    )


class CustomerMemory(BaseModel):
    """Full memory structure for a customer across all sessions."""

    customer_id: str
    interactions: list[InteractionRecord] = Field(default_factory=list)
    last_updated: datetime


class CustomerMemoryInput(BaseModel):
    """Input schema for save_customer_memory tool."""

    customer_id: str = Field(description="Musteri ID'si (ornek: cust-001)")
    summary: str = Field(description="Etkilesim ozeti (Turkce)")
    topics: list[str] = Field(
        default_factory=list, description="Konusulan konular"
    )
    actions_taken: list[str] = Field(
        default_factory=list, description="Gerceklestirilen islemler"
    )
    unresolved_issues: list[str] = Field(
        default_factory=list, description="Cozulmemis sorunlar"
    )
    preferences_learned: list[str] = Field(
        default_factory=list, description="Ogreniilen tercihler"
    )
    sentiment: str = Field(
        default="notr", description="Musteri duygu durumu: olumlu/notr/olumsuz"
    )


class GetCustomerMemoryInput(BaseModel):
    """Input schema for get_customer_memory tool."""

    customer_id: str = Field(description="Hafiza sorgulanacak musteri ID'si")
