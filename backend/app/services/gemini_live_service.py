"""Gemini Live API session management for real-time bidirectional voice.

Manages per-connection Live API sessions that handle STT + LLM + TTS in a
single bidirectional WebSocket, replacing the sequential STT -> Chat -> TTS
pipeline for dramatically reduced latency.
"""

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from google import genai
from google.genai import types

from app.config import Settings
from app.prompts.agent_prompts import AGENT_SYSTEM_PROMPT
from app.services.billing_context import BillingContextService
from app.services.personalization_engine import get_conversation_style
from app.services.live_tools import (
    build_action_description,
    dispatch_tool,
    get_live_tool_declarations,
    is_action_tool,
)
from app.services.memory_service import MemoryService
from app.services.mock_bss import MockBSSService
from app.services.pii_service import PIIMaskingService
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

# Map raw tool names to frontend-compatible action_type values
_ACTION_TYPE_MAP = {
    "activate_package": "package_activation",
    "change_tariff": "tariff_change",
}


def _map_action_type(tool_name: str) -> str:
    return _ACTION_TYPE_MAP.get(tool_name, tool_name)


def _build_friendly_details(
    name: str, args: dict[str, Any], mock_bss: MockBSSService
) -> dict[str, str]:
    """Build user-friendly detail dict for action proposals (no raw IDs)."""
    if name == "activate_package":
        package_id = args.get("package_id", "")
        package = mock_bss.get_package(package_id) if hasattr(mock_bss, "get_package") else None
        if package:
            return {
                "Paket": package.name,
                "Ücret": f"{package.price_tl} TL",
                "Süre": f"{package.duration_days} gün",
            }
        return {"Paket": package_id}

    if name == "change_tariff":
        customer_id = args.get("customer_id", "")
        new_tariff_id = args.get("new_tariff_id", "")
        customer = mock_bss.get_customer(customer_id)
        new_tariff = mock_bss.get_tariff(new_tariff_id) if hasattr(mock_bss, "get_tariff") else None
        details: dict[str, str] = {}
        if customer and customer.tariff:
            details["Mevcut Tarife"] = customer.tariff.name
        if new_tariff:
            details["Yeni Tarife"] = new_tariff.name
            details["Aylık Ücret"] = f"{new_tariff.monthly_price_tl} TL"
        else:
            details["Yeni Tarife"] = new_tariff_id
        return details

    return {}


@dataclass
class PendingToolCall:
    """A tool call waiting for user confirmation."""

    function_call: Any  # google.genai types.FunctionCall
    name: str
    args: dict[str, Any]
    description: str


@dataclass
class GeminiLiveSession:
    """Wrapper around a single Live API session with state tracking."""

    session: Any  # google.genai.live.AsyncSession
    session_id: str
    customer_id: str | None
    pending_tool_call: PendingToolCall | None = None
    user_transcript: str = ""
    model_transcript: str = ""
    _closed: bool = False

    @property
    def is_closed(self) -> bool:
        return self._closed


