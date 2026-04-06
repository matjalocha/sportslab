"""Tests for match-level player quality features module."""

from pathlib import Path

import pandas as pd
import pytest
from ml_in_sports.features.match_player_quality import (
    _build_xi_fifa_stats,
    _compute_bench_strength,
    _compute_fifa_xi_features,
    _compute_market_value_features,
    _join_player_matches_with_fifa,
    _map_fifa_version_to_season,
    _normalize_player_name,
    add_match_player_quality,
)
from ml_in_sports.utils.database import FootballDatabase

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def player_matches_df() -> pd.DataFrame:
    """Player matches for two teams in one game."""
    return pd.DataFrame({
        "game": ["g1"] * 6,
        "team": ["TeamA"] * 3 + ["TeamB"] * 3,
        "player": [
            "John Smith", "Jane Doe", "Bob Keeper",
            "Alice Forward", "Charlie Mid", "Dave Keeper",
        ],
        "minutes": [90, 85, 90, 90, 70, 90],
        "goals": [1, 0, 0, 2, 0, 0],
        "assists": [0, 1, 0, 0, 1, 0],
        "xg": [0.8, 0.1, 0.0, 1.5, 0.2, 0.0],
        "xa": [0.0, 0.9, 0.0, 0.0, 0.8, 0.0],
        "shots": [3, 1, 0, 5, 1, 0],
        "key_passes": [0, 3, 0, 0, 2, 0],
        "yellow_cards": [0, 1, 0, 0, 0, 1],
        "red_cards": [0, 0, 0, 0, 0, 0],
        "xg_chain": [0.5, 0.3, 0.0, 1.0, 0.4, 0.0],
        "xg_buildup": [0.2, 0.4, 0.0, 0.3, 0.5, 0.0],
        "league": ["EPL"] * 6,
        "season": ["2324"] * 6,
        "position": ["FW", "MF", "GK", "FW", "MF", "GK"],
    })


@pytest.fixture
def fifa_ratings_df() -> pd.DataFrame:
    """FIFA ratings for players in test data."""
    return pd.DataFrame({
        "player_name": [
            "John Smith", "Jane Doe", "Bob Keeper",
            "Alice Forward", "Charlie Mid", "Dave Keeper",
            "Bench Player One", "Bench Player Two",
        ],
        "long_name": [
            "John A. Smith", "Jane B. Doe", "Robert Keeper",
            "Alice C. Forward", "Charlie D. Mid", "David Keeper",
            "Bench P. One", "Bench P. Two",
        ],
        "club_name": [
            "TeamA", "TeamA", "TeamA",
            "TeamB", "TeamB", "TeamB",
            "TeamA", "TeamB",
        ],
        "league_name": ["EPL"] * 8,
        "overall": [85, 80, 78, 88, 82, 76, 72, 70],
        "potential": [87, 85, 80, 90, 86, 78, 78, 75],
        "value_eur": [
            40000000, 25000000, 10000000,
            60000000, 30000000, 8000000,
            5000000, 4000000,
        ],
        "wage_eur": [
            200000, 120000, 50000,
            300000, 150000, 40000,
            30000, 25000,
        ],
        "positions": ["ST", "CM", "GK", "ST", "CM", "GK", "CB", "CB"],
        "pace": [88, 72, 40, 92, 75, 38, 65, 60],
        "shooting": [86, 70, 15, 90, 72, 12, 45, 40],
        "passing": [78, 82, 30, 75, 85, 28, 55, 50],
        "dribbling": [84, 80, 20, 88, 78, 18, 58, 52],
        "defending": [40, 72, 18, 35, 70, 16, 78, 75],
        "physic": [76, 68, 70, 80, 72, 68, 74, 70],
        "skill_moves": [4, 3, 1, 4, 3, 1, 2, 2],
        "weak_foot": [4, 3, 2, 3, 4, 2, 3, 3],
        "fifa_version": ["24"] * 8,
        "age": [27, 25, 30, 24, 28, 31, 22, 23],
    })


