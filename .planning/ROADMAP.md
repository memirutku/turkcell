# Roadmap: Turkcell AI-Gen

## Overview

Turkcell AI-Gen is a Turkish-language AI customer assistant combining RAG-based knowledge retrieval, voice interaction, and agentic capabilities. The roadmap progresses from infrastructure through retrieval quality, chat UX, security compliance, domain intelligence, voice interaction, agentic actions, and accessibility -- each phase delivering a verifiable user-facing capability that builds on the previous. The dependency chain reflects architectural reality: embeddings before LLM, PII masking before voice, billing intelligence before agent actions, and accessibility as a hardening pass over all features.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Infrastructure & Foundation** - Docker Compose environment with all services running and mock data available
- [ ] **Phase 2: Turkish Embedding & RAG Pipeline** - Turkish document corpus indexed in Milvus with accurate vector retrieval
- [ ] **Phase 3: Core Chat & LLM Integration** - Working text chat with Gemini, streaming responses, conversation memory, and polished UI
- [ ] **Phase 4: PII Masking & KVKK Compliance** - All user data masked before reaching Gemini, with Turkish-specific PII detection
- [ ] **Phase 5: Billing & Tariff Q&A** - Users can ask billing and tariff questions and get accurate, natural-language answers from mock data
- [ ] **Phase 6: Personalized Recommendations & Rich UI** - Usage-based tariff recommendations with savings calculations and rich billing cards
- [ ] **Phase 7: Voice Input & Output** - Users can speak to the assistant and hear responses in natural Turkish voice
- [ ] **Phase 8: Full Voice Conversation** - Continuous hands-free voice interaction with automatic turn detection
- [ ] **Phase 9: Agentic Capabilities** - Assistant can execute actions (package activation, tariff change) with user confirmation
- [ ] **Phase 10: Accessibility & Hardening** - WCAG 2.1 AA compliance, screen reader support, and eyes-free operation

## Phase Details

### Phase 1: Infrastructure & Foundation
**Goal**: All project services run from a single `docker compose up` command with health checks passing and mock data accessible
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, INFRA-06, INFRA-07
**Success Criteria** (what must be TRUE):
  1. Running `docker compose up` starts all containers (FastAPI, Next.js, Milvus, Redis) and they reach healthy state
  2. FastAPI health endpoint returns 200 and Next.js dev server loads in browser
  3. Mock BSS/OSS API returns realistic billing, tariff, and package data when queried
  4. Milvus accepts connections and Redis stores/retrieves session data
  5. API keys and credentials are loaded from .env file, not hardcoded anywhere
**Plans**: 3 plans in 2 waves

Plans:
- [x] 01-01-PLAN.md — Docker Compose infrastructure with 7 services, .env config, verification script (Wave 1)
- [x] 01-02-PLAN.md — FastAPI backend with health endpoint and Mock BSS/OSS API (Wave 2)
- [x] 01-03-PLAN.md — Next.js frontend with Tailwind CSS and health status landing page (Wave 2)

### Phase 2: Turkish Embedding & RAG Pipeline
**Goal**: Turkcell documents (tariffs, campaigns, FAQ) are chunked, embedded with a Turkish-capable model, and retrievable via semantic search in Milvus
**Depends on**: Phase 1
**Requirements**: RAG-01, RAG-02, RAG-05
**Success Criteria** (what must be TRUE):
  1. Turkcell document corpus is chunked with Turkish-aware sentence splitting and indexed in Milvus
  2. A user query in Turkish returns relevant document chunks from Milvus (precision target: 75%+ on telecom queries)
  3. Embedding model handles Turkish telecom terminology correctly (agglutinative morphology, domain jargon)
**Plans**: 2 plans in 2 waves

Plans:
- [x] 02-01-PLAN.md — LangChain dependencies, Turkish document corpus, config, and ingestion script (Wave 1)
- [x] 02-02-PLAN.md — RAGService retrieval layer, /api/rag/search endpoint, and test suite (Wave 2)

