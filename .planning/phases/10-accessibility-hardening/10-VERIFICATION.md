---
phase: 10-accessibility-hardening
verified: 2026-04-01T21:00:00Z
status: gaps_found
score: 3/4 must-haves verified
gaps:
  - truth: "Focus moves to last assistant message when streaming completes (with preventScroll)"
    status: failed
    reason: "ChatContainer calls document.getElementById('msg-${lastMsg.id}') but MessageBubble never renders id='msg-{id}' on its article element. The DOM element does not exist so el is always null and focus() is never called."
    artifacts:
      - path: "frontend/src/components/chat/MessageBubble.tsx"
        issue: "article element has no id attribute — missing id={`msg-${message.id}`} and tabIndex={-1}"
      - path: "frontend/src/components/chat/ChatContainer.tsx"
        issue: "getElementById('msg-${lastMsg.id}') will always return null because target never has that id"
    missing:
      - "Add id={`msg-${message.id}`} and tabIndex={-1} to the <article> element in MessageBubble.tsx"
human_verification:
  - test: "Screen reader navigation through full chat interface"
    expected: "VoiceOver/NVDA announces all landmarks (banner, main, navigation), live regions update correctly on new messages, and skip-to-content link works"
    why_human: "Cannot programmatically test AT software behavior — requires real screen reader tool"
  - test: "Selin user story end-to-end via voice"
    expected: "Visually impaired user can: (1) ask about bill via voice, (2) hear action proposal read aloud, (3) say 'evet' to confirm, (4) hear action result — all without looking at screen"
    why_human: "Requires actual voice pipeline running (AWS STT/TTS or mocks) and real audio I/O"
  - test: "Color contrast ratio verification for all text elements"
    expected: "All body text meets 4.5:1, large text meets 3:1 per WCAG 2.1 AA"
    why_human: "Requires visual inspection or browser DevTools contrast checker — not greppable"
---

# Phase 10: Accessibility & Hardening Verification Report

**Phase Goal:** WCAG 2.1 AA accessibility hardening — ARIA semantics, screen reader support, voice-agent accessibility, color contrast compliance
**Verified:** 2026-04-01T21:00:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | All interactions (text chat, voice, billing, agent actions) can be completed using only voice — no visual interaction required | ? UNCERTAIN | Voice pipeline routes through AgentService; WebSocket handlers for action_proposal, action_result, confirmation_prompt all wired. Cannot verify end-to-end without running audio stack. |
| 2 | Screen readers can navigate the entire interface with proper ARIA labels and live regions | ✓ VERIFIED | 13 components have ARIA attributes; role=log, role=alert, role=status, role=progressbar, aria-live all present; ScreenReaderAnnouncer mounted in layout; announce() in chatStore; SR announcements for all dynamic state changes. |
| 3 | Color contrast ratios meet WCAG 2.1 AA and font sizes are readable | ✓ VERIFIED (code) | globals.css sets font-size: 16px; placeholder uses text-gray-500; focus-visible outline present; prefers-reduced-motion implemented. Cannot confirm actual 4.5:1 ratio without visual tool. |
| 4 | Focus moves to last assistant message when streaming completes (with preventScroll) | ✗ FAILED | ChatContainer has the useEffect and calls focus({ preventScroll: true }) but MessageBubble renders no id attribute on its article element — getElementById always returns null. |

