"""Tests for the player features module (FIFA ratings aggregation)."""

from pathlib import Path

import pandas as pd
import pytest
from ml_in_sports.features.player_features import (
    aggregate_squad_features,
    build_player_features,
    classify_position_group,
    fifa_version_to_season,
    load_ea_fc24_csv,
    load_ea_fc25_csv,
    load_sofifa_csv,
    normalize_player_dataframe,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sofifa_csv(tmp_path: Path) -> Path:
    """Create a minimal sofifa-format CSV (like players_15.csv)."""
    csv_path = tmp_path / "players_15.csv"
    data = pd.DataFrame({
        "sofifa_id": [1, 2, 3, 4, 5],
        "short_name": ["A", "B", "C", "D", "E"],
        "club_name": [
            "FC Barcelona", "FC Barcelona", "FC Barcelona",
            "Real Madrid CF", "Real Madrid CF",
        ],
        "overall": [93, 85, 78, 90, 82],
        "potential": [95, 88, 82, 90, 86],
        "age": [27, 25, 22, 29, 24],
        "player_positions": ["CF", "CB, LB", "GK", "LW, LM", "CM, CDM"],
        "league_name": ["Spain Primera Division"] * 5,
        "league_level": [1] * 5,
        "pace": [85, 60, 40, 90, 70],
        "shooting": [92, 45, 15, 88, 72],
        "passing": [88, 55, 30, 82, 80],
        "dribbling": [96, 60, 25, 90, 78],
        "defending": [35, 82, 20, 40, 75],
        "physic": [70, 78, 65, 72, 76],
        "attacking_finishing": [95, 30, 10, 88, 65],
        "defending_standing_tackle": [30, 85, 15, 35, 78],
        "goalkeeping_reflexes": [10, 8, 88, 7, 9],
        "mentality_composure": [95, 78, 65, 88, 80],
        "mentality_vision": [92, 55, 30, 82, 84],
        "power_stamina": [72, 80, 50, 78, 85],
        "movement_sprint_speed": [82, 58, 38, 88, 68],
        "value_eur": [120000000, 40000000, 10000000, 100000000, 50000000],
        "wage_eur": [560000, 120000, 30000, 480000, 100000],
        "skill_moves": [4, 2, 1, 4, 3],
        "weak_foot": [4, 3, 2, 3, 4],
        "international_reputation": [5, 3, 1, 5, 3],
    })
    data.to_csv(csv_path, index=False)
    return csv_path


@pytest.fixture
def sofifa_csv_with_version(tmp_path: Path) -> Path:
    """Create a minimal sofifa CSV with fifa_version column."""
    csv_path = tmp_path / "male_players_23.csv"
    data = pd.DataFrame({
        "player_id": [1, 2, 3],
        "short_name": ["A", "B", "C"],
        "club_name": [
            "Manchester City", "Manchester City", "Arsenal",
        ],
        "overall": [91, 84, 88],
        "potential": [91, 88, 90],
        "age": [35, 25, 30],
        "player_positions": ["RW", "CB", "ST"],
        "league_name": ["English Premier League"] * 3,
        "league_level": [1] * 3,
        "fifa_version": [23, 23, 23],
        "fifa_update": [9, 9, 9],
        "pace": [80, 55, 85],
        "shooting": [85, 40, 90],
    })
    data.to_csv(csv_path, index=False)
    return csv_path


@pytest.fixture
def ea_fc24_csv(tmp_path: Path) -> Path:
    """Create a minimal EA FC24-format CSV."""
    csv_path = tmp_path / "male_players.csv"
    data = pd.DataFrame({
        "Name": ["X", "Y", "Z"],
        "Club": ["Paris SG", "Paris SG", "Marseille"],
        "Overall": [91, 83, 85],
        "Age": [24, 28, 26],
        "Position": ["ST", "GK", "CM"],
        "Pace": [95, 40, 75],
        "Shooting": [90, 15, 78],
        "Passing": [82, 30, 85],
        "Dribbling": [92, 20, 80],
        "Defending": [35, 18, 72],
        "Physicality": [80, 70, 76],
        "Finishing": [93, 10, 70],
        "Composure": [90, 65, 78],
        "Vision": [85, 25, 82],
        "Stamina": [78, 50, 85],
        "Sprint": [93, 38, 72],
        "Weak foot": [4, 3, 4],
        "Skill moves": [5, 1, 3],
    })
    data.to_csv(csv_path, index=False)
    return csv_path


@pytest.fixture
def ea_fc25_csv(tmp_path: Path) -> Path:
    """Create a minimal EA FC25-format CSV."""
    csv_path = tmp_path / "male_players.csv"
    data = pd.DataFrame({
        "Name": ["P", "Q", "R", "S"],
        "Team": [
            "Manchester City", "Manchester City",
            "Liverpool", "Liverpool",
        ],
        "OVR": [91, 84, 88, 80],
        "Age": [28, 25, 30, 22],
        "Position": ["CDM", "ST", "LW", "GK"],
        "League": ["Premier League"] * 4,
        "Alternative positions": ["CM", "", "LM, CF", ""],
        "PAC": [70, 88, 90, 42],
        "SHO": [72, 90, 85, 15],
        "PAS": [88, 65, 78, 28],
        "DRI": [82, 85, 90, 20],
        "DEF": [85, 40, 35, 18],
        "PHY": [82, 78, 72, 68],
        "Composure": [88, 80, 85, 60],
        "Vision": [90, 65, 82, 25],
        "Stamina": [88, 80, 82, 50],
        "Sprint Speed": [68, 85, 88, 40],
        "Finishing": [65, 92, 88, 10],
        "Standing Tackle": [85, 35, 30, 12],
        "GK Reflexes": [10, 8, 7, 88],
        "Weak foot": [4, 4, 3, 3],
        "Skill moves": [3, 4, 4, 1],
    })
    data.to_csv(csv_path, index=False)
    return csv_path


@pytest.fixture
def squad_df() -> pd.DataFrame:
    """Normalized player DataFrame for a single team/season."""
    return pd.DataFrame({
        "club_name": ["TeamA"] * 5,
        "overall": [90, 85, 78, 82, 70],
        "potential": [90, 88, 84, 85, 78],
        "age": [30, 25, 22, 27, 20],
        "position_group": ["FWD", "DEF", "GK", "MID", "DEF"],
    })


@pytest.fixture
def squad_df_extended() -> pd.DataFrame:
    """Normalized player DataFrame with extended attributes."""
    return pd.DataFrame({
        "club_name": ["TeamA"] * 5,
        "season": ["2122"] * 5,
        "overall": [90, 85, 78, 82, 70],
        "potential": [90, 88, 84, 85, 78],
        "age": [30, 25, 22, 27, 20],
        "position_group": ["FWD", "DEF", "GK", "MID", "DEF"],
        "pace": [88, 62, 42, 72, 58],
        "shooting": [92, 48, 15, 72, 40],
        "passing": [85, 58, 30, 82, 55],
        "dribbling": [94, 62, 25, 80, 52],
        "defending": [38, 84, 20, 72, 78],
        "physic": [72, 80, 65, 76, 74],
        "attacking_finishing": [95, 35, 10, 68, 30],
        "defending_standing_tackle": [32, 86, 15, 75, 82],
        "goalkeeping_reflexes": [10, 8, 90, 7, 9],
        "mentality_composure": [92, 78, 65, 82, 68],
        "mentality_vision": [90, 55, 30, 85, 48],
        "power_stamina": [72, 82, 50, 85, 78],
        "movement_sprint_speed": [85, 60, 38, 70, 55],
        "value_eur": [120000000, 40000000, 10000000, 50000000, 15000000],
        "wage_eur": [500000, 120000, 30000, 100000, 40000],
        "skill_moves": [4, 2, 1, 3, 2],
        "weak_foot": [4, 3, 2, 4, 3],
        "international_reputation": [5, 3, 1, 4, 2],
    })


@pytest.fixture
def fifa_dir_with_sofifa(tmp_path: Path, sofifa_csv: Path) -> Path:
    """FIFA directory containing one sofifa CSV in expected structure."""
    fifa_dir = tmp_path / "fifa"
    datasets_dir = fifa_dir / "fifa_2022_datasets"
    datasets_dir.mkdir(parents=True)
    sofifa_csv.rename(datasets_dir / "players_15.csv")
    return fifa_dir


# ---------------------------------------------------------------------------
# fifa_version_to_season
# ---------------------------------------------------------------------------

class TestFifaVersionToSeason:
    """Tests for FIFA version to season code mapping."""

    def test_fifa_15(self) -> None:
        """FIFA 15 maps to season 1415."""
        assert fifa_version_to_season(15) == "1415"

    def test_fifa_22(self) -> None:
        """FIFA 22 maps to season 2122."""
        assert fifa_version_to_season(22) == "2122"

    def test_fifa_23(self) -> None:
        """FIFA 23 maps to season 2223."""
        assert fifa_version_to_season(23) == "2223"

    def test_fc_24(self) -> None:
        """FC 24 maps to season 2324."""
        assert fifa_version_to_season(24) == "2324"

    def test_fc_25(self) -> None:
        """FC 25 maps to season 2425."""
        assert fifa_version_to_season(25) == "2425"

    def test_fc_26(self) -> None:
        """FC 26 maps to season 2526."""
        assert fifa_version_to_season(26) == "2526"


# ---------------------------------------------------------------------------
# classify_position_group
# ---------------------------------------------------------------------------

class TestClassifyPositionGroup:
    """Tests for position group classification."""

    def test_goalkeeper(self) -> None:
        """GK is classified as goalkeeper."""
        assert classify_position_group("GK") == "GK"

    def test_defender(self) -> None:
        """CB is classified as defender."""
        assert classify_position_group("CB") == "DEF"

    def test_midfielder(self) -> None:
        """CM is classified as midfielder."""
        assert classify_position_group("CM") == "MID"

    def test_forward(self) -> None:
        """ST is classified as forward."""
        assert classify_position_group("ST") == "FWD"

    def test_multi_position_uses_first(self) -> None:
        """Multi-position string uses first position."""
        assert classify_position_group("CB, LB") == "DEF"

    def test_left_wing(self) -> None:
        """LW is classified as forward."""
        assert classify_position_group("LW") == "FWD"

    def test_cdm(self) -> None:
        """CDM is classified as midfielder."""
        assert classify_position_group("CDM") == "MID"

    def test_unknown_returns_none(self) -> None:
        """Unknown position returns None."""
        assert classify_position_group("") is None

    def test_nan_returns_none(self) -> None:
        """NaN value returns None."""
        assert classify_position_group(None) is None


# ---------------------------------------------------------------------------
# load_sofifa_csv
# ---------------------------------------------------------------------------

class TestLoadSofifaCsv:
    """Tests for loading sofifa-format CSV files."""

    def test_loads_correct_columns(self, sofifa_csv: Path) -> None:
        """Result has the expected standardized columns."""
        result = load_sofifa_csv(sofifa_csv, fifa_version=15)
        expected = {
            "club_name", "overall", "potential", "age",
            "player_positions", "season",
        }
        assert expected.issubset(set(result.columns))

    def test_assigns_season(self, sofifa_csv: Path) -> None:
        """Season column is set correctly from FIFA version."""
        result = load_sofifa_csv(sofifa_csv, fifa_version=15)
        assert (result["season"] == "1415").all()

    def test_row_count_matches(self, sofifa_csv: Path) -> None:
        """All rows are loaded."""
        result = load_sofifa_csv(sofifa_csv, fifa_version=15)
        assert len(result) == 5

    def test_loads_extended_attributes(self, sofifa_csv: Path) -> None:
        """Extended attribute columns are loaded from sofifa CSV."""
        result = load_sofifa_csv(sofifa_csv, fifa_version=15)
        assert "pace" in result.columns
        assert "shooting" in result.columns
        assert "attacking_finishing" in result.columns
        assert "value_eur" in result.columns

    def test_missing_extended_columns_filled_with_na(
        self, tmp_path: Path,
    ) -> None:
        """Missing extended columns are filled with NaN."""
        csv_path = tmp_path / "minimal.csv"
        data = pd.DataFrame({
            "club_name": ["TeamA"],
            "overall": [85],
            "potential": [88],
            "age": [25],
            "player_positions": ["CM"],
        })
        data.to_csv(csv_path, index=False)
        result = load_sofifa_csv(csv_path, fifa_version=15)
        assert pd.isna(result["pace"].iloc[0])


class TestLoadSofifaCsvWithVersion:
    """Tests for loading sofifa CSV with fifa_version column."""

    def test_loads_and_uses_version_column(
        self, sofifa_csv_with_version: Path,
    ) -> None:
        """Reads fifa_version from the CSV data."""
        result = load_sofifa_csv(sofifa_csv_with_version, fifa_version=23)
        assert (result["season"] == "2223").all()


# ---------------------------------------------------------------------------
# load_ea_fc24_csv
# ---------------------------------------------------------------------------

class TestLoadEaFc24Csv:
    """Tests for loading EA FC24-format CSV files."""

    def test_loads_correct_columns(self, ea_fc24_csv: Path) -> None:
        """Result has standardized columns."""
        result = load_ea_fc24_csv(ea_fc24_csv)
        expected = {"club_name", "overall", "age", "player_positions", "season"}
        assert expected.issubset(set(result.columns))

    def test_assigns_season_2324(self, ea_fc24_csv: Path) -> None:
        """Season is set to 2324 for FC24."""
        result = load_ea_fc24_csv(ea_fc24_csv)
        assert (result["season"] == "2324").all()

    def test_row_count_matches(self, ea_fc24_csv: Path) -> None:
        """All rows are loaded."""
        result = load_ea_fc24_csv(ea_fc24_csv)
        assert len(result) == 3

    def test_maps_extended_attributes(self, ea_fc24_csv: Path) -> None:
        """FC24 attributes are mapped to standard column names."""
        result = load_ea_fc24_csv(ea_fc24_csv)
        assert "pace" in result.columns
        assert "shooting" in result.columns
        assert "physic" in result.columns
        assert "mentality_composure" in result.columns

    def test_fc24_pace_values_mapped(self, ea_fc24_csv: Path) -> None:
        """FC24 Pace column values are correctly mapped."""
        result = load_ea_fc24_csv(ea_fc24_csv)
        assert result["pace"].iloc[0] == 95


# ---------------------------------------------------------------------------
# load_ea_fc25_csv
# ---------------------------------------------------------------------------

class TestLoadEaFc25Csv:
    """Tests for loading EA FC25-format CSV files."""

    def test_loads_correct_columns(self, ea_fc25_csv: Path) -> None:
        """Result has standardized columns."""
        result = load_ea_fc25_csv(ea_fc25_csv)
        expected = {"club_name", "overall", "age", "player_positions", "season"}
        assert expected.issubset(set(result.columns))

    def test_assigns_season_2425(self, ea_fc25_csv: Path) -> None:
        """Season is set to 2425 for FC25."""
        result = load_ea_fc25_csv(ea_fc25_csv)
        assert (result["season"] == "2425").all()

    def test_maps_extended_attributes(self, ea_fc25_csv: Path) -> None:
        """FC25 attributes are mapped to standard column names."""
        result = load_ea_fc25_csv(ea_fc25_csv)
        assert "pace" in result.columns
        assert "shooting" in result.columns
        assert "physic" in result.columns
        assert "goalkeeping_reflexes" in result.columns

    def test_fc25_gk_reflexes_mapped(self, ea_fc25_csv: Path) -> None:
        """FC25 GK Reflexes column values are correctly mapped."""
        result = load_ea_fc25_csv(ea_fc25_csv)
        gk_row = result[result["player_positions"] == "GK"].iloc[0]
        assert gk_row["goalkeeping_reflexes"] == 88


# ---------------------------------------------------------------------------
# normalize_player_dataframe
# ---------------------------------------------------------------------------

class TestNormalizePlayerDataframe:
    """Tests for normalize_player_dataframe."""

    def test_adds_position_group_column(self, sofifa_csv: Path) -> None:
        """Position group column is added."""
        raw = load_sofifa_csv(sofifa_csv, fifa_version=15)
        result = normalize_player_dataframe(raw)
        assert "position_group" in result.columns

    def test_normalizes_club_names(self, sofifa_csv: Path) -> None:
        """Club names are normalized to canonical form."""
        raw = load_sofifa_csv(sofifa_csv, fifa_version=15)
        result = normalize_player_dataframe(raw)
        clubs = result["club_name"].unique().tolist()
        assert "Barcelona" in clubs
        assert "Real Madrid" in clubs


# ---------------------------------------------------------------------------
# aggregate_squad_features (original)
# ---------------------------------------------------------------------------

class TestAggregateSquadFeatures:
    """Tests for aggregate_squad_features."""

    def test_returns_one_row_per_team_season(
        self, squad_df: pd.DataFrame,
    ) -> None:
        """Aggregation produces one row per team."""
        squad_df["season"] = "2122"
        result = aggregate_squad_features(squad_df)
        assert len(result) == 1

    def test_avg_overall_computed(self, squad_df: pd.DataFrame) -> None:
        """Average overall rating is computed correctly."""
        squad_df["season"] = "2122"
        result = aggregate_squad_features(squad_df)
        expected_avg = (90 + 85 + 78 + 82 + 70) / 5
        assert result["avg_overall"].iloc[0] == pytest.approx(expected_avg)

    def test_avg_potential_computed(self, squad_df: pd.DataFrame) -> None:
        """Average potential rating is computed correctly."""
        squad_df["season"] = "2122"
        result = aggregate_squad_features(squad_df)
        expected_avg = (90 + 88 + 84 + 85 + 78) / 5
        assert result["avg_potential"].iloc[0] == pytest.approx(expected_avg)

    def test_squad_depth_counts_above_75(
        self, squad_df: pd.DataFrame,
    ) -> None:
        """Squad depth counts players with overall > 75."""
        squad_df["season"] = "2122"
        result = aggregate_squad_features(squad_df)
        assert result["squad_depth"].iloc[0] == 4

    def test_top_player_rating(self, squad_df: pd.DataFrame) -> None:
        """Top player rating is the max overall."""
        squad_df["season"] = "2122"
        result = aggregate_squad_features(squad_df)
        assert result["top_player_rating"].iloc[0] == 90

    def test_avg_age_computed(self, squad_df: pd.DataFrame) -> None:
        """Average age is computed correctly."""
        squad_df["season"] = "2122"
        result = aggregate_squad_features(squad_df)
        expected_avg = (30 + 25 + 22 + 27 + 20) / 5
        assert result["avg_age"].iloc[0] == pytest.approx(expected_avg)

    def test_positional_ratings(self, squad_df: pd.DataFrame) -> None:
        """Positional average ratings are computed correctly."""
        squad_df["season"] = "2122"
        result = aggregate_squad_features(squad_df)
        assert result["avg_gk_rating"].iloc[0] == pytest.approx(78.0)
        assert result["avg_def_rating"].iloc[0] == pytest.approx(
            (85 + 70) / 2,
        )
        assert result["avg_mid_rating"].iloc[0] == pytest.approx(82.0)
        assert result["avg_fwd_rating"].iloc[0] == pytest.approx(90.0)

    def test_output_columns(self, squad_df: pd.DataFrame) -> None:
        """Output DataFrame has all expected feature columns."""
        squad_df["season"] = "2122"
        result = aggregate_squad_features(squad_df)
        expected_columns = [
            "club_name", "season", "avg_overall", "avg_potential",
            "squad_depth", "top_player_rating", "avg_age",
            "avg_gk_rating", "avg_def_rating",
            "avg_mid_rating", "avg_fwd_rating",
        ]
        for col in expected_columns:
            assert col in result.columns, f"Missing column: {col}"


# ---------------------------------------------------------------------------
# aggregate_squad_features (extended attributes)
# ---------------------------------------------------------------------------

class TestAggregateExtendedAttributes:
    """Tests for extended attribute aggregation."""

    def test_avg_main_attributes(
        self, squad_df_extended: pd.DataFrame,
    ) -> None:
        """Main 6 attribute averages are computed correctly."""
        result = aggregate_squad_features(squad_df_extended)
        expected_pace = (88 + 62 + 42 + 72 + 58) / 5
        assert result["avg_pace"].iloc[0] == pytest.approx(expected_pace)
        expected_shooting = (92 + 48 + 15 + 72 + 40) / 5
        assert result["avg_shooting"].iloc[0] == pytest.approx(
            expected_shooting,
        )

    def test_avg_stamina(self, squad_df_extended: pd.DataFrame) -> None:
        """Average stamina is computed correctly."""
        result = aggregate_squad_features(squad_df_extended)
        expected = (72 + 82 + 50 + 85 + 78) / 5
        assert result["avg_stamina"].iloc[0] == pytest.approx(expected)

    def test_avg_sprint_speed(
        self, squad_df_extended: pd.DataFrame,
    ) -> None:
        """Average sprint speed is computed correctly."""
        result = aggregate_squad_features(squad_df_extended)
        expected = (85 + 60 + 38 + 70 + 55) / 5
        assert result["avg_sprint_speed"].iloc[0] == pytest.approx(expected)

    def test_avg_composure(
        self, squad_df_extended: pd.DataFrame,
    ) -> None:
        """Average composure is computed correctly."""
        result = aggregate_squad_features(squad_df_extended)
        expected = (92 + 78 + 65 + 82 + 68) / 5
        assert result["avg_composure"].iloc[0] == pytest.approx(expected)

    def test_avg_vision(self, squad_df_extended: pd.DataFrame) -> None:
        """Average vision is computed correctly."""
        result = aggregate_squad_features(squad_df_extended)
        expected = (90 + 55 + 30 + 85 + 48) / 5
        assert result["avg_vision"].iloc[0] == pytest.approx(expected)

    def test_avg_fwd_finishing(
        self, squad_df_extended: pd.DataFrame,
    ) -> None:
        """Average finishing for forwards is computed correctly."""
        result = aggregate_squad_features(squad_df_extended)
        assert result["avg_fwd_finishing"].iloc[0] == pytest.approx(95.0)

    def test_avg_def_standing_tackle(
        self, squad_df_extended: pd.DataFrame,
    ) -> None:
        """Average standing tackle for defenders is computed correctly."""
        result = aggregate_squad_features(squad_df_extended)
        expected = (86 + 82) / 2
        assert result["avg_def_standing_tackle"].iloc[0] == pytest.approx(
            expected,
        )

    def test_avg_gk_reflexes(
        self, squad_df_extended: pd.DataFrame,
    ) -> None:
        """Average reflexes for goalkeepers is computed correctly."""
        result = aggregate_squad_features(squad_df_extended)
        assert result["avg_gk_reflexes"].iloc[0] == pytest.approx(90.0)

    def test_total_value_eur(
        self, squad_df_extended: pd.DataFrame,
    ) -> None:
        """Total squad value is computed correctly."""
        result = aggregate_squad_features(squad_df_extended)
        expected = 120000000 + 40000000 + 10000000 + 50000000 + 15000000
        assert result["total_value_eur"].iloc[0] == pytest.approx(expected)

    def test_total_wage_eur(
        self, squad_df_extended: pd.DataFrame,
    ) -> None:
        """Total squad wage is computed correctly."""
        result = aggregate_squad_features(squad_df_extended)
        expected = 500000 + 120000 + 30000 + 100000 + 40000
        assert result["total_wage_eur"].iloc[0] == pytest.approx(expected)

    def test_avg_skill_moves(
        self, squad_df_extended: pd.DataFrame,
    ) -> None:
        """Average skill moves is computed correctly."""
        result = aggregate_squad_features(squad_df_extended)
        expected = (4 + 2 + 1 + 3 + 2) / 5
        assert result["avg_skill_moves"].iloc[0] == pytest.approx(expected)

    def test_avg_weak_foot(
        self, squad_df_extended: pd.DataFrame,
    ) -> None:
        """Average weak foot is computed correctly."""
        result = aggregate_squad_features(squad_df_extended)
        expected = (4 + 3 + 2 + 4 + 3) / 5
        assert result["avg_weak_foot"].iloc[0] == pytest.approx(expected)

    def test_avg_international_reputation(
        self, squad_df_extended: pd.DataFrame,
    ) -> None:
        """Average international reputation is computed correctly."""
        result = aggregate_squad_features(squad_df_extended)
        expected = (5 + 3 + 1 + 4 + 2) / 5
        assert result["avg_international_reputation"].iloc[0] == (
            pytest.approx(expected)
        )

    def test_missing_extended_columns_produce_nan(
        self, squad_df: pd.DataFrame,
    ) -> None:
        """Missing extended attribute columns produce NaN in output."""
        squad_df["season"] = "2122"
        result = aggregate_squad_features(squad_df)
        assert pd.isna(result["avg_pace"].iloc[0])
        assert pd.isna(result["total_value_eur"].iloc[0])

    def test_extended_output_columns(
        self, squad_df_extended: pd.DataFrame,
    ) -> None:
        """Output has all expected extended feature columns."""
        result = aggregate_squad_features(squad_df_extended)
        extended_columns = [
            "avg_pace", "avg_shooting", "avg_passing",
            "avg_dribbling", "avg_defending", "avg_physic",
            "avg_stamina", "avg_sprint_speed",
            "avg_composure", "avg_vision",
            "avg_fwd_finishing", "avg_def_standing_tackle",
            "avg_gk_reflexes",
            "total_value_eur", "total_wage_eur",
            "avg_skill_moves", "avg_weak_foot",
            "avg_international_reputation",
        ]
        for col in extended_columns:
            assert col in result.columns, f"Missing column: {col}"


# ---------------------------------------------------------------------------
# build_player_features (integration)
# ---------------------------------------------------------------------------

class TestBuildPlayerFeatures:
    """Tests for the build_player_features orchestrator."""

    def test_returns_dataframe(
        self, fifa_dir_with_sofifa: Path,
    ) -> None:
        """Returns a DataFrame."""
        result = build_player_features(fifa_dir_with_sofifa)
        assert isinstance(result, pd.DataFrame)

    def test_has_team_and_season_columns(
        self, fifa_dir_with_sofifa: Path,
    ) -> None:
        """Output has team and season columns for joining."""
        result = build_player_features(fifa_dir_with_sofifa)
        assert "club_name" in result.columns
        assert "season" in result.columns

    def test_returns_empty_for_missing_dir(self, tmp_path: Path) -> None:
        """Returns empty DataFrame when FIFA dir does not exist."""
        result = build_player_features(tmp_path / "nonexistent")
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_has_feature_columns(
        self, fifa_dir_with_sofifa: Path,
    ) -> None:
        """Output has expected feature columns."""
        result = build_player_features(fifa_dir_with_sofifa)
        feature_columns = [
            "avg_overall", "squad_depth", "top_player_rating",
            "avg_age",
        ]
        for col in feature_columns:
            assert col in result.columns, f"Missing column: {col}"

    def test_has_extended_feature_columns(
        self, fifa_dir_with_sofifa: Path,
    ) -> None:
        """Output has extended feature columns from FIFA data."""
        result = build_player_features(fifa_dir_with_sofifa)
        extended_columns = [
            "avg_pace", "avg_shooting", "total_value_eur",
            "avg_skill_moves",
        ]
        for col in extended_columns:
            assert col in result.columns, f"Missing column: {col}"
