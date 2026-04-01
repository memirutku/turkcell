---
phase: 08-full-voice-conversation
plan: 02
subsystem: voice-ui
tags: [vad, silero, onnxruntime-web, conversation-mode, websocket, audio-queue, wav-encoder]

# Dependency graph
requires:
  - phase: 08-full-voice-conversation
    provides: Sentence-level TTS streaming via WebSocket audio_chunk protocol
  - phase: 07-voice-input-output
    provides: useVoiceChat hook, VoiceButton, VoiceStatusBanner, AudioWaveform, audioUtils
provides:
  - useVoiceConversation hook with VAD + WebSocket + audio queue orchestration
  - ConversationModeToggle component for entering/exiting conversation mode
  - SilenceIndicator component for silence countdown visualization
  - float32ToWavBlob encoder for VAD audio to WAV conversion
  - VAD configuration constants (vadConfig.ts)
  - Sentence-level audio queue in useVoiceChat (push-to-talk also benefits)
affects: [09-docker-compose-integration, 10-accessibility-hardening]

# Tech tracking
tech-stack:
  added: ["@ricky0123/vad-react", "@ricky0123/vad-web", "onnxruntime-web", "copy-webpack-plugin"]
  patterns: [vad-conversation-loop, audio-playback-queue, mutual-exclusion-mode-toggle, conversation-state-machine]

key-files:
  created:
    - frontend/src/hooks/useVoiceConversation.ts
    - frontend/src/lib/vadConfig.ts
    - frontend/src/components/chat/ConversationModeToggle.tsx
    - frontend/src/components/chat/SilenceIndicator.tsx
  modified:
    - frontend/next.config.mjs
    - frontend/src/lib/audioUtils.ts
    - frontend/src/types/index.ts
    - frontend/src/hooks/useVoiceChat.ts
    - frontend/src/components/chat/VoiceButton.tsx
    - frontend/src/components/chat/VoiceStatusBanner.tsx
    - frontend/src/components/chat/MessageInput.tsx
    - frontend/src/app/globals.css

key-decisions:
  - "Used conversationStateRef to avoid stale closure reads inside VAD and WebSocket callbacks"
  - "VAD pause/start are async (Promise) -- called without await in fire-and-forget contexts"
  - "Audio queue pattern shared between useVoiceConversation (conversation mode) and useVoiceChat (push-to-talk)"
  - "ConversationStatusArea as inline component in MessageInput for state-dependent status display"
  - "CSS keyframe animations in globals.css rather than Tailwind config for silence dot and breathing pulse"

patterns-established:
  - "Conversation state machine: off -> listening -> speech-detected -> processing -> playing -> listening (auto-loop)"
  - "Mutual exclusion: conversation mode and push-to-talk disable each other via prop-driven disabled states"
  - "Audio playback queue: sentence-level TTS chunks queued and played sequentially with auto-cleanup"
  - "VAD echo prevention: pause VAD on first audio arrival, resume after POST_PLAYBACK_DELAY_MS"

requirements-completed: [VOICE-03, VOICE-04, VOICE-07]

# Metrics
duration: 29min
completed: 2026-04-01
---

# Phase 8 Plan 02: VAD Conversation Mode UI Summary

**Browser-side Silero VAD integration with continuous conversation loop, sentence-level audio queue, and four-button MessageInput layout**

## Performance

- **Duration:** 29 min
- **Started:** 2026-04-01T05:26:25Z
- **Completed:** 2026-04-01T05:55:25Z
- **Tasks:** 2 completed, 1 checkpoint pending
- **Files modified:** 12

## Accomplishments
- Integrated @ricky0123/vad-react (Silero VAD v5) with ONNX Runtime Web for browser-side voice activity detection
- Built useVoiceConversation hook orchestrating VAD lifecycle, WebSocket communication, and audio playback queue for hands-free conversation
- Created ConversationModeToggle and SilenceIndicator components per UI-SPEC contract with full accessibility (aria-pressed, aria-hidden, aria-live)
- Extended VoiceStatusBanner with four conversation states and custom breathing-pulse/silence-dot CSS animations
- Updated useVoiceChat with sentence-level audio playback queue (benefits push-to-talk mode too)
- MessageInput layout updated to four-button pattern: textarea/status | ConvToggle | Mic | Send with mutual exclusion