@pytest.fixture
def tm_players_df() -> pd.DataFrame:
    """Transfer market player data."""
    return pd.DataFrame({
        "name": [
            "John Smith", "Jane Doe", "Bob Keeper",
            "Alice Forward", "Charlie Mid", "Dave Keeper",
        ],
        "first_name": [
            "John", "Jane", "Bob", "Alice", "Charlie", "Dave",
        ],
        "last_name": [
            "Smith", "Doe", "Keeper", "Forward", "Mid", "Keeper",
        ],
        "position": ["Attack", "Midfield", "Goalkeeper",
                      "Attack", "Midfield", "Goalkeeper"],
        "sub_position": ["Centre-Forward", "Central Midfield",
                         "Goalkeeper", "Centre-Forward",
                         "Central Midfield", "Goalkeeper"],
        "foot": ["Right", "Left", "Right", "Right", "Right", "Left"],
        "height_in_cm": [182.0, 170.0, 190.0, 175.0, 180.0, 188.0],
        "date_of_birth": [
            "1997-03-15", "1999-05-20", "1994-08-10",
            "2000-01-05", "1996-11-22", "1993-06-18",
        ],
        "country_of_citizenship": [
            "England", "France", "Germany",
            "Brazil", "Spain", "Italy",
        ],
        "current_club_name": [
            "TeamA", "TeamA", "TeamA",
            "TeamB", "TeamB", "TeamB",
        ],
        "market_value_in_eur": [
            45000000, 28000000, 12000000,
            65000000, 32000000, 9000000,
        ],
        "highest_market_value_in_eur": [
            50000000, 30000000, 15000000,
            70000000, 35000000, 12000000,
        ],
    })


@pytest.fixture
def match_df() -> pd.DataFrame:
    """Match-level DataFrame for orchestrator testing."""
    return pd.DataFrame({
        "game": ["g1", "g2"],
        "home_team": ["TeamA", "TeamB"],
        "away_team": ["TeamB", "TeamA"],
        "date": ["2024-01-15", "2024-01-22"],
        "season": ["2324", "2324"],
        "league": ["EPL", "EPL"],
        "home_goals": [2, 1],
        "away_goals": [1, 0],
    })


@pytest.fixture
def multi_game_player_matches() -> pd.DataFrame:
    """Player matches spanning multiple games."""
    records = []
    for _idx, game_id in enumerate(["g1", "g2", "g3"]):
        for team in ["TeamA", "TeamB"]:
            for player, pos in [("P1", "FW"), ("P2", "MF"), ("GK1", "GK")]:
                full_name = f"{player}_{team}"
                records.append({
                    "game": game_id,
                    "team": team,
                    "player": full_name,
                    "minutes": 90,
                    "goals": 1 if pos == "FW" else 0,
                    "assists": 1 if pos == "MF" else 0,
                    "xg": 0.8 if pos == "FW" else 0.0,
                    "xa": 0.5 if pos == "MF" else 0.0,
                    "shots": 3 if pos == "FW" else 0,
                    "key_passes": 2 if pos == "MF" else 0,
                    "yellow_cards": 0,
                    "red_cards": 0,
                    "xg_chain": 0.3,
                    "xg_buildup": 0.2,
                    "league": "EPL",
                    "season": "2324",
                    "position": pos,
                })
    return pd.DataFrame(records)


@pytest.fixture
def multi_game_fifa_ratings() -> pd.DataFrame:
    """FIFA ratings for multi-game test players."""
    records = []
    for team in ["TeamA", "TeamB"]:
        for player, pos, ovr, pot in [
            ("P1", "ST", 85, 88),
            ("P2", "CM", 80, 84),
            ("GK1", "GK", 78, 80),
            ("BenchP", "CB", 72, 76),
        ]:
            full_name = f"{player}_{team}"
            records.append({
                "player_name": full_name,
                "long_name": full_name,
                "club_name": team,
                "league_name": "EPL",
                "overall": ovr,
                "potential": pot,
                "value_eur": ovr * 500000,
                "wage_eur": ovr * 2000,
                "positions": pos,
                "pace": ovr - 5,
                "shooting": ovr - 10 if pos != "GK" else 15,
                "passing": ovr - 3,
                "dribbling": ovr - 8 if pos != "GK" else 20,
                "defending": 40 if pos == "ST" else ovr - 2,
                "physic": ovr - 7,
                "skill_moves": 3 if pos != "GK" else 1,
                "weak_foot": 3,
                "fifa_version": "24",
                "age": 25,
            })
    return pd.DataFrame(records)


