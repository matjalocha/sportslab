"""Pipeline orchestration: extract, merge, and store football data.

Coordinates extractors and database to build unified datasets.
Checks scrape_log to avoid re-fetching already stored data.
"""

import re
from collections.abc import Callable
from datetime import UTC, date, datetime

import pandas as pd
import structlog

from ml_in_sports.processing.extractors import (
    ALL_LEAGUES,
    LEAGUE_CONFIG,
    ClubEloExtractor,
    EspnExtractor,
    FifaRatingsExtractor,
    FootballDataExtractor,
    SofascoreExtractor,
    TransfermarktExtractor,
    UnderstatExtractor,
)
from ml_in_sports.utils.database import FootballDatabase
from ml_in_sports.utils.seasons import season_start_date
from ml_in_sports.utils.team_names import normalize_team_name

logger = structlog.get_logger(__name__)

ESPN_COLUMN_RENAMES: dict[str, str] = {
    "home_possession_pct": "home_possession",
    "away_possession_pct": "away_possession",
    "home_fouls_committed": "home_fouls",
    "away_fouls_committed": "away_fouls",
}


def _get_season_start(season: str) -> str:
    """Get approximate season start date for Elo lookup.

    Args:
        season: Season code (e.g. "2324").

    Returns:
        Date string in YYYY-MM-DD format.
    """
    return season_start_date(season)


def _parse_game_key(game: str) -> tuple[str, str] | None:
    """Split game key into (date, teams).

    Args:
        game: Game key like "2023-08-12 Bournemouth-West Ham".

    Returns:
        Tuple of (date_str, teams_str) or None if unparseable.
    """
    match = re.match(r"^(\d{4}-\d{2}-\d{2}) (.+)$", game)
    if not match:
        return None
    return match.group(1), match.group(2)


def _align_espn_dates(
    existing: pd.DataFrame,
    espn_df: pd.DataFrame,
) -> pd.DataFrame:
    """Align ESPN game dates to match existing data.

    When ESPN and Understat record the same match on different
    dates (timezone offset or rescheduled fixture), adjusts
    the ESPN game key to use the existing (Understat) date.

    Matching priority:
    1. Exact date match — no change needed.
    2. Date differs by 1 day — timezone fix.
    3. Same home-away pair, any date — rescheduled fixture.

    Args:
        existing: Matches from DB with canonical game keys.
        espn_df: ESPN data with potentially shifted dates.

    Returns:
        ESPN DataFrame with aligned game keys.
    """
    existing_lookup: dict[str, list[tuple[str, str]]] = {}
    for game in existing["game"].unique():
        parsed = _parse_game_key(game)
        if parsed:
            date_str, teams = parsed
            existing_lookup.setdefault(teams, []).append(
                (date_str, game),
            )

    def fix_game_key(espn_game: str) -> str:
        parsed = _parse_game_key(espn_game)
        if not parsed:
            return espn_game
        espn_date_str, teams = parsed

        candidates = existing_lookup.get(teams, [])
        if not candidates:
            return espn_game

        for exist_date_str, _exist_game in candidates:
            if espn_date_str == exist_date_str:
                return espn_game

        for exist_date_str, exist_game in candidates:
            try:
                d1 = date.fromisoformat(espn_date_str)
                d2 = date.fromisoformat(exist_date_str)
                if abs((d1 - d2).days) == 1:
                    return exist_game
            except ValueError:
                continue

        if len(candidates) == 1:
            return candidates[0][1]

        return espn_game

    espn_df = espn_df.copy()
    espn_df["game"] = espn_df["game"].map(fix_game_key)
    return espn_df


# ESPN season offset: soccerdata returns wrong season for some codes.
# Key = (league, season_we_want), Value = ESPN season code to request.
ESPN_SEASON_OVERRIDES: dict[tuple[str, str], str] = {
    ("ITA-Serie A", "1415"): "1516",
}


