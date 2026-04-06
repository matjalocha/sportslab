# UI/UX Blueprint

**Owner:** Designer (primary), SWE (implementation), Lead (approval)
**Status:** Do finalizacji w P6.0 po customer discovery, iteracja w P6.1-P6.2.

## Design principles

1. **Dane-first, nie design-first** — każdy widok musi pokazywać realną wartość; żadnego "pretty dashboards" bez substance
2. **Progresywne ujawnianie** — podstawowe metryki widoczne od razu, szczegóły na żądanie
3. **Exportable** — każdy widok ma 1-click PDF/Excel/image export
4. **Mobile-considered, desktop-first** — klienci (kluby, trenerzy) pracują na desktopach
5. **Dark mode first** — developerzy i power users preferują dark; landing może być light
6. **Accessible** — WCAG 2.1 AA minimum
7. **Brand consistency** — jeden look dla landing + app + dashboards + raportów PDF

## Information architecture

```
sportslab.xyz/ (landing)
├── /                               # Hero + value prop
├── /pricing                        # 9 SKU breakdown
├── /docs                           # Redirect do docs.sportslab.xyz
├── /blog                           # Case studies, tutoriale
├── /about                          # Team, mission
└── /signup
    ├── /onboarding                 # Post-signup wizard
    └── /login

app.sportslab.xyz/ (application)
├── /                               # Dashboard home (role-aware)
├── /data                           # Data Lake query (SKU 2)
│   ├── /matches
│   ├── /teams
│   ├── /players
│   ├── /odds
│   └── /query                      # SQL-lite builder
├── /predictions                    # Probabilities API browser (SKU 3)
│   ├── /upcoming
│   ├── /historical
│   └── /calibration
├── /value-bets                     # Value feed (SKU 1)
│   ├── /live
│   ├── /history
│   └── /portfolio
├── /club                           # Club analytics (SKU 4)
│   ├── /my-team
│   ├── /opponents
│   ├── /reports
│   └── /players
├── /coach                          # Coach analytics (SKU 5)
│   ├── /h2h
│   ├── /weaknesses
│   ├── /match-prep
│   └── /reports
├── /backtest                       # Backtest-as-a-service (SKU 7, V2)
├── /api                            # Token management
│   ├── /tokens
│   ├── /usage
│   └── /webhooks
├── /billing                        # Stripe + plan management
└── /settings                       # User profile, team members, preferences

docs.sportslab.xyz/ (documentation)
├── /                               # API overview
├── /api/                           # Endpoints reference
├── /guides/                        # Tutorials per use case
├── /sports/                        # Per-sport guides
└── /changelog                      # API version history
```

## User personas & flows

### Persona 1: "Tipster Tim" — Value Feed API user
- **Who:** Małą/średnią działalność tipster z 10k followersami
- **Goal:** Dostać daily value bety bez własnego ML
- **Flow:**
  1. Signup → kreator API tokenu → pierwszy call (tutorial)
  2. Ustawia webhook lub Telegram bot integration
  3. Codziennie dostaje push value betów
  4. Eksportuje do swojej aplikacji / publikuje

### Persona 2: "Researcher Rachel" — Data Lake user
- **Who:** Doktorantka analizująca wpływ xG na wyniki
- **Goal:** Pobrać dane do analizy w Jupyter
- **Flow:**
  1. Signup → Researcher plan
  2. SQL query builder → filtruje ligi, sezony
  3. Exportuje Parquet
  4. Używa w notebooks
  5. Cytuje SportsLab w pracy

### Persona 3: "Club Carlo" — Club Dashboard user
- **Who:** Analityk w klubie II ligi włoskiej (Serie B)
- **Goal:** Przygotować raport o rywalu przed meczem
- **Flow:**
  1. Login → Club dashboard home
  2. Wybiera "Prepare for next match"
  3. Wybiera rywala → dashboard się ładuje
  4. Przegląda radar, xG flow, player profile
  5. Klika "Generate PDF Report" → pobiera 8-stronicowy PDF
  6. Wysyła trenerowi

