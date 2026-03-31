---
phase: 05-billing-tariff-q-a
plan: 02
subsystem: ui
tags: [shadcn, select, zustand, customer-selector, base-ui, react]

requires:
  - phase: 03-core-chat-llm-integration
    provides: chatStore, api.ts streamChat, ChatHeader, EmptyState, chat UI foundation
provides:
  - CustomerSelector dropdown component with 3 demo customers and Genel Sohbet
  - customerId state in zustand chatStore with session reset on switch
  - customer_id field conditionally passed in streamChat POST body
  - Customer-specific EmptyState greeting
affects: [05-billing-tariff-q-a, 06-tariff-recommendation-agent, 08-frontend-dashboard]

tech-stack:
  added: ["@base-ui/react (via shadcn Select)", "shadcn Select component"]
  patterns: ["Customer-scoped chat sessions via zustand customerId state", "Conditional API body fields based on UI selection", "Session reset on context switch (customer change clears messages)"]

key-files:
  created:
    - frontend/src/components/chat/CustomerSelector.tsx
    - frontend/src/components/ui/select.tsx
  modified:
    - frontend/src/types/index.ts
    - frontend/src/stores/chatStore.ts
    - frontend/src/lib/api.ts
    - frontend/src/components/chat/ChatHeader.tsx
    - frontend/src/components/chat/EmptyState.tsx

key-decisions:
  - "shadcn v4 base-nova preset uses @base-ui/react instead of @radix-ui -- adapted component API accordingly"
  - "GENERAL_CHAT_VALUE sentinel (__general__) since base-ui Select does not support null values"
  - "Yeni Sohbet preserves customerId (only clears messages), customer switch resets everything"
  - "customer_id omitted from POST body when null (Genel Sohbet mode) per API contract"

patterns-established:
  - "Customer context pattern: zustand stores customerId, components read via selector, API layer conditionally includes"
  - "Session reset on context switch: setCustomerId generates new sessionId, clears messages"
  - "Demo customer data as component-local constants (DEMO_CUSTOMERS array)"

requirements-completed: [BILL-01, BILL-02, BILL-03, BILL-04]

duration: 5min
completed: 2026-03-31
---

# Phase 5 Plan 02: Customer Selector UI Summary

**Customer selector dropdown with 3 demo customers and Genel Sohbet option, driving customer-scoped billing conversations via zustand state and conditional API customer_id**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-31T11:06:18Z
- **Completed:** 2026-03-31T11:12:02Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- CustomerSelector component renders shadcn Select dropdown with Ahmet Y., Elif D., Mehmet K. and Genel Sohbet option
- Zustand chatStore extended with customerId state (default cust-001) and setCustomerId action that resets session
- streamChat API function conditionally includes customer_id in POST body when a customer is selected
- ChatHeader renders CustomerSelector between logo and Yeni Sohbet button
- EmptyState shows customer-specific greeting ("Merhaba! {name} hesabi hakkinda soru sorabilirsiniz.") or general greeting

## Task Commits

Each task was committed atomically:

1. **Task 1: Install shadcn Select and create CustomerSelector component with types** - `4d0d97f` (feat)
2. **Task 2: Update chatStore, api.ts, ChatHeader, and EmptyState for customer context** - `9310268` (feat)

## Files Created/Modified
- `frontend/src/components/ui/select.tsx` - shadcn Select primitive (base-nova preset, @base-ui/react)
- `frontend/src/components/chat/CustomerSelector.tsx` - Customer selector dropdown with 3 demo customers + Genel Sohbet
- `frontend/src/types/index.ts` - Added CustomerOption interface (id, name, tariff)
- `frontend/src/stores/chatStore.ts` - Added customerId state, setCustomerId action, pass customerId to streamChat
- `frontend/src/lib/api.ts` - streamChat accepts customerId, conditionally includes customer_id in POST body
- `frontend/src/components/chat/ChatHeader.tsx` - Renders CustomerSelector between logo and Yeni Sohbet
- `frontend/src/components/chat/EmptyState.tsx` - Customer-specific vs general greeting based on customerId

## Decisions Made
- **shadcn v4 base-nova API adaptation**: The installed shadcn Select uses @base-ui/react (not @radix-ui) -- adapted onValueChange signature and component structure accordingly
- **GENERAL_CHAT_VALUE sentinel**: Used "__general__" string sentinel since base-ui Select does not support null values natively
- **Yeni Sohbet preserves customer**: resetSession only clears messages/error/sessionId, intentionally omitting customerId from the set() call
- **Conditional customer_id in body**: When customerId is null (Genel Sohbet), customer_id is omitted entirely from the POST body per API contract

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Adapted plan's Radix Select API to base-ui Select API**
- **Found during:** Task 1 (CustomerSelector creation)
- **Issue:** Plan assumed @radix-ui/react-select API but shadcn v4 base-nova preset uses @base-ui/react/select with different component structure
- **Fix:** Adapted onValueChange to accept (value: string | null) instead of (value: string), aligned component tree with base-ui primitives
- **Files modified:** frontend/src/components/chat/CustomerSelector.tsx
- **Verification:** TypeScript compilation clean (npx tsc --noEmit produces no errors)
- **Committed in:** 4d0d97f (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** API adaptation was necessary due to shadcn v4 using a different underlying primitive library. No scope creep.

## Issues Encountered
- Worktree was behind main branch (missing phases 03-05 code) -- fast-forward merged main before starting execution

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all components are fully wired to zustand state and API layer.

## Next Phase Readiness
- Customer selector is ready for Plan 03 (end-to-end billing Q&A flow)
- Backend BillingContextService (Plan 01) provides the customer_id-driven context enrichment
- TypeScript compiles clean, all acceptance criteria pass

## Self-Check: PASSED

All 8 files verified present. Both task commits (4d0d97f, 9310268) verified in git log.

---
*Phase: 05-billing-tariff-q-a*
*Completed: 2026-03-31*
