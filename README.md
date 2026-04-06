# SportsLab

Sports analytics and value-betting platform. B2B productization of ML research codebase.

**Current phase:** R2 — Better Models (backtest framework, calibration, ensemble)

## Quick start

```bash
# Install everything
uv sync --all-extras --dev

# Run tests (1029 passing)
uv run pytest packages/ml-in-sports -q

# Lint + typecheck
uv run ruff check .
uv run mypy packages

# Run a backtest with synthetic data
uv run sl backtest run experiments/hybrid_v1.yaml --synthetic

# See all CLI commands
uv run sl --help
```

## Repository structure

```
sportslab/
├── packages/ml-in-sports/       Core Python package (features, models, backtesting)
│   ├── src/ml_in_sports/        Production source code
│   ├── tests/                   1029 tests, 87.5% coverage
│   ├── alembic/                 Database migrations
│   └── experiments/             YAML backtest configs
├── docs/
│   ├── architecture/            ADRs (decision records)
│   ├── design/                  Report specs, UI guidelines
│   ├── tech_debt_audit.md       Research codebase audit
│   ├── math_audit.md            NB01-NB30 model audit
│   ├── pricing_validation.md    Competitor pricing research
│   └── migration_pattern.md     P1 migration playbook
├── ideas/                       Roadmap and planning artifacts
│   ├── solo_founder_roadmap.md  Active roadmap (R0-R6)
│   └── phase_*/                 Detailed phase plans (reference)
├── .claude/                     Claude Code config and subagents
├── .github/workflows/ci.yml    GitHub Actions (ruff + mypy + pytest)
└── reports/                     Generated backtest reports (HTML)
```

## Key commands

| Command | Description |
|---------|-------------|
| `sl pipeline run` | Run data pipeline (scrape + store) |
| `sl features build` | Materialize features to Parquet |
| `sl backtest run <config>` | Walk-forward backtest with HTML report |
| `sl kelly compute` | Compute Kelly stakes for current bets |
| `sl refresh run` | Refresh current season data |

## Tech stack

- **Python 3.11+**, managed by **uv** (workspace)
- **ML:** LightGBM, XGBoost, TabPFN, scikit-learn
- **Quality:** ruff (strict), mypy (strict), pytest (87.5% coverage)
- **Structured logging:** structlog
- **Config:** pydantic-settings (env var based)
- **Database:** SQLite (dev) / Postgres (production), Alembic migrations
- **Reports:** Plotly (interactive HTML) + Rich (terminal)

## Roadmap

See [ideas/solo_founder_roadmap.md](ideas/solo_founder_roadmap.md) for the full plan.

| Phase | Status | Summary |
|-------|--------|---------|
| R0 Foundations | Done | Linear, GitHub, audits |
| R1 Clean Code | Done | 22 modules migrated, 1029 tests, CLI, Alembic |
| **R2 Better Models** | **In Progress** | Backtest framework, calibration, Kelly, ensemble |
| R3 Proof of Edge | Planned | Paper trading + real money validation |
| R4 Automation | Planned | VPS, cron, Postgres, Telegram alerts |
| R5 Expansion | Planned | More leagues + sports |
| R6 Product | Planned | FastAPI, Stripe, first customer |

## Development

```bash
# Pre-commit hooks
uv run pre-commit install
uv run pre-commit run --all-files

# Coverage report
uv run pytest packages/ml-in-sports --cov --cov-report=html

# Database migrations
cd packages/ml-in-sports && uv run alembic upgrade head
```

## Project tracking

Linear workspace: [sportslab](https://linear.app/sportslab) (team key: SPO)