### Persona 4: "Coach Kate" — Coach Analytics user
- **Who:** Trenerka tenisa w ITF juniors
- **Goal:** Przygotować swoją zawodniczkę do meczu
- **Flow:**
  1. Login → Coach dashboard
  2. Wybiera sport (tennis) → wybiera rywalkę
  3. Przegląda H2H (jeśli istnieje) lub "Similar player profile"
  4. Widzi słabości (np. backhand return na clay)
  5. Zapisuje notatki → eksportuje PDF "Match prep"

### Persona 5: "Quant Quentin" — Backtest-as-a-service user (V2)
- **Who:** Solo bettor testujący strategie
- **Goal:** Porównać swoje strategie na historical data
- **Flow:**
  1. Login → Backtest section
  2. Upload strategy (Python file lub YAML config)
  3. Wybiera parametry (seasons, leagues, sports)
  4. Klika "Run backtest" → job submitted
  5. Za 10-30 min dostaje email z raportem + dashboard link

## Design system

### Colors (preliminary, do finalizacji w P6.0.10)

```
Primary:        #5B67F2  (energetic blue)
Primary Dark:   #3B47D2
Secondary:      #14B8A6  (teal accent)
Accent:         #F59E0B  (amber, for alerts)
Success:        #10B981
Warning:        #F59E0B
Error:          #EF4444

Background:
  - Dark mode primary:   #0A0A0F
  - Dark mode secondary: #111118
  - Dark mode tertiary:  #1A1A24
  - Light mode:          #FFFFFF / #F9FAFB

Text:
  - Dark mode primary:   #E5E7EB
  - Dark mode secondary: #9CA3AF
  - Dark mode tertiary:  #6B7280
```

### Typography

```
Headings:     Inter Tight 700
Body:         Inter 400/500
Monospace:    JetBrains Mono 400 (for code, data)
Display:      Inter Tight 900 (hero landing)

Scale (rem):
  - h1: 3.0
  - h2: 2.25
  - h3: 1.75
  - h4: 1.25
  - body: 1.0
  - small: 0.875
  - micro: 0.75
```

### Spacing scale

```
4px, 8px, 12px, 16px, 24px, 32px, 48px, 64px, 96px, 128px
(Tailwind default)
```

### Components (kluczowe)

1. **DataTable** — z sortowaniem, filtrowaniem, paginacją, exportem
2. **Chart wrapper** — unified style dla line, bar, radar, scatter (Recharts/Visx)
3. **FilterBar** — sport, liga, date range, team, market
4. **StatCard** — key metric + trend + sparkline
5. **MatchCard** — pre-match preview z predictions
6. **BetCard** — value bet ze wszystkimi szczegółami
7. **PlayerRadar** — 6-axis radar dla porównań graczy
8. **xGFlow** — line chart per-minute cumulative xG
9. **PitchMap** — SVG boisko z shot/pass markers (dla club dashboard)
10. **CourtHeatmap** — basketball/tennis heatmap positioning

## Wireframes (do utworzenia w Figma przez Designera)

### Landing page (P6.0.10)
- Hero z value prop + CTA signup
- 3-kolumny: "For Tipsters / For Clubs / For Researchers"
- 9 SKU cards
- Social proof (logos klientów when available)
- Case study preview
- Pricing table
- FAQ
- Footer z linkami, social, contact

### App dashboard home (role-aware)
- Sidebar nav
- Top bar z user menu, notifications, search
- Role-specific widgets:
  - Tipster: recent value bets, CLV, portfolio
  - Club: next opponent preview, my team form, alerts
  - Coach: next match prep, quick H2H lookup
  - Researcher: recent queries, saved exports

### Club dashboard (SKU 4)
- **My Team view:**
  - Current form card
  - xG for/against chart (rolling)
  - Table position + points trajectory
  - Next 5 fixtures
