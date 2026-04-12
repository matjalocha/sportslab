"""Sofascore data types, constants, and serialization helpers.

Defines the MatchStats and SofascoreMatchEvent dataclasses, tournament
and season ID lookup tables, and functions for parsing/building/
converting MatchStats instances.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any

# Sofascore unique tournament IDs for our target leagues.
SOFASCORE_TOURNAMENTS: dict[str, int] = {
    "ENG-Premier League": 17,
    "ENG-Championship": 18,
    "ESP-La Liga": 8,
    "ESP-Segunda": 54,
    "GER-Bundesliga": 35,
    "GER-Bundesliga 2": 44,
    "ITA-Serie A": 23,
    "ITA-Serie B": 53,
    "FRA-Ligue 1": 34,
    "FRA-Ligue 2": 182,
    "NED-Eredivisie": 37,
    "POR-Primeira Liga": 238,
    "BEL-Jupiler Pro League": 38,
    "TUR-Süper Lig": 52,
    "GRE-Super League": 185,
    "SCO-Premiership": 36,
}

# Sofascore season IDs keyed by our season code (e.g. "24/25").
# These change every year and must be updated manually or discovered
# via the /api/v1/unique-tournament/{id}/seasons endpoint.
SOFASCORE_SEASON_IDS: dict[str, dict[str, int]] = {
    "24/25": {
        "ENG-Premier League": 61627,
        "ENG-Championship": 62045,
        "ESP-La Liga": 61643,
        "ESP-Segunda": 62046,
        "GER-Bundesliga": 61635,
        "GER-Bundesliga 2": 62047,
        "ITA-Serie A": 61639,
        "ITA-Serie B": 62048,
        "FRA-Ligue 1": 61736,
        "FRA-Ligue 2": 62049,
        "NED-Eredivisie": 61641,
        "POR-Primeira Liga": 62050,
        "BEL-Jupiler Pro League": 62051,
        "TUR-Süper Lig": 62052,
        "GRE-Super League": 62053,
        "SCO-Premiership": 62054,
    },
}

# JavaScript template: fetch match list from Sofascore API.
# Parameters: tournamentId (int), seasonId (int), page (int).
_JS_FETCH_MATCH_LIST = """
const resp = await fetch(
    '/api/v1/unique-tournament/' + arguments[0]
    + '/season/' + arguments[1]
    + '/events/last/' + arguments[2]
);
if (!resp.ok) return JSON.stringify({error: resp.status});
const data = await resp.json();
return JSON.stringify(
    (data.events || []).map(e => ({
        id: e.id,
        home: e.homeTeam.name,
        away: e.awayTeam.name,
        date: e.startTimestamp
    }))
);
"""

# JavaScript template: fetch match statistics and flatten nested structure.
# Parameters: matchId (int).
_JS_FETCH_MATCH_STATS = """
const matchId = arguments[0];
const resp = await fetch('/api/v1/event/' + matchId + '/statistics');
if (!resp.ok) return JSON.stringify({error: resp.status});
const data = await resp.json();
const stats = {};
for (const period of data.statistics || []) {
    if (period.period !== 'ALL') continue;
    for (const group of period.groups || []) {
        for (const item of group.statisticsItems || []) {
            stats[item.key + '_home'] = item.homeValue;
            stats[item.key + '_away'] = item.awayValue;
        }
    }
}
return JSON.stringify(stats);
"""


@dataclass(frozen=True)
class SofascoreMatchEvent:
    """Minimal match metadata from the Sofascore events endpoint."""

    match_id: int
    home_team: str
    away_team: str
    start_timestamp: int


@dataclass(frozen=True)
class MatchStats:
    """Statistics for one match from Sofascore.

    All stat fields are Optional because Sofascore does not guarantee
    every statistic is present for every match (e.g. lower leagues
    may lack xG or detailed passing data).
    """

    match_id: int
    home_team: str
    away_team: str
    date: str
    # Tactical stats
    home_possession: float | None
    away_possession: float | None
    home_total_shots: int | None
    away_total_shots: int | None
    home_shots_on_target: int | None
    away_shots_on_target: int | None
    home_tackles: int | None
    away_tackles: int | None
    home_accurate_passes: int | None
    away_accurate_passes: int | None
    home_accurate_passes_pct: float | None
    away_accurate_passes_pct: float | None
    home_accurate_crosses: int | None
    away_accurate_crosses: int | None
    home_interceptions: int | None
    away_interceptions: int | None
    home_clearances: int | None
    away_clearances: int | None
    home_accurate_long_balls: int | None
    away_accurate_long_balls: int | None
    home_ground_duels_won: int | None
    away_ground_duels_won: int | None
    home_aerial_duels_won: int | None
    away_aerial_duels_won: int | None
    home_successful_dribbles: int | None
    away_successful_dribbles: int | None
    home_saves: int | None
    away_saves: int | None
    # xG
    home_expected_goals: float | None
    away_expected_goals: float | None


# Mapping from Sofascore JSON keys to MatchStats field names (minus home/away prefix).
# The JSON keys use camelCase; we map to snake_case fields.
_STAT_KEY_MAP: dict[str, str] = {
    "ballPossession": "possession",
    "totalShotsOnGoal": "total_shots",  # Sofascore calls total "on goal"
    "shotsOnTarget": "shots_on_target",
    "tackles": "tackles",
    "accuratePasses": "accurate_passes",
    "accuratePassesPercentage": "accurate_passes_pct",
    "accurateCrosses": "accurate_crosses",
    "interceptions": "interceptions",
    "clearances": "clearances",
    "accurateLongBalls": "accurate_long_balls",
    "groundDuelsWon": "ground_duels_won",
    "aerialDuelsWon": "aerial_duels_won",
    "successfulDribbles": "successful_dribbles",
    "saves": "saves",
    "expectedGoals": "expected_goals",
}


def parse_stat_value(value: Any) -> int | float | None:
    """Parse a stat value from Sofascore JSON to int or float.

    Sofascore returns stats as strings like "62%", "15", "1.45",
    or sometimes as plain numbers. This function normalises them.

    Args:
        value: Raw value from Sofascore JSON.

    Returns:
        Parsed numeric value or None if unparseable.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        cleaned = value.strip().rstrip("%")
        if not cleaned:
            return None
        try:
            if "." in cleaned:
                return float(cleaned)
            return int(cleaned)
        except ValueError:
            return None
    return None


