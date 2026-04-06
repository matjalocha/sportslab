"""Tests for tactical and efficiency rolling features."""

import pandas as pd
import pytest
from ml_in_sports.features.tactical_features import (
    add_tactical_features,
    compute_momentum_features,
    compute_ratio_rolling_features,
    compute_raw_tactical_rolling_features,
)


def _build_tactical_matches() -> pd.DataFrame:
    """Build a realistic fixture list with tactical columns.

    Creates 12 matches for 4 teams (6 matches each) so that
    rolling windows of 3 and 5 can be tested.
    """
    matches = [
        ("2024-01-01", "Arsenal", "Chelsea", 2, 1, 1.8, 0.9),
        ("2024-01-01", "Liverpool", "Everton", 1, 0, 1.2, 0.5),
        ("2024-01-15", "Chelsea", "Liverpool", 0, 2, 0.7, 1.5),
        ("2024-01-15", "Everton", "Arsenal", 1, 3, 0.9, 2.1),
        ("2024-02-01", "Arsenal", "Liverpool", 1, 1, 1.3, 1.2),
        ("2024-02-01", "Chelsea", "Everton", 3, 0, 2.2, 0.4),
        ("2024-02-15", "Liverpool", "Arsenal", 2, 0, 1.7, 0.8),
        ("2024-02-15", "Everton", "Chelsea", 1, 2, 0.6, 1.4),
        ("2024-03-01", "Arsenal", "Everton", 4, 0, 3.1, 0.3),
        ("2024-03-01", "Liverpool", "Chelsea", 1, 1, 1.1, 1.0),
        ("2024-03-15", "Chelsea", "Arsenal", 1, 2, 0.9, 1.6),
        ("2024-03-15", "Everton", "Liverpool", 0, 3, 0.4, 2.3),
    ]
    columns = [
        "date", "home_team", "away_team",
        "home_goals", "away_goals", "home_xg", "away_xg",
    ]
    df = pd.DataFrame(matches, columns=columns)
    df["league"] = "ENG-Premier League"
    df["season"] = "2324"

    df["home_ppda"] = [10.5, 12.0, 8.3, 14.0, 11.0, 9.5, 13.0, 15.0, 10.0, 11.5, 8.0, 16.0]
    df["away_ppda"] = [8.3, 9.1, 11.0, 10.2, 12.5, 14.0, 9.0, 8.5, 13.5, 10.0, 11.5, 9.5]
    df["home_possession"] = [62.0, 55.0, 45.0, 40.0, 58.0, 60.0, 52.0, 38.0, 65.0, 50.0, 48.0, 35.0]
    df["away_possession"] = [38.0, 45.0, 55.0, 60.0, 42.0, 40.0, 48.0, 62.0, 35.0, 50.0, 52.0, 65.0]
    df["home_deep_completions"] = [5, 3, 2, 1, 4, 6, 3, 1, 7, 2, 3, 0]
    df["away_deep_completions"] = [2, 1, 4, 5, 3, 0, 4, 5, 0, 3, 5, 6]
    df["home_total_shots"] = [15, 10, 8, 6, 12, 18, 11, 5, 20, 9, 10, 4]
    df["away_total_shots"] = [8, 5, 12, 16, 10, 4, 14, 12, 3, 10, 15, 14]
    df["home_shots_on_target"] = [5, 3, 2, 2, 4, 7, 4, 1, 8, 3, 3, 1]
    df["away_shots_on_target"] = [3, 1, 4, 6, 4, 1, 5, 4, 0, 3, 6, 5]
    df["home_accurate_passes"] = [450, 380, 310, 260, 420, 440, 360, 240, 480, 350, 330, 220]
    df["away_accurate_passes"] = [280, 300, 390, 430, 300, 250, 340, 430, 210, 350, 380, 450]
    df["home_total_passes"] = [550, 480, 420, 360, 530, 540, 460, 340, 580, 450, 430, 320]
    df["away_total_passes"] = [380, 400, 500, 540, 400, 350, 440, 540, 300, 450, 480, 560]
    df["home_accurate_crosses"] = [8, 5, 3, 2, 7, 9, 4, 1, 10, 4, 5, 1]
    df["away_accurate_crosses"] = [3, 2, 6, 7, 4, 1, 6, 8, 1, 5, 7, 9]
    df["home_total_crosses"] = [20, 15, 10, 8, 18, 22, 12, 5, 25, 12, 14, 4]
    df["away_total_crosses"] = [10, 8, 16, 18, 12, 6, 17, 20, 5, 14, 18, 22]
    df["home_accurate_long_balls"] = [12, 8, 6, 4, 10, 14, 7, 3, 16, 6, 8, 2]
    df["away_accurate_long_balls"] = [5, 4, 9, 10, 6, 3, 8, 12, 2, 7, 10, 14]
    df["home_total_long_balls"] = [25, 18, 14, 10, 22, 28, 16, 8, 32, 14, 18, 6]
    df["away_total_long_balls"] = [12, 10, 20, 22, 14, 8, 18, 26, 6, 16, 22, 28]
    df["home_effective_tackles"] = [12, 10, 14, 8, 11, 13, 9, 7, 14, 10, 15, 6]
    df["away_effective_tackles"] = [14, 8, 10, 12, 9, 7, 13, 13, 6, 11, 12, 10]
    df["home_total_tackles"] = [18, 15, 20, 12, 17, 19, 14, 10, 20, 15, 22, 9]
    df["away_total_tackles"] = [20, 12, 15, 18, 14, 10, 19, 18, 9, 16, 17, 15]
    df["home_effective_clearance"] = [8, 6, 10, 5, 7, 9, 5, 4, 10, 7, 12, 3]
    df["away_effective_clearance"] = [10, 4, 7, 8, 6, 3, 9, 10, 3, 8, 9, 7]
    df["home_total_clearance"] = [12, 10, 15, 8, 11, 13, 8, 6, 14, 10, 16, 5]
    df["away_total_clearance"] = [15, 7, 11, 12, 9, 5, 13, 14, 5, 12, 13, 10]
    df["home_blocked_shots"] = [2, 1, 3, 4, 2, 1, 3, 3, 1, 2, 4, 3]
    df["away_blocked_shots"] = [3, 2, 2, 3, 3, 4, 2, 1, 5, 2, 2, 1]
    df["home_saves"] = [2, 1, 4, 5, 3, 1, 4, 3, 0, 2, 5, 4]
    df["away_saves"] = [3, 2, 1, 4, 3, 5, 2, 0, 6, 2, 1, 0]
    df["home_interceptions"] = [10, 8, 12, 6, 9, 11, 7, 5, 12, 8, 14, 4]
    df["away_interceptions"] = [12, 6, 8, 10, 7, 5, 11, 12, 4, 9, 10, 8]
    df["home_penalty_kick_goals"] = [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0]
    df["away_penalty_kick_goals"] = [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0]
    df["home_penalty_kick_shots"] = [0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0]
    df["away_penalty_kick_shots"] = [0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0]

    return df


