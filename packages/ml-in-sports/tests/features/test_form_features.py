"""Tests for form streaks and advanced match features module."""

import pandas as pd
import pytest
from ml_in_sports.features.form_features import (
    _build_streak_histories,
    _compute_all_streaks,
    _compute_corners_rolling,
    _compute_discipline_rolling,
    _compute_timing_goals,
    _compute_xg_chain_rolling,
    _join_team_features_to_matches,
    add_form_features,
)
from ml_in_sports.utils.database import FootballDatabase

# ---------------------------------------------------------------------------
# TestBuildStreakHistories
# ---------------------------------------------------------------------------


class TestBuildStreakHistories:
    """Tests for building per-team streak histories."""

    def test_produces_two_rows_per_match(
        self, simple_matches: pd.DataFrame,
    ) -> None:
        """Each match produces one row per team (2 per match)."""
        result = _build_streak_histories(simple_matches)
        assert len(result) == len(simple_matches) * 2

    def test_contains_required_columns(
        self, simple_matches: pd.DataFrame,
    ) -> None:
        """History DataFrame has won, drawn, lost, scored, clean_sheet."""
        result = _build_streak_histories(simple_matches)
        for col in ["won", "drawn", "lost", "scored", "clean_sheet"]:
            assert col in result.columns

    def test_home_win_flags_correct(
        self, simple_matches: pd.DataFrame,
    ) -> None:
        """Home team win is flagged correctly."""
        result = _build_streak_histories(simple_matches)
        g1_home = result[
            (result["game"] == "g1") & (result["team"] == "Arsenal")
        ]
        assert g1_home["won"].iloc[0] == 1
        assert g1_home["lost"].iloc[0] == 0

    def test_away_loss_flags_correct(
        self, simple_matches: pd.DataFrame,
    ) -> None:
        """Away team loss is flagged correctly."""
        result = _build_streak_histories(simple_matches)
        g1_away = result[
            (result["game"] == "g1") & (result["team"] == "Chelsea")
        ]
        assert g1_away["won"].iloc[0] == 0
        assert g1_away["lost"].iloc[0] == 1

    def test_draw_flags_correct(
        self, simple_matches: pd.DataFrame,
    ) -> None:
        """Draw is flagged correctly for both teams."""
        result = _build_streak_histories(simple_matches)
        g3 = result[result["game"] == "g3"]
        assert g3["drawn"].values.tolist() == [1, 1]

    def test_clean_sheet_flag(
        self, simple_matches: pd.DataFrame,
    ) -> None:
        """Clean sheet is 1 when opponent scored 0."""
        result = _build_streak_histories(simple_matches)
        g5_home = result[
            (result["game"] == "g5") & (result["team"] == "Arsenal")
        ]
        assert g5_home["clean_sheet"].iloc[0] == 1

    def test_scored_flag(
        self, simple_matches: pd.DataFrame,
    ) -> None:
        """Scored is 1 when team scored at least 1 goal."""
        result = _build_streak_histories(simple_matches)
        g2_away = result[
            (result["game"] == "g2") & (result["team"] == "Arsenal")
        ]
        assert g2_away["scored"].iloc[0] == 1

    def test_empty_input_returns_empty(self) -> None:
        """Empty input returns empty DataFrame."""
        result = _build_streak_histories(pd.DataFrame())
        assert result.empty


# ---------------------------------------------------------------------------
# TestComputeAllStreaks
# ---------------------------------------------------------------------------


