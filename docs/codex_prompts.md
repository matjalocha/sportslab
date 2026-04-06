# Prompty dla Codex — SportsLab

> Kopiuj każdy prompt osobno do Codexa. Każdy jest samodzielny.
> TASK-01,02,03 (report sekcje C,F,H) już zaimplementowane — skip.
> Zacznij od TASK-04.
> 
> Repo root: główny katalog projektu (tam gdzie jest pyproject.toml)
> Python package: `packages/ml-in-sports/src/ml_in_sports/`
> Testy: `packages/ml-in-sports/tests/`
> 
> Po każdym tasku uruchom:
> ```bash
> uv run ruff check packages/ml-in-sports --fix
> uv run mypy packages
> uv run pytest packages/ml-in-sports -q
> ```
> Wszystkie 1134+ testów muszą przechodzić. Zero nowych ruff/mypy errors.

---

## TASK-04: Daily Predictor — generuj codzienne rekomendacje zakładów

```
# KONTEKST PROJEKTU

SportsLab to platforma sports analytics / value-betting.
Repo jest Python monorepo zarządzane przez `uv` (package manager).
Główny package: `packages/ml-in-sports/src/ml_in_sports/`
Testy: `packages/ml-in-sports/tests/`
CLI: Typer, entry point `sl` (zdefiniowany w cli/main.py)

Mamy backtest framework który trenuje modele ML (LightGBM, XGBoost) na historycznych
danych piłkarskich i generuje raporty. Teraz potrzebujemy **daily prediction pipeline**:
załaduj dane → trenuj model na historii → predykcja na upcoming mecze → oblicz Kelly stakes
→ output listę rekomendowanych zakładów.

# DANE

Features parquet: `data/features/all_features.parquet`
- 21,719 wierszy, 825 kolumn
- Kolumny kluczowe:
  - `league` (str): "ENG-Premier League", "ESP-La Liga", "GER-Bundesliga", "ITA-Serie A", "FRA-Ligue 1"
  - `season` (str): "1415" do "2526" (format 4-cyfrowy, np. "2324" = sezon 2023/24)
  - `game` (str): "2024-01-06 Arsenal-Chelsea" (unique match ID)
  - `date` (datetime): data meczu
  - `home_team`, `away_team` (str): nazwy drużyn
  - `result_1x2` (str): "H" (home win), "D" (draw), "A" (away win) — NaN dla upcoming meczów
  - `b365_home`, `b365_draw`, `b365_away` (float): kursy Bet365
  - `avg_home`, `avg_draw`, `avg_away` (float): średnie kursy rynkowe
  - ~800 feature columns (numeryczne): rolling stats, elo, form, itp.

Upcoming mecze = wiersze gdzie `result_1x2` jest NaN (lub date > today).

# CO STWORZYĆ

## 1. packages/ml-in-sports/src/ml_in_sports/prediction/__init__.py

```python
"""Daily prediction pipeline for SportsLab."""
```

## 2. packages/ml-in-sports/src/ml_in_sports/prediction/daily.py

```python
"""Generate daily bet recommendations.

Pipeline: load features → train model on history → predict upcoming → 
calibrate → compute Kelly stakes → filter by edge → output recommendations.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import structlog

from ml_in_sports.backtesting.data import BacktestDataLoader
from ml_in_sports.models.calibration.selector import CalibrationSelector
from ml_in_sports.models.ensemble.registry import create_model
from ml_in_sports.settings import get_settings

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class BetRecommendation:
    """Single bet recommendation.

    Attributes:
        match_id: Unique match identifier (e.g. "2024-04-06 Arsenal-Chelsea").
        home_team: Home team name.
        away_team: Away team name.
        league: League name (e.g. "ENG-Premier League").
        kickoff: Match kickoff datetime.
        market: Bet market (e.g. "1x2_home", "1x2_draw", "1x2_away").
        model_prob: Model's predicted probability for this outcome.
        bookmaker_prob: Bookmaker's implied probability (1 / odds).
        edge: model_prob - bookmaker_prob. Positive = value bet.
        min_odds: Minimum acceptable odds (1 / model_prob).
        kelly_fraction: Recommended fraction of bankroll to stake.
        stake_eur: Recommended stake in EUR.
        model_agreement: How many models agree (1-3). 3 = all models see value.
        best_bookmaker: Which bookmaker offers best odds.
        best_odds: Best available decimal odds.
    """

    match_id: str
    home_team: str
    away_team: str
    league: str
    kickoff: str  # ISO format string (JSON-safe)
    market: str
    model_prob: float
    bookmaker_prob: float
    edge: float
    min_odds: float
    kelly_fraction: float
    stake_eur: float
    model_agreement: int
    best_bookmaker: str
    best_odds: float


class DailyPredictor:
    """Generate bet recommendations for upcoming matches.

    Usage::

        predictor = DailyPredictor(bankroll=5000.0, min_edge=0.02)
        bets = predictor.predict(date=date(2024, 4, 6))
        predictor.save_predictions(bets, Path("predictions"))

    Args:
        model_type: Model to use ("lightgbm" or "xgboost").
        bankroll: Current bankroll in EUR.
        kelly_fraction: Kelly multiplier (0.25 = quarter-Kelly).
        min_edge: Minimum edge to include (0.02 = 2%).
        parquet_path: Path to features parquet.
    """

    def __init__(
        self,
        model_type: str = "lightgbm",
        bankroll: float = 5000.0,
        kelly_fraction: float = 0.25,
        min_edge: float = 0.02,
        parquet_path: Path | None = None,
    ) -> None:
        self._model_type = model_type
        self._bankroll = bankroll
        self._kelly_fraction = kelly_fraction
        self._min_edge = min_edge
        self._parquet_path = parquet_path or Path("data/features/all_features.parquet")

    def predict(self, target_date: date | None = None) -> list[BetRecommendation]:
        """Generate recommendations for matches on target_date.

        Steps:
        1. Load features parquet via BacktestDataLoader
        2. Split: history (result_1x2 not NaN) as training, upcoming (NaN) as prediction
        3. If no upcoming matches for target_date, return empty list
        4. Select feature columns (same as BacktestDataLoader.get_feature_columns())
        5. Train model on last 2 seasons of history
        6. Predict probabilities on upcoming matches
        7. For each match, for each outcome (H/D/A), compute edge vs bookmaker odds
        8. Filter: keep only bets where edge > min_edge
        9. Compute Kelly fraction per bet
        10. Sort by edge descending
        11. Return list of BetRecommendation

        Args:
            target_date: Date to predict for. None = today.

        Returns:
            List of BetRecommendation sorted by edge descending.
        """
        # IMPLEMENT THIS:
        # 
        # Step 1: Load data
        # loader = BacktestDataLoader(parquet_path=self._parquet_path)
        # df = loader.load()
        #
        # Step 2: Split history vs upcoming
        # history = df[df["result_1x2"].notna()]
        # upcoming = df[df["result_1x2"].isna()]
        # If target_date: filter upcoming by date
        #
        # Step 3: Get feature columns
        # feature_cols = loader.get_feature_columns()
        #
        # Step 4: Prepare training data (last 2 seasons)
        # recent_seasons = sorted(history["season"].unique())[-2:]
        # train = history[history["season"].isin(recent_seasons)]
        # X_train = train[feature_cols].values
        # y_train = train["result_1x2"].map({"H": 0, "D": 1, "A": 2}).values
        # Drop rows with NaN target
        #
        # Step 5: Train model
        # model = create_model(self._model_type, n_estimators=200, learning_rate=0.05)
        # model.fit(pd.DataFrame(X_train, columns=feature_cols), y_train)
        #
        # Step 6: Predict
        # X_upcoming = upcoming[feature_cols].values  
        # Fill NaN with median from training data
        # probs = model.predict_proba(pd.DataFrame(X_upcoming, columns=feature_cols))
        # probs shape: (n_matches, 3) for [home, draw, away]
        #
        # Step 7: Build recommendations
        # For each match row i in upcoming:
        #   For each outcome j in [0=home, 1=draw, 2=away]:
        #     market_name = ["1x2_home", "1x2_draw", "1x2_away"][j]
        #     model_prob = probs[i, j]
        #     odds_col = ["avg_home", "avg_draw", "avg_away"][j]
        #     if odds_col in upcoming.columns and not pd.isna(upcoming.iloc[i][odds_col]):
        #       book_odds = upcoming.iloc[i][odds_col]
        #       book_prob = 1.0 / book_odds
        #       edge = model_prob - book_prob
        #       if edge > self._min_edge:
        #         kelly = max(0, (model_prob * book_odds - 1) / (book_odds - 1))
        #         kelly_adj = kelly * self._kelly_fraction
        #         kelly_adj = min(kelly_adj, 0.03)  # cap at 3% bankroll
        #         stake = kelly_adj * self._bankroll
        #         rec = BetRecommendation(
        #           match_id=upcoming.iloc[i]["game"],
        #           home_team=upcoming.iloc[i]["home_team"],
        #           away_team=upcoming.iloc[i]["away_team"],
        #           league=upcoming.iloc[i]["league"],
        #           kickoff=str(upcoming.iloc[i]["date"]),
        #           market=market_name,
        #           model_prob=round(model_prob, 4),
        #           bookmaker_prob=round(book_prob, 4),
        #           edge=round(edge, 4),
        #           min_odds=round(1.0 / model_prob, 2),
        #           kelly_fraction=round(kelly_adj, 4),
        #           stake_eur=round(stake, 2),
        #           model_agreement=1,  # single model for now
        #           best_bookmaker="avg_market",
        #           best_odds=round(book_odds, 2),
        #         )
        #         recommendations.append(rec)
        #
        # Step 8: Sort by edge descending
        # recommendations.sort(key=lambda r: r.edge, reverse=True)
        # return recommendations

    def save_predictions(
        self,
        predictions: list[BetRecommendation],
        output_dir: Path,
    ) -> Path:
        """Save predictions as JSON file.

        Args:
            predictions: List of recommendations.
            output_dir: Directory for output. Created if missing.

        Returns:
            Path to the saved JSON file.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        today = date.today().isoformat()
        path = output_dir / f"predictions_{today}.json"
        data = [asdict(p) for p in predictions]
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        logger.info("predictions_saved", path=str(path), count=len(predictions))
        return path

    @staticmethod
    def load_predictions(path: Path) -> list[BetRecommendation]:
        """Load predictions from JSON file.

        Args:
            path: Path to predictions JSON.

        Returns:
            List of BetRecommendation.
        """
        data = json.loads(path.read_text(encoding="utf-8"))
        return [BetRecommendation(**d) for d in data]
