# Requirements: Turkcell AI-Gen

**Defined:** 2026-03-30
**Core Value:** Müşterilerin fatura/tarife/destek taleplerini sesli AI asistan ile saniyeler içinde çözmek

## v1 Requirements

Requirements for initial MVP release. Each maps to roadmap phases.

### Infrastructure

- [x] **INFRA-01**: Proje Docker Compose ile tek komutla ayağa kalkar (backend, frontend, Milvus, Redis)
- [x] **INFRA-02**: FastAPI backend health check endpoint'i çalışır
- [x] **INFRA-03**: Next.js frontend dev server çalışır ve backend'e bağlanır
- [x] **INFRA-04**: Milvus vector DB container'ı çalışır ve bağlantı kabul eder
- [x] **INFRA-05**: Redis session store çalışır
- [x] **INFRA-06**: Mock BSS/OSS API servisi çalışır (fatura, tarife, paket verileri)
- [x] **INFRA-07**: Ortam değişkenleri (.env) ile API anahtarları güvenli şekilde yönetilir

### RAG Pipeline

- [x] **RAG-01**: Turkcell dökümanları (tarifeler, kampanyalar, SSS) chunk'lanarak Milvus'a yüklenir
- [x] **RAG-02**: Kullanıcı sorusu embedding'e dönüştürülür ve Milvus'ta vektör araması yapılır
- [x] **RAG-03**: Bulunan context Gemini'ye prompt ile birlikte gönderilir
- [x] **RAG-04**: Sistem halüsinasyonu minimize eder — yanıtlar sadece bilinen bilgilere dayanır
- [x] **RAG-05**: Embedding modeli Türkçe telekomünikasyon terimlerini doğru şekilde vektörize eder

### Chat & LLM

- [x] **CHAT-01**: Kullanıcı web arayüzünden metin yazarak soru sorabilir
- [x] **CHAT-02**: Gemini API entegrasyonu çalışır ve Türkçe yanıtlar üretir
- [x] **CHAT-03**: Yanıtlar streaming (SSE/WebSocket) ile token token görüntülenir
- [x] **CHAT-04**: Konuşma hafızası (Redis) ile çok turlu diyalog desteklenir (en az 10-15 tur)
- [x] **CHAT-05**: Yazı göstergesi (typing indicator) kullanıcıya geri bildirim verir
- [x] **CHAT-06**: Hata durumlarında kullanıcı dostu Türkçe mesajlar gösterilir
- [x] **CHAT-07**: Sistem empatik bir ton kullanır (sistem prompt mühendisliği ile)

### Fatura & Tarife

- [x] **BILL-01**: Kullanıcı "faturam neden yüksek?" diye sorarak fatura detaylarını öğrenebilir
- [x] **BILL-02**: Fatura kalemleri (ana ücret, aşım, vergiler) doğal dilde açıklanır
- [x] **BILL-03**: Kullanıcının mevcut tarife bilgisi sorgulanabilir
- [x] **BILL-04**: Mevcut tarifeler ve kampanyalar RAG ile sorgulanabilir
- [x] **BILL-05**: Kullanıcıya kullanım analizine dayalı kişiselleştirilmiş tarife önerisi sunulur
- [x] **BILL-06**: Tasarruf hesaplaması yapılır ("Bu paket aylık 40 TL tasarruf sağlar")

### Güvenlik & KVKK

- [x] **SEC-01**: PII maskeleme — isim, telefon, TC Kimlik No Gemini'ye gönderilmeden önce maskelenir
- [x] **SEC-02**: Presidio + özel Türkçe recognizer'lar (TC Kimlik, Türk telefon formatı, IBAN) kullanılır
- [x] **SEC-03**: Log'larda PII asla açık şekilde yazılmaz
- [x] **SEC-04**: AI Guardrails — model hassas bilgileri paylaşmaya zorlanamaz
- [x] **SEC-05**: API anahtarları ve credentials .env dosyasında tutulur, git'e commit edilmez

### Voice AI

- [x] **VOICE-01**: Kullanıcı ses girişi (STT) — AWS Transcribe ile ses metne dönüştürülür
- [x] **VOICE-02**: Sesli yanıt (TTS) — AWS Polly ile metin doğal Türkçe sesle okunur
- [x] **VOICE-03**: Full voice conversation loop — kullanıcı sürekli sesli konuşabilir
- [x] **VOICE-04**: Voice Activity Detection (VAD) — kullanıcının konuşmasının bittiğini algılar
- [x] **VOICE-05**: WebSocket üzerinden streaming ses iletimi (browser ↔ backend)
- [x] **VOICE-06**: Ses işleme sırasında görsel geri bildirim (dalga formu / animasyon)
- [x] **VOICE-07**: Uçtan uca ses döngüsü latency'si 3 saniyenin altında hedeflenir

### Agentic Actions

- [ ] **AGENT-01**: LangGraph ile agent workflow çalışır (analiz → öneri → işlem)
- [ ] **AGENT-02**: Mock paket tanımlama işlemi simüle edilir
- [ ] **AGENT-03**: Mock tarife değişikliği işlemi simüle edilir
- [ ] **AGENT-04**: İşlem öncesi kullanıcı onayı alınır ("Bu paketi tanımlayalım mı?")
- [ ] **AGENT-05**: Gemini function calling ile araçlar (tools) entegre edilir
- [ ] **AGENT-06**: Mock BSS/OSS API'ları gerçekçi yanıtlar ve gecikmeler simüle eder

### Erişilebilirlik

