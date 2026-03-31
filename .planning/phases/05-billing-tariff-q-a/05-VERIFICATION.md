---
phase: 05-billing-tariff-q-a
verified: 2026-03-31T12:00:00Z
status: human_needed
score: 8/8 must-haves verified
re_verification: false
human_verification:
  - test: "Verify customer selector visible in browser and billing Q&A end-to-end"
    expected: "Customer dropdown appears in header, selecting Ahmet Y. and asking 'Faturam neden yuksek?' returns a response referencing actual bill amounts and line items in Turkish"
    why_human: "Full pipeline requires running Docker Compose (Milvus + Gemini API + Redis). RAG re-ingestion of fatura_bilgileri.txt was deferred in Plan 03 and requires Milvus to be running. Visual layout and streaming behavior cannot be verified programmatically."
  - test: "Verify session isolation between customers"
    expected: "Switching from Ahmet Y. to Elif D. clears messages, then asking about bill returns Silver 5GB tariff details — not Ahmet's Platinum data"
    why_human: "Requires live Gemini API + frontend browser interaction to confirm session isolation produces different LLM responses."
  - test: "Verify RAG re-ingestion of fatura_bilgileri.txt"
    expected: "After running 'cd backend && uv run python scripts/ingest_documents.py', asking 'KDV nedir?' in Genel Sohbet mode returns an explanation of the %20 rate from the FAQ document"
    why_human: "Requires Milvus running to execute ingestion and confirm retrieval of the new document."
---

# Phase 5: Billing Tariff Q&A Verification Report

**Phase Goal:** Users can ask natural-language questions about their bills and available tariffs and receive accurate, detailed answers from mock data
**Verified:** 2026-03-31T12:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | BillingContextService formats customer profile, tariff, bills, and usage as structured Turkish text | VERIFIED | `billing_context.py` lines 23-44 — get_customer_context() assembles all four sections; test_get_customer_context_returns_formatted_text passes |
| 2 | Bill line items are categorized as Ana Ucret, Asim Ucreti, Vergi with Turkish labels | VERIFIED | `CATEGORY_MAP` dict in `billing_context.py` lines 9-13; test_line_item_categories_turkish passes confirming cust-001 data contains all three categories |
| 3 | Currency amounts use Turkish formatting with TL suffix | VERIFIED | `_format_tl()` static method lines 124-161; test_currency_formatting_with_thousands confirms "1.234,56 TL"; test_currency_formatting confirms "299,00 TL" |
| 4 | Customer PII (TC Kimlik, full phone) is redacted in formatted context | VERIFIED | `_format_customer_profile()` lines 48-66 — phone masked to `***XXXX`, TC Kimlik field never formatted at all; test_pii_redaction passes confirming "12345678901" absent and "***4567" present |
| 5 | Billing system prompt includes fatura analiz kurallari and dual context sections | VERIFIED | `billing_prompts.py` lines 30-42 — `{customer_context}` at line 31, `{rag_context}` at line 34, "Fatura Analiz Kurallari" section at line 36; all three TestBillingPrompts assertions pass |
| 6 | Billing FAQ RAG document covers KDV, OIV, overage, and payment in Turkish | VERIFIED | `fatura_bilgileri.txt` — 85 lines; contains KDV (%20), OIV (%15), asim ucreti, ana ucret, tarife degisikligi, "faturam neden yuksek" FAQ section |
| 7 | ChatService uses BillingContextService when customer_id is provided, falls back to SYSTEM_PROMPT otherwise | VERIFIED | `chat_service.py` lines 79-94 — conditional prompt routing; test_chat_service_with_customer_id_uses_billing_prompt and test_chat_service_without_customer_id_uses_standard_prompt both pass |
| 8 | Frontend customer selector drives customer_id in API requests, with session reset on switch | VERIFIED | `CustomerSelector.tsx` uses useChatStore setCustomerId; `chatStore.ts` setCustomerId resets session and passes customerId to streamChat; `api.ts` conditionally includes customer_id in POST body when truthy |

