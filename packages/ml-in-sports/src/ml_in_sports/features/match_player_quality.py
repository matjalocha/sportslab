"""Match-level player quality features for match prediction.

Computes per-match squad quality indicators by joining player_matches
(who actually played) with fifa_ratings (player attributes). Produces
FIFA-based XI quality, market value quality, and bench strength
features, prefixed with home_/away_ for the final match DataFrame.
"""

import pandas as pd
import structlog

from ml_in_sports.utils.database import FootballDatabase

logger = structlog.get_logger(__name__)

_FIFA_ATTRIBUTE_COLS: list[str] = [
    "pace", "shooting", "passing", "dribbling",
    "defending", "physic",
]

_FIFA_META_COLS: list[str] = [
    "skill_moves", "weak_foot",
]

_FIFA_VERSION_SEASON_MAP: dict[str, str] = {
    "15": "1415",
    "16": "1516",
    "17": "1617",
    "18": "1718",
    "19": "1819",
    "20": "1920",
    "21": "2021",
    "22": "2122",
    "23": "2223",
    "24": "2324",
    "25": "2425",
    "26": "2526",
}


# ---------------------------------------------------------------------------
# Name normalization
# ---------------------------------------------------------------------------

def _normalize_player_name(name: str) -> str:
    """Normalize a player name for matching.

    Lowercases and strips whitespace. Does not remove special
    characters like hyphens or apostrophes.

    Args:
        name: Raw player name string.

    Returns:
        Normalized name string.
    """
    return name.strip().lower()


# ---------------------------------------------------------------------------
# FIFA version to season mapping
# ---------------------------------------------------------------------------

def _map_fifa_version_to_season(version: str) -> str | None:
    """Map a FIFA version string to a season code.

    Args:
        version: FIFA version string (e.g. "24").

    Returns:
        Season code (e.g. "2324") or None if not mappable.
    """
    if not version or not version.strip().isdigit():
        return None
    return _FIFA_VERSION_SEASON_MAP.get(version.strip())


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_player_matches(db: FootballDatabase) -> pd.DataFrame:
    """Load player_matches table from the database.

    Args:
        db: FootballDatabase instance.

    Returns:
        DataFrame with player match data.
    """
    return db.read_table("player_matches")


def _load_fifa_ratings(db: FootballDatabase) -> pd.DataFrame:
    """Load fifa_ratings table from the database.

    Args:
        db: FootballDatabase instance.

    Returns:
        DataFrame with FIFA rating data.
    """
    return db.read_table("fifa_ratings")


# ---------------------------------------------------------------------------
# Joining player_matches with fifa_ratings
# ---------------------------------------------------------------------------

