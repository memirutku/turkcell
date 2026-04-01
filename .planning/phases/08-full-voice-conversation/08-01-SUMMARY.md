---
phase: 08-full-voice-conversation
plan: 01
subsystem: voice
tags: [websocket, tts, streaming, sentence-boundary, wav, async-generator, pydub]

# Dependency graph
requires:
  - phase: 07-voice-input-output
    provides: VoiceService with process_voice(), STT/TTS services, WebSocket /ws/voice endpoint
provides:
  - process_voice_streaming async generator for sentence-level TTS
  - WAV auto-detection in _convert_to_wav (skips pydub for RIFF input)
  - audio_chunk WebSocket protocol for incremental TTS delivery
  - SENTENCE_BOUNDARY regex for splitting LLM output at sentence ends
affects: [08-full-voice-conversation, 10-accessibility-hardening]

# Tech tracking
tech-stack:
  added: []
  patterns: [async-generator-pipeline, sentence-boundary-tts, wav-format-detection]

key-files:
  created: []
  modified:
    - backend/app/services/voice_service.py
    - backend/app/models/voice_schemas.py
    - backend/app/api/routes/voice.py
    - backend/tests/test_voice.py

key-decisions:
  - "Sentence boundary regex (?<=[.!?])\\s+ for splitting LLM output into TTS chunks"
  - "WAV detected via RIFF+WAVE header bytes (positions 0:4 and 8:12)"
  - "audio_chunk events yield binary data in dict, WebSocket sends via send_bytes()"
  - "Existing process_voice() kept for backward compatibility but no longer called by endpoint"

patterns-established:
  - "Async generator pipeline: process_voice_streaming yields typed dicts for incremental WebSocket delivery"
  - "WAV auto-detection: check RIFF header before pydub conversion to skip unnecessary ffmpeg calls"

requirements-completed: [VOICE-03, VOICE-07]

# Metrics
duration: 18min
completed: 2026-04-01
---

# Phase 8 Plan 01: Sentence-Level TTS Streaming Summary

**Sentence-boundary TTS streaming via async generator with WAV auto-detection and incremental audio_chunk WebSocket delivery**

## Performance

- **Duration:** 18 min
- **Started:** 2026-04-01T04:42:18Z
- **Completed:** 2026-04-01T05:00:27Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- WAV format auto-detection in `_convert_to_wav` skips pydub/ffmpeg when input has RIFF header (prerequisite for Phase 8 VAD path)
- `process_voice_streaming` async generator splits LLM response at sentence boundaries and synthesizes TTS per sentence, yielding audio_chunk events incrementally
- WebSocket endpoint upgraded from batch `process_voice()` to streaming `process_voice_streaming()` -- audio chunks arrive before full LLM response completes
- Full backend test suite green: 150 passed, 3 skipped

## Task Commits

Each task was committed atomically:

1. **Task 1: WAV auto-detection + sentence-level TTS streaming** - `d6eb5e5` (test: RED), `e6ec19e` (feat: GREEN)
2. **Task 2: Upgrade WebSocket endpoint to streaming pipeline** - `d68bcdd` (feat)

## Files Created/Modified
- `backend/app/services/voice_service.py` - Added SENTENCE_BOUNDARY regex, process_voice_streaming async generator, WAV header detection in _convert_to_wav
- `backend/app/models/voice_schemas.py` - Added VoiceAudioChunk schema for protocol documentation
- `backend/app/api/routes/voice.py` - Replaced process_voice() with process_voice_streaming() in WebSocket handler, updated protocol docs
- `backend/tests/test_voice.py` - Added 3 new tests (WAV passthrough, streaming sequence, no-TTS), updated WebSocket mock and flow test

## Decisions Made
- Used `(?<=[.!?])\s+` regex for sentence boundary detection -- simple but effective for Turkish text which uses the same sentence-ending punctuation as English
- WAV detection checks bytes at positions 0:4 (RIFF) and 8:12 (WAVE) with minimum 12-byte length guard
- Kept `process_voice()` method for backward compatibility even though it is no longer called by the endpoint
- audio_chunk events carry binary data in a dict `{"type": "audio_chunk", "data": bytes}` -- the WebSocket handler dispatches binary via `send_bytes()` directly

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Worktree was behind main branch (missing Phase 7 commits) -- resolved by merging main into worktree
- uv virtual environment needed explicit `--extra dev` sync for pytest -- standard issue with optional dependency groups

## User Setup Required

None - no external service configuration required.

## Known Stubs

None - all functionality is fully wired to existing services.

## Next Phase Readiness
- Backend streaming pipeline ready for Plan 02 (frontend conversation mode with VAD)
- `process_voice_streaming` provides the incremental audio delivery needed for continuous hands-free conversation
- WAV auto-detection enables direct VAD-recorded audio without format conversion overhead

## Self-Check: PASSED

- All 4 modified files exist on disk
- All 3 commits verified in git log (d6eb5e5, e6ec19e, d68bcdd)
- SUMMARY.md created at expected path

---
*Phase: 08-full-voice-conversation*
*Completed: 2026-04-01*