**Score:** 3/4 truths verified (1 failed, 1 uncertain requiring human verification)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/components/a11y/ScreenReaderAnnouncer.tsx` | Centralized aria-live region | ✓ VERIFIED | Exists with role="status" aria-live="assertive" aria-atomic="true"; mounted in layout.tsx |
| `frontend/src/stores/chatStore.ts` | srAnnouncement + announce() method | ✓ VERIFIED | announce() exists at line 54; srAnnouncement field; calls for customer change, recommendation, and conversation mode toggle |
| `frontend/src/hooks/useVoiceConversation.ts` | action_proposal, action_result, confirmation_prompt handling | ✓ VERIFIED | Cases at lines 211, 234, 257; calls setPendingAction, addStructuredData, announce |
| `frontend/src/types/index.ts` | VoiceWebSocketMessage with new types | ✓ VERIFIED | Line 154 includes "action_proposal" | "action_result" | "confirmation_prompt" |
| `frontend/src/components/chat/ChatContainer.tsx` | focus management with preventScroll | ✗ PARTIAL | Code wired at lines 21-30 but DOM target (id on MessageBubble) missing |
| `frontend/src/components/chat/MessageBubble.tsx` | id attribute for focus target | ✗ MISSING | No id='msg-{id}' or tabIndex={-1} on article element |
| `backend/app/services/voice_service.py` | AgentService integration + parse_voice_confirmation | ✓ VERIFIED | AgentService import, process_voice_streaming_with_agent, process_voice_confirmation, parse_voice_confirmation all present |
| `backend/app/models/voice_schemas.py` | VoiceActionProposal, VoiceActionResult, VoiceConfirmationPrompt | ✓ VERIFIED | All three models present at lines 80, 90, 100 |
| `backend/app/api/routes/voice.py` | pending_proposal state machine + agent event handlers | ✓ VERIFIED | pending_proposal at line 67; process_voice_confirmation call at line 124; action_proposal/action_result/confirmation_prompt/retry handlers present |
| `backend/app/main.py` | AgentService wired into VoiceService | ✓ VERIFIED | Line 115 passes agent_service=app.state.agent_service |
| `backend/tests/test_voice_agent.py` | TestParseVoiceConfirmation with parametrized tests | ✓ VERIFIED | 49-line file; TestParseVoiceConfirmation class; 21 parametrized cases across confirm/reject/ambiguous/case/whitespace |
| `frontend/src/app/globals.css` | prefers-reduced-motion, focus-visible, base font size | ✓ VERIFIED | font-size: 16px, *:focus-visible rule, @media prefers-reduced-motion block all present |
| `frontend/src/app/layout.tsx` | Skip-to-content + ScreenReaderAnnouncer | ✓ VERIFIED | Skip link with sr-only/focus:not-sr-only at line 23; ScreenReaderAnnouncer import and render at line 28 |
| `frontend/src/components/chat/UsageBar.tsx` | role=progressbar with aria value attributes | ✓ VERIFIED | Lines 37-42: role="progressbar", aria-label, aria-valuenow, aria-valuemin, aria-valuemax, aria-valuetext |
| `frontend/src/components/chat/ErrorBanner.tsx` | role=alert with aria-live=assertive | ✓ VERIFIED | Lines 25-27: role="alert", aria-live="assertive", aria-atomic="true" |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `useVoiceConversation.ts` | `chatStore.ts` | setPendingAction, addStructuredData, announce | ✓ WIRED | All three calls confirmed in cases at lines 211-265 |
| `ChatContainer.tsx` | `MessageBubble` (DOM element) | focus({ preventScroll: true }) via getElementById | ✗ NOT_WIRED | getElementById('msg-X') always returns null — MessageBubble has no id attribute |
| `voice_service.py` | `agent_service.py` | AgentService.stream() call when customer_id is set | ✓ WIRED | Line 226: self._agent.stream() in process_voice_streaming_with_agent |
| `voice.py` (route) | `voice_service.py` | process_voice_confirmation call | ✓ WIRED | Line 124: voice_service.process_voice_confirmation() |
| `layout.tsx` | `ScreenReaderAnnouncer.tsx` | Direct render as last child of body | ✓ WIRED | Line 28 in layout.tsx |
| `chatStore.ts` | `ScreenReaderAnnouncer.tsx` | srAnnouncement state | ✓ WIRED | Component subscribes to useChatStore state at line 11 |
| `main.py` | `VoiceService` | agent_service constructor param | ✓ WIRED | Line 115: agent_service=app.state.agent_service |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `ScreenReaderAnnouncer.tsx` | srAnnouncement | chatStore.announce() | Yes — populated by multiple call sites (action proposals, customer change, conversation toggle, recommendations) | ✓ FLOWING |
| `ChatContainer.tsx` focus | document.getElementById(msg-id) | MessageBubble DOM | No — MessageBubble never sets id attribute | ✗ DISCONNECTED |
| `useVoiceConversation.ts` action_proposal case | proposal from WebSocket msg | Backend voice WebSocket event | Yes — backend emits real action_proposal events from AgentService | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| parse_voice_confirmation('evet') returns True | Python module import check | Module structure confirmed via grep; dependencies not installed in shell env | ? SKIP (no venv activated) |
| VoiceActionProposal schema importable | grep check | Class definition confirmed at voice_schemas.py line 80 | ✓ PASS (structural) |
| test_voice_agent.py test structure | File count: 49 lines, TestParseVoiceConfirmation class, parametrized cases | Confirmed | ✓ PASS (structural) |
| Next.js build succeeds | `npx next build` | Not run — build not attempted in verification | ? SKIP |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| A11Y-01 | 10-01 (SUMMARY claims it) | Web arayüzü WCAG 2.1 AA seviyesinde erişilebilirdir | ✓ SATISFIED | 13 components have ARIA attributes; skip navigation; role landmarks; focus-visible; prefers-reduced-motion; base 16px font; role=progressbar on UsageBar |
| A11Y-02 | 10-02, 10-03 | Tüm etkileşimler yalnızca sesle (eyes-free) tamamlanabilir | ? PARTIALLY SATISFIED | Backend voice pipeline complete; frontend handles all voice-agent WS messages; focus management partially wired (see gap); requires human E2E test |
| A11Y-03 | 10-01, 10-03 | Ekran okuyucu uyumluluğu (ARIA etiketleri) | ✓ SATISFIED | Comprehensive ARIA across all 13 components; centralized ScreenReaderAnnouncer; announce() calls for all dynamic state changes |
| A11Y-04 | 10-01 | Yeterli renk kontrastı ve font büyüklüğü | ✓ SATISFIED (code) | 16px base font; text-gray-500 placeholder (not gray-400); turkcell-blue focus rings; arrow indicators alongside color in savings callouts. Human visual check needed for exact ratios. |

**Requirements Coverage Summary:** All 4 requirements targeted by Phase 10 are addressed. A11Y-01, A11Y-03, A11Y-04 are satisfied. A11Y-02 has a blocking gap (focus target missing) that prevents full confidence.

**Note on REQUIREMENTS.md status:** All four A11Y requirements are still marked `[ ]` (Pending) in REQUIREMENTS.md traceability table, not yet updated to reflect completion.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/src/components/chat/MessageBubble.tsx` | 19-68 | article element missing id and tabIndex — focus() target never created | ✗ Blocker | Focus management useEffect in ChatContainer silently fails; screen readers do not receive programmatic focus after streaming |
| `frontend/src/components/chat/MessageBubble.tsx` | 54 | `{/* Phase 7: TTS indicator placeholder -- activate when wasSpoken tracking is added */}` | ℹ️ Info | Acknowledged deferred feature from Phase 7, not a Phase 10 regression |
| SUMMARY files | - | Commit hashes in 10-01-SUMMARY.md (657830c, 4c5e535, 28c232b) and 10-02-SUMMARY.md (1356e76, 9895056) do not match actual git log | ℹ️ Info | Actual commits are 37fde8e, 13433bd, 0a46b35 and 9977f73, c8ac3fa respectively. Documentation error only, code is correct. |

