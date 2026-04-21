# Umay AI-Gen

[EN](#en) | [TR](#tr)

## EN

Umay AI-Gen is a voice and text AI assistant project built for telecom customer-service scenarios.  
It includes a FastAPI backend, a Next.js frontend, and supporting services orchestrated with Docker Compose.

### Demo Notice

This repository is a **competition demo/prototype** and is shared publicly for portfolio and technical showcase purposes.

### Support

If you find this project useful, **please consider starring the repository**.

### Competition Background

This project was developed for Turkcell's "Yarının Teknoloji Liderleri" competition and reached the semi-finals.

- Competition page: [Yarının Teknoloji Liderleri Yarışması](https://www.turkcell.com.tr/yarininteknolojiliderleri/)

### Key Features

- Text-based chat with streaming responses
- Real-time voice interaction (Live Voice mode)
- RAG pipeline with Milvus vector database
- Personalization and recommendation flow (MCP endpoint support)
- One-command local environment with Docker Compose

### Tech Stack

- **Frontend**: Next.js 14, React 18, TypeScript, Tailwind CSS, Zustand
- **Backend**: FastAPI, Python 3.12+, LangChain/LangGraph, Google GenAI SDK
- **Data & Infrastructure**: Milvus, Redis, MinIO, Etcd, Traefik
- **Other**: SSE streaming, WebSocket, Presidio (PII masking)

### Project Structure

```text
.
├── backend/          # FastAPI app, services, tests
├── frontend/         # Next.js app
├── traefik/          # Reverse proxy configuration
├── docker-compose.yml
└── .env.example
```

### Quick Start (Docker)

1) Prepare environment variables:

```bash
cp .env.example .env
```

2) Check at least these values in `.env`:

- `GEMINI_API_KEY=` (if empty, related AI features are disabled)
- `NEXT_PUBLIC_API_URL=http://localhost:8000`
- `GEMINI_LIVE_ENABLED=false` (set `true` to enable voice mode)

3) Start services:

```bash
docker compose up --build
```

4) Open the app:

- App: `http://localhost`
- Frontend (direct): `http://localhost:3000`
- Backend API (direct): `http://localhost:8000`
- Traefik dashboard: `http://localhost:8080`

### API and Health Check

- Health endpoint: `GET /api/health`
- Chat endpoints: `/api/...`
- WebSocket endpoints: `/ws/...`
- MCP endpoint: `/mcp`

Example:

```bash
curl http://localhost:8000/api/health
```

### Development Notes

- Hot-reload behavior can be limited under Docker Compose; rebuilding may be required after changes.
- Frontend dependencies are in `frontend/package.json`; backend dependencies are in `backend/pyproject.toml`.
- Tests and evaluation files are under `backend/tests` and `backend/eval`.

### Local Test Commands

Backend tests:

```bash
cd backend
pytest
```

Frontend lint:

```bash
cd frontend
pnpm lint
```

### Security and Public Release

- Do not commit real API keys from `.env`.
- Run a secret scan before making the repository public.
- Use `.env.example` as the configuration template.

### License

This project was built as a competition/prototype project.

---

## TR

Umay AI-Gen, telekom müşteri hizmetleri senaryoları için geliştirilmiş, sesli ve metin tabanlı bir yapay zeka asistanı projesidir.  
Proje; FastAPI tabanlı bir backend, Next.js tabanlı bir frontend ve Docker Compose ile orkestre edilen yardımcı servislerden oluşur.

### Demo Notu

Bu repo bir **yarışma demosu/prototipi** olarak geliştirilmiştir ve portföy ile teknik paylaşım amaçlı public olarak yayınlanmıştır.

### Destek

Projeyi faydalı bulduysanız, **repo'yu yıldızlamayı unutmayın**.

### Yarışma Geçmişi

Bu proje, Turkcell'in Yarının Teknoloji Liderleri yarışması kapsamında geliştirilmiştir ve yarı finale yükselmiştir.

- Yarışma sayfası: [Yarının Teknoloji Liderleri Yarışması](https://www.turkcell.com.tr/yarininteknolojiliderleri/)

### Öne Çıkan Özellikler

- Metin tabanlı sohbet ve akış (streaming) yanıtları
- Gerçek zamanlı sesli etkileşim (Live Voice modu)
- RAG altyapısı (Milvus vektör veritabanı)
- Kişiselleştirme ve öneri akışı (MCP endpoint desteği)
- Docker Compose ile tek komutta ayağa kaldırılabilen local geliştirme ortamı

### Teknoloji Yığını

- **Frontend**: Next.js 14, React 18, TypeScript, Tailwind CSS, Zustand
- **Backend**: FastAPI, Python 3.12+, LangChain/LangGraph, Google GenAI SDK
- **Veri & Altyapı**: Milvus, Redis, MinIO, Etcd, Traefik
- **Diğer**: SSE streaming, WebSocket, Presidio (PII maskeleme)

### Proje Yapısı

```text
.
├── backend/          # FastAPI uygulaması, servisler, testler
├── frontend/         # Next.js uygulaması
├── traefik/          # Reverse proxy ayarları
├── docker-compose.yml
└── .env.example
```

### Hızlı Başlangıç (Docker ile)

1) Ortam değişkenlerini hazırla:

```bash
cp .env.example .env
```

2) `.env` içinde en az aşağıdaki alanları kontrol et:

- `GEMINI_API_KEY=` (boşsa ilgili AI özellikleri devre dışı kalır)
- `NEXT_PUBLIC_API_URL=http://localhost:8000`
- `GEMINI_LIVE_ENABLED=false` (sesli modu açmak için `true`)

3) Servisleri başlat:

```bash
docker compose up --build
```

4) Uygulamayı aç:

- Uygulama: `http://localhost`
- Frontend (doğrudan): `http://localhost:3000`
- Backend API (doğrudan): `http://localhost:8000`
- Traefik paneli: `http://localhost:8080`

### API ve Sağlık Kontrolü

- Sağlık endpointi: `GET /api/health`
- Sohbet endpointleri: `/api/...`
- WebSocket endpointleri: `/ws/...`
- MCP endpointi: `/mcp`

Örnek:

```bash
curl http://localhost:8000/api/health
```

### Geliştirme Notları

- Docker Compose üzerinde hot-reload davranışı sınırlı olabilir; değişikliklerden sonra yeniden build gerekebilir.
- Frontend bağımlılıkları `frontend/package.json`, backend bağımlılıkları `backend/pyproject.toml` içindedir.
- Test ve değerlendirme dosyaları `backend/tests` ve `backend/eval` altındadır.

### Lokal Test Komutları

Backend testleri:

```bash
cd backend
pytest
```

Frontend lint:

```bash
cd frontend
pnpm lint
```

### Güvenlik ve Public Paylaşım

- Gerçek API anahtarlarını (`.env`) repoya commit etmeyin.
- Public paylaşım öncesi secret taraması yapın.
- Örnek yapılandırma için `.env.example` kullanın.

### Lisans

Bu proje yarışma/prototip amaçlı geliştirilmiştir.