- [ ] **A11Y-01**: Web arayüzü WCAG 2.1 AA seviyesinde erişilebilirdir
- [ ] **A11Y-02**: Tüm etkileşimler yalnızca sesle (eyes-free) tamamlanabilir
- [ ] **A11Y-03**: Ekran okuyucu uyumluluğu (ARIA etiketleri)
- [ ] **A11Y-04**: Yeterli renk kontrastı ve font büyüklüğü

### Frontend UI

- [x] **UI-01**: Modern chat arayüzü (mesaj baloncukları, kullanıcı/asistan ayrımı)
- [x] **UI-02**: Ses kayıt butonu ve ses dalgası animasyonu
- [x] **UI-03**: Responsive tasarım (mobil tarayıcıda çalışır)
- [x] **UI-04**: Markdown rendering (yapılandırılmış yanıtlar, tablolar)
- [x] **UI-05**: Fatura detayları için zengin UI kartları (tablo/card)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Entegrasyonlar

- **INT-01**: Gerçek Turkcell BSS/OSS API entegrasyonu
- **INT-02**: Gerçek ödeme/fatura işlemleri
- **INT-03**: Canlı müşteri temsilcisine aktarım (live agent handoff)
- **INT-04**: CRM entegrasyonu

### Genişleme

- **EXT-01**: Çok dilli destek (İngilizce, Arapça)
- **EXT-02**: Mobil native uygulama (iOS/Android)
- **EXT-03**: Proaktif bildirimler (push notification)
- **EXT-04**: Chat geçmişi kalıcılığı (cross-session)
- **EXT-05**: Özel Turkcell markası ses (custom voice)
- **EXT-06**: Analitik dashboard (Prometheus/Grafana)
- **EXT-07**: OAuth/SSO kimlik doğrulama

## Out of Scope

| Feature | Reason |
|---------|--------|
| Gerçek BSS/OSS entegrasyonu | Production API erişimi ve güvenlik denetimi gerektirir |
| Çok dilli destek | Test yüzeyini N katına çıkarır, Türkçe yeterince zor |
| Mobil native app | Web-first yaklaşım, mobil tarayıcıda çalışır |
| Proaktif bildirimler | Push altyapısı ve KVKK opt-in/opt-out gerektirir |
| Otonom yüksek riskli işlemler | Sözleşme iptali, numara taşıma gibi riskli işlemler v1'de yok |
| Video / ekran paylaşımı | Marjinal değer için çok karmaşık |
| Gerçek zamanlı analitik | Operasyonel araç, kullanıcı değeri yok |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 1 | Complete |
| INFRA-02 | Phase 1 | Complete |
| INFRA-03 | Phase 1 | Complete |
| INFRA-04 | Phase 1 | Complete |
| INFRA-05 | Phase 1 | Complete |
| INFRA-06 | Phase 1 | Complete |
| INFRA-07 | Phase 1 | Complete |
| RAG-01 | Phase 2 | Complete |
| RAG-02 | Phase 2 | Complete |
| RAG-03 | Phase 3 | Complete |
| RAG-04 | Phase 3 | Complete |
| RAG-05 | Phase 2 | Complete |
| CHAT-01 | Phase 3 | Complete |
| CHAT-02 | Phase 3 | Complete |
| CHAT-03 | Phase 3 | Complete |
| CHAT-04 | Phase 3 | Complete |
| CHAT-05 | Phase 3 | Complete |
| CHAT-06 | Phase 3 | Complete |
| CHAT-07 | Phase 3 | Complete |
| BILL-01 | Phase 5 | Complete |
| BILL-02 | Phase 5 | Complete |
| BILL-03 | Phase 5 | Complete |
| BILL-04 | Phase 5 | Complete |
| BILL-05 | Phase 6 | Complete |
| BILL-06 | Phase 6 | Complete |
| SEC-01 | Phase 4 | Complete |
| SEC-02 | Phase 4 | Complete |
| SEC-03 | Phase 4 | Complete |
| SEC-04 | Phase 4 | Complete |
| SEC-05 | Phase 4 | Complete |
| VOICE-01 | Phase 7 | Complete |
| VOICE-02 | Phase 7 | Complete |
| VOICE-03 | Phase 8 | In Progress (backend streaming done, frontend VAD in Plan 02) |
| VOICE-04 | Phase 8 | Complete |
| VOICE-05 | Phase 7 | Complete |
| VOICE-06 | Phase 7 | Complete |
| VOICE-07 | Phase 8 | In Progress (sentence-level TTS streaming reduces latency, needs Plan 02 validation) |
| AGENT-01 | Phase 9 | Pending |
| AGENT-02 | Phase 9 | Pending |
| AGENT-03 | Phase 9 | Pending |
| AGENT-04 | Phase 9 | Pending |
| AGENT-05 | Phase 9 | Pending |
| AGENT-06 | Phase 9 | Pending |
| A11Y-01 | Phase 10 | Pending |
| A11Y-02 | Phase 10 | Pending |
| A11Y-03 | Phase 10 | Pending |
| A11Y-04 | Phase 10 | Pending |
| UI-01 | Phase 3 | Complete |
| UI-02 | Phase 7 | Complete |
| UI-03 | Phase 3 | Complete |
| UI-04 | Phase 3 | Complete |
| UI-05 | Phase 6 | Complete |

**Coverage:**
- v1 requirements: 52 total
- Mapped to phases: 52
- Unmapped: 0

---
*Requirements defined: 2026-03-30*
*Last updated: 2026-03-30 after roadmap creation*
