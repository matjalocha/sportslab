"""Tests for the central league registry."""

from ml_in_sports.processing.leagues import (
    LEAGUE_REGISTRY,
    LeagueInfo,
    get_all_leagues,
    get_league,
)


def test_league_registry_has_all_14_leagues() -> None:
    """Registry contains all R5a supported leagues."""
    assert len(LEAGUE_REGISTRY) == 16
    assert "ENG-Premier League" in LEAGUE_REGISTRY
    assert "ENG-Championship" in LEAGUE_REGISTRY
    assert "NED-Eredivisie" in LEAGUE_REGISTRY
    assert "GRE-Super League" in LEAGUE_REGISTRY
    assert "SCO-Premiership" in LEAGUE_REGISTRY
    assert "ESP-Segunda" in LEAGUE_REGISTRY
    assert "FRA-Ligue 2" in LEAGUE_REGISTRY
    assert "TUR-Süper Lig" in LEAGUE_REGISTRY


def test_get_league_returns_league_info() -> None:
    """get_league returns canonical metadata."""
    league = get_league("ENG-Championship")

    assert league == LeagueInfo(
        "ENG-Championship",
        "E1",
        "England",
        2,
        False,
        True,
    )


def test_get_league_returns_none_for_unknown() -> None:
    """Unknown names do not raise."""
    assert get_league("UNKNOWN-League") is None


def test_get_all_leagues_tier_filter() -> None:
    """Tier filtering returns only the requested tier."""
    tier_two = get_all_leagues(tier=2)

    assert {league.canonical_name for league in tier_two} == {
        "ENG-Championship",
        "GER-Bundesliga 2",
        "ITA-Serie B",
        "ESP-Segunda",
        "FRA-Ligue 2",
    }