@pytest.fixture
def football_db(tmp_path: Path) -> FootballDatabase:
    """Create a temporary FootballDatabase instance."""
    db_path = tmp_path / "test.db"
    db = FootballDatabase(db_path=db_path)
    db.create_tables()
    return db


# ---------------------------------------------------------------------------
# _normalize_player_name
# ---------------------------------------------------------------------------

class TestNormalizePlayerName:
    """Tests for player name normalization."""

    def test_lowercase(self) -> None:
        """Names are lowercased."""
        assert _normalize_player_name("John Smith") == "john smith"

    def test_strips_whitespace(self) -> None:
        """Leading and trailing whitespace is removed."""
        assert _normalize_player_name("  John Smith  ") == "john smith"

    def test_removes_accents(self) -> None:
        """Accented characters are normalized."""
        result = _normalize_player_name("Jose Martinez")
        assert result == "jose martinez"

    def test_empty_string(self) -> None:
        """Empty string returns empty string."""
        assert _normalize_player_name("") == ""

    def test_handles_special_characters(self) -> None:
        """Names with hyphens and apostrophes are preserved."""
        result = _normalize_player_name("O'Brien-Smith")
        assert result == "o'brien-smith"


# ---------------------------------------------------------------------------
# _map_fifa_version_to_season
# ---------------------------------------------------------------------------

class TestMapFifaVersionToSeason:
    """Tests for FIFA version to season mapping."""

    def test_fifa_24_maps_to_2324(self) -> None:
        """FIFA 24 corresponds to season 2324."""
        assert _map_fifa_version_to_season("24") == "2324"

    def test_fifa_23_maps_to_2223(self) -> None:
        """FIFA 23 corresponds to season 2223."""
        assert _map_fifa_version_to_season("23") == "2223"

    def test_fifa_25_maps_to_2425(self) -> None:
        """FIFA 25 corresponds to season 2425."""
        assert _map_fifa_version_to_season("25") == "2425"

    def test_non_numeric_returns_none(self) -> None:
        """Non-numeric version returns None."""
        assert _map_fifa_version_to_season("abc") is None

    def test_empty_string_returns_none(self) -> None:
        """Empty string returns None."""
        assert _map_fifa_version_to_season("") is None


# ---------------------------------------------------------------------------
# _join_player_matches_with_fifa
# ---------------------------------------------------------------------------

class TestJoinPlayerMatchesWithFifa:
    """Tests for joining player matches with FIFA ratings."""

    def test_exact_name_match(
        self,
        player_matches_df: pd.DataFrame,
        fifa_ratings_df: pd.DataFrame,
    ) -> None:
        """Players with exact name matches are joined."""
        result = _join_player_matches_with_fifa(
            player_matches_df, fifa_ratings_df,
        )
        assert len(result) > 0
        assert "overall" in result.columns

    def test_unmatched_players_excluded(
        self,
        player_matches_df: pd.DataFrame,
    ) -> None:
        """Players without FIFA data are excluded from join result."""
        empty_fifa = pd.DataFrame(columns=[
            "player_name", "club_name", "overall", "potential",
            "value_eur", "wage_eur", "positions", "pace",
            "shooting", "passing", "dribbling", "defending",
            "physic", "skill_moves", "weak_foot", "fifa_version",
        ])
        result = _join_player_matches_with_fifa(
            player_matches_df, empty_fifa,
        )
        assert len(result) == 0

    def test_preserves_game_and_team_columns(
        self,
        player_matches_df: pd.DataFrame,
        fifa_ratings_df: pd.DataFrame,
    ) -> None:
        """Game and team columns are preserved after join."""
        result = _join_player_matches_with_fifa(
            player_matches_df, fifa_ratings_df,
        )
        assert "game" in result.columns
        assert "team" in result.columns


