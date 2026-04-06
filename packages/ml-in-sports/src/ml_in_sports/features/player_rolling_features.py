"""Player rolling performance features for match prediction.

Computes per-player rolling statistics (goals, xG, assists, etc.),
then aggregates them to team-match level. Captures the current form
of players who are actually playing in each match. All features use
shift(1) to prevent lookahead bias with season boundary resets.
"""

import pandas as pd
import structlog

from ml_in_sports.utils.database import FootballDatabase

logger = structlog.get_logger(__name__)

_DEFAULT_WINDOWS: list[int] = [3, 5, 10]

_PLAYER_ROLLING_STATS: list[str] = [
    "goals",
    "assists",
    "xg",
    "xa",
    "xg_overperformance",
    "shots",
    "key_passes",
    "xg_chain",
    "xg_buildup",
    "yellow_cards",
    "minutes",
]

_SUM_AGGREGATIONS: dict[str, str] = {
    "goals_rolling": "team_xi_goals_form",
    "xg_rolling": "team_xi_xg_form",
    "xa_rolling": "team_xi_xa_form",
    "key_passes_rolling": "team_xi_key_passes_form",
    "xg_overperformance_rolling": "team_xi_xg_overperformance",
    "xg_chain_rolling": "team_xi_xg_chain_form",
    "yellow_cards_rolling": "team_xi_discipline",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def add_player_rolling_features(
    df: pd.DataFrame,
    db: FootballDatabase,
    windows: list[int] | None = None,
    player_matches_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Add player-based rolling features to a match DataFrame.

    Loads player_matches from DB, computes per-player rolling stats,
    aggregates to team-match level, and joins as home_/away_ columns.

    Args:
        df: DataFrame with match-level data (game, home_team, etc.).
        db: FootballDatabase instance for loading player_matches.
        windows: Rolling window sizes (default: [3, 5, 10]).
        player_matches_df: Pre-loaded player_matches (skips DB load).

    Returns:
        DataFrame with player rolling feature columns added.
    """
    if df.empty:
        return df.copy()

    if windows is None:
        windows = _DEFAULT_WINDOWS

    player_matches = (
        player_matches_df if player_matches_df is not None
        else db.read_table("player_matches")
    )
    if player_matches.empty:
        logger.warning("No player_matches data found")
        return _add_empty_feature_columns(df, windows)

    rolled = _compute_player_rolling_stats(player_matches, windows)
    result = _aggregate_team_match_features(df, rolled, windows)

    logger.info(
        "Added player rolling features: %d new columns",
        len(result.columns) - len(df.columns),
    )
    return result


# ---------------------------------------------------------------------------
# Per-player rolling computation
# ---------------------------------------------------------------------------

def _compute_player_rolling_stats(
    player_matches: pd.DataFrame,
    windows: list[int],
) -> pd.DataFrame:
    """Compute rolling stats per player per season (vectorized).

    Args:
        player_matches: Raw player_matches table from DB.
        windows: Rolling window sizes.

    Returns:
        Player matches with rolling stat columns added.
    """
    if player_matches.empty:
        return pd.DataFrame()

    result = player_matches.copy()
    result = _add_xg_overperformance_raw(result)
    result = _sort_player_matches(result)

    group_keys = ["player", "season"]
    for stat_name in _PLAYER_ROLLING_STATS:
        if stat_name not in result.columns:
            continue
        shifted = result.groupby(group_keys, sort=False)[stat_name].shift(1)
        for window in windows:
            col_name = f"{stat_name}_rolling_{window}"
            rolled = (
                shifted
                .groupby([result["player"], result["season"]], sort=False)
                .rolling(window=window, min_periods=window)
                .mean()
            )
            result[col_name] = rolled.droplevel([0, 1])

    return result


def _add_xg_overperformance_raw(
    player_matches: pd.DataFrame,
) -> pd.DataFrame:
    """Add raw xG overperformance column (goals - xG).

    Args:
        player_matches: Player matches DataFrame.

    Returns:
        DataFrame with xg_overperformance column added.
    """
    result = player_matches.copy()
    if "goals" in result.columns and "xg" in result.columns:
        result["xg_overperformance"] = (
            result["goals"] - result["xg"]
        )
    return result


def _sort_player_matches(
    player_matches: pd.DataFrame,
) -> pd.DataFrame:
    """Sort player matches by game key for chronological order.

    Args:
        player_matches: Player matches DataFrame.

    Returns:
        Sorted DataFrame.
    """
    return player_matches.sort_values("game").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Team-match aggregation
# ---------------------------------------------------------------------------

def _aggregate_team_match_features(
    match_df: pd.DataFrame,
    rolled_players: pd.DataFrame,
    windows: list[int],
) -> pd.DataFrame:
    """Aggregate player rolling stats to team-match level.

    For each match, finds active players (minutes > 0) and
    aggregates their rolling stats. Adds top scorer/creator features.

    Args:
        match_df: Match-level DataFrame.
        rolled_players: Player matches with rolling columns.
        windows: Window sizes used.

    Returns:
        Match DataFrame with team-level player features.
    """
    result = match_df.copy()
    active_players = _filter_active_players(rolled_players)

    for window in windows:
        result = _aggregate_for_window(
            result, active_players, rolled_players, window,
        )
    return result


def _filter_active_players(
    rolled_players: pd.DataFrame,
) -> pd.DataFrame:
    """Filter to players with minutes > 0.

    Args:
        rolled_players: Player matches with rolling columns.

    Returns:
        DataFrame with only active players.
    """
    if rolled_players.empty or "minutes" not in rolled_players.columns:
        return rolled_players
    return rolled_players[rolled_players["minutes"] > 0].copy()


def _aggregate_for_window(
    match_df: pd.DataFrame,
    active_players: pd.DataFrame,
    all_players: pd.DataFrame,
    window: int,
) -> pd.DataFrame:
    """Aggregate team features for a single window size.

    Args:
        match_df: Match DataFrame to add features to.
        active_players: Active (minutes > 0) player matches.
        all_players: All player matches (for top scorer lookup).
        window: Window size.

    Returns:
        Match DataFrame with features for this window.
    """
    result = match_df.copy()
    result = _add_sum_features(result, active_players, window)
    result = _add_top_player_features(
        result, active_players, all_players, window,
    )
    return result


def _add_sum_features(
    match_df: pd.DataFrame,
    active_players: pd.DataFrame,
    window: int,
) -> pd.DataFrame:
    """Add SUM aggregation features for both home and away teams.

    Args:
        match_df: Match DataFrame.
        active_players: Active player matches with rolling columns.
        window: Window size.

    Returns:
        Match DataFrame with sum features added.
    """
    result = match_df.copy()
    for venue in ["home", "away"]:
        result = _add_venue_sum_features(
            result, active_players, window, venue,
        )
    return result


def _add_venue_sum_features(
    match_df: pd.DataFrame,
    active_players: pd.DataFrame,
    window: int,
    venue: str,
) -> pd.DataFrame:
    """Add SUM features for one venue (home or away).

    Args:
        match_df: Match DataFrame.
        active_players: Active player matches.
        window: Window size.
        venue: "home" or "away".

    Returns:
        Match DataFrame with venue-specific sum features.
    """
    team_col = f"{venue}_team"
    game_team_agg = _compute_game_team_sums(
        active_players, window,
    )

    for player_col, feature_name in _SUM_AGGREGATIONS.items():
        rolling_col = f"{player_col}_{window}"
        target_col = f"{venue}_{feature_name}_{window}"
        match_df[target_col] = _lookup_team_stat(
            match_df, game_team_agg, team_col, rolling_col,
        )
    return match_df


def _compute_game_team_sums(
    active_players: pd.DataFrame,
    window: int,
) -> pd.DataFrame:
    """Compute sum of rolling stats per game per team.

    Args:
        active_players: Active player matches with rolling columns.
        window: Window size.

    Returns:
        DataFrame with game, team, and summed rolling columns.
    """
    rolling_cols = [
        f"{col}_{window}" for col in _SUM_AGGREGATIONS
    ]
    available_cols = [
        c for c in rolling_cols if c in active_players.columns
    ]
    if not available_cols:
        return pd.DataFrame(columns=["game", "team"])

    return active_players.groupby(
        ["game", "team"], as_index=False,
    )[available_cols].sum(min_count=1)


def _lookup_team_stat(
    match_df: pd.DataFrame,
    game_team_agg: pd.DataFrame,
    team_col: str,
    rolling_col: str,
) -> pd.Series:
    """Look up aggregated stat for each match-team pair.

    Args:
        match_df: Match DataFrame.
        game_team_agg: Aggregated stats per game-team.
        team_col: Column name for the team (home_team/away_team).
        rolling_col: Rolling column to look up.

    Returns:
        Series of stat values aligned to match_df index.
    """
    if rolling_col not in game_team_agg.columns:
        return pd.Series(
            pd.NA, index=match_df.index, dtype=float,
        )

    merged = match_df[["game", team_col]].merge(
        game_team_agg[["game", "team", rolling_col]],
        left_on=["game", team_col],
        right_on=["game", "team"],
        how="left",
    )
    return pd.Series(merged[rolling_col].values)


def _add_top_player_features(
    match_df: pd.DataFrame,
    active_players: pd.DataFrame,
    all_players: pd.DataFrame,
    window: int,
) -> pd.DataFrame:
    """Add top scorer and top creator features (vectorized).

    Uses cumulative sums + idxmax to identify top players per
    game-team, then merges their rolling values in bulk.

    Args:
        match_df: Match DataFrame.
        active_players: Active player matches.
        all_players: All player matches (for cumulative stats).
        window: Window size.

    Returns:
        Match DataFrame with top player features.
    """
    top_map = _build_top_player_map(all_players)
    rolling_lookup = _build_rolling_lookup(active_players, window)

    result = match_df.copy()
    for venue in ["home", "away"]:
        result = _merge_top_features(
            result, top_map, rolling_lookup, window, venue,
        )
    return result


def _build_top_player_map(
    all_players: pd.DataFrame,
) -> pd.DataFrame:
    """Build a map of top scorer/creator per (game, team).

    Computes cumulative goals/assists per player within each
    team-season, shifted by 1 to exclude current game. Then
    picks the player with max cumulative stat per game-team.

    Args:
        all_players: All player matches sorted by game.

    Returns:
        DataFrame with columns: game, team, top_scorer, top_creator.
    """
    group_keys = ["team", "season", "player"]
    sorted_pm = all_players.sort_values("game")

    sorted_pm = sorted_pm.assign(
        cum_goals=sorted_pm.groupby(group_keys)["goals"]
        .cumsum()
        .groupby(sorted_pm.groupby(group_keys).ngroup())
        .shift(1),
        cum_assists=sorted_pm.groupby(group_keys)["assists"]
        .cumsum()
        .groupby(sorted_pm.groupby(group_keys).ngroup())
        .shift(1),
    )

    scorer_idx = (
        sorted_pm.groupby(["game", "team"])["cum_goals"]
        .idxmax()
        .dropna()
    )
    creator_idx = (
        sorted_pm.groupby(["game", "team"])["cum_assists"]
        .idxmax()
        .dropna()
    )

    scorer_map = sorted_pm.loc[
        scorer_idx, ["game", "team", "player"],
    ].rename(columns={"player": "top_scorer"})
    creator_map = sorted_pm.loc[
        creator_idx, ["game", "team", "player"],
    ].rename(columns={"player": "top_creator"})

    return scorer_map.merge(
        creator_map, on=["game", "team"], how="outer",
    )


def _build_rolling_lookup(
    active_players: pd.DataFrame,
    window: int,
) -> pd.DataFrame:
    """Build lookup table: (game, player) -> rolling values.

    Args:
        active_players: Active player matches with rolling columns.
        window: Window size.

    Returns:
        DataFrame indexed by (game, player) with rolling cols.
    """
    goals_col = f"goals_rolling_{window}"
    xa_col = f"xa_rolling_{window}"
    cols = ["game", "player"]
    if goals_col in active_players.columns:
        cols.append(goals_col)
    if xa_col in active_players.columns:
        cols.append(xa_col)
    return active_players[cols].drop_duplicates(
        subset=["game", "player"], keep="first",
    )


def _merge_top_features(
    match_df: pd.DataFrame,
    top_map: pd.DataFrame,
    rolling_lookup: pd.DataFrame,
    window: int,
    venue: str,
) -> pd.DataFrame:
    """Merge top scorer/creator rolling values for one venue.

    Args:
        match_df: Match DataFrame.
        top_map: Top player map (game, team -> top_scorer/creator).
        rolling_lookup: Rolling values per (game, player).
        window: Window size.
        venue: "home" or "away".

    Returns:
        Match DataFrame with top player features added.
    """
    team_col = f"{venue}_team"
    scorer_out = f"{venue}_top_scorer_goals_form_{window}"
    creator_out = f"{venue}_top_creator_xa_form_{window}"
    goals_col = f"goals_rolling_{window}"
    xa_col = f"xa_rolling_{window}"

    merged = match_df[["game", team_col]].merge(
        top_map, left_on=["game", team_col],
        right_on=["game", "team"], how="left",
    )

    scorer_vals = merged[["game", "top_scorer"]].merge(
        rolling_lookup[["game", "player", goals_col]]
        if goals_col in rolling_lookup.columns
        else pd.DataFrame(columns=["game", "player", goals_col]),
        left_on=["game", "top_scorer"],
        right_on=["game", "player"], how="left",
    )
    match_df[scorer_out] = scorer_vals[goals_col].values

    creator_vals = merged[["game", "top_creator"]].merge(
        rolling_lookup[["game", "player", xa_col]]
        if xa_col in rolling_lookup.columns
        else pd.DataFrame(columns=["game", "player", xa_col]),
        left_on=["game", "top_creator"],
        right_on=["game", "player"], how="left",
    )
    match_df[creator_out] = creator_vals[xa_col].values

    return match_df


# ---------------------------------------------------------------------------
# Empty feature column helper
# ---------------------------------------------------------------------------

def _add_empty_feature_columns(
    match_df: pd.DataFrame,
    windows: list[int],
) -> pd.DataFrame:
    """Add NaN-filled feature columns when no player data exists.

    Args:
        match_df: Match DataFrame.
        windows: Window sizes.

    Returns:
        Match DataFrame with NaN feature columns.
    """
    result = match_df.copy()
    for window in windows:
        for venue in ["home", "away"]:
            for feature_name in _SUM_AGGREGATIONS.values():
                col = f"{venue}_{feature_name}_{window}"
                result[col] = float("nan")
            result[f"{venue}_top_scorer_goals_form_{window}"] = (
                float("nan")
            )
            result[f"{venue}_top_creator_xa_form_{window}"] = (
                float("nan")
            )
    return result
