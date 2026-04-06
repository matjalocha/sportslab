"""League registry and football-data.co.uk data management."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LeagueInfo:
    """Metadata for a SportsLab-supported football league."""

    canonical_name: str
    football_data_code: str
    country: str
    tier: int
    has_xg: bool
    has_sofascore: bool


LEAGUE_REGISTRY: dict[str, LeagueInfo] = {
    "ENG-Premier League": LeagueInfo(
        "ENG-Premier League", "E0", "England", 1, True, True
    ),
    "ESP-La Liga": LeagueInfo("ESP-La Liga", "SP1", "Spain", 1, True, True),
    "GER-Bundesliga": LeagueInfo("GER-Bundesliga", "D1", "Germany", 1, True, True),
    "ITA-Serie A": LeagueInfo("ITA-Serie A", "I1", "Italy", 1, True, True),
    "FRA-Ligue 1": LeagueInfo("FRA-Ligue 1", "F1", "France", 1, True, True),
    "ENG-Championship": LeagueInfo(
        "ENG-Championship", "E1", "England", 2, False, True
    ),
    "NED-Eredivisie": LeagueInfo(
        "NED-Eredivisie", "N1", "Netherlands", 1, False, True
    ),
    "GER-Bundesliga 2": LeagueInfo(
        "GER-Bundesliga 2", "D2", "Germany", 2, False, True
    ),
    "ITA-Serie B": LeagueInfo("ITA-Serie B", "I2", "Italy", 2, False, True),
    "POR-Primeira Liga": LeagueInfo(
        "POR-Primeira Liga", "P1", "Portugal", 1, False, True
    ),
    "BEL-Jupiler Pro League": LeagueInfo(
        "BEL-Jupiler Pro League", "B1", "Belgium", 1, False, True
    ),
    "TUR-Süper Lig": LeagueInfo("TUR-Süper Lig", "T1", "Turkey", 1, False, True),
    "GRE-Super League": LeagueInfo(
        "GRE-Super League", "G1", "Greece", 1, False, True
    ),
    "SCO-Premiership": LeagueInfo(
        "SCO-Premiership", "SC0", "Scotland", 1, False, True
    ),
    "ESP-Segunda": LeagueInfo("ESP-Segunda", "SP2", "Spain", 2, False, True),
    "FRA-Ligue 2": LeagueInfo("FRA-Ligue 2", "F2", "France", 2, False, True),
}


def get_league(name: str) -> LeagueInfo | None:
    """Return league metadata by canonical SportsLab name."""
    return LEAGUE_REGISTRY.get(name)


def get_all_leagues(tier: int | None = None) -> list[LeagueInfo]:
    """Return all registered leagues, optionally filtered by tier."""
    leagues = list(LEAGUE_REGISTRY.values())
    if tier is not None:
        leagues = [league for league in leagues if league.tier == tier]
    return leagues
