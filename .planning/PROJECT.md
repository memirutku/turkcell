# Turkcell AI-Gen

## What This Is

Turkcell AI-Gen, LLM ve RAG teknolojilerini kullanarak Turkcell altyapısına özel, anlık ve hatasız çözüm sunan bulut tabanlı bir dijital asistan sistemidir. Müşterilerin fatura analizi, tarife değişikliği ve teknik destek gibi taleplerini sesli yapay zeka ile saniyeler içinde çözerek, geleneksel çağrı merkezi deneyimini dönüştürmeyi hedefler. Bireysel ve kurumsal Turkcell abonelerine, özellikle dijital kanalları aktif kullanan gençlere, yoğun iş profesyonellerine ve sesli erişilebilirliğe ihtiyaç duyan engelli bireylere hizmet eder.

## Core Value

Müşterilerin fatura, tarife ve destek taleplerini sesli AI asistan ile saniyeler içinde, insan benzeri empatiyle çözmek — bekleme stresini ortadan kaldırmak.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Kullanıcı sesli veya metin tabanlı soru sorarak fatura detaylarını öğrenebilir
- [ ] Sistem, RAG mimarisi ile Turkcell'in güncel tarife ve kampanya bilgilerini anlık olarak sorgulayabilir
- [ ] Kullanıcıya kişiselleştirilmiş tarife ve paket önerileri sunulabilir
- [ ] Kullanıcı sesli komutla işlem onaylayabilir (paket tanımlama vb.)
- [ ] Ses girişi metne dönüştürülür (STT - AWS Transcribe)
- [ ] Metin yanıtları doğal sesle okunur (TTS - AWS Polly)
- [ ] Kullanıcı verileri PII maskeleme ile korunur (KVKK uyumu)
- [ ] Oturum hafızası ile çok turlu konuşma desteklenir
- [ ] Web tabanlı chat arayüzü ile etkileşim sağlanır
- [ ] Sistem Docker Compose ile tek komutla ayağa kalkar

### Out of Scope

- Gerçek Turkcell BSS/OSS entegrasyonu — v1'de mock veri kullanılacak
- Mobil uygulama — v1 web-first, mobil sonraki sürümlerde
- Proaktif bildirimler — ileri vadeli özellik
- Çok dilli destek — v1 sadece Türkçe
- Gerçek ödeme/fatura işlemleri — v1'de simülasyon
- OAuth/SSO entegrasyonu — v1'de basit session yönetimi
- 6G entegrasyonu — çok ileri vadeli

## Context

- **Proje Sahipleri**: Mustafa Emir Utku, Yavuz Selim Utku
- **Teknoloji Alanı**: Büyük Veri ve Yapay Zeka
- **Pazar**: 2026 itibarıyla küresel telekom AI pazarı 6.73 milyar dolar. Türkiye pazarında 41 milyar TL potansiyel.
- **Rakipler**: Teneo.ai (Telefónica), IBM watsonx, Ada/Intercom Fin
- **Fark**: "Agentic AI" yaklaşımı — sadece yanıt vermez, işlem yapar. Yerel bulut + Türkçe NLU hassasiyeti.
- **Ticari Model**: Pay-per-resolution (sonuç odaklı fiyatlandırma)
- **Pilot**: Turkcell Dijital Operatör uygulamasında beta fatura analizi modülü
- **User Story**: Görme engelli Selin'in sesli asistanla yüksek fatura nedenini öğrenip avantajlı paket alması
- **Mimari Referans**: proje_dokuman.pdf Ek 2 (RAG + Bulut Entegrasyonu şeması)
- **Veri Güvenliği**: KVKK ve ETSI uyumlu, PII maskeleme, TLS 1.3, AES-256, Zero Trust IAM, AI Guardrails

## Constraints

- **Tech Stack**: Next.js (frontend) + Python FastAPI (backend) + Google Gemini API (LLM) + Milvus (vector DB) + AWS Transcribe/Polly (voice) — kullanıcı tercihi
- **Veri**: Mock/sentetik Turkcell verisi kullanılacak, gerçek müşteri verisi yok
- **LLM**: Google Gemini API (doküman Gemini 3 belirtiyor, mevcut en güncel Gemini API kullanılacak)
- **Güvenlik**: PII maskeleme zorunlu — kişisel veriler LLM'e gönderilmeden önce maskelenmeli (KVKK)
- **Dil**: Türkçe doğal dil anlama (NLU) öncelikli
- **Deploy**: Docker Compose ile containerized mimari
- **Erişilebilirlik**: Görme engelli kullanıcılar için sesli etkileşim kalitesi kritik

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Google Gemini API (LLM) | Dokümanla uyumlu, güçlü Türkçe desteği | — Pending |
| Milvus (Vector DB) | Açık kaynak, self-hosted, Docker uyumlu | — Pending |
| FastAPI (Backend) | Python AI/ML ekosistemiyle doğal uyum | — Pending |
| Next.js (Frontend) | Modern SSR, API routes, React ekosistemi | — Pending |
| Mock veri (v1) | Gerçek Turkcell verisi erişimi yok | — Pending |
| Docker Compose (Deploy) | Tüm servisleri tek komutla ayağa kaldırma | — Pending |
| AWS Transcribe + Polly (Voice) | Dokümanın belirttiği servisler, yüksek kaliteli Türkçe desteği | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-30 after initialization*
