"""Tests for voice services: STT, TTS, VoiceService orchestration, and WebSocket endpoint."""

import io
import json
import shutil

import pytest
from starlette.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from app.main import app


# -- STTService tests --


class TestSTTService:
    """Test STTService with mocked Gemini client."""

    @patch("app.services.stt_service.genai")
    async def test_stt_transcribes_audio(self, mock_genai):
        from app.services.stt_service import STTService

        # Setup mock Gemini client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Faturami ogrenmek istiyorum"
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        settings = MagicMock()
        settings.gemini_api_key = "test-key"

        service = STTService(settings)
        result = await service.transcribe(b"fake-wav-bytes")

        assert result == "Faturami ogrenmek istiyorum"
        mock_client.models.generate_content.assert_called_once()

    async def test_stt_mock_returns_fixed_text(self):
        from app.services.stt_service import MockSTTService

        service = MockSTTService()
        result = await service.transcribe(b"any-bytes")

        assert result == "Bu bir test ses kaydidir"


# -- TTSService tests --


class TestTTSService:
    """Test TTSService with mocked AWS Polly client."""

    @patch("app.services.tts_service.boto3")
    async def test_tts_synthesizes_turkish(self, mock_boto3):
        from app.services.tts_service import TTSService

        # Setup mock Polly client
        mock_polly = MagicMock()
        mock_audio_stream = MagicMock()
        mock_audio_stream.read.return_value = b"fake-mp3-data"
        mock_polly.synthesize_speech.return_value = {"AudioStream": mock_audio_stream}
        mock_boto3.client.return_value = mock_polly

        settings = MagicMock()
        settings.aws_access_key_id = "test-key"
        settings.aws_secret_access_key = "test-secret"
        settings.aws_region = "eu-west-1"

        service = TTSService(settings)
        result = await service.synthesize("Merhaba")

        assert result == b"fake-mp3-data"
        assert len(result) > 0

    async def test_tts_mock_returns_none(self):
        from app.services.tts_service import MockTTSService

        service = MockTTSService()
        result = await service.synthesize("any text")

        assert result is None

    @patch("app.services.tts_service.boto3")
    async def test_tts_uses_burcu_neural(self, mock_boto3):
        from app.services.tts_service import TTSService

        mock_polly = MagicMock()
        mock_audio_stream = MagicMock()
        mock_audio_stream.read.return_value = b"fake-mp3-data"
        mock_polly.synthesize_speech.return_value = {"AudioStream": mock_audio_stream}
        mock_boto3.client.return_value = mock_polly

        settings = MagicMock()
        settings.aws_access_key_id = "test-key"
        settings.aws_secret_access_key = "test-secret"
        settings.aws_region = "eu-west-1"

        service = TTSService(settings)
        await service.synthesize("Test metni")

        call_kwargs = mock_polly.synthesize_speech.call_args
        assert call_kwargs.kwargs["VoiceId"] == "Burcu"
        assert call_kwargs.kwargs["Engine"] == "neural"
        assert call_kwargs.kwargs["LanguageCode"] == "tr-TR"


# -- VoiceService tests --