def _build_two_season_tactical() -> pd.DataFrame:
    """Build tactical matches across two seasons for boundary tests."""
    season_1 = _build_tactical_matches().head(6).copy()
    season_1["season"] = "2223"
    season_1["date"] = [
        "2023-04-01", "2023-04-01", "2023-04-15",
        "2023-04-15", "2023-05-01", "2023-05-01",
    ]

    season_2 = _build_tactical_matches().copy()
    season_2["season"] = "2324"
    season_2["date"] = pd.to_datetime(season_2["date"]).dt.strftime("%Y-%m-%d")

    df = pd.concat([season_1, season_2], ignore_index=True)
    return df


@pytest.fixture
def tactical_matches() -> pd.DataFrame:
    """Full fixture list with tactical data for testing."""
    return _build_tactical_matches()


@pytest.fixture
def two_season_tactical() -> pd.DataFrame:
    """Two-season fixture list for boundary tests."""
    return _build_two_season_tactical()


class TestComputeRawTacticalRollingFeatures:
    """Tests for raw tactical stats rolling (ppda, possession, etc.)."""

    def test_creates_ppda_columns(
        self, tactical_matches: pd.DataFrame,
    ) -> None:
        """Rolling PPDA columns are created for both sides."""
        result = compute_raw_tactical_rolling_features(
            tactical_matches, windows=[3],
        )
        assert "home_rolling_ppda_3" in result.columns
        assert "away_rolling_ppda_3" in result.columns

    def test_creates_possession_columns(
        self, tactical_matches: pd.DataFrame,
    ) -> None:
        """Rolling possession columns are created for both sides."""
        result = compute_raw_tactical_rolling_features(
            tactical_matches, windows=[3],
        )
        assert "home_rolling_possession_3" in result.columns
        assert "away_rolling_possession_3" in result.columns

    def test_creates_deep_completions_columns(
        self, tactical_matches: pd.DataFrame,
    ) -> None:
        """Rolling deep completions columns are created."""
        result = compute_raw_tactical_rolling_features(
            tactical_matches, windows=[3],
        )
        assert "home_rolling_deep_completions_3" in result.columns
        assert "away_rolling_deep_completions_3" in result.columns

    def test_creates_interceptions_columns(
        self, tactical_matches: pd.DataFrame,
    ) -> None:
        """Rolling interceptions columns are created."""
        result = compute_raw_tactical_rolling_features(
            tactical_matches, windows=[3],
        )
        assert "home_rolling_interceptions_3" in result.columns
        assert "away_rolling_interceptions_3" in result.columns

    def test_no_lookahead_bias(
        self, tactical_matches: pd.DataFrame,
    ) -> None:
        """First match for each team has NaN rolling features."""
        result = compute_raw_tactical_rolling_features(
            tactical_matches, windows=[3],
        )
        first_row = result.iloc[0]
        assert pd.isna(first_row["home_rolling_ppda_3"])

    def test_multiple_windows(
        self, tactical_matches: pd.DataFrame,
    ) -> None:
        """Multiple window sizes produce separate columns."""
        result = compute_raw_tactical_rolling_features(
            tactical_matches, windows=[3, 5],
        )
        assert "home_rolling_ppda_3" in result.columns
        assert "home_rolling_ppda_5" in result.columns

    def test_preserves_row_count(
        self, tactical_matches: pd.DataFrame,
    ) -> None:
        """Output has the same number of rows as input."""
        result = compute_raw_tactical_rolling_features(
            tactical_matches, windows=[3],
        )
        assert len(result) == len(tactical_matches)

    def test_preserves_original_columns(
        self, tactical_matches: pd.DataFrame,
    ) -> None:
        """Original columns remain unchanged."""
        original_cols = set(tactical_matches.columns)
        result = compute_raw_tactical_rolling_features(
            tactical_matches, windows=[3],
        )
        assert original_cols.issubset(set(result.columns))

    def test_ppda_rolling_value(
        self, tactical_matches: pd.DataFrame,
    ) -> None:
        """Rolling PPDA computes correct value for Arsenal.

        Arsenal match history (all, ppda perspective):
          1. 2024-01-01 home: ppda=10.5
          2. 2024-01-15 away @ Everton: ppda=10.2
          3. 2024-02-01 home: ppda=11.0
          4. 2024-02-15 away @ Liverpool: ppda=9.0

        At match 5 (Arsenal home vs Everton, 2024-03-01):
          shift(1), window 3 uses matches 2-4: [10.2, 11.0, 9.0]
          mean = 30.2 / 3 = 10.0667
        """
        result = compute_raw_tactical_rolling_features(
            tactical_matches, windows=[3],
        )
        arsenal_home = result[result["home_team"] == "Arsenal"]
        fifth_match = arsenal_home.iloc[2]
        expected = (10.2 + 11.0 + 9.0) / 3.0
        assert fifth_match["home_rolling_ppda_3"] == pytest.approx(
            expected, abs=0.01,
        )