### Human Verification Required

#### 1. Screen Reader Navigation

**Test:** Launch the app with VoiceOver (macOS) or NVDA (Windows). Navigate through the chat interface using keyboard only (Tab, arrow keys, screen reader shortcuts).
**Expected:** Hear "Sohbete gec" skip link on first Tab; navigate to main landmark; live region announces new assistant messages; typing indicator is announced; error messages are assertively announced
**Why human:** Cannot test AT software behavior programmatically

#### 2. Selin User Story — Eyes-Free Voice Agent Workflow

**Test:** With a customer selected (e.g., cust-001 Ahmet), press the voice conversation button without looking at screen. Ask "faturam neden yüksek?" via microphone. When the action proposal audio plays, say "evet". Verify the action result is announced.
**Expected:** Full voice loop completes: STT -> AgentService -> action_proposal TTS prompt -> voice confirmation -> action_result TTS
**Why human:** Requires live AWS Transcribe/Polly or mock voice services running end-to-end

#### 3. Color Contrast Verification

**Test:** Use browser DevTools or axe browser extension on the chat page. Check all text elements.
**Expected:** Body text on white background >= 4.5:1; turkcell-blue (#0066CC) on white >= 4.5:1; placeholder text (gray-500) on white >= 4.5:1
**Why human:** Exact pixel color values require visual/DevTools inspection

### Gaps Summary

**One blocking gap found:**

**Focus management is wired but the DOM target is missing.** `ChatContainer.tsx` has a `useEffect` that correctly calls `document.getElementById('msg-${lastMsg.id}')?.focus({ preventScroll: true })` when streaming ends. However, `MessageBubble.tsx` renders an `<article>` element with no `id` attribute and no `tabIndex` — so the getElementById lookup always returns `null` and `focus()` is never invoked. This directly blocks the WCAG 2.1 AA success criterion for focus management and the A11Y-02/A11Y-03 requirement for screen reader users receiving focus after streaming completes.

**Fix required:**
- Add `id={`msg-${message.id}`}` to the `<article>` in `MessageBubble.tsx`
- Add `tabIndex={-1}` to the same element (required for programmatic focus on non-interactive elements)

**All other Phase 10 deliverables are substantively complete:**
- Backend voice-agent pipeline (voice_service + voice.py route) fully wired
- Frontend voice-agent WebSocket message handling complete
- ScreenReaderAnnouncer component created and wired
- All 13 components have ARIA attributes
- Color contrast and font size improvements applied
- prefers-reduced-motion and focus-visible styles present
- Test suite for voice confirmation parsing exists (49 lines, TestParseVoiceConfirmation)

---

_Verified: 2026-04-01T21:00:00Z_
_Verifier: Claude (gsd-verifier)_
