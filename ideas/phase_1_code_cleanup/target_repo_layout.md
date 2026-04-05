# Target Repo Layout — After Phase 1

Ten dokument opisuje **docelową strukturę katalogów** po zakończeniu Phase 1. Każda ścieżka ma wyjaśnienie, co się w niej znajduje.

## Drzewo katalogów (root = `sportslab/`)

```
sportslab/
│
├── apps/                               # Deployable applications (będą rosnąć od P5+)
│   ├── api/                            # FastAPI backend (P6)
│   ├── web/                            # Next.js frontend (P6)
│   └── scheduler/                      # Prefect flows orchestrator (P5)
│
├── packages/
│   ├── ml-in-sports/                   # CORE Python package (to serce repo)
│   │   ├── src/
│   │   │   └── ml_in_sports/
│   │   │       ├── __init__.py
│   │   │       ├── config.py           # Pydantic Settings (env vars)
│   │   │       ├── logging.py          # Structlog config
│   │   │       │
│   │   │       ├── cli/                # Entry points (Typer)
│   │   │       │   ├── __init__.py
│   │   │       │   ├── main.py         # Root CLI: `sl` command
│   │   │       │   ├── pipeline.py     # `sl run-pipeline`
│   │   │       │   ├── scrape.py       # `sl scrape sts`, `sl scrape espn`
│   │   │       │   ├── train.py        # `sl train --model lgb --league epl`
│   │   │       │   ├── predict.py      # `sl predict --round 32`
│   │   │       │   ├── backtest.py     # `sl backtest --strategy s1`
│   │   │       │   └── report.py       # `sl report --format md|pdf|json`
│   │   │       │
│   │   │       ├── db/                 # Database access layer
│   │   │       │   ├── __init__.py
│   │   │       │   ├── base.py         # SQLAlchemy base, session factory
│   │   │       │   ├── matches.py      # Matches CRUD
│   │   │       │   ├── odds.py         # Odds CRUD
│   │   │       │   ├── players.py      # Players CRUD
│   │   │       │   ├── scrape_log.py   # ScrapeLog CRUD
│   │   │       │   └── fifa.py         # FIFA ratings
│   │   │       │
│   │   │       ├── processing/         # Data extraction + transformation
│   │   │       │   ├── __init__.py
│   │   │       │   ├── base.py         # BaseExtractor abstract
│   │   │       │   ├── extractors/
│   │   │       │   │   ├── understat.py
│   │   │       │   │   ├── espn.py
│   │   │       │   │   ├── sofascore.py
│   │   │       │   │   ├── clubelo.py
│   │   │       │   │   ├── footballdata.py
│   │   │       │   │   ├── transfermarkt.py
│   │   │       │   │   ├── fifa.py
│   │   │       │   │   └── pinnacle.py      # NEW in P2 (CLV tracking)
│   │   │       │   ├── transformers/
│   │   │       │   │   ├── align_dates.py
│   │   │       │   │   ├── normalize_names.py
│   │   │       │   │   └── merge_sources.py
│   │   │       │   └── loaders/
│   │   │       │       ├── sqlite_loader.py
│   │   │       │       └── postgres_loader.py  # P5+
│   │   │       │
│   │   │       ├── features/           # Feature engineering
│   │   │       │   ├── __init__.py
│   │   │       │   ├── base.py         # BaseFeatureBuilder
│   │   │       │   ├── rolling.py
│   │   │       │   ├── elo.py
│   │   │       │   ├── tactical.py
│   │   │       │   ├── form.py
│   │   │       │   ├── contextual.py
│   │   │       │   ├── setpiece.py
│   │   │       │   ├── betting.py
│   │   │       │   ├── player.py
│   │   │       │   ├── table.py        # league table features (z NB13)
│   │   │       │   └── build.py        # Orchestrator: build_all_features()
│   │   │       │
│   │   │       ├── models/             # Model definitions + inference
│   │   │       │   ├── __init__.py
│   │   │       │   ├── base.py         # BaseModel abstract
│   │   │       │   ├── schemas.py      # Pydantic models (Match, Bet, Prediction)
│   │   │       │   ├── lgb.py
│   │   │       │   ├── xgb.py
│   │   │       │   ├── tabpfn.py
│   │   │       │   ├── logreg.py
│   │   │       │   ├── ensemble.py
│   │   │       │   ├── dixon_coles.py  # NEW P2
│   │   │       │   ├── calibration.py  # NEW P2
│   │   │       │   └── portfolio_kelly.py  # NEW P2 (IP)
│   │   │       │
│   │   │       ├── backtesting/        # Backtest framework
│   │   │       │   ├── __init__.py
│   │   │       │   ├── walk_forward.py
│   │   │       │   ├── strategies.py   # S1, S2, S3, S4, S5 strategies
│   │   │       │   ├── metrics.py      # ROI, yield, CLV, sharpe
│   │   │       │   └── reports.py
│   │   │       │
│   │   │       ├── sports/             # Multi-sport abstraction (P4+)
│   │   │       │   ├── __init__.py
│   │   │       │   ├── base_adapter.py
│   │   │       │   ├── football/
│   │   │       │   ├── tennis/         # P4.1
│   │   │       │   ├── basketball/     # P4.2
│   │   │       │   └── hockey/         # P4.3
│   │   │       │
│   │   │       ├── reporting/          # Output generation
│   │   │       │   ├── __init__.py
│   │   │       │   ├── markdown.py     # MD reports (obecny format)
│   │   │       │   ├── pdf.py          # PDF reports (P6)
│   │   │       │   └── json_export.py  # API-ready JSON
│   │   │       │
│   │   │       └── utils/
│   │   │           ├── __init__.py
│   │   │           ├── team_names.py
│   │   │           ├── seasons.py
│   │   │           ├── dates.py
│   │   │           └── paths.py
│   │   │
│   │   ├── tests/
│   │   │   ├── conftest.py
│   │   │   ├── fixtures/               # Test data (mini CSVs, mock responses)
│   │   │   ├── unit/
│   │   │   │   ├── test_features/
│   │   │   │   ├── test_models/
│   │   │   │   ├── test_processing/
│   │   │   │   └── test_utils/
│   │   │   ├── integration/
│   │   │   │   ├── test_pipeline_end_to_end.py
│   │   │   │   ├── test_backtest.py
│   │   │   │   └── test_cli.py
│   │   │   └── benchmarks/             # pytest-benchmark
│   │   │
│   │   ├── alembic/                    # DB migrations
│   │   │   ├── env.py
│   │   │   └── versions/
│   │   │
│   │   ├── pyproject.toml              # Package config
│   │   └── README.md
│   │
│   ├── shared-types/                   # Type contracts (Python ↔ TS)
│   │   ├── schemas/                    # Pydantic models
│   │   └── generated/                  # Auto-generated TS types
│   │
│   ├── ui/                             # Design system (Designer owner)
│   │   ├── tokens.json
│   │   ├── components/
│   │   └── figma/
│   │
│   └── config/                         # Shared tooling configs
│       ├── tsconfig.base.json
│       ├── ruff.toml
│       ├── mypy.ini
│       └── eslint.config.js
│
├── research/                           # Notebooks + experimental scripts (non-production)
│   ├── notebooks/
│   │   ├── 01_feature_quality_eda.ipynb
│   │   ├── ... (obecne 18 notebooków)
│   │   └── README.md
│   └── experiments/
│       └── (new experiments in phase 2+)
│
├── infra/                              # Infrastructure as code
│   ├── docker/
│   │   ├── Dockerfile.api
│   │   ├── Dockerfile.scheduler
│   │   └── Dockerfile.ml
│   ├── docker-compose.yml              # Local dev
│   ├── docker-compose.prod.yml         # Production
│   ├── prefect/                        # Prefect deployments (P5)
│   ├── nginx/                          # Reverse proxy
│   └── grafana/                        # Dashboards as JSON
│
├── docs/
│   ├── architecture/
│   │   ├── overview.md                 # System diagram (Mermaid)
│   │   ├── data_flow.md
│   │   ├── ml_pipeline.md
│   │   └── api.md
│   ├── sports/                         # Per-sport docs (P4+)
│   ├── leagues/                        # Per-league docs (P3+)
│   ├── feature_catalog.md              # Rozszerzony z obecnego
│   ├── schema.md                       # DB schema
│   ├── whitepaper/
│   │   └── hybrid_calibrated_portfolio_kelly.md  # IP publication
│   └── tutorials/                      # Developer onboarding
│
├── ideas/                              # Ten folder — planning artifacts (all phases)
│
├── data/                               # Gitignored, bez commitów
│   ├── raw/                            # Source dumps
│   ├── features/                       # Parquet features
│   ├── artifacts/                      # Model artifacts + bets
│   └── cache/                          # soccerdata cache
│
├── logs/                               # Gitignored
│
├── .github/
│   ├── workflows/
│   │   ├── ci.yml
│   │   ├── deploy.yml                  # P5+
│   │   └── nightly.yml                 # P5+
│   ├── CODEOWNERS
│   ├── pull_request_template.md
│   └── ISSUE_TEMPLATE/
│
├── pyproject.toml                      # Root Python workspace (uv)
├── pnpm-workspace.yaml                 # TS workspaces
├── Justfile                            # Command runner
├── .pre-commit-config.yaml
├── .gitignore
├── README.md
├── CONTRIBUTING.md
├── LICENSE
└── SECURITY.md
```