def _normalize_game_key(game: str) -> str:
    """Normalize team names within a game key.

    Handles hyphenated team names (e.g. Saint-Etienne) by trying
    all possible split positions and picking the one where the
    most parts are recognized as known aliases.

    Args:
        game: Game key like "2023-08-12 Bournemouth-West Ham".

    Returns:
        Game key with canonical team names.
    """
    match = re.match(r"^(\d{4}-\d{2}-\d{2}) (.+)$", game)
    if not match:
        return game
    date_str, teams_str = match.groups()

    positions = [i for i, c in enumerate(teams_str) if c == "-"]
    if not positions:
        return game

    best_score = 0
    best_result = None

    for pos in positions:
        home_raw = teams_str[:pos]
        away_raw = teams_str[pos + 1 :]
        home_norm = normalize_team_name(home_raw)
        away_norm = normalize_team_name(away_raw)
        score = (home_norm != home_raw) + (away_norm != away_raw)
        if score > best_score:
            best_score = score
            best_result = f"{date_str} {home_norm}-{away_norm}"

    if best_result:
        return best_result

    # Fallback: greedy split (last hyphen)
    home = teams_str[: positions[-1]]
    away = teams_str[positions[-1] + 1 :]
    return (
        f"{date_str} "
        f"{normalize_team_name(home)}-{normalize_team_name(away)}"
    )


def _normalize_team_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize home_team and away_team columns.

    Args:
        df: DataFrame with team columns.

    Returns:
        DataFrame with canonical team names.
    """
    for col in ("home_team", "away_team"):
        if col in df.columns:
            df[col] = df[col].map(normalize_team_name)
    return df


def _normalize_game_index(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize game keys in a DataFrame with game column or MultiIndex.

    Args:
        df: DataFrame with 'game' column.

    Returns:
        DataFrame with normalized game keys.
    """
    if "game" in df.columns:
        df["game"] = df["game"].map(_normalize_game_key)
    return df


def _extract_source(
    db: FootballDatabase,
    source_name: str,
    league: str,
    season: str,
    extract_fn: Callable[[], pd.DataFrame | None],
) -> pd.DataFrame | None:
    """Extract data from a source with scrape_log check.

    Args:
        db: Database instance.
        source_name: Name for scrape_log.
        league: League identifier.
        season: Season code.
        extract_fn: Callable that returns Optional[pd.DataFrame].

    Returns:
        Extracted DataFrame or None.
    """
    if db.is_scraped(source_name, league, season):
        logger.info(f"Skipping {source_name} ({league} {season}): already scraped")
        return None

    result = extract_fn()
    if result is not None:
        db.log_scrape(source_name, league, season, len(result), "success")

    return result


def _add_elo_to_matches(
    matches: pd.DataFrame,
    elo_df: pd.DataFrame,
) -> pd.DataFrame:
    """Add home_elo and away_elo columns to match data.

    Normalizes both elo key names and match team names
    to ensure ClubElo names (e.g. "ManCity") match our
    canonical names (e.g. "Manchester City").

    Args:
        matches: Match DataFrame with home_team/away_team columns.
        elo_df: Elo DataFrame indexed by team name.

    Returns:
        Match DataFrame with elo columns added.
    """
    elo_lookup = {
        normalize_team_name(str(team)): elo
        for team, elo in elo_df["elo"].to_dict().items()
    }

    matches["home_elo"] = matches["home_team"].map(
        lambda t: elo_lookup.get(normalize_team_name(t))
    )
    matches["away_elo"] = matches["away_team"].map(
        lambda t: elo_lookup.get(normalize_team_name(t))
    )
    return matches


def backfill_elo_ratings(
    db: FootballDatabase | None = None,
) -> int:
    """Re-join Elo ratings to all existing matches in the database.

    Reads elo_ratings and matches tables, rebuilds the lookup
    with normalized team names, and updates home_elo/away_elo
    for every match row grouped by season.

    Args:
        db: Optional database instance.

    Returns:
        Number of matches updated with Elo data.
    """
    if db is None:
        db = FootballDatabase()

    elo_all = db.read_table("elo_ratings")
    if elo_all.empty:
        logger.warning("No elo_ratings in database, nothing to backfill")
        return 0

    matches = db.read_table("matches")
    if matches.empty:
        logger.warning("No matches in database, nothing to backfill")
        return 0

    elo_by_date: dict[str, dict[str, float]] = {}
    for _, row in elo_all.iterrows():
        date_key = row["date"]
        team_key = normalize_team_name(row["team"])
        if date_key not in elo_by_date:
            elo_by_date[date_key] = {}
        elo_by_date[date_key][team_key] = row["elo"]

    updated_count = 0
    for season in matches["season"].unique():
        elo_date = _get_season_start(season)
        lookup = elo_by_date.get(elo_date, {})
        if not lookup:
            continue

        season_mask = matches["season"] == season
        matches.loc[season_mask, "home_elo"] = (
            matches.loc[season_mask, "home_team"]
            .map(lambda t, _lk=lookup: _lk.get(normalize_team_name(t)))
        )
        matches.loc[season_mask, "away_elo"] = (
            matches.loc[season_mask, "away_team"]
            .map(lambda t, _lk=lookup: _lk.get(normalize_team_name(t)))
        )
        updated_count += season_mask.sum()

    _store_matches(db, matches)
    filled = matches["home_elo"].notna().sum()
    total = len(matches)
    pct = filled / total * 100 if total else 0
    logger.info(
        f"Backfilled Elo: {filled}/{total} matches "
        f"({pct:.1f}%) have home_elo"
    )
    return updated_count


