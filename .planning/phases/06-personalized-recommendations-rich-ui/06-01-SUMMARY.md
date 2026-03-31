---
phase: 06-personalized-recommendations-rich-ui
plan: 01
subsystem: api
tags: [recommendation-engine, decimal-arithmetic, sse, pydantic, tariff, billing]

requires:
  - phase: 05-billing-tariff-q-a
    provides: BillingContextService, MockBSSService, BILLING_SYSTEM_PROMPT, chat SSE pipeline
provides:
  - TariffRecommendationService with deterministic savings calculations
  - Recommendation Pydantic schemas (TariffRecommendation, RecommendationResult, UsageSummary)
  - Structured SSE event type ("structured") for rich UI recommendation payload
  - RECOMMENDATION_CONTEXT_SECTION for LLM prompt injection
  - Extended billing prompt with tarife onerisi rules
affects: [06-02-rich-ui-components, frontend-recommendation-cards, chat-ui]

tech-stack:
  added: []
  patterns: [Decimal arithmetic for all currency calculations, structured SSE events alongside text tokens, optional DI pattern for service composition]

key-files:
  created:
    - backend/app/models/recommendation_schemas.py
    - backend/app/services/recommendation_service.py
    - backend/tests/test_recommendation.py
  modified:
    - backend/app/prompts/billing_prompts.py
    - backend/app/services/chat_service.py
    - backend/app/api/routes/chat.py
    - backend/app/main.py

key-decisions:
  - "Only recommend tariffs with positive savings (filtered out zero/negative)"
  - "Fallback data overage rate 20 TL/GB and voice 0.50 TL/min derived from mock bill data patterns"
  - "Fit score weighted: data 50%, voice 30%, SMS 20% with over-provisioning penalty"
  - "Structured SSE event emitted after all text tokens, before done event"

patterns-established:
  - "Decimal arithmetic for all TL calculations: KDV_RATE, OIV_RATE, quantize to 0.01"
  - "Optional DI for service composition: recommendation_service kwarg on ChatService"
  - "Structured SSE: isinstance(item, dict) check in event_generator for typed payloads"

requirements-completed: [BILL-05, BILL-06]

duration: 12min
completed: 2026-03-31
---

# Phase 6 Plan 01: Recommendation Engine Summary

**Deterministic tariff recommendation engine with Decimal savings calculations, usage-based fit scoring, and structured SSE event emission for rich UI**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-31T18:17:55Z
- **Completed:** 2026-03-31T18:30:00Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- TariffRecommendationService produces personalized tariff recommendations using Decimal arithmetic for exact KDV/OIV tax calculations
- 22 unit tests covering BILL-05 (personalized recommendations) and BILL-06 (savings accuracy) pass with zero regression (135 total)
- Chat pipeline extended with recommendation context injection and structured SSE events for frontend consumption
- Billing prompt enhanced with recommendation presentation rules (BIREBIR transfer, no LLM self-calculation)

## Task Commits

Each task was committed atomically:

1. **Task 1: Recommendation schemas, TariffRecommendationService, and unit tests (TDD)**
   - `f04ad6b` (test) - RED: failing tests for recommendation service
   - `a734f15` (feat) - GREEN: implementation passing all 22 tests
2. **Task 2: Wire recommendations into chat pipeline with structured SSE events** - `4234de7` (feat)

## Files Created/Modified
- `backend/app/models/recommendation_schemas.py` - TariffRecommendation, RecommendationResult, UsageSummary Pydantic models
- `backend/app/services/recommendation_service.py` - TariffRecommendationService with get_recommendations, cost projection, fit scoring
- `backend/tests/test_recommendation.py` - 22 tests covering BILL-05 and BILL-06 requirements
- `backend/app/prompts/billing_prompts.py` - RECOMMENDATION_CONTEXT_SECTION and extended analysis rules
- `backend/app/services/chat_service.py` - Recommendation DI, context formatting, structured dict yield
- `backend/app/api/routes/chat.py` - Structured SSE event handling (isinstance check for dict)
- `backend/app/main.py` - TariffRecommendationService initialization in lifespan

## Decisions Made
- Only tariffs with positive savings are included in recommendations (zero/negative filtered out) -- this means cust-002 gets 1 recommendation (Ekonomik 3GB saves 8.10 TL) while cust-001 gets 0 (already on the most cost-effective tariff for their 18.5 GB usage)
- Used fixed overage rates (20 TL/GB data, 0.50 TL/min voice) matching mock bill data patterns rather than dynamic derivation
- Fit score uses weighted formula: data 50%, voice 30%, SMS 20% with slight penalty for over-provisioning (>2x usage)
- Structured SSE event emitted after all text tokens complete, before the "done" event

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Adjusted sorting test to use mock BSS with custom tariffs**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Plan's sorting test expected >=2 recommendations for cust-002, but the mock data only yields 1 tariff with positive savings (Gold 10GB projected cost exactly equals effective cost at 268.65 TL)
- **Fix:** Used a mock BSS with custom cheap tariffs that guarantee multiple positive-savings recommendations for the sorting assertion
- **Files modified:** backend/tests/test_recommendation.py
- **Verification:** All 22 tests pass
- **Committed in:** a734f15

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Test data adjustment necessary for correctness. No scope creep.

## Issues Encountered
None - plan executed smoothly after test data adjustment.

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all data flows are wired to real mock BSS data through TariffRecommendationService.

## Next Phase Readiness
- Structured SSE "recommendation" payload ready for frontend rich UI components (06-02)
- RecommendationResult model provides all data needed for tariff comparison cards, usage gauges, and savings badges
- Frontend needs to handle `event: structured` SSE events alongside existing `event: token` events

## Self-Check: PASSED

- All 4 created files exist on disk
- All 3 task commits found in git history (f04ad6b, a734f15, 4234de7)
- All 13 acceptance criteria verified via grep

---
*Phase: 06-personalized-recommendations-rich-ui*
*Completed: 2026-03-31*
