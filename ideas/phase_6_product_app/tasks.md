# Phase 6 — Tasks

## Pod-fazy

- **P6.0** — Customer discovery + research (przed kodem, 3-4 tyg.)
- **P6.1** — MVP API (3 SKU pure API, 4-6 tyg.)
- **P6.2** — V1 Dashboards (Club + Coach, 6-10 tyg.)
- **P6.3** — Sales + pierwsi klienci (ongoing)

## P6.0 — Discovery & Research

| # | Task | Owner | Collab | Depends on | DoD |
|---|------|-------|--------|------------|-----|
| P6.0.1 | Lista 20 potencjalnych klientów per segment | Lead | Designer | — | Lista w Notion z kontaktami, LinkedIn, statusem |
| P6.0.2 | Outreach script + cold email template | Lead | Designer | P6.0.1 | Template tested, outbound flow gotowy |
| P6.0.3 | 20 wywiadów z potencjalnymi klientami (Zoom, 30 min) | Lead | Designer | P6.0.1 | Notatki w Notion, transcripts, summary per segment |
| P6.0.4 | Customer discovery summary — insights, patterns, willingness to pay | Lead | Designer | P6.0.3 | `docs/customer_discovery_summary.md` |
| P6.0.5 | Segment prioritization — który segment najpierw | Lead | — | P6.0.4 | Decyzja: kluby czy tipsterzy czy researcherzy jako first |
| P6.0.6 | Competitive analysis (10 konkurentów) | Lead | Designer | — | `docs/competitive_analysis.md` z feature matrixem, pricingiem |
| P6.0.7 | Legal review — GDPR, regulacje per kraj, licencje | Lead | SWE | — | Raport prawnika, decyzje compliance, ToS + Privacy draft |
| P6.0.8 | Pricing experiments — landing z 3 cennikami, A/B test | Lead | Designer | P6.0.4 | Min. 100 visits na landing, data zebrana, decyzja o pricing |
| P6.0.9 | Pre-sales — waitlist + early bird offer dla pierwszych 10 klientów | Lead | Designer | P6.0.8 | Landing z waitlist form, min. 30 signups |
| P6.0.10 | Brand identity — logo, kolory, typografia, tone of voice | Designer | Lead | — | Brand guidelines w Figma, logo SVG, brand book |

## P6.1 — MVP API (3 SKU pure API)

### Infrastructure
| # | Task | Owner | Collab | Depends on | DoD |
|---|------|-------|--------|------------|-----|
| P6.1.1 | FastAPI skeleton — routing, middleware, health check | SWE | — | P5 done | API odpowiada 200 na /health |
| P6.1.2 | Auth integration — Clerk lub Auth0 | SWE | Lead | P6.1.1 | Signup, login, password reset działają |
| P6.1.3 | API token management — generowanie, rotacja, rate limits | SWE | DataEng | P6.1.2 | Tokens tworzone per plan, rate limits enforced |
| P6.1.4 | Stripe integration — subscriptions, invoicing, webhooks | SWE | Lead | P6.1.2 | Subskrypcje tworzone, invoices generated, webhooks handled |
| P6.1.5 | Usage analytics — ile calls, ile GB, per user | SWE | DataEng | P6.1.3 | Dashboard pokazuje per-user usage |
| P6.1.6 | Rate limiting — per plan (Basic 1k, Pro 10k, Enterprise unlimited) | SWE | — | P6.1.3 | Limits enforced, 429 response gdy przekroczone |
| P6.1.7 | API dokumentacja — OpenAPI + static docs (Redoc/Mintlify) | SWE | Lead | P6.1.1 | docs.sportslab.xyz z auto-generated docs |

### SKU 1 — Value feed API
| # | Task | Owner | Collab | Depends on | DoD |
|---|------|-------|--------|------------|-----|
| P6.1.8 | Endpoint GET `/v1/value-bets` — query z filters (sport, liga, market, min edge) | SWE | MLEng | P6.1.3 | Endpoint returns cached value bets, pagination, filters |
| P6.1.9 | Endpoint GET `/v1/value-bets/:id` — szczegóły konkretnego beta | SWE | MLEng | P6.1.8 | Details z P, odds, edge, Kelly stake |
| P6.1.10 | Webhook system — nowy value bet → call do klienta URL | SWE | DataEng | P6.1.8 | Webhooks działają, retry, dead letter queue |
| P6.1.11 | Telegram / Discord integration — push value bets jako bot | SWE | MLEng | P6.1.8 | Bot działa, klienci subscribują, value bets pushowane |