### Phase 3: Core Chat & LLM Integration
**Goal**: Users can have a multi-turn text conversation with the assistant through a polished web interface, receiving streaming Gemini responses grounded in RAG context
**Depends on**: Phase 1, Phase 2
**Requirements**: CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-05, CHAT-06, CHAT-07, RAG-03, RAG-04, UI-01, UI-03, UI-04
**Success Criteria** (what must be TRUE):
  1. User types a question in the chat interface and receives a streaming Turkish response from Gemini
  2. Responses are grounded in RAG context -- the assistant does not fabricate tariff details or billing amounts
  3. Conversation memory persists across multiple turns (at least 10-15 turns within a session)
  4. Chat UI displays messages in styled bubbles with user/assistant distinction, markdown rendering, and responsive layout
  5. Typing indicator shows during response generation, and errors display user-friendly Turkish messages
**Plans**: 3 plans in 2 waves

Plans:
- [ ] 03-01-PLAN.md — Backend chat engine: ChatService, MemoryService, system prompt, SSE endpoint, tests (Wave 1)
- [ ] 03-02-PLAN.md — Frontend foundation: shadcn/ui init, zustand store, SSE client, chat types (Wave 1)
- [ ] 03-03-PLAN.md — Chat UI components, /chat page, and visual verification checkpoint (Wave 2)

### Phase 4: PII Masking & KVKK Compliance
**Goal**: All personally identifiable information is detected and masked before any data reaches Gemini, with Turkish-specific recognizers for TC Kimlik, IBAN, and phone numbers
**Depends on**: Phase 3
**Requirements**: SEC-01, SEC-02, SEC-03, SEC-04, SEC-05
**Success Criteria** (what must be TRUE):
  1. Turkish PII (names, TC Kimlik No, phone numbers, IBAN) in user messages is masked before being sent to Gemini
  2. Presidio with custom Turkish recognizers correctly identifies TC Kimlik, Turkish phone format, and IBAN patterns
  3. Application logs never contain unmasked PII -- all logging is sanitized
  4. AI guardrails prevent the model from being manipulated into revealing masked or sensitive information
**Plans**: TBD

Plans:
- [x] 04-01-PLAN.md — Presidio/spaCy dependencies, Turkish PII recognizers (TC Kimlik, phone, IBAN), PIIMaskingService, test suite (Wave 1)
- [ ] 04-02-PLAN.md — ChatService PII integration, log sanitization filter, system prompt guardrails, Dockerfile update (Wave 2)

### Phase 5: Billing & Tariff Q&A
**Goal**: Users can ask natural-language questions about their bills and available tariffs and receive accurate, detailed answers from mock data
**Depends on**: Phase 3, Phase 4
**Requirements**: BILL-01, BILL-02, BILL-03, BILL-04
**Success Criteria** (what must be TRUE):
  1. User can ask "faturam neden yuksek?" and receive a breakdown of bill components (base fee, overages, taxes) in natural Turkish
  2. User can query their current tariff and get accurate details from mock data
  3. Available tariffs and campaigns are retrievable via RAG and presented clearly
**Plans**: TBD

Plans:
- [x] 05-01: TBD
- [ ] 05-02: TBD

### Phase 6: Personalized Recommendations & Rich UI
**Goal**: The assistant analyzes user usage patterns and recommends optimal tariffs with concrete savings calculations, displayed in rich UI cards
**Depends on**: Phase 5
**Requirements**: BILL-05, BILL-06, UI-05
**Success Criteria** (what must be TRUE):
  1. User receives a personalized tariff recommendation based on their mock usage data (not generic suggestions)
  2. Savings calculation is shown with specific amounts ("Bu paket aylik 40 TL tasarruf saglar")
  3. Billing details and recommendations display in structured UI cards with tables, not just plain text
**Plans**: TBD

Plans:
- [x] 06-01-PLAN.md — TariffRecommendationService with Decimal savings, structured SSE events, billing prompt extension (Wave 1)
- [x] 06-02-PLAN.md — Rich UI recommendation cards, usage gauges, savings display (Wave 2)

### Phase 7: Voice Input & Output
**Goal**: Users can speak to the assistant using their microphone and hear responses read aloud in natural Turkish voice
**Depends on**: Phase 4
**Requirements**: VOICE-01, VOICE-02, VOICE-05, VOICE-06, UI-02
**Success Criteria** (what must be TRUE):
  1. User clicks the microphone button and their speech is transcribed to text via AWS Transcribe
  2. Assistant responses are read aloud in natural Turkish voice via AWS Polly (Filiz neural voice)
  3. Audio streams over WebSocket (not file upload/download) for low-latency interaction
  4. Voice recording button shows visual feedback (waveform animation) during recording and processing