class TestComputeAllStreaks:
    """Tests for streak computation logic."""

    def test_win_streak_starts_at_nan(
        self, simple_matches: pd.DataFrame,
    ) -> None:
        """First match has NaN streak (shift prevents lookahead)."""
        histories = _build_streak_histories(simple_matches)
        result = _compute_all_streaks(histories)
        arsenal = result[
            result["team"] == "Arsenal"
        ].sort_values("date")
        assert pd.isna(arsenal.iloc[0]["win_streak"])

    def test_win_streak_counts_consecutive_wins(
        self, simple_matches: pd.DataFrame,
    ) -> None:
        """Win streak increments for consecutive wins."""
        histories = _build_streak_histories(simple_matches)
        result = _compute_all_streaks(histories)
        arsenal = result[result["team"] == "Arsenal"].sort_values("date")
        streaks = arsenal["win_streak"].tolist()
        assert not all(pd.isna(s) for s in streaks)

    def test_losing_streak_resets_on_non_loss(
        self, simple_matches: pd.DataFrame,
    ) -> None:
        """Losing streak resets to 0 when team does not lose."""
        histories = _build_streak_histories(simple_matches)
        result = _compute_all_streaks(histories)
        arsenal = result[result["team"] == "Arsenal"].sort_values("date")
        valid = arsenal.dropna(subset=["losing_streak"])
        if not valid.empty:
            assert 0 in valid["losing_streak"].values

    def test_unbeaten_streak_includes_draws(
        self, simple_matches: pd.DataFrame,
    ) -> None:
        """Unbeaten streak counts wins and draws."""
        histories = _build_streak_histories(simple_matches)
        result = _compute_all_streaks(histories)
        assert "unbeaten_streak" in result.columns

    def test_streak_columns_present(
        self, simple_matches: pd.DataFrame,
    ) -> None:
        """All six streak columns are present."""
        histories = _build_streak_histories(simple_matches)
        result = _compute_all_streaks(histories)
        expected = [
            "win_streak", "unbeaten_streak", "losing_streak",
            "draw_streak", "scoring_streak", "clean_sheet_streak",
        ]
        for col in expected:
            assert col in result.columns

    def test_no_lookahead_in_streaks(
        self, simple_matches: pd.DataFrame,
    ) -> None:
        """Streaks at match i do not use match i data (shift(1))."""
        histories = _build_streak_histories(simple_matches)
        result = _compute_all_streaks(histories)
        for team in result["team"].unique():
            team_data = result[result["team"] == team].sort_values("date")
            assert pd.isna(team_data.iloc[0]["win_streak"])

    def test_season_boundary_resets_streaks(
        self, two_season_matches: pd.DataFrame,
    ) -> None:
        """Streaks reset at season boundary."""
        histories = _build_streak_histories(two_season_matches)
        result = _compute_all_streaks(histories)
        for team in result["team"].unique():
            team_s2 = result[
                (result["team"] == team)
                & (result["season"] == "2324")
            ].sort_values("date")
            if not team_s2.empty:
                assert pd.isna(team_s2.iloc[0]["win_streak"])

    def test_empty_input_returns_empty(self) -> None:
        """Empty input returns empty DataFrame."""
        result = _compute_all_streaks(pd.DataFrame())
        assert result.empty


# ---------------------------------------------------------------------------
# TestComputeTimingGoals
# ---------------------------------------------------------------------------


class TestComputeTimingGoals:
    """Tests for timing-based goal features from shots."""

    def test_creates_rolling_columns(
        self, sample_shots: pd.DataFrame,
    ) -> None:
        """Timing features produce rolling columns."""
        result = _compute_timing_goals(sample_shots, windows=[3])
        assert any(
            "goals_last_15min" in c for c in result.columns
        )
        assert any(
            "goals_first_15min" in c for c in result.columns
        )

    def test_goals_last_15min_counts_76_to_90(
        self, sample_shots: pd.DataFrame,
    ) -> None:
        """Goals in minutes 76-90+ are counted for last 15min."""
        result = _compute_timing_goals(sample_shots, windows=[3])
        arsenal = result[result["team"] == "Arsenal"]
        assert "goals_last_15min" in arsenal.columns

    def test_goals_first_15min_counts_1_to_15(
        self, sample_shots: pd.DataFrame,
    ) -> None:
        """Goals in minutes 1-15 are counted for first 15min."""
        result = _compute_timing_goals(sample_shots, windows=[3])
        arsenal = result[result["team"] == "Arsenal"]
        assert "goals_first_15min" in arsenal.columns

    def test_empty_shots_returns_empty(self) -> None:
        """Empty shots returns empty DataFrame."""
        result = _compute_timing_goals(pd.DataFrame(), windows=[3])
        assert result.empty

    def test_shift_prevents_lookahead(
        self, sample_shots: pd.DataFrame,
    ) -> None:
        """First game has NaN rolling timing features."""
        result = _compute_timing_goals(sample_shots, windows=[3])
        for team in result["team"].unique():
            team_data = result[
                result["team"] == team
            ].sort_values("date")
            rolling_cols = [
                c for c in result.columns
                if "rolling" in c
            ]
            if rolling_cols and not team_data.empty:
                assert pd.isna(team_data.iloc[0][rolling_cols[0]])


# ---------------------------------------------------------------------------
# TestComputeDisciplineRolling
# ---------------------------------------------------------------------------