### SKU 2 — Data Lake access
| # | Task | Owner | Collab | Depends on | DoD |
|---|------|-------|--------|------------|-----|
| P6.1.12 | Endpoint GET `/v1/matches` — query matches z Postgres via SQLAlchemy | SWE | DataEng | P6.1.3 | Filters: sport, liga, season, date_range; pagination |
| P6.1.13 | Endpoint GET `/v1/teams`, `/v1/players`, `/v1/odds` — CRUD dla core entities | SWE | DataEng | P6.1.12 | Wszystkie endpoints z OpenAPI docs |
| P6.1.14 | Endpoint GET `/v1/features` — raw features per match | SWE | MLEng | P6.1.12 | Features returnable, schema documented |
| P6.1.15 | Bulk download endpoint — Parquet export pod przestawioną query | SWE | DataEng | P6.1.12 | `POST /v1/exports` tworzy export, `GET /v1/exports/:id` pobiera |
| P6.1.16 | Usage-based pricing — per GB downloaded + flat fee | SWE | Lead | P6.1.4 | Stripe metered billing, GB tracking |

### SKU 3 — Probabilities API
| # | Task | Owner | Collab | Depends on | DoD |
|---|------|-------|--------|------------|-----|
| P6.1.17 | Endpoint GET `/v1/predictions` — all upcoming predictions | SWE | MLEng | P6.1.3 | P(H/D/A), P(O/U 2.5), P(BTTS) dla upcoming matches |
| P6.1.18 | Endpoint GET `/v1/predictions/:match_id` — szczegóły predykcji dla meczu | SWE | MLEng | P6.1.17 | Pełne probabilistyka per market |
| P6.1.19 | Endpoint GET `/v1/calibration` — per liga, per sezon | SWE | DrMat | P6.1.17 | Klient widzi ECE per ich use case |
| P6.1.20 | Endpoint GET `/v1/historical-predictions` — backtest data | SWE | MLEng | P6.1.17 | Historical predictions + actual results |

### Public stuff
| # | Task | Owner | Collab | Depends on | DoD |
|---|------|-------|--------|------------|-----|
| P6.1.21 | Landing page — Next.js, Tailwind, responsive | Designer | SWE | P6.0.10 | sportslab.xyz z pricing, signup, features |
| P6.1.22 | Signup flow — email → email verification → onboarding | SWE | Designer | P6.1.2 | User może signup i dostać API token |
| P6.1.23 | Onboarding flow — pierwszy API call tutorial | SWE | Designer | P6.1.22 | Nowy user wie co zrobić, ma działający call w < 5 min |
| P6.1.24 | Billing dashboard — usage, invoices, plan upgrade | SWE | Designer | P6.1.4 | User widzi swoją usage, upgrade self-serve |

## P6.2 — V1 Dashboards (Club + Coach)

### Shared dashboard infrastructure
| # | Task | Owner | Collab | Depends on | DoD |
|---|------|-------|--------|------------|-----|
| P6.2.1 | Next.js app shell — layout, navigation, auth flow | SWE | Designer | P6.1 done | App z login, dashboard nav |
| P6.2.2 | Data visualization library setup (Recharts/Visx/D3) | SWE | Designer | P6.2.1 | Proof-of-concept: 1 chart per library, pick best |
| P6.2.3 | Shared components: filters, date pickers, exports | SWE | Designer | P6.2.1 | Reusable components w `packages/ui/` |
| P6.2.4 | Report builder — user wybiera widoki, eksport PDF | SWE | Designer | P6.2.3 | PDF export działa, customizable |

### Club analytics dashboard (SKU 4)
| # | Task | Owner | Collab | Depends on | DoD |
|---|------|-------|--------|------------|-----|
| P6.2.5 | Designer: wireframes + high-fidelity designs | Designer | Lead | P6.0.10 | Figma file z pełnymi screens |
| P6.2.6 | Opponent scouting view — team profile, formation, xG, strengths/weaknesses | SWE | Designer, MLEng | P6.2.5 | View live, używa data z API |
| P6.2.7 | Radar chart — team comparison (attack, defense, pace, possession) | SWE | Designer, DrMat | P6.2.5 | Interactive radar, customizable metrics |
| P6.2.8 | xG flow chart — per match, cumulative xG over time | SWE | Designer, MLEng | P6.2.5 | D3 chart działa, smooth animations |
| P6.2.9 | Player radar — key players with ratings, form, injuries | SWE | Designer, MLEng | P6.2.5 | Per-player view |
| P6.2.10 | 1-click PDF report generator — "Opponent Report" | SWE | Designer | P6.2.4, P6.2.6 | PDF ~5-10 stron, branded, professional |
| P6.2.11 | Club onboarding — setup ich ligi, ich drużyny | SWE | Designer | P6.2.5 | Self-serve setup |