class TestComputeRatioRollingFeatures:
    """Tests for ratio-based rolling features."""

    def test_creates_shot_conversion_columns(
        self, tactical_matches: pd.DataFrame,
    ) -> None:
        """Shot conversion rate columns are created."""
        result = compute_ratio_rolling_features(
            tactical_matches, windows=[3],
        )
        assert "home_rolling_shot_conversion_3" in result.columns
        assert "away_rolling_shot_conversion_3" in result.columns

    def test_creates_xg_overperformance_columns(
        self, tactical_matches: pd.DataFrame,
    ) -> None:
        """xG overperformance columns are created."""
        result = compute_ratio_rolling_features(
            tactical_matches, windows=[3],
        )
        assert "home_rolling_xg_overperformance_3" in result.columns
        assert "away_rolling_xg_overperformance_3" in result.columns

    def test_creates_sot_ratio_columns(
        self, tactical_matches: pd.DataFrame,
    ) -> None:
        """SOT ratio columns are created."""
        result = compute_ratio_rolling_features(
            tactical_matches, windows=[3],
        )
        assert "home_rolling_sot_ratio_3" in result.columns
        assert "away_rolling_sot_ratio_3" in result.columns

    def test_creates_pass_accuracy_columns(
        self, tactical_matches: pd.DataFrame,
    ) -> None:
        """Pass accuracy columns are created."""
        result = compute_ratio_rolling_features(
            tactical_matches, windows=[3],
        )
        assert "home_rolling_pass_accuracy_3" in result.columns
        assert "away_rolling_pass_accuracy_3" in result.columns

    def test_creates_cross_accuracy_columns(
        self, tactical_matches: pd.DataFrame,
    ) -> None:
        """Cross accuracy columns are created."""
        result = compute_ratio_rolling_features(
            tactical_matches, windows=[3],
        )
        assert "home_rolling_cross_accuracy_3" in result.columns
        assert "away_rolling_cross_accuracy_3" in result.columns

    def test_creates_long_ball_accuracy_columns(
        self, tactical_matches: pd.DataFrame,
    ) -> None:
        """Long ball accuracy columns are created."""
        result = compute_ratio_rolling_features(
            tactical_matches, windows=[3],
        )
        assert "home_rolling_long_ball_accuracy_3" in result.columns
        assert "away_rolling_long_ball_accuracy_3" in result.columns

    def test_creates_tackle_success_columns(
        self, tactical_matches: pd.DataFrame,
    ) -> None:
        """Tackle success rate columns are created."""
        result = compute_ratio_rolling_features(
            tactical_matches, windows=[3],
        )
        assert "home_rolling_tackle_success_3" in result.columns
        assert "away_rolling_tackle_success_3" in result.columns

    def test_creates_clearance_effectiveness_columns(
        self, tactical_matches: pd.DataFrame,
    ) -> None:
        """Clearance effectiveness columns are created."""
        result = compute_ratio_rolling_features(
            tactical_matches, windows=[3],
        )
        assert "home_rolling_clearance_effectiveness_3" in result.columns
        assert "away_rolling_clearance_effectiveness_3" in result.columns

    def test_creates_blocked_shots_ratio_columns(
        self, tactical_matches: pd.DataFrame,
    ) -> None:
        """Blocked shots ratio columns are created."""
        result = compute_ratio_rolling_features(
            tactical_matches, windows=[3],
        )
        assert "home_rolling_blocked_shots_ratio_3" in result.columns
        assert "away_rolling_blocked_shots_ratio_3" in result.columns

    def test_creates_saves_ratio_columns(
        self, tactical_matches: pd.DataFrame,
    ) -> None:
        """Saves ratio columns are created."""
        result = compute_ratio_rolling_features(
            tactical_matches, windows=[3],
        )
        assert "home_rolling_saves_ratio_3" in result.columns
        assert "away_rolling_saves_ratio_3" in result.columns

    def test_creates_penalty_conversion_columns(
        self, tactical_matches: pd.DataFrame,
    ) -> None:
        """Penalty conversion columns are created."""
        result = compute_ratio_rolling_features(
            tactical_matches, windows=[3],
        )
        assert "home_rolling_penalty_conversion_3" in result.columns
        assert "away_rolling_penalty_conversion_3" in result.columns

    def test_no_lookahead_bias(
        self, tactical_matches: pd.DataFrame,
    ) -> None:
        """First match for each team has NaN rolling features."""
        result = compute_ratio_rolling_features(
            tactical_matches, windows=[3],
        )
        first_row = result.iloc[0]
        assert pd.isna(first_row["home_rolling_shot_conversion_3"])

    def test_shot_conversion_value(
        self, tactical_matches: pd.DataFrame,
    ) -> None:
        """Shot conversion correctly computes goals/total_shots rolling.

        Arsenal match history:
          1. 2024-01-01 home: 2/15 = 0.1333
          2. 2024-01-15 away: 3/16 = 0.1875
          3. 2024-02-01 home: 1/12 = 0.0833
          4. 2024-02-15 away: 0/14 = 0.0

        At match 5 (Arsenal home vs Everton, 2024-03-01):
          shift(1), window 3 uses matches 2-4:
          [0.1875, 0.0833, 0.0] -> mean = 0.0903
        """
        result = compute_ratio_rolling_features(
            tactical_matches, windows=[3],
        )
        arsenal_home = result[result["home_team"] == "Arsenal"]
        fifth_match = arsenal_home.iloc[2]
        expected = (3 / 16 + 1 / 12 + 0 / 14) / 3.0
        assert fifth_match[
            "home_rolling_shot_conversion_3"
        ] == pytest.approx(expected, abs=0.01)

    def test_preserves_row_count(
        self, tactical_matches: pd.DataFrame,
    ) -> None:
        """Output has same number of rows as input."""
        result = compute_ratio_rolling_features(
            tactical_matches, windows=[3],
        )
        assert len(result) == len(tactical_matches)