def build_match_base(
    league: str,
    season: str,
    db: FootballDatabase | None = None,
) -> pd.DataFrame | None:
    """Build base match dataset from fast sources.

    Merges Understat (xG) + Sofascore (round) + ClubElo.
    Skips ESPN (slow). Stores result in database.

    Args:
        league: League identifier (e.g. "ENG-Premier League").
        season: Season code (e.g. "2324").
        db: Optional database for storage and scrape_log checks.

    Returns:
        Merged DataFrame with one row per match, or None.
    """
    if db is None:
        db = FootballDatabase()
        db.create_tables()

    understat = UnderstatExtractor()
    sofascore = SofascoreExtractor()
    elo_extractor = ClubEloExtractor()

    understat_df = _extract_source(
        db, "understat_matches", league, season,
        lambda: understat.extract_matches(league, season),
    )

    if understat_df is None:
        existing = db.read_table("matches", league=league, season=season)
        if not existing.empty:
            logger.info(f"Loaded {len(existing)} matches from DB")
            return existing
        logger.warning("No Understat data and no cached data")
        return None

    merged = _normalize_game_index(understat_df.reset_index())
    merged = _normalize_team_columns(merged)

    sofa_df = _extract_source(
        db, "sofascore_matches", league, season,
        lambda: sofascore.extract_matches(league, season),
    )
    if sofa_df is not None:
        sofa_reset = _normalize_game_index(sofa_df.reset_index())
        sofa_cols = ["league", "season", "game", "round", "week"]
        available_sofa = [c for c in sofa_cols if c in sofa_reset.columns]
        merged = merged.merge(
            sofa_reset[available_sofa],
            on=["league", "season", "game"],
            how="left",
        )

    elo_date = _get_season_start(season)
    elo_df = elo_extractor.extract_ratings(elo_date)
    if elo_df is not None:
        merged = _add_elo_to_matches(merged, elo_df)
        _store_elo_ratings(db, elo_df, elo_date)

    league_table = _extract_source(
        db, "sofascore_league_table", league, season,
        lambda: sofascore.extract_league_table(league, season),
    )
    if league_table is not None:
        _store_league_table(db, league_table, league, season)

    now = datetime.now(UTC).isoformat()
    merged["source_updated_at"] = now

    _store_matches(db, merged)
    logger.info(f"Built match base: {len(merged)} rows")
    return merged


def enrich_matches_espn(
    league: str,
    season: str,
    db: FootballDatabase | None = None,
    before_date: str | None = None,
) -> pd.DataFrame | None:
    """Enrich existing matches with ESPN stats.

    Reads matches from DB, merges ESPN matchsheet data, upserts back.
    Uses fuzzy date matching (±1 day) and season code overrides.

    Args:
        league: League identifier.
        season: Season code.
        db: Optional database instance.
        before_date: Only scrape matches before this date (YYYY-MM-DD).

    Returns:
        Updated DataFrame with ESPN columns, or None.
    """
    if db is None:
        db = FootballDatabase()
        db.create_tables()

    espn = EspnExtractor()
    espn_season = ESPN_SEASON_OVERRIDES.get(
        (league, season), season,
    )

    espn_df = _extract_source(
        db, "espn_matches", league, season,
        lambda: espn.extract_matches(
            league, espn_season, before_date=before_date,
        ),
    )
    if espn_df is None:
        return None

    existing = db.read_table("matches", league=league, season=season)
    if existing.empty:
        logger.warning("No base matches to enrich with ESPN data")
        return None

    existing = _normalize_game_index(existing)
    existing = _normalize_team_columns(existing)

    espn_reset = _normalize_game_index(espn_df.reset_index())
    espn_reset = espn_reset.rename(columns=ESPN_COLUMN_RENAMES)

    if espn_season != season:
        espn_reset["season"] = season

    espn_reset = _align_espn_dates(existing, espn_reset)

    merge_keys = ["league", "season", "game"]
    espn_new_cols = [c for c in espn_reset.columns if c not in merge_keys]
    existing = existing.drop(
        columns=[c for c in espn_new_cols if c in existing.columns],
    )

    merged = existing.merge(
        espn_reset, on=merge_keys, how="left",
    )

    now = datetime.now(UTC).isoformat()
    merged["source_updated_at"] = now

    _store_matches(db, merged)
    logger.info(f"Enriched matches with ESPN: {len(merged)} rows")
    return merged


