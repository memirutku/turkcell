---
phase: 07-voice-input-output
plan: 01
subsystem: voice
tags: [gemini-multimodal, aws-polly, boto3, pydub, stt, tts, websocket, voice-pipeline]

# Dependency graph
requires:
  - phase: 03-core-chat-llm-integration
    provides: ChatService with stream_response for LLM interaction
  - phase: 04-pii-masking-kvkk-compliance
    provides: PII masking pipeline applied before LLM calls
provides:
  - STTService for Gemini multimodal speech-to-text transcription
  - TTSService for AWS Polly Burcu neural Turkish TTS
  - VoiceService orchestrating STT -> Chat -> TTS pipeline
  - MockSTTService and MockTTSService for credential-free development
  - Voice WebSocket message schemas (Pydantic models)
affects: [07-02-voice-websocket-endpoint, 07-03-voice-ui, 08-full-voice-conversation]

# Tech tracking
tech-stack:
  added: [boto3, pydub, audioop-lts, google-genai (multimodal audio)]
  patterns: [asyncio.to_thread for blocking I/O, mock service pattern for credential-free dev, pydub WebM-to-WAV conversion]

key-files:
  created:
    - backend/app/services/stt_service.py
    - backend/app/services/tts_service.py
    - backend/app/services/voice_service.py
    - backend/app/models/voice_schemas.py
    - backend/tests/test_voice.py
  modified:
    - backend/pyproject.toml
    - backend/Dockerfile

key-decisions:
  - "Gemini multimodal for STT instead of AWS Transcribe -- simpler architecture, strong Turkish support, single API provider"
  - "Polly Burcu neural voice (not Filiz) -- newer, higher quality Turkish neural voice"
  - "audioop-lts added for Python 3.13+ compatibility with pydub"
  - "WebM-to-WAV conversion via pydub/ffmpeg at 16kHz mono for Gemini audio input"

patterns-established:
  - "Voice mock pattern: MockSTTService/MockTTSService for development without API credentials"
  - "asyncio.to_thread wrapping for all blocking boto3/genai calls"
  - "Polly POLLY_MAX_CHARS=2500 with sentence-boundary truncation"

requirements-completed: [VOICE-01, VOICE-02]

# Metrics
duration: 5min
completed: 2026-04-01
---

# Phase 7 Plan 01: Voice Services Backend Summary

**Gemini multimodal STT + AWS Polly Burcu neural TTS with VoiceService orchestrating the full voice pipeline**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-31T22:54:41Z
- **Completed:** 2026-03-31T22:59:59Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- STTService uses Gemini multimodal to transcribe audio directly, avoiding a separate AWS Transcribe dependency
- TTSService synthesizes Turkish speech via AWS Polly Burcu neural voice with character limit truncation
- VoiceService orchestrates the full STT -> ChatService -> TTS pipeline with WebM-to-WAV audio conversion
- Mock services (MockSTTService, MockTTSService) enable development without API credentials
- Voice WebSocket message schemas defined as Pydantic models for the WebSocket protocol (Plan 02)
- All 142 tests pass (7 new voice tests + 135 existing)

## Task Commits

Each task was committed atomically:

1. **Task 1: Install dependencies, Dockerfile ffmpeg, voice schemas** - `6ba13c6` (feat)
2. **Task 2 RED: Add failing voice tests** - `e2c4f33` (test)
3. **Task 2 GREEN: Implement STT, TTS, VoiceService** - `9b28113` (feat)

## Files Created/Modified
- `backend/app/services/stt_service.py` - Gemini multimodal STT with MockSTTService
- `backend/app/services/tts_service.py` - AWS Polly Burcu neural TTS with MockTTSService
- `backend/app/services/voice_service.py` - Voice pipeline orchestration (STT -> Chat -> TTS)
- `backend/app/models/voice_schemas.py` - Pydantic models for WebSocket voice message protocol
- `backend/tests/test_voice.py` - Unit tests for all voice services (7 tests + 1 skipped)
- `backend/pyproject.toml` - Added boto3, pydub, audioop-lts dependencies
- `backend/Dockerfile` - Added ffmpeg to runtime apt-get install

## Decisions Made
- Used Gemini multimodal for STT instead of AWS Transcribe -- simplifies architecture by using single API provider, leverages Gemini's strong Turkish language understanding
- Selected Polly Burcu neural voice (not Filiz) -- newer, higher quality Turkish neural voice as identified in research
- Added audioop-lts dependency for Python 3.13+ compatibility (audioop module removed from stdlib)
- POLLY_MAX_CHARS=2500 with sentence-boundary truncation to stay under Polly's 3000 char limit

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added audioop-lts for Python 3.13 pydub compatibility**
- **Found during:** Task 2 (TDD GREEN phase)
- **Issue:** pydub imports `audioop` which was removed from Python 3.13 stdlib, causing ModuleNotFoundError
- **Fix:** Installed `audioop-lts>=0.2.1` as a dependency in pyproject.toml
- **Files modified:** backend/pyproject.toml
- **Verification:** All 142 tests pass including pydub-dependent VoiceService tests
- **Committed in:** 9b28113 (Task 2 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Essential for Python 3.13 runtime compatibility. No scope creep.

## Issues Encountered
None beyond the audioop-lts issue documented above.

## User Setup Required
None - mock services allow development without AWS or Gemini credentials. Real credentials needed for production use (configured via existing .env AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, GEMINI_API_KEY).

## Known Stubs
None - all services are fully implemented with real and mock variants.

## Next Phase Readiness
- Voice services ready for WebSocket endpoint integration (Plan 02)
- VoiceService.process_voice() provides the complete pipeline that Plan 02's WebSocket handler will call
- Voice schemas define the WebSocket message protocol for Plan 02 and Plan 03 (UI)

## Self-Check: PASSED

- All 6 created files verified on disk
- All 3 commit hashes verified in git log
- 142/142 tests passing (7 voice + 135 existing)

---
*Phase: 07-voice-input-output*
*Completed: 2026-04-01*
