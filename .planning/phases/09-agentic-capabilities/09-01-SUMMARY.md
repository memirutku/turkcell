---
phase: 09-agentic-capabilities
plan: 01
subsystem: api
tags: [langchain, langgraph, gemini-function-calling, agent-tools, mock-bss, pydantic]

# Dependency graph
requires:
  - phase: 05-billing-tariff-q-a
    provides: MockBSSService read methods, billing/tariff schemas
provides:
  - MockBSSService activate_package() and change_tariff() async action methods
  - 5 LangChain tool definitions for Gemini function calling
  - Agent Pydantic schemas (AgentState, AgentChatRequest, AgentConfirmRequest, ActionProposal, ActionResult)
  - Agent system prompt with tool instructions, context placeholders, and security guardrails
affects: [09-02-PLAN, 09-03-PLAN, 10-accessibility-hardening]

# Tech tracking
tech-stack:
  added: [langgraph]
  patterns: [closure-based tool factory, async BSS action methods with simulated delays, Turkish tool docstrings for Gemini routing]

key-files:
  created:
    - backend/app/models/agent_schemas.py
    - backend/app/services/agent_tools.py
    - backend/app/prompts/agent_prompts.py
    - backend/tests/test_agent.py
  modified:
    - backend/app/services/mock_bss.py
    - backend/pyproject.toml
    - backend/uv.lock

key-decisions:
  - "langgraph added as explicit dependency (was transitive through langchain) for agent_schemas AgentState TypedDict"
  - "Tool factory pattern: get_telecom_tools(mock_bss) returns closures bound to a service instance for testability"
  - "Turkish tool docstrings critical for Gemini function calling to route Turkish queries to correct tools"
  - "Pydantic v2 models mutable by default -- change_tariff mutates customer.tariff_id in-place"

patterns-established:
  - "Closure-based tool factory: get_telecom_tools(bss) returns LangChain tools bound to a service instance"
  - "Async action methods with asyncio.sleep(random.uniform(0.5, 1.5)) for realistic BSS simulation"
  - "Tool return JSON strings (not dicts) for LangChain ToolNode compatibility"

requirements-completed: [AGENT-02, AGENT-03, AGENT-05, AGENT-06]

# Metrics
duration: 5min
completed: 2026-04-01
---

# Phase 9 Plan 01: Agent Foundation Summary

**Mock BSS action methods, 5 LangChain tools with Turkish docstrings, agent schemas, and agentic system prompt for Gemini function calling**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-01T09:47:37Z
- **Completed:** 2026-04-01T09:52:37Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Extended MockBSSService with async activate_package() and change_tariff() methods that simulate realistic 0.5-1.5s BSS delays and return structured Turkish responses
- Created 5 LangChain tool definitions (activate_package, change_tariff, lookup_customer_bill, get_available_packages, get_available_tariffs) with Turkish docstrings and Pydantic input schemas
- Defined agent Pydantic models: AgentState TypedDict, AgentChatRequest, AgentConfirmRequest, ActionProposal, ActionResult, and tool input schemas
- Created AGENT_SYSTEM_PROMPT with tool instructions, customer/RAG context placeholders, and KVKK security guardrails
- All 15 agent tests pass (8 MockBSSActions + 7 ToolDefinitions), full suite 165 pass with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend MockBSSService with action methods and create agent schemas**
   - `5942d48` (test: failing tests for MockBSS actions - RED)
   - `89a6036` (feat: MockBSS async action methods + agent schemas - GREEN)
2. **Task 2: Create agent tools and system prompt**
   - `2602c3c` (test: failing tests for agent tool definitions - RED)
   - `13af295` (feat: agent tools with Turkish docstrings + agent prompt - GREEN)

_Note: TDD tasks have RED/GREEN commits_

## Files Created/Modified
- `backend/app/models/agent_schemas.py` - AgentState, AgentChatRequest, AgentConfirmRequest, ActionProposal, ActionResult, tool input schemas
- `backend/app/services/agent_tools.py` - get_telecom_tools() factory returning 5 LangChain tools bound to MockBSSService
- `backend/app/prompts/agent_prompts.py` - AGENT_SYSTEM_PROMPT with tool instructions and KVKK guardrails
- `backend/app/services/mock_bss.py` - Added activate_package() and change_tariff() async methods
- `backend/tests/test_agent.py` - 15 tests covering BSS actions and tool definitions
- `backend/pyproject.toml` - Added langgraph explicit dependency
- `backend/uv.lock` - Updated lockfile

## Decisions Made
- **langgraph as explicit dependency**: Was available transitively through langchain, but agent_schemas imports from it directly. Added explicitly to prevent breakage if langchain changes transitive deps.
- **Tool factory closure pattern**: get_telecom_tools(mock_bss) creates tool closures bound to a service instance, enabling easy testing and swapping of BSS implementations.
- **Turkish tool docstrings**: Gemini function calling uses tool descriptions to decide which tool to invoke. Turkish descriptions ensure Turkish user queries route correctly.
- **Pydantic v2 in-place mutation**: Customer model is mutable by default in Pydantic v2 (no frozen config), so change_tariff mutates customer.tariff_id directly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added langgraph as explicit dependency**
- **Found during:** Task 1 (agent_schemas.py creation)
- **Issue:** agent_schemas.py imports `from langgraph.graph.message import add_messages` but langgraph was not in pyproject.toml
- **Fix:** Added `langgraph>=0.2.0` to pyproject.toml dependencies
- **Files modified:** backend/pyproject.toml, backend/uv.lock
- **Verification:** `uv run python -c "from langgraph.graph.message import add_messages"` succeeds
- **Committed in:** 13af295 (part of Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Essential for correct import resolution. No scope creep.

## Issues Encountered
None

## Known Stubs
None - all code is fully wired and functional.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Mock BSS action methods, tools, schemas, and prompt are ready for Plan 02 (LangGraph StateGraph agent workflow)
- get_telecom_tools() returns bound tools ready for ChatGoogleGenerativeAI.bind_tools() and ToolNode()
- AgentState TypedDict ready for LangGraph StateGraph definition
- AGENT_SYSTEM_PROMPT has {customer_context} and {rag_context} placeholders ready for runtime formatting

## Self-Check: PASSED

All 5 created files verified on disk. All 4 commit hashes found in git log.

---
*Phase: 09-agentic-capabilities*
*Completed: 2026-04-01*
