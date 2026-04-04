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

        greeting_text = "Merhaba"
        if live_session.customer_id:
            alerts = self._mock_bss.get_proactive_alerts(live_session.customer_id)
            if alerts:
                alert_lines = [a["message"] for a in alerts]
                greeting_text += ". Musteri uyarilari: " + " | ".join(alert_lines)

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

                            if is_action_tool(name):
                                # Gate behind confirmation
                                description = build_action_description(
                                    name, args, self._mock_bss
                                )
                                live_session.pending_tool_call = PendingToolCall(
                                    function_call=fc,
                                    name=name,
                                    args=args,
                                    description=description,
                                )
                                yield {
                                    "type": "action_proposal",
                                    "data": {
                                        "action_type": name,
                                        "description": description,
                                        "details": args,
                                    },
                                }
                            else:
                                # Safe tool — auto-execute and respond
                                result = await dispatch_tool(
                                    name, args, self._mock_bss, self._rag,
                                    customer_memory_service=self._customer_memory,
                                )
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
                customer_memory_service=self._customer_memory,
            )
            try:
                result_data = json.loads(result_str)
            except json.JSONDecodeError:
                result_data = {"result": result_str}

            yield {
                "type": "action_result",
                "data": {
                    "success": "error" not in result_data,
                    "action_type": pending.name,
                    "description": pending.description,
                    "details": result_data,
                },
            }
            tool_response_content = result_str
        else:
            yield {
                "type": "action_result",
                "data": {
                    "success": False,
                    "action_type": pending.name,
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
                    results = loop.run_until_complete(self._rag.search("Turkcell genel bilgi", top_k=5))
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

## Sesli Asistan Kurallari
- Turkce konusuyorsun. Yanit dilini her zaman Turkce tut.
- Kisa ve oz yanitlar ver. Sesli konusmada uzun paragraflardan kacin.
- Kisisel bilgileri (TC Kimlik, telefon, IBAN vb.) ASLA sesli olarak tekrarlama.
- Islem onay gerektiren durumlarda kullanicidan acik onay al.
- Konusma basladiginda kendini kisaca tanit ve nasil yardimci olabileceginizi sor. Ornek: "Merhaba! Ben Turkcell dijital asistaniyim. Fatura, tarife veya teknik destek konularinda size yardimci olabilirim. Nasil yardimci olabilirim?"
- Musteri hakkinda uyarilar (odenmemis fatura, asim, limit yakinligi) varsa, selamlamada bunlari nazikce belirt ve cozum oner.
- Asim durumunda kullaniciya uygun paket veya tarife onerisi yapabilecegini bildir.
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
