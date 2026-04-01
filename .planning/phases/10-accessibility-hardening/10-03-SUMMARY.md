---
phase: 10-accessibility-hardening
plan: "03"
subsystem: ui
tags: [accessibility, voice-agent, screen-reader, websocket, focus-management, a11y]

# Dependency graph
requires:
  - phase: 10-accessibility-hardening/01
    provides: ARIA landmarks, skip navigation, focus-visible styles, sr-only utility
  - phase: 10-accessibility-hardening/02
    provides: Voice-agent backend with action_proposal, action_result, confirmation_prompt WebSocket events
provides:
  - Frontend voice-agent WebSocket message handling in useVoiceConversation
  - Centralized ScreenReaderAnnouncer component for dynamic content announcements
  - chatStore announce() method for screen reader notifications
  - Focus management for new assistant messages with preventScroll
  - Screen reader announcements for all dynamic state changes
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: [centralized screen reader announcer, aria-live assertive, focus management with preventScroll]

key-files:
  created:
    - frontend/src/components/a11y/ScreenReaderAnnouncer.tsx
  modified:
    - frontend/src/hooks/useVoiceConversation.ts
    - frontend/src/stores/chatStore.ts
    - frontend/src/components/chat/ChatContainer.tsx
    - frontend/src/components/chat/MessageInput.tsx
    - frontend/src/app/layout.tsx
    - frontend/src/types/index.ts

key-decisions:
  - "Centralized ScreenReaderAnnouncer over per-component aria-live regions for consistent announcements"
  - "announce() uses 1s setTimeout to clear srAnnouncement, preventing stale reads"
  - "Focus moves to last assistant message on streaming complete, not on every token"
  - "preventScroll: true on focus() to avoid jarring scroll jumps for sighted users"
  - "Customer name lookup map in chatStore for meaningful SR customer change announcements"

patterns-established:
  - "Centralized announcer: all dynamic content changes go through useChatStore.announce()"
  - "Focus management: useEffect on isStreaming change triggers focus on last assistant message"

requirements-completed: [A11Y-02, A11Y-03]

# Metrics
duration: 6min
completed: 2026-04-01

# Self-Check
self_check: PASSED
---

# Plan 10-03: Frontend Voice-Agent Wiring & Screen Reader Announcements

**Complete eyes-free voice-agent workflow with centralized screen reader announcements and focus management for all dynamic state changes.**

## What was built

### Voice-agent WebSocket message handling
- `useVoiceConversation.ts` now handles three new WebSocket message types: `action_proposal`, `action_result`, `confirmation_prompt`
- Action proposals trigger `setPendingAction()` and `addStructuredData()` to display ActionConfirmationCard
- Action results clear pending state and add result structured data
- Confirmation prompts are announced via screen reader

### Centralized ScreenReaderAnnouncer
- Created `ScreenReaderAnnouncer.tsx` component with `role="status"` and `aria-live="assertive"`
- Wired into `layout.tsx` as last child of body
- `chatStore` extended with `srAnnouncement: string` and `announce(text: string)` method
- All dynamic state changes route through this single announcer

### Screen reader announcements added for:
- Action proposals: "Islem onerisi: {type}. {description}. Onaylamak icin..."
- Action results: "Islem basarili/basarisiz: {description}"
- Confirmation prompts: text relayed from backend
- Customer changes: "Musteri degistirildi: {name}"
- Conversation mode toggle: "Sesli konusma modu aktif/kapatildi"
- Recommendations: "Tarife onerisi alindi: {name}, aylik {savings} TL tasarruf"

### Focus management
- `ChatContainer.tsx` auto-focuses last assistant message when streaming completes
- Uses `preventScroll: true` to avoid scroll jumps
- Messages have `tabIndex={-1}` (from Plan 01) enabling programmatic focus

## Deviations

1. **[Rule 3 - Blocking] ScreenReaderAnnouncer and announce() created in Plan 03 instead of Plan 01**
   - Plan assumed these existed from Plan 01, but Plan 01 only added ARIA attributes to existing components
   - Created the component and chatStore extensions here as a blocking dependency

## Verification

- TypeScript compilation: PASS (zero errors)
- Backend voice agent tests: PASS (21/21)
- Human verification: APPROVED (code review + automated checks)
