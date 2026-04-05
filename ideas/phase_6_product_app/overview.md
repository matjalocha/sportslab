# Phase 6 — Product & App

**Widełki:** 16-24 tygodnie
**Cel:** Zbudować i uruchomić **komercyjny produkt** (aplikację + API) generujący realne przychody z klientów B2B + dodatkowe modele monetyzacji.
**Wejście:** Wymaga P5 (automation) — bez niej produkt jest nie do utrzymania.

## Kontekst (decyzja użytkownika)

Użytkownik zdecydował:

> "b2b api/ value feed, ale nie tylko bety zróbcie research co można sprzedać jeszcze z tego może jakieś analizy dla klubów piłkarskich czy trenerów innych dyscyplin lub dostęp do danych w jednym miejscu i możliwość przeprowadzania analiz"

**Implikacja:** Nie budujemy tylko "tipster service". Budujemy **"Bloomberg dla sportów"** — platformę, na której różne persony (tipsterzy, kluby, trenerzy, analitycy) mają dostęp do danych, modeli i narzędzi.

## Dziewięć SKU — produkty do zaprojektowania

Wszystkie szczegóły w [product_offerings.md](product_offerings.md). Tutaj tylko lista + priorytet.

| # | SKU | Priorytet P6 | Primary target |
|---|-----|---|---|
| 1 | **Value feed API** | **MVP** | Tipsterzy, serwisy |
| 2 | **Data Lake access** | **MVP** | Researcherzy, fantasy apps |
| 3 | **Probabilities API** | **MVP** | ML teams, fantasy apps |
| 4 | **Club analytics dashboard** | **V1 (P6 main)** | Kluby niższych lig, akademie |
| 5 | **Coach analytics multi-sport** | **V1** | Trenerzy tenisowi, koszykarscy |
| 6 | **Custom research / consulting** | Enabler | Duzi klienci, agencje |
| 7 | **Backtest-as-a-service** | V2 (później) | Bettorzy, fundusze |
| 8 | **White-label platform** | V2 | Partnerzy |
| 9 | **Telegram/Discord Pro bot** | Sekundarne | B2C end-users |

**MVP w P6:** SKU 1, 2, 3 (pure API, najszybsze do zbudowania i najłatwiejsze do monetizacji)
**V1 w P6:** SKU 4, 5 (aplikacja z dashboardami, visible value proposition)
**V2:** SKU 7, 8 (dodajemy po pierwszych klientach)

## Aplikacja (web + API)

### Stack (rekomendacja)
- **Frontend**: Next.js 14 + TypeScript + Tailwind + TanStack Query + Recharts/Visx (data viz)
- **Backend**: FastAPI + Pydantic + async SQLAlchemy
- **DB**: Postgres (z P5) + Timescale dla time-series
- **Auth**: Clerk (prosty setup) lub Auth0 (więcej customization)
- **Payments**: Stripe (B2B invoicing + usage-based subscriptions)
- **Hosting**:
  - Frontend: Vercel (Next.js native)
  - Backend: Hetzner (z P5) lub Fly.io dla global
  - Database: Supabase managed Postgres lub self-hosted na Hetzner
- **Email**: Resend (transactional)
- **Analytics**: PostHog (self-hosted, privacy-friendly)

### Core platform features

1. **Dashboard z danymi** — filter by sport, liga, team, period, market
2. **Ad-hoc query builder** — SQL-lite lub drag-drop query UI
3. **API token management** — wygenerowanie, rotacja, rate limits per plan
4. **Usage analytics** — ile calls, ile GB, który endpoint
5. **Report builder** — eksport PDF/Excel z zapisanych widoków
6. **Custom alerting** — webhooks, Telegram, email dla value bets / drift / custom triggers
7. **Billing** — self-serve upgrade, invoices, payment history
8. **Team accounts** — multi-user, role-based access

### Segmented dashboards

- **Club dashboard** — opponent scouting, xG, formacje, radar chartów
- **Coach dashboard** (multi-sport) — H2H, słabości, przygotowanie
- **Tipster dashboard** — value bets, portfolio tracking, CLV
- **Researcher dashboard** — raw data query, export, notebook-friendly

## Research do zrobienia **przed** budowaniem (P6.0)

**Kluczowe:** Nie budujemy w próżni. Najpierw walidacja.