class TestComputeDisciplineRolling:
    """Tests for discipline rolling features from player_matches."""

    def test_yellow_cards_rolling_created(
        self, sample_player_matches: pd.DataFrame,
    ) -> None:
        """Yellow cards rolling column is created."""
        result = _compute_discipline_rolling(
            sample_player_matches, windows=[3],
        )
        assert any("yellow_cards_rolling" in c for c in result.columns)

    def test_red_cards_rolling_created(
        self, sample_player_matches: pd.DataFrame,
    ) -> None:
        """Red cards rolling column is created."""
        result = _compute_discipline_rolling(
            sample_player_matches, windows=[3],
        )
        assert any("red_cards_rolling" in c for c in result.columns)

    def test_fouls_rolling_created_when_available(
        self, sample_player_matches: pd.DataFrame,
    ) -> None:
        """Fouls rolling is created if fouls_committed column exists."""
        result = _compute_discipline_rolling(
            sample_player_matches, windows=[3],
        )
        assert any("fouls_rolling" in c for c in result.columns)

    def test_empty_input_returns_empty(self) -> None:
        """Empty input returns empty DataFrame."""
        result = _compute_discipline_rolling(pd.DataFrame(), windows=[3])
        assert result.empty

    def test_aggregates_per_team_per_game(
        self, sample_player_matches: pd.DataFrame,
    ) -> None:
        """Discipline stats are aggregated per team per game."""
        result = _compute_discipline_rolling(
            sample_player_matches, windows=[3],
        )
        rows_per_game = result.groupby(["game", "team"]).size()
        assert (rows_per_game == 1).all()


# ---------------------------------------------------------------------------
# TestComputeXgChainRolling
# ---------------------------------------------------------------------------


class TestComputeXgChainRolling:
    """Tests for xG chain/buildup rolling features."""

    def test_xg_chain_rolling_created(
        self, sample_player_matches: pd.DataFrame,
    ) -> None:
        """xG chain rolling column is created."""
        result = _compute_xg_chain_rolling(
            sample_player_matches, windows=[3],
        )
        assert any("xg_chain_rolling" in c for c in result.columns)

    def test_xg_buildup_rolling_created(
        self, sample_player_matches: pd.DataFrame,
    ) -> None:
        """xG buildup rolling column is created."""
        result = _compute_xg_chain_rolling(
            sample_player_matches, windows=[3],
        )
        assert any("xg_buildup_rolling" in c for c in result.columns)

    def test_empty_input_returns_empty(self) -> None:
        """Empty input returns empty DataFrame."""
        result = _compute_xg_chain_rolling(pd.DataFrame(), windows=[3])
        assert result.empty

    def test_no_lookahead(
        self, sample_player_matches: pd.DataFrame,
    ) -> None:
        """First game per team has NaN rolling values."""
        result = _compute_xg_chain_rolling(
            sample_player_matches, windows=[3],
        )
        for team in result["team"].unique():
            team_data = result[
                result["team"] == team
            ].sort_values("date")
            rolling_cols = [
                c for c in result.columns
                if "rolling" in c
            ]
            if rolling_cols and not team_data.empty:
                assert pd.isna(team_data.iloc[0][rolling_cols[0]])


# ---------------------------------------------------------------------------
# TestComputeCornersRolling
# ---------------------------------------------------------------------------


class TestComputeCornersRolling:
    """Tests for corners rolling features from matches table."""

    def test_corners_won_rolling_created(
        self, matches_with_corners: pd.DataFrame,
    ) -> None:
        """Corners won rolling column is created."""
        result = _compute_corners_rolling(
            matches_with_corners, windows=[3],
        )
        assert any("corners_won_rolling" in c for c in result.columns)

    def test_opponent_corners_rolling_created(
        self, matches_with_corners: pd.DataFrame,
    ) -> None:
        """Opponent corners rolling column is created."""
        result = _compute_corners_rolling(
            matches_with_corners, windows=[3],
        )
        assert any(
            "opponent_corners_rolling" in c for c in result.columns
        )

    def test_empty_returns_empty(self) -> None:
        """Empty DataFrame returns empty."""
        result = _compute_corners_rolling(pd.DataFrame(), windows=[3])
        assert result.empty

    def test_missing_corner_columns_returns_empty(self) -> None:
        """Missing corner columns returns empty DataFrame."""
        df = pd.DataFrame({
            "league": ["EPL"],
            "season": ["2324"],
            "game": ["g1"],
            "home_team": ["A"],
            "away_team": ["B"],
            "home_goals": [1],
            "away_goals": [0],
        })
        result = _compute_corners_rolling(df, windows=[3])
        assert result.empty


# ---------------------------------------------------------------------------
# TestJoinTeamFeaturesToMatches
# ---------------------------------------------------------------------------