```

## 3. packages/ml-in-sports/src/ml_in_sports/cli/predict_cmd.py

```python
"""CLI command: sl predict run — generate daily bet recommendations."""

from __future__ import annotations

from pathlib import Path

import typer
import structlog

from ml_in_sports.prediction.daily import DailyPredictor

logger = structlog.get_logger(__name__)

predict_app = typer.Typer(help="Generate daily predictions.")


@predict_app.command("run")
def run(
    date: str = typer.Option(None, help="Target date YYYY-MM-DD. Default: today."),
    bankroll: float = typer.Option(5000.0, help="Current bankroll in EUR."),
    kelly_fraction: float = typer.Option(0.25, help="Kelly fraction (0.25 = quarter-Kelly)."),
    min_edge: float = typer.Option(0.02, help="Minimum edge to include (0.02 = 2%)."),
    model: str = typer.Option("lightgbm", help="Model type: lightgbm or xgboost."),
    output_dir: Path = typer.Option("predictions", help="Output directory for JSON."),
) -> None:
    """Generate bet recommendations for upcoming matches."""
    from datetime import date as date_cls

    target = date_cls.fromisoformat(date) if date else None

    predictor = DailyPredictor(
        model_type=model,
        bankroll=bankroll,
        kelly_fraction=kelly_fraction,
        min_edge=min_edge,
    )
    bets = predictor.predict(target_date=target)

    if not bets:
        logger.info("no_value_bets_found", date=str(target))
        typer.echo("Zero value bets found for this date.")
        return

    # Print summary
    total_stake = sum(b.stake_eur for b in bets)
    typer.echo(f"\n{len(bets)} value bets | Total stake: EUR {total_stake:.2f}")
    typer.echo("-" * 70)
    for i, b in enumerate(bets, 1):
        typer.echo(
            f"{i:2d}. {b.home_team} vs {b.away_team} | {b.league}\n"
            f"    {b.market} | Edge: {b.edge*100:+.1f}% | "
            f"Kelly: {b.kelly_fraction*100:.1f}% | EUR {b.stake_eur:.2f} | "
            f"@{b.best_odds:.2f}"
        )
    typer.echo("-" * 70)

    # Save
    path = predictor.save_predictions(bets, output_dir)
    typer.echo(f"Saved to: {path}")