**Score:** 8/8 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/services/billing_context.py` | BillingContextService with get_customer_context() | VERIFIED | 162 lines; exports BillingContextService; all formatting methods present |
| `backend/app/prompts/billing_prompts.py` | BILLING_SYSTEM_PROMPT with dual context placeholders | VERIFIED | 47 lines; contains {customer_context}, {rag_context}, Fatura Analiz Kurallari, GUVENLIK guardrails |
| `backend/data/documents/fatura_bilgileri.txt` | Turkish billing FAQ for RAG (min 40 lines) | VERIFIED | 85 lines; UTF-8 Turkish; KDV, OIV, asim, ana ucret, tarife all present |
| `backend/tests/test_billing.py` | Unit + integration tests (min 80 lines) | VERIFIED | 385 lines; 24 test functions across 3 classes; all 24 pass |
| `backend/app/models/chat_schemas.py` | ChatRequest with optional customer_id | VERIFIED | customer_id: str | None = Field(default=None) at line 21 |
| `backend/app/services/chat_service.py` | Extended ChatService with billing_context parameter | VERIFIED | billing_context param in __init__ (line 38), customer_id in stream_response (line 52), conditional BILLING_SYSTEM_PROMPT (lines 88-90) |
| `backend/app/api/routes/chat.py` | Chat route passing customer_id | VERIFIED | body.customer_id passed as third arg to stream_response at line 32 |
| `backend/app/main.py` | BillingContextService wired at startup | VERIFIED | BillingContextService imported (line 10), instantiated at line 52, injected into ChatService at line 60 |
| `frontend/src/components/chat/CustomerSelector.tsx` | Customer dropdown with 3 customers + Genel Sohbet | VERIFIED | 93 lines; DEMO_CUSTOMERS with cust-001/002/003; Genel Sohbet with separator; disabled={isStreaming} |
| `frontend/src/stores/chatStore.ts` | customerId state with setCustomerId action | VERIFIED | customerId: "cust-001" default; setCustomerId resets session; sendMessage passes customerId to streamChat |
| `frontend/src/lib/api.ts` | streamChat with conditional customer_id | VERIFIED | customerId parameter at line 26; body.customer_id conditionally added lines 35-37 |
| `frontend/src/types/index.ts` | CustomerOption type definition | VERIFIED | CustomerOption interface at lines 73-77 |
| `frontend/src/components/chat/ChatHeader.tsx` | Renders CustomerSelector between logo and Yeni Sohbet | VERIFIED | CustomerSelector imported and rendered at line 26 inside flex div with Yeni Sohbet |
| `frontend/src/components/chat/EmptyState.tsx` | Customer-specific greeting | VERIFIED | CUSTOMER_NAMES map; conditional greeting showing "hesabi hakkinda soru sorabilirsiniz" |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `billing_context.py` | `mock_bss.py` | self._bss.get_customer / get_customer_bills / get_customer_usage | WIRED | Lines 26-31 of billing_context.py call all three MockBSSService methods |
| `billing_prompts.py` | `system_prompt.py` | Same prompt structure, added billing sections | WIRED | BILLING_SYSTEM_PROMPT preserves all GUVENLIK rules from Phase 4; dual context replaces single {context} |
| `chat.py` route | `chat_service.py` | stream_response(body.message, body.session_id, body.customer_id) | WIRED | chat.py line 31-33 passes all three arguments |
| `chat_service.py` | `billing_context.py` | self._billing_context.get_customer_context(customer_id) | WIRED | chat_service.py line 82 |
| `chat_service.py` | `billing_prompts.py` | BILLING_SYSTEM_PROMPT.format(customer_context=..., rag_context=...) | WIRED | chat_service.py lines 89-92 |
| `main.py` | `billing_context.py` | BillingContextService(mock_service) | WIRED | main.py line 52 — instantiated once at startup |
| `CustomerSelector.tsx` | `chatStore.ts` | useChatStore for customerId and setCustomerId | WIRED | CustomerSelector.tsx lines 21-23 |
| `chatStore.ts` | `api.ts` | sendMessage passes customerId to streamChat | WIRED | chatStore.ts line 97 — customerId passed as third argument |
| `ChatHeader.tsx` | `CustomerSelector.tsx` | Renders CustomerSelector | WIRED | ChatHeader.tsx line 3 imports, line 26 renders |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `billing_context.py` | customer, bills, usage | MockBSSService.get_customer / get_customer_bills / get_customer_usage | Yes — MockBSSService reads from JSON fixture files (customers.json, bills.json, usage.json) | FLOWING |
| `chat_service.py` | customer_context | BillingContextService.get_customer_context(customer_id) | Yes — returns formatted string from real mock data or None for unknown customer | FLOWING |
| `chatStore.ts` | customerId | user interaction via setCustomerId (default "cust-001") | Yes — initial state "cust-001", propagates to API body | FLOWING |
| `api.ts` | body.customer_id | customerId from chatStore | Yes — conditionally included, omitted when null | FLOWING |
| `EmptyState.tsx` | customerName | CUSTOMER_NAMES[customerId] from useChatStore | Yes — reads live zustand state | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All billing tests pass | uv run python -m pytest tests/test_billing.py -x -v | 24 passed in 0.02s | PASS |
| Full backend test suite (regression) | uv run python -m pytest tests/ -x -q | 113 passed, 2 skipped | PASS |
| TypeScript frontend compiles | npx tsc --noEmit | No output (clean) | PASS |
| fatura_bilgileri.txt meets min line count | wc -l fatura_bilgileri.txt | 85 lines | PASS |
| BillingContextService exports exist | grep "class BillingContextService" billing_context.py | Found at line 16 | PASS |
| tc_kimlik_no absent from context output | grep "tc_kimlik_no" billing_context.py | No matches (field never formatted) | PASS |
| RAG ingestion of fatura_bilgileri.txt | ingest_documents.py (requires Milvus) | DEFERRED — needs Milvus running | SKIP |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| BILL-01 | 05-01, 05-02, 05-03 | Kullanici "faturam neden yuksek?" diye sorarak fatura detaylarini ogrenebilir | SATISFIED | BillingContextService formats all bill data; ChatService injects into BILLING_SYSTEM_PROMPT; customer_id flows frontend->backend; end-to-end pipeline wired. Human verification confirms actual response quality. |
| BILL-02 | 05-01, 05-02, 05-03 | Fatura kalemleri (ana ucret, asim, vergiler) dogal dilde aciklanir | SATISFIED | CATEGORY_MAP maps base->Ana Ucret, overage->Asim Ucreti, tax->Vergi; Fatura Analiz Kurallari in BILLING_SYSTEM_PROMPT instructs LLM to explain each category; test_line_item_categories_turkish confirms mapping in output |
| BILL-03 | 05-01, 05-02, 05-03 | Kullanicinin mevcut tarife bilgisi sorgulanabilir | SATISFIED | _format_current_tariff() includes tariff name, data_gb, voice_minutes, sms_count, monthly price; wired via customer.tariff from MockBSSService.get_customer(); test_get_customer_context_returns_formatted_text confirms "Platinum" in output |
| BILL-04 | 05-01, 05-02, 05-03 | Mevcut tarifeler ve kampanyalar RAG ile sorgulanabilir | PARTIAL — code complete, RAG ingestion deferred | fatura_bilgileri.txt document created (85 lines covering tariff details); existing tariff documents remain in Milvus; re-ingestion to add new document deferred to human verification step due to Milvus unavailability in test environment |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | No stubs, TODOs, placeholders, or empty implementations in phase 05 files |

### Human Verification Required

#### 1. Full Billing Q&A Flow (BILL-01, BILL-02, BILL-03)

**Test:** Start the application with `docker compose up` (or backend + frontend separately). Open `http://localhost:3000/chat`. Select "Ahmet Y. - Platinum 20GB" in the dropdown. Ask: "Faturam neden yuksek?"
**Expected:** Response references actual bill amounts visible in Ahmet's mock data (403,65 TL base + overages), categorizes line items as ana ucret / asim ucreti / vergi, and responds in natural Turkish with empathetic tone.
**Why human:** Requires live Gemini API + Redis + Milvus stack running; LLM response quality and Turkish naturalness cannot be verified programmatically.

