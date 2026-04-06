"""Tests for Pinnacle closing odds loader."""

from pathlib import Path

import pandas as pd
import pytest
from ml_in_sports.processing.odds.pinnacle import (
    FOOTBALL_DATA_LEAGUE_MAP,
    _parse_csv_location,
    download_season_csv,
    load_football_data_csv,
    load_pinnacle_odds,
)

# ---------------------------------------------------------------------------
# Helpers: minimal CSV content
# ---------------------------------------------------------------------------

_FULL_CSV = (
    "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR,"
    "PSH,PSD,PSA,PSCH,PSCD,PSCA,"
    "MaxH,MaxD,MaxA,MaxCH,MaxCD,MaxCA,"
    "Max>2.5,Max<2.5,MaxC>2.5,MaxC<2.5\n"
    "E0,15/08/2023,Arsenal,Nott'm Forest,2,1,H,"
    "1.30,5.50,10.00,1.28,5.75,11.00,"
    "1.35,5.80,11.50,1.33,6.00,12.00,"
    "1.80,2.10,1.82,2.08\n"
    "E0,15/08/2023,Burnley,Man City,0,3,A,"
    "9.00,5.00,1.35,9.50,5.25,1.33,"
    "10.00,5.50,1.40,10.50,5.75,1.38,"
    "1.90,2.00,1.92,1.98\n"
)

_NO_PINNACLE_CSV = (
    "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR,"
    "BbMxH,BbMxD,BbMxA,BbMx>2.5,BbMx<2.5\n"
    "E0,20/08/2016,Arsenal,Liverpool,3,4,A,"
    "1.90,3.60,4.20,1.75,2.15\n"
)

_OPENING_ONLY_CSV = (
    "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR,"
    "PSH,PSD,PSA,MaxH,MaxD,MaxA\n"
    "E0,10/09/2022,Liverpool,Wolves,3,1,H,"
    "1.25,6.00,12.00,1.30,6.50,13.00\n"
)


def _write_csv(tmp_path: Path, name: str, content: str) -> Path:
    """Write CSV content to a file and return its path."""
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Tests: load_football_data_csv
# ---------------------------------------------------------------------------


class TestLoadFootballDataCsv:
    """Tests for single-file CSV loading."""

    def test_parses_full_csv_with_pinnacle_closing(
        self,
        tmp_path: Path,
    ) -> None:
        """Full CSV with Pinnacle closing odds loads correctly."""
        csv_path = _write_csv(tmp_path, "season.csv", _FULL_CSV)
        result = load_football_data_csv(csv_path)

        assert len(result) == 2
        assert "pinnacle_home" in result.columns
        assert "pinnacle_draw" in result.columns
        assert "pinnacle_away" in result.columns
        assert "max_home" in result.columns
        assert "max_over_25" in result.columns
        assert "max_under_25" in result.columns

    def test_pinnacle_closing_values_are_correct(
        self,
        tmp_path: Path,
    ) -> None:
        """Pinnacle closing values come from PSCH/PSCD/PSCA columns."""
        csv_path = _write_csv(tmp_path, "season.csv", _FULL_CSV)
        result = load_football_data_csv(csv_path)

        # First row: Arsenal vs Forest closing odds.
        assert result.iloc[0]["pinnacle_home"] == pytest.approx(1.28)
        assert result.iloc[0]["pinnacle_draw"] == pytest.approx(5.75)
        assert result.iloc[0]["pinnacle_away"] == pytest.approx(11.00)

    def test_max_closing_values_preferred_over_opening(
        self,
        tmp_path: Path,
    ) -> None:
        """MaxCH/MaxCD/MaxCA are used when both opening and closing exist."""
        csv_path = _write_csv(tmp_path, "season.csv", _FULL_CSV)
        result = load_football_data_csv(csv_path)

        # MaxCH for Arsenal row = 1.33.
        assert result.iloc[0]["max_home"] == pytest.approx(1.33)

    def test_date_parsed_correctly(self, tmp_path: Path) -> None:
        """Date column is parsed from DD/MM/YYYY to YYYY-MM-DD."""
        csv_path = _write_csv(tmp_path, "season.csv", _FULL_CSV)
        result = load_football_data_csv(csv_path)

        assert result.iloc[0]["date"] == "2023-08-15"

    def test_team_names_preserved(self, tmp_path: Path) -> None:
        """Team names are passed through without normalization."""
        csv_path = _write_csv(tmp_path, "season.csv", _FULL_CSV)
        result = load_football_data_csv(csv_path)

        assert result.iloc[0]["home_team"] == "Arsenal"
        assert result.iloc[0]["away_team"] == "Nott'm Forest"

    def test_missing_pinnacle_falls_back_to_betbrain_max(
        self,
        tmp_path: Path,
    ) -> None:
        """When Pinnacle columns are absent, BbMx* fills max_* columns."""
        csv_path = _write_csv(tmp_path, "no_pin.csv", _NO_PINNACLE_CSV)
        result = load_football_data_csv(csv_path)

        assert len(result) == 1
        # Pinnacle columns should be NaN.
        assert pd.isna(result.iloc[0]["pinnacle_home"])
        assert pd.isna(result.iloc[0]["pinnacle_draw"])
        assert pd.isna(result.iloc[0]["pinnacle_away"])
        # Max columns from BbMx*.
        assert result.iloc[0]["max_home"] == pytest.approx(1.90)
        assert result.iloc[0]["max_draw"] == pytest.approx(3.60)
        # O/U from BbMx.
        assert result.iloc[0]["max_over_25"] == pytest.approx(1.75)

    def test_opening_pinnacle_fallback_when_no_closing(
        self,
        tmp_path: Path,
    ) -> None:
        """When PSCH is missing but PSH exists, PSH fills pinnacle_home."""
        csv_path = _write_csv(tmp_path, "opening.csv", _OPENING_ONLY_CSV)
        result = load_football_data_csv(csv_path)

        assert result.iloc[0]["pinnacle_home"] == pytest.approx(1.25)
        assert result.iloc[0]["pinnacle_draw"] == pytest.approx(6.00)

    def test_raises_on_missing_required_columns(
        self,
        tmp_path: Path,
    ) -> None:
        """ValueError if HomeTeam/AwayTeam columns are missing."""
        bad_csv = "Col1,Col2\n1,2\n"
        csv_path = _write_csv(tmp_path, "bad.csv", bad_csv)

        with pytest.raises(ValueError, match="missing required columns"):
            load_football_data_csv(csv_path)

    def test_drops_trailing_garbage_rows(self, tmp_path: Path) -> None:
        """Rows with NaN teams (common trailing rows) are dropped."""
        content = (
            "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR,PSH,PSD,PSA\n"
            "E0,01/01/2024,TeamA,TeamB,1,0,H,1.50,4.00,6.00\n"
            ",,,,,,,,\n"
            ",,,,,,,,\n"
        )
        csv_path = _write_csv(tmp_path, "garbage.csv", content)
        result = load_football_data_csv(csv_path)

        assert len(result) == 1
        assert result.iloc[0]["home_team"] == "TeamA"

    def test_odds_coerced_to_float(self, tmp_path: Path) -> None:
        """Odds columns are numeric even if CSV has mixed types."""
        csv_path = _write_csv(tmp_path, "season.csv", _FULL_CSV)
        result = load_football_data_csv(csv_path)

        assert result["pinnacle_home"].dtype == float


