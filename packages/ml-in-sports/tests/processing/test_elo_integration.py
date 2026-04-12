"""Tests for ClubElo integration into features parquet."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from ml_in_sports.processing.elo_integration import (
    LEAGUE_TO_COUNTRY,
    LEAGUE_TO_LEVEL,
    _add_elo_form,
    _normalize_elo_snapshot,
    compute_elo_features,
    match_elo_to_features,
)


@pytest.fixture
def sample_elo_raw() -> pd.DataFrame:
    """ClubElo-style raw snapshot (indexed by team name)."""
    data = {
        "rank": [1.0, 2.0, 3.0, 4.0, 5.0],
        "country": ["ENG", "ENG", "ESP", "NED", "NED"],
        "level": [1, 1, 1, 1, 1],
        "elo": [2000.0, 1900.0, 1950.0, 1800.0, 1750.0],
        "from": ["2025-03-01"] * 5,
        "to": ["2025-03-08"] * 5,
        "league": [
            "ENG-Premier League",
            "ENG-Premier League",
            "ESP-La Liga",
            np.nan,
            np.nan,
        ],
    }
    return pd.DataFrame(
        data,
        index=pd.Index(
            ["Liverpool", "Man City", "Real Madrid", "Ajax", "PSV"],
            name="team",
        ),
    )


@pytest.fixture
def sample_elo_df() -> pd.DataFrame:
    """Normalized ELO snapshots across two dates."""
    rows = [
        ("Liverpool", "2025-03-01", 2000.0, "ENG", 1),
        ("Manchester City", "2025-03-01", 1900.0, "ENG", 1),
        ("Real Madrid", "2025-03-01", 1950.0, "ESP", 1),
        ("Ajax Amsterdam", "2025-03-01", 1800.0, "NED", 1),
        ("PSV Eindhoven", "2025-03-01", 1750.0, "NED", 1),
        ("Liverpool", "2025-03-08", 2010.0, "ENG", 1),
        ("Manchester City", "2025-03-08", 1895.0, "ENG", 1),
        ("Real Madrid", "2025-03-08", 1960.0, "ESP", 1),
        ("Ajax Amsterdam", "2025-03-08", 1810.0, "NED", 1),
        ("PSV Eindhoven", "2025-03-08", 1740.0, "NED", 1),
    ]
    return pd.DataFrame(
        rows,
        columns=["team", "date", "elo", "country", "level"],
    )


@pytest.fixture
def sample_features() -> pd.DataFrame:
    """Minimal features DataFrame for testing ELO matching."""
    return pd.DataFrame({
        "date": pd.to_datetime([
            "2025-03-05",
            "2025-03-05",
            "2025-03-10",
        ]),
        "league": [
            "ENG-Premier League",
            "NED-Eredivisie",
            "ESP-La Liga",
        ],
        "home_team": ["Liverpool", "Ajax Amsterdam", "Real Madrid"],
        "away_team": ["Manchester City", "PSV Eindhoven", "Real Madrid"],
        "home_goals": [2.0, 1.0, 3.0],
        "away_goals": [1.0, 1.0, 0.0],
    })


class TestNormalizeEloSnapshot:
    """Tests for _normalize_elo_snapshot."""

    def test_applies_team_name_normalization(
        self, sample_elo_raw: pd.DataFrame,
    ) -> None:
        """ClubElo short names like 'Man City' become canonical forms."""
        result = _normalize_elo_snapshot(sample_elo_raw, "2025-03-01")
        assert "Manchester City" in result["team"].values
        assert "Man City" not in result["team"].values

    def test_produces_correct_columns(
        self, sample_elo_raw: pd.DataFrame,
    ) -> None:
        """Output has exactly team, date, elo, country, level."""
        result = _normalize_elo_snapshot(sample_elo_raw, "2025-03-01")
        assert set(result.columns) == {"team", "date", "elo", "country", "level"}

    def test_preserves_elo_values(
        self, sample_elo_raw: pd.DataFrame,
    ) -> None:
        """ELO ratings pass through without modification."""
        result = _normalize_elo_snapshot(sample_elo_raw, "2025-03-01")
        liverpool = result[result["team"] == "Liverpool"]
        assert liverpool["elo"].iloc[0] == pytest.approx(2000.0)

    def test_sets_date_from_argument(
        self, sample_elo_raw: pd.DataFrame,
    ) -> None:
        """All rows get the passed date string."""
        result = _normalize_elo_snapshot(sample_elo_raw, "2025-03-15")
        assert (result["date"] == "2025-03-15").all()


class TestMatchEloToFeatures:
    """Tests for match_elo_to_features."""

    def test_matches_by_team_and_date(
        self,
        sample_features: pd.DataFrame,
        sample_elo_df: pd.DataFrame,
    ) -> None:
        """ELO is matched from the snapshot BEFORE the match date."""
        result = match_elo_to_features(sample_features, sample_elo_df)

        # Match on 2025-03-05: should use 2025-03-01 snapshot
        liverpool_elo = result.loc[0, "home_elo"]
        assert liverpool_elo == pytest.approx(2000.0)

    def test_no_lookahead(
        self,
        sample_features: pd.DataFrame,
        sample_elo_df: pd.DataFrame,
    ) -> None:
        """Match on 2025-03-05 must NOT use 2025-03-08 snapshot."""
        result = match_elo_to_features(sample_features, sample_elo_df)

        # Liverpool's 03-08 ELO is 2010, but match is on 03-05
        assert result.loc[0, "home_elo"] == pytest.approx(2000.0)
        assert result.loc[0, "home_elo"] != pytest.approx(2010.0)

    def test_later_match_uses_later_snapshot(
        self,
        sample_features: pd.DataFrame,
        sample_elo_df: pd.DataFrame,
    ) -> None:
        """Match on 2025-03-10 should use 2025-03-08 snapshot."""
        result = match_elo_to_features(sample_features, sample_elo_df)

        # Real Madrid on 03-10: should use 03-08 snapshot (1960)
        assert result.loc[2, "home_elo"] == pytest.approx(1960.0)

    def test_expansion_league_matching(
        self,
        sample_features: pd.DataFrame,
        sample_elo_df: pd.DataFrame,
    ) -> None:
        """NED-Eredivisie teams match via country code, not league name."""
        result = match_elo_to_features(sample_features, sample_elo_df)

        # Ajax in NED-Eredivisie should match
        assert pd.notna(result.loc[1, "home_elo"])
        assert result.loc[1, "home_elo"] == pytest.approx(1800.0)

    def test_returns_nan_for_no_match(self) -> None:
        """Teams not in ELO data get NaN."""
        features = pd.DataFrame({
            "date": pd.to_datetime(["2025-03-05"]),
            "league": ["ENG-Premier League"],
            "home_team": ["Unknown FC"],
            "away_team": ["Mystery United"],
            "home_goals": [1.0],
            "away_goals": [0.0],
        })
        elo = pd.DataFrame({
            "team": ["Liverpool"],
            "date": pd.to_datetime(["2025-03-01"]),
            "elo": [2000.0],
            "country": ["ENG"],
            "level": [1],
        })

        result = match_elo_to_features(features, elo)
        assert pd.isna(result.loc[0, "home_elo"])
        assert pd.isna(result.loc[0, "away_elo"])


class TestComputeEloFeatures:
    """Tests for compute_elo_features."""

    def test_diff_elo_computed(self) -> None:
        """diff_elo = home_elo - away_elo."""
        df = pd.DataFrame({
            "date": pd.to_datetime(["2025-03-05"]),
            "league": ["ENG-Premier League"],
            "home_team": ["Liverpool"],
            "away_team": ["Manchester City"],
            "home_elo": [2000.0],
            "away_elo": [1900.0],
            "home_goals": [2.0],
            "away_goals": [1.0],
        })

        result = compute_elo_features(df)
        assert result.loc[0, "diff_elo"] == pytest.approx(100.0)

    def test_elo_form_columns_created(self) -> None:
        """Rolling ELO form columns are created for windows 3, 5, 10."""
        # Need enough rows for rolling windows
        dates = pd.date_range("2025-01-01", periods=15, freq="7D")
        df = pd.DataFrame({
            "date": dates,
            "league": ["ENG-Premier League"] * 15,
            "home_team": ["Liverpool"] * 15,
            "away_team": ["Manchester City"] * 15,
            "home_elo": np.linspace(1900, 2000, 15),
            "away_elo": np.linspace(1850, 1900, 15),
            "home_goals": [2.0] * 15,
            "away_goals": [1.0] * 15,
        })

        result = compute_elo_features(df)

        for window in (3, 5, 10):
            assert f"home_elo_form_{window}" in result.columns
            assert f"away_elo_form_{window}" in result.columns
            assert f"diff_elo_form_{window}" in result.columns

    def test_elo_form_no_lookahead(self) -> None:
        """ELO form uses shift(1) so current match ELO is excluded."""
        dates = pd.date_range("2025-01-01", periods=5, freq="7D")
        df = pd.DataFrame({
            "date": dates,
            "league": ["ENG-Premier League"] * 5,
            "home_team": ["Liverpool"] * 5,
            "away_team": ["Manchester City"] * 5,
            "home_elo": [1900.0, 1910.0, 1920.0, 1930.0, 1940.0],
            "away_elo": [1800.0] * 5,
            "home_goals": [2.0] * 5,
            "away_goals": [1.0] * 5,
        })

        result = compute_elo_features(df)

        # For window=3, home_elo_form_3 at index 3:
        # shift(1) = 1920, shift(3) = 1900, form = 20
        form_3 = result["home_elo_form_3"]
        # First 3 rows should be NaN (not enough data)
        assert pd.isna(form_3.iloc[0])
        assert pd.isna(form_3.iloc[1])
        assert pd.isna(form_3.iloc[2])
        # Row 3: shift(1)=1920, shift(3)=1900, diff=20
        assert form_3.iloc[3] == pytest.approx(20.0)


class TestLeagueMappings:
    """Tests for league-to-country/level mapping completeness."""

    def test_all_leagues_have_country_mapping(self) -> None:
        """Every league in LEAGUE_TO_COUNTRY also has a level mapping."""
        for league in LEAGUE_TO_COUNTRY:
            assert league in LEAGUE_TO_LEVEL, (
                f"{league} in LEAGUE_TO_COUNTRY but not LEAGUE_TO_LEVEL"
            )

    def test_country_codes_are_three_letter(self) -> None:
        """All country codes are exactly 3 uppercase letters."""
        for league, country in LEAGUE_TO_COUNTRY.items():
            assert len(country) == 3, f"{league}: country code '{country}' is not 3 chars"
            assert country == country.upper(), f"{league}: country code '{country}' is not uppercase"

    def test_levels_are_one_or_two(self) -> None:
        """All league levels are 1 (top flight) or 2 (second tier)."""
        for league, level in LEAGUE_TO_LEVEL.items():
            assert level in (1, 2), f"{league}: level {level} not in (1, 2)"


class TestAddEloForm:
    """Tests for _add_elo_form helper."""

    def test_computes_elo_change_over_window(self) -> None:
        """ELO form captures the change from N matches ago."""
        df = pd.DataFrame({
            "date": pd.date_range("2025-01-01", periods=6, freq="7D"),
            "home_team": ["TeamA"] * 6,
            "home_elo": [1500.0, 1510.0, 1520.0, 1530.0, 1540.0, 1550.0],
        })

        result = _add_elo_form(df, "home", 3)

        # At index 3: shift(1)=1520, shift(3)=1500, diff=20
        assert result["home_elo_form_3"].iloc[3] == pytest.approx(20.0)

    def test_returns_nan_when_elo_missing(self) -> None:
        """If home_elo column does not exist, form is all NaN."""
        df = pd.DataFrame({
            "date": pd.date_range("2025-01-01", periods=3, freq="7D"),
            "home_team": ["TeamA"] * 3,
        })

        result = _add_elo_form(df, "home", 3)
        assert result["home_elo_form_3"].isna().all()


class TestMatchEloToFeaturesEmpty:
    """Tests for match_elo_to_features with edge-case inputs."""

    def test_empty_features_dataframe(self) -> None:
        """Empty features DataFrame does not crash (no ZeroDivisionError)."""
        features = pd.DataFrame({
            "date": pd.to_datetime([]),
            "league": pd.Series([], dtype=str),
            "home_team": pd.Series([], dtype=str),
            "away_team": pd.Series([], dtype=str),
            "home_goals": pd.Series([], dtype=float),
            "away_goals": pd.Series([], dtype=float),
        })
        elo = pd.DataFrame({
            "team": ["Liverpool"],
            "date": pd.to_datetime(["2025-03-01"]),
            "elo": [2000.0],
            "country": ["ENG"],
            "level": [1],
        })

        result = match_elo_to_features(features, elo)

        assert len(result) == 0
        assert "home_elo" in result.columns
        assert "away_elo" in result.columns
