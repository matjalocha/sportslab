# Phase Transitions — Kryteria przejścia między fazami

**Zasada:** Faza kończy się gdy **wszystkie kryteria DoD są spełnione**, nie gdy minie kalendarz. Widełki czasowe są orientacyjne — nie deadline'y.

**Gate review** — przed przejściem do kolejnej fazy: 60-minutowy meeting zespołu + decyzja Lead'a. Jeśli któryś warunek nie jest spełniony — blok przejścia, tworzenie dodatkowych zadań w obecnej fazie.

---

## P0 → P1 — Foundations → Code Cleanup

**Widełki:** 2-4 tygodnie

**Kryteria wejścia do P0:**
- Prompt zatwierdzony przez użytkownika
- `ideas/` folder istnieje i zawiera wszystkie pliki planu

**Kryteria wyjścia z P0 (= wejścia do P1):**
- [ ] Zespół 6 osób ukonstytuowany (umowy/kontrakty, dostępy)
- [ ] Forma prawna firmy ustalona (JDG lub sp. z o.o.)
- [ ] Konto bankowe firmowe + bankroll operacyjny wydzielony
- [ ] Linear workspace utworzony, projekty P0-P6 założone, issue templates gotowe
- [ ] GitHub organization utworzona, monorepo zainicjalizowane, branch protection na main
- [ ] 1Password/Bitwarden/Doppler secrets vault dla zespołu
- [ ] Konta testowe u STS (✅ już mamy), **LVBet, Superbet, Fortuna, Betclic** założone, KYC przeszedł
- [ ] Pierwszy review istniejącego kodu z MLEng + DataEng + SWE — raport "debt audit"
- [ ] Budżet 3-6 miesięcy operacyjny zapewniony (decyzja Lead)
- [ ] Weekly rhythm ustalony (poniedziałek planning, środa demo, piątek retro)

**Blokery (nie wolno przejść dalej jeśli):**
- Brak zespołu (nawet jedna kluczowa osoba = blok)
- Brak dostępu do co najmniej 3 bukmacherów
- Brak formalności prawno-finansowych

---

## P1 → P2 — Code Cleanup → New Features

**Widełki:** 4-8 tygodni

**Kryteria wyjścia z P1:**
- [ ] GitHub Actions: **zielone CI** na każdym PR (lint + test + typecheck + build)
- [ ] **Pokrycie testami ≥ 80%** na `src/ml_in_sports/` (mierzone pytest-cov)
- [ ] **ruff check** przechodzi bez warnings (strict config)
- [ ] **mypy strict** przechodzi na `src/ml_in_sports/` (test mogą być luźniejsze)
- [ ] Monorepo zrestrukturyzowane (patrz `phase_1_code_cleanup/target_repo_layout.md`)
- [ ] `scripts/` zkonsolidowane do CLI entry points w `src/ml_in_sports/cli/`
- [ ] `notebooks/` przeniesione do `research/` — **zero notebooków w produkcji**
- [ ] SQLite schema w Alembic migrations (reversible)
- [ ] Logging strukturalny (structlog) wszędzie — **zero `print()` w production code**
- [ ] Pydantic-settings do configu (zero hardcoded paths)
- [ ] `scripts/_archive/` zarchiwizowane do osobnej gałęzi `archive/pre-cleanup`
- [ ] Dokumentacja developera (`CONTRIBUTING.md`) zaktualizowana
- [ ] **Smoke test**: nowy dev klonuje repo, uruchamia `uv sync && pytest` i wszystko działa

**Blokery:**
- Testy flakey na CI (>1% failure rate)
- mypy errors > 0 na `src/`

---

## P2 → P3 — New Features → More Leagues

**Widełki:** 6-10 tygodni

**Kryteria wyjścia z P2:**
- [ ] Kalibracja: **ECE < 2%** per liga per sezon na hold-out
- [ ] Portfolio Kelly z ograniczeniami zaimplementowany + udokumentowany
- [ ] CLV tracking live vs Pinnacle closing — **mean CLV > 0** na ostatnie 100+ betów
- [ ] Goals/Poisson model działa (AH, Correct Score, O/U 0.5-5.5)
- [ ] Dixon-Coles lub Bayesian wariant dostępny
- [ ] Drift detection uruchomiony (feature + label + odds drift)
- [ ] IP udokumentowane — **whitepaper "Hybrid Calibrated Portfolio Kelly" draft 1 gotowy**
- [ ] Benchmark: nowa architektura bije obecny NB14 ensemble o **≥ 0.002 LogLoss** (statystycznie istotne)
- [ ] Wszystkie feature'y objęte testami

**Blokery:**
- ECE > 5% na którejkolwiek lidze
- Negative mean CLV na walk-forward

---

## P3 → P4 — More Leagues → More Sports

**Widełki:** 6-10 tygodni