# ---------------------------------------------------------------------------
# Tests: league code mapping
# ---------------------------------------------------------------------------


class TestLeagueMapping:
    """Tests for FOOTBALL_DATA_LEAGUE_MAP."""

    def test_all_top_five_leagues_present(self) -> None:
        """Top 5 European leagues are mapped."""
        top_five = {
            "ENG-Premier League",
            "ESP-La Liga",
            "GER-Bundesliga",
            "ITA-Serie A",
            "FRA-Ligue 1",
        }
        mapped_leagues = set(FOOTBALL_DATA_LEAGUE_MAP.values())
        assert top_five.issubset(mapped_leagues)

    def test_codes_are_strings(self) -> None:
        """All keys are non-empty strings."""
        for code in FOOTBALL_DATA_LEAGUE_MAP:
            assert isinstance(code, str)
            assert len(code) >= 2

    def test_reverse_lookup_works(self) -> None:
        """Every mapped league can be found by name."""
        from ml_in_sports.processing.odds.pinnacle import _LEAGUE_TO_CODE

        for code, name in FOOTBALL_DATA_LEAGUE_MAP.items():
            assert _LEAGUE_TO_CODE[name] == code


# ---------------------------------------------------------------------------
# Tests: _parse_csv_location
# ---------------------------------------------------------------------------


class TestParseCsvLocation:
    """Tests for file path -> (league_code, season) extraction."""

    def test_nested_layout(self, tmp_path: Path) -> None:
        """data_dir/E0/2324.csv -> ('E0', '2324')."""
        csv_path = tmp_path / "E0" / "2324.csv"
        league, season = _parse_csv_location(csv_path, tmp_path)

        assert league == "E0"
        assert season == "2324"

    def test_flat_layout(self, tmp_path: Path) -> None:
        """data_dir/E0_2324.csv -> ('E0', '2324')."""
        csv_path = tmp_path / "E0_2324.csv"
        league, season = _parse_csv_location(csv_path, tmp_path)

        assert league == "E0"
        assert season == "2324"

    def test_unknown_league_code_nested_returns_none(
        self,
        tmp_path: Path,
    ) -> None:
        """Unrecognized league code in nested layout returns (None, None)."""
        csv_path = tmp_path / "ZZ" / "2324.csv"
        league, season = _parse_csv_location(csv_path, tmp_path)

        assert league is None
        assert season is None

    def test_unrelated_file_returns_none(self, tmp_path: Path) -> None:
        """A random file name returns (None, None)."""
        csv_path = tmp_path / "notes.csv"
        league, season = _parse_csv_location(csv_path, tmp_path)

        assert league is None
        assert season is None