def build_match_dataset(
    league: str,
    season: str,
    db: FootballDatabase | None = None,
) -> pd.DataFrame | None:
    """Build unified match dataset (base + ESPN).

    Convenience wrapper that runs both fast and slow passes.

    Args:
        league: League identifier (e.g. "ENG-Premier League").
        season: Season code (e.g. "2324").
        db: Optional database for storage and scrape_log checks.

    Returns:
        Merged DataFrame with one row per match, or None.
    """
    if db is None:
        db = FootballDatabase()
        db.create_tables()

    result = build_match_base(league, season, db)
    enriched = enrich_matches_espn(league, season, db)
    return enriched if enriched is not None else result


def build_player_base(
    league: str,
    season: str,
    db: FootballDatabase | None = None,
) -> pd.DataFrame | None:
    """Build base player-match dataset from Understat.

    Stores result in database. Does not include ESPN lineup data.

    Args:
        league: League identifier.
        season: Season code.
        db: Optional database for storage.

    Returns:
        DataFrame with one row per player-match, or None.
    """
    if db is None:
        db = FootballDatabase()
        db.create_tables()

    understat = UnderstatExtractor()

    understat_df = _extract_source(
        db, "understat_players", league, season,
        lambda: understat.extract_player_matches(league, season),
    )

    if understat_df is None:
        existing = db.read_table("player_matches", league=league, season=season)
        if not existing.empty:
            logger.info(f"Loaded {len(existing)} player records from DB")
            return existing
        return None

    merged = understat_df.reset_index()

    now = datetime.now(UTC).isoformat()
    merged["source_updated_at"] = now

    _store_player_matches(db, merged)
    logger.info(f"Built player base: {len(merged)} rows")
    return merged


def enrich_players_espn(
    league: str,
    season: str,
    db: FootballDatabase | None = None,
    before_date: str | None = None,
) -> pd.DataFrame | None:
    """Enrich existing player data with ESPN lineup stats.

    Reads player_matches from DB, merges ESPN lineup data, upserts back.
    Uses fuzzy date matching (±1 day) and season code overrides.

    Args:
        league: League identifier.
        season: Season code.
        db: Optional database instance.
        before_date: Only scrape matches before this date (YYYY-MM-DD).

    Returns:
        Updated DataFrame with ESPN columns, or None.
    """
    if db is None:
        db = FootballDatabase()
        db.create_tables()

    espn = EspnExtractor()
    espn_season = ESPN_SEASON_OVERRIDES.get(
        (league, season), season,
    )

    espn_df = _extract_source(
        db, "espn_players", league, season,
        lambda: espn.extract_player_matches(
            league, espn_season, before_date=before_date,
        ),
    )
    if espn_df is None:
        return None

    existing = db.read_table("player_matches", league=league, season=season)
    if existing.empty:
        logger.warning("No base player data to enrich with ESPN")
        return None

    espn_reset = espn_df.reset_index()
    espn_reset = _normalize_game_index(espn_reset)

    if espn_season != season:
        espn_reset["season"] = season

    existing_matches = db.read_table(
        "matches", league=league, season=season,
    )
    existing_matches = _normalize_game_index(existing_matches)
    espn_reset = _align_espn_dates(existing_matches, espn_reset)

    merge_keys = ["league", "season", "game", "team", "player"]
    espn_new_cols = [c for c in espn_reset.columns if c not in merge_keys]
    existing = existing.drop(
        columns=[c for c in espn_new_cols if c in existing.columns],
    )

    merged = existing.merge(
        espn_reset, on=merge_keys, how="left",
    )

    now = datetime.now(UTC).isoformat()
    merged["source_updated_at"] = now

    _store_player_matches(db, merged)
    logger.info(f"Enriched players with ESPN: {len(merged)} rows")
    return merged


