<!-- GSD:project-start source:PROJECT.md -->
## Project

**Turkcell AI-Gen**

Turkcell AI-Gen, LLM ve RAG teknolojilerini kullanarak Turkcell altyapısına özel, anlık ve hatasız çözüm sunan bulut tabanlı bir dijital asistan sistemidir. Müşterilerin fatura analizi, tarife değişikliği ve teknik destek gibi taleplerini sesli yapay zeka ile saniyeler içinde çözerek, geleneksel çağrı merkezi deneyimini dönüştürmeyi hedefler. Bireysel ve kurumsal Turkcell abonelerine, özellikle dijital kanalları aktif kullanan gençlere, yoğun iş profesyonellerine ve sesli erişilebilirliğe ihtiyaç duyan engelli bireylere hizmet eder.

**Core Value:** Müşterilerin fatura, tarife ve destek taleplerini sesli AI asistan ile saniyeler içinde, insan benzeri empatiyle çözmek — bekleme stresini ortadan kaldırmak.

### Constraints

- **Tech Stack**: Next.js (frontend) + Python FastAPI (backend) + Google Gemini API (LLM) + Milvus (vector DB) + AWS Transcribe/Polly (voice) — kullanıcı tercihi
- **Veri**: Mock/sentetik Turkcell verisi kullanılacak, gerçek müşteri verisi yok
- **LLM**: Google Gemini API (doküman Gemini 3 belirtiyor, mevcut en güncel Gemini API kullanılacak)
- **Güvenlik**: PII maskeleme zorunlu — kişisel veriler LLM'e gönderilmeden önce maskelenmeli (KVKK)
- **Dil**: Türkçe doğal dil anlama (NLU) öncelikli
- **Deploy**: Docker Compose ile containerized mimari
- **Erişilebilirlik**: Görme engelli kullanıcılar için sesli etkileşim kalitesi kritik
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### Core Technologies
| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| **Python** | 3.12+ | Backend runtime | FastAPI and all AI/ML libraries target 3.12. Performance improvements (PEP 684 per-interpreter GIL), improved error messages. 3.11 minimum, 3.12 preferred. | HIGH |
| **FastAPI** | 0.115+ | REST/WebSocket API server | Already decided. Async-native, auto OpenAPI docs, Pydantic v2 integration. Best Python framework for AI service backends. | HIGH |
| **Next.js** | 14.x or 15.x | Frontend framework | Already decided. App Router for streaming responses, Server Components for SEO, built-in API routes for BFF pattern. | HIGH |
| **Google Gemini API** | `google-genai` 1.x | LLM provider | Already decided. Strong multilingual/Turkish capability, large context windows (1M+ tokens on Gemini 1.5 Pro), native function calling for agentic flows, competitive pricing. | HIGH |
| **Milvus** | 2.4+ | Vector database | Already decided. Open-source, self-hosted via Docker, excellent performance for million-scale vectors, hybrid search (dense + sparse). Milvus Lite available for development. | HIGH |
| **AWS Transcribe** | Service (boto3) | Speech-to-Text | Already decided. Turkish language support available. Real-time streaming transcription via WebSocket. | MEDIUM |
| **AWS Polly** | Service (boto3) | Text-to-Speech | Already decided. Neural TTS voices with Turkish support (Filiz voice). SSML support for natural prosody. | MEDIUM |
### RAG Pipeline
| Library | Version | Purpose | Why Recommended | Confidence |
|---------|---------|---------|-----------------|------------|
| **LangChain** | 0.3+ | RAG orchestration & agent framework | Industry standard for RAG pipelines. Excellent Gemini integration via `langchain-google-genai`. Built-in document loaders, text splitters, retrieval chains. Agent framework with tool-calling support. Use LangChain over LlamaIndex because: (1) better agentic capabilities, (2) larger ecosystem, (3) more flexible for custom telecom workflows. | HIGH |
| **langchain-google-genai** | 2.x | Gemini LLM/Embedding integration | Official LangChain partner package for Google Gemini. Supports chat models, embeddings, and function calling. Maintained by Google + LangChain team. | HIGH |
| **langchain-milvus** | 0.1+ | Milvus vector store integration | Official LangChain integration for Milvus. Handles vector upsert, similarity search, metadata filtering. | HIGH |
| **LangGraph** | 0.2+ | Agentic workflow orchestration | LangChain's graph-based agent framework. Better than raw LangChain agents for complex multi-step telecom workflows (bill analysis -> recommendation -> action). Supports cycles, branching, human-in-the-loop. | HIGH |
| **LangSmith** | Cloud/OSS | Tracing & evaluation | Essential for debugging RAG quality. Trace every LLM call, retriever result, and agent step. Free tier sufficient for development. | MEDIUM |
### Embedding Model (Critical for Turkish)
| Model | Dimension | Purpose | Why Recommended | Confidence |
|-------|-----------|---------|-----------------|------------|
| **Gemini Text Embedding** (`text-embedding-004` or latest) | 768 | Primary embedding model | Use Gemini's own embedding API via `langchain-google-genai`. Keeps the stack unified under one provider. Supports Turkish text. Available through the same API key. Cost-effective for this use case. | HIGH |
| **Multilingual E5 Large** (`intfloat/multilingual-e5-large`) | 1024 | Fallback/offline embedding | If you need a self-hosted alternative. Trained on 100+ languages including Turkish. Strong cross-lingual retrieval. Run via `sentence-transformers`. Only use if Gemini embeddings prove insufficient for Turkish retrieval quality. | MEDIUM |
### Voice Pipeline
| Library | Version | Purpose | Why Recommended | Confidence |
|---------|---------|---------|-----------------|------------|
| **boto3** | 1.35+ | AWS SDK for Transcribe/Polly | Standard AWS Python SDK. Use `TranscribeStreamingClient` for real-time STT, `polly.synthesize_speech()` for TTS. | HIGH |
| **amazon-transcribe-streaming-sdk** | 0.6+ | Streaming STT | Provides higher-level async streaming API for real-time transcription. Simpler than raw boto3 WebSocket handling. | MEDIUM |
| **pydub** | 0.25+ | Audio processing | Convert between audio formats (WebM from browser -> PCM for Transcribe). Lightweight, well-maintained. | HIGH |
| **websockets** | 12+ | WebSocket server | Handle real-time audio streaming from browser to FastAPI. Native async support. FastAPI has built-in WebSocket support, but this provides lower-level control if needed. | HIGH |
### Data & Security
| Library | Version | Purpose | Why Recommended | Confidence |
|---------|---------|---------|-----------------|------------|
| **Pydantic** | 2.9+ | Data validation & schemas | Already bundled with FastAPI. Use for all request/response models, config validation, and PII detection schemas. v2 is 5-17x faster than v1. | HIGH |
| **presidio-analyzer** + **presidio-anonymizer** | 2.2+ | PII detection & masking | Microsoft's PII framework. Supports Turkish language via spaCy NER. Essential for KVKK compliance -- mask TC Kimlik No, phone numbers, addresses before sending to Gemini. | HIGH |
| **spacy** | 3.7+ | NLP for PII detection | Required by Presidio for entity recognition. Use `xx_ent_wiki_sm` (multilingual) model. For better Turkish NER, consider training a custom model or using a community Turkish model. | HIGH |
| **python-jose** | 3.3+ | JWT handling | Session token management for user authentication. Lightweight, well-tested. | HIGH |
| **cryptography** | 42+ | Encryption | AES-256 encryption for sensitive data at rest. TLS handled at reverse proxy level. | HIGH |
### Frontend Libraries
| Library | Version | Purpose | Why Recommended | Confidence |
|---------|---------|---------|-----------------|------------|
| **React** | 18.x / 19.x | UI framework | Bundled with Next.js. | HIGH |
| **Tailwind CSS** | 3.4+ / 4.x | Styling | Utility-first CSS. Fast development, consistent design. Industry standard for Next.js projects. | HIGH |
| **shadcn/ui** | Latest | UI components | Not a dependency -- copies component code into your project. Accessible, customizable. Perfect for chat UI, buttons, cards. | HIGH |
| **react-markdown** | 9+ | Markdown rendering | Render LLM responses with formatting (bold, lists, tables). Essential for rich AI responses. | HIGH |
| **zustand** | 5+ | State management | Lightweight global state for chat history, user session, audio state. Simpler than Redux for this scale. | HIGH |
| **use-sound** or **Web Audio API** | - | Audio playback | Play TTS audio responses in the browser. `use-sound` for simple playback, raw Web Audio API for streaming audio. | MEDIUM |
### Infrastructure & DevOps
| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| **Docker** | 25+ | Containerization | Already decided (Docker Compose). Multi-stage builds for smaller images. | HIGH |
| **Docker Compose** | 2.x (v2 spec) | Orchestration | Already decided. Define all services (FastAPI, Milvus, Next.js, Redis) in one file. | HIGH |
| **Redis** | 7+ | Session store & cache | Conversation memory store, rate limiting, response caching. Essential for multi-turn chat. Docker image readily available. | HIGH |
| **Nginx** | 1.25+ | Reverse proxy | TLS termination, WebSocket proxying, static file serving. Place in front of FastAPI and Next.js. | HIGH |
| **Traefik** | 3.x | Alternative reverse proxy | Auto-discovers Docker services, simpler config than Nginx for Docker Compose setups. Choose one: Nginx if you want more control, Traefik if you want simplicity. | MEDIUM |
### Development Tools
| Tool | Purpose | Notes |
|------|---------|-------|
| **uv** | Python package manager | 10-100x faster than pip. Use instead of pip/poetry/pipenv. `uv init`, `uv add`, `uv sync`. Becoming the standard Python package manager. |
| **Ruff** | Python linter + formatter | Replaces flake8, black, isort in one tool. Extremely fast (Rust-based). |
| **pytest** | Python testing | Standard. Use with `pytest-asyncio` for async FastAPI tests. |
| **httpx** | HTTP test client | Async HTTP client for testing FastAPI endpoints. Also useful as production HTTP client. |
| **ESLint** + **Prettier** | JS/TS linting + formatting | Standard for Next.js projects. |
| **pnpm** | Node.js package manager | Faster and more disk-efficient than npm. Better monorepo support if needed. |
## Installation
### Backend (Python)
# Initialize with uv
# Core framework
# LLM & RAG
# Vector DB client
# Voice / AWS
# Security / PII
# Session & caching
# Dev dependencies
### Frontend (Next.js)
# Initialize
# UI
# Dev
### Infrastructure (Docker Compose)
# docker-compose.yml services overview
## Alternatives Considered
| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| **LangChain + LangGraph** | **LlamaIndex** | If the project were purely document Q&A without agentic actions. LlamaIndex excels at pure retrieval but LangGraph is far superior for multi-step agent workflows (approve package, change tariff). |
| **LangChain + LangGraph** | **Raw Gemini SDK** | Only if you want zero abstraction. Loses retrieval chain composability, agent framework, and observability. Not recommended for this complexity level. |
| **Gemini Embeddings** | **OpenAI text-embedding-3-large** | If you already have OpenAI billing. Slightly better multilingual benchmarks but adds a second API provider, complicating the stack. |
| **Gemini Embeddings** | **Self-hosted multilingual-e5-large** | If you need offline/air-gapped operation or embedding costs become significant at scale. Adds GPU infrastructure complexity. |
| **Milvus** | **Qdrant** | Simpler single-binary deployment, good REST API. Use if Milvus's etcd+minio dependencies feel too heavy for a portfolio project. However, Milvus is already decided. |
| **Milvus** | **Chroma** | Simpler for prototyping but not production-grade. Do not use for this project. |
| **Redis** | **In-memory (Python dict)** | Only for local development. Never for production -- loses state on restart. |
| **uv** | **Poetry** | If team is already proficient in Poetry. But uv is objectively faster and now more feature-complete. |
| **Presidio** | **Custom regex PII** | Never for production PII handling. Regex misses edge cases. Presidio has battle-tested recognizers. |
| **zustand** | **Redux Toolkit** | If you need time-travel debugging or very complex state. Overkill for a chat interface. |
| **pnpm** | **npm** | If the team prefers npm simplicity. No strong reason to switch if npm is comfortable. |
## What NOT to Use
| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **Flask** | No async support, no auto-validation, no WebSocket built-in. Inadequate for real-time voice streaming. | FastAPI |
| **LangChain 0.1.x** | Deprecated import paths, different architecture. Many tutorials still reference old APIs. | LangChain 0.3+ with `langchain-google-genai` partner package |
| **ChromaDB for production** | In-process DB, limited scalability, no production clustering. Fine for prototypes, not for a telecom assistant demo. | Milvus (already decided) |
| **gTTS (Google TTS free)** | Low quality, no streaming, rate-limited, no Turkish neural voices. | AWS Polly Neural (already decided) |
| **Whisper (local STT)** | Requires GPU, high latency for real-time, no streaming API. Great for batch but wrong for live conversation. | AWS Transcribe Streaming (already decided) |
| **pip + requirements.txt** | No dependency resolution, no lock file, slow installs. | uv with pyproject.toml |
| **SQLAlchemy for chat history** | Relational DB is overkill for session-scoped conversation data. Adds unnecessary complexity. | Redis with JSON serialization |
| **socket.io** | Adds complexity over native WebSocket. FastAPI has built-in WebSocket support. No need for fallback transports in 2025. | Native WebSocket (FastAPI built-in) |
| **Haystack** | Smaller ecosystem than LangChain, less Gemini support, fewer agentic capabilities. | LangChain + LangGraph |
| **AutoGen / CrewAI** | Multi-agent frameworks -- overkill for a single-assistant system. Adds unnecessary abstraction. | LangGraph for workflow orchestration |
## Turkish Language Considerations
### Critical for This Project
### Recommended Testing Matrix
| Dimension | Test With | Expected Challenge |
|-----------|-----------|-------------------|
| Embedding retrieval | Turkish telecom FAQ pairs | Agglutinative morphology reducing cosine similarity |
| PII detection | Sample TC Kimlik, IBAN, phone numbers | Turkish-specific formats not in Presidio defaults |
| STT accuracy | Spoken telecom queries with accent variation | Telecom jargon, Istanbul vs. Anatolian accents |
| TTS quality | Long bill explanations | Natural prosody for numbers and currency (TL) |
| LLM reasoning | Multi-step tariff comparison in Turkish | Correct Turkish grammar in generated responses |
## Stack Patterns by Variant
- Use WebRTC instead of plain WebSocket for audio
- Consider Deepgram for lower-latency STT (if Turkish support improves)
- Add Voice Activity Detection (VAD) with `silero-vad` or `webrtcvad`
- Replace Docker Compose with Kubernetes
- Use Milvus Operator for K8s-native Milvus deployment
- Add Celery + Redis for async task processing (bulk bill analysis)
- Language detection with `langdetect` or Gemini's built-in detection
- Per-language embedding namespaces in Milvus
- AWS Transcribe/Polly language routing
- Evaluate Gemini Flash (cheaper, faster, slightly less capable)
- Use Gemini Flash for simple queries, Gemini Pro for complex reasoning
- Implement response caching in Redis for common queries
## Version Compatibility Matrix
| Package | Compatible With | Notes |
|---------|-----------------|-------|
| FastAPI 0.115+ | Pydantic 2.9+ | FastAPI 0.100+ requires Pydantic v2. Do not use Pydantic v1. |
| LangChain 0.3+ | langchain-google-genai 2.x | Must use partner packages, not community integrations for Gemini |
| pymilvus 2.4+ | Milvus server 2.4+ | Client and server versions should match major.minor |
| boto3 1.35+ | Python 3.12+ | Check AWS SDK compatibility if using Python 3.13+ |
| Presidio 2.2+ | spaCy 3.7+ | Presidio pins spaCy version range; let it resolve |
| Next.js 14/15 | React 18.x / 19.x | Next.js 15 uses React 19; if using 14, stick with React 18 |
## Architecture Integration: How Pieces Connect
## Sources
- Training data (cutoff May 2025) -- MEDIUM confidence on versions
- FastAPI, LangChain, Milvus, Presidio -- well-established libraries with stable APIs; architectural recommendations are HIGH confidence
- Turkish language considerations -- based on NLP domain knowledge and agglutinative language challenges; HIGH confidence on patterns, MEDIUM confidence on specific model performance claims
- AWS Transcribe/Polly Turkish support -- known to exist as of early 2025; verify current voice options and streaming availability
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
