"""Tests for BacktestDataLoader.

Uses synthetic 100-row parquet files created in tmp_path fixtures.
Does NOT use the real 45MB features parquet (too slow for CI).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from ml_in_sports.backtesting.data import BacktestDataLoader

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _create_synthetic_parquet(
    path: Path,
    n_rows: int = 100,
    n_features: int = 10,
    seed: int = 42,
) -> Path:
    """Create a minimal synthetic parquet mimicking the real schema.

    Returns the path to the created parquet file.
    """
    rng = np.random.default_rng(seed)

    leagues = ["ENG-Premier League", "ESP-La Liga"]
    seasons = ["2122", "2223", "2324"]
    results = ["H", "D", "A"]

    data: dict[str, object] = {
        "id": np.arange(n_rows),
        "league": rng.choice(leagues, size=n_rows),
        "season": rng.choice(seasons, size=n_rows),
        "game": [f"Game_{i}" for i in range(n_rows)],
        "date": pd.date_range("2022-01-01", periods=n_rows, freq="D"),
        "home_team": [f"Team_H_{i}" for i in range(n_rows)],
        "away_team": [f"Team_A_{i}" for i in range(n_rows)],
        "home_goals": rng.integers(0, 5, size=n_rows).astype(float),
        "away_goals": rng.integers(0, 5, size=n_rows).astype(float),
        "result_1x2": rng.choice(results, size=n_rows),
        # Odds columns
        "b365_home": rng.uniform(1.2, 5.0, size=n_rows),
        "b365_draw": rng.uniform(2.5, 5.0, size=n_rows),
        "b365_away": rng.uniform(1.5, 8.0, size=n_rows),
        "avg_home": rng.uniform(1.2, 5.0, size=n_rows),
        "avg_draw": rng.uniform(2.5, 5.0, size=n_rows),
        "avg_away": rng.uniform(1.5, 8.0, size=n_rows),
    }

    # Add numeric feature columns
    for i in range(n_features):
        data[f"feature_{i}"] = rng.standard_normal(n_rows)

    # Add a column with >50% NaN (should be dropped)
    high_nan_col = rng.standard_normal(n_rows)
    high_nan_col[: int(n_rows * 0.6)] = np.nan
    data["feature_high_nan"] = high_nan_col

    # Add a column with some NaN (<50%, should be filled)
    partial_nan_col = rng.standard_normal(n_rows)
    partial_nan_col[:10] = np.nan
    data["feature_partial_nan"] = partial_nan_col

    df = pd.DataFrame(data)
    df.to_parquet(path)
    return path


@pytest.fixture
def synthetic_parquet(tmp_path: Path) -> Path:
    """Create a synthetic parquet file for testing."""
    return _create_synthetic_parquet(tmp_path / "test_features.parquet")


@pytest.fixture
def loader(synthetic_parquet: Path) -> BacktestDataLoader:
    """Create a BacktestDataLoader pointed at the synthetic parquet."""
    return BacktestDataLoader(parquet_path=synthetic_parquet)


@pytest.fixture
def parquet_with_nan_targets(tmp_path: Path) -> Path:
    """Create parquet where some rows have NaN target."""
    rng = np.random.default_rng(99)
    n_rows = 50
    results = list(rng.choice(["H", "D", "A"], size=n_rows - 5))
    # Add 5 NaN targets (future matches)
    results.extend([None] * 5)

    data: dict[str, object] = {
        "id": np.arange(n_rows),
        "league": ["ENG-Premier League"] * n_rows,
        "season": ["2324"] * n_rows,
        "game": [f"Game_{i}" for i in range(n_rows)],
        "date": pd.date_range("2023-08-01", periods=n_rows, freq="D"),
        "home_team": [f"H_{i}" for i in range(n_rows)],
        "away_team": [f"A_{i}" for i in range(n_rows)],
        "home_goals": rng.integers(0, 4, size=n_rows).astype(float),
        "away_goals": rng.integers(0, 4, size=n_rows).astype(float),
        "result_1x2": results,
        "avg_home": rng.uniform(1.5, 4.0, size=n_rows),
        "avg_draw": rng.uniform(3.0, 4.5, size=n_rows),
        "avg_away": rng.uniform(2.0, 6.0, size=n_rows),
        "feature_a": rng.standard_normal(n_rows),
        "feature_b": rng.standard_normal(n_rows),
    }
    path = tmp_path / "nan_target.parquet"
    pd.DataFrame(data).to_parquet(path)
    return path


# ---------------------------------------------------------------------------
# BacktestDataLoader.load() tests
# ---------------------------------------------------------------------------


class TestBacktestDataLoaderLoad:
    """Tests for data loading and preparation."""

    def test_load_returns_dataframe(self, loader: BacktestDataLoader) -> None:
        """load() returns a non-empty pandas DataFrame."""
        df = loader.load()
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_load_creates_target_column(self, loader: BacktestDataLoader) -> None:
        """load() creates an integer 'target' column."""
        df = loader.load()
        assert "target" in df.columns
        assert df["target"].dtype in (np.int32, np.int64)

    def test_target_encoding_values(self, loader: BacktestDataLoader) -> None:
        """Target values are 0 (Home), 1 (Draw), 2 (Away)."""
        df = loader.load()
        unique_targets = set(df["target"].unique())
        assert unique_targets.issubset({0, 1, 2})

    def test_load_filters_by_league(self, loader: BacktestDataLoader) -> None:
        """Filtering by league returns only matching rows."""
        df = loader.load(leagues=["ENG-Premier League"])
        assert all(df["league"] == "ENG-Premier League")

    def test_load_filters_by_season(self, loader: BacktestDataLoader) -> None:
        """Filtering by season returns only matching rows."""
        df = loader.load(seasons=["2223"])
        assert all(df["season"] == "2223")

    def test_load_sorted_by_date(self, loader: BacktestDataLoader) -> None:
        """Loaded data is sorted by date within each season."""
        df = loader.load()
        for _season, group in df.groupby("season"):
            dates = group["date"].values
            assert np.all(dates[:-1] <= dates[1:])

    def test_missing_parquet_raises(self, tmp_path: Path) -> None:
        """FileNotFoundError when parquet does not exist."""
        loader = BacktestDataLoader(parquet_path=tmp_path / "nonexistent.parquet")
        with pytest.raises(FileNotFoundError, match="not found"):
            loader.load()


class TestBacktestDataLoaderNanHandling:
    """Tests for NaN handling in data loading."""

    def test_nan_targets_dropped(self, parquet_with_nan_targets: Path) -> None:
        """Rows with NaN target are dropped during loading."""
        loader = BacktestDataLoader(parquet_path=parquet_with_nan_targets)
        df = loader.load()
        assert df["target"].isna().sum() == 0
        # Original had 50 rows, 5 with NaN target
        assert len(df) == 45

    def test_high_nan_columns_dropped(
        self, synthetic_parquet: Path
    ) -> None:
        """Columns with >50% NaN are excluded from features."""
        loader = BacktestDataLoader(parquet_path=synthetic_parquet)
        loader.load()
        feature_cols = loader.get_feature_columns()
        assert "feature_high_nan" not in feature_cols

    def test_partial_nan_columns_filled(
        self, synthetic_parquet: Path
    ) -> None:
        """Columns with <50% NaN are kept and filled with median."""
        loader = BacktestDataLoader(parquet_path=synthetic_parquet)
        df = loader.load()
        feature_cols = loader.get_feature_columns()
        assert "feature_partial_nan" in feature_cols
        assert df["feature_partial_nan"].isna().sum() == 0

    def test_no_nan_in_features(self, loader: BacktestDataLoader) -> None:
        """After loading, no feature columns contain NaN."""
        df = loader.load()
        feature_cols = loader.get_feature_columns()
        assert df[feature_cols].isna().sum().sum() == 0


# ---------------------------------------------------------------------------
# Feature column selection tests
# ---------------------------------------------------------------------------


class TestFeatureColumnSelection:
    """Tests for automatic feature column selection."""

    def test_feature_columns_excludes_meta(
        self, loader: BacktestDataLoader
    ) -> None:
        """Feature columns do not include metadata columns."""
        loader.load()
        feature_cols = set(loader.get_feature_columns())
        for meta_col in ["id", "league", "season", "game", "date",
                         "home_team", "away_team", "home_goals",
                         "away_goals", "result_1x2"]:
            assert meta_col not in feature_cols

    def test_feature_columns_excludes_odds(
        self, loader: BacktestDataLoader
    ) -> None:
        """Feature columns do not include odds columns."""
        loader.load()
        feature_cols = set(loader.get_feature_columns())
        for odds_col in ["b365_home", "b365_draw", "b365_away",
                         "avg_home", "avg_draw", "avg_away"]:
            assert odds_col not in feature_cols

    def test_feature_columns_excludes_target(
        self, loader: BacktestDataLoader
    ) -> None:
        """Feature columns do not include the encoded target."""
        loader.load()
        feature_cols = set(loader.get_feature_columns())
        assert "target" not in feature_cols

    def test_feature_columns_includes_features(
        self, loader: BacktestDataLoader
    ) -> None:
        """Feature columns include the synthetic feature_N columns."""
        loader.load()
        feature_cols = set(loader.get_feature_columns())
        for i in range(10):
            assert f"feature_{i}" in feature_cols

    def test_get_feature_columns_before_load_raises(
        self, synthetic_parquet: Path
    ) -> None:
        """Calling get_feature_columns() before load() raises RuntimeError."""
        loader = BacktestDataLoader(parquet_path=synthetic_parquet)
        with pytest.raises(RuntimeError, match="Call load\\(\\) first"):
            loader.get_feature_columns()


# ---------------------------------------------------------------------------
# Fold splitting tests
# ---------------------------------------------------------------------------


class TestFoldSplitting:
    """Tests for train/test fold data extraction."""

    def test_fold_data_shapes(self, loader: BacktestDataLoader) -> None:
        """Fold data has consistent shapes between X and y."""
        df = loader.load()
        x_train, y_train, x_test, y_test, _ = loader.get_fold_data(
            df, train_seasons=["2122"], test_seasons=["2223"]
        )
        assert len(x_train) == len(y_train)
        assert len(x_test) == len(y_test)
        assert x_train.shape[1] == x_test.shape[1]

    def test_fold_data_no_season_overlap(
        self, loader: BacktestDataLoader
    ) -> None:
        """Train and test data contain distinct seasons."""
        df = loader.load()
        # We need to check the actual data, not just the inputs
        train_seasons = ["2122"]
        test_seasons = ["2324"]
        x_train, _, x_test, _, _ = loader.get_fold_data(
            df, train_seasons=train_seasons, test_seasons=test_seasons
        )
        assert len(x_train) > 0
        assert len(x_test) > 0

    def test_fold_data_returns_odds(self, loader: BacktestDataLoader) -> None:
        """Fold data includes closing odds when available."""
        df = loader.load()
        _, _, _, _, test_odds = loader.get_fold_data(
            df, train_seasons=["2122"], test_seasons=["2223"]
        )
        assert test_odds is not None
        assert test_odds.shape[1] == 3  # avg_home, avg_draw, avg_away

    def test_fold_data_feature_columns_match(
        self, loader: BacktestDataLoader
    ) -> None:
        """Train and test DataFrames have the same feature columns."""
        df = loader.load()
        x_train, _, x_test, _, _ = loader.get_fold_data(
            df, train_seasons=["2122"], test_seasons=["2223"]
        )
        assert list(x_train.columns) == list(x_test.columns)
        assert list(x_train.columns) == loader.get_feature_columns()

    def test_fold_data_empty_train_raises(
        self, loader: BacktestDataLoader
    ) -> None:
        """ValueError when train seasons yield no data."""
        df = loader.load()
        with pytest.raises(ValueError, match="No training data"):
            loader.get_fold_data(
                df, train_seasons=["9999"], test_seasons=["2223"]
            )

    def test_fold_data_empty_test_raises(
        self, loader: BacktestDataLoader
    ) -> None:
        """ValueError when test seasons yield no data."""
        df = loader.load()
        with pytest.raises(ValueError, match="No test data"):
            loader.get_fold_data(
                df, train_seasons=["2122"], test_seasons=["9999"]
            )

    def test_fold_target_values_valid(
        self, loader: BacktestDataLoader
    ) -> None:
        """Target arrays contain only valid class indices."""
        df = loader.load()
        _, y_train, _, y_test, _ = loader.get_fold_data(
            df, train_seasons=["2122"], test_seasons=["2223"]
        )
        assert set(np.unique(y_train)).issubset({0, 1, 2})
        assert set(np.unique(y_test)).issubset({0, 1, 2})


# ---------------------------------------------------------------------------
# Pinnacle odds integration tests (SPO-60)
# ---------------------------------------------------------------------------

# Minimal CSV content with Pinnacle closing odds (PSCH/PSCD/PSCA).
_PINNACLE_CSV_CONTENT = (
    "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR,"
    "PSCH,PSCD,PSCA,MaxCH,MaxCD,MaxCA\n"
)


def _build_pinnacle_csv_rows(
    rows: list[tuple[str, str, str, float, float, float]],
) -> str:
    """Build CSV content from (date, home, away, psh, psd, psa) tuples.

    Max market odds are set to Pinnacle + 0.05 for simplicity.
    """
    lines = [_PINNACLE_CSV_CONTENT.rstrip("\n")]
    for date_str, home, away, psh, psd, psa in rows:
        lines.append(
            f"E0,{date_str},{home},{away},2,1,H,"
            f"{psh:.2f},{psd:.2f},{psa:.2f},"
            f"{psh + 0.05:.2f},{psd + 0.05:.2f},{psa + 0.05:.2f}"
        )
    return "\n".join(lines) + "\n"


def _create_parquet_with_known_teams(
    path: Path,
    teams: list[tuple[str, str]],
    season: str = "2324",
    league: str = "ENG-Premier League",
    seed: int = 42,
) -> Path:
    """Create a parquet where home/away teams are known.

    Each (home, away) pair becomes one row.
    """
    rng = np.random.default_rng(seed)
    n_rows = len(teams)

    data: dict[str, object] = {
        "id": np.arange(n_rows),
        "league": [league] * n_rows,
        "season": [season] * n_rows,
        "game": [f"Game_{i}" for i in range(n_rows)],
        "date": pd.date_range("2023-08-15", periods=n_rows, freq="7D"),
        "home_team": [t[0] for t in teams],
        "away_team": [t[1] for t in teams],
        "home_goals": rng.integers(0, 4, size=n_rows).astype(float),
        "away_goals": rng.integers(0, 4, size=n_rows).astype(float),
        "result_1x2": rng.choice(["H", "D", "A"], size=n_rows),
        "avg_home": rng.uniform(1.3, 4.0, size=n_rows),
        "avg_draw": rng.uniform(3.0, 4.5, size=n_rows),
        "avg_away": rng.uniform(2.0, 6.0, size=n_rows),
        "feature_x": rng.standard_normal(n_rows),
        "feature_y": rng.standard_normal(n_rows),
    }
    df = pd.DataFrame(data)
    df.to_parquet(path)
    return path


class TestPinnacleOddsIntegration:
    """Tests for Pinnacle closing odds merge in BacktestDataLoader."""

    def test_pinnacle_odds_preferred_over_avg(
        self, tmp_path: Path
    ) -> None:
        """When Pinnacle data exists, closing odds come from Pinnacle."""
        # Arrange: parquet with canonical names
        teams = [("Arsenal", "Chelsea"), ("Liverpool", "Everton")]
        parquet_path = _create_parquet_with_known_teams(
            tmp_path / "features.parquet",
            teams=teams,
            season="2324",
        )

        # Arrange: Pinnacle CSV with matching teams
        odds_dir = tmp_path / "odds"
        e0_dir = odds_dir / "E0"
        e0_dir.mkdir(parents=True)
        csv_content = _build_pinnacle_csv_rows([
            ("15/08/2023", "Arsenal", "Chelsea", 1.50, 4.20, 6.00),
            ("22/08/2023", "Liverpool", "Everton", 1.40, 4.50, 7.50),
        ])
        (e0_dir / "2324.csv").write_text(csv_content, encoding="utf-8")

        # Act
        loader = BacktestDataLoader(
            parquet_path=parquet_path,
            pinnacle_odds_dir=odds_dir,
        )
        df = loader.load(seasons=["2324"])
        _, _, _, _, test_odds = loader.get_fold_data(
            df, train_seasons=["2324"], test_seasons=["2324"],
        )

        # Assert: odds should be Pinnacle values, not avg_*
        assert test_odds is not None
        assert test_odds.shape == (2, 3)
        # First match: Arsenal vs Chelsea -> 1.50, 4.20, 6.00
        assert test_odds[0, 0] == pytest.approx(1.50, abs=0.01)
        assert test_odds[0, 1] == pytest.approx(4.20, abs=0.01)
        assert test_odds[0, 2] == pytest.approx(6.00, abs=0.01)

    def test_fallback_to_avg_when_no_pinnacle_dir(
        self, tmp_path: Path
    ) -> None:
        """Without pinnacle_odds_dir, avg_* odds are used."""
        # Arrange
        teams = [("Arsenal", "Chelsea")]
        parquet_path = _create_parquet_with_known_teams(
            tmp_path / "features.parquet",
            teams=teams,
            season="2324",
        )

        # Act: no pinnacle_odds_dir
        loader = BacktestDataLoader(parquet_path=parquet_path)
        df = loader.load(seasons=["2324"])
        _, _, _, _, test_odds = loader.get_fold_data(
            df, train_seasons=["2324"], test_seasons=["2324"],
        )

        # Assert: should still have odds (from avg_*)
        assert test_odds is not None
        assert test_odds.shape == (1, 3)

    def test_fallback_to_avg_when_pinnacle_dir_empty(
        self, tmp_path: Path
    ) -> None:
        """Empty Pinnacle directory triggers avg_* fallback."""
        teams = [("Arsenal", "Chelsea")]
        parquet_path = _create_parquet_with_known_teams(
            tmp_path / "features.parquet",
            teams=teams,
            season="2324",
        )
        odds_dir = tmp_path / "odds"
        odds_dir.mkdir()

        loader = BacktestDataLoader(
            parquet_path=parquet_path,
            pinnacle_odds_dir=odds_dir,
        )
        df = loader.load(seasons=["2324"])
        _, _, _, _, test_odds = loader.get_fold_data(
            df, train_seasons=["2324"], test_seasons=["2324"],
        )

        # Should fall back to avg_*
        assert test_odds is not None
        assert test_odds.shape == (1, 3)

    def test_fallback_to_avg_when_pinnacle_dir_missing(
        self, tmp_path: Path
    ) -> None:
        """Non-existent Pinnacle directory triggers avg_* fallback."""
        teams = [("Arsenal", "Chelsea")]
        parquet_path = _create_parquet_with_known_teams(
            tmp_path / "features.parquet",
            teams=teams,
            season="2324",
        )

        loader = BacktestDataLoader(
            parquet_path=parquet_path,
            pinnacle_odds_dir=tmp_path / "nonexistent",
        )
        df = loader.load(seasons=["2324"])
        _, _, _, _, test_odds = loader.get_fold_data(
            df, train_seasons=["2324"], test_seasons=["2324"],
        )

        assert test_odds is not None
        assert test_odds.shape == (1, 3)

    def test_team_name_normalization_in_merge(
        self, tmp_path: Path
    ) -> None:
        """Football-data 'Nott'm Forest' matches parquet 'Nottingham Forest'."""
        # Parquet uses canonical names
        teams = [("Nottingham Forest", "Manchester City")]
        parquet_path = _create_parquet_with_known_teams(
            tmp_path / "features.parquet",
            teams=teams,
            season="2324",
        )

        # CSV uses football-data.co.uk short names
        odds_dir = tmp_path / "odds"
        e0_dir = odds_dir / "E0"
        e0_dir.mkdir(parents=True)
        csv_content = _build_pinnacle_csv_rows([
            ("15/08/2023", "Nott'm Forest", "Man City", 3.50, 3.40, 2.10),
        ])
        (e0_dir / "2324.csv").write_text(csv_content, encoding="utf-8")

        loader = BacktestDataLoader(
            parquet_path=parquet_path,
            pinnacle_odds_dir=odds_dir,
        )
        df = loader.load(seasons=["2324"])
        _, _, _, _, test_odds = loader.get_fold_data(
            df, train_seasons=["2324"], test_seasons=["2324"],
        )

        assert test_odds is not None
        # Should have matched via normalization
        assert test_odds[0, 0] == pytest.approx(3.50, abs=0.01)

    def test_partial_match_uses_avg_fallback_for_unmatched(
        self, tmp_path: Path
    ) -> None:
        """Unmatched rows fall back to avg_* while matched use Pinnacle."""
        # Two matches: one matchable, one not
        teams = [("Arsenal", "Chelsea"), ("UnknownTeamA", "UnknownTeamB")]
        parquet_path = _create_parquet_with_known_teams(
            tmp_path / "features.parquet",
            teams=teams,
            season="2324",
        )

        odds_dir = tmp_path / "odds"
        e0_dir = odds_dir / "E0"
        e0_dir.mkdir(parents=True)
        csv_content = _build_pinnacle_csv_rows([
            ("15/08/2023", "Arsenal", "Chelsea", 1.50, 4.20, 6.00),
        ])
        (e0_dir / "2324.csv").write_text(csv_content, encoding="utf-8")

        loader = BacktestDataLoader(
            parquet_path=parquet_path,
            pinnacle_odds_dir=odds_dir,
        )
        df = loader.load(seasons=["2324"])
        _, _, _, _, test_odds = loader.get_fold_data(
            df, train_seasons=["2324"], test_seasons=["2324"],
        )

        assert test_odds is not None
        assert test_odds.shape == (2, 3)
        # First row: Pinnacle
        assert test_odds[0, 0] == pytest.approx(1.50, abs=0.01)
        # Second row: avg_* fallback (not NaN)
        assert np.isfinite(test_odds[1, 0])

    def test_pinnacle_cols_excluded_from_features(
        self, tmp_path: Path
    ) -> None:
        """Pinnacle odds columns never appear in the feature list."""
        teams = [("Arsenal", "Chelsea")]
        parquet_path = _create_parquet_with_known_teams(
            tmp_path / "features.parquet",
            teams=teams,
            season="2324",
        )

        loader = BacktestDataLoader(parquet_path=parquet_path)
        loader.load(seasons=["2324"])
        feature_cols = set(loader.get_feature_columns())

        assert "pinnacle_home" not in feature_cols
        assert "pinnacle_draw" not in feature_cols
        assert "pinnacle_away" not in feature_cols
