# Codex Status R5a

Date: 2026-04-06

## Tasks

- TASK-R5a-01: DONE
  - Added central league registry for 14 leagues.
  - Added `sl download-leagues` CLI.
  - Extended football-data.co.uk code map with R5a leagues.
  - Added registry tests.

- TASK-R5a-02: DONE
  - Extended team-name aliases for Championship, Eredivisie, Ekstraklasa, Portugal, Belgium, Turkey, and Czech Republic.
  - Extended known team names and tests.

- TASK-R5a-03: DONE
  - Added basic non-xG feature pipeline using shifted rolling goals, form, shots on target, corners, fouls, cards, home win rate, odds-implied values, and optional table-position deltas.
  - Added leakage-oriented tests for `shift(1)` and rolling windows.

- TASK-R5a-04: DONE
  - Added experiment configs:
    - `experiments/championship.yaml`
    - `experiments/eredivisie.yaml`
    - `experiments/ekstraklasa.yaml`
    - `experiments/all_14_leagues.yaml`
  - Updated raw-stat exclusions so newly ingested football-data match stats are not used as current-match features.

- TASK-R5a-05: DONE
  - Added football-data ingestion pipeline: download, parse, normalize team names, compute basic features, append/deduplicate parquet.
  - Added `sl ingest` CLI.
  - Added mock CSV-to-parquet ingestion test.

## Verification

- `uv run ruff check packages/ml-in-sports --fix`: PASS
- `uv run mypy packages`: FAIL with 24 existing non-R5a errors in:
  - `packages/ml-in-sports/tests/backtesting/test_data.py`
  - `packages/ml-in-sports/tests/models/ensemble/test_stacking.py`
  - `packages/ml-in-sports/tests/backtesting/test_calibration_integration.py`
  - `packages/ml-in-sports/tests/backtesting/test_runner.py`
- `uv run pytest packages/ml-in-sports -q`: PASS, `1209 passed`
- `uv run sl download-leagues --help`: PASS
- `uv run sl ingest --help`: PASS
- `uv run sl download-leagues --leagues UNKNOWN --seasons 2425`: PASS callback smoke test, no network download attempted
