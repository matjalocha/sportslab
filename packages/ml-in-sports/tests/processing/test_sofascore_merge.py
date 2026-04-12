"""Tests for sofascore_merge.py — cache loading, matching, and merge pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from ml_in_sports.processing.sofascore_merge import (
    _parse_numeric,
    _parse_raw_format,
    load_sofascore_cache,
    match_sofascore_to_features,
    run_sofascore_merge,
)

# ---------------------------------------------------------------------------
# _parse_raw_format
# ---------------------------------------------------------------------------


class TestParseRawFormat:
    """Tests for parsing the raw scraper JSON format."""

    def test_valid_input(self) -> None:
        """Valid raw format produces expected flat dict with sofa_ prefix."""
        data: dict[str, Any] = {
            "game_id": 12345,
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "timestamp": 1705305600,  # 2024-01-15 12:00 UTC
            "stats": {
                "home_expectedGoals": "1.45",
                "away_expectedGoals": "0.89",
                "home_ballPossession": "62%",
                "away_ballPossession": "38%",
            },
        }

        result = _parse_raw_format(data)

        assert result["game_id"] == 12345
        assert result["home_team"] == "Arsenal"
        assert result["away_team"] == "Chelsea"
        assert result["date"] == "2024-01-15"
        assert result["sofa_home_expected_goals"] == pytest.approx(1.45)
        assert result["sofa_away_expected_goals"] == pytest.approx(0.89)
        assert result["sofa_home_possession"] == pytest.approx(62.0)
        assert result["sofa_away_possession"] == pytest.approx(38.0)

    def test_missing_keys_raises(self) -> None:
        """Missing required keys raise KeyError."""
        data: dict[str, Any] = {
            "game_id": 1,
            "home_team": "A",
            # Missing "timestamp" and "stats"
        }

        with pytest.raises(KeyError):
            _parse_raw_format(data)

    def test_empty_stats(self) -> None:
        """Empty stats dict produces record with only metadata, no sofa_ columns."""
        data: dict[str, Any] = {
            "game_id": 1,
            "home_team": "TeamA",
            "away_team": "TeamB",
            "timestamp": 1705305600,
            "stats": {},
        }

        result = _parse_raw_format(data)

        assert result["game_id"] == 1
        assert result["home_team"] == "TeamA"
        assert result["away_team"] == "TeamB"
        assert result["date"] == "2024-01-15"
        sofa_keys = [k for k in result if k.startswith("sofa_")]
        assert len(sofa_keys) == 0

    def test_ignores_malformed_stat_keys(self) -> None:
        """Stat keys without home_/away_ prefix are silently skipped."""
        data: dict[str, Any] = {
            "game_id": 1,
            "home_team": "A",
            "away_team": "B",
            "timestamp": 1705305600,
            "stats": {
                "weirdKey": "123",
                "home_expectedGoals": "1.0",
            },
        }

        result = _parse_raw_format(data)

        # "weirdKey" has no valid side prefix, so only home_expectedGoals should appear
        sofa_keys = [k for k in result if k.startswith("sofa_")]
        assert len(sofa_keys) == 1
        assert "sofa_home_expected_goals" in result


# ---------------------------------------------------------------------------
# _parse_numeric
# ---------------------------------------------------------------------------


class TestParseNumeric:
    """Tests for numeric parsing of Sofascore stat values."""

    def test_integer(self) -> None:
        assert _parse_numeric(15) == pytest.approx(15.0)

    def test_float(self) -> None:
        assert _parse_numeric(1.45) == pytest.approx(1.45)

    def test_string_with_percent(self) -> None:
        assert _parse_numeric("62%") == pytest.approx(62.0)

    def test_string_float(self) -> None:
        assert _parse_numeric("1.45") == pytest.approx(1.45)

    def test_string_int(self) -> None:
        assert _parse_numeric("15") == pytest.approx(15.0)

    def test_none_returns_none(self) -> None:
        assert _parse_numeric(None) is None

    def test_garbage_string_returns_none(self) -> None:
        assert _parse_numeric("not_a_number") is None

    def test_empty_string_returns_none(self) -> None:
        assert _parse_numeric("") is None

    def test_whitespace_string_returns_none(self) -> None:
        assert _parse_numeric("  ") is None

    def test_list_returns_none(self) -> None:
        assert _parse_numeric([1, 2, 3]) is None


# ---------------------------------------------------------------------------
# load_sofascore_cache
# ---------------------------------------------------------------------------


def _write_json(path: Path, data: dict[str, Any]) -> None:
    """Helper: write a JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