### Coach analytics multi-sport (SKU 5)
| # | Task | Owner | Collab | Depends on | DoD |
|---|------|-------|--------|------------|-----|
| P6.2.12 | Designer: wireframes + designs per sport (tennis, basketball, hockey) | Designer | Lead | P6.0.10 | Figma files per sport, unified look |
| P6.2.13 | H2H analysis view — head-to-head stats, visualization | SWE | Designer, MLEng | P6.2.12 | View per sport, używa data z API |
| P6.2.14 | Opponent weaknesses view — data-driven insights | SWE | Designer, DrMat | P6.2.12 | Auto-generated insights per opponent |
| P6.2.15 | Custom report builder dla trenerów | SWE | Designer | P6.2.4 | Trenerzy mogą save views, eksportuje PDF |
| P6.2.16 | Per-sport customization — tenis ma inne metrics niż NBA | SWE | Designer | P6.2.12 | Schema-driven rendering |

## P6.3 — Sales + First Customers

| # | Task | Owner | Collab | Depends on | DoD |
|---|------|-------|--------|------------|-----|
| P6.3.1 | Sales collateral — pitch deck, one-pager, case studies template | Lead | Designer | P6.0.4 | Materials w Notion + Google Slides |
| P6.3.2 | Demo environment — mock client account z sample data | Lead | SWE | P6.2 done | Demo ready dla sales calls |
| P6.3.3 | Outreach — 50 outbound contacts per tydzień | Lead | — | P6.3.1 | Linear tracking leads, CRM-lite |
| P6.3.4 | First 5 klientów — negotiated, contract, onboarded | Lead | SWE | P6.3.3 | 5 invoices, MRR tracking |
| P6.3.5 | First case study — zgoda klienta, publikacja | Lead | Designer | P6.3.4 | Case study na landing page |
| P6.3.6 | Customer success — onboarding calls, support | Lead | SWE | P6.3.4 | NPS tracking, churn monitoring |
| P6.3.7 | Referral program — klient poleca, dostaje discount | Lead | SWE | P6.3.4 | Referral system w aplikacji |

## P6.4 — V2 SKU (jeśli pierwsze 5 klientów zadziała)

| # | Task | Owner | Collab | Depends on | DoD |
|---|------|-------|--------|------------|-----|
| P6.4.1 | SKU 7 — Backtest-as-a-service | MLEng | SWE, Designer | P6.2, P6.3 done | Klient uploadi strategię, dostaje raport |
| P6.4.2 | SKU 8 — White-label platform | SWE | Designer | P6.3 done | Partner może rebrand aplikację |
| P6.4.3 | SKU 9 — Telegram Pro bot (B2C) | SWE | MLEng | P6.1 done | Bot z subskrypcją via Stripe |
| P6.4.4 | SKU 6 — Custom consulting offering | Lead | DrMat | — | Oferta + first project delivered |

## Równoległa praca w P6

- **DrMat**: Supports MLEng w API endpoints, model explanations
- **DataEng**: Postgres optimization, query performance, custom views dla dashboards
- **Designer**: Główna rola w P6 — wszystkie dashboardy, brand, landing
- **MLEng**: Pipeline optymalizacje, API integration, explanations
- **Lead**: Customer discovery + sales + pierwsi klienci (główna rola)

## Kluczowe decyzje w P6

1. **Next.js 14 vs 15** — wait until Next 15 stable (rekomendacja: use latest stable)
2. **Clerk vs Auth0 vs self-hosted** — **rekomendacja: Clerk** (szybkość, ergonomia)
3. **Self-hosted Postgres vs Supabase** — **rekomendacja: Supabase** dla P6 (szybciej), self-hosted w P6+ gdy >100 klientów
4. **Stripe vs Paddle vs Lemon Squeezy** — **rekomendacja: Stripe** (standard B2B, invoice, metered)
5. **Pricing model** — subscription vs usage vs hybrid. **Rekomendacja: hybrid** (flat fee + usage overage)
6. **PL vs EN language** — **rekomendacja: EN only w MVP**, PL jako fallback dla landing
7. **Dorekrutacja Growth/Marketing** — kiedy i czy? **Rekomendacja: przed P6.3**
8. **B2C czy nie** — **decyzja: pomijamy w MVP**, może V2/V3 jeśli scale pozwala

## DoD fazy P6

- [ ] Aplikacja live na `app.sportslab.xyz`
- [ ] API live na `api.sportslab.xyz` z dokumentacją
- [ ] Landing page na `sportslab.xyz`
- [ ] Min. **3 MVP SKU** dostępne do sprzedaży (Value feed, Data Lake, Probabilities)
- [ ] Min. **1 V1 dashboard** (Club lub Coach) live
- [ ] **≥ 1 płacący klient B2B** z invoice > €200
- [ ] **MRR > koszty infra** (break-even)
- [ ] Customer onboarding automatyczny (self-serve możliwy)
- [ ] Usage analytics działa
- [ ] Legal compliance (ToS, Privacy Policy, GDPR) zaakceptowane przez prawnika
- [ ] Pierwsze case study opublikowane
