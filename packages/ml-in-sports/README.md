# ml-in-sports

Core Python package for SportsLab. Features, models, backtesting, and data processing.

## Package structure

```
src/ml_in_sports/
├── backtesting/          Walk-forward backtest framework
│   ├── config.py         YAML experiment config (Pydantic)
│   ├── metrics.py        11 evaluation metrics (ECE, CLV, ROI, Sharpe, ...)
│   ├── runner.py          WalkForwardRunner orchestrator
│   ├── models.py          BaseModel protocol + DummyModel
│   ├── simulation.py      Flat-bet simulation helpers
│   └── report/
│       ├── generator.py   Report data builder
│       ├── html.py        Plotly interactive HTML report
│       ├── terminal.py    Rich terminal summary
│       └── charts.py      Chart builders (CLV, equity, comparison)
├── cli/                  Typer CLI (`sl` command)
│   ├── main.py            Root app + logging callback
│   ├── pipeline_cmd.py    `sl pipeline run`
│   ├── features_cmd.py    `sl features build`
│   ├── kelly_cmd.py       `sl kelly compute`
│   ├── refresh_cmd.py     `sl refresh run`
│   └── backtest_cmd.py    `sl backtest run <config>`
├── db/                   SQLAlchemy models (11 tables)
│   └── models.py          Declarative models matching SQLite schema
├── features/             Feature engineering (15 modules, ~8.5k LOC)
│   ├── _shared.py         Common helpers (compute_match_points, ensure_datetime)
│   ├── rolling_features.py  Rolling xG, goals, shots, possession
│   ├── betting_features.py  Odds → implied probs, overround, fair odds
│   ├── form_features.py     Win/loss streaks, timing, discipline
│   ├── tactical_features.py  PPDA, possession, efficiency ratios
│   ├── contextual_features.py  Venue stats, fatigue, H2H
│   ├── formation_features.py  Formation parsing, stability, matchup
│   ├── derived_features.py  Calendar, lags, interactions, percentiles
│   ├── setpiece_features.py  Corner/FK/open play set-piece metrics
│   ├── player_features.py  FIFA/FC ratings aggregation
│   ├── player_rolling_features.py  Per-player form → team aggregation
│   ├── match_player_quality.py  XI quality, market value, bench strength
│   ├── new_features.py    League table position, xG rolling, venue streaks
│   ├── build_features.py  Master DataFrame builder (joins all tables)
│   └── targets.py         Target variables (1X2, OU, BTTS, DC, margins)
├── models/
│   ├── calibration/       Probability calibration
│   │   ├── temperature.py   TemperatureScaler (TabPFN overconfidence fix)
│   │   ├── platt.py         PlattScaler (logistic regression on logits)
│   │   ├── isotonic.py      IsotonicScaler (non-parametric)
│   │   └── selector.py      Walk-forward auto-select best method
│   ├── ensemble/          Model wrappers + stacking
│   │   ├── registry.py      LightGBM, XGBoost, TabPFN, Dummy wrappers
│   │   └── stacking.py      OOF stacking meta-learner
│   ├── kelly/             Staking algorithms
│   │   ├── portfolio.py     Portfolio Kelly with exposure constraints
│   │   └── shrinkage.py     Shrinkage toward market for outlier edges
│   ├── monitoring/        Drift and calibration monitoring
│   │   ├── drift.py         PSI (Population Stability Index)
│   │   └── ece.py           Rolling ECE per league/market
│   ├── schemas.py         Data classes (MatchRecord, etc.)
│   └── value_betting.py   Basic Kelly stake computation
├── processing/
│   ├── extractors.py      7 data extractors (Understat, ESPN, FBref, ...)
│   ├── pipeline.py        Pipeline orchestrator (1187 LOC)
│   └── odds/
│       ├── pinnacle.py    Pinnacle closing odds loader (football-data.co.uk)
│       └── clv.py         CLV (Closing Line Value) tracker
├── utils/
│   ├── database.py        FootballDatabase (SQLite, 11 tables)
│   ├── seasons.py         Season code utilities
│   └── team_names.py      Team name normalization (alias mapping)
├── settings.py            Centralized config (pydantic-settings)
└── logging.py             structlog configuration
```

## Development

```bash
# From monorepo root:
uv sync --all-extras --dev

# Tests
uv run pytest packages/ml-in-sports -q          # 1029 tests
uv run pytest packages/ml-in-sports --cov       # with coverage (87.5%)

# Lint + typecheck
uv run ruff check packages/ml-in-sports
uv run mypy packages

# CLI
uv run sl --help
uv run sl backtest run experiments/hybrid_v1.yaml --synthetic
```

## Key design decisions

- **Walk-forward backtesting** (not k-fold) to prevent time leakage in sports data
- **Calibration per (league, season, market)** — each combination gets the best scaler
- **Portfolio Kelly with constraints** — per-match, per-round, per-league exposure caps
- **Shrinkage toward market** — reduces Kelly when edge is suspiciously large
- **TabPFN optional** — ensemble works without it (LGB + XGB + LogReg meta)
- **structlog everywhere** — structured JSON logging, zero print() statements
- **pydantic-settings** — all paths/config from env vars (ML_IN_SPORTS_ prefix)
- **Alembic migrations** — schema versioned, supports SQLite and Postgres
