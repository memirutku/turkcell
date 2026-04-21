<div align="center">

<a id="top"></a>

# Umay AI-Gen

### Telekom müşteri asistanı · Telecom customer AI assistant

<p>
  <b>EN</b> — <i>Voice &amp; text AI for telecom customer-service scenarios: FastAPI, Next.js, Docker Compose, RAG (Milvus), MCP, Gemini.</i><br>
  <b>TR</b> — <i>Telekom müşteri hizmetleri için sesli ve metin asistanı: FastAPI, Next.js, Docker Compose, RAG (Milvus), MCP, Gemini.</i>
</p>

**Dil &nbsp;·&nbsp; Language:** [**English**](#english) &nbsp;|&nbsp; [**Türkçe**](#turkce)

[![](https://img.shields.io/badge/frontend-Next.js%2014-0d1117?logo=nextdotjs)](https://nextjs.org/) [![](https://img.shields.io/badge/backend-FastAPI-0d1117?logo=fastapi)](https://fastapi.tiangolo.com/) [![](https://img.shields.io/badge/orchestration-Docker%20Compose-0d1117?logo=docker)](https://docs.docker.com/compose/) [![](https://img.shields.io/badge/RAG-Milvus-0d1117)](https://milvus.io/) [![](https://img.shields.io/badge/LLM-Google%20GenAI-0d1117?logo=google)](https://ai.google.dev/) [![](https://img.shields.io/badge/protocol-MCP-0d1117)](https://modelcontextprotocol.io/)

**Repo:** [github.com/memirutku/turkcell](https://github.com/memirutku/turkcell)

</div>

---

<a id="english"></a>

## English

Umay AI-Gen is a voice and text AI assistant project built for telecom customer-service scenarios.  
It includes a FastAPI backend, a Next.js frontend, and supporting services orchestrated with Docker Compose.

### Demo Notice

This repository is a **competition demo/prototype** and is shared publicly for portfolio and technical showcase purposes.

### Support

If you find this project useful, **please consider starring the repository**.

### Competition Background

This project was developed for Turkcell's "Yarının Teknoloji Liderleri" competition and reached the semi-finals.

- Competition page: [Yarının Teknoloji Liderleri Yarışması](https://www.turkcell.com.tr/yarininteknolojiliderleri/)

### Stack (short)

| Area                    | Choices                                                                 |
| ----------------------- | ----------------------------------------------------------------------- |
| Frontend                | Next.js 14, React 18, TypeScript, Tailwind CSS, Zustand                 |
| Backend                 | FastAPI, Python 3.12+, LangChain/LangGraph, Google GenAI SDK            |
| Data & infrastructure  | Milvus, Redis, MinIO, Etcd, Traefik                                    |
| Realtime & safety       | SSE streaming, WebSocket, Presidio (PII masking)                        |
| Public integration      | App via Traefik; MCP tools served under `/mcp`                                        |

### Key features

| Feature                         | What it is                                                              |
| ------------------------------- | ----------------------------------------------------------------------- |
| Text chat + streaming            | Server-sent streaming chat responses from the FastAPI layer             |
| Live Voice                       | Real-time voice interaction (Google Live / `GEMINI_LIVE_ENABLED`)        |
| RAG (Milvus)                    | Document-backed answers via a Milvus vector store                       |
| Personalization                | Profile and usage-based flows; tool calls exposed through MCP         |
| Local environment              | `docker compose up` brings the full stack (see Quick Start)             |

### MCP (Model Context Protocol)

MCP is exposed for personalized telecom recommendations and analysis.

| Aspect        | Details                                                                                |
| ------------- | -------------------------------------------------------------------------------------- |
| Purpose       | Standardized tool access for assistant-side personalization and recommendation logic   |
| Focus area   | Tariff/package fit, usage insights, customer risk–style signals                        |
| Integration  | Invoked from assistant flows and available as an MCP-compatible HTTP surface         |

#### Full MCP tool list

| Tool (name)                                 | Route                     | What it does                                                         |
| ------------------------------------------- | ------------------------- | -------------------------------------------------------------------- |
| `get_personalized_tariff_recommendations`  | `/tariff-recommendations` | Suggests tariffs from profile + usage                                |
| `get_personalized_package_recommendations` | `/package-recommendations` | Suggests add-on packages                                            |
| `get_customer_risk_profile`                 | `/customer-risk-profile`  | Churn, loyalty, and value-oriented risk view                         |
| `get_usage_pattern_analysis`                 | `/usage-pattern-analysis` | Time- and category-based usage patterns                            |
| `get_market_comparison`                     | `/market-comparison`      | Compare a selected Umay tariff to competitor-like market offers     |

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

| Variable                 | Default / example              | Meaning                                                |
| ------------------------ | ----------------------------- | ------------------------------------------------------ |
| `GEMINI_API_KEY`         | empty                         | If empty, Gemini-powered features are limited/disabled  |
| `NEXT_PUBLIC_API_URL`    | `http://localhost:8000`       | URL the browser uses to call the API                   |
| `GEMINI_LIVE_ENABLED`    | `false`                       | Set to `true` to enable real-time (Live) voice mode   |

3) Start services:

```bash
docker compose up --build
```

4) Open the app (local):

| What              | URL                     |
| ----------------- | ----------------------- |
| App (Traefik)     | `http://localhost`      |
| Frontend (direct) | `http://localhost:3000` |
| Backend (direct)  | `http://localhost:8000` |
| Traefik dashboard | `http://localhost:8080` |

### API and health (reference)

| Kind        | Path / prefix | Notes                    |
| ----------- | ------------- | ------------------------ |
| Health      | `GET /api/health` | Liveness/health check |
| Chat / REST | `/api/...`    | App-specific HTTP routes |
| WebSocket   | `/ws/...`     | Streaming and live features |
| MCP         | `/mcp`        | Model Context Protocol tools and metadata |

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

**[↑ Back to top](#top)**

---

<a id="turkce"></a>

## Türkçe

Umay AI-Gen, telekom müşteri hizmetleri senaryoları için geliştirilmiş, sesli ve metin tabanlı bir yapay zeka asistanı projesidir.  
Proje; FastAPI tabanlı bir backend, Next.js tabanlı bir frontend ve Docker Compose ile orkestre edilen yardımcı servislerden oluşur.

### Demo Notu

Bu repo bir **yarışma demosu/prototipi** olarak geliştirilmiştir ve portföy ile teknik paylaşım amaçlı public olarak yayınlanmıştır.

### Destek

Projeyi faydalı bulduysanız, **repo'yu yıldızlamayı unutmayın**.

### Yarışma Geçmişi

Bu proje, Turkcell'in Yarının Teknoloji Liderleri yarışması kapsamında geliştirilmiştir ve yarı finale yükselmiştir.

- Yarışma sayfası: [Yarının Teknoloji Liderleri Yarışması](https://www.turkcell.com.tr/yarininteknolojiliderleri/)

### Yığın (özet)

| Alan                    | Seçimler                                                                 |
| ----------------------- | ------------------------------------------------------------------------ |
| Ön uç (frontend)      | Next.js 14, React 18, TypeScript, Tailwind CSS, Zustand                 |
| Arka uç (backend)       | FastAPI, Python 3.12+, LangChain/LangGraph, Google GenAI SDK            |
| Veri ve altyapı        | Milvus, Redis, MinIO, Etcd, Traefik                                    |
| Gerçek zaman ve güvenlik | SSE akışı, WebSocket, Presidio (PII maskeleme)                        |
| Dışa açılan entegrasyon  | Uygulama Traefik üzerinden; MCP araçları `/mcp` altında                  |

### Öne çıkan özellikler

| Özellik                 | Açıklama                                                                |
| ----------------------- | ----------------------------------------------------------------------- |
| Metin sohbet + akış     | Sunucu tarafında akışlı (streaming) sohbet yanıtları                    |
| Live Voice              | Gerçek zamanlı ses (Google Live / `GEMINI_LIVE_ENABLED`)                 |
| RAG (Milvus)            | Milvus vektör veritabanı ile belge destekli yanıtlar                    |
| Kişiselleştirme         | Profil ve kullanıma dayalı akışlar; araçlar MCP üzerinden               |
| Yerel ortam            | `docker compose up` ile tüm yığın (Hızlı Başlangıç’a bakın)             |

### MCP (Model Context Protocol)

MCP, kişiselleştirilmiş telekom önerileri ve analizleri için kullanılır.

| Boyut         | Açıklama                                                                               |
| ------------- | -------------------------------------------------------------------------------------- |
| Amaç          | Asistan tarafındaki kişiselleştirme/öneri mantığı için standart araç sözleşmesi         |
| Odak         | Tarife ve paket uyumu, kullanım içgörüleri, müşteri riski tarzı sinyaller                |
| Entegrasyon  | Asistan akışlarının yanında, dışarıdan MCP uyumlu HTTP yüzeyi olarak da erişilebilir    |

#### Tam MCP araç listesi

| Araç (ad)                                 | Rota                        | Ne yapar                                                                 |
| ---------------------------------------- | --------------------------- | ------------------------------------------------------------------------ |
| `get_personalized_tariff_recommendations` | `/tariff-recommendations`  | Profil + kullanıma göre tarife önerileri                                 |
| `get_personalized_package_recommendations` | `/package-recommendations` | Ek paket önerileri                                                      |
| `get_customer_risk_profile`              | `/customer-risk-profile`   | Churn, sadakat ve değer odaklı risk görünümü                            |
| `get_usage_pattern_analysis`             | `/usage-pattern-analysis`  | Zaman ve kategori bazlı kullanım kalıbı                                 |
| `get_market_comparison`                 | `/market-comparison`       | Seçilen Umay tarifesini piyasadaki benzer tekliflerle kıyaslama         |

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

| Değişken                 | Varsayılan / örnek           | Anlamı                                                      |
| ------------------------ | ----------------------------- | ---------------------------------------------------------- |
| `GEMINI_API_KEY`         | boş                           | Boşsa Gemini tabanlı özellikler sınırlı veya kapalı olabilir |
| `NEXT_PUBLIC_API_URL`    | `http://localhost:8000`       | Tarayıcının API’ye giderken kullandığı adres                 |
| `GEMINI_LIVE_ENABLED`    | `false`                       | Gerçek zamanlı (Live) ses için `true` yapın                 |

3) Servisleri başlat:

```bash
docker compose up --build
```

4) Uygulamayı aç (lokal):

| Ne                    | Adres                    |
| --------------------- | ------------------------ |
| Uygulama (Traefik)   | `http://localhost`       |
| Ön uç (doğrudan)     | `http://localhost:3000` |
| Arka uç (doğrudan)   | `http://localhost:8000`  |
| Traefik paneli       | `http://localhost:8080`  |

### API ve sağlık (özet)

| Tür          | Yol / önek    | Not                                     |
| ------------ | ------------- | ---------------------------------------- |
| Sağlık      | `GET /api/health` | Canlılık / health kontrolü         |
| Sohbet / REST | `/api/...`  | Uygulamaya özel HTTP yolları          |
| WebSocket  | `/ws/...`     | Akış ve canlı özellikler                 |
| MCP        | `/mcp`        | Model Context Protocol araçları ve metadata |

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

**[↑ Başa dön](#top)**
