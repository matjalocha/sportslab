# Codex Prompts — R5b More Sports

> Realizuj sekwencyjnie (tenis → koszykówka → hokej).
> Testy RAZ na końcu każdego sportu.
> Po zakończeniu zapisz status w `docs/codex_status_r5b.md`.

---

## TASK-R5b-01: Abstract sport framework

```
Stwórz bazową architekturę multi-sport.

Pliki do stworzenia:
- packages/ml-in-sports/src/ml_in_sports/sports/__init__.py
- packages/ml-in-sports/src/ml_in_sports/sports/base.py
- packages/ml-in-sports/tests/sports/__init__.py
- packages/ml-in-sports/tests/sports/test_base.py

sports/base.py:
```python
"""Abstract base classes for multi-sport support."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

@dataclass(frozen=True)
class SportConfig:
    """Configuration for a sport."""
    name: str                    # "football", "tennis", "basketball", "hockey"
    markets: list[str]           # ["1x2", "over_under_25", "btts"] or ["match_winner"]
    target_column: str           # "result_1x2" or "winner"
    target_encoding: dict[str, int]  # {"H": 0, "D": 1, "A": 2} or {"player1": 0, "player2": 1}
    min_train_samples: int       # 500 for football, 200 for tennis
    default_seasons: list[str]   # ["2223", "2324", "2425"]

class BaseSportDataLoader(ABC):
    """Abstract data loader for a sport."""
    
    @abstractmethod
    def load(self, seasons: list[str] | None = None) -> pd.DataFrame: ...
    
    @abstractmethod
    def get_feature_columns(self) -> list[str]: ...
    
    @abstractmethod
    def get_upcoming_matches(self) -> pd.DataFrame: ...

class BaseSportFeatureBuilder(ABC):
    """Abstract feature engineering for a sport."""
    
    @abstractmethod
    def build_features(self, raw_data: pd.DataFrame) -> pd.DataFrame: ...

# Football config (existing sport)
FOOTBALL_CONFIG = SportConfig(
    name="football",
    markets=["1x2", "over_under_25", "btts"],
    target_column="result_1x2",
    target_encoding={"H": 0, "D": 1, "A": 2},
    min_train_samples=500,
    default_seasons=["2223", "2324", "2425"],
)
```

Testy:
- SportConfig creation
- FOOTBALL_CONFIG has correct values
- ABC cannot be instantiated directly
```

---

## TASK-R5b-02: Tennis — Jeff Sackmann data loader

```
Załaduj dane tenisowe z Jeff Sackmann GitHub.

Pliki do stworzenia:
- packages/ml-in-sports/src/ml_in_sports/sports/tennis/__init__.py
- packages/ml-in-sports/src/ml_in_sports/sports/tennis/data.py
- packages/ml-in-sports/src/ml_in_sports/sports/tennis/config.py
- packages/ml-in-sports/tests/sports/tennis/__init__.py
- packages/ml-in-sports/tests/sports/tennis/test_data.py

Jeff Sackmann data format (CSV z GitHub):
https://github.com/JeffSackmann/tennis_atp/blob/master/atp_matches_2024.csv

Kolumny: tourney_id, tourney_name, surface, draw_size, tourney_level,
tourney_date, match_num, winner_id, winner_name, winner_hand, winner_ht,
winner_ioc, winner_age, loser_id, loser_name, ..., score, best_of,
round, minutes, w_ace, w_df, w_svpt, w_1stIn, w_1stWon, w_2ndWon,
w_SvGms, w_bpSaved, w_bpFaced, l_ace, l_df, ...

config.py:
```python
TENNIS_CONFIG = SportConfig(
    name="tennis",
    markets=["match_winner"],
    target_column="winner",
    target_encoding={"player1": 0, "player2": 1},
    min_train_samples=200,
    default_seasons=["2022", "2023", "2024", "2025"],
)
```

data.py:
```python
class TennisDataLoader(BaseSportDataLoader):
    """Load ATP/WTA match data from Jeff Sackmann CSVs.
    
    Data source: https://github.com/JeffSackmann/tennis_atp
    
    Args:
        data_dir: Directory with atp_matches_YYYY.csv files.
    """
    
    def __init__(self, data_dir: Path = Path("data/tennis")) -> None: ...
    
    def download_season(self, year: int) -> Path:
        """Download a season CSV from GitHub."""
    
    def load(self, seasons: list[str] | None = None) -> pd.DataFrame:
        """Load and standardize match data.
        
        Standardized columns:
        - match_id, date, tournament, surface (hard/clay/grass/indoor)
        - player1, player2 (alphabetically sorted for consistency)
        - winner (0=player1, 1=player2)
        - player1_rank, player2_rank
        - score, best_of, round
        - Stats: aces, double_faults, serve_points, 1st_serve_pct, etc.
        """
    
    def get_feature_columns(self) -> list[str]: ...
    def get_upcoming_matches(self) -> pd.DataFrame: ...
```

Testy: test z fake CSV (3-4 matches), standardization, download mock.
```

---

## TASK-R5b-03: Tennis — ELO + features

```
Feature engineering dla tenisa.

Pliki do stworzenia:
- packages/ml-in-sports/src/ml_in_sports/sports/tennis/features.py
- packages/ml-in-sports/src/ml_in_sports/sports/tennis/elo.py
- packages/ml-in-sports/tests/sports/tennis/test_features.py
- packages/ml-in-sports/tests/sports/tennis/test_elo.py

elo.py:
```python
class TennisElo:
    """ELO rating system per surface.
    
    Maintains separate ratings for hard, clay, grass, indoor.
    K-factor: 32 (default), decays for established players.
    """
    
    def __init__(self, k_factor: float = 32.0, initial_rating: float = 1500.0) -> None: ...
    
    def update(self, winner: str, loser: str, surface: str) -> tuple[float, float]:
        """Update ratings after a match. Returns (winner_new, loser_new)."""
    
    def get_rating(self, player: str, surface: str) -> float: ...
    def get_overall_rating(self, player: str) -> float:
        """Weighted average across surfaces."""
```

features.py:
```python
class TennisFeatureBuilder(BaseSportFeatureBuilder):
    """Feature engineering for tennis.
    
    Features:
    - ELO diff (overall + per surface)
    - Ranking diff
    - Form: win rate last 10/20 matches
    - H2H: historical record between the two players
    - Fatigue: days since last match, matches in last 7/14/30 days
    - Surface specialist: win rate on this surface
    - Tournament level: Grand Slam vs ATP500 vs ATP250
    - Age, height difference
    - Serve stats rolling (aces, double faults, 1st serve %)
    """
    
    def build_features(self, matches: pd.DataFrame) -> pd.DataFrame:
        """Add all features to match DataFrame. Uses shift(1) to prevent lookahead."""
```

Testy:
- ELO: after win, winner rating increases, loser decreases
- ELO: per-surface ratings independent
- Features: shift(1) verified
- H2H: correct historical record
```

---

## TASK-R5b-04: Tennis — backtest + experiment config

```
Uruchom backtest na tenisie.

Pliki do stworzenia:
- experiments/tennis_atp.yaml
- packages/ml-in-sports/src/ml_in_sports/sports/tennis/backtest.py

tennis_atp.yaml:
```yaml
name: "ATP Tennis Backtest"
description: "Tennis 1v1 prediction: LGB + XGB, ELO features"
data:
  sport: tennis
  seasons: ["2022", "2023", "2024"]
models:
  - name: lightgbm
    type: lightgbm
    params: {n_estimators: 200}
  - name: xgboost
    type: xgboost
    params: {n_estimators: 200}
calibration:
  methods: [platt, isotonic]
evaluation:
  walk_forward: {train_seasons: 2, test_seasons: 1}
```

backtest.py — adapter: łączy TennisDataLoader + TennisFeatureBuilder z 
istniejącym WalkForwardRunner. Może wymagać rozszerzenia runnera o parametr `sport`.
Jeśli runner wymaga zmian — minimalne (dodaj `sport: str` do ExperimentConfig).
```

---

## TASK-R5b-05: Basketball — NBA data loader + features

```
Pliki do stworzenia:
- packages/ml-in-sports/src/ml_in_sports/sports/basketball/__init__.py
- packages/ml-in-sports/src/ml_in_sports/sports/basketball/data.py
- packages/ml-in-sports/src/ml_in_sports/sports/basketball/features.py
- packages/ml-in-sports/src/ml_in_sports/sports/basketball/config.py
- packages/ml-in-sports/tests/sports/basketball/__init__.py
- packages/ml-in-sports/tests/sports/basketball/test_data.py
- packages/ml-in-sports/tests/sports/basketball/test_features.py

Data source: NBA Stats API (stats.nba.com) — free, rate limited (1 req/s).

config.py:
```python
BASKETBALL_CONFIG = SportConfig(
    name="basketball",
    markets=["moneyline", "spread", "totals"],
    target_column="winner",
    target_encoding={"home": 0, "away": 1},
    min_train_samples=300,
    default_seasons=["2022-23", "2023-24", "2024-25"],
)
```

Features:
- Pace-adjusted: OffRtg, DefRtg, NetRtg
- Rolling: scoring, rebounds, assists, turnovers
- Back-to-back: fatigue indicator (played yesterday)
- Home/away split stats
- Player availability (simplified: team strength proxy)
- H2H season record

Rate limiting: 1 req/s. Cache responses locally.
Testy: mock API responses (zero live calls).
```

---

## TASK-R5b-06: Hockey — NHL data loader + features

```
Pliki do stworzenia:
- packages/ml-in-sports/src/ml_in_sports/sports/hockey/__init__.py
- packages/ml-in-sports/src/ml_in_sports/sports/hockey/data.py
- packages/ml-in-sports/src/ml_in_sports/sports/hockey/features.py
- packages/ml-in-sports/src/ml_in_sports/sports/hockey/config.py
- packages/ml-in-sports/tests/sports/hockey/__init__.py
- packages/ml-in-sports/tests/sports/hockey/test_data.py

Data source: NHL API (api-web.nhle.com) — free, no auth.

config.py:
```python
HOCKEY_CONFIG = SportConfig(
    name="hockey",
    markets=["moneyline", "puck_line", "totals"],
    target_column="winner",
    target_encoding={"home": 0, "away": 1},
    min_train_samples=300,
    default_seasons=["2022-23", "2023-24", "2024-25"],
)
```

Features:
- Corsi, Fenwick (shot attempt metrics)
- PDO (shooting % + save %)
- Power play / penalty kill %
- Rolling goals for/against
- Goalie save %
- Back-to-back fatigue
- Home/away splits

Testy: mock API responses.

Po zakończeniu WSZYSTKICH tasków R5b, uruchom:
```bash
uv run ruff check packages/ml-in-sports --fix
uv run mypy packages
uv run pytest packages/ml-in-sports -q
```

Zapisz wynik w docs/codex_status_r5b.md.
```
