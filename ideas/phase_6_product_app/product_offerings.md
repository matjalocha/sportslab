# Product Offerings — 9 SKU

**Cel dokumentu:** Szczegółowa specyfikacja każdego produktu, target customer, value proposition, pricing, implementation effort, priorytet.

**Update cadence:** Aktualizowane po P6.0.4 (customer discovery summary) i po każdym pricing experyment.

---

## SKU 1 — Value Feed API

**Priorytet:** **MVP (launch w P6.1)**

### Target customer
- Mniejsi tipsterzy (followers 500-50k na Telegramie/Twitterze)
- Serwisy bukmacherskie (blogi, review sites)
- Aggregatorzy value betów
- Betting syndykaty B2B

### Value proposition
> "Realtime value bety z 5+ bukmacherów × 3 sportów × 10 lig. Żadnego data scraping, żadnego własnego ML. Po prostu API call i masz value bety."

### Core features
- REST API + WebSocket (opcjonalnie dla realtime push)
- Filters: sport, liga, market, min edge, min P, date range
- Per-bet details: P(nasz), P(rynek), edge, Kelly stake suggestion, odds per bookmaker
- Webhook push dla nowych value bets
- Historical value bets (do backtestingu klienta)

### Pricing
| Plan | Calls/m-c | Price | Target |
|---|---|---|---|
| **Basic** | 1000 | €99/m-c | Solo tipster |
| **Pro** | 10,000 | €299/m-c | Growing tipster |
| **Enterprise** | Unlimited + priority | €999/m-c | Serwisy, aggregatorzy |

Overage: €0.01 per call above limit.

### Implementation effort
- **Tygodnie:** 2-3 (w P6.1)
- **Dependencies:** P5 (automation), bez której value bets nie są aktualizowane daily

### Monetization math
- Target: 20 Basic + 5 Pro + 1 Enterprise = 20 × 99 + 5 × 299 + 999 = **€3,474/m-c**
- Breakeven z infra (~€500/m-c): 6 Basic plans

---

## SKU 2 — Data Lake Access

**Priorytet:** **MVP (launch w P6.1)**

### Target customer
- Researcherzy akademiccy / doktoranci sportów
- Fantasy apps (football, tennis, NBA)
- Niezależni tipsterzy budujący własne modele
- Szkoły / akademie potrzebujące danych do projektów

### Value proposition
> "Jedno miejsce, gdzie masz enriched dane z 10 lig × 4 sportów. Raw CSV/Parquet/JSON download + SQL query API. Nie musisz scrapować tygodniami."

### Core features
- REST API dla wszystkich core entities (matches, teams, players, odds, predictions)
- Bulk export endpoint — query → download Parquet/CSV
- SQL-lite query builder w aplikacji (drag-drop UI)
- Read-only Postgres access dla Enterprise (connection string)
- Regular data updates (daily refresh)
- Historical data dostępny dla wszystkich planów

### Pricing
| Plan | Query limit | Storage/m-c download | Price |
|---|---|---|---|
| **Researcher** | 100 queries/dzień | 1 GB | €49/m-c |
| **Professional** | 1000/dzień | 10 GB | €199/m-c |
| **Enterprise** | Unlimited + DB access | 100 GB | €599/m-c |

Overage storage: €0.10/GB.

### Implementation effort
- **Tygodnie:** 2-3 (w P6.1)
- **Dependencies:** Postgres (P5), partitioning dla performance

### Monetization math
- Target: 30 Researcher + 10 Professional + 2 Enterprise = 30 × 49 + 10 × 199 + 2 × 599 = **€4,658/m-c**

---

## SKU 3 — Probabilities API

**Priorytet:** **MVP (launch w P6.1)**

### Target customer
- Fantasy apps (które budują własne scoringi)
- Inne ML teams (którzy chcą meta-features)
- Betting simulators
- Academic researchers comparing models

### Value proposition
> "Prawdopodobieństwa pre-match dla wszystkich meczów, rynków, ligi, sportów. Wypełnij lukę gdzie Twój model nie ma danych."

