---
phase: 09-agentic-capabilities
plan: 02
subsystem: api
tags: [langgraph, stategraph, interrupt, command, sse, agent-service, gemini-tools]

# Dependency graph
requires:
  - phase: 09-agentic-capabilities
    provides: MockBSSService action methods, 5 LangChain tools, AgentState TypedDict, agent system prompt
provides:
  - AgentService with LangGraph StateGraph (5 nodes: gather_context, agent, tools, propose_action, execute_action)
  - POST /api/agent/chat SSE endpoint for agentic chat with streaming and action proposals
  - POST /api/agent/confirm SSE endpoint for resuming after user confirmation/rejection
  - App startup wiring for AgentService in lifespan
affects: [09-03-PLAN, 10-accessibility-hardening]

# Tech tracking
tech-stack:
  added: []
  patterns: [interrupt-based confirmation flow, astream_events v2 for token streaming, MemorySaver checkpointing, separate SSE streams for proposal and confirmation]

key-files:
  created:
    - backend/app/services/agent_service.py
    - backend/app/api/routes/agent.py
  modified:
    - backend/app/main.py
    - backend/tests/test_agent.py

key-decisions:
  - "Separate SSE streams for chat and confirm: stream() closes after action_proposal, resume() opens new stream (per RESEARCH.md Pitfall 3)"
  - "astream_events v2 with on_chat_model_stream for token-level streaming (per RESEARCH.md Pitfall 6)"
  - "Side effects placed AFTER interrupt() in propose_action_node to avoid re-execution on resume (per RESEARCH.md Pitfall 1)"
  - "MemorySaver checkpointer for in-memory graph state persistence across confirmation round-trip"

patterns-established:
  - "interrupt()-based confirmation: propose_action node calls interrupt(proposal), frontend receives action_proposal SSE event, sends POST /confirm, graph resumes via Command(resume=user_response)"
  - "Dual routing for tool calls: destructive tools (activate_package, change_tariff) route to propose_action, non-destructive tools (lookup, list) route directly to ToolNode"
  - "Agent coexistence: /api/agent/chat for agentic flows, /api/chat preserved for simple Q&A (no code changes to existing endpoint)"

requirements-completed: [AGENT-01, AGENT-04]

# Metrics
duration: 6min
completed: 2026-04-01
---

# Phase 9 Plan 02: Agent Service & API Endpoints Summary

**LangGraph StateGraph agent with 5-node workflow, interrupt()-based confirmation, SSE streaming endpoints, and app startup wiring**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-01T09:57:02Z
- **Completed:** 2026-04-01T10:03:02Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Created AgentService with LangGraph StateGraph containing 5 nodes (gather_context, agent, tools, propose_action, execute_action) that orchestrates multi-step telecom workflows
- Implemented interrupt()-based confirmation flow: agent proposes actions, pauses graph, yields action_proposal SSE event, then resumes on user approval/rejection via Command(resume=...)
- Created POST /api/agent/chat and POST /api/agent/confirm SSE endpoints following the same pattern as existing /api/chat
- Wired AgentService into app startup lifespan with PII masking and billing context integration
- All 24 agent tests pass (15 from Plan 01 + 9 new), full suite 174 pass with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Create AgentService with LangGraph StateGraph** - `ae9dd60` (feat)
2. **Task 2: Create agent API endpoints and wire into app startup** - `c815a10` (feat)

## Files Created/Modified
- `backend/app/services/agent_service.py` - AgentService class with LangGraph StateGraph, stream() and resume() methods, 5 graph nodes
- `backend/app/api/routes/agent.py` - POST /api/agent/chat and POST /api/agent/confirm SSE endpoints
- `backend/app/main.py` - AgentService initialization in lifespan, agent router registration
- `backend/tests/test_agent.py` - 9 new tests: 3 workflow, 2 confirmation, 4 endpoint tests

## Decisions Made
- **Separate SSE streams**: stream() closes after emitting action_proposal, confirm endpoint opens a new stream. This avoids keeping connections open during user decision time (per RESEARCH.md Pitfall 3).
- **astream_events v2**: Used `astream_events(version="v2")` with `on_chat_model_stream` event filtering for token-level streaming instead of default `astream()` which only yields full node outputs (per RESEARCH.md Pitfall 6).
- **MemorySaver checkpointer**: In-memory checkpointer for graph state persistence. Sufficient for development; production would use a persistent store.
- **Dual tool routing**: Destructive tools (activate_package, change_tariff) route to propose_action for confirmation; non-destructive tools (lookup, list) execute directly via ToolNode.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## Known Stubs
None - all code is fully wired and functional.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- AgentService is fully functional and ready for frontend integration in Plan 03
- SSE event types (token, action_proposal, action_result, done, error) documented for frontend consumption
- Confirmation flow (POST /api/agent/chat -> action_proposal -> POST /api/agent/confirm) ready for ActionConfirmationCard and ActionResultCard components
- Existing /api/chat endpoint unchanged -- backward compatibility maintained

## Self-Check: PASSED

All 4 files verified on disk. Both commit hashes found in git log.

---
*Phase: 09-agentic-capabilities*
*Completed: 2026-04-01*