class TestLoadSofascoreCache:
    """Tests for loading and parsing Sofascore JSON cache files."""

    def test_raw_format(self, tmp_path: Path) -> None:
        """Loads raw scraper JSON format correctly."""
        cache_dir = tmp_path / "sofascore"
        match_path = cache_dir / "ENG-Championship" / "61234" / "99999.json"
        _write_json(match_path, {
            "game_id": 99999,
            "home_team": "Leeds United",
            "away_team": "Sheffield United",
            "timestamp": 1705305600,
            "stats": {
                "home_expectedGoals": "1.2",
                "away_expectedGoals": "0.7",
            },
        })

        result = load_sofascore_cache(cache_dir)

        assert len(result) == 1
        assert result["game_id"].iloc[0] == 99999
        assert result["sofa_home_expected_goals"].iloc[0] == pytest.approx(1.2)

    def test_matchstats_format(self, tmp_path: Path) -> None:
        """Loads MatchStats-serialized JSON format correctly."""
        cache_dir = tmp_path / "sofascore"
        match_path = cache_dir / "ENG-Premier_League" / "61627" / "88888.json"
        _write_json(match_path, {
            "match_id": 88888,
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "date": "2024-01-15",
            "home_possession": 62.0,
            "away_possession": 38.0,
            "home_expected_goals": 1.5,
            "away_expected_goals": 0.8,
        })

        result = load_sofascore_cache(cache_dir)

        assert len(result) == 1
        assert result["game_id"].iloc[0] == 88888
        assert result["sofa_home_possession"].iloc[0] == pytest.approx(62.0)

    def test_corrupt_file_skipped(self, tmp_path: Path) -> None:
        """Corrupt JSON files are skipped without crashing."""
        cache_dir = tmp_path / "sofascore"
        bad_path = cache_dir / "ENG-Championship" / "61234" / "bad.json"
        bad_path.parent.mkdir(parents=True, exist_ok=True)
        bad_path.write_text("{this is not valid json", encoding="utf-8")

        result = load_sofascore_cache(cache_dir)

        assert len(result) == 0

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Empty cache directory returns empty DataFrame."""
        cache_dir = tmp_path / "sofascore"
        cache_dir.mkdir(parents=True)

        result = load_sofascore_cache(cache_dir)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_mixed_formats(self, tmp_path: Path) -> None:
        """Both raw and MatchStats formats can coexist."""
        cache_dir = tmp_path / "sofascore"

        _write_json(cache_dir / "league1" / "s1" / "1.json", {
            "game_id": 1,
            "home_team": "A",
            "away_team": "B",
            "timestamp": 1705305600,
            "stats": {"home_expectedGoals": "1.0", "away_expectedGoals": "0.5"},
        })
        _write_json(cache_dir / "league2" / "s2" / "2.json", {
            "match_id": 2,
            "home_team": "C",
            "away_team": "D",
            "date": "2024-01-16",
            "home_possession": 55.0,
            "away_possession": 45.0,
        })

        result = load_sofascore_cache(cache_dir)

        assert len(result) == 2


# ---------------------------------------------------------------------------
# match_sofascore_to_features
# ---------------------------------------------------------------------------


class TestMatchSofascoreToFeatures:
    """Tests for matching Sofascore cache rows to features parquet rows."""

    def test_exact_date_match(self) -> None:
        """Exact date + team name match works."""
        features = pd.DataFrame({
            "date": ["2024-01-15"],
            "home_team": ["Arsenal"],
            "away_team": ["Chelsea"],
            "league": ["ENG-Premier League"],
        })
        sofa = pd.DataFrame({
            "game_id": [100],
            "home_team": ["Arsenal"],
            "away_team": ["Chelsea"],
            "date": ["2024-01-15"],
            "sofa_home_xg": [1.5],
            "sofa_away_xg": [0.8],
        })

        result = match_sofascore_to_features(features, sofa)

        assert result["sofa_home_xg"].iloc[0] == pytest.approx(1.5)

    def test_date_tolerance_one_day(self) -> None:
        """Matches within +/- 1 day tolerance."""
        features = pd.DataFrame({
            "date": ["2024-01-15"],
            "home_team": ["Arsenal"],
            "away_team": ["Chelsea"],
            "league": ["ENG-Premier League"],
        })
        sofa = pd.DataFrame({
            "game_id": [100],
            "home_team": ["Arsenal"],
            "away_team": ["Chelsea"],
            "date": ["2024-01-16"],
            "sofa_home_xg": [1.5],
        })

        result = match_sofascore_to_features(features, sofa, date_tolerance_days=1)

        assert result["sofa_home_xg"].iloc[0] == pytest.approx(1.5)

    def test_team_name_normalization(self) -> None:
        """normalize_team_name aligns different name variants."""
        features = pd.DataFrame({
            "date": ["2024-01-15"],
            "home_team": ["Man City"],
            "away_team": ["Wolves"],
            "league": ["ENG-Premier League"],
        })
        sofa = pd.DataFrame({
            "game_id": [200],
            "home_team": ["Manchester City"],
            "away_team": ["Wolverhampton Wanderers"],
            "date": ["2024-01-15"],
            "sofa_home_xg": [2.3],
        })

        result = match_sofascore_to_features(features, sofa)

        assert result["sofa_home_xg"].iloc[0] == pytest.approx(2.3)

    def test_no_match_returns_nan(self) -> None:
        """Unmatched rows get NaN for sofa_ columns."""
        features = pd.DataFrame({
            "date": ["2024-01-15"],
            "home_team": ["Unknown FC"],
            "away_team": ["Mystery United"],
            "league": ["ENG-Premier League"],
        })
        sofa = pd.DataFrame({
            "game_id": [100],
            "home_team": ["Arsenal"],
            "away_team": ["Chelsea"],
            "date": ["2024-01-15"],
            "sofa_home_xg": [1.5],
        })

        result = match_sofascore_to_features(features, sofa)

        assert pd.isna(result["sofa_home_xg"].iloc[0])

    def test_empty_sofascore_returns_original(self) -> None:
        """Empty Sofascore DataFrame returns features unchanged."""
        features = pd.DataFrame({
            "date": ["2024-01-15"],
            "home_team": ["Arsenal"],
            "away_team": ["Chelsea"],
            "league": ["ENG-Premier League"],
        })
        sofa = pd.DataFrame()

        result = match_sofascore_to_features(features, sofa)

        assert list(result.columns) == list(features.columns)


# ---------------------------------------------------------------------------
# run_sofascore_merge (smoke test with dry_run=True)
# ---------------------------------------------------------------------------


class TestRunSofascoreMerge:
    """Smoke test for the full merge pipeline with dry_run=True."""

    def test_dry_run_on_synthetic_data(self, tmp_path: Path) -> None:
        """Pipeline runs to completion on synthetic data without saving."""
        # Create a minimal parquet
        parquet_path = tmp_path / "features.parquet"
        features = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-15", "2024-01-16", "2024-01-17"]),
            "league": ["ENG-Premier League"] * 3,
            "home_team": ["Arsenal", "Liverpool", "Chelsea"],
            "away_team": ["Chelsea", "Everton", "Arsenal"],
            "home_goals": [2.0, 1.0, 0.0],
            "away_goals": [1.0, 1.0, 2.0],
        })
        features.to_parquet(parquet_path, index=False)

        # Create a Sofascore cache directory with one match
        sofa_dir = tmp_path / "sofascore"
        match_path = sofa_dir / "ENG-Premier_League" / "61627" / "100.json"
        _write_json(match_path, {
            "match_id": 100,
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "date": "2024-01-15",
            "home_possession": 62.0,
            "away_possession": 38.0,
            "home_expected_goals": 1.5,
            "away_expected_goals": 0.8,
            "home_total_shots": 10,
            "away_total_shots": 6,
            "home_shots_on_target": 4,
            "away_shots_on_target": 2,
            "home_tackles": 15,
            "away_tackles": 12,
            "home_accurate_passes": 400,
            "away_accurate_passes": 350,
            "home_accurate_passes_pct": 85.0,
            "away_accurate_passes_pct": 78.0,
            "home_accurate_crosses": 4,
            "away_accurate_crosses": 2,
            "home_interceptions": 10,
            "away_interceptions": 8,
            "home_clearances": 12,
            "away_clearances": 18,
            "home_accurate_long_balls": 6,
            "away_accurate_long_balls": 9,
            "home_ground_duels_won": 22,
            "away_ground_duels_won": 18,
            "home_aerial_duels_won": 8,
            "away_aerial_duels_won": 11,
            "home_successful_dribbles": 5,
            "away_successful_dribbles": 3,
            "home_saves": 3,
            "away_saves": 4,
        })

        result = run_sofascore_merge(
            parquet_path=parquet_path,
            sofascore_dir=sofa_dir,
            windows=[3],
            dry_run=True,
        )

        assert len(result) == 3
        # Should have sofa_ columns
        sofa_cols = [c for c in result.columns if c.startswith("sofa_")]
        assert len(sofa_cols) > 0
        # Parquet should NOT have been overwritten (dry_run)
        reloaded = pd.read_parquet(parquet_path)
        assert "sofa_home_possession" not in reloaded.columns