### Core features
- Probability predictions per match: P(H/D/A), P(O/U lines), P(BTTS), P(exact scores), P(AH lines)
- Historical predictions (dla backtestingu klienta)
- Calibration metrics (ECE) per liga, sezon, rynek
- Model version tracking (wiesz jakiego modelu klient używał)
- Confidence intervals dla każdej predykcji

### Pricing
| Plan | Calls/m-c | Price |
|---|---|---|
| **Starter** | 1000 | €79/m-c |
| **Growth** | 20,000 | €399/m-c |
| **Scale** | 200,000 | €1,499/m-c |

Overage: €0.005 per call.

### Implementation effort
- **Tygodnie:** 1-2 (jeśli Value Feed API istnieje, reużywamy infrastruktury)

### Monetization math
- Target: 10 Starter + 5 Growth + 1 Scale = 10 × 79 + 5 × 399 + 1 × 1499 = **€4,284/m-c**

---

## SKU 4 — Club Analytics Dashboard

**Priorytet:** **V1 (launch w P6.2, core revenue driver)**

### Target customer
- Kluby z Ekstraklasy (PL), I ligi PL, Championship EN lower, Eredivisie lower, 2 Bundesliga, Serie B, Segunda División, Ligue 2
- Akademie piłkarskie
- Małe kluby europejskie spoza top-5 lig
- Agencje scoutingowe pracujące z klubami

### Value proposition
> "Dashboard jakości Statsbomba / Opty za €500-3000/m-c zamiast €50k/rok. Opponent scouting, xG breakdown, player radars, 1-click PDF reports."

### Core features
- **Opponent report** — jednokliknięciem PDF 5-10 stron z:
  - Team form + key stats
  - Formacje + taktyka (z Transfermarkt + FBref)
  - xG profile (attack, defense, pace)
  - Player radar chartów (top 11)
  - Słabości + strengths data-driven
- **Dashboard monitoring**:
  - Moja drużyna vs liga (percentiles)
  - xG flow chart
  - Form tracking + xGvs actual goals
  - Next opponents preview
- **Player tracker**:
  - Per-player rolling form
  - Injury tracking
  - Market value tracking (Transfermarkt)
- **Multi-user teams** — trener + analityk + scout, różne role

### Pricing
| Plan | Features | Price |
|---|---|---|
| **Akademia** | 1 drużyna, 1 liga, read-only | €499/m-c |
| **Club Standard** | 1 drużyna, 3 ligi (ich + 2 scouting), 3 users | €1,499/m-c |
| **Club Pro** | Multi-drużyna (A+B+U19), 10 lig, 10 users, custom reports | €2,999/m-c |
| **Enterprise** | Custom + consulting | €5,000+/m-c |

### Implementation effort
- **Tygodnie:** 8-12 (większość wysiłku P6.2)
- **Dependencies:** Aplikacja Next.js, designer Figma, advanced data z P3

### Monetization math
- Target: 10 Akademia + 5 Club Standard + 2 Club Pro = 10 × 499 + 5 × 1499 + 2 × 2999 = **€18,483/m-c**
- **To jest potencjalnie największy revenue driver** — kluczowy dla fazy 6

---

## SKU 5 — Coach Analytics Multi-Sport

**Priorytet:** **V1 (launch w P6.2)**

### Target customer
- Trenerzy tenisowi ATP/WTA Challenger + ITF + akademie
- Trenerzy koszykarscy EuroLeague B + niższe ligi europejskie + NCAA Division II/III
- Trenerzy hokejowi AHL + ECHL + ligi europejskie
- Indywidualni trenerzy juniorzy

### Value proposition
> "Przygotowanie meczu w 15 minut zamiast 3 godzin oglądania taśm. H2H deep dive, słabości przeciwnika, custom raporty dla każdego meczu."

### Core features
- **H2H analysis** — head-to-head per nawierzchnię (tennis), per arena (basketball/hockey)
- **Opponent weaknesses** — data-driven insights (np. "return game świetny na clay, ale 55% 1st serve na hard")
- **Match prep workflow** — guided setup: wybór rywala → generate report
- **Custom report builder** — trener zapisuje swoje ulubione widoki
- **Video integration** (V2) — link do Wyscout/Instat/YouTube highlights
- **Multi-sport unified UX** — jedna platforma dla różnych dyscyplin

