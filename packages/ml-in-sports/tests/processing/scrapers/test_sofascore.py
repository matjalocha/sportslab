"""Tests for the Sofascore scraper.

All tests use mocks -- no real browser is launched, no network calls are made.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from ml_in_sports.processing.scrapers.sofascore import (
    MatchStats,
    SofascoreMatchEvent,
    SofascoreScraper,
    build_match_stats,
    load_cached_stats,
    match_stats_from_dict,
    match_stats_to_dict,
    parse_stat_value,
)

# ---------------------------------------------------------------------------
# MatchStats dataclass
# ---------------------------------------------------------------------------


class TestMatchStats:
    """Tests for the MatchStats frozen dataclass."""

    def test_create_with_all_fields(self) -> None:
        stats = MatchStats(
            match_id=12345,
            home_team="Arsenal",
            away_team="Chelsea",
            date="2024-01-15",
            home_possession=62.0,
            away_possession=38.0,
            home_total_shots=15,
            away_total_shots=8,
            home_shots_on_target=6,
            away_shots_on_target=3,
            home_tackles=18,
            away_tackles=22,
            home_accurate_passes=450,
            away_accurate_passes=320,
            home_accurate_passes_pct=87.0,
            away_accurate_passes_pct=79.0,
            home_accurate_crosses=5,
            away_accurate_crosses=3,
            home_interceptions=12,
            away_interceptions=8,
            home_clearances=15,
            away_clearances=25,
            home_accurate_long_balls=8,
            away_accurate_long_balls=12,
            home_ground_duels_won=25,
            away_ground_duels_won=20,
            home_aerial_duels_won=10,
            away_aerial_duels_won=14,
            home_successful_dribbles=7,
            away_successful_dribbles=4,
            home_saves=3,
            away_saves=5,
            home_expected_goals=1.85,
            away_expected_goals=0.72,
        )
        assert stats.match_id == 12345
        assert stats.home_team == "Arsenal"
        assert stats.home_possession == 62.0
        assert stats.home_expected_goals == 1.85

    def test_create_with_none_stats(self) -> None:
        stats = MatchStats(
            match_id=99999,
            home_team="TeamA",
            away_team="TeamB",
            date="2024-06-01",
            home_possession=None,
            away_possession=None,
            home_total_shots=None,
            away_total_shots=None,
            home_shots_on_target=None,
            away_shots_on_target=None,
            home_tackles=None,
            away_tackles=None,
            home_accurate_passes=None,
            away_accurate_passes=None,
            home_accurate_passes_pct=None,
            away_accurate_passes_pct=None,
            home_accurate_crosses=None,
            away_accurate_crosses=None,
            home_interceptions=None,
            away_interceptions=None,
            home_clearances=None,
            away_clearances=None,
            home_accurate_long_balls=None,
            away_accurate_long_balls=None,
            home_ground_duels_won=None,
            away_ground_duels_won=None,
            home_aerial_duels_won=None,
            away_aerial_duels_won=None,
            home_successful_dribbles=None,
            away_successful_dribbles=None,
            home_saves=None,
            away_saves=None,
            home_expected_goals=None,
            away_expected_goals=None,
        )
        assert stats.home_possession is None
        assert stats.home_expected_goals is None

    def test_frozen_prevents_mutation(self) -> None:
        stats = MatchStats(
            match_id=1,
            home_team="A",
            away_team="B",
            date="2024-01-01",
            home_possession=50.0,
            away_possession=50.0,
            home_total_shots=None,
            away_total_shots=None,
            home_shots_on_target=None,
            away_shots_on_target=None,
            home_tackles=None,
            away_tackles=None,
            home_accurate_passes=None,
            away_accurate_passes=None,
            home_accurate_passes_pct=None,
            away_accurate_passes_pct=None,
            home_accurate_crosses=None,
            away_accurate_crosses=None,
            home_interceptions=None,
            away_interceptions=None,
            home_clearances=None,
            away_clearances=None,
            home_accurate_long_balls=None,
            away_accurate_long_balls=None,
            home_ground_duels_won=None,
            away_ground_duels_won=None,
            home_aerial_duels_won=None,
            away_aerial_duels_won=None,
            home_successful_dribbles=None,
            away_successful_dribbles=None,
            home_saves=None,
            away_saves=None,
            home_expected_goals=None,
            away_expected_goals=None,
        )
        with pytest.raises(AttributeError):
            stats.home_possession = 99.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# parse_stat_value
# ---------------------------------------------------------------------------


class TestParseStatValue:
    """Tests for the stat value parser."""

    def test_none_returns_none(self) -> None:
        assert parse_stat_value(None) is None

    def test_int_passthrough(self) -> None:
        assert parse_stat_value(15) == 15

    def test_float_passthrough(self) -> None:
        assert parse_stat_value(1.85) == 1.85

    def test_string_integer(self) -> None:
        assert parse_stat_value("15") == 15

    def test_string_float(self) -> None:
        assert parse_stat_value("1.85") == 1.85

    def test_string_percentage(self) -> None:
        assert parse_stat_value("62%") == 62

    def test_string_float_percentage(self) -> None:
        assert parse_stat_value("87.5%") == 87.5

    def test_empty_string_returns_none(self) -> None:
        assert parse_stat_value("") is None

    def test_whitespace_string_returns_none(self) -> None:
        assert parse_stat_value("  ") is None

    def test_unparseable_returns_none(self) -> None:
        assert parse_stat_value("N/A") is None

    def test_list_returns_none(self) -> None:
        assert parse_stat_value([1, 2]) is None


# ---------------------------------------------------------------------------
# build_match_stats / JSON round-trip
# ---------------------------------------------------------------------------


def _sample_raw_stats() -> dict[str, Any]:
    """Return a sample flattened Sofascore stats dict."""
    return {
        "ballPossession_home": "62%",
        "ballPossession_away": "38%",
        "totalShotsOnGoal_home": 15,
        "totalShotsOnGoal_away": 8,
        "shotsOnTarget_home": "6",
        "shotsOnTarget_away": "3",
        "tackles_home": 18,
        "tackles_away": 22,
        "accuratePasses_home": 450,
        "accuratePasses_away": 320,
        "accuratePassesPercentage_home": "87%",
        "accuratePassesPercentage_away": "79%",
        "accurateCrosses_home": 5,
        "accurateCrosses_away": 3,
        "interceptions_home": 12,
        "interceptions_away": 8,
        "clearances_home": 15,
        "clearances_away": 25,
        "accurateLongBalls_home": 8,
        "accurateLongBalls_away": 12,
        "groundDuelsWon_home": 25,
        "groundDuelsWon_away": 20,
        "aerialDuelsWon_home": 10,
        "aerialDuelsWon_away": 14,
        "successfulDribbles_home": 7,
        "successfulDribbles_away": 4,
        "saves_home": 3,
        "saves_away": 5,
        "expectedGoals_home": "1.85",
        "expectedGoals_away": "0.72",
    }


class TestBuildMatchStats:
    """Tests for building MatchStats from raw Sofascore JSON."""

    def test_build_from_raw_stats(self) -> None:
        stats = build_match_stats(
            match_id=12345,
            home_team="Arsenal",
            away_team="Chelsea",
            date="2024-01-15",
            raw_stats=_sample_raw_stats(),
        )
        assert stats.match_id == 12345
        assert stats.home_possession == 62
        assert stats.away_possession == 38
        assert stats.home_total_shots == 15
        assert stats.home_tackles == 18
        assert stats.home_expected_goals == 1.85
        assert stats.away_expected_goals == 0.72

    def test_build_with_missing_keys(self) -> None:
        stats = build_match_stats(
            match_id=1,
            home_team="A",
            away_team="B",
            date="2024-01-01",
            raw_stats={},
        )
        assert stats.home_possession is None
        assert stats.home_expected_goals is None
        assert stats.home_tackles is None

    def test_build_ignores_unknown_keys(self) -> None:
        raw = {"unknownStat_home": 99, "unknownStat_away": 88}
        stats = build_match_stats(
            match_id=1,
            home_team="A",
            away_team="B",
            date="2024-01-01",
            raw_stats=raw,
        )
        assert stats.match_id == 1


# ---------------------------------------------------------------------------
# JSON cache round-trip
# ---------------------------------------------------------------------------


class TestJsonCacheRoundTrip:
    """Tests for MatchStats serialisation/deserialisation."""

    def test_to_dict_and_back(self) -> None:
        original = build_match_stats(
            match_id=12345,
            home_team="Arsenal",
            away_team="Chelsea",
            date="2024-01-15",
            raw_stats=_sample_raw_stats(),
        )
        as_dict = match_stats_to_dict(original)
        restored = match_stats_from_dict(as_dict)
        assert restored == original

    def test_json_serialise_deserialise(self) -> None:
        original = build_match_stats(
            match_id=777,
            home_team="Liverpool",
            away_team="Everton",
            date="2024-02-20",
            raw_stats=_sample_raw_stats(),
        )
        json_str = json.dumps(match_stats_to_dict(original))
        restored = match_stats_from_dict(json.loads(json_str))
        assert restored == original

    def test_from_dict_ignores_extra_keys(self) -> None:
        data = match_stats_to_dict(
            build_match_stats(1, "A", "B", "2024-01-01", {})
        )
        data["extra_field"] = "should be ignored"
        stats = match_stats_from_dict(data)
        assert stats.match_id == 1


# ---------------------------------------------------------------------------
# JSON file cache on disk
# ---------------------------------------------------------------------------


class TestLoadCachedStats:
    """Tests for loading cached stats from disk."""

    def test_load_from_cache_dir(self, tmp_path: Path) -> None:
        season_dir = tmp_path / "ENG-Championship" / "24_25"
        season_dir.mkdir(parents=True)

        stats = build_match_stats(100, "Leeds", "Norwich", "2024-09-01", _sample_raw_stats())
        (season_dir / "100.json").write_text(
            json.dumps(match_stats_to_dict(stats)),
            encoding="utf-8",
        )

        loaded = load_cached_stats(tmp_path, "ENG-Championship", "24/25")
        assert len(loaded) == 1
        assert loaded[0].match_id == 100
        assert loaded[0].home_team == "Leeds"

    def test_load_empty_dir_returns_empty(self, tmp_path: Path) -> None:
        loaded = load_cached_stats(tmp_path, "ENG-Championship", "24/25")
        assert loaded == []

    def test_load_skips_corrupt_files(self, tmp_path: Path) -> None:
        season_dir = tmp_path / "ENG-Championship" / "24_25"
        season_dir.mkdir(parents=True)

        # Valid file
        stats = build_match_stats(100, "Leeds", "Norwich", "2024-09-01", {})
        (season_dir / "100.json").write_text(
            json.dumps(match_stats_to_dict(stats)),
            encoding="utf-8",
        )
        # Corrupt file
        (season_dir / "200.json").write_text("not valid json", encoding="utf-8")

        loaded = load_cached_stats(tmp_path, "ENG-Championship", "24/25")
        assert len(loaded) == 1
        assert loaded[0].match_id == 100


# ---------------------------------------------------------------------------
# SofascoreScraper with mocked browser
# ---------------------------------------------------------------------------


def _make_mock_sb() -> tuple[MagicMock, MagicMock]:
    """Create a mock SeleniumBase SB context manager."""
    mock_sb_instance = MagicMock()
    mock_sb_instance.open = MagicMock()
    mock_sb_instance.sleep = MagicMock()
    mock_sb_instance.execute_script = MagicMock()

    mock_sb_ctx = MagicMock()
    mock_sb_ctx.__enter__ = MagicMock(return_value=mock_sb_instance)
    mock_sb_ctx.__exit__ = MagicMock(return_value=False)

    return mock_sb_ctx, mock_sb_instance


class TestSofascoreScraperGetSeasonMatchIds:
    """Tests for match list fetching with mocked browser."""

    def test_unknown_league_raises(self) -> None:
        scraper = SofascoreScraper()
        with pytest.raises(ValueError, match="Unknown league"):
            scraper.get_season_match_ids("FAKE-League", "24/25")
        scraper.close()

    def test_unknown_season_raises(self) -> None:
        scraper = SofascoreScraper()
        with pytest.raises(ValueError, match="Unknown season"):
            scraper.get_season_match_ids("ENG-Premier League", "99/00")
        scraper.close()

    @patch("seleniumbase.SB")
    def test_fetches_paginated_match_list(self, mock_sb_cls: MagicMock) -> None:
        mock_ctx, mock_sb = _make_mock_sb()
        mock_sb_cls.return_value = mock_ctx

        page_0 = json.dumps([
            {"id": 100, "home": "Leeds", "away": "Norwich", "date": 1700000000},
            {"id": 101, "home": "Burnley", "away": "QPR", "date": 1700100000},
        ])
        page_1 = json.dumps([
            {"id": 102, "home": "Stoke", "away": "Hull", "date": 1700200000},
        ])
        page_2 = json.dumps([])

        mock_sb.execute_script.side_effect = [page_0, page_1, page_2]

        scraper = SofascoreScraper(rate_limit=0.0)
        events = scraper.get_season_match_ids("ENG-Championship", "24/25")
        scraper.close()

        assert len(events) == 3
        assert events[0] == SofascoreMatchEvent(100, "Leeds", "Norwich", 1700000000)
        assert events[2].match_id == 102


class TestSofascoreScraperGetMatchStats:
    """Tests for single match stats fetching with mocked browser."""

    @patch("seleniumbase.SB")
    def test_fetches_and_parses_stats(self, mock_sb_cls: MagicMock) -> None:
        mock_ctx, mock_sb = _make_mock_sb()
        mock_sb_cls.return_value = mock_ctx

        mock_sb.execute_script.return_value = json.dumps(_sample_raw_stats())

        scraper = SofascoreScraper(rate_limit=0.0)
        stats = scraper.get_match_stats(12345, "Arsenal", "Chelsea", 1705276800)
        scraper.close()

        assert stats is not None
        assert stats.match_id == 12345
        assert stats.home_team == "Arsenal"
        assert stats.home_possession == 62

    @patch("seleniumbase.SB")
    def test_returns_none_on_404(self, mock_sb_cls: MagicMock) -> None:
        mock_ctx, mock_sb = _make_mock_sb()
        mock_sb_cls.return_value = mock_ctx

        mock_sb.execute_script.return_value = json.dumps({"error": 404})

        scraper = SofascoreScraper(rate_limit=0.0)
        stats = scraper.get_match_stats(99999, "A", "B", 1705276800)
        scraper.close()

        assert stats is None

    @patch("seleniumbase.SB")
    def test_returns_none_on_null_response(self, mock_sb_cls: MagicMock) -> None:
        mock_ctx, mock_sb = _make_mock_sb()
        mock_sb_cls.return_value = mock_ctx

        mock_sb.execute_script.return_value = None

        scraper = SofascoreScraper(rate_limit=0.0)
        stats = scraper.get_match_stats(99999, "A", "B", 1705276800)
        scraper.close()

        assert stats is None


class TestSofascoreScraperScrapeLeagueSeason:
    """Tests for full league/season scraping with caching."""

    @patch("seleniumbase.SB")
    def test_scrape_caches_results(self, mock_sb_cls: MagicMock, tmp_path: Path) -> None:
        mock_ctx, mock_sb = _make_mock_sb()
        mock_sb_cls.return_value = mock_ctx

        # Page 0: one match. Page 1: empty (stops pagination).
        match_list_page = json.dumps([
            {"id": 500, "home": "Leeds", "away": "Norwich", "date": 1700000000},
        ])
        stats_json = json.dumps(_sample_raw_stats())
        empty_page = json.dumps([])

        mock_sb.execute_script.side_effect = [
            match_list_page,  # page 0
            empty_page,       # page 1 (empty, stops)
            stats_json,       # match 500 stats
        ]

        scraper = SofascoreScraper(rate_limit=0.0)
        results = scraper.scrape_league_season(
            "ENG-Championship", "24/25", cache_dir=tmp_path,
        )
        scraper.close()

        assert len(results) == 1
        assert results[0].match_id == 500

        # Verify cache file was written
        cache_file = tmp_path / "ENG-Championship" / "24_25" / "500.json"
        assert cache_file.exists()
        cached_data = json.loads(cache_file.read_text(encoding="utf-8"))
        assert cached_data["match_id"] == 500

    @patch("seleniumbase.SB")
    def test_scrape_uses_cache_on_rerun(
        self, mock_sb_cls: MagicMock, tmp_path: Path,
    ) -> None:
        mock_ctx, mock_sb = _make_mock_sb()
        mock_sb_cls.return_value = mock_ctx

        # Pre-populate cache
        season_dir = tmp_path / "ENG-Championship" / "24_25"
        season_dir.mkdir(parents=True)
        cached_stats = build_match_stats(500, "Leeds", "Norwich", "2023-11-14", _sample_raw_stats())
        (season_dir / "500.json").write_text(
            json.dumps(match_stats_to_dict(cached_stats)),
            encoding="utf-8",
        )

        # Match list returns the same match
        match_list_page = json.dumps([
            {"id": 500, "home": "Leeds", "away": "Norwich", "date": 1700000000},
        ])
        empty_page = json.dumps([])

        mock_sb.execute_script.side_effect = [
            match_list_page,
            empty_page,
            # No stats fetch call -- should use cache
        ]

        scraper = SofascoreScraper(rate_limit=0.0)
        results = scraper.scrape_league_season(
            "ENG-Championship", "24/25", cache_dir=tmp_path,
        )
        scraper.close()

        assert len(results) == 1
        assert results[0].match_id == 500
        # The execute_script should only be called twice (for match list pages),
        # not a third time for stats (since cache was used).
        assert mock_sb.execute_script.call_count == 2