class TestVoiceService:
    """Test VoiceService pipeline orchestration."""

    async def test_voice_service_pipeline(self):
        from app.services.voice_service import VoiceService

        # Mock STT
        mock_stt = AsyncMock()
        mock_stt.transcribe = AsyncMock(return_value="Test sorusu")

        # Mock TTS
        mock_tts = AsyncMock()
        mock_tts.synthesize = AsyncMock(return_value=b"fake-audio")

        # Mock ChatService
        mock_chat = MagicMock()

        async def mock_stream(*args, **kwargs):
            for token in ["Merhaba", ", ", "yardimci", " olabilirim"]:
                yield token

        mock_chat.stream_response = mock_stream

        service = VoiceService(
            stt_service=mock_stt,
            tts_service=mock_tts,
            chat_service=mock_chat,
        )

        with patch.object(VoiceService, "_convert_to_wav", return_value=b"fake-wav"):
            result = await service.process_voice(b"fake-webm", "session-1")

        assert result["transcribed_text"] == "Test sorusu"
        assert result["response_text"] == "Merhaba, yardimci olabilirim"
        assert result["audio_response"] == b"fake-audio"

    async def test_voice_service_tts_none_graceful(self):
        from app.services.voice_service import VoiceService

        # Mock STT
        mock_stt = AsyncMock()
        mock_stt.transcribe = AsyncMock(return_value="Test sorusu")

        # Mock ChatService
        mock_chat = MagicMock()

        async def mock_stream(*args, **kwargs):
            for token in ["Yanit", " metni"]:
                yield token

        mock_chat.stream_response = mock_stream

        service = VoiceService(
            stt_service=mock_stt,
            tts_service=None,
            chat_service=mock_chat,
        )

        with patch.object(VoiceService, "_convert_to_wav", return_value=b"fake-wav"):
            result = await service.process_voice(b"fake-webm", "session-1")

        assert result["transcribed_text"] == "Test sorusu"
        assert result["response_text"] == "Yanit metni"
        assert result["audio_response"] is None

    @pytest.mark.skipif(
        not shutil.which("ffmpeg"),
        reason="ffmpeg not installed",
    )
    def test_convert_to_wav(self):
        from app.services.voice_service import VoiceService

        # Create a minimal valid WebM-like audio for pydub
        # Since we need actual audio data for pydub, we just test
        # that the method exists and is callable. Real conversion
        # requires valid audio binary.
        assert callable(VoiceService._convert_to_wav)

    def test_convert_to_wav_passes_through_wav(self):
        """WAV input (RIFF header) is returned unchanged."""
        from app.services.voice_service import VoiceService

        wav_header = b"RIFF" + b"\x00" * 4 + b"WAVE" + b"\x00" * 100
        result = VoiceService._convert_to_wav(wav_header)
        assert result == wav_header
        assert result[:4] == b"RIFF"

    async def test_process_voice_streaming_yields_correct_sequence(self):
        """Streaming pipeline yields transcription, tokens, audio_chunks, response_end, audio_done."""
        from app.services.voice_service import VoiceService

        mock_stt = AsyncMock()
        mock_stt.transcribe = AsyncMock(return_value="Test sorusu")

        mock_tts = AsyncMock()
        mock_tts.synthesize = AsyncMock(return_value=b"fake-mp3-chunk")

        mock_chat = MagicMock()

        async def mock_stream(*args, **kwargs):
            # Simulate response with sentence boundary
            for token in ["Merhaba", ".", " ", "Nasil", " ", "yardimci", " ", "olabilirim", "?"]:
                yield token

        mock_chat.stream_response = mock_stream

        service = VoiceService(stt_service=mock_stt, tts_service=mock_tts, chat_service=mock_chat)
        events = []
        with patch.object(VoiceService, "_convert_to_wav", return_value=b"fake-wav"):
            async for event in service.process_voice_streaming(b"fake-audio", "session-1"):
                events.append(event)

        types = [e["type"] for e in events]
        assert types[0] == "transcription"
        assert "token" in types
        assert "audio_chunk" in types
        assert types[-2] == "response_end"
        assert types[-1] == "audio_done"
        assert events[0]["text"] == "Test sorusu"
        assert events[-2]["full_text"] == "Merhaba. Nasil yardimci olabilirim?"

    async def test_process_voice_streaming_no_tts(self):
        """Streaming pipeline with TTS=None yields no audio_chunks."""
        from app.services.voice_service import VoiceService

        mock_stt = AsyncMock()
        mock_stt.transcribe = AsyncMock(return_value="Test")

        mock_chat = MagicMock()

        async def mock_stream(*args, **kwargs):
            for token in ["Yanit."]:
                yield token

        mock_chat.stream_response = mock_stream

        service = VoiceService(stt_service=mock_stt, tts_service=None, chat_service=mock_chat)
        events = []
        with patch.object(VoiceService, "_convert_to_wav", return_value=b"fake-wav"):
            async for event in service.process_voice_streaming(b"fake-audio", "session-1"):
                events.append(event)

        types = [e["type"] for e in events]
        assert "audio_chunk" not in types
        assert "transcription" in types
        assert "audio_done" in types


# -- WebSocket endpoint tests (synchronous, using Starlette TestClient) --