### Pricing
| Plan | Features | Price |
|---|---|---|
| **Solo** | 1 sport, 1 user | €199/m-c |
| **Duo** | 2 sporty, 3 users | €499/m-c |
| **Academy** | All sports, 10 users | €999/m-c |
| **Enterprise** | Custom + consulting | €2,000+/m-c |

### Implementation effort
- **Tygodnie:** 6-8 (reużywa infrastruktury z SKU 4)
- **Dependencies:** P4 done (tennis, basketball, hockey)

### Monetization math
- Target: 15 Solo + 5 Duo + 2 Academy = 15 × 199 + 5 × 499 + 2 × 999 = **€7,478/m-c**

---

## SKU 6 — Custom Research / Consulting

**Priorytet:** **Enabler (ongoing, od P6.3)**

### Target customer
- Duże kluby piłkarskie (recruitment analysis)
- Agencje piłkarskie (player valuation)
- Sponsorzy sportowi (market studies)
- Inwestorzy klubowi (due diligence)

### Value proposition
> "Custom analizy na bazie naszej data lake + ML stack. Wyceny graczy, market studies, scouting reports, recruitment."

### Core services
- **Player valuation reports** — model-based + market context + comparable analysis
- **Recruitment analysis** — liste graczy spełniających kryteria (position, age, value)
- **Opposition analysis** (jedna-off) — dla klubów bez subskrypcji SKU 4
- **Market studies** — trendy w lidze, liga analytics dla sponsorów
- **Custom ML projects** — klient ma specific problem, my budujemy

### Pricing
- **Short report** (1 raport): €2,000-5,000
- **Multi-report engagement** (5 raportów/3 mies.): €15,000
- **Custom ML project**: €10,000-50,000
- **Consulting retainer**: €3,000-10,000/m-c

### Implementation effort
- **Per engagement:** 1-4 tygodnie
- **Dependencies:** Zespół (DrMat + MLEng + Lead)
- **Kapacytet:** Lead zarządza, DrMat + MLEng executes; 2-3 equivalent engagements per kwartał

### Monetization math
- Target: 1 engagement × €10k per kwartał średnio = **€3,333/m-c average**
- Niestabilne, ale wysokie ticket. Dobre dla customer acquisition (gateway do subskrypcji).

---

## SKU 7 — Backtest-as-a-Service

**Priorytet:** **V2 (post-P6 success, w P6.4)**

### Target customer
- Indywidualni bettorzy testujący strategie
- Fundusze sportowe (quant-ish)
- Developerzy aplikacji betting

### Value proposition
> "Wklej swoją strategię, dostaniesz walk-forward raport z naszymi features. Nie buduj własnej data infra."

### Core features
- Upload strategy (Python function lub YAML config)
- Backtest na historical data
- Walk-forward analysis z selectable seasons
- Performance metrics (ROI, yield, sharpe, drawdown, CLV)
- Comparison z baseline strategies (flat, Kelly)
- PDF raport + interactive dashboard

### Pricing
| Plan | Backtests/m-c | Price |
|---|---|---|
| **Pay-per-run** | 1 | €50 |
| **Starter** | 5 | €199/m-c |
| **Pro** | 30 | €699/m-c |
| **Fund** | Unlimited + priority | €2,499/m-c |

### Implementation effort
- **Tygodnie:** 4-6 (w P6.4)
- **Dependencies:** Stable data lake + compute infrastructure

### Monetization math
- Target: 20 pay-per-run + 5 Starter + 2 Pro = 20 × 50 + 5 × 199 + 2 × 699 = **€3,393/m-c**

---

## SKU 8 — White-Label Platform

**Priorytet:** **V2 (post-P6 success, w P6.4)**

### Target customer
- Istniejący tipster serwisy chcący lepszą platformę
- Bukmacherzy oferujący data usługi swoim VIP
- Partnerzy B2B chcący rebranded version

### Value proposition
> "Twoja marka, nasza technologia. Kompletna platforma tipster pod Twoim branding'iem za procent przychodów."