```

## 4. Zarejestruj w cli/main.py

Otwórz `packages/ml-in-sports/src/ml_in_sports/cli/main.py`.
Na górze pliku, obok istniejących importów (np. `from ml_in_sports.cli.backtest_cmd import backtest_app`), dodaj:
```python
from ml_in_sports.cli.predict_cmd import predict_app
```

Niżej, obok istniejących `app.add_typer(...)`, dodaj:
```python
app.add_typer(predict_app, name="predict", help="Generate daily predictions.")
```

## 5. Testy: packages/ml-in-sports/tests/prediction/__init__.py

```python
"""Tests for prediction module."""
```

## 6. Testy: packages/ml-in-sports/tests/prediction/test_daily.py

```python
"""Tests for daily prediction pipeline."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ml_in_sports.prediction.daily import BetRecommendation, DailyPredictor


class TestBetRecommendation:
    """Tests for BetRecommendation dataclass."""

    def test_create_recommendation(self) -> None:
        rec = BetRecommendation(
            match_id="2024-04-06 Arsenal-Chelsea",
            home_team="Arsenal",
            away_team="Chelsea",
            league="ENG-Premier League",
            kickoff="2024-04-06 15:30:00",
            market="1x2_home",
            model_prob=0.55,
            bookmaker_prob=0.45,
            edge=0.10,
            min_odds=1.82,
            kelly_fraction=0.02,
            stake_eur=100.0,
            model_agreement=3,
            best_bookmaker="STS",
            best_odds=2.15,
        )
        assert rec.edge == 0.10
        assert rec.market == "1x2_home"

    def test_frozen(self) -> None:
        rec = BetRecommendation(
            match_id="x", home_team="A", away_team="B",
            league="L", kickoff="2024-01-01", market="1x2_home",
            model_prob=0.5, bookmaker_prob=0.4, edge=0.1,
            min_odds=2.0, kelly_fraction=0.01, stake_eur=50.0,
            model_agreement=1, best_bookmaker="X", best_odds=2.0,
        )
        with pytest.raises(AttributeError):
            rec.edge = 0.2  # type: ignore[misc]


class TestDailyPredictor:
    """Tests for DailyPredictor."""

    @pytest.fixture
    def fake_parquet(self, tmp_path: Path) -> Path:
        """Create a minimal fake parquet with history + upcoming."""
        rng = np.random.default_rng(42)
        n_history = 200
        n_upcoming = 10

        # History rows (have result)
        history = pd.DataFrame({
            "league": ["ENG-Premier League"] * n_history,
            "season": ["2324"] * n_history,
            "game": [f"2024-01-{i:02d} TeamA-TeamB" for i in range(n_history)],
            "date": pd.date_range("2024-01-01", periods=n_history, freq="D"),
            "home_team": ["TeamA"] * n_history,
            "away_team": ["TeamB"] * n_history,
            "result_1x2": rng.choice(["H", "D", "A"], n_history),
            "home_goals": rng.integers(0, 4, n_history),
            "away_goals": rng.integers(0, 3, n_history),
            "avg_home": rng.uniform(1.5, 3.5, n_history),
            "avg_draw": rng.uniform(2.5, 4.5, n_history),
            "avg_away": rng.uniform(2.0, 6.0, n_history),
            "feature_1": rng.normal(0, 1, n_history),
            "feature_2": rng.normal(0, 1, n_history),
            "feature_3": rng.normal(0, 1, n_history),
        })

        # Upcoming rows (no result)
        upcoming = pd.DataFrame({
            "league": ["ENG-Premier League"] * n_upcoming,
            "season": ["2425"] * n_upcoming,
            "game": [f"2025-04-{i+6:02d} TeamC-TeamD" for i in range(n_upcoming)],
            "date": pd.date_range("2025-04-06", periods=n_upcoming, freq="D"),
            "home_team": ["TeamC"] * n_upcoming,
            "away_team": ["TeamD"] * n_upcoming,
            "result_1x2": [None] * n_upcoming,
            "home_goals": [None] * n_upcoming,
            "away_goals": [None] * n_upcoming,
            "avg_home": rng.uniform(1.5, 3.5, n_upcoming),
            "avg_draw": rng.uniform(2.5, 4.5, n_upcoming),
            "avg_away": rng.uniform(2.0, 6.0, n_upcoming),
            "feature_1": rng.normal(0, 1, n_upcoming),
            "feature_2": rng.normal(0, 1, n_upcoming),
            "feature_3": rng.normal(0, 1, n_upcoming),
        })

        df = pd.concat([history, upcoming], ignore_index=True)
        path = tmp_path / "features.parquet"
        df.to_parquet(path)
        return path

    def test_predict_returns_list(self, fake_parquet: Path) -> None:
        predictor = DailyPredictor(parquet_path=fake_parquet, min_edge=0.0)
        bets = predictor.predict()
        assert isinstance(bets, list)

    def test_predict_filters_by_edge(self, fake_parquet: Path) -> None:
        predictor = DailyPredictor(parquet_path=fake_parquet, min_edge=0.50)
        bets = predictor.predict()
        # Very high min_edge should filter most/all
        for bet in bets:
            assert bet.edge >= 0.50

    def test_predict_sorted_by_edge_desc(self, fake_parquet: Path) -> None:
        predictor = DailyPredictor(parquet_path=fake_parquet, min_edge=0.0)
        bets = predictor.predict()
        if len(bets) >= 2:
            edges = [b.edge for b in bets]
            assert edges == sorted(edges, reverse=True)

    def test_kelly_fraction_applied(self, fake_parquet: Path) -> None:
        predictor = DailyPredictor(
            parquet_path=fake_parquet, kelly_fraction=0.25, min_edge=0.0,
        )
        bets = predictor.predict()
        for bet in bets:
            assert bet.kelly_fraction <= 0.03  # capped at 3% per bet
            assert bet.kelly_fraction >= 0.0

    def test_stake_matches_kelly_times_bankroll(self, fake_parquet: Path) -> None:
        bankroll = 10000.0
        predictor = DailyPredictor(
            parquet_path=fake_parquet, bankroll=bankroll, min_edge=0.0,
        )
        bets = predictor.predict()
        for bet in bets:
            expected_stake = bet.kelly_fraction * bankroll
            assert abs(bet.stake_eur - expected_stake) < 0.01

    def test_save_and_load_roundtrip(self, fake_parquet: Path, tmp_path: Path) -> None:
        predictor = DailyPredictor(parquet_path=fake_parquet, min_edge=0.0)
        bets = predictor.predict()
        if not bets:
            pytest.skip("No bets generated")

        path = predictor.save_predictions(bets, tmp_path / "preds")
        loaded = DailyPredictor.load_predictions(path)
        assert len(loaded) == len(bets)
        assert loaded[0].match_id == bets[0].match_id
        assert loaded[0].edge == bets[0].edge

    def test_empty_upcoming_returns_empty(self, tmp_path: Path) -> None:
        """Parquet with no upcoming matches → empty list."""
        df = pd.DataFrame({
            "league": ["ENG-Premier League"] * 50,
            "season": ["2324"] * 50,
            "game": [f"g{i}" for i in range(50)],
            "date": pd.date_range("2024-01-01", periods=50),
            "home_team": ["A"] * 50,
            "away_team": ["B"] * 50,
            "result_1x2": ["H"] * 50,  # all have results
            "home_goals": [1] * 50,
            "away_goals": [0] * 50,
            "avg_home": [2.0] * 50,
            "avg_draw": [3.5] * 50,
            "avg_away": [4.0] * 50,
            "feature_1": [0.5] * 50,
        })
        path = tmp_path / "no_upcoming.parquet"
        df.to_parquet(path)

        predictor = DailyPredictor(parquet_path=path)
        bets = predictor.predict()
        assert bets == []
```

# ZASADY

- Type hints na WSZYSTKIM (parametry + return types)
- Google docstrings na publicznych klasach/metodach
- `import structlog` + `logger = structlog.get_logger(__name__)` do logowania (NIE print())
- Frozen dataclasses (immutable)
- JSON serialization z obsługą datetime (użyj str() lub .isoformat())
- NIE modyfikuj plików w backtesting/, models/, processing/ — tylko twórz NOWE pliki w prediction/
- Jedyna modyfikacja istniejącego pliku: dodaj import + app.add_typer w cli/main.py

# WERYFIKACJA

```bash
uv run sl predict run --help          # powinno pokazać opcje
uv run ruff check packages/ml-in-sports --fix
uv run mypy packages
uv run pytest packages/ml-in-sports -q  # 1134+ testów musi przechodzić
```
```

---

## TASK-05: Bet Slip Reports — HTML + terminal + Telegram rendering

```
# KONTEKST

SportsLab ma daily predictor (TASK-04) który generuje list[BetRecommendation].
Teraz trzeba wyrenderować te rekomendacje w 3 formatach:
- HTML (self-contained, otwierany w przeglądarce)
- Terminal (Rich library, kolorowy output)
- Telegram (plain text markdown, max 4096 znaków)

Design system (te same tokeny co backtest report):
- Fonty: Inter (tekst), JetBrains Mono (liczby)
- Kolory brand: primary=#1B2A4A, accent=#2D7DD2, surface=#F7F8FA
- Kolory semantyczne: positive=#1A7F37, negative=#CF222E, neutral=#9A6700
- Muted text: #656D76

BetRecommendation dataclass (z TASK-04):
```python
@dataclass(frozen=True)
class BetRecommendation:
    match_id: str          # "2024-04-06 Arsenal-Chelsea"
    home_team: str         # "Arsenal"
    away_team: str         # "Chelsea"
    league: str            # "ENG-Premier League"
    kickoff: str           # "2024-04-06 15:30:00"
    market: str            # "1x2_home", "1x2_draw", "1x2_away"
    model_prob: float      # 0.5523
    bookmaker_prob: float  # 0.4545
    edge: float            # 0.0978 (model_prob - bookmaker_prob)
    min_odds: float        # 1.81
    kelly_fraction: float  # 0.021
    stake_eur: float       # 105.00
    model_agreement: int   # 1-3
    best_bookmaker: str    # "STS"
    best_odds: float       # 2.15
```

# CO STWORZYĆ

## 1. packages/ml-in-sports/src/ml_in_sports/prediction/report/__init__.py
```python
"""Bet slip and results report rendering."""
```

## 2. packages/ml-in-sports/src/ml_in_sports/prediction/report/html.py

Self-contained HTML z Jinja2. Struktura:

```html
<!DOCTYPE html>
<html>
<head>
  <title>SportsLab Daily Bet Slip — {{ date }}</title>
  <!-- Google Fonts: Inter + JetBrains Mono -->
  <!-- Inline CSS z brand tokenami (jak w backtesting/report/html.py) -->
</head>
<body>
<div class="container">
  <!-- Summary Card -->
  <div class="summary-card">
    <h1>Daily Bet Slip</h1>
    <div class="hero-grid">
      <div class="hero-card"><div class="hero-label">BETS</div><div class="hero-value">{{ n_bets }}</div></div>
      <div class="hero-card"><div class="hero-label">TOTAL STAKE</div><div class="hero-value">EUR {{ total_stake }}</div></div>
      <div class="hero-card"><div class="hero-label">BEST EDGE</div><div class="hero-value">{{ best_edge }}%</div></div>
    </div>
  </div>

  <!-- Bets Table -->
  <table>
    <thead>
      <tr><th>#</th><th>Match</th><th>League</th><th>Market</th><th>Edge</th><th>Kelly%</th><th>Stake</th><th>Odds</th></tr>
    </thead>
    <tbody>
      {% for bet in bets %}
      <tr>
        <td>{{ loop.index }}</td>
        <td>{{ bet.home_team }} vs {{ bet.away_team }}</td>
        <td>{{ bet.league }}</td>
        <td>{{ bet.market }}</td>
        <td style="color: #1A7F37">+{{ "%.1f"|format(bet.edge * 100) }}%</td>
        <td>{{ "%.1f"|format(bet.kelly_fraction * 100) }}%</td>
        <td>EUR {{ "%.2f"|format(bet.stake_eur) }}</td>
        <td>{{ "%.2f"|format(bet.best_odds) }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>

  <!-- Glossary -->
  <div class="glossary">
    <h3>Glossary</h3>
    <p><strong>Edge</strong>: Model probability minus bookmaker probability. Higher = more value.</p>
    <p><strong>Kelly%</strong>: Optimal bankroll fraction (quarter-Kelly). Capped at 3%.</p>
    <p><strong>Model Agreement</strong>: How many of 3 models see value (currently 1 model).</p>
  </div>
</div>
</body>
</html>
```

Implementuj jako:
```python
def render_bet_slip_html(
    bets: list[BetRecommendation],
    output_path: Path,
    date_str: str = "",
) -> Path:
    """Render bet slip as self-contained HTML."""
```

## 3. packages/ml-in-sports/src/ml_in_sports/prediction/report/terminal.py

```python
def print_bet_slip_terminal(bets: list[BetRecommendation]) -> None:
    """Print bet slip using Rich library."""
    # Use rich.table.Table, rich.console.Console
    # Columns: #, Match, League, Market, Edge (green), Kelly%, Stake, Odds
    # Summary line at top: "N bets | Total: EUR X"
    # Empty state: "Zero value bets found."
```

## 4. packages/ml-in-sports/src/ml_in_sports/prediction/report/telegram.py

```python
def format_bet_slip_telegram(bets: list[BetRecommendation]) -> str:
    """Format bet slip for Telegram (max 4096 chars).
    
    Format per bet (3 lines):
    1. {home} vs {away} | {league}
    2. {market} | Edge +{edge}% | K {kelly}% EUR {stake}
    3. @{odds} {bookmaker} | Models: {agreement}/3
    
    If > 20 bets: truncate to top 15, add "... + N more"
    
    Returns: plain text string, max 4096 characters.
    """
```

## 5. Testy: packages/ml-in-sports/tests/prediction/test_report.py

```python
"""Tests for bet slip report rendering."""

# Test HTML:
# - Contains "Daily Bet Slip" title
# - Contains summary card with bet count
# - Contains table with all bets
# - Contains glossary
# - Is valid HTML (starts with <!DOCTYPE)
# - Empty bets → contains "Zero" message

# Test Terminal:
# - Returns None (prints to stdout)
# - No exception on empty bets

# Test Telegram:
# - Returns string
# - Length < 4096
# - Contains match names
# - 30 bets → truncated, contains "more"
# - Empty bets → contains "Zero" or similar
```

## 6. Update cli/predict_cmd.py

Po generowaniu predictions, dodaj rendering:
```python
from ml_in_sports.prediction.report.terminal import print_bet_slip_terminal
from ml_in_sports.prediction.report.html import render_bet_slip_html

# After generating bets:
print_bet_slip_terminal(bets)
report_path = render_bet_slip_html(bets, Path("reports") / f"slip_{date}.html")
typer.echo(f"HTML report: {report_path}")
```

# ZASADY
- Self-contained HTML (inline CSS, Google Fonts CDN, NO external files)
- autoescape=False w Jinja2 (żeby Plotly HTML nie był escapowany)
- Rich library dla terminala (rich.table.Table, rich.console.Console)
- Telegram: pure text, max 4096 chars, truncate if needed
- NIE modyfikuj backtesting/report/ — twórz NOWE pliki w prediction/report/

# WERYFIKACJA
```bash
uv run ruff check packages/ml-in-sports --fix
uv run mypy packages
uv run pytest packages/ml-in-sports -q
```
```

---

## TASK-06: Results Tracker — log wyników zakładów

```
# KONTEKST

Po postawieniu zakładów (TASK-04/05) trzeba śledzić wyniki.
ResultsTracker ładuje predictions JSON, matchuje z faktycznymi wynikami meczów,
oblicza CLV i P&L per bet.

BetRecommendation: patrz TASK-04 (match_id, market, model_prob, stake_eur, best_odds).
Predictions JSON: {"predictions": [...]} w predictions/predictions_2024-04-06.json

# CO STWORZYĆ

## 1. packages/ml-in-sports/src/ml_in_sports/prediction/results.py

```python
"""Track bet results and compute daily P&L."""

@dataclass(frozen=True)
class BetResult:
    """Result of a placed bet.
    
    Attributes:
        recommendation: Original bet recommendation.
        actual_score: Match score e.g. "2-1".
        actual_result: "home", "draw", or "away".
        hit: Whether our bet was correct.
        closing_odds: Pinnacle/market closing odds (for CLV). None if unavailable.
        clv: Closing Line Value. model_prob - 1/closing_odds. None if no closing odds.
        pnl: Profit/loss in EUR. Win: stake * (odds - 1). Loss: -stake.
        bankroll_after: Running bankroll after this bet.
    """
    recommendation: BetRecommendation
    actual_score: str
    actual_result: str
    hit: bool
    closing_odds: float | None
    clv: float | None
    pnl: float
    bankroll_after: float


class ResultsTracker:
    """Track bet results across days.
    
    Loads predictions JSON, matches with actual results, computes P&L and CLV.
    
    Args:
        predictions_dir: Directory with predictions_YYYY-MM-DD.json files.
        results_dir: Directory with results_YYYY-MM-DD.json files (manual input).
        initial_bankroll: Starting bankroll for R3.
    """
    
    def __init__(
        self,
        predictions_dir: Path = Path("predictions"),
        results_dir: Path = Path("results"),
        initial_bankroll: float = 5000.0,
    ) -> None: ...
    
    def process_day(self, day: date) -> list[BetResult]:
        """Process results for a given day.
        
        1. Load predictions JSON for this day
        2. Load actual results (from results JSON or features parquet)
        3. Match predictions with results by match_id
        4. Compute hit/miss, P&L, CLV
        5. Save results JSON
        6. Return list of BetResult
        """
    
    def running_totals(self) -> dict[str, float]:
        """Compute cumulative stats across all tracked days.
        
        Returns dict with keys:
        - total_bets: int
        - wins: int  
        - losses: int
        - hit_rate: float (0-1)
        - total_pnl: float (EUR)
        - roi: float (total_pnl / total_staked)
        - mean_clv: float
        - current_bankroll: float
        - max_drawdown: float
        - current_streak: int (positive = winning, negative = losing)
        """
```

Actual results format (ręcznie tworzony JSON w results/ lub z parquet):
```json
// results/results_2024-04-06.json
[
  {"match_id": "2024-04-06 Arsenal-Chelsea", "score": "2-1", "result": "home"},
  {"match_id": "2024-04-06 Barcelona-Atletico", "score": "1-1", "result": "draw"}
]
```

P&L computation:
- Hit (market "1x2_home" and result "home"): pnl = stake * (odds - 1)
- Miss: pnl = -stake

## 2. packages/ml-in-sports/src/ml_in_sports/cli/results_cmd.py

```python
# sl results run --date 2024-04-06
# Loads predictions + results for that date, prints summary
```

Register in cli/main.py.

## 3. Tests: packages/ml-in-sports/tests/prediction/test_results.py

- BetResult creation from recommendation + actual
- P&L computation: hit → positive, miss → negative
- CLV computation with mock closing odds
- Running totals accumulation over 3 days
- Empty predictions for date → empty list
- Missing results file → warning, skip

# ZASADY
- Frozen dataclasses
- JSON persistence (predictions + results dirs)
- structlog logging
- Type hints, Google docstrings
- NIE modyfikuj prediction/daily.py — only import from it

# WERYFIKACJA
```bash
uv run sl results run --help
uv run ruff check packages/ml-in-sports --fix
uv run mypy packages
uv run pytest packages/ml-in-sports -q
```
```

---

## TASK-07: Results Reports — HTML + terminal + Telegram

```
# KONTEKST

ResultsTracker (TASK-06) produkuje list[BetResult]. Trzeba wyrenderować w 3 formatach.

BetResult fields: recommendation (BetRecommendation), actual_score, actual_result, hit (bool),
closing_odds, clv, pnl (EUR), bankroll_after.

Design: ten sam system co bet slip (Inter + JetBrains Mono, brand colors).
Kolorowanie: hit=True → zielone tło (#dcfce7), hit=False → czerwone tło (#fef2f2).

# CO STWORZYĆ

## 1. packages/ml-in-sports/src/ml_in_sports/prediction/report/results_html.py
- Summary card: W/L, P&L, CLV, bankroll
- Table: match, score, bet type, WIN/MISS (colored), odds, CLV, P&L, running bankroll
- Running totals section

## 2. packages/ml-in-sports/src/ml_in_sports/prediction/report/results_terminal.py  
- Rich table with colored WIN/MISS

## 3. packages/ml-in-sports/src/ml_in_sports/prediction/report/results_telegram.py
- TRAFIONE: + match @odds +EUR X
- PUDŁA: - match @odds -EUR X
- Summary line

## 4. Tests: packages/ml-in-sports/tests/prediction/test_results_report.py
- HTML has summary + table
- Terminal doesn't crash
- Telegram < 4096 chars
- Empty results → empty state message

# ZASADY & WERYFIKACJA
Same as TASK-05.
```

---

## TASK-08: Weekly Performance Report

```
# KONTEKST

Tygodniowy raport łączący daily results. Generowany w niedzielę.
ResultsTracker (TASK-06) ma running_totals(). Potrzebujemy aggregację per tydzień.

# CO STWORZYĆ

## 1. packages/ml-in-sports/src/ml_in_sports/prediction/weekly.py

```python
@dataclass
class WeeklyData:
    week_start: date
    week_end: date
    total_bets: int
    wins: int
    losses: int
    pnl: float
    bankroll_start: float
    bankroll_end: float
    clv_7d: float
    roi_7d: float
    daily_pnl: dict[str, float]  # "2024-04-01" → EUR +35.00
    per_league: list[dict]       # [{league, bets, wins, losses, pnl, roi, clv}]
    per_market: list[dict]       # [{market, bets, wins, losses, pnl, roi, clv}]
    best_bets: list[BetResult]   # top 3 by P&L
    worst_bets: list[BetResult]  # bottom 3 by P&L

class WeeklyReporter:
    def __init__(self, results_tracker: ResultsTracker) -> None: ...
    def generate(self, week_start: date) -> WeeklyData: ...
```

## 2. Report renderers:
- prediction/report/weekly_html.py — summary card + P&L bar chart (Plotly) + per-league table + per-market table
- prediction/report/weekly_terminal.py — Rich tables
- prediction/report/weekly_telegram.py — compact, < 4096 chars

## 3. CLI: packages/ml-in-sports/src/ml_in_sports/cli/weekly_cmd.py
```python
# sl weekly run --week 2024-04-01
```

## 4. Tests: packages/ml-in-sports/tests/prediction/test_weekly.py

# ZASADY & WERYFIKACJA
Same pattern as TASK-05/06/07.
```

---

## TASK-09: Telegram Bot

```
# KONTEKST

Telegram Bot API wysyła daily bet slips i results automatycznie.
Bot token i chat ID w env vars: ML_IN_SPORTS_TELEGRAM_BOT_TOKEN, ML_IN_SPORTS_TELEGRAM_CHAT_ID.

# CO STWORZYĆ

## 1. packages/ml-in-sports/src/ml_in_sports/notification/__init__.py
## 2. packages/ml-in-sports/src/ml_in_sports/notification/telegram.py

```python
import httpx
from ml_in_sports.settings import get_settings

class TelegramNotifier:
    def __init__(self) -> None:
        s = get_settings()
        self._token = s.telegram_bot_token
        self._chat_id = s.telegram_chat_id
        if not self._token or not self._chat_id:
            raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set")
    
    def send_message(self, text: str) -> bool:
        """POST to https://api.telegram.org/bot{token}/sendMessage"""
        url = f"https://api.telegram.org/bot{self._token}/sendMessage"
        resp = httpx.post(url, json={
            "chat_id": self._chat_id,
            "text": text[:4096],
            "parse_mode": "Markdown",
        })
        return resp.status_code == 200