def build_match_stats(
    match_id: int,
    home_team: str,
    away_team: str,
    date: str,
    raw_stats: dict[str, Any],
) -> MatchStats:
    """Build a MatchStats from flattened Sofascore JSON stats.

    The raw_stats dict has keys like ``"ballPossession_home"``,
    ``"tackles_away"``, etc. This function maps them to MatchStats fields.

    Args:
        match_id: Sofascore event ID.
        home_team: Home team name.
        away_team: Away team name.
        date: ISO date string.
        raw_stats: Flattened statistics dict from the JS fetch script.

    Returns:
        Populated MatchStats dataclass.
    """
    parsed: dict[str, Any] = {
        "match_id": match_id,
        "home_team": home_team,
        "away_team": away_team,
        "date": date,
    }

    for sofa_key, field_base in _STAT_KEY_MAP.items():
        home_raw = raw_stats.get(f"{sofa_key}_home")
        away_raw = raw_stats.get(f"{sofa_key}_away")
        parsed[f"home_{field_base}"] = parse_stat_value(home_raw)
        parsed[f"away_{field_base}"] = parse_stat_value(away_raw)

    # Only pass fields that exist on MatchStats to avoid TypeError
    valid_field_names = {f.name for f in fields(MatchStats)}
    filtered = {k: v for k, v in parsed.items() if k in valid_field_names}
    return MatchStats(**filtered)


def match_stats_to_dict(stats: MatchStats) -> dict[str, Any]:
    """Convert MatchStats to a JSON-serialisable dict.

    Args:
        stats: MatchStats instance.

    Returns:
        Dictionary suitable for ``json.dumps``.
    """
    return asdict(stats)


def match_stats_from_dict(data: dict[str, Any]) -> MatchStats:
    """Reconstruct MatchStats from a dict (e.g. loaded from JSON cache).

    Args:
        data: Dictionary with MatchStats field names as keys.

    Returns:
        MatchStats instance.
    """
    valid_field_names = {f.name for f in fields(MatchStats)}
    filtered = {k: v for k, v in data.items() if k in valid_field_names}
    return MatchStats(**filtered)
