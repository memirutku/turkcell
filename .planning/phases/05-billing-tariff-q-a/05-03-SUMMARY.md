---
phase: 05-billing-tariff-q-a
plan: 03
subsystem: api
tags: [billing, chat-integration, prompt-routing, customer-context, fastapi]

requires:
  - phase: 05-billing-tariff-q-a
    plan: 01
    provides: BillingContextService, BILLING_SYSTEM_PROMPT, billing FAQ document
  - phase: 05-billing-tariff-q-a
    plan: 02
    provides: CustomerSelector UI, customerId in zustand store, customer_id in API body
provides:
  - ChatService with conditional billing context injection via customer_id
  - ChatRequest schema with optional customer_id field
  - Chat route passing customer_id through to ChatService
  - App startup wiring BillingContextService into ChatService
affects: [05-billing-tariff-q-a, 06-personalized-recommendations]

tech-stack:
  added: []
  patterns: [Conditional system prompt selection based on customer context, Billing context injection into LLM pipeline]

key-files:
  created: []
  modified:
    - backend/app/models/chat_schemas.py
    - backend/app/services/chat_service.py
    - backend/app/api/routes/chat.py
    - backend/app/main.py
    - backend/tests/test_billing.py

key-decisions:
  - "Conditional prompt routing: BILLING_SYSTEM_PROMPT when customer context available, standard SYSTEM_PROMPT as fallback"
  - "Unknown customer_id gracefully falls back to standard prompt (billing context returns None)"
  - "BillingContextService created once at startup from MockBSSService, injected into ChatService constructor"

patterns-established:
  - "Customer-scoped prompt injection: customer_id -> BillingContextService -> BILLING_SYSTEM_PROMPT.format()"
  - "Graceful degradation chain: no customer_id OR unknown customer -> standard SYSTEM_PROMPT"

requirements-completed: [BILL-01, BILL-02, BILL-03, BILL-04]

duration: 6min
completed: 2026-03-31
---

# Phase 5 Plan 03: Billing Chat Pipeline Integration Summary

**Wired BillingContextService into ChatService with conditional BILLING_SYSTEM_PROMPT selection based on customer_id, enabling customer-specific billing Q&A through the existing chat API**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-31T11:15:35Z
- **Completed:** 2026-03-31T11:21:39Z
- **Tasks:** 1 of 2 (Task 2 is human-verify checkpoint)
- **Files modified:** 5

## Accomplishments
- ChatRequest schema extended with optional customer_id field (default None)
- ChatService accepts BillingContextService via constructor and uses BILLING_SYSTEM_PROMPT when customer context is available
- Chat route passes body.customer_id through to stream_response
- App startup creates BillingContextService from MockBSSService and injects into ChatService
- Unknown customer_id gracefully falls back to standard SYSTEM_PROMPT
- 7 new billing integration tests added, 113 total tests pass with no regression (2 skipped for spaCy)

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire ChatService, ChatRequest, chat route, and app startup for billing context (TDD)**
   - `16502ad` (test) - Failing tests for billing chat integration
   - `8193d83` (feat) - Wire billing context into ChatService pipeline

## Files Created/Modified
- `backend/app/models/chat_schemas.py` - Added optional customer_id: str | None = Field(default=None)
- `backend/app/services/chat_service.py` - Added billing_context parameter, customer_id to stream_response, conditional prompt selection
- `backend/app/api/routes/chat.py` - Pass body.customer_id to stream_response
- `backend/app/main.py` - Create BillingContextService from MockBSSService, inject into ChatService
- `backend/tests/test_billing.py` - 7 new TestBillingChatIntegration tests

## Decisions Made
- Conditional prompt routing: BILLING_SYSTEM_PROMPT used only when BillingContextService returns non-empty customer context
- Unknown customer_id returns None from BillingContextService, triggering fallback to standard SYSTEM_PROMPT
- BillingContextService instantiated once at app startup, not per-request

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Test runner PATH issue in worktree**
- **Found during:** TDD RED phase
- **Issue:** Worktree venv did not have pytest installed, and system PATH pointed to anaconda pytest which could not import project modules
- **Fix:** Installed pytest/pytest-asyncio into venv, used `uv run python -m pytest` instead of bare `pytest`
- **Files modified:** None (runtime fix only)

### Deferred Items

**RAG re-ingestion skipped:** The plan calls for running `scripts/ingest_documents.py` to add fatura_bilgileri.txt to Milvus. This requires Milvus and Gemini API to be running, which is not available in the worktree test environment. The document file exists at `backend/data/documents/fatura_bilgileri.txt` and will be ingested when the full Docker Compose stack is running during human verification (Task 2).

## Issues Encountered
- Worktree was behind main branch by ~15 commits -- fast-forward merged to HEAD before starting

## User Setup Required
- RAG re-ingestion: Run `cd backend && uv run python scripts/ingest_documents.py` with Milvus and Gemini API available

## Known Stubs
None - all data sources are wired to MockBSSService via BillingContextService, no placeholder data.

## Self-Check: PASSED

All 5 modified files verified present. Both task commits (16502ad, 8193d83) verified in git log. 113 tests pass.

---
*Phase: 05-billing-tariff-q-a*
*Completed: 2026-03-31 (Task 1 only, Task 2 awaiting human verification)*