# ---------------------------------------------------------------------------
# _compute_fifa_xi_features
# ---------------------------------------------------------------------------

class TestComputeFifaXiFeatures:
    """Tests for FIFA XI quality feature computation."""

    def test_avg_overall_xi_computed(self) -> None:
        """Average overall rating of XI is computed correctly."""
        xi_data = pd.DataFrame({
            "game": ["g1"] * 3,
            "team": ["TeamA"] * 3,
            "overall": [85, 80, 78],
            "potential": [88, 85, 80],
            "positions": ["ST", "CM", "GK"],
            "pace": [88, 72, 40],
            "shooting": [86, 70, 15],
            "passing": [78, 82, 30],
            "dribbling": [84, 80, 20],
            "defending": [40, 72, 18],
            "physic": [76, 68, 70],
            "skill_moves": [4, 3, 1],
            "weak_foot": [4, 3, 2],
        })
        result = _compute_fifa_xi_features(xi_data)
        expected_avg = (85 + 80 + 78) / 3
        row = result[
            (result["game"] == "g1") & (result["team"] == "TeamA")
        ]
        assert row["avg_overall_xi"].iloc[0] == pytest.approx(expected_avg)

    def test_max_overall_xi(self) -> None:
        """Max overall in XI is identified correctly."""
        xi_data = pd.DataFrame({
            "game": ["g1"] * 3,
            "team": ["TeamA"] * 3,
            "overall": [85, 80, 78],
            "potential": [88, 85, 80],
            "positions": ["ST", "CM", "GK"],
            "pace": [88, 72, 40],
            "shooting": [86, 70, 15],
            "passing": [78, 82, 30],
            "dribbling": [84, 80, 20],
            "defending": [40, 72, 18],
            "physic": [76, 68, 70],
            "skill_moves": [4, 3, 1],
            "weak_foot": [4, 3, 2],
        })
        result = _compute_fifa_xi_features(xi_data)
        row = result[
            (result["game"] == "g1") & (result["team"] == "TeamA")
        ]
        assert row["max_overall_xi"].iloc[0] == 85

    def test_min_overall_xi(self) -> None:
        """Min overall in XI is identified correctly."""
        xi_data = pd.DataFrame({
            "game": ["g1"] * 3,
            "team": ["TeamA"] * 3,
            "overall": [85, 80, 78],
            "potential": [88, 85, 80],
            "positions": ["ST", "CM", "GK"],
            "pace": [88, 72, 40],
            "shooting": [86, 70, 15],
            "passing": [78, 82, 30],
            "dribbling": [84, 80, 20],
            "defending": [40, 72, 18],
            "physic": [76, 68, 70],
            "skill_moves": [4, 3, 1],
            "weak_foot": [4, 3, 2],
        })
        result = _compute_fifa_xi_features(xi_data)
        row = result[
            (result["game"] == "g1") & (result["team"] == "TeamA")
        ]
        assert row["min_overall_xi"].iloc[0] == 78

    def test_overall_std_xi(self) -> None:
        """Standard deviation of overall ratings is computed."""
        xi_data = pd.DataFrame({
            "game": ["g1"] * 3,
            "team": ["TeamA"] * 3,
            "overall": [85, 80, 78],
            "potential": [88, 85, 80],
            "positions": ["ST", "CM", "GK"],
            "pace": [88, 72, 40],
            "shooting": [86, 70, 15],
            "passing": [78, 82, 30],
            "dribbling": [84, 80, 20],
            "defending": [40, 72, 18],
            "physic": [76, 68, 70],
            "skill_moves": [4, 3, 1],
            "weak_foot": [4, 3, 2],
        })
        result = _compute_fifa_xi_features(xi_data)
        row = result[
            (result["game"] == "g1") & (result["team"] == "TeamA")
        ]
        expected_std = pd.Series([85, 80, 78]).std()
        assert row["overall_std_xi"].iloc[0] == pytest.approx(expected_std)

    def test_starting_gk_overall(self) -> None:
        """GK overall is extracted from goalkeeper in XI."""
        xi_data = pd.DataFrame({
            "game": ["g1"] * 3,
            "team": ["TeamA"] * 3,
            "overall": [85, 80, 78],
            "potential": [88, 85, 80],
            "positions": ["ST", "CM", "GK"],
            "pace": [88, 72, 40],
            "shooting": [86, 70, 15],
            "passing": [78, 82, 30],
            "dribbling": [84, 80, 20],
            "defending": [40, 72, 18],
            "physic": [76, 68, 70],
            "skill_moves": [4, 3, 1],
            "weak_foot": [4, 3, 2],
        })
        result = _compute_fifa_xi_features(xi_data)
        row = result[
            (result["game"] == "g1") & (result["team"] == "TeamA")
        ]
        assert row["starting_gk_overall"].iloc[0] == 78

    def test_no_gk_returns_nan(self) -> None:
        """Missing GK in XI returns NaN for starting_gk_overall."""
        xi_data = pd.DataFrame({
            "game": ["g1"] * 2,
            "team": ["TeamA"] * 2,
            "overall": [85, 80],
            "potential": [88, 85],
            "positions": ["ST", "CM"],
            "pace": [88, 72],
            "shooting": [86, 70],
            "passing": [78, 82],
            "dribbling": [84, 80],
            "defending": [40, 72],
            "physic": [76, 68],
            "skill_moves": [4, 3],
            "weak_foot": [4, 3],
        })
        result = _compute_fifa_xi_features(xi_data)
        row = result[
            (result["game"] == "g1") & (result["team"] == "TeamA")
        ]
        assert pd.isna(row["starting_gk_overall"].iloc[0])

    def test_avg_attribute_columns(self) -> None:
        """Mean attribute columns are computed for XI."""
        xi_data = pd.DataFrame({
            "game": ["g1"] * 2,
            "team": ["TeamA"] * 2,
            "overall": [85, 80],
            "potential": [88, 85],
            "positions": ["ST", "CM"],
            "pace": [88, 72],
            "shooting": [86, 70],
            "passing": [78, 82],
            "dribbling": [84, 80],
            "defending": [40, 72],
            "physic": [76, 68],
            "skill_moves": [4, 3],
            "weak_foot": [4, 3],
        })
        result = _compute_fifa_xi_features(xi_data)
        row = result[
            (result["game"] == "g1") & (result["team"] == "TeamA")
        ]
        assert row["avg_pace_xi"].iloc[0] == pytest.approx((88 + 72) / 2)
        assert row["avg_shooting_xi"].iloc[0] == pytest.approx(
            (86 + 70) / 2,
        )

    def test_empty_input_returns_empty(self) -> None:
        """Empty DataFrame input returns empty DataFrame."""
        result = _compute_fifa_xi_features(pd.DataFrame())
        assert result.empty


