---
status: partial
phase: 05-billing-tariff-q-a
source: [05-VERIFICATION.md]
started: 2026-03-31T14:35:00.000Z
updated: 2026-03-31T14:35:00.000Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Full Billing Q&A Flow
expected: Start Docker Compose, ask "Faturam neden yuksek?" as Ahmet Y., verify response references real bill amounts and Turkish line-item categories.
result: [pending]

### 2. Customer Session Isolation
expected: Switch from Ahmet to Elif, confirm messages clear and subsequent bill query reflects Elif's Silver 5GB data.
result: [pending]

### 3. RAG Re-ingestion (BILL-04)
expected: Run `cd backend && uv run python scripts/ingest_documents.py` with Milvus live, then verify "KDV nedir?" in Genel Sohbet mode retrieves from the new fatura_bilgileri.txt document. This is a deployment step, not a code gap.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