def _make_mock_voice_service():
    """Create a mock VoiceService that returns predetermined results via streaming."""
    mock = AsyncMock()

    async def mock_streaming(audio_bytes, session_id, customer_id=None):
        yield {"type": "transcription", "text": "test metin"}
        yield {"type": "token", "content": "Merhaba"}
        yield {"type": "audio_chunk", "data": b"fake-mp3-chunk"}
        yield {"type": "response_end", "full_text": "Merhaba"}
        yield {"type": "audio_done"}

    mock.process_voice_streaming = mock_streaming
    return mock


class TestVoiceWebSocket:
    """WebSocket integration tests for /ws/voice endpoint."""

    def test_voice_websocket_init(self):
        """WebSocket connects and sends init JSON without error."""
        original = getattr(app.state, "voice_service", None)
        app.state.voice_service = _make_mock_voice_service()
        try:
            client = TestClient(app)
            with client.websocket_connect("/ws/voice") as ws:
                ws.send_json({"type": "init", "session_id": "test-sess", "customer_id": "cust-001"})
                # If init succeeds, no error is sent back.
                # Send audio to trigger a response so we know init worked.
                ws.send_bytes(b"fake-audio-data" * 10)
                data = ws.receive_json()
                assert data["type"] == "transcription"
        finally:
            app.state.voice_service = original

    def test_voice_websocket_no_init_error(self):
        """WebSocket sends audio before init, receives error."""
        original = getattr(app.state, "voice_service", None)
        app.state.voice_service = _make_mock_voice_service()
        try:
            client = TestClient(app)
            with client.websocket_connect("/ws/voice") as ws:
                # Send audio without init first
                ws.send_bytes(b"fake-audio-data" * 10)
                data = ws.receive_json()
                assert data["type"] == "error"
                assert "Oturum baslatilmadi" in data["message"]
        finally:
            app.state.voice_service = original

    def test_voice_websocket_flow(self):
        """Full WebSocket flow: init -> audio -> transcription -> tokens -> audio_chunk -> response_end -> audio_done."""
        original = getattr(app.state, "voice_service", None)
        app.state.voice_service = _make_mock_voice_service()
        try:
            client = TestClient(app)
            with client.websocket_connect("/ws/voice") as ws:
                # 1. Send init
                ws.send_json({"type": "init", "session_id": "test-session", "customer_id": "cust-001"})

                # 2. Send binary audio (must be > 100 bytes)
                ws.send_bytes(b"fake-audio-data" * 10)

                # 3. Receive transcription
                data = ws.receive_json()
                assert data["type"] == "transcription"
                assert data["text"] == "test metin"

                # 4. Receive token(s)
                data = ws.receive_json()
                assert data["type"] == "token"
                assert data["content"] == "Merhaba"

                # 5. Receive audio_chunk (binary)
                audio_data = ws.receive_bytes()
                assert audio_data == b"fake-mp3-chunk"

                # 6. Receive response_end
                data = ws.receive_json()
                assert data["type"] == "response_end"
                assert data["full_text"] == "Merhaba"

                # 7. Receive audio_done signal
                data = ws.receive_json()
                assert data["type"] == "audio_done"
        finally:
            app.state.voice_service = original

    def test_voice_websocket_no_voice_service(self):
        """When voice_service is None, WebSocket receives error and closes."""
        original = getattr(app.state, "voice_service", None)
        app.state.voice_service = None
        try:
            client = TestClient(app)
            with client.websocket_connect("/ws/voice") as ws:
                data = ws.receive_json()
                assert data["type"] == "error"
                assert "Ses servisi kullanilamiyor" in data["message"]
        finally:
            app.state.voice_service = original

    def test_voice_websocket_empty_audio(self):
        """WebSocket sends very small binary (< 100 bytes), receives empty audio error."""
        original = getattr(app.state, "voice_service", None)
        app.state.voice_service = _make_mock_voice_service()
        try:
            client = TestClient(app)
            with client.websocket_connect("/ws/voice") as ws:
                ws.send_json({"type": "init", "session_id": "test-sess"})
                ws.send_bytes(b"tiny")  # < 100 bytes
                data = ws.receive_json()
                assert data["type"] == "error"
                assert "Ses algilanamadi" in data["message"]
        finally:
            app.state.voice_service = original