**Plans**: TBD

Plans:
- [x] 07-01: Voice services backend (Gemini STT + AWS Polly TTS)
- [x] 07-02: Voice WebSocket endpoint
- [x] 07-03: Voice UI frontend (mic button, waveform, state machine)

### Phase 8: Full Voice Conversation
**Goal**: Users can have a continuous hands-free voice conversation without manually pressing buttons for each turn
**Depends on**: Phase 7
**Requirements**: VOICE-03, VOICE-04, VOICE-07
**Success Criteria** (what must be TRUE):
  1. User can speak continuously without pressing a button for each turn -- the system detects when they stop talking
  2. Voice Activity Detection (VAD) correctly identifies speech boundaries and silence
  3. End-to-end voice loop latency (speak -> transcribe -> LLM -> synthesize -> play) is under 3 seconds
**Plans**: TBD

Plans:
- [x] 08-01-PLAN.md -- Sentence-level TTS streaming, WAV auto-detection, WebSocket streaming pipeline (Wave 1)
- [ ] 08-02: TBD

### Phase 9: Agentic Capabilities
**Goal**: The assistant can reason through multi-step workflows and execute telecom actions (package activation, tariff change) against mock APIs with explicit user confirmation
**Depends on**: Phase 5, Phase 4
**Requirements**: AGENT-01, AGENT-02, AGENT-03, AGENT-04, AGENT-05, AGENT-06
**Success Criteria** (what must be TRUE):
  1. LangGraph agent follows a reason-act-observe workflow to handle complex requests (analyze -> recommend -> execute)
  2. User can confirm or reject proposed actions ("Bu paketi tanimlayalim mi?") before execution
  3. Mock package activation and tariff change operations execute successfully and return realistic responses
  4. Gemini function calling integrates with defined tools (bill lookup, tariff change, package activation)
**Plans**: 3 plans in 3 waves

Plans:
- [x] 09-01-PLAN.md — Mock BSS action methods, agent tools, schemas, and agent prompt (Wave 1)
- [ ] 09-02-PLAN.md — LangGraph StateGraph agent service and SSE API endpoints (Wave 2)
- [ ] 09-03-PLAN.md — Frontend action confirmation/result UI components and chatStore integration (Wave 3)

### Phase 10: Accessibility & Hardening
**Goal**: The complete application meets WCAG 2.1 AA accessibility standards and enables fully eyes-free operation for visually impaired users
**Depends on**: Phase 8, Phase 9
**Requirements**: A11Y-01, A11Y-02, A11Y-03, A11Y-04
**Success Criteria** (what must be TRUE):
  1. All interactions (text chat, voice, billing, agent actions) can be completed using only voice -- no visual interaction required
  2. Screen readers (NVDA, VoiceOver) can navigate the entire interface with proper ARIA labels and live regions
  3. Color contrast ratios meet WCAG 2.1 AA (4.5:1 for text, 3:1 for large text) and font sizes are readable
  4. The Selin user story works end-to-end: a visually impaired user discovers a high bill cause and activates a better package via voice alone
**Plans**: TBD

Plans:
- [ ] 10-01: TBD
- [ ] 10-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9 -> 10

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Infrastructure & Foundation | 0/3 | Planned | - |
| 2. Turkish Embedding & RAG Pipeline | 0/2 | Not started | - |
| 3. Core Chat & LLM Integration | 2/3 | In progress (checkpoint pending) | - |
| 4. PII Masking & KVKK Compliance | 1/2 | In progress | - |
| 5. Billing & Tariff Q&A | 0/2 | Not started | - |
| 6. Personalized Recommendations & Rich UI | 2/2 | Complete | 2026-03-31 |
| 7. Voice Input & Output | 2/3 | In Progress|  |
| 8. Full Voice Conversation | 1/2 | In progress | - |
| 9. Agentic Capabilities | 1/3 | In progress | - |
| 10. Accessibility & Hardening | 0/2 | Not started | - |