def build_player_dataset(
    league: str,
    season: str,
    db: FootballDatabase | None = None,
) -> pd.DataFrame | None:
    """Build unified player-match dataset (base + ESPN).

    Convenience wrapper that runs both fast and slow passes.

    Args:
        league: League identifier.
        season: Season code.
        db: Optional database for storage.

    Returns:
        Merged DataFrame with one row per player-match, or None.
    """
    if db is None:
        db = FootballDatabase()
        db.create_tables()

    result = build_player_base(league, season, db)
    enriched = enrich_players_espn(league, season, db)
    return enriched if enriched is not None else result


def build_shot_dataset(
    league: str,
    season: str,
    db: FootballDatabase | None = None,
) -> pd.DataFrame | None:
    """Build shot-level dataset from Understat.

    Each row is one shot event with xG, coordinates, and result.

    Args:
        league: League identifier (e.g. "ENG-Premier League").
        season: Season code (e.g. "2324").
        db: Optional database for storage and scrape_log checks.

    Returns:
        DataFrame with one row per shot, or None.
    """
    if db is None:
        db = FootballDatabase()
        db.create_tables()

    understat = UnderstatExtractor()

    shots_df = _extract_source(
        db, "understat_shots", league, season,
        lambda: understat.extract_shots(league, season),
    )

    if shots_df is None:
        existing = db.read_table("shots", league=league, season=season)
        if not existing.empty:
            logger.info(f"Loaded {len(existing)} shots from DB")
            return existing
        return None

    merged = shots_df.reset_index()

    now = datetime.now(UTC).isoformat()
    merged["source_updated_at"] = now

    _store_shots(db, merged)
    logger.info(f"Built shot dataset: {len(merged)} rows")
    return merged


def build_odds_dataset(
    league: str,
    season: str,
    db: FootballDatabase | None = None,
) -> pd.DataFrame | None:
    """Build betting odds dataset from football-data.co.uk.

    Downloads CSV with match odds (1X2, O/U, Asian handicap)
    and stores in database.

    Args:
        league: League identifier (e.g. "ENG-Premier League").
        season: Season code (e.g. "2324").
        db: Optional database for storage and scrape_log checks.

    Returns:
        DataFrame with one row per match odds, or None.
    """
    if db is None:
        db = FootballDatabase()
        db.create_tables()

    extractor = FootballDataExtractor(league=league)

    odds_df = _extract_source(
        db, "football_data_odds", league, season,
        lambda: extractor.extract_odds(season),
    )

    if odds_df is None:
        existing = db.read_table("match_odds", league=league, season=season)
        if not existing.empty:
            logger.info(f"Loaded {len(existing)} odds from DB")
            return existing
        return None

    now = datetime.now(UTC).isoformat()
    odds_df["source_updated_at"] = now

    _store_match_odds(db, odds_df)
    logger.info(f"Built odds dataset: {len(odds_df)} rows")
    return odds_df


def build_transfermarkt_datasets(
    league: str = "ENG-Premier League",
    db: FootballDatabase | None = None,
) -> dict[str, pd.DataFrame | None]:
    """Download and store Transfermarkt data for a league.

    Downloads players, player valuations, and games tables
    filtered by competition ID. This is a one-time bulk download,
    not per-season.

    Args:
        league: League identifier (e.g. "ENG-Premier League").
        db: Optional database for storage and scrape_log checks.

    Returns:
        Dict of table name to DataFrame (or None if failed).
    """
    if db is None:
        db = FootballDatabase()
        db.create_tables()

    config = LEAGUE_CONFIG.get(league, {})
    competition_id = config.get("tm_competition_id", "GB1")
    extractor = TransfermarktExtractor(competition_id=competition_id)
    now = datetime.now(UTC).isoformat()
    results: dict[str, pd.DataFrame | None] = {}

    players = _extract_source(
        db, "transfermarkt_players", league, "all",
        extractor.extract_players,
    )
    if players is not None:
        players["source_updated_at"] = now
        _store_tm_players(db, players)
        logger.info(f"Stored {len(players)} TM players ({league})")
    results["players"] = players

    valuations = _extract_source(
        db, "transfermarkt_valuations", league, "all",
        extractor.extract_player_valuations,
    )
    if valuations is not None:
        valuations["source_updated_at"] = now
        _store_tm_player_valuations(db, valuations)
        logger.info(f"Stored {len(valuations)} TM valuations ({league})")
    results["valuations"] = valuations

    games = _extract_source(
        db, "transfermarkt_games", league, "all",
        extractor.extract_games,
    )
    if games is not None:
        games["source_updated_at"] = now
        _store_tm_games(db, games)
        logger.info(f"Stored {len(games)} TM games ({league})")
    results["games"] = games

    return results


