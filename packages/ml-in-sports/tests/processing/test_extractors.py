"""Tests for data extractors."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from ml_in_sports.processing.extractors import (
    ALL_LEAGUES,
    LEAGUE_CONFIG,
    ClubEloExtractor,
    FifaRatingsExtractor,
    FootballDataExtractor,
    SofascoreExtractor,
    TransfermarktExtractor,
    UnderstatExtractor,
    _parse_football_data_csv,
    _pivot_espn_matchsheet,
)


class TestPivotEspnMatchsheet:
    """Tests for ESPN matchsheet pivot logic."""

    def test_pivots_to_one_row_per_match(
        self, espn_matchsheet: pd.DataFrame,
    ) -> None:
        """Two rows (home/away) become one row per match."""
        result = _pivot_espn_matchsheet(espn_matchsheet)
        assert len(result) == 1

    def test_pivot_creates_prefixed_columns(
        self, espn_matchsheet: pd.DataFrame,
    ) -> None:
        """Output has home_ and away_ prefixed columns."""
        result = _pivot_espn_matchsheet(espn_matchsheet)
        assert "home_possession_pct" in result.columns
        assert "away_possession_pct" in result.columns
        assert "home_total_shots" in result.columns
        assert "away_effective_tackles" in result.columns


class TestUnderstatExtractor:
    """Tests for UnderstatExtractor."""

    @patch("ml_in_sports.processing.extractors.sd.Understat")
    def test_extract_matches_returns_dataframe(
        self,
        mock_understat_cls: MagicMock,
        understat_schedule: pd.DataFrame,
        understat_team_match: pd.DataFrame,
    ) -> None:
        """Returns merged DataFrame on success."""
        mock_client = MagicMock()
        mock_client.read_schedule.return_value = understat_schedule
        mock_client.read_team_match_stats.return_value = understat_team_match
        mock_understat_cls.return_value = mock_client

        extractor = UnderstatExtractor()
        result = extractor.extract_matches("ENG-Premier League", "2324")

        assert result is not None
        assert len(result) == 2
        assert "home_xg" in result.columns
        assert "home_ppda" in result.columns

    @patch("ml_in_sports.processing.extractors.sd.Understat")
    def test_extract_matches_returns_none_on_error(
        self, mock_understat_cls: MagicMock,
    ) -> None:
        """Returns None when scraping fails."""
        mock_understat_cls.side_effect = ConnectionError("blocked")

        extractor = UnderstatExtractor()
        result = extractor.extract_matches("ENG-Premier League", "2324")
        assert result is None

    @patch("ml_in_sports.processing.extractors.sd.Understat")
    def test_extract_player_matches_returns_dataframe(
        self, mock_understat_cls: MagicMock,
    ) -> None:
        """Returns player match stats DataFrame."""
        mock_client = MagicMock()
        mock_client.read_player_match_stats.return_value = pd.DataFrame(
            {"player": ["Saka"], "minutes": [90]}
        )
        mock_understat_cls.return_value = mock_client

        extractor = UnderstatExtractor()
        result = extractor.extract_player_matches("ENG-Premier League", "2324")
        assert result is not None
        assert len(result) == 1


class TestSofascoreExtractor:
    """Tests for SofascoreExtractor."""

    @patch("ml_in_sports.processing.extractors.sd.Sofascore")
    def test_extract_league_table(
        self, mock_sofascore_cls: MagicMock,
    ) -> None:
        """Returns league table DataFrame."""
        mock_client = MagicMock()
        mock_client.read_league_table.return_value = pd.DataFrame(
            {"team": ["Arsenal"], "Pts": [90]}
        )
        mock_sofascore_cls.return_value = mock_client

        extractor = SofascoreExtractor()
        result = extractor.extract_league_table("ENG-Premier League", "2324")
        assert result is not None
        assert "Pts" in result.columns


class TestClubEloExtractor:
    """Tests for ClubEloExtractor."""

    @patch("ml_in_sports.processing.extractors.sd.ClubElo")
    def test_extract_ratings(
        self, mock_elo_cls: MagicMock,
    ) -> None:
        """Returns Elo ratings DataFrame."""
        mock_client = MagicMock()
        mock_client.read_by_date.return_value = pd.DataFrame(
            {"elo": [2000.0], "rank": [1]},
            index=pd.Index(["Manchester City"], name="team"),
        )
        mock_elo_cls.return_value = mock_client

        extractor = ClubEloExtractor()
        result = extractor.extract_ratings("2024-01-01")
        assert result is not None
        assert len(result) == 1

    @patch("ml_in_sports.processing.extractors.sd.ClubElo")
    def test_returns_none_on_error(
        self, mock_elo_cls: MagicMock,
    ) -> None:
        """Returns None on connection failure."""
        mock_elo_cls.side_effect = ConnectionError("timeout")

        extractor = ClubEloExtractor()
        result = extractor.extract_ratings("2024-01-01")
        assert result is None


class TestParseFootballDataCsv:
    """Tests for football-data.co.uk CSV parsing."""

    @pytest.fixture
    def raw_new_format(self) -> pd.DataFrame:
        """Raw CSV in new format (19/20+)."""
        return pd.DataFrame({
            "Div": ["E0"],
            "Date": ["11/08/2023"],
            "Time": ["20:00"],
            "HomeTeam": ["Man City"],
            "AwayTeam": ["Burnley"],
            "FTHG": [3],
            "FTAG": [0],
            "FTR": ["H"],
            "HTHG": [2],
            "HTAG": [0],
            "HTR": ["H"],
            "Referee": ["C Pawson"],
            "HS": [17],
            "AS": [6],
            "HC": [5],
            "AC": [6],
            "B365H": [1.33],
            "B365D": [5.5],
            "B365A": [8.0],
            "MaxH": [1.39],
            "AvgH": [1.35],
        })

    @pytest.fixture
    def raw_old_format(self) -> pd.DataFrame:
        """Raw CSV in old format (14/15-18/19)."""
        return pd.DataFrame({
            "Div": ["E0"],
            "Date": ["16/08/2014"],
            "HomeTeam": ["Man United"],
            "AwayTeam": ["Swansea"],
            "FTHG": [1],
            "FTAG": [2],
            "FTR": ["A"],
            "HTHG": [1],
            "HTAG": [1],
            "HTR": ["D"],
            "Referee": ["M Dean"],
            "HS": [18],
            "AS": [11],
            "HC": [7],
            "AC": [3],
            "B365H": [1.33],
            "BbMxH": [1.40],
            "BbAvH": [1.34],
            "BbMxD": [5.80],
            "BbAvD": [5.30],
        })

    def test_new_format_renames_columns(
        self, raw_new_format: pd.DataFrame,
    ) -> None:
        """New format columns are renamed to standard names."""
        result = _parse_football_data_csv(raw_new_format, "2324")

        assert result is not None
        assert "home_team" in result.columns
        assert "away_team" in result.columns
        assert "ft_home_goals" in result.columns
        assert "b365_home" in result.columns
        assert "max_home" in result.columns
        assert "avg_home" in result.columns

    def test_normalizes_team_names(
        self, raw_new_format: pd.DataFrame,
    ) -> None:
        """Team names are normalized to canonical form."""
        result = _parse_football_data_csv(raw_new_format, "2324")

        assert result is not None
        assert result.iloc[0]["home_team"] == "Manchester City"

    def test_builds_game_key(
        self, raw_new_format: pd.DataFrame,
    ) -> None:
        """Builds game key from date and team names."""
        result = _parse_football_data_csv(raw_new_format, "2324")

        assert result is not None
        game = result.iloc[0]["game"]
        assert game == "2023-08-11 Manchester City-Burnley"

    def test_parses_date_format(
        self, raw_new_format: pd.DataFrame,
    ) -> None:
        """Converts DD/MM/YYYY to YYYY-MM-DD."""
        result = _parse_football_data_csv(raw_new_format, "2324")

        assert result is not None
        assert result.iloc[0]["date"] == "2023-08-11"

    def test_old_format_maps_betbrain_to_standard(
        self, raw_old_format: pd.DataFrame,
    ) -> None:
        """Old Betbrain format (BbMx/BbAv) maps to Max/Avg columns."""
        result = _parse_football_data_csv(raw_old_format, "1415")

        assert result is not None
        assert "max_home" in result.columns
        assert result.iloc[0]["max_home"] == 1.40
        assert result.iloc[0]["max_draw"] == 5.80

    def test_adds_league_and_season(
        self, raw_new_format: pd.DataFrame,
    ) -> None:
        """Adds league and season metadata."""
        result = _parse_football_data_csv(raw_new_format, "2324")

        assert result is not None
        assert result.iloc[0]["league"] == "ENG-Premier League"
        assert result.iloc[0]["season"] == "2324"

    def test_drops_div_column(
        self, raw_new_format: pd.DataFrame,
    ) -> None:
        """Drops the Div column (always E0)."""
        result = _parse_football_data_csv(raw_new_format, "2324")

        assert result is not None
        assert "Div" not in result.columns


class TestFifaRatingsExtractor:
    """Tests for FifaRatingsExtractor column detection."""

    def test_normalizes_sofifa_format(self, tmp_path: Path) -> None:
        """Normalizes sofifa-format columns (FIFA 15-24, FC 26)."""
        csv_path = tmp_path / "fc26_players.csv"
        pd.DataFrame({
            "short_name": ["Saka"],
            "long_name": ["Bukayo Saka"],
            "club_name": ["Arsenal"],
            "league_name": ["English Premier League"],
            "overall": [88],
            "pace": [86],
            "player_positions": ["RW"],
        }).to_csv(csv_path, index=False)

        extractor = FifaRatingsExtractor(data_dir=tmp_path)
        result = extractor.extract_ratings("fc26")

        assert result is not None
        assert result.iloc[0]["player_name"] == "Saka"
        assert result.iloc[0]["positions"] == "RW"
        assert result.iloc[0]["fifa_version"] == "fc26"

    def test_normalizes_fc25_format(self, tmp_path: Path) -> None:
        """Normalizes FC 25 easports.com format (Title Case columns)."""
        csv_path = tmp_path / "fc25_players.csv"
        pd.DataFrame({
            "name": ["Saka"],
            "club": ["Arsenal"],
            "league": ["English Premier League"],
            "overall": [87],
            "PAC": [85],
            "SHO": [78],
            "PAS": [80],
            "DRI": [87],
            "DEF": [55],
            "PHY": [68],
            "position": ["RW"],
        }).to_csv(csv_path, index=False)

        extractor = FifaRatingsExtractor(data_dir=tmp_path)
        result = extractor.extract_ratings("fc25")

        assert result is not None
        assert result.iloc[0]["player_name"] == "Saka"
        assert result.iloc[0]["pace"] == 85
        assert result.iloc[0]["positions"] == "RW"

    def test_combined_file_splits_by_version(
        self, tmp_path: Path,
    ) -> None:
        """Combined male_players.csv splits correctly by version."""
        csv_path = tmp_path / "male_players.csv"
        pd.DataFrame({
            "short_name": ["Saka", "Salah"],
            "club_name": ["Arsenal", "Liverpool"],
            "league_name": ["English Premier League"] * 2,
            "overall": [82, 90],
            "fifa_version": [22, 23],
            "fifa_update": [1, 1],
        }).to_csv(csv_path, index=False)

        extractor = FifaRatingsExtractor(data_dir=tmp_path)
        results = extractor.extract_combined_ratings()

        assert "22" in results
        assert "23" in results
        assert len(results["22"]) == 1
        assert results["22"].iloc[0]["player_name"] == "Saka"
        assert results["23"].iloc[0]["player_name"] == "Salah"

    def test_combined_file_keeps_latest_update(
        self, tmp_path: Path,
    ) -> None:
        """Combined file keeps only the latest update per version."""
        csv_path = tmp_path / "male_players.csv"
        pd.DataFrame({
            "short_name": ["Saka", "Saka"],
            "club_name": ["Arsenal", "Arsenal"],
            "league_name": ["English Premier League"] * 2,
            "overall": [80, 82],
            "fifa_version": [23, 23],
            "fifa_update": [1, 5],
        }).to_csv(csv_path, index=False)

        extractor = FifaRatingsExtractor(data_dir=tmp_path)
        results = extractor.extract_combined_ratings()

        assert len(results["23"]) == 1
        assert results["23"].iloc[0]["overall"] == 82

    def test_multi_league_filter(self, tmp_path: Path) -> None:
        """Filters to multiple leagues when configured."""
        csv_path = tmp_path / "fc26_players.csv"
        pd.DataFrame({
            "short_name": ["Saka", "Messi", "Mueller"],
            "club_name": ["Arsenal", "Inter Miami", "Bayern"],
            "league_name": [
                "English Premier League",
                "Major League Soccer",
                "German 1. Bundesliga",
            ],
            "overall": [88, 85, 84],
        }).to_csv(csv_path, index=False)

        extractor = FifaRatingsExtractor(
            data_dir=tmp_path,
            league_filters=["Premier League", "German 1. Bundesliga"],
        )
        result = extractor.extract_ratings("fc26")

        assert result is not None
        assert len(result) == 2

    def test_default_filter_is_epl_only(self, tmp_path: Path) -> None:
        """Default league filter returns only EPL players."""
        csv_path = tmp_path / "fc26_players.csv"
        pd.DataFrame({
            "short_name": ["Saka", "Vinicius"],
            "club_name": ["Arsenal", "Real Madrid"],
            "league_name": [
                "English Premier League",
                "Spain Primera Division",
            ],
            "overall": [88, 91],
        }).to_csv(csv_path, index=False)

        extractor = FifaRatingsExtractor(data_dir=tmp_path)
        result = extractor.extract_ratings("fc26")

        assert result is not None
        assert len(result) == 1
        assert result.iloc[0]["player_name"] == "Saka"


class TestLeagueConfig:
    """Tests for LEAGUE_CONFIG and ALL_LEAGUES."""

    def test_all_leagues_has_five_entries(self) -> None:
        """ALL_LEAGUES contains exactly 5 leagues."""
        assert len(ALL_LEAGUES) == 5

    def test_league_config_has_required_keys(self) -> None:
        """Each league config has all required keys."""
        required = {
            "football_data_code", "tm_competition_id", "fifa_league_filter",
        }
        for league, config in LEAGUE_CONFIG.items():
            assert required.issubset(config.keys()), f"{league} missing keys"

    def test_epl_config_values(self) -> None:
        """EPL config matches expected values."""
        epl = LEAGUE_CONFIG["ENG-Premier League"]
        assert epl["football_data_code"] == "E0"
        assert epl["tm_competition_id"] == "GB1"
        assert epl["fifa_league_filter"] == "Premier League"

    def test_la_liga_config_values(self) -> None:
        """La Liga config matches expected values."""
        config = LEAGUE_CONFIG["ESP-La Liga"]
        assert config["football_data_code"] == "SP1"
        assert config["tm_competition_id"] == "ES1"


class TestParseFootballDataCsvMultiLeague:
    """Tests for _parse_football_data_csv with league parameter."""

    def test_la_liga_league_label(self) -> None:
        """La Liga CSV gets correct league label."""
        raw = pd.DataFrame({
            "Div": ["SP1"],
            "Date": ["13/08/2023"],
            "HomeTeam": ["Barcelona"],
            "AwayTeam": ["Getafe"],
            "FTHG": [4],
            "FTAG": [0],
            "FTR": ["H"],
            "B365H": [1.22],
        })
        result = _parse_football_data_csv(raw, "2324", "ESP-La Liga")

        assert result is not None
        assert result.iloc[0]["league"] == "ESP-La Liga"

    def test_default_league_is_epl(self) -> None:
        """Default league parameter is EPL."""
        raw = pd.DataFrame({
            "Date": ["11/08/2023"],
            "HomeTeam": ["Arsenal"],
            "AwayTeam": ["Chelsea"],
            "FTHG": [2],
            "FTAG": [1],
        })
        result = _parse_football_data_csv(raw, "2324")

        assert result is not None
        assert result.iloc[0]["league"] == "ENG-Premier League"


class TestFootballDataExtractorMultiLeague:
    """Tests for FootballDataExtractor with league parameter."""

    def test_default_league_is_epl(self) -> None:
        """Default league is EPL."""
        extractor = FootballDataExtractor()
        assert extractor._league == "ENG-Premier League"
        assert extractor._code == "E0"

    def test_la_liga_code(self) -> None:
        """La Liga uses SP1 code."""
        extractor = FootballDataExtractor(league="ESP-La Liga")
        assert extractor._code == "SP1"

    def test_bundesliga_code(self) -> None:
        """Bundesliga uses D1 code."""
        extractor = FootballDataExtractor(league="GER-Bundesliga")
        assert extractor._code == "D1"


class TestTransfermarktExtractorMultiLeague:
    """Tests for TransfermarktExtractor with competition_id."""

    def test_default_competition_is_epl(self) -> None:
        """Default competition is GB1 (EPL)."""
        extractor = TransfermarktExtractor()
        assert extractor._competition_id == "GB1"

    def test_custom_competition_id(self) -> None:
        """Custom competition ID is stored."""
        extractor = TransfermarktExtractor(competition_id="ES1")
        assert extractor._competition_id == "ES1"

    @patch("ml_in_sports.processing.extractors._download_tm_csv")
    def test_filters_by_competition_id(
        self, mock_download: MagicMock,
    ) -> None:
        """Filters games by the configured competition_id."""
        mock_download.return_value = pd.DataFrame({
            "competition_id": ["GB1", "ES1", "ES1"],
            "game_id": [1, 2, 3],
            "home_club_name": ["Arsenal", "Barcelona", "Real Madrid"],
        })

        extractor = TransfermarktExtractor(competition_id="ES1")
        result = extractor.extract_games()

        assert result is not None
        assert len(result) == 2