# ---------------------------------------------------------------------------
# _compute_market_value_features
# ---------------------------------------------------------------------------

class TestComputeMarketValueFeatures:
    """Tests for market value feature computation."""

    def test_total_value_eur_xi(self) -> None:
        """Total value of XI is computed correctly."""
        xi_data = pd.DataFrame({
            "game": ["g1"] * 3,
            "team": ["TeamA"] * 3,
            "value_eur": [40000000, 25000000, 10000000],
            "wage_eur": [200000, 120000, 50000],
        })
        result = _compute_market_value_features(xi_data)
        row = result[
            (result["game"] == "g1") & (result["team"] == "TeamA")
        ]
        assert row["total_value_eur_xi"].iloc[0] == 75000000

    def test_total_wage_eur_xi(self) -> None:
        """Total wage of XI is computed correctly."""
        xi_data = pd.DataFrame({
            "game": ["g1"] * 3,
            "team": ["TeamA"] * 3,
            "value_eur": [40000000, 25000000, 10000000],
            "wage_eur": [200000, 120000, 50000],
        })
        result = _compute_market_value_features(xi_data)
        row = result[
            (result["game"] == "g1") & (result["team"] == "TeamA")
        ]
        assert row["total_wage_eur_xi"].iloc[0] == 370000

    def test_avg_value_eur_xi(self) -> None:
        """Average value of XI is computed correctly."""
        xi_data = pd.DataFrame({
            "game": ["g1"] * 3,
            "team": ["TeamA"] * 3,
            "value_eur": [40000000, 25000000, 10000000],
            "wage_eur": [200000, 120000, 50000],
        })
        result = _compute_market_value_features(xi_data)
        row = result[
            (result["game"] == "g1") & (result["team"] == "TeamA")
        ]
        assert row["avg_value_eur_xi"].iloc[0] == pytest.approx(25000000)

    def test_max_value_eur_xi(self) -> None:
        """Max value player in XI is identified."""
        xi_data = pd.DataFrame({
            "game": ["g1"] * 3,
            "team": ["TeamA"] * 3,
            "value_eur": [40000000, 25000000, 10000000],
            "wage_eur": [200000, 120000, 50000],
        })
        result = _compute_market_value_features(xi_data)
        row = result[
            (result["game"] == "g1") & (result["team"] == "TeamA")
        ]
        assert row["max_value_eur_xi"].iloc[0] == 40000000

    def test_empty_input_returns_empty(self) -> None:
        """Empty input returns empty DataFrame."""
        result = _compute_market_value_features(pd.DataFrame())
        assert result.empty