ALL_FIFA_VERSIONS = [
    "15", "16", "17", "18", "19", "20",
    "21", "22", "23", "24", "25", "26",
]


def build_fifa_ratings(
    db: FootballDatabase | None = None,
    versions: list[str] | None = None,
    leagues: list[str] | None = None,
) -> dict[str, pd.DataFrame | None]:
    """Load FIFA/EA FC ratings from local CSVs into the database.

    Handles two file types:
    - Combined: male_players.csv (FIFA 15-24, read once, split by version)
    - Individual: version-specific CSVs (FC 25, FC 26)

    CSVs must be downloaded from Kaggle and placed in data/fifa/.

    Args:
        db: Optional database for storage.
        versions: FIFA versions to load (default: all 15-26).
        leagues: League identifiers to filter (default: EPL only).

    Returns:
        Dict of version to DataFrame (or None if not found).
    """
    if db is None:
        db = FootballDatabase()
        db.create_tables()

    if versions is None:
        versions = ALL_FIFA_VERSIONS

    if leagues is None:
        leagues = ["ENG-Premier League"]

    league_filters = _build_fifa_league_filters(leagues)
    scrape_label = _build_fifa_scrape_label(leagues)

    extractor = FifaRatingsExtractor(league_filters=league_filters)
    now = datetime.now(UTC).isoformat()
    results: dict[str, pd.DataFrame | None] = {}

    combined = extractor.extract_combined_ratings()
    for version in versions:
        if db.is_scraped(f"fifa_{version}", scrape_label, version):
            logger.info(f"Skipping FIFA {version}: already scraped")
            results[version] = None
            continue

        ratings = combined.get(version)
        if ratings is None:
            ratings = extractor.extract_ratings(version)

        if ratings is not None:
            ratings["source_updated_at"] = now
            _store_fifa_ratings(db, ratings)
            db.log_scrape(
                f"fifa_{version}", scrape_label, version,
                len(ratings), "success",
            )
            logger.info(f"Stored {len(ratings)} FIFA {version} ratings")
        else:
            db.log_scrape(
                f"fifa_{version}", scrape_label, version, 0, "failed",
            )
        results[version] = ratings

    return results


def _build_fifa_league_filters(leagues: list[str]) -> list[str]:
    """Convert league identifiers to FIFA CSV league name filters.

    Args:
        leagues: List of league identifiers.

    Returns:
        List of FIFA league name substrings for filtering.
    """
    return [
        LEAGUE_CONFIG[lg]["fifa_league_filter"]
        for lg in leagues
        if lg in LEAGUE_CONFIG
    ]


def _build_fifa_scrape_label(leagues: list[str]) -> str:
    """Build a scrape_log label for a set of leagues.

    Args:
        leagues: List of league identifiers.

    Returns:
        Label string for scrape_log (e.g. "ALL" or "EPL").
    """
    if set(leagues) == set(ALL_LEAGUES):
        return "ALL"
    if leagues == ["ENG-Premier League"]:
        return "EPL"
    return "+".join(sorted(leagues))


def _store_matches(
    db: FootballDatabase, df: pd.DataFrame,
) -> None:
    """Store match data in the database.

    Args:
        db: Database instance.
        df: Match DataFrame to store.
    """
    table_columns = [
        "league", "season", "game", "date", "home_team", "away_team",
        "home_goals", "away_goals", "home_xg", "away_xg",
        "home_np_xg", "away_np_xg", "home_expected_points",
        "away_expected_points", "home_ppda", "away_ppda",
        "home_deep_completions", "away_deep_completions",
        "home_possession", "away_possession",
        "home_total_shots", "away_total_shots",
        "home_shots_on_target", "away_shots_on_target",
        "home_effective_tackles", "away_effective_tackles",
        "home_total_tackles", "away_total_tackles",
        "home_accurate_passes", "away_accurate_passes",
        "home_total_passes", "away_total_passes",
        "home_accurate_crosses", "away_accurate_crosses",
        "home_effective_clearance", "away_effective_clearance",
        "home_interceptions", "away_interceptions",
        "home_saves", "away_saves",
        "home_fouls", "away_fouls",
        "home_yellow_cards", "away_yellow_cards",
        "home_red_cards", "away_red_cards",
        "home_won_corners", "away_won_corners",
        "home_offsides", "away_offsides",
        "home_blocked_shots", "away_blocked_shots",
        "home_total_crosses", "away_total_crosses",
        "home_total_long_balls", "away_total_long_balls",
        "home_accurate_long_balls", "away_accurate_long_balls",
        "home_total_clearance", "away_total_clearance",
        "home_penalty_kick_goals", "away_penalty_kick_goals",
        "home_penalty_kick_shots", "away_penalty_kick_shots",
        "home_attendance", "away_attendance",
        "round", "week", "home_elo", "away_elo",
        "source_updated_at",
    ]
    available = [c for c in table_columns if c in df.columns]
    db.upsert_dataframe("matches", df[available])


