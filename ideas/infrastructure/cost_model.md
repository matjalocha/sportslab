# Cost Model — Miesięczne koszty per faza

**Owner:** Lead (budget), SWE (infra costs), DataEng (data infra)
**Update cadence:** Co miesiąc po P0, review w gate reviews.

## Koszty per faza (orientacyjne, EUR/miesiąc)

### Phase 0 — Foundations

| Kategoria | Koszt | Notes |
|---|---|---|
| Google Workspace (6 users) | €35 | Business Starter |
| Slack Pro (6 users) | €40 | Standard plan |
| Linear (free tier < 10 users) | €0 | Upgrade w P4+ |
| GitHub Team | €25 | 6 users |
| Figma (2 editors) | €22 | Designer + SWE |
| 1Password Teams (6 users) | €50 | Essential |
| Doppler (team) | €40 | Pro |
| Cloudflare (free) | €0 | — |
| Domain + DNS | €2 | sportslab.xyz |
| Notion (optional) | €15 | Plus |
| **Total tooling** | **€229** | |
| | | |
| Bookmaker deposits (test) | €1,500 (one-time) | KYC + test betów |
| **Total P0** | **€229 + €1,500 one-time** | |

### Phase 1 — Code Cleanup

Same as P0, plus:
| Kategoria | Koszt | Notes |
|---|---|---|
| Hetzner staging VPS (CX32) | €20 | Pierwszy VPS dla CI/testów |
| B2 backup bucket (small) | €1 | 100GB |
| **Dodatkowo P1** | **€21** | |
| **Total P1** | **€250** | |

### Phase 2 — New Features

Same as P1, plus:
| Kategoria | Koszt | Notes |
|---|---|---|
| RunPod GPU (TabPFN, okazjonalnie) | €30-50 | On-demand, ~10-20h/m-c |
| Pinnacle data partner (opcjonalnie) | €100-300 | Jeśli nie scraping |
| **Dodatkowo P2** | **€130-350** | |
| **Total P2** | **€380-600** | |

### Phase 3 — More Leagues

Same as P2, plus:
| Kategoria | Koszt | Notes |
|---|---|---|
| Proxy residential (dla scraping) | €50-100 | Rotating proxies |
| 2captcha (jeśli potrzebne) | €10-30 | Captcha solving |
| B2 backup (większy) | €5 | 500GB |
| Linear Plus (gdy > 10 issues/dzień) | €50 | Optional upgrade |
| **Dodatkowo P3** | **€115-185** | |
| **Total P3** | **€495-785** | |

### Phase 4 — More Sports

Same as P3, plus:
| Kategoria | Koszt | Notes |
|---|---|---|
| NBA Stats API (rate limited, free) | €0 | |
| NHL API (free) | €0 | |
| Jeff Sackmann data (free GitHub) | €0 | |
| Dodatkowe proxy dla nowych sports | €30 | |
| Większy VPS (CX42 zamiast CX32) | +€15 | Production scaling |
| **Dodatkowo P4** | **€45** | |
| **Total P4** | **€540-830** | |

### Phase 5 — Automation

Same as P4, plus:
| Kategoria | Koszt | Notes |
|---|---|---|
| Hetzner production VPS (CX42) | €35 | Dedicated production |
| Prefect Cloud (opcjonalnie) | €0-50 | Free tier wystarcza początkowo |
| Better Stack Pro | €22 | Monitoring |
| Supabase Pro (jeśli managed PG) | €25 | Alternatywa self-hosted |
| Resend | €20 | Email (50k/m-c) |
| RunPod GPU (więcej użycia) | €50-100 | Daily inference |
| B2 backup (duży) | €10 | 1TB+ |
| DNS + CDN Cloudflare Pro (opcjonalnie) | €20 | |
| **Dodatkowo P5** | **€182-262** | |
| **Total P5** | **€722-1,092** | |

### Phase 6 — Product & App

Same as P5, plus:
| Kategoria | Koszt | Notes |
|---|---|---|
| Clerk (10k MAU free → Pro gdy > 10k) | €0-25 | Free tier dla startu |
| Stripe (fees, nie subscription) | ~1.4% rev | Variable |
| Vercel Pro | €20 | Next.js hosting |
| PostHog (self-hosted lub cloud) | €0-50 | Product analytics |
| Termly / Iubenda (ToS/PP) | €10-20 | Legal templates |
| Intercom / Crisp (customer support) | €0-30 | Crisp free tier |
| **Dodatkowo P6** | **€30-145** | |
| **Total P6** | **€752-1,237** | |

## Bankroll tradingowy (oddzielnie od infra)

**Uwaga:** Bankroll do stawiania zakładów to **nie jest koszt infra**. To kapitał operacyjny oddzielnie księgowany.