```

## 3. Dodaj do settings.py:
```python
telegram_bot_token: str = ""
telegram_chat_id: str = ""
```

## 4. Dodaj httpx do deps:
W packages/ml-in-sports/pyproject.toml [project].dependencies dodaj:
```
"httpx>=0.27,<1.0",
```

## 5. CLI: packages/ml-in-sports/src/ml_in_sports/cli/notify_cmd.py
```python
# sl notify bet-slip --date 2024-04-06
# sl notify results --date 2024-04-06
```

## 6. Tests (MOCK httpx, zero prawdziwych API calls):
- Mock httpx.post → return 200
- Message < 4096 chars
- Missing token → ValueError
- Network error → return False

# WERYFIKACJA
```bash
uv run ruff check packages/ml-in-sports --fix
uv run mypy packages
uv run pytest packages/ml-in-sports -q
```
```

---

## TASK-10: STS Odds Scraper

```
# KONTEKST

Scraper kursów z STS.pl dla upcoming meczów. Używa requests + BeautifulSoup.
Rate limit: 1 request per 3 sekundy.

# CO STWORZYĆ

## 1. packages/ml-in-sports/src/ml_in_sports/processing/scrapers/__init__.py
## 2. packages/ml-in-sports/src/ml_in_sports/processing/scrapers/sts.py

```python
@dataclass(frozen=True)
class OddsSnapshot:
    bookmaker: str          # "STS"
    match_id: str           # "2024-04-06 Arsenal-Chelsea"
    home_team: str
    away_team: str
    league: str
    kickoff: datetime
    market: str             # "1x2_home"
    odds: float             # 2.15
    scraped_at: datetime

