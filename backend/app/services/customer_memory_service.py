"""Per-customer interaction memory backed by Redis.

Stores structured interaction summaries keyed by customer_id (not session_id)
so the AI assistant remembers previous conversations across sessions.
"""

import json
import logging
import uuid
from datetime import datetime, timezone

import redis.asyncio as aioredis

from app.models.customer_memory_schemas import CustomerMemory, InteractionRecord

logger = logging.getLogger(__name__)

_KEY_PREFIX = "customer_memory"


class CustomerMemoryService:
    """Redis-backed customer interaction memory with sliding-window TTL."""

    def __init__(
        self,
        redis_url: str,
        ttl: int = 2592000,
        max_interactions: int = 20,
    ) -> None:
        self._redis_url = redis_url
        self._ttl = ttl
        self._max = max_interactions
        self._redis: aioredis.Redis | None = None

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(
                self._redis_url, decode_responses=True
            )
        return self._redis

    def _key(self, customer_id: str) -> str:
        return f"{_KEY_PREFIX}:{customer_id}"

    async def get_memory(self, customer_id: str) -> CustomerMemory | None:
        """Load customer memory from Redis. Returns None if not found."""
        r = await self._get_redis()
        raw = await r.get(self._key(customer_id))
        if not raw:
            return None
        try:
            memory = CustomerMemory.model_validate_json(raw)
            # Sliding window: refresh TTL on read
            await r.expire(self._key(customer_id), self._ttl)
            return memory
        except Exception as e:
            logger.warning("Failed to parse memory for %s: %s", customer_id, e)
            return None

    async def save_interaction(
        self, customer_id: str, record: InteractionRecord
    ) -> CustomerMemory:
        """Append an interaction, trim to max, persist with TTL refresh."""
        r = await self._get_redis()

        # Load existing or create new
        existing = await self.get_memory(customer_id)
        if existing:
            interactions = existing.interactions
        else:
            interactions = []

        interactions.append(record)

        # Trim oldest if over max
        if len(interactions) > self._max:
            interactions = interactions[-self._max :]

        memory = CustomerMemory(
            customer_id=customer_id,
            interactions=interactions,
            last_updated=datetime.now(timezone.utc),
        )

        await r.set(
            self._key(customer_id),
            memory.model_dump_json(),
            ex=self._ttl,
        )
        return memory

    async def seed_mock_data(self) -> None:
        """Pre-populate interaction history for demo customers.

        Only seeds if the key does not already exist (avoids overwriting).
        """
        r = await self._get_redis()

        seeds: dict[str, list[InteractionRecord]] = {
            "cust-001": [
                InteractionRecord(
                    interaction_id=str(uuid.uuid4()),
                    session_id="seed-session-001a",
                    timestamp=datetime(2026, 3, 15, 10, 30, tzinfo=timezone.utc),
                    summary="Musteri Mart ayi faturasini sorguladi. 18.5 GB kullanim ile 20 GB limitine yakin oldugunu ogrendi. Asim ucreti konusunda endiseli.",
                    topics=["fatura_sorgulama", "kullanim_kontrolu"],
                    actions_taken=[],
                    unresolved_issues=["internet_hizi_yavaslik_sikayeti"],
                    preferences_learned=["maliyet_hassasiyeti_yuksek", "veri_kullanimi_yogun"],
                    sentiment="olumsuz",
                ),
                InteractionRecord(
                    interaction_id=str(uuid.uuid4()),
                    session_id="seed-session-001b",
                    timestamp=datetime(2026, 3, 22, 14, 15, tzinfo=timezone.utc),
                    summary="Mevcut tarifesi (Platinum 20GB) icin daha uygun alternatifler istedi. Kisisellestirilmis tarife onerisi yapildi. Platinum Plus 50GB onerisi begenildi ama karar vermedi.",
                    topics=["tarife_onerisi", "tarife_karsilastirma"],
                    actions_taken=[],
                    unresolved_issues=["internet_hizi_yavaslik_sikayeti"],
                    preferences_learned=["whatsapp_yogun_kullanim", "aylik_300tl_alti_tercih"],
                    sentiment="notr",
                ),
                InteractionRecord(
                    interaction_id=str(uuid.uuid4()),
                    session_id="seed-session-001c",
                    timestamp=datetime(2026, 3, 28, 9, 0, tzinfo=timezone.utc),
                    summary="5 GB ek internet paketi aktive edildi. Ay sonuna kadar asim riski ortadan kalkti.",
                    topics=["paket_aktivasyonu"],
                    actions_taken=["paket_aktivasyonu: pkg-001 (5GB Ek Internet)"],
                    unresolved_issues=["internet_hizi_yavaslik_sikayeti"],
                    preferences_learned=[],
                    sentiment="olumlu",
                ),
            ],
            "cust-002": [
                InteractionRecord(
                    interaction_id=str(uuid.uuid4()),
                    session_id="seed-session-002a",
                    timestamp=datetime(2026, 3, 18, 16, 45, tzinfo=timezone.utc),
                    summary="Sosyal medya paketi hakkinda bilgi aldi. Instagram ve TikTok icin ek paket secenekleri soruldu. Ogrenci indirimi olup olmadigini sordu.",
                    topics=["paket_bilgi", "sosyal_medya"],
                    actions_taken=[],
                    unresolved_issues=[],
                    preferences_learned=["sosyal_medya_oncelikli", "fiyat_cok_hassas", "instagram_tiktok_agirlikli"],
                    sentiment="notr",
                ),
                InteractionRecord(
                    interaction_id=str(uuid.uuid4()),
                    session_id="seed-session-002b",
                    timestamp=datetime(2026, 3, 25, 11, 20, tzinfo=timezone.utc),
                    summary="Fatura odeme tarihi ve odeme yontemleri hakkinda bilgi aldi. Otomatik odeme tanimlamak istedi ama banka bilgisi girmek istemedi.",
                    topics=["fatura_odeme", "odeme_yontemleri"],
                    actions_taken=[],
                    unresolved_issues=[],
                    preferences_learned=["dijital_odeme_tercih", "banka_bilgisi_paylasmak_istemiyor"],
                    sentiment="notr",
                ),
            ],
            "cust-003": [
                InteractionRecord(
                    interaction_id=str(uuid.uuid4()),
                    session_id="seed-session-003a",
                    timestamp=datetime(2026, 3, 10, 8, 0, tzinfo=timezone.utc),
                    summary="Almanya is seyahati icin yurt disi roaming paketlerini sorguladi. Avrupa paketi onerisi yapildi. Aktivasyon icin sirket onayina ihtiyaci vardi.",
                    topics=["yurt_disi_roaming", "kurumsal_islemler"],
                    actions_taken=[],
                    unresolved_issues=["yurt_disi_paket_aktivasyon_bekliyor"],
                    preferences_learned=["sik_yurt_disi_seyahat", "uluslararasi_ozellik_oncelikli", "premium_hizmet_tercih"],
                    sentiment="notr",
                ),
                InteractionRecord(
                    interaction_id=str(uuid.uuid4()),
                    session_id="seed-session-003b",
                    timestamp=datetime(2026, 3, 20, 15, 30, tzinfo=timezone.utc),
                    summary="Mevcut kurumsal tarife ile bireysel tarifeleri karsilastirmak istedi. Kurumsal avantajlarin detayli dokumu yapildi.",
                    topics=["tarife_karsilastirma", "kurumsal_bilgi"],
                    actions_taken=[],
                    unresolved_issues=["yurt_disi_paket_aktivasyon_bekliyor"],
                    preferences_learned=["detayli_analiz_tercih"],
                    sentiment="olumlu",
                ),
            ],
        }

        for customer_id, records in seeds.items():
            key = self._key(customer_id)
            if await r.exists(key):
                logger.debug("Seed skip — key already exists: %s", key)
                continue

            memory = CustomerMemory(
                customer_id=customer_id,
                interactions=records,
                last_updated=records[-1].timestamp,
            )
            await r.set(key, memory.model_dump_json(), ex=self._ttl)
            logger.info(
                "Seeded %d interactions for %s", len(records), customer_id
            )