| Faza | Początkowy bankroll |
|---|---|
| P0 | €1,500 (test KYC) |
| P2 | €5,000 (confirmed edge) |
| P4 | €10,000 |
| P5 | €20,000 (pełna automatyzacja) |
| P6 | €30,000+ (jako produkt demo) |

**Źródło:** początkowe inwestycje Leada, potem reinwestycja zysków.

## Koszt pracowniczy (NIE jest w tej tabeli)

Najwyższy koszt biznesu to **ludzie**, nie infra. Orientacyjne koszty miesięczne (EUR brutto, PL market):

| Rola | Juniorzy / Mid | Senior (20 lat doświad.) |
|---|---|---|
| Lead / Founder | (equity) | (equity) |
| Dr matematyki | €5-8k | €10-15k |
| Senior ML Engineer | €6-10k | €12-18k |
| Senior Data Engineer | €6-10k | €12-18k |
| Senior Software Engineer | €6-10k | €12-18k |
| Senior Designer | €4-8k | €8-12k |
| **Team monthly** | **~€30-50k** | **~€55-80k** |

**Implikacja:** Infra (€500-1,200/m-c) to **<2%** kosztów. Nie optymalizujemy infra, optymalizujemy produktywność ludzi.

## Przychody — target po fazach

| Faza | MRR target | ARR target |
|---|---|---|
| P0 | €0 | €0 |
| P1 | €0 | €0 |
| P2 | €0 | €0 |
| P3 | €0 | €0 |
| P4 | €500 (first pilot customer) | €6k |
| P5 | €2,000 (few early adopters) | €24k |
| P6 | €10,000 (product launch) | €120k |
| P6 + 6 miesięcy | €30,000 | €360k |
| P6 + 12 miesięcy | €55,000 | €660k |

**Break-even z infra:** P4 (€500 MRR > €500-800 infra)
**Break-even z zespołem:** P6 + 12 miesięcy (€55k MRR > €55-80k team cost)
**Profitability:** P6 + 18-24 miesięcy

## Budget alerts

Reguły w monitoring (Better Stack / Grafana):
- Hetzner bill > €100/m-c → warning
- B2 bill > €30/m-c → warning
- RunPod bill > €200/m-c → warning (unusual GPU usage)
- Stripe revenue < 50% target → warning (pipeline issue)
- Total infra > €1,500/m-c → critical, review meeting

## Investment vs bootstrap

**Decyzja użytkownika:** Bootstrap (obecna assumption)

Jeśli bootstrap:
- P0-P1: Lead funds personal money
- P2-P4: Continued funding + first revenue
- P5-P6: Self-sustaining gdy MRR > koszty
- Benefit: pełna kontrola, brak dilution
- Risk: slower growth, cash flow tight

Jeśli investment (opcja):
- Seed round €300k-500k po P2-P3 (pokazaliśmy IP + data)
- Series A €1-3M po P6 (traction + metrics)
- Benefit: faster scaling
- Risk: dilution, investor pressure

**Recommendation:** Bootstrap do P6 launch, rozważ seed gdy mamy 3-5 płacących klientów i chcemy przyspieszyć growth.

## Cost optimization opportunities

### P5+
- **Self-host monitoring** zamiast Better Stack (€22 → €0, koszt: maintenance)
- **Self-host Postgres** zamiast Supabase (koszt: backup + monitoring effort)
- **Cloudflare R2** zamiast B2 (tańsze dla transfer)
- **Hetzner dedicated** zamiast cloud (gdy >3 serwery, dedicated jest tańsze)

### P6+
- **Reserved instances** na cloud (gdy stabilni)
- **Cold storage** dla archive (90% data rzadko accessed)
- **Query optimization** (indeksy, caching) redukuje compute

## Monthly cost review (Lead)

Co miesiąc:
1. Aktualne koszty per kategoria
2. Variance vs budget
3. Top 3 cost drivers
4. 3 action items dla redukcji (jeśli powyżej budget)
5. Revenue update
6. Runway calculation (ile miesięcy bieżącego stanu)

## Obecny staging P0 → co kosztuje

Przy starcie obecnego planu (przed zatrudnianiem zespołu):

**Miesięcznie (tooling only):** ~€230
**One-time (setup):** ~€1,500 (bookmaker deposits)
**Bankroll tradingowy (oddzielnie):** €1,500-5,000 zależnie od apetytu

**Roczny budget P0-P1 (tooling bez zespołu):** €230 × 12 = **€2,760**

Z zespołem senior 6 osób przez rok (konserwatywnie €55k × 12) = **€660k/rok**.

**Wniosek:** Bootstrap wymaga agresywnej sales w P6, lub pivotu do mniejszego zespołu (np. 3 osoby zamiast 6 na start, reszta w P4+).