# ---------------------------------------------------------------------------
# _build_xi_fifa_stats
# ---------------------------------------------------------------------------

class TestBuildXiFifaStats:
    """Tests for building XI FIFA stats from player matches and ratings."""

    def test_filters_active_players(
        self,
        player_matches_df: pd.DataFrame,
        fifa_ratings_df: pd.DataFrame,
    ) -> None:
        """Only players with minutes > 0 are included."""
        pm = player_matches_df.copy()
        pm.loc[0, "minutes"] = 0
        result = _build_xi_fifa_stats(pm, fifa_ratings_df)
        player_names = result["player"].unique()
        assert "John Smith" not in player_names

    def test_includes_fifa_attributes(
        self,
        player_matches_df: pd.DataFrame,
        fifa_ratings_df: pd.DataFrame,
    ) -> None:
        """Result includes FIFA attribute columns."""
        result = _build_xi_fifa_stats(player_matches_df, fifa_ratings_df)
        assert "overall" in result.columns
        assert "pace" in result.columns
        assert "shooting" in result.columns


# ---------------------------------------------------------------------------
# _compute_bench_strength
# ---------------------------------------------------------------------------

class TestComputeBenchStrength:
    """Tests for bench strength computation."""

    def test_bench_avg_overall(
        self,
        fifa_ratings_df: pd.DataFrame,
    ) -> None:
        """Bench average is computed from squad minus XI players."""
        xi_players = pd.DataFrame({
            "game": ["g1"] * 3,
            "team": ["TeamA"] * 3,
            "player": ["John Smith", "Jane Doe", "Bob Keeper"],
        })
        result = _compute_bench_strength(
            xi_players, fifa_ratings_df,
        )
        team_a_row = result[result["team"] == "TeamA"]
        assert len(team_a_row) == 1
        assert team_a_row["bench_avg_overall"].iloc[0] == pytest.approx(72.0)

    def test_no_bench_players_returns_nan(self) -> None:
        """No bench players returns NaN for bench_avg_overall."""
        xi_players = pd.DataFrame({
            "game": ["g1"],
            "team": ["TeamC"],
            "player": ["Player X"],
        })
        fifa = pd.DataFrame({
            "player_name": ["Player X"],
            "club_name": ["TeamC"],
            "overall": [85],
            "fifa_version": ["24"],
            "positions": ["ST"],
        })
        result = _compute_bench_strength(xi_players, fifa)
        team_row = result[result["team"] == "TeamC"]
        assert pd.isna(team_row["bench_avg_overall"].iloc[0])


# ---------------------------------------------------------------------------
# add_match_player_quality (orchestrator)
# ---------------------------------------------------------------------------