def _store_player_matches(
    db: FootballDatabase, df: pd.DataFrame,
) -> None:
    """Store player match data in the database.

    Args:
        db: Database instance.
        df: Player match DataFrame to store.
    """
    table_columns = [
        "league", "season", "game", "team", "player",
        "position", "minutes", "goals", "shots", "xg", "xa",
        "key_passes", "xg_chain", "xg_buildup", "own_goals",
        "assists", "fouls_committed", "fouls_suffered",
        "saves", "offsides", "total_shots_espn",
        "shots_on_target_espn", "sub_in", "sub_out",
        "yellow_cards", "red_cards", "source_updated_at",
    ]
    available = [c for c in table_columns if c in df.columns]
    db.upsert_dataframe("player_matches", df[available])


def _store_elo_ratings(
    db: FootballDatabase, elo_df: pd.DataFrame, date: str,
) -> None:
    """Store Elo ratings snapshot in the database.

    Args:
        db: Database instance.
        elo_df: Elo DataFrame indexed by team name.
        date: Date of the snapshot.
    """
    df = elo_df.reset_index()
    df["date"] = date

    table_columns = ["team", "date", "elo", "rank", "country", "league"]
    available = [c for c in table_columns if c in df.columns]
    db.upsert_dataframe("elo_ratings", df[available])


def _store_league_table(
    db: FootballDatabase, table_df: pd.DataFrame,
    league: str, season: str,
) -> None:
    """Store league standings in the database.

    Args:
        db: Database instance.
        table_df: Sofascore league table DataFrame.
        league: League identifier.
        season: Season code.
    """
    df = table_df.reset_index()
    df = df.rename(columns={
        "MP": "matches_played", "W": "wins", "D": "draws",
        "L": "losses", "GF": "goals_for", "GA": "goals_against",
        "GD": "goal_difference", "Pts": "points",
    })

    table_columns = [
        "league", "season", "team",
        "matches_played", "wins", "draws", "losses",
        "goals_for", "goals_against", "goal_difference", "points",
    ]
    available = [c for c in table_columns if c in df.columns]
    db.upsert_dataframe("league_tables", df[available])


def _store_shots(
    db: FootballDatabase, df: pd.DataFrame,
) -> None:
    """Store shot events in the database.

    Args:
        db: Database instance.
        df: Shot events DataFrame to store.
    """
    table_columns = [
        "league", "season", "game", "team", "player",
        "shot_id", "date", "xg", "location_x", "location_y",
        "minute", "body_part", "situation", "result",
        "assist_player", "player_id", "assist_player_id",
        "source_updated_at",
    ]
    available = [c for c in table_columns if c in df.columns]
    db.upsert_dataframe("shots", df[available])