class TestComputeMomentumFeatures:
    """Tests for momentum/trend features (rolling_3 - rolling_10)."""

    def test_creates_momentum_ppda_columns(
        self, tactical_matches: pd.DataFrame,
    ) -> None:
        """Momentum PPDA columns are created."""
        result = compute_momentum_features(tactical_matches)
        assert "home_momentum_ppda" in result.columns
        assert "away_momentum_ppda" in result.columns

    def test_creates_momentum_possession_columns(
        self, tactical_matches: pd.DataFrame,
    ) -> None:
        """Momentum possession columns are created."""
        result = compute_momentum_features(tactical_matches)
        assert "home_momentum_possession" in result.columns
        assert "away_momentum_possession" in result.columns

    def test_creates_momentum_shot_conversion_columns(
        self, tactical_matches: pd.DataFrame,
    ) -> None:
        """Momentum shot conversion columns are created."""
        result = compute_momentum_features(tactical_matches)
        assert "home_momentum_shot_conversion" in result.columns
        assert "away_momentum_shot_conversion" in result.columns

    def test_creates_momentum_xg_overperformance_columns(
        self, tactical_matches: pd.DataFrame,
    ) -> None:
        """Momentum xG overperformance columns are created."""
        result = compute_momentum_features(tactical_matches)
        assert "home_momentum_xg_overperformance" in result.columns
        assert "away_momentum_xg_overperformance" in result.columns

    def test_creates_momentum_pass_accuracy_columns(
        self, tactical_matches: pd.DataFrame,
    ) -> None:
        """Momentum pass accuracy columns are created."""
        result = compute_momentum_features(tactical_matches)
        assert "home_momentum_pass_accuracy" in result.columns

    def test_creates_momentum_tackle_success_columns(
        self, tactical_matches: pd.DataFrame,
    ) -> None:
        """Momentum tackle success columns are created."""
        result = compute_momentum_features(tactical_matches)
        assert "home_momentum_tackle_success" in result.columns

    def test_creates_momentum_deep_completions_columns(
        self, tactical_matches: pd.DataFrame,
    ) -> None:
        """Momentum deep completions columns are created."""
        result = compute_momentum_features(tactical_matches)
        assert "home_momentum_deep_completions" in result.columns

    def test_momentum_mostly_nan_with_few_matches(
        self, tactical_matches: pd.DataFrame,
    ) -> None:
        """Momentum requires both rolling_3 and rolling_10, so many NaNs.

        With only 12 matches total and 6 per team, rolling_10
        rarely has enough data, so momentum should be mostly NaN.
        """
        result = compute_momentum_features(tactical_matches)
        momentum_col = "home_momentum_ppda"
        nan_count = result[momentum_col].isna().sum()
        assert nan_count > len(result) // 2

    def test_preserves_row_count(
        self, tactical_matches: pd.DataFrame,
    ) -> None:
        """Output has same number of rows as input."""
        result = compute_momentum_features(tactical_matches)
        assert len(result) == len(tactical_matches)