def _add_normalized_names(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Add a normalized name column for matching.

    Args:
        df: DataFrame containing the name column.
        column: Name of the column to normalize.

    Returns:
        DataFrame with _norm_name column added.
    """
    result = df.copy()
    result["_norm_name"] = result[column].fillna("").apply(
        _normalize_player_name,
    )
    return result


def _prepare_fifa_with_season(fifa: pd.DataFrame) -> pd.DataFrame:
    """Add season column to FIFA ratings based on fifa_version.

    Args:
        fifa: FIFA ratings DataFrame.

    Returns:
        FIFA ratings with _fifa_season column added.
    """
    result = fifa.copy()
    result["_fifa_season"] = result["fifa_version"].astype(str).apply(
        _map_fifa_version_to_season,
    )
    return result


def _join_player_matches_with_fifa(
    player_matches: pd.DataFrame,
    fifa_ratings: pd.DataFrame,
) -> pd.DataFrame:
    """Join player_matches with fifa_ratings by normalized name.

    Uses exact name matching after normalization. Joins on player
    name and club name, preferring FIFA data from the matching season.

    Args:
        player_matches: Player match data with player and team columns.
        fifa_ratings: FIFA ratings with player_name and club_name.

    Returns:
        Merged DataFrame with FIFA attributes for matched players.
    """
    if player_matches.empty or fifa_ratings.empty:
        return pd.DataFrame()

    pm = _add_normalized_names(player_matches, "player")
    fifa = _add_normalized_names(fifa_ratings, "player_name")
    fifa = _prepare_fifa_with_season(fifa)

    merged = pm.merge(
        fifa,
        left_on=["_norm_name"],
        right_on=["_norm_name"],
        how="inner",
    )

    if merged.empty:
        return pd.DataFrame()

    merged = _filter_best_fifa_match(merged)
    return _drop_helper_columns(merged)


def _filter_best_fifa_match(merged: pd.DataFrame) -> pd.DataFrame:
    """Keep the best FIFA match per player-game pair.

    Prefers rows where the FIFA season matches the match season,
    then falls back to the highest overall rating.

    Args:
        merged: Merged player-matches + FIFA DataFrame.

    Returns:
        Deduplicated DataFrame with one row per player per game.
    """
    has_season = "season" in merged.columns
    has_fifa_season = "_fifa_season" in merged.columns
    if has_season and has_fifa_season:
        merged["_season_match"] = (
            merged["season"] == merged["_fifa_season"]
        ).astype(int)
    else:
        merged["_season_match"] = 0
    merged = merged.sort_values(
        ["_season_match", "overall"],
        ascending=[False, False],
    )
    return merged.drop_duplicates(
        subset=["game", "team", "player"],
        keep="first",
    )


def _drop_helper_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Remove internal helper columns from the DataFrame.

    Args:
        df: DataFrame with helper columns.

    Returns:
        DataFrame with helper columns removed.
    """
    helper_cols = [
        "_norm_name", "_fifa_season", "_season_match",
    ]
    existing = [c for c in helper_cols if c in df.columns]
    return df.drop(columns=existing)


# ---------------------------------------------------------------------------
# Build XI FIFA stats
# ---------------------------------------------------------------------------

def _build_xi_fifa_stats(
    player_matches: pd.DataFrame,
    fifa_ratings: pd.DataFrame,
) -> pd.DataFrame:
    """Build FIFA stats for active XI players.

    Filters to players with minutes > 0, then joins with FIFA data.

    Args:
        player_matches: Player match data.
        fifa_ratings: FIFA ratings data.

    Returns:
        DataFrame of active players with FIFA attributes.
    """
    active = _filter_active_players(player_matches)
    return _join_player_matches_with_fifa(active, fifa_ratings)


def _filter_active_players(
    player_matches: pd.DataFrame,
) -> pd.DataFrame:
    """Filter to players with minutes > 0.

    Args:
        player_matches: Player match DataFrame.

    Returns:
        DataFrame with only active players.
    """
    if player_matches.empty or "minutes" not in player_matches.columns:
        return player_matches
    return player_matches[player_matches["minutes"] > 0].copy()


# ---------------------------------------------------------------------------
# FIFA XI features
# ---------------------------------------------------------------------------

def _compute_fifa_xi_features(
    xi_data: pd.DataFrame,
) -> pd.DataFrame:
    """Compute FIFA-based XI quality features per game-team.

    Args:
        xi_data: Active players with FIFA attributes joined.

    Returns:
        DataFrame with one row per game-team with FIFA features.
    """
    if xi_data.empty:
        return pd.DataFrame()

    records: list[dict[str, object]] = []
    for (game, team), group in xi_data.groupby(["game", "team"]):
        record = _compute_single_xi_features(str(game), str(team), group)
        records.append(record)

    return pd.DataFrame(records)


def _compute_single_xi_features(
    game: str,
    team: str,
    group: pd.DataFrame,
) -> dict[str, object]:
    """Compute FIFA features for a single game-team XI.

    Args:
        game: Game identifier.
        team: Team name.
        group: Player rows for this game-team.

    Returns:
        Dict of feature name to value.
    """
    record: dict[str, object] = {
        "game": game,
        "team": team,
    }
    record["avg_overall_xi"] = group["overall"].mean()
    record["avg_potential_xi"] = group["potential"].mean()
    record["max_overall_xi"] = group["overall"].max()
    record["min_overall_xi"] = group["overall"].min()
    record["overall_std_xi"] = group["overall"].std()
    record["starting_gk_overall"] = _extract_gk_overall(group)

    _add_attribute_means(record, group)
    return record


def _extract_gk_overall(group: pd.DataFrame) -> float:
    """Extract the goalkeeper's overall rating from XI.

    Args:
        group: Player rows for one game-team.

    Returns:
        GK overall rating, or NaN if no GK found.
    """
    if "positions" not in group.columns:
        return float("nan")

    gk_mask = group["positions"].fillna("").str.contains("GK")
    gk_rows = group[gk_mask]

    if gk_rows.empty:
        return float("nan")
    return float(gk_rows["overall"].iloc[0])


def _add_attribute_means(
    record: dict[str, object],
    group: pd.DataFrame,
) -> None:
    """Add mean FIFA attribute columns to the record dict.

    Args:
        record: Dict to add features to (mutated in-place).
        group: Player rows for one game-team.
    """
    for attr in _FIFA_ATTRIBUTE_COLS:
        col_name = f"avg_{attr}_xi"
        if attr in group.columns:
            record[col_name] = group[attr].mean()
        else:
            record[col_name] = float("nan")

    for attr in _FIFA_META_COLS:
        col_name = f"avg_{attr}_xi"
        if attr in group.columns:
            record[col_name] = group[attr].mean()
        else:
            record[col_name] = float("nan")


# ---------------------------------------------------------------------------
# Market value features
# ---------------------------------------------------------------------------

def _compute_market_value_features(
    xi_data: pd.DataFrame,
) -> pd.DataFrame:
    """Compute market value features per game-team.

    Args:
        xi_data: Active players with value/wage columns.

    Returns:
        DataFrame with one row per game-team with value features.
    """
    if xi_data.empty:
        return pd.DataFrame()

    records: list[dict[str, object]] = []
    for (game, team), group in xi_data.groupby(["game", "team"]):
        record = _compute_single_value_features(str(game), str(team), group)
        records.append(record)

    return pd.DataFrame(records)


def _compute_single_value_features(
    game: str,
    team: str,
    group: pd.DataFrame,
) -> dict[str, object]:
    """Compute market value features for a single game-team.

    Args:
        game: Game identifier.
        team: Team name.
        group: Player rows for this game-team.

    Returns:
        Dict of feature name to value.
    """
    record: dict[str, object] = {
        "game": game,
        "team": team,
    }

    if "value_eur" in group.columns:
        record["total_value_eur_xi"] = group["value_eur"].sum()
        record["avg_value_eur_xi"] = group["value_eur"].mean()
        record["max_value_eur_xi"] = group["value_eur"].max()
    else:
        record["total_value_eur_xi"] = float("nan")
        record["avg_value_eur_xi"] = float("nan")
        record["max_value_eur_xi"] = float("nan")

    if "wage_eur" in group.columns:
        record["total_wage_eur_xi"] = group["wage_eur"].sum()
    else:
        record["total_wage_eur_xi"] = float("nan")

    return record


# ---------------------------------------------------------------------------
# FIFA match rate
# ---------------------------------------------------------------------------

def _compute_fifa_match_rate(
    player_matches: pd.DataFrame,
    xi_data: pd.DataFrame,
) -> pd.DataFrame:
    """Compute the proportion of XI players with FIFA data.

    Args:
        player_matches: All player match data.
        xi_data: Matched XI players with FIFA attributes.

    Returns:
        DataFrame with game, team, fifa_match_rate_xi columns.
    """
    active = _filter_active_players(player_matches)
    if active.empty:
        return pd.DataFrame()

    total_counts = active.groupby(
        ["game", "team"],
    ).size().reset_index(name="_total")

    if xi_data.empty:
        total_counts["fifa_match_rate_xi"] = 0.0
        return total_counts[["game", "team", "fifa_match_rate_xi"]]

    matched_counts = xi_data.groupby(
        ["game", "team"],
    ).size().reset_index(name="_matched")

    merged = total_counts.merge(
        matched_counts,
        on=["game", "team"],
        how="left",
    )
    merged["_matched"] = merged["_matched"].fillna(0)
    merged["fifa_match_rate_xi"] = merged["_matched"] / merged["_total"]

    return merged[["game", "team", "fifa_match_rate_xi"]]


# ---------------------------------------------------------------------------
# Bench strength
# ---------------------------------------------------------------------------

def _compute_bench_strength(
    xi_players: pd.DataFrame,
    fifa_ratings: pd.DataFrame,
) -> pd.DataFrame:
    """Compute bench strength as avg overall of non-XI squad members.

    Args:
        xi_players: DataFrame with game, team, player for XI players.
        fifa_ratings: Full FIFA ratings for all players.

    Returns:
        DataFrame with team and bench_avg_overall columns.
    """
    if xi_players.empty or fifa_ratings.empty:
        return pd.DataFrame(columns=["team", "bench_avg_overall"])

    teams = xi_players["team"].unique()
    xi_names = _get_xi_normalized_names(xi_players)

    records: list[dict[str, object]] = []
    for team in teams:
        bench_overall = _compute_team_bench_overall(
            team, xi_names, fifa_ratings,
        )
        records.append({
            "team": team,
            "bench_avg_overall": bench_overall,
        })

    return pd.DataFrame(records)


def _get_xi_normalized_names(
    xi_players: pd.DataFrame,
) -> set[str]:
    """Get normalized names of XI players.

    Args:
        xi_players: XI player DataFrame with player column.

    Returns:
        Set of normalized player name strings.
    """
    return set(
        xi_players["player"].fillna("").apply(
            _normalize_player_name,
        ).unique(),
    )


def _compute_team_bench_overall(
    team: str,
    xi_names: set[str],
    fifa_ratings: pd.DataFrame,
) -> float:
    """Compute bench avg overall for a single team.

    Args:
        team: Team name.
        xi_names: Set of normalized XI player names.
        fifa_ratings: FIFA ratings DataFrame.

    Returns:
        Mean overall of bench players, or NaN if none.
    """
    club_players = fifa_ratings[
        fifa_ratings["club_name"] == team
    ].copy()

    if club_players.empty:
        return float("nan")

    club_players["_norm"] = club_players["player_name"].fillna("").apply(
        _normalize_player_name,
    )
    bench = club_players[~club_players["_norm"].isin(xi_names)]

    if bench.empty:
        return float("nan")
    return bench["overall"].mean()


# ---------------------------------------------------------------------------
# Join features to match DataFrame
# ---------------------------------------------------------------------------

def _join_features_to_matches(
    match_df: pd.DataFrame,
    features: pd.DataFrame,
    feature_cols: list[str],
) -> pd.DataFrame:
    """Join game-team features to match DataFrame as home_/away_ columns.

    Args:
        match_df: Match-level DataFrame with home_team, away_team.
        features: Feature DataFrame with game and team columns.
        feature_cols: List of feature column names to join.

    Returns:
        Match DataFrame with home_/away_ prefixed feature columns.
    """
    if features.empty:
        return match_df

    result = match_df.copy()
    result = _join_side(result, features, feature_cols, "home")
    result = _join_side(result, features, feature_cols, "away")
    return result


def _join_side(
    df: pd.DataFrame,
    features: pd.DataFrame,
    feature_cols: list[str],
    side: str,
) -> pd.DataFrame:
    """Join features for one side (home or away).

    Args:
        df: Match DataFrame.
        features: Feature data with game and team columns.
        feature_cols: Feature column names.
        side: "home" or "away".

    Returns:
        DataFrame with side-prefixed feature columns.
    """
    team_col = f"{side}_team"
    available = [c for c in feature_cols if c in features.columns]
    if not available:
        return df

    subset = features[["game", "team", *available]].copy()
    renamed = subset.rename(columns={
        col: f"{side}_{col}" for col in available
    })
    renamed = renamed.rename(columns={"team": team_col})

    return df.merge(
        renamed, on=["game", team_col], how="left",
    )


# ---------------------------------------------------------------------------
# Bench features join
# ---------------------------------------------------------------------------

def _join_bench_to_matches(
    match_df: pd.DataFrame,
    bench: pd.DataFrame,
) -> pd.DataFrame:
    """Join bench strength to match DataFrame.

    Args:
        match_df: Match-level DataFrame.
        bench: Bench strength DataFrame with team and bench_avg_overall.

    Returns:
        Match DataFrame with home_/away_ bench columns.
    """
    if bench.empty:
        return match_df

    result = match_df.copy()
    for side in ["home", "away"]:
        team_col = f"{side}_team"
        merged = result[[team_col]].merge(
            bench.rename(columns={"team": team_col}),
            on=team_col,
            how="left",
        )
        result[f"{side}_bench_avg_overall"] = (
            merged["bench_avg_overall"].values
        )
    return result


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def add_match_player_quality(
    df: pd.DataFrame,
    db: FootballDatabase,
    player_matches_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Add match-level player quality features to a match DataFrame.

    Loads player_matches and fifa_ratings from the database, computes
    per-match FIFA XI quality, market value features, match rate,
    and bench strength, then joins them as home_/away_ columns.

    Args:
        df: Match-level DataFrame with game, home_team, away_team.
        db: FootballDatabase instance for reading tables.
        player_matches_df: Pre-loaded player_matches (skips DB load).

    Returns:
        DataFrame with player quality feature columns added.
    """
    if df.empty:
        return df.copy()

    player_matches = (
        player_matches_df if player_matches_df is not None
        else _load_player_matches(db)
    )
    if player_matches.empty:
        logger.warning("No player_matches data, skipping quality features")
        return df.copy()

    fifa_ratings = _load_fifa_ratings(db)
    if fifa_ratings.empty:
        logger.warning("No fifa_ratings data, skipping quality features")
        return df.copy()

    xi_data = _build_xi_fifa_stats(player_matches, fifa_ratings)
    if xi_data.empty:
        logger.warning("No FIFA matches found for XI players")
        return df.copy()

    result = df.copy()
    result = _add_fifa_xi_features(result, xi_data)
    result = _add_value_features(result, xi_data)
    result = _add_match_rate_features(result, player_matches, xi_data)
    result = _add_bench_features(result, xi_data, fifa_ratings)

    new_cols = len(result.columns) - len(df.columns)
    logger.info("Added %d player quality feature columns", new_cols)

    return result


def _add_fifa_xi_features(
    match_df: pd.DataFrame,
    xi_data: pd.DataFrame,
) -> pd.DataFrame:
    """Add FIFA XI quality features to match DataFrame.

    Args:
        match_df: Match-level DataFrame.
        xi_data: XI players with FIFA attributes.

    Returns:
        Match DataFrame with FIFA XI feature columns.
    """
    fifa_features = _compute_fifa_xi_features(xi_data)
    feature_cols = [
        "avg_overall_xi", "avg_potential_xi",
        "max_overall_xi", "min_overall_xi", "overall_std_xi",
        "starting_gk_overall",
        "avg_pace_xi", "avg_shooting_xi", "avg_passing_xi",
        "avg_dribbling_xi", "avg_defending_xi", "avg_physic_xi",
        "avg_skill_moves_xi", "avg_weak_foot_xi",
    ]
    return _join_features_to_matches(
        match_df, fifa_features, feature_cols,
    )


def _add_value_features(
    match_df: pd.DataFrame,
    xi_data: pd.DataFrame,
) -> pd.DataFrame:
    """Add market value features to match DataFrame.

    Args:
        match_df: Match-level DataFrame.
        xi_data: XI players with value/wage columns.

    Returns:
        Match DataFrame with value feature columns.
    """
    value_features = _compute_market_value_features(xi_data)
    feature_cols = [
        "total_value_eur_xi", "avg_value_eur_xi",
        "max_value_eur_xi", "total_wage_eur_xi",
    ]
    return _join_features_to_matches(
        match_df, value_features, feature_cols,
    )


def _add_match_rate_features(
    match_df: pd.DataFrame,
    player_matches: pd.DataFrame,
    xi_data: pd.DataFrame,
) -> pd.DataFrame:
    """Add FIFA match rate features to match DataFrame.

    Args:
        match_df: Match-level DataFrame.
        player_matches: All player match data.
        xi_data: Matched XI players.

    Returns:
        Match DataFrame with match rate columns.
    """
    match_rate = _compute_fifa_match_rate(player_matches, xi_data)
    return _join_features_to_matches(
        match_df, match_rate, ["fifa_match_rate_xi"],
    )


def _add_bench_features(
    match_df: pd.DataFrame,
    xi_data: pd.DataFrame,
    fifa_ratings: pd.DataFrame,
) -> pd.DataFrame:
    """Add bench strength features to match DataFrame.

    Args:
        match_df: Match-level DataFrame.
        xi_data: XI players DataFrame.
        fifa_ratings: Full FIFA ratings.

    Returns:
        Match DataFrame with bench strength columns.
    """
    xi_players = xi_data[["game", "team", "player"]].copy()
    bench = _compute_bench_strength(xi_players, fifa_ratings)
    return _join_bench_to_matches(match_df, bench)