class TestAddMatchPlayerQuality:
    """Tests for the orchestrator function."""

    def test_returns_dataframe(
        self,
        match_df: pd.DataFrame,
        football_db: FootballDatabase,
        multi_game_player_matches: pd.DataFrame,
        multi_game_fifa_ratings: pd.DataFrame,
    ) -> None:
        """Returns a DataFrame."""
        football_db.upsert_dataframe(
            "player_matches", multi_game_player_matches,
        )
        football_db.upsert_dataframe(
            "fifa_ratings", multi_game_fifa_ratings,
        )
        result = add_match_player_quality(match_df, football_db)
        assert isinstance(result, pd.DataFrame)

    def test_empty_df_returns_empty(
        self,
        football_db: FootballDatabase,
    ) -> None:
        """Empty input DataFrame returns empty DataFrame."""
        result = add_match_player_quality(pd.DataFrame(), football_db)
        assert result.empty

    def test_no_player_matches_returns_copy(
        self,
        match_df: pd.DataFrame,
        football_db: FootballDatabase,
    ) -> None:
        """No player_matches data returns input unchanged."""
        result = add_match_player_quality(match_df, football_db)
        assert len(result) == len(match_df)

    def test_home_away_prefix_columns(
        self,
        match_df: pd.DataFrame,
        football_db: FootballDatabase,
        multi_game_player_matches: pd.DataFrame,
        multi_game_fifa_ratings: pd.DataFrame,
    ) -> None:
        """Output has home_ and away_ prefixed columns."""
        football_db.upsert_dataframe(
            "player_matches", multi_game_player_matches,
        )
        football_db.upsert_dataframe(
            "fifa_ratings", multi_game_fifa_ratings,
        )
        result = add_match_player_quality(match_df, football_db)
        home_cols = [c for c in result.columns if c.startswith("home_")]
        away_cols = [c for c in result.columns if c.startswith("away_")]
        new_home = [
            c for c in home_cols if c not in match_df.columns
        ]
        new_away = [
            c for c in away_cols if c not in match_df.columns
        ]
        assert len(new_home) > 0
        assert len(new_away) > 0

    def test_fifa_match_rate_column_present(
        self,
        match_df: pd.DataFrame,
        football_db: FootballDatabase,
        multi_game_player_matches: pd.DataFrame,
        multi_game_fifa_ratings: pd.DataFrame,
    ) -> None:
        """FIFA match rate column is present in output."""
        football_db.upsert_dataframe(
            "player_matches", multi_game_player_matches,
        )
        football_db.upsert_dataframe(
            "fifa_ratings", multi_game_fifa_ratings,
        )
        result = add_match_player_quality(match_df, football_db)
        assert "home_fifa_match_rate_xi" in result.columns
        assert "away_fifa_match_rate_xi" in result.columns

    def test_preserves_original_columns(
        self,
        match_df: pd.DataFrame,
        football_db: FootballDatabase,
        multi_game_player_matches: pd.DataFrame,
        multi_game_fifa_ratings: pd.DataFrame,
    ) -> None:
        """Original match columns are preserved."""
        football_db.upsert_dataframe(
            "player_matches", multi_game_player_matches,
        )
        football_db.upsert_dataframe(
            "fifa_ratings", multi_game_fifa_ratings,
        )
        result = add_match_player_quality(match_df, football_db)
        for col in match_df.columns:
            assert col in result.columns

    def test_row_count_preserved(
        self,
        match_df: pd.DataFrame,
        football_db: FootballDatabase,
        multi_game_player_matches: pd.DataFrame,
        multi_game_fifa_ratings: pd.DataFrame,
    ) -> None:
        """Number of rows is preserved after adding features."""
        football_db.upsert_dataframe(
            "player_matches", multi_game_player_matches,
        )
        football_db.upsert_dataframe(
            "fifa_ratings", multi_game_fifa_ratings,
        )
        result = add_match_player_quality(match_df, football_db)
        assert len(result) == len(match_df)

    def test_no_fifa_data_returns_copy(
        self,
        match_df: pd.DataFrame,
        football_db: FootballDatabase,
        multi_game_player_matches: pd.DataFrame,
    ) -> None:
        """No FIFA ratings returns input unchanged."""
        football_db.upsert_dataframe(
            "player_matches", multi_game_player_matches,
        )
        result = add_match_player_quality(match_df, football_db)
        assert len(result) == len(match_df)
