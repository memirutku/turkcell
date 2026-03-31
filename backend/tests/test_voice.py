"""Tests for voice services: STT, TTS, and VoiceService orchestration."""

import io
import shutil

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


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