## Kluczowe różnice vs obecny stan

| Element | Teraz | Docelowo |
|---|---|---|
| Top-level Python | `src/` | `packages/ml-in-sports/src/ml_in_sports/` |
| Skrypty | `scripts/*.py` (45+) | `src/ml_in_sports/cli/*.py` (CLI subcommands) |
| Notebooki | `notebooks/` (w repo root) | `research/notebooks/` (niezintegrowane z production) |
| Archiv skrypty | `scripts/_archive/` | gałąź `archive/pre-cleanup`, usunięte z main |
| DB layer | `src/utils/database.py` (1 plik) | `src/ml_in_sports/db/*.py` (per tabela) |
| Pipeline | `src/processing/pipeline.py` (monolit) | `src/ml_in_sports/processing/{extractors,transformers,loaders}/` |
| Config | Hardcoded paths | `src/ml_in_sports/config.py` + env vars |
| Logging | `print()` + basic logging | structlog + JSON output |
| Tests | 21 plików, nieznane pokrycie | 21+ plików, ≥ 80% pokrycia, z marker'ami |
| CI | Brak | GitHub Actions na każdy PR |
| Docker | Brak | Multi-stage Dockerfiles + docker-compose |
| Docs | `docs/` (kilka mdfiles) | Rozszerzone `docs/` + Mermaid diagramy |
| Multi-sport | Brak | `src/ml_in_sports/sports/` abstraction (ready for P4) |

## Naming conventions

- **Moduły**: `snake_case`
- **Klasy**: `PascalCase`
- **Funkcje / metody**: `snake_case`
- **Stałe**: `UPPER_SNAKE_CASE`
- **Private**: `_leading_underscore`
- **CLI commands**: `kebab-case` (np. `sl run-pipeline`)
- **Linear issues**: `SPO-123` prefix (projekt "SportsLab Operations")
- **Git branches**: `feature/SPO-123-add-tennis-elo`

## Package naming

- Python: `ml_in_sports` (snake_case, jak obecnie)
- PyPI (jeśli kiedyś publikujemy): `sportslab-ml` (brand-aligned)
- npm (jeśli publikujemy komponenty): `@sportslab/ui`, `@sportslab/types`
