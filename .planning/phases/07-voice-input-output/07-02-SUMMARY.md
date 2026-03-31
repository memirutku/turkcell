---
phase: 07-voice-input-output
plan: 02
subsystem: voice
tags: [websocket, fastapi, voice-pipeline, real-time, starlette-testclient]

# Dependency graph
requires:
  - phase: 07-voice-input-output
    plan: 01
    provides: STTService, TTSService, VoiceService, voice_schemas
  - phase: 03-core-chat-llm-integration
    provides: ChatService with stream_response
provides:
  - WebSocket /ws/voice endpoint with full voice protocol (init/audio/response)
  - Voice service initialization in FastAPI lifespan with graceful degradation
  - WebSocket integration tests covering all protocol paths
affects: [07-03-voice-ui, 08-full-voice-conversation]

# Tech tracking
tech-stack:
  added: []
  patterns: [WebSocket mixed text/binary frame handling with raw receive(), disconnect message type guard, Starlette TestClient for sync WebSocket testing]

key-files:
  created:
    - backend/app/api/routes/voice.py
  modified:
    - backend/app/main.py
    - backend/tests/test_voice.py
    - backend/pyproject.toml

key-decisions:
  - "WebSocket uses raw receive() for mixed text/binary frames with explicit disconnect type guard"
  - "No prefix for voice router -- WebSocket path /ws/voice defined directly in decorator"
  - "Starlette TestClient (sync) for WebSocket tests instead of async httpx (no native WS support)"
  - "audioop-lts dependency marker restricted to python_version >= 3.13 for cross-version compatibility"

patterns-established:
  - "WebSocket disconnect guard: check data.get('type') == 'websocket.disconnect' before processing frames"
  - "WebSocket test pattern: save/restore app.state attributes around TestClient tests"
  - "Voice service initialization chain: STT (Gemini) -> TTS (Polly, optional) -> VoiceService (requires chat_service)"

requirements-completed: [VOICE-05]

# Metrics
duration: 5min
completed: 2026-04-01
---

# Phase 7 Plan 02: Voice WebSocket Endpoint Summary

**WebSocket /ws/voice endpoint with init/audio/response protocol, lifespan wiring, and 5 integration tests covering all protocol paths**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-31T23:05:54Z
- **Completed:** 2026-03-31T23:11:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- WebSocket endpoint at /ws/voice handles the full voice protocol: init -> binary audio -> transcription JSON -> token streaming -> response_end -> TTS binary -> audio_done
- Voice services (STT, TTS, VoiceService) initialized in FastAPI lifespan with graceful degradation for missing credentials
- Error handling covers: no voice service, no init session, empty audio (<100 bytes), pipeline failures
- 5 WebSocket integration tests using Starlette TestClient verify all protocol paths
- All 147 tests pass (12 voice + 135 existing)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create WebSocket voice endpoint and wire services into lifespan** - `c6bd1a1` (feat)
2. **Task 2: Add WebSocket integration tests for the voice endpoint** - `71a596a` (test)

## Files Created/Modified
- `backend/app/api/routes/voice.py` - WebSocket /ws/voice endpoint with init/audio/response protocol
- `backend/app/main.py` - Voice service initialization in lifespan, voice router registration
- `backend/tests/test_voice.py` - 5 WebSocket integration tests added to existing voice test file
- `backend/pyproject.toml` - Fixed audioop-lts dependency marker for Python 3.12 compatibility

## Decisions Made
- Used raw `websocket.receive()` for mixed text/binary frame handling (FastAPI's standard approach for protocols mixing JSON and binary)
- Added explicit disconnect message type guard (`data.get("type") == "websocket.disconnect"`) to handle TestClient's disconnect signaling cleanly
- No prefix on voice router registration since WebSocket paths are absolute (/ws/voice)
- Used Starlette TestClient (synchronous) for WebSocket tests since httpx does not support native WebSocket testing

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed audioop-lts dependency marker for Python 3.12 compatibility**
- **Found during:** Task 1 (verification step)
- **Issue:** `audioop-lts>=0.2.1` requires Python >=3.13 but pyproject.toml `requires-python = ">=3.12"` caused uv resolution failure for Python 3.12 splits
- **Fix:** Changed to `audioop-lts>=0.2.1; python_version>='3.13'` (conditional dependency)
- **Files modified:** backend/pyproject.toml
- **Verification:** `uv sync` resolves successfully, all tests pass
- **Committed in:** c6bd1a1 (Task 1 commit)

**2. [Rule 1 - Bug] Added WebSocket disconnect message type guard**
- **Found during:** Task 2 (WebSocket test execution)
- **Issue:** Raw `websocket.receive()` returns `{"type": "websocket.disconnect"}` on client disconnect instead of raising `WebSocketDisconnect`. Server loop's next `receive()` call then raises RuntimeError.
- **Fix:** Added `if data.get("type") == "websocket.disconnect": break` before frame processing in the while loop
- **Files modified:** backend/app/api/routes/voice.py
- **Verification:** All 5 WebSocket tests pass cleanly without RuntimeError
- **Committed in:** 71a596a (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both fixes essential for correct operation. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviations documented above.

## User Setup Required
None - WebSocket endpoint uses the same credentials as Plan 01 services (GEMINI_API_KEY for STT, AWS credentials for TTS). Mock services work without any credentials.

## Known Stubs
None - endpoint is fully implemented with complete protocol handling and error cases.

## Next Phase Readiness
- WebSocket endpoint ready for frontend voice UI integration (Plan 03)
- Protocol fully defined: init -> audio -> transcription -> tokens -> response_end -> audio bytes -> audio_done
- Error messages are in Turkish, ready for user-facing display

## Self-Check: PASSED

- backend/app/api/routes/voice.py: FOUND
- backend/app/main.py: FOUND (modified)
- backend/tests/test_voice.py: FOUND (modified)
- Commit c6bd1a1: verified
- Commit 71a596a: verified
- 147/147 tests passing (12 voice + 135 existing)

---
*Phase: 07-voice-input-output*
*Completed: 2026-04-01*