- **Opponent view:**
  - Team profile (formation, key players, form)
  - Radar comparison (my team vs them)
  - xG flow chart
  - Shot map historical
  - Player radar (key opponents)
  - "Generate PDF report" button

### Coach dashboard (SKU 5)
- **Sport selector:** tennis / basketball / hockey
- **Opponent selector:** search player/team
- **H2H panel:** history, surface-specific stats, trends
- **Weaknesses panel:** data-driven insights ("wins 68% when first serve > 62%")
- **Match prep:** custom notes + charts → PDF

### API token management
- Token list with created date, last used, usage
- "Generate new token" modal
- Rotate/revoke actions
- Rate limit visualization
- Usage chart (daily calls over month)

## Key UX decisions

1. **Schema-driven rendering** — dashboardy per sport używają tego samego core, ale różne schematów features. **Benefit:** dodanie nowego sportu w frontendzie = update schema JSON, nie nowy kod.

2. **PDF jako first-class citizen** — kluby i trenerzy będą chcieli wysyłać raporty. PDF generation musi być **beautiful**, nie tylko funkcjonalne. **Implementacja:** server-side rendering (Puppeteer lub react-pdf) z branded templates.

3. **Dark mode default dla app, light dla landing** — landing jest SEO/marketing, app jest "work mode".

4. **Onboarding wizard** — nowy user przechodzi przez 3-5 stepów aby mieć pierwszy working call/widok. Nie zostawiamy pustego dashboardu.

5. **Empty states z CTAs** — zamiast "No data", mówimy "No matches yet. Scrape starts tomorrow. Meanwhile, [browse historical]."

6. **Breadcrumbs + back** — deep navigation w data lake wymaga łatwego powrotu.

7. **Keyboard shortcuts dla power users** — `Cmd+K` do search, `G+D` do Data, etc.

## Mobile strategy

**P6 MVP:** Responsive web only (nie native app).
- Landing page mobile-first (większość traffic'u)
- App mobile viewable (read-only mode)
- PDFs work on mobile (download + view)

**P6+ (V2):** PWA dla app (offline cache, installable).

**P6+ (V3):** Native iOS/Android tylko jeśli B2C SKU 9 (Telegram) zyskuje traction i użytkownicy żądają.

## Accessibility

- WCAG 2.1 AA compliance minimum
- Keyboard navigation everywhere
- Screen reader friendly (semantic HTML, ARIA)
- Color contrast ratio 4.5:1 minimum
- No color-only information (always icon + text)

## Performance budgets

- Landing page: LCP < 1.5s, CLS < 0.1, FID < 100ms
- App dashboard: First interactive < 3s, chart render < 500ms
- PDF generation: < 10s from click to download

## Designer deliverables per faza

### P0
- Moodboard + inspiracje
- Brand identity v1 draft

### P1
- Design system tokens (Figma + JSON export do `packages/ui/`)
- Komponenty shared (Button, Card, Input, Table)

### P2
- Data visualization exploration (chart libraries, examples)
- Dashboard wireframes v1 (low-fidelity)

### P3
- Landing page wireframes + pierwsza wersja

### P4
- Multi-sport dashboard wireframes (per sport)
- Badge system (surface, sport, market)

### P5
- Raporty PDF templates (beautiful output)

### P6.0
- Complete design system v1
- Landing page high-fidelity
- All 9 SKU mockups
- Onboarding flow

### P6.1
- App shell high-fidelity
- MVP API pages (token management, usage, billing)

### P6.2
- Club dashboard high-fidelity + prototypes
- Coach dashboard high-fidelity + prototypes
- Handoff to SWE (Figma Dev Mode)

### P6.3
- Landing iterations based on conversion data
- New case study templates
- Email templates (branded)

### P6.4
- V2 SKUs designs (Backtest, White-label, Telegram)