**Kryteria wyjścia z P3:**
- [ ] **Top-10 lig piłki nożnej** w production DB (baseline 5 + 5 nowych)
- [ ] Feature parity dla każdej nowej ligi (wszystkie features obecne)
- [ ] Backtest per liga — **walk-forward ROI > 5%** w ostatnich 2 sezonach
- [ ] Team name normalization dla nowych lig (aliases, edge cases)
- [ ] Scrapery dla nowych lig uruchomione i monitorowane
- [ ] Koszt infra per liga oszacowany — decision log: które ligi kontynuujemy, które porzucamy
- [ ] Dokumentacja per liga (`docs/leagues/*.md`)

**Blokery:**
- ROI < 3% na żadnej nowej lidze
- Braki danych (< 90% coverage) na żadnej nowej lidze

---

## P4 → P5 — More Sports → Automation

**Widełki:** 20-32 tygodnie (3 pod-fazy P4.1, P4.2, P4.3)

**Uwaga:** P4 może iść równolegle z P5 (P4.1 najpierw, potem P5 startuje, potem P4.2 i P4.3 równolegle z P5).

**Kryteria wyjścia z P4 (wszystkie 3 pod-fazy):**
- [ ] **Tenis** w produkcji, ROI walk-forward ≥ 5%, 2+ bukmacherów z odds
- [ ] **Koszykówka** (NBA) w produkcji, ROI walk-forward ≥ 5%
- [ ] **Hokej** (NHL) w produkcji, ROI walk-forward ≥ 5%
- [ ] Abstract sport framework (`src/ml_in_sports/sports/`) gotowy i udokumentowany
- [ ] Testy kontraktowe — każdy nowy sport przechodzi te same integration testy
- [ ] Per-sport feature documentation (`docs/sports/*.md`)
- [ ] Postgres schema obsługuje multi-sport (sport-agnostic base + sport-specific extensions)

**Blokery P4.1 (tenis):**
- Model nie bije ATP/WTA ELO baseline

**Blokery P4.2 (koszykówka):**
- NBA Stats API rate limity uniemożliwiają daily pipeline

**Blokery P4.3 (hokej):**
- NHL API deprecated lub niedostępne

---

## P5 → P6 — Automation → Product & App

**Widełki:** 6-10 tygodni

**Kryteria wyjścia z P5:**
- [ ] Orkiestracja (Prefect/Dagster) działa — **30 dni bez manual intervention**
- [ ] Daily schedule: scraping → features → model → bets → report, w pełni automatyczny
- [ ] Monitoring: Grafana + Loki (lub Better Stack) z alertami Telegram/Slack
- [ ] Health checks na każdym etapie (scrape success rate, feature coverage, model ECE, bet count)
- [ ] Rollback mechanism (poprzedni model dostępny, DB backup z ostatnich 7 dni)
- [ ] Secrets management w Doppler / 1Password Connect
- [ ] VPS production stabilny (Hetzner CX32 lub równoważnik)
- [ ] GPU bursts (RunPod/Lambda) uruchamiają się tylko gdy potrzebne (koszt < €100/m-c)
- [ ] Cost per bet oszacowany (infra / betów generowanych)
- [ ] DR (Disaster Recovery) plan — odtworzenie systemu z backupów < 4h

**Blokery:**
- Pipeline łamie się częściej niż 1× tydzień
- Brak alertów gdy coś nie działa

---

## P6 → P6+ (skalowanie) — Product & App → Growth

**Widełki:** 16-24 tygodnie do pierwszego płacącego klienta

**Kryteria wyjścia z P6:**
- [ ] Aplikacja SaaS uruchomiona (Next.js + FastAPI + Postgres + Stripe + Clerk)
- [ ] Co najmniej **3 z 9 SKU** dostępne do sprzedaży:
  - [ ] Value feed API (podstawowy SKU)
  - [ ] Data Lake access (podstawowy SKU)
  - [ ] Club analytics dashboard LUB Coach analytics multi-sport
- [ ] **≥ 1 płacący klient B2B** z invoice > €200 (realny cash flow)
- [ ] **MRR > koszty infra** (break-even na infrastrukturze)
- [ ] Landing page live z signup flow + pricing
- [ ] Customer onboarding flow automatyczny (self-serve + manual)
- [ ] Usage analytics działa (track ile calls, ile GB, który klient)
- [ ] Legal: ToS, Privacy Policy, GDPR compliance sprawdzone przez prawnika
- [ ] Dokumentacja API publiczna (docs.sportslab.xyz lub podobne)
- [ ] Pierwszy case study napisany i opublikowany

**Blokery P6:**
- Brak płacącego klienta po 24 tygodniach → retrospektywa, reorientacja (pivot produktu?)

---

## Gate review template

Przed każdym przejściem z fazy N do fazy N+1 (60 min meeting):

```markdown
# Gate Review: P{N} → P{N+1}
Data: {DATA}
Uczestnicy: wszyscy z zespołu

## Status DoD (checklista)
- [X] Kryterium 1
- [X] Kryterium 2
- [ ] Kryterium 3 — BLOKER

## Blokery
- {lista problemów}

## Decyzja
- [ ] ✅ Przechodzimy do P{N+1}
- [ ] ⏳ Zostajemy w P{N}, sprinty dodatkowe na blokery
- [ ] 🔄 Redesign fazy — wracamy do planning

## Akcje po meetingu
- {lista}

## Następny gate review
{DATA}
```