### Core features
- Complete platform z ich logo, kolorami, domeną
- API dostęp do data lake
- Custom model training (ich dane + nasze)
- Revenue share 20-30%

### Pricing
- **Setup fee:** €5,000-20,000 one-time
- **Revenue share:** 20-30% z ich przychodów
- **Minimum monthly:** €1,000

### Implementation effort
- **Per partner:** 4-8 tygodnie (multi-tenancy, branding)
- **Dependencies:** Dojrzała platforma, ≥5 własnych klientów pokazuje że działa

### Monetization math
- Target: 2 partners z €3k/m-c rev share = **€6,000/m-c**

---

## SKU 9 — Telegram/Discord Pro Bot (B2C)

**Priorytet:** **Sekundarny (V2+, P6.4 lub później)**

### Target customer
- End-user bettorzy (Polska + inne rynki)
- Followersi tipsterów chcący surowe value bety

### Value proposition
> "Automatyczne alerty value betów wprost na Telegramie. Zero scraping, zero czekania."

### Core features
- Telegram bot z subskrypcją Stripe
- Push value bets z filters (sport, liga, min edge, min odds)
- Daily summary
- Portfolio tracking (user może oznaczać które bety gra, ROI tracking)

### Pricing
| Plan | Features | Price |
|---|---|---|
| **Free trial** | 1 tydzień, 3 bety/dzień | Free |
| **Basic** | 10 bety/dzień | €20/m-c |
| **Pro** | Unlimited + filters | €49/m-c |
| **VIP** | Pro + private channel + priority | €99/m-c |

### Implementation effort
- **Tygodnie:** 2-3 (w P6.4)
- **Dependencies:** Value feed API (SKU 1), Stripe, Telegram bot SDK

### Regulacje
- **B2C = większe regulacje** — wymaga analizy prawnej per kraj przed launch
- Może wymagać licencji hazardowej w niektórych krajach
- Pomijamy w MVP z tego powodu

### Monetization math
- Target: 50 Basic + 30 Pro + 10 VIP = 50 × 20 + 30 × 49 + 10 × 99 = **€3,460/m-c**
- Wymaga marketingu B2C (bardziej złożone niż B2B sales)

---

## Łączny potencjał przychodowy (po 12 miesiącach)

Konserwatywny target:

| SKU | MRR target |
|---|---|
| Value Feed API | €3,500 |
| Data Lake Access | €4,700 |
| Probabilities API | €4,300 |
| Club Dashboard | €18,500 |
| Coach Multi-Sport | €7,500 |
| Custom Research | €3,300 |
| Backtest-as-a-service | €3,400 |
| White-label | €6,000 |
| Telegram Pro | €3,500 |
| **TOTAL MRR** | **€54,700** |

**Roczny:** ~€656,000 ARR target po 12 miesiącach od P6 launch.

**Break-even infra:** ~€2,000-3,000/m-c (P6 z 10+ klientami). Kosz pracowniczy: największy. Firma self-sustaining po MRR > €30k.

## Priorytet implementacji (rekomendacja)

1. **P6.0 (3-4 tyg.)** — Customer discovery, pricing experiments, legal
2. **P6.1 (4-6 tyg.)** — MVP API: SKU 1 + 2 + 3 (pure API, fast to build)
3. **P6.2 (6-10 tyg.)** — V1 Dashboards: SKU 4 (Club) first, then SKU 5 (Coach)
4. **P6.3 (ongoing)** — Sales, pierwsze 5 klientów, iteracja
5. **P6.4 (4-8 tyg., po pierwszych klientach)** — SKU 6 (Custom), SKU 7 (Backtest), SKU 8 (White-label), SKU 9 (Telegram) — według popytu

## Decyzje do potwierdzenia

1. Czy SKU 9 (Telegram B2C) jest w ogóle w scope, given regulation concerns?
2. Czy oferujemy discount rocznym kontraktem (np. -20% przy annual billing)?
3. Czy ma być free trial dla wszystkich SKU czy tylko dla B2C?
4. Czy oferujemy multi-SKU bundle pricing (np. Value Feed + Data Lake = -15%)?
5. Pricing EUR czy USD czy lokalnie per kraj?