#### 2. Customer Session Isolation

**Test:** With Ahmet Y. selected, ask about the bill. Then select "Elif D." — verify messages clear. Ask about her tariff.
**Expected:** Chat clears on customer switch; Elif's responses reference Silver 5GB tariff (129 TL), not Ahmet's Platinum data.
**Why human:** Requires browser interaction and live LLM responses; session isolation between customers depends on distinct BillingContextService outputs being correctly injected.

#### 3. RAG Re-ingestion of fatura_bilgileri.txt (BILL-04)

**Test:** With Milvus running, execute: `cd backend && uv run python scripts/ingest_documents.py`. Then select "Genel Sohbet" and ask: "KDV nedir?"
**Expected:** Response includes the %20 rate explanation from fatura_bilgileri.txt, demonstrating the new document was indexed and retrieved.
**Why human:** Requires Milvus running for ingestion. The document file exists and is correct but was not ingested during automated execution due to missing Milvus in the test environment.

#### 4. Streaming and Disable Behavior

**Test:** Select a customer and send a message. While the response is streaming, try to change the customer in the dropdown.
**Expected:** Dropdown is disabled (grayed out) during streaming; it re-enables after the response completes.
**Why human:** Streaming state and UI disable behavior require browser interaction.

### Gaps Summary

No automated gaps. All code artifacts exist, are substantive, and are correctly wired. The one outstanding item is operational: the RAG re-ingestion of `fatura_bilgileri.txt` into Milvus was deferred by the executor because Milvus was unavailable in the test environment. BILL-04 (tariff queries via RAG) is partially satisfied — the document exists and contains the required content, but it will not be retrievable until the ingestion script is run against a live Milvus instance. This is a deployment step, not a code gap.

All 24 billing tests pass. Full backend suite (113 tests) passes with no regression. TypeScript compiles clean.

---

_Verified: 2026-03-31T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
