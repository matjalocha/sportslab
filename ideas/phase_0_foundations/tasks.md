# Phase 0 — Tasks

## Legend

- **Owner** — główny odpowiedzialny
- **Collab** — osoby wspierające
- **DoD** — Definition of Done (mierzalne)
- **Gap** — czy potrzebujemy kogoś spoza zespołu

## Task table

| # | Task | Owner | Collab | Depends on | DoD | Gap |
|---|------|-------|--------|------------|-----|-----|
| P0.1 | Decyzja o formie prawnej (JDG vs sp. z o.o. vs inne) | Lead | DrMat, SWE | — | Decyzja spisana w `infrastructure/secrets_and_compliance.md` | **Prawnik** (1h consulting) |
| P0.2 | Rejestracja firmy + NIP + REGON | Lead | — | P0.1 | Firma w KRS/CEIDG, KRS number | Księgowy |
| P0.3 | Otwarcie konta bankowego firmowego | Lead | — | P0.2 | IBAN dostępny, multi-access dla zespołu | — |
| P0.4 | Założenie konta u LVBet (firma + osobiste) | Lead | — | P0.3 | KYC przeszedł, dostęp do oferty, odnotowane limity | — |
| P0.5 | Założenie konta u Superbet | Lead | — | P0.3 | KYC przeszedł | — |
| P0.6 | Założenie konta u Fortuna | Lead | — | P0.3 | KYC przeszedł | — |
| P0.7 | Założenie konta u Betclic | Lead | — | P0.3 | KYC przeszedł | — |
| P0.8 | Zdokumentowanie istniejącego konta STS + Pinnacle (jeśli masz) | Lead | DataEng | — | Dane zalogowania w 1Password, limity spisane | — |
| P0.9 | Założenie konta Pinnacle (lub alternatywy — Pinnacle nie jest w PL, więc Betfair Exchange/Matchbook) | Lead | — | — | Konto aktywne, dostęp do closing odds | — |
| P0.10 | Umowy z zespołem (kontrakty, NDA, IP assignment) | Lead | — | P0.2 | 5 kontraktów podpisanych (DrMat, MLEng, DataEng, SWE, Designer) | **Prawnik** (template + review) |
| P0.11 | Linear workspace setup | Lead | — | — | Workspace "SportsLab", 7 projektów (P0-P6), members invited | — |
| P0.12 | Linear issue templates (Task, Bug, Research, Spike) | Lead | — | P0.11 | 4 templates działają, widoczne dla zespołu | — |
| P0.13 | GitHub organization + monorepo init | SWE | Lead | — | Organization "sportslab-io", repo `sportslab` jako monorepo, branch protection on main | — |
| P0.14 | GitHub CODEOWNERS + teams | SWE | Lead | P0.13 | CODEOWNERS per katalog, 3 teams (engineering, research, design) | — |
| P0.15 | 1Password Teams / Bitwarden Business vault | Lead | SWE | — | Wszyscy członkowie mają dostęp, vaults podzielone (credentials, keys, personal) | — |
| P0.16 | Kanał komunikacji (Slack lub Discord) | Lead | Designer | — | Workspace utworzony, kanały (#general, #engineering, #design, #data, #sales, #random), wszyscy invited | — |
| P0.17 | Core hours + time zone agreement | Lead | wszyscy | P0.16 | Spisane w `coordination/weekly_rhythm.md`, zaakceptowane przez zespół | — |
| P0.18 | Pierwszy weekly rhythm cycle (planning → demo → retro) | Lead | wszyscy | P0.17 | Odbył się pełen cykl, notatki w Linear | — |
| P0.19 | Audyt długu technicznego obecnego repo | MLEng | DataEng, SWE | — | Raport w `docs/tech_debt_audit.md`, lista problemów z priorytetami | — |
| P0.20 | Audyt matematyczny obecnych modeli (NB01-NB30) | DrMat | MLEng | — | Raport w `docs/math_audit.md` — jakość kalibracji, SHAP stability, CLV, co działa/nie działa | — |
| P0.21 | Research: design inspirations + konkurencja wizualna | Designer | Lead | — | Moodboard Figma + analiza 10 konkurentów (Stats Perform, Opta, Statsbomb, ClubElo, FBref...) | — |
| P0.22 | Budżet startowy + bankroll operacyjny | Lead | — | P0.3 | Spreadsheet w Notion/Google Sheets, minimum 3 miesiące runway, bankroll tradingowy wydzielony | — |
| P0.23 | Setup Doppler lub 1Password Connect (secrets w pipeline) | SWE | DataEng | P0.15 | Secrets sync działa, CI może pobierać (mock credentials) | — |
| P0.24 | Domain + email setup (sportslab.xyz lub podobne) | Lead | SWE | — | Domena kupiona, email działa (Google Workspace), DNS w Cloudflare | — |
| P0.25 | Pricing research (konkurenci B2B) | Lead | Designer | P0.21 | Raport w `ideas/phase_6_product_app/product_offerings.md` — pricing per konkurent | — |

## Milestones

- **Milestone 1** (koniec tyg. 1): P0.1, P0.2, P0.11, P0.13, P0.15, P0.16 — "Mamy firmę i narzędzia"
- **Milestone 2** (koniec tyg. 2): P0.3-P0.9 — "Mamy konta bukmacherskie"
- **Milestone 3** (koniec tyg. 3): P0.10, P0.19, P0.20, P0.21 — "Mamy umowy i audyty"
- **Milestone 4** (koniec tyg. 4): P0.18, wszystkie pozostałe — "Rytm pracy działa, P1 może startować"

## Braki kompetencyjne identyfikowane w P0

1. **Prawnik** — potrzebny przy P0.1 (forma prawna), P0.10 (umowy), P6 (regulacje). **Kontrakt na retainer 2-4h/m-c** lub freelance per sprawa.
2. **Księgowy** — potrzebny od P0.2. **Biuro rachunkowe**, standardowy kontrakt miesięczny.
3. **Opcjonalnie: Designer konsultant brandingowy** — jeśli senior Designer nie czuje się w brand identity (logo, typografia, nazwa). **Freelance, jednorazowo.**

## Kluczowe decyzje do podjęcia w P0 (przez Lead)

1. **Forma prawna**: sp. z o.o. rekomendowana (IP protection, limit odpowiedzialności, łatwiej dla inwestorów) vs JDG (szybsza, tańsza, ale osobista odpowiedzialność)
2. **Monorepo vs polyrepo**: rekomendacja monorepo (patrz `repo_strategy.md`)
3. **Linear paid plan czy free**: free dla < 10 osób, paid dla zaawansowanych automatyzacji
4. **Discord vs Slack**: Slack dla profesjonalności B2B (rekomendacja), Discord tańszy i podobny UX
5. **Nazwa firmy / brand**: decyzja przed P0.24 (domena)
6. **Core hours time zone**: wszyscy w CET? czy asynchronicznie?