def _store_match_odds(
    db: FootballDatabase, df: pd.DataFrame,
) -> None:
    """Store match betting odds in the database.

    Args:
        db: Database instance.
        df: Match odds DataFrame to store.
    """
    table_columns = [
        "league", "season", "game", "date", "home_team", "away_team",
        "ft_home_goals", "ft_away_goals", "ft_result",
        "ht_home_goals", "ht_away_goals", "ht_result",
        "referee",
        "home_shots", "away_shots",
        "home_shots_on_target", "away_shots_on_target",
        "home_fouls", "away_fouls",
        "home_corners", "away_corners",
        "home_yellow_cards", "away_yellow_cards",
        "home_red_cards", "away_red_cards",
        "b365_home", "b365_draw", "b365_away",
        "bw_home", "bw_draw", "bw_away",
        "iw_home", "iw_draw", "iw_away",
        "ps_home", "ps_draw", "ps_away",
        "wh_home", "wh_draw", "wh_away",
        "vc_home", "vc_draw", "vc_away",
        "max_home", "max_draw", "max_away",
        "avg_home", "avg_draw", "avg_away",
        "b365_over_25", "b365_under_25",
        "ps_over_25", "ps_under_25",
        "max_over_25", "max_under_25",
        "avg_over_25", "avg_under_25",
        "ah_handicap",
        "b365_ah_home", "b365_ah_away",
        "ps_ah_home", "ps_ah_away",
        "max_ah_home", "max_ah_away",
        "avg_ah_home", "avg_ah_away",
        "b365c_home", "b365c_draw", "b365c_away",
        "bwc_home", "bwc_draw", "bwc_away",
        "iwc_home", "iwc_draw", "iwc_away",
        "psc_home", "psc_draw", "psc_away",
        "whc_home", "whc_draw", "whc_away",
        "vcc_home", "vcc_draw", "vcc_away",
        "maxc_home", "maxc_draw", "maxc_away",
        "avgc_home", "avgc_draw", "avgc_away",
        "b365c_over_25", "b365c_under_25",
        "psc_over_25", "psc_under_25",
        "maxc_over_25", "maxc_under_25",
        "avgc_over_25", "avgc_under_25",
        "ahc_handicap",
        "b365c_ah_home", "b365c_ah_away",
        "psc_ah_home", "psc_ah_away",
        "maxc_ah_home", "maxc_ah_away",
        "avgc_ah_home", "avgc_ah_away",
        "source_updated_at",
    ]
    available = [c for c in table_columns if c in df.columns]
    db.upsert_dataframe("match_odds", df[available])


def _store_tm_players(
    db: FootballDatabase, df: pd.DataFrame,
) -> None:
    """Store Transfermarkt player profiles.

    Args:
        db: Database instance.
        df: Players DataFrame to store.
    """
    table_columns = [
        "player_id", "name", "first_name", "last_name",
        "position", "sub_position", "foot", "height_in_cm",
        "date_of_birth", "country_of_citizenship",
        "current_club_id", "current_club_name",
        "market_value_in_eur", "highest_market_value_in_eur",
        "contract_expiration_date", "source_updated_at",
    ]
    available = [c for c in table_columns if c in df.columns]
    db.upsert_dataframe("tm_players", df[available])


def _store_tm_player_valuations(
    db: FootballDatabase, df: pd.DataFrame,
) -> None:
    """Store Transfermarkt player market value history.

    Args:
        db: Database instance.
        df: Valuations DataFrame to store.
    """
    table_columns = [
        "player_id", "date", "market_value_in_eur",
        "current_club_id", "current_club_name",
        "source_updated_at",
    ]
    available = [c for c in table_columns if c in df.columns]
    db.upsert_dataframe("tm_player_valuations", df[available])


def _store_tm_games(
    db: FootballDatabase, df: pd.DataFrame,
) -> None:
    """Store Transfermarkt game data.

    Args:
        db: Database instance.
        df: Games DataFrame to store.
    """
    table_columns = [
        "game_id", "competition_id", "season", "round", "date",
        "home_club_id", "away_club_id",
        "home_club_name", "away_club_name",
        "home_club_goals", "away_club_goals",
        "home_club_manager_name", "away_club_manager_name",
        "stadium", "attendance", "referee",
        "home_club_formation", "away_club_formation",
        "source_updated_at",
    ]
    available = [c for c in table_columns if c in df.columns]
    db.upsert_dataframe("tm_games", df[available])


def _store_fifa_ratings(
    db: FootballDatabase, df: pd.DataFrame,
) -> None:
    """Store FIFA/EA FC player ratings.

    Args:
        db: Database instance.
        df: FIFA ratings DataFrame to store.
    """
    table_columns = [
        "player_name", "long_name", "age", "nationality",
        "club_name", "league_name", "overall", "potential",
        "value_eur", "wage_eur", "preferred_foot",
        "height_cm", "weight_kg", "positions",
        "pace", "shooting", "passing", "dribbling",
        "defending", "physic", "skill_moves", "weak_foot",
        "fifa_version", "source_updated_at",
    ]
    available = [c for c in table_columns if c in df.columns]
    db.upsert_dataframe("fifa_ratings", df[available])