class TestSeasonBoundaryReset:
    """Tests for season boundary handling in tactical features."""

    def test_rolling_resets_at_season_boundary(
        self, two_season_tactical: pd.DataFrame,
    ) -> None:
        """Rolling tactical stats reset when a new season starts."""
        result = compute_raw_tactical_rolling_features(
            two_season_tactical, windows=[3],
        )
        new_season = result[result["season"] == "2324"]
        first_new = new_season.iloc[0]
        assert pd.isna(first_new["home_rolling_ppda_3"])

    def test_ratios_reset_at_season_boundary(
        self, two_season_tactical: pd.DataFrame,
    ) -> None:
        """Rolling ratio stats reset when a new season starts."""
        result = compute_ratio_rolling_features(
            two_season_tactical, windows=[3],
        )
        new_season = result[result["season"] == "2324"]
        first_new = new_season.iloc[0]
        assert pd.isna(first_new["home_rolling_shot_conversion_3"])


class TestAddTacticalFeatures:
    """Tests for the top-level add_tactical_features function."""

    def test_adds_all_feature_groups(
        self, tactical_matches: pd.DataFrame,
    ) -> None:
        """All tactical feature groups are present in output."""
        result = add_tactical_features(tactical_matches, windows=[3])
        expected_prefixes = [
            "home_rolling_ppda",
            "home_rolling_possession",
            "home_rolling_deep_completions",
            "home_rolling_shot_conversion",
            "home_rolling_xg_overperformance",
            "home_rolling_sot_ratio",
            "home_rolling_pass_accuracy",
            "home_rolling_cross_accuracy",
            "home_rolling_long_ball_accuracy",
            "home_rolling_tackle_success",
            "home_rolling_clearance_effectiveness",
            "home_rolling_blocked_shots_ratio",
            "home_rolling_saves_ratio",
            "home_momentum_ppda",
        ]
        for prefix in expected_prefixes:
            matching = [c for c in result.columns if c.startswith(prefix)]
            assert len(matching) > 0, f"No columns with prefix: {prefix}"

    def test_handles_empty_dataframe(self) -> None:
        """Returns empty DataFrame with no errors."""
        df = pd.DataFrame()
        result = add_tactical_features(df)
        assert isinstance(result, pd.DataFrame)

    def test_default_windows(
        self, tactical_matches: pd.DataFrame,
    ) -> None:
        """Default windows [3, 5, 10] are used when none specified."""
        result = add_tactical_features(tactical_matches)
        assert "home_rolling_ppda_3" in result.columns
        assert "home_rolling_ppda_5" in result.columns
        assert "home_rolling_ppda_10" in result.columns

    def test_preserves_original_data(
        self, tactical_matches: pd.DataFrame,
    ) -> None:
        """Original column values are not modified."""
        original_ppda = tactical_matches["home_ppda"].copy()
        result = add_tactical_features(tactical_matches, windows=[3])
        pd.testing.assert_series_equal(
            result["home_ppda"], original_ppda,
        )

    def test_sorted_by_date(
        self, tactical_matches: pd.DataFrame,
    ) -> None:
        """Output is sorted by date."""
        shuffled = tactical_matches.sample(frac=1.0, random_state=42)
        result = add_tactical_features(shuffled, windows=[3])
        dates = result["date"].tolist()
        assert dates == sorted(dates)

    def test_missing_columns_handled_gracefully(self) -> None:
        """Missing tactical columns are skipped without error."""
        df = pd.DataFrame({
            "date": ["2024-01-01", "2024-01-15"],
            "home_team": ["Arsenal", "Chelsea"],
            "away_team": ["Chelsea", "Arsenal"],
            "home_goals": [2, 1],
            "away_goals": [1, 2],
            "home_xg": [1.8, 0.9],
            "away_xg": [0.9, 1.8],
            "season": ["2324", "2324"],
        })
        result = add_tactical_features(df, windows=[3])
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