### 1. Customer discovery (P6.0.1-5)
- **10-20 wywiadów** z potencjalnymi klientami:
  - 5 klubów (Ekstraklasa, I liga PL, Championship lower, Eredivisie lower, lower league kluby)
  - 5 tipsterów / serwisów bukmacherskich
  - 3 trenerów tennis/basketball/hockey
  - 2 researchers / fantasy apps
  - 2 agencje sportowe / sponsorzy
- **Pytania kluczowe:**
  - Jakie dane obecnie płacisz? Ile płacisz?
  - Co byś chciał mieć, a nie masz?
  - Jakiej formy dostarczania preferujesz (API, dashboard, raport PDF, Excel)?
  - Jaki cennik byłby akceptowalny?
  - Kiedy byś kupił (jakie trigger'y)?

### 2. Competitive analysis (P6.0.6)
Konkurenci do zbadania:
- **Stats Perform / Opta** — enterprise
- **StatsBomb** — enterprise + research
- **Wyscout** — scouting dla klubów
- **Football Benchmark** — analytics
- **Instat** — video analysis
- **SciSports** — scouting + video
- **FBref / Transfermarkt** — free baseline
- **Betaminic, Oddsportal, Betegy** — tipster platforms

Output: `docs/competitive_analysis.md`

### 3. Regulacje i compliance (P6.0.7)
- GDPR dla danych graczy
- Licencje dla tipów B2C (w UE różne per kraj)
- Podatki cross-border (jeśli sprzedajemy do UK, US, Asia)
- Hazard / tips regulations per kraj
- ToS + Privacy Policy drafting

**Konsultacja z prawnikiem** — obowiązkowe przed uruchomieniem B2C tipów.

### 4. Pricing experiments (P6.0.8)
- Landing pages z 3 różnymi cennikami (A/B test)
- Waitlist z form'em zbierającym willingness-to-pay
- Pre-sales — oferta "early bird" dla pierwszych 10 klientów

## Główne outputy P6

- **Aplikacja SaaS live** pod domeną `app.sportslab.xyz`
- **Public API** pod `api.sportslab.xyz` z dokumentacją
- **Landing page** pod `sportslab.xyz` z pricing, signup, dokumentacją
- **3 MVP SKU live** (Value feed API, Data Lake, Probabilities API)
- **1-2 V1 SKU live** (Club dashboard lub Coach analytics)
- **≥ 1 płacący klient** z invoice > €200
- **MRR > koszty infra** (break-even)
- **Case study** — 1 opublikowany (z klientem, za jego zgodą)
- **Documentation** — `docs.sportslab.xyz` z API reference, tutoriale, guides

## Zadania

Szczegóły → [tasks.md](tasks.md)

## Wspierające dokumenty

- [product_offerings.md](product_offerings.md) — Szczegóły 9 SKU, pricing, target, value prop
- [ui_ux_blueprint.md](ui_ux_blueprint.md) — Wireframes, flows, design system, user journeys

## Ryzyka w P6

| Ryzyko | Prawdopodobieństwo | Impact | Mitigation |
|---|---|---|---|
| Brak płacącego klienta po P6 | Średnie | **Krytyczny** | Intensywny customer discovery w P6.0, pre-sales, waitlist |
| Zbyt długa budowa aplikacji (perfekcja) | Wysokie | Wysoki | MVP first (3 SKU API), V1 dashboard później, YAGNI |
| Regulacje hazardowe blokują B2C | Wysokie | Średni | Fokus B2B (user decision), B2C tipy opcjonalne |
| Klienci chcą custom features (feature creep) | Wysokie | Średni | Ograniczony scope, lista "Pro Services" dla paid custom |
| Cena za niska → unsustainable, za wysoka → brak sprzedaży | Średnie | Wysoki | A/B test, iteracja, pricing calls z pierwszymi klientami |
| Konkurencja obniża ceny (Stats Perform, Opta) | Niskie | Wysoki | Targetujemy dolny segment którego oni nie obsługują |
| GDPR / legal issue z danymi graczy | Średnie | **Krytyczny** | Prawnik wcześnie, compliance-by-design, data minimization |
| Churn klientów po 1 miesiącu | Wysokie | Wysoki | Onboarding success, customer success focus, usage analytics |
| Brak talentu sprzedażowego w zespole | Wysokie | Wysoki | Lead robi sales, dorekrutacja Growth w P6.0 |
| Aplikacja ma bugi na produkcji | Średnie | Średni | Staging environment, smoke tests, feature flags |