class StsScraper:
    def __init__(self, rate_limit_seconds: float = 3.0) -> None: ...
    def scrape_upcoming(self, leagues: list[str] | None = None) -> list[OddsSnapshot]: ...
```

UWAGA: Nie wiem jaka jest aktualna struktura HTML STS.pl. 
Stwórz PLACEHOLDER implementację:
- scrape_upcoming() próbuje requests.get("https://www.sts.pl/pl/oferta/pilka-nozna/")  
- Jeśli się uda — parsuje z BeautifulSoup
- Jeśli się nie uda (lub HTML się zmienił) — loguje warning, return []
- Rate limiting via time.sleep()

## 3. Testy z FIXTURE HTML (zero live requests):
Stwórz tests/fixtures/sts_sample.html z minimalnym fragmentem HTML
i testuj parsowanie na tym.

# WERYFIKACJA
Same as above.
```

---

## Kolejność wykonania

```
Niezależne (równolegle):
  TASK-10 (STS scraper)

Sekwencyjne:
  TASK-04 (predictor) 
    → TASK-05 (bet slip reports)
    → TASK-06 (results tracker)
      → TASK-07 (results reports)
      → TASK-08 (weekly report)
    → TASK-09 (telegram bot) — wymaga TASK-05 + TASK-06
```