class GeminiLiveService:
    """Manages Gemini Live API sessions for real-time voice interaction.

    Each browser WebSocket connection gets its own Live API session.
    The service handles:
    - Session creation with system instruction, tools, and voice config
    - Audio forwarding (browser PCM -> Gemini)
    - Response reading (Gemini audio/text/tool_calls -> browser)
    - Tool dispatch: safe tools auto-execute, action tools gate behind confirmation
    - Conversation memory persistence via Redis
    """

    def __init__(
        self,
        settings: Settings,
        mock_bss: MockBSSService,
        billing_context: BillingContextService,
        rag_service: RAGService | None = None,
        pii_service: PIIMaskingService | None = None,
        memory_service: MemoryService | None = None,
        customer_memory_service=None,
        personalization_engine=None,
    ) -> None:
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_live_model
        self._voice = settings.gemini_live_voice
        self._mock_bss = mock_bss
        self._billing_context = billing_context
        self._rag = rag_service
        self._pii = pii_service
        self._memory = memory_service
        self._customer_memory = customer_memory_service
        self._personalization_engine = personalization_engine

    @asynccontextmanager
    async def create_session(
        self,
        session_id: str,
        customer_id: str | None = None,
    ) -> AsyncIterator[GeminiLiveSession]:
        """Create a new Gemini Live API session as an async context manager.

        Builds system instruction with customer context and initial RAG results,
        configures tools and voice, then connects to the Live API.
        The session is automatically closed when the context exits.
        """
        # Build system instruction
        system_instruction = self._build_system_instruction(session_id, customer_id)

        # Configure Live API session
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=self._voice,
                    ),
                ),
            ),
            system_instruction=types.Content(
                parts=[types.Part(text=system_instruction)],
            ),
            tools=[types.Tool(function_declarations=get_live_tool_declarations())],
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
        )

        async with self._client.aio.live.connect(
            model=self._model,
            config=config,
        ) as session:
            logger.info(
                "Live API session created: session=%s customer=%s model=%s voice=%s",
                session_id,
                customer_id,
                self._model,
                self._voice,
            )

            live_session = GeminiLiveSession(
                session=session,
                session_id=session_id,
                customer_id=customer_id,
            )
            try:
                yield live_session
            finally:
                live_session._closed = True
                logger.info("Live API session closed: session=%s", session_id)

    async def send_greeting(self, live_session: GeminiLiveSession) -> None:
        """Send an initial greeting trigger so the model speaks first.

        If a customer_id is set, includes proactive alerts (unpaid bills,
        overages, near-limit usage) so the model can personalize the greeting.
        """
        if live_session.is_closed:
            return

        display_name = ""
        if live_session.customer_id:
            customer = self._mock_bss.get_customer(live_session.customer_id)
            if customer:
                name_parts = customer.name.split()
                display_name = name_parts[0]

        if display_name:
            greeting_text = (
                f"Merhaba {display_name}! Ben Umay müşteri hizmetleri asistanıyım. "
                f"Size nasıl yardımcı olabilirim?"
            )
        else:
            greeting_text = (
                "Merhaba! Ben Umay müşteri hizmetleri asistanıyım. "
                "Size nasıl yardımcı olabilirim?"
            )

        if live_session.customer_id:
            alerts = self._mock_bss.get_proactive_alerts(live_session.customer_id)
            if alerts:
                alert_lines = [a["message"] for a in alerts]
                greeting_text += " Müşteri uyarıları: " + " | ".join(alert_lines)

        await live_session.session.send_realtime_input(text=greeting_text)

    async def send_audio(
        self,
        live_session: GeminiLiveSession,
        audio_chunk: bytes,
    ) -> None:
        """Forward raw PCM16 audio from the browser to the Live API session."""
        if live_session.is_closed:
            logger.debug("send_audio: dropping %d bytes, session closed", len(audio_chunk))
            return
        await live_session.session.send_realtime_input(
            audio=types.Blob(
                mime_type="audio/pcm;rate=16000",
                data=audio_chunk,
            ),
        )

    async def read_responses(
        self,
        live_session: GeminiLiveSession,
    ) -> AsyncIterator[dict]:
        """Read responses from the Live API session.

        Yields event dicts:
        - {"type": "audio", "data": bytes}  — PCM16 audio chunk
        - {"type": "text", "text": str}     — text transcript delta
        - {"type": "turn_complete"}         — model finished speaking
        - {"type": "interrupted"}            — user interrupted model speech
        - {"type": "action_proposal", "data": {...}} — action needing confirmation
        - {"type": "action_result", "data": {...}}   — action execution result
        - {"type": "error", "message": str}
        """
        try:
            # SDK's receive() terminates its iterator after each turn_complete,
            # so we must re-call it for each new turn.
            while not live_session.is_closed:
                async for response in live_session.session.receive():
                    if live_session.is_closed:
                        break

                    # Handle server content (audio + text)
                    if response.server_content is not None:
                        content = response.server_content

                        if content.model_turn is not None:
                            for part in content.model_turn.parts:
                                if part.inline_data is not None:
                                    yield {"type": "audio", "data": part.inline_data.data}
                                if part.text is not None:
                                    live_session.model_transcript += part.text
                                    yield {"type": "text", "text": part.text}

                        if content.turn_complete:
                            # Persist conversation turn to memory
                            await self._persist_turn(live_session)
                            yield {"type": "turn_complete"}

                        if content.interrupted:
                            logger.info(
                                "Model interrupted by user: session=%s",
                                live_session.session_id,
                            )
                            yield {"type": "interrupted"}

                        if content.input_transcription is not None:
                            transcript = content.input_transcription.text
                            if transcript:
                                live_session.user_transcript = transcript
                                yield {"type": "input_transcript", "text": transcript}

                        if content.output_transcription is not None:
                            transcript = content.output_transcription.text
                            if transcript:
                                yield {"type": "output_transcript", "text": transcript}

                    # Handle tool calls
                    if response.tool_call is not None:
                        for fc in response.tool_call.function_calls:
                            name = fc.name
                            args = dict(fc.args) if fc.args else {}

                            # Propose action: yield info card (no buttons)
                            if name == "propose_action":
                                action_type = args.get("action_type", "tariff_change")
                                proposal_name = args.get("name", "")
                                price = args.get("price", "")
                                features = args.get("features", "")
                                description = f"{proposal_name} — {price}"
                                details = {"Tarife/Paket": proposal_name, "Fiyat": price}
                                if features:
                                    details["Özellikler"] = features
                                yield {
                                    "type": "action_proposal",
                                    "data": {
                                        "action_type": action_type,
                                        "description": description,
                                        "details": details,
                                    },
                                }

                            # Auto-execute all tools (model handles confirmation via voice)
                            result = await dispatch_tool(
                                name, args, self._mock_bss, self._rag,
                                personalization_engine=self._personalization_engine,
                                customer_memory_service=self._customer_memory,
                            )

                            # Action tools: yield result card for frontend UI
                            if is_action_tool(name):
                                try:
                                    result_data = json.loads(result)
                                except json.JSONDecodeError:
                                    result_data = {"result": result}
                                action_type = _map_action_type(name)
                                success = result_data.get("success", "error" not in result_data)
                                result_desc = result_data.get("message_tr", build_action_description(name, args, self._mock_bss))
                                friendly = {}
                                if result_data.get("transaction_id"):
                                    friendly["İşlem No"] = result_data["transaction_id"]
                                if name == "change_tariff" and result_data.get("new_tariff"):
                                    t = result_data["new_tariff"]
                                    friendly["Yeni Tarife"] = t.get("name", "")
                                    friendly["Aylık Ücret"] = f"{t.get('monthly_price_tl', '')} TL"
                                elif name == "activate_package" and result_data.get("package"):
                                    p = result_data["package"]
                                    friendly["Paket"] = p.get("name", "")
                                    friendly["Ücret"] = f"{p.get('price_tl', '')} TL"
                                    friendly["Süre"] = f"{p.get('duration_days', '')} gün"
                                yield {
                                    "type": "action_result",
                                    "data": {
                                        "success": success,
                                        "action_type": action_type,
                                        "description": result_desc,
                                        "details": friendly,
                                    },
                                }

                            await live_session.session.send_tool_response(
                                function_responses=[
                                    types.FunctionResponse(
                                        name=name,
                                        id=fc.id,
                                        response={"result": result},
                                    ),
                                ],
                            )

                logger.debug(
                    "receive() iterator completed (turn ended), re-entering: session=%s",
                    live_session.session_id,
                )

        except Exception as e:
            if not live_session.is_closed:
                logger.exception("Live API read error: %s", e)
                yield {"type": "error", "message": f"Live API hatasi: {e}"}

        logger.info("read_responses generator finished: session=%s", live_session.session_id)

    async def handle_confirmation(
        self,
        live_session: GeminiLiveSession,
        approved: bool,
    ) -> AsyncIterator[dict]:
        """Handle user confirmation for a pending action tool call.

        Executes the action if approved, sends cancellation if rejected,
        then sends the tool response to Gemini so it can continue.
        """
        pending = live_session.pending_tool_call
        if pending is None:
            yield {"type": "error", "message": "Bekleyen islem yok."}
            return

        if approved:
            result_str = await dispatch_tool(
                pending.name, pending.args, self._mock_bss, self._rag,
                personalization_engine=self._personalization_engine,
                customer_memory_service=self._customer_memory,
            )
            try:
                result_data = json.loads(result_str)
            except json.JSONDecodeError:
                result_data = {"result": result_str}

            action_type = _map_action_type(pending.name)
            success = result_data.get("success", "error" not in result_data)
            result_desc = result_data.get("message_tr", pending.description)
            # Build user-friendly details from result
            friendly = {}
            if result_data.get("transaction_id"):
                friendly["Islem No"] = result_data["transaction_id"]
            if pending.name == "change_tariff" and result_data.get("new_tariff"):
                t = result_data["new_tariff"]
                friendly["Yeni Tarife"] = t.get("name", "")
                friendly["Aylik Ucret"] = f"{t.get('monthly_price_tl', '')} TL"
            elif pending.name == "activate_package" and result_data.get("package"):
                p = result_data["package"]
                friendly["Paket"] = p.get("name", "")
                friendly["Ucret"] = f"{p.get('price_tl', '')} TL"
                friendly["Sure"] = f"{p.get('duration_days', '')} gun"
            yield {
                "type": "action_result",
                "data": {
                    "success": success,
                    "action_type": action_type,
                    "description": result_desc,
                    "details": friendly,
                },
            }
            tool_response_content = result_str
        else:
            action_type = _map_action_type(pending.name)
            yield {
                "type": "action_result",
                "data": {
                    "success": False,
                    "action_type": action_type,
                    "description": "Islem kullanici tarafindan iptal edildi.",
                    "details": {},
                },
            }
            tool_response_content = json.dumps(
                {"status": "cancelled", "message": "Kullanici islemi iptal etti."},
                ensure_ascii=False,
            )

        # Send tool response to Gemini so it can continue
        await live_session.session.send_tool_response(
            function_responses=[
                types.FunctionResponse(
                    name=pending.name,
                    id=pending.function_call.id,
                    response={"result": tool_response_content},
                ),
            ],
        )

        live_session.pending_tool_call = None

    def _build_system_instruction(
        self,
        session_id: str,
        customer_id: str | None,
    ) -> str:
        """Build the system instruction with customer context and conversation history."""
        # Customer context
        customer_context = ""
        if customer_id:
            customer_context = self._billing_context.get_customer_context(customer_id) or ""

        # Initial RAG context (general FAQ)
        rag_context = ""
        if self._rag:
            try:
                # Synchronous call wrapped — RAG search is fast enough for session init
                import asyncio

                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # We're already in an async context, use a simple approach
                    rag_context = "(RAG baglami oturum sirasinda arac cagrisi ile alinacaktir)"
                else:
                    results = loop.run_until_complete(self._rag.search("Umay genel bilgi", top_k=5))
                    rag_context = "\n".join(r["content"] for r in results)
            except Exception:
                logger.debug("Initial RAG fetch failed, will use tool-based retrieval")

        # Conversation history
        history_context = ""
        if self._memory:
            past_messages = self._memory.get_history(session_id)
            if past_messages:
                history_lines = []
                for msg in past_messages[-10:]:
                    role = "Kullanici" if msg.type == "human" else "Asistan"
                    history_lines.append(f"{role}: {msg.content}")
                history_context = (
                    "\n\n## Onceki Konusma\n" + "\n".join(history_lines)
                )

        # Customer memory (cross-session)
        memory_context = "Bu musteri icin onceki etkilesim kaydi bulunamadi."
        if customer_id and self._customer_memory:
            try:
                import asyncio

                # _build_system_instruction is sync; run async get_memory inline
                memory = asyncio.get_event_loop().run_until_complete(
                    self._customer_memory.get_memory(customer_id)
                ) if not asyncio.get_event_loop().is_running() else None

                # If we're inside a running loop, we can't block — memory will
                # be available through the get_customer_memory tool instead.
                if memory and memory.interactions:
                    lines = []
                    for inter in memory.interactions[-5:]:
                        lines.append(f"- [{inter.timestamp:%Y-%m-%d}] {inter.summary}")
                        if inter.unresolved_issues:
                            lines.append(f"  Cozulmemis: {', '.join(inter.unresolved_issues)}")
                        if inter.preferences_learned:
                            lines.append(f"  Tercihler: {', '.join(inter.preferences_learned)}")
                    memory_context = "\n".join(lines)
            except Exception:
                logger.debug("Customer memory fetch skipped in sync context, tool-based retrieval will be used")

        # Resolve conversation style based on customer segment
        conversation_style = get_conversation_style()
        if customer_id:
            customer = self._mock_bss.get_customer(customer_id)
            if customer:
                conversation_style = get_conversation_style(
                    customer.segment or "default",
                    customer.contract_type or "bireysel",
                )

        # Build from agent prompt template
        system_text = AGENT_SYSTEM_PROMPT.format(
            customer_memory=memory_context,
            customer_context=customer_context or "Musteri bilgisi mevcut degil.",
            rag_context=rag_context or "Bilgi tabani arama araci ile sorgulanabilir.",
            conversation_style=conversation_style,
        )

        # Add Live API specific instructions
        system_text += """

## Sesli Asistan Kuralları
- Türkçe konuşuyorsun. Yanıt dilini her zaman Türkçe tut.
- Kısa ve öz yanıtlar ver. Sesli konuşmada uzun paragraflardan kaçın.
- Kişisel bilgileri (TC Kimlik, telefon, IBAN vb.) ASLA sesli olarak tekrarlama.
- Konuşma başladığında kendini kısaca tanıt ve nasıl yardımcı olabileceğini sor. Örnek: "Merhaba [Müşteri Adı]! Ben Umay müşteri hizmetleri asistanıyım. Fatura, tarife veya teknik destek konularında size yardımcı olabilirim. Nasıl yardımcı olabilirim?"
- Müşteri hakkında uyarılar (ödenmemiş fatura, aşım, limit yakınlığı) varsa, selamlamada bunları nazikçe belirt ve çözüm öner.
- Aşım durumunda kullanıcıya uygun paket veya tarife önerisi yapabileceğini bildir.
- Müşteri paket önerisi istediğinde, paketleri sunduktan sonra tarife değişikliği de teklif et: "Tarifenizi de gözden geçirmek ister misiniz?"
- Müşteri paket veya tarife önerisi istediğinde, kullanım verisine dayanarak neden bu öneriyi yaptığını açıkla. Örneğin: "İnternet kullanımınız yüksek, bu yüzden size daha fazla internet içeren paketleri getiriyorum."

## Tarife/Paket Değişikliği Onay Akışı (ÇOK KRİTİK)
Tarife değişikliği veya paket aktivasyonu gibi işlemlerde aşağıdaki adımları SIRASI İLE takip et:

1. **Bilgi kartı göster**: Önce `propose_action` aracını çağır. Bu araç ekranda bilgi kartı gösterir. Parametreler: action_type ("tariff_change" veya "package_activation"), name (tarife/paket adı), price (fiyat), features (özellikler).
2. **Sesli onay al**: "Bu tarifeye/pakete geçmek ister misiniz?" diye sor. change_tariff veya activate_package aracını çağırmadan ÖNCE müşterinin sesli onayını MUTLAKA bekle.
3. **Onay gelirse tool çağır**: Müşteri "evet", "olur", "yapalım", "tamam", "onaylıyorum" gibi onay verdiyse, ilgili aracı (change_tariff veya activate_package) HEMEN çağır. Sadece sözlü olarak "değiştiriyorum" deme — gerçek işlem aracını çalıştır.
4. **Sonucu bildir**: İşlem başarılıysa "Yeni [tarife/paket adı] hayırlı olsun!" de ve kısaca tanıt. Başarısızsa nedenini açıkla.
5. **Devam et**: "Başka bir isteğiniz var mı?" diye sor.

YASAK: Müşteri henüz onay vermeden change_tariff veya activate_package aracını çağırma. Önce propose_action çağır, sesli onay al, sonra işlem aracını çağır.
"""

        if history_context:
            system_text += history_context

        return system_text

    async def _persist_turn(self, live_session: GeminiLiveSession) -> None:
        """Persist the current conversation turn to Redis."""
        if not self._memory:
            return

        user_text = live_session.user_transcript.strip()
        model_text = live_session.model_transcript.strip()

        if not user_text and not model_text:
            return

        # PII mask before storage
        if self._pii and user_text:
            user_text = self._pii.mask(user_text)

        if user_text or model_text:
            try:
                self._memory.add_messages(
                    live_session.session_id,
                    user_text or "(ses girisi)",
                    model_text or "(yanit yok)",
                )
            except Exception:
                logger.debug("Failed to persist turn to memory", exc_info=True)

        # Reset for next turn
        live_session.user_transcript = ""
        live_session.model_transcript = ""