## Task Commits

Each task was committed atomically:

1. **Task 1: VAD dependencies, webpack config, and conversation hook** - `ce594bf` (feat)
2. **Task 2: Conversation mode UI components and MessageInput integration** - `25d27df` (feat)
3. **Task 3: Visual and functional verification** - checkpoint (human-verify, pending)

## Files Created/Modified
- `frontend/src/hooks/useVoiceConversation.ts` - VAD + WebSocket + audio queue orchestration hook
- `frontend/src/lib/vadConfig.ts` - VAD parameter constants (thresholds, timing, asset paths)
- `frontend/src/lib/audioUtils.ts` - Added float32ToWavBlob encoder for VAD audio conversion
- `frontend/src/types/index.ts` - Added ConversationState type
- `frontend/src/components/chat/ConversationModeToggle.tsx` - Toggle button with MessageSquare/PhoneOff icons
- `frontend/src/components/chat/SilenceIndicator.tsx` - Three-dot silence countdown animation
- `frontend/src/components/chat/VoiceStatusBanner.tsx` - Extended with conversation mode states
- `frontend/src/components/chat/VoiceButton.tsx` - Added conversationActive prop for disabling
- `frontend/src/components/chat/MessageInput.tsx` - Rewritten with conversation mode integration
- `frontend/src/app/globals.css` - Added silence-dot-fade and breathing-pulse keyframes
- `frontend/next.config.mjs` - CopyPlugin webpack config for ONNX/WASM/worklet assets
- `frontend/src/hooks/useVoiceChat.ts` - Added sentence-level audio playback queue

## Decisions Made
- Used `conversationStateRef` alongside `conversationState` to prevent stale closure issues in VAD/WebSocket callbacks
- VAD `pause()` and `start()` are async (return Promise) but called in fire-and-forget style in event handlers
- Sentence-level audio queue pattern applied to both conversation mode (useVoiceConversation) and push-to-talk (useVoiceChat) -- both now benefit from incremental TTS playback
- ConversationStatusArea implemented as inline component in MessageInput rather than separate file (single usage, state-tightly-coupled)
- CSS animations (silence-dot-fade, breathing-pulse) placed in globals.css rather than extending Tailwind config -- simpler for custom sequential delay animations

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added conversationStateRef to prevent stale closure reads**
- **Found during:** Task 1 (useVoiceConversation hook)
- **Issue:** Plan's code used `conversationState` directly in callbacks (VAD onSpeechStart, ws.onclose, setTimeout handlers) which would be stale due to React closure semantics
- **Fix:** Added `conversationStateRef` that syncs via useEffect, used ref in all callback/timeout guards
- **Files modified:** frontend/src/hooks/useVoiceConversation.ts
- **Verification:** TypeScript compiles clean, no stale state reads possible
- **Committed in:** ce594bf (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Essential for correctness -- stale closure state would cause conversation mode to not properly detect "off" state in callbacks.

## Issues Encountered
- Worktree was behind main (missing Phase 7 and 8-01 commits) -- resolved by merging main into worktree
- Verified vad-react API uses ms-based parameters (redemptionMs, minSpeechMs, preSpeechPadMs) directly, no frame conversion needed

## User Setup Required

None - no external service configuration required.

## Known Stubs

None - all functionality is fully wired to existing services.

## Next Phase Readiness
- Task 3 checkpoint pending: human verification of conversation mode end-to-end in browser
- All code changes complete and TypeScript-clean
- Backend streaming pipeline (Plan 08-01) provides the WebSocket protocol consumed by this frontend

## Self-Check: PASSED

- All 12 files exist on disk (4 created, 8 modified)
- Both task commits verified in git log (ce594bf, 25d27df)
- SUMMARY.md created at expected path
- TypeScript compilation passes (npx tsc --noEmit exits 0)

---
*Phase: 08-full-voice-conversation*
*Completed: 2026-04-01 (Tasks 1-2; Task 3 checkpoint pending)*