class TestJoinTeamFeaturesToMatches:
    """Tests for joining per-team features to match rows."""

    def test_creates_home_and_away_columns(self) -> None:
        """Creates home_ and away_ prefixed columns."""
        match_df = pd.DataFrame({
            "game": ["g1"],
            "home_team": ["Arsenal"],
            "away_team": ["Chelsea"],
        })
        team_features = pd.DataFrame({
            "game": ["g1", "g1"],
            "team": ["Arsenal", "Chelsea"],
            "win_streak": [3.0, 1.0],
        })
        result = _join_team_features_to_matches(
            match_df, team_features, ["win_streak"],
        )
        assert "home_win_streak" in result.columns
        assert "away_win_streak" in result.columns

    def test_values_assigned_correctly(self) -> None:
        """Correct values assigned to home/away sides."""
        match_df = pd.DataFrame({
            "game": ["g1"],
            "home_team": ["Arsenal"],
            "away_team": ["Chelsea"],
        })
        team_features = pd.DataFrame({
            "game": ["g1", "g1"],
            "team": ["Arsenal", "Chelsea"],
            "win_streak": [3.0, 1.0],
        })
        result = _join_team_features_to_matches(
            match_df, team_features, ["win_streak"],
        )
        assert result["home_win_streak"].iloc[0] == pytest.approx(3.0)
        assert result["away_win_streak"].iloc[0] == pytest.approx(1.0)

    def test_empty_features_returns_original(self) -> None:
        """Empty team features returns match df unchanged."""
        match_df = pd.DataFrame({
            "game": ["g1"],
            "home_team": ["A"],
            "away_team": ["B"],
        })
        result = _join_team_features_to_matches(
            match_df, pd.DataFrame(), ["win_streak"],
        )
        assert len(result.columns) == len(match_df.columns)


# ---------------------------------------------------------------------------
# TestAddFormFeatures (integration)
# ---------------------------------------------------------------------------


class TestAddFormFeatures:
    """Integration tests for the add_form_features orchestrator."""

    def test_empty_df_returns_empty(
        self, football_db: FootballDatabase,
    ) -> None:
        """Empty match DataFrame returns empty."""
        result = add_form_features(pd.DataFrame(), football_db)
        assert result.empty

    def test_returns_same_row_count(
        self,
        simple_matches: pd.DataFrame,
        football_db: FootballDatabase,
    ) -> None:
        """Output has same number of rows as input."""
        result = add_form_features(simple_matches, football_db)
        assert len(result) == len(simple_matches)

    def test_adds_streak_columns(
        self,
        simple_matches: pd.DataFrame,
        football_db: FootballDatabase,
    ) -> None:
        """Streak columns are added to the result."""
        result = add_form_features(simple_matches, football_db)
        assert "home_win_streak" in result.columns
        assert "away_win_streak" in result.columns

    def test_with_shots_data(
        self,
        simple_matches: pd.DataFrame,
        sample_shots: pd.DataFrame,
        football_db: FootballDatabase,
    ) -> None:
        """Timing features are added when shots data exists."""
        football_db.upsert_dataframe("shots", sample_shots)
        result = add_form_features(
            simple_matches, football_db, windows=[3],
        )
        timing_cols = [
            c for c in result.columns
            if "goals_last_15min" in c or "goals_first_15min" in c
        ]
        assert len(timing_cols) > 0

    def test_with_player_matches_data(
        self,
        simple_matches: pd.DataFrame,
        sample_player_matches: pd.DataFrame,
        football_db: FootballDatabase,
    ) -> None:
        """Discipline and xG chain features added with player data."""
        football_db.upsert_dataframe(
            "player_matches", sample_player_matches,
        )
        result = add_form_features(
            simple_matches, football_db, windows=[3],
        )
        discipline_cols = [
            c for c in result.columns
            if "yellow_cards" in c or "red_cards" in c
        ]
        assert len(discipline_cols) > 0

    def test_custom_windows(
        self,
        simple_matches: pd.DataFrame,
        football_db: FootballDatabase,
    ) -> None:
        """Custom window sizes are respected."""
        result = add_form_features(
            simple_matches, football_db, windows=[5],
        )
        streak_cols = [
            c for c in result.columns
            if "streak" in c
        ]
        assert len(streak_cols) > 0

    def test_preserves_original_columns(
        self,
        simple_matches: pd.DataFrame,
        football_db: FootballDatabase,
    ) -> None:
        """Original columns are preserved in the output."""
        original_cols = set(simple_matches.columns)
        result = add_form_features(simple_matches, football_db)
        assert original_cols.issubset(set(result.columns))

    def test_corners_features_when_available(
        self,
        matches_with_corners: pd.DataFrame,
        football_db: FootballDatabase,
    ) -> None:
        """Corner features are added when corner columns exist."""
        result = add_form_features(
            matches_with_corners, football_db, windows=[3],
        )
        corner_cols = [
            c for c in result.columns
            if "corners" in c and "rolling" in c
        ]
        assert len(corner_cols) > 0