# ---------------------------------------------------------------------------
# Tests: load_pinnacle_odds (multi-file)
# ---------------------------------------------------------------------------


class TestLoadPinnacleOdds:
    """Tests for multi-file odds loading."""

    def _setup_data_dir(self, tmp_path: Path) -> Path:
        """Create a minimal data directory with two leagues/seasons."""
        data_dir = tmp_path / "odds_data"

        # E0/2324.csv
        e0_dir = data_dir / "E0"
        e0_dir.mkdir(parents=True)
        (e0_dir / "2324.csv").write_text(_FULL_CSV, encoding="utf-8")

        # SP1/2324.csv
        sp1_dir = data_dir / "SP1"
        sp1_dir.mkdir(parents=True)
        sp1_csv = (
            "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR,"
            "PSCH,PSCD,PSCA,MaxCH,MaxCD,MaxCA,"
            "MaxC>2.5,MaxC<2.5\n"
            "SP1,12/08/2023,Barcelona,Getafe,4,0,H,"
            "1.20,7.00,15.00,1.25,7.50,16.00,"
            "1.70,2.20\n"
        )
        (sp1_dir / "2324.csv").write_text(sp1_csv, encoding="utf-8")

        return data_dir

    def test_loads_all_leagues_and_seasons(
        self,
        tmp_path: Path,
    ) -> None:
        """Without filters, loads all discovered CSVs."""
        data_dir = self._setup_data_dir(tmp_path)
        result = load_pinnacle_odds(data_dir)

        assert len(result) == 3  # 2 from E0 + 1 from SP1
        assert set(result["league"]) == {
            "ENG-Premier League",
            "ESP-La Liga",
        }

    def test_filters_by_league(self, tmp_path: Path) -> None:
        """Filtering by league returns only matching data."""
        data_dir = self._setup_data_dir(tmp_path)
        result = load_pinnacle_odds(
            data_dir,
            leagues=["ESP-La Liga"],
        )

        assert len(result) == 1
        assert result.iloc[0]["league"] == "ESP-La Liga"

    def test_filters_by_season(self, tmp_path: Path) -> None:
        """Filtering by season returns only matching data."""
        data_dir = self._setup_data_dir(tmp_path)

        # Add a second season.
        e0_dir = data_dir / "E0"
        (e0_dir / "2223.csv").write_text(_FULL_CSV, encoding="utf-8")

        result = load_pinnacle_odds(data_dir, seasons=["2223"])

        assert len(result) == 2  # Both rows from E0/2223.csv
        assert set(result["season"]) == {"2223"}

    def test_empty_directory_returns_empty_dataframe(
        self,
        tmp_path: Path,
    ) -> None:
        """Empty data directory returns a DataFrame with correct columns."""
        data_dir = tmp_path / "empty"
        data_dir.mkdir()
        result = load_pinnacle_odds(data_dir)

        assert len(result) == 0
        assert "pinnacle_home" in result.columns
        assert "league" in result.columns
        assert "season" in result.columns

    def test_league_and_season_columns_added(
        self,
        tmp_path: Path,
    ) -> None:
        """Each row has league and season metadata."""
        data_dir = self._setup_data_dir(tmp_path)
        result = load_pinnacle_odds(data_dir)

        assert "league" in result.columns
        assert "season" in result.columns
        assert result["season"].iloc[0] == "2324"

    def test_unknown_league_filter_logs_warning(
        self,
        tmp_path: Path,
    ) -> None:
        """Filtering by unknown league name returns empty (no crash)."""
        data_dir = self._setup_data_dir(tmp_path)
        result = load_pinnacle_odds(
            data_dir,
            leagues=["UNKNOWN-League"],
        )

        assert len(result) == 0

    def test_flat_layout_files(self, tmp_path: Path) -> None:
        """Flat CSV names like E0_2324.csv are discovered."""
        data_dir = tmp_path / "flat"
        data_dir.mkdir()
        (data_dir / "E0_2324.csv").write_text(_FULL_CSV, encoding="utf-8")

        result = load_pinnacle_odds(data_dir)

        assert len(result) == 2
        assert result.iloc[0]["league"] == "ENG-Premier League"
        assert result.iloc[0]["season"] == "2324"


# ---------------------------------------------------------------------------
# Tests: download_season_csv
# ---------------------------------------------------------------------------


class TestDownloadSeasonCsv:
    """Tests for download_season_csv (mocked network)."""

    def test_rejects_unknown_league_code(self, tmp_path: Path) -> None:
        """Unknown league code raises ValueError before any HTTP call."""
        with pytest.raises(ValueError, match="Unknown league code"):
            download_season_csv("ZZ", "2324", tmp_path)
