# Phase 1 — Tasks

## Task table

| # | Task | Owner | Collab | Depends on | DoD | Gap |
|---|------|-------|--------|------------|-----|-----|
| P1.1 | Zbackupować obecny stan repo (`archive/pre-cleanup` branch + backup DB do B2) | SWE | DataEng | — | Gałąź + dump SQLite w Backblaze B2 | — |
| P1.2 | Migracja Poetry → uv | SWE | MLEng | P1.1 | `uv sync` działa, `pyproject.toml` zaktualizowany, CI zielone | — |
| P1.3 | Monorepo init — `pnpm-workspace.yaml` + root `pyproject.toml` workspace | SWE | — | P1.2 | Workspace detectable, monorepo struktura gotowa | — |
| P1.4 | Przeniesienie `src/` → `packages/ml-in-sports/src/ml_in_sports/` | MLEng | DataEng, SWE | P1.3 | Stary src/ usunięty, wszystkie importy zaktualizowane, testy przechodzą | — |
| P1.5 | Konsolidacja `scripts/` → `src/ml_in_sports/cli/` (CLI entry points via Typer/Click) | DataEng | MLEng | P1.4 | Każdy skrypt ma entry point `sl-<name>`, np. `sl-run-pipeline`, `sl-scrape-sts` | — |
| P1.6 | Przeniesienie `notebooks/` → `research/` + usunięcie importów notebook→script | DrMat | MLEng | P1.4 | Notebooki w `research/`, żaden skrypt ich nie importuje | — |
| P1.7 | Usunięcie `scripts/_archive/` (kopia w gałęzi `archive/pre-cleanup`) | SWE | — | P1.1 | Katalog usunięty z main | — |
| P1.8 | GitHub Actions: workflow `ci.yml` (lint + test + typecheck + build) | SWE | MLEng | P1.3 | Workflow zielony na PR, wymagany status check | — |
| P1.9 | pre-commit setup (ruff, mypy --strict, eslint, prettier) | SWE | MLEng | P1.3 | `pre-commit run --all-files` przechodzi | — |
| P1.10 | ruff strict config — usunięcie wszystkich warnings | MLEng | DataEng | P1.9 | `ruff check` bez warnings | — |
| P1.11 | mypy strict config per moduł — stopniowe włączanie | MLEng | DataEng | P1.9 | `mypy --strict src/ml_in_sports/` bez errors | — |
| P1.12 | Structlog setup + usunięcie wszystkich `print()` | MLEng | DataEng, SWE | P1.4 | `grep print\(` znajduje 0 hits w `src/`, `scripts/` | — |
| P1.13 | Pydantic-settings layer — centralna konfiguracja z env vars | SWE | DataEng | P1.4 | `src/ml_in_sports/config.py` importowany wszędzie zamiast hardcoded paths | — |
| P1.14 | Alembic migrations — reverse engineer obecnego schema | DataEng | MLEng | P1.4 | `alembic upgrade head` odtwarza obecne schema z zera | — |
| P1.15 | Zwiększenie pokrycia testami do ≥ 80% | MLEng | DataEng, SWE | P1.10, P1.11 | `pytest --cov` pokazuje ≥ 80% na src/ml_in_sports | — |
| P1.16 | Rozbicie testów ostatnich dużych modułów (ex `pipeline.py` → mniejsze klasy + dedykowane testy) | DataEng | MLEng | P1.15 | Żaden moduł nie ma > 300 linii bez podziału | — |
| P1.17 | `CONTRIBUTING.md` + developer setup guide | SWE | Lead | P1.8 | Nowy dev klonuje repo, uruchamia `just dev` i wszystko działa | — |
| P1.18 | `ARCHITECTURE.md` — diagram wysokopoziomowy (Mermaid) | SWE | MLEng, DataEng | P1.4 | Diagram w `docs/architecture/overview.md`, up-to-date | — |
| P1.19 | Dependency audit — usunięcie nieużywanych, upgrade przestarzałych | SWE | MLEng | P1.2 | `uv tree` czysty, `pip-audit` bez high vulns | — |
| P1.20 | Benchmark performance — materialize_features, training, prediction (aby mierzyć regresje w P2+) | MLEng | DataEng | P1.15 | `benchmarks/` folder z wynikami, uruchamialne przez `just bench` | — |
| P1.21 | `just` (command runner) — wspólny Justfile dla developerów | SWE | — | P1.2 | `just` commands: dev, test, lint, typecheck, bench, migrate, clean | — |
| P1.22 | Split `src/processing/pipeline.py` na `extractors/`, `transformers/`, `loaders/` | DataEng | MLEng | P1.4 | Plik < 300 linii, każda klasa testowana | — |
| P1.23 | Split `src/utils/database.py` na `src/db/` z osobnymi plikami per tabela/operacja | DataEng | — | P1.22 | `src/ml_in_sports/db/` zawiera `matches.py`, `odds.py`, `players.py`, `base.py` | — |
| P1.24 | Ustandaryzowanie team_name normalization — jeden moduł z pełną mapą | DataEng | — | P1.4 | `src/ml_in_sports/utils/team_names.py` z testami per liga | — |
| P1.25 | CI caching — uv cache, pytest cache, docker layer cache | SWE | — | P1.8 | CI czas < 5 min dla średniego PR | — |
| P1.26 | Docker setup — base image dla dev + production | SWE | DataEng | P1.2 | `docker-compose up` startuje API + DB lokalnie | — |
| P1.27 | Design system init — kolory, typografia, spacing, Figma tokens | Designer | SWE | — | `packages/ui/tokens.json` + Figma library z podstawowymi tokenami | — |
| P1.28 | Review IP whitepaper draft od DrMat (rozpoczęty równolegle) | DrMat | MLEng, Lead | — | Pierwszy draft w `docs/whitepaper/hybrid_calibrated_portfolio_kelly_v1.md` | — |

## Równoległa praca (aby zespół nie zanudził się cleanupem)

Podczas gdy MLEng/DataEng/SWE sprzątają:
- **DrMat** pracuje nad whitepaperem IP (P1.28) i audytem matematycznym z P0.20 — to wchodzi jako draft do P2
- **Designer** pracuje nad design systemem (P1.27), moodboardem, wireframes do P6 (research wyprzedzający)
- **Lead** pracuje nad pierwszymi rozmowami sprzedażowymi (customer discovery), analizą konkurencji, pricingiem

## Code review gates

- Każdy PR: min. 1 reviewer (P1)
- Critical paths (migrations, CI, security): min. 2 reviewers
- Linear task zamknięty tylko po merge do main

## Kluczowe decyzje w P1

1. **uv vs Poetry** — **rekomendacja uv** (szybsze, lepszy workspace)
2. **Typer vs Click** — **rekomendacja Typer** (type-safe, modern)
3. **structlog vs loguru** — **rekomendacja structlog** (JSON output, ecosystem)
4. **pytest config** — jakie markers (slow, integration, gpu), jakie fixtures centralizujemy
5. **Mypy strict scope** — `src/ml_in_sports` only, czy też tests?
