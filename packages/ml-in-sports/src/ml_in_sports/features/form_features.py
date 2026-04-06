"""Form streaks and advanced match features for prediction.

Computes per-team rolling streaks (win, unbeaten, losing, draw,
scoring, clean sheet), timing-based goal features from shots,
discipline and xG chain features from player_matches, and corner
rolling features from matches. All use shift(1) to prevent
lookahead bias. Grouped by (team, season) with season resets.
"""

import pandas as pd
import structlog

from ml_in_sports.utils.database import FootballDatabase

logger = structlog.get_logger(__name__)

_DEFAULT_WINDOWS: list[int] = [3, 5, 10]


# -------------------------------------------------------------------
# Streak histories: build per-team match history with result flags
# -------------------------------------------------------------------


def _build_streak_histories(df: pd.DataFrame) -> pd.DataFrame:
    """Build per-team match history with win/loss/draw flags.

    Each match creates two rows (home and away perspective).

    Args:
        df: Match DataFrame with home/away goals.

    Returns:
        DataFrame with one row per team per match, sorted by date.
    """
    if df.empty:
        return pd.DataFrame()

    home = _extract_home_result_flags(df)
    away = _extract_away_result_flags(df)
    combined = pd.concat([home, away], ignore_index=True)
    return combined.sort_values("date").reset_index(drop=True)


def _extract_home_result_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Extract result flags from the home team perspective.

    Args:
        df: Match DataFrame.

    Returns:
        DataFrame with result flags for home teams.
    """
    return pd.DataFrame({
        "match_idx": df.index,
        "game": df["game"].values,
        "date": df["date"].values,
        "season": df["season"].values,
        "team": df["home_team"].values,
        "venue": "home",
        "won": (df["home_goals"] > df["away_goals"]).astype(int).values,
        "drawn": (df["home_goals"] == df["away_goals"]).astype(int).values,
        "lost": (df["home_goals"] < df["away_goals"]).astype(int).values,
        "scored": (df["home_goals"] > 0).astype(int).values,
        "clean_sheet": (df["away_goals"] == 0).astype(int).values,
    })


def _extract_away_result_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Extract result flags from the away team perspective.

    Args:
        df: Match DataFrame.

    Returns:
        DataFrame with result flags for away teams.
    """
    return pd.DataFrame({
        "match_idx": df.index,
        "game": df["game"].values,
        "date": df["date"].values,
        "season": df["season"].values,
        "team": df["away_team"].values,
        "venue": "away",
        "won": (df["away_goals"] > df["home_goals"]).astype(int).values,
        "drawn": (df["home_goals"] == df["away_goals"]).astype(int).values,
        "lost": (df["away_goals"] < df["home_goals"]).astype(int).values,
        "scored": (df["away_goals"] > 0).astype(int).values,
        "clean_sheet": (df["home_goals"] == 0).astype(int).values,
    })


# -------------------------------------------------------------------
# Streak computation: consecutive runs per team-season
# -------------------------------------------------------------------


def _compute_all_streaks(histories: pd.DataFrame) -> pd.DataFrame:
    """Compute all streak features per team-season group.

    Uses shift(1) so streaks reflect history before each match.

    Args:
        histories: Per-team match history with result flags.

    Returns:
        DataFrame with streak columns added.
    """
    if histories.empty:
        return pd.DataFrame()

    frames: list[pd.DataFrame] = []
    for (_team, _season), group in histories.groupby(["team", "season"]):
        streaked = _compute_group_streaks(group)
        frames.append(streaked)

    return pd.concat(frames, ignore_index=True)


def _compute_group_streaks(group: pd.DataFrame) -> pd.DataFrame:
    """Compute streak features for one team-season group.

    Args:
        group: Chronologically sorted match history for one team.

    Returns:
        DataFrame with streak columns.
    """
    sorted_group = group.sort_values("date").copy()
    sorted_group["win_streak"] = _streak_of(sorted_group["won"])
    sorted_group["losing_streak"] = _streak_of(sorted_group["lost"])
    sorted_group["draw_streak"] = _streak_of(sorted_group["drawn"])
    sorted_group["scoring_streak"] = _streak_of(sorted_group["scored"])
    sorted_group["clean_sheet_streak"] = _streak_of(
        sorted_group["clean_sheet"],
    )
    sorted_group["unbeaten_streak"] = _streak_of(
        1 - sorted_group["lost"],
    )
    return sorted_group


def _streak_of(series: pd.Series) -> pd.Series:
    """Compute consecutive-run length of 1s, shifted by 1.

    For each row, returns the number of consecutive 1s
    in the rows before it. Uses shift(1) to avoid lookahead.

    Args:
        series: Binary (0/1) Series.

    Returns:
        Series of streak lengths (NaN for first row).
    """
    cumsum = series.cumsum()
    reset_points = series.eq(0)
    reset_cumsum = cumsum.where(reset_points).ffill().fillna(0)
    running_streak = cumsum - reset_cumsum
    return running_streak.shift(1)


# -------------------------------------------------------------------
# Timing-based goal features from shots table
# -------------------------------------------------------------------


def _compute_timing_goals(
    shots: pd.DataFrame,
    windows: list[int],
) -> pd.DataFrame:
    """Compute timing-based goal features from shots data.

    Aggregates goals per team per game by time period (first/last
    15 minutes), then applies rolling mean with shift(1).

    Args:
        shots: Shots DataFrame with minute column.
        windows: Rolling window sizes.

    Returns:
        Per-team per-game DataFrame with timing rolling columns.
    """
    if shots.empty:
        return pd.DataFrame()

    per_game = _aggregate_timing_per_game(shots)
    return _roll_timing_features(per_game, windows)


def _aggregate_timing_per_game(shots: pd.DataFrame) -> pd.DataFrame:
    """Aggregate goals by time period per team per game.

    Args:
        shots: Shots DataFrame with minute, result, team, game.

    Returns:
        DataFrame with goals_first_15min, goals_last_15min columns.
    """
    is_goal = shots["result"] == "Goal"
    goals_only = shots[is_goal].copy()

    grouped = goals_only.groupby(
        ["league", "season", "game", "team"],
    )

    records: list[dict[str, object]] = []
    for _keys, group in grouped:
        records.append({
            "league": group["league"].iloc[0],
            "season": group["season"].iloc[0],
            "game": group["game"].iloc[0],
            "team": group["team"].iloc[0],
            "date": group["date"].iloc[0],
            "goals_first_15min": (group["minute"] <= 15).sum(),
            "goals_last_15min": (group["minute"] >= 76).sum(),
        })

    if not records:
        return pd.DataFrame()

    return pd.DataFrame(records)


def _roll_timing_features(
    per_game: pd.DataFrame,
    windows: list[int],
) -> pd.DataFrame:
    """Apply rolling to timing goal aggregates per team-season.

    Args:
        per_game: Per-team per-game timing stats.
        windows: Rolling window sizes.

    Returns:
        DataFrame with rolling timing columns.
    """
    if per_game.empty:
        return pd.DataFrame()

    frames: list[pd.DataFrame] = []
    stats = ["goals_first_15min", "goals_last_15min"]

    for (_team, _season), group in per_game.groupby(["team", "season"]):
        rolled = _roll_stats_for_group(group, stats, windows)
        frames.append(rolled)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _roll_stats_for_group(
    group: pd.DataFrame,
    stat_names: list[str],
    windows: list[int],
) -> pd.DataFrame:
    """Apply rolling mean with shift(1) to stats in one group.

    Args:
        group: Single team-season sorted by date.
        stat_names: Column names to roll.
        windows: Window sizes.

    Returns:
        DataFrame with game, team, date, and rolling columns.
    """
    sorted_group = group.sort_values("date")
    result = sorted_group[
        ["league", "season", "game", "team", "date"]
    ].copy()

    for stat in stat_names:
        if stat not in sorted_group.columns:
            continue
        result[stat] = sorted_group[stat].values
        shifted = sorted_group[stat].shift(1)
        for window in windows:
            col = f"{stat}_rolling_{window}"
            result[col] = shifted.rolling(
                window=window, min_periods=window,
            ).mean().values

    return result


# -------------------------------------------------------------------
# Discipline features from player_matches
# -------------------------------------------------------------------


def _compute_discipline_rolling(
    player_matches: pd.DataFrame,
    windows: list[int],
) -> pd.DataFrame:
    """Compute discipline rolling features from player_matches.

    Aggregates yellow/red cards and fouls per team per game,
    then applies rolling mean with shift(1).

    Args:
        player_matches: Player-match level data.
        windows: Rolling window sizes.

    Returns:
        Per-team per-game DataFrame with discipline rolling columns.
    """
    if player_matches.empty:
        return pd.DataFrame()

    per_game = _aggregate_discipline_per_game(player_matches)
    return _roll_discipline_features(per_game, windows)


def _aggregate_discipline_per_game(
    player_matches: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate discipline stats per team per game.

    Args:
        player_matches: Player-match level data.

    Returns:
        DataFrame with team total yellow/red cards per game.
    """
    agg_dict: dict[str, tuple[str, str]] = {
        "yellow_cards_total": ("yellow_cards", "sum"),
        "red_cards_total": ("red_cards", "sum"),
    }
    if "fouls_committed" in player_matches.columns:
        agg_dict["fouls_total"] = ("fouls_committed", "sum")

    grouped = player_matches.groupby(
        ["league", "season", "game", "team"], as_index=False,
    ).agg(**agg_dict)

    _add_date_from_player_matches(grouped, player_matches)
    return grouped


def _add_date_from_player_matches(
    grouped: pd.DataFrame,
    player_matches: pd.DataFrame,
) -> None:
    """Add date column to grouped discipline data.

    Uses game name ordering as proxy if date is not available.

    Args:
        grouped: Aggregated discipline DataFrame (mutated).
        player_matches: Source player_matches DataFrame.
    """
    if "date" in player_matches.columns:
        date_map = player_matches[
            ["game", "date"]
        ].drop_duplicates()
        grouped_with_date = grouped.merge(
            date_map, on="game", how="left",
        )
        grouped["date"] = grouped_with_date["date"]
    else:
        grouped["date"] = grouped["game"]


def _roll_discipline_features(
    per_game: pd.DataFrame,
    windows: list[int],
) -> pd.DataFrame:
    """Apply rolling to discipline stats per team-season.

    Args:
        per_game: Per-team per-game discipline stats.
        windows: Rolling window sizes.

    Returns:
        DataFrame with rolling discipline columns.
    """
    if per_game.empty:
        return pd.DataFrame()

    stats = ["yellow_cards_total", "red_cards_total"]
    if "fouls_total" in per_game.columns:
        stats.append("fouls_total")

    rename_map = {
        "yellow_cards_total": "yellow_cards",
        "red_cards_total": "red_cards",
        "fouls_total": "fouls",
    }

    frames: list[pd.DataFrame] = []
    for (_team, _season), group in per_game.groupby(["team", "season"]):
        rolled = _roll_stats_for_group(group, stats, windows)
        frames.append(rolled)

    if not frames:
        return pd.DataFrame()

    result = pd.concat(frames, ignore_index=True)
    return _rename_rolling_columns(result, rename_map)


def _rename_rolling_columns(
    df: pd.DataFrame,
    rename_map: dict[str, str],
) -> pd.DataFrame:
    """Rename rolling columns from source to target names.

    Args:
        df: DataFrame with rolling columns.
        rename_map: Mapping from source base name to target base.

    Returns:
        DataFrame with renamed columns.
    """
    col_renames: dict[str, str] = {}
    for old_base, new_base in rename_map.items():
        for col in df.columns:
            if col.startswith(f"{old_base}_rolling_"):
                suffix = col[len(f"{old_base}_rolling_"):]
                col_renames[col] = f"{new_base}_rolling_{suffix}"
    return df.rename(columns=col_renames)


# -------------------------------------------------------------------
# xG chain and buildup features from player_matches
# -------------------------------------------------------------------


def _compute_xg_chain_rolling(
    player_matches: pd.DataFrame,
    windows: list[int],
) -> pd.DataFrame:
    """Compute xG chain/buildup rolling features.

    Aggregates xg_chain and xg_buildup per team per game,
    then applies rolling mean with shift(1).

    Args:
        player_matches: Player-match level data.
        windows: Rolling window sizes.

    Returns:
        Per-team per-game DataFrame with xG chain rolling columns.
    """
    if player_matches.empty:
        return pd.DataFrame()

    per_game = _aggregate_xg_chain_per_game(player_matches)
    return _roll_xg_chain_features(per_game, windows)


def _aggregate_xg_chain_per_game(
    player_matches: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate xG chain/buildup per team per game.

    Args:
        player_matches: Player-match level data.

    Returns:
        DataFrame with team total xg_chain and xg_buildup per game.
    """
    agg_dict: dict[str, tuple[str, str]] = {}
    if "xg_chain" in player_matches.columns:
        agg_dict["xg_chain_total"] = ("xg_chain", "sum")
    if "xg_buildup" in player_matches.columns:
        agg_dict["xg_buildup_total"] = ("xg_buildup", "sum")

    if not agg_dict:
        return pd.DataFrame()

    grouped = player_matches.groupby(
        ["league", "season", "game", "team"], as_index=False,
    ).agg(**agg_dict)

    _add_date_from_player_matches(grouped, player_matches)
    return grouped


def _roll_xg_chain_features(
    per_game: pd.DataFrame,
    windows: list[int],
) -> pd.DataFrame:
    """Apply rolling to xG chain stats per team-season.

    Args:
        per_game: Per-team per-game xG chain stats.
        windows: Rolling window sizes.

    Returns:
        DataFrame with rolling xG chain columns.
    """
    if per_game.empty:
        return pd.DataFrame()

    stats: list[str] = []
    rename_map: dict[str, str] = {}
    if "xg_chain_total" in per_game.columns:
        stats.append("xg_chain_total")
        rename_map["xg_chain_total"] = "xg_chain"
    if "xg_buildup_total" in per_game.columns:
        stats.append("xg_buildup_total")
        rename_map["xg_buildup_total"] = "xg_buildup"

    frames: list[pd.DataFrame] = []
    for (_team, _season), group in per_game.groupby(["team", "season"]):
        rolled = _roll_stats_for_group(group, stats, windows)
        frames.append(rolled)

    if not frames:
        return pd.DataFrame()

    result = pd.concat(frames, ignore_index=True)
    return _rename_rolling_columns(result, rename_map)


# -------------------------------------------------------------------
# Corners rolling features from matches table
# -------------------------------------------------------------------


def _compute_corners_rolling(
    matches: pd.DataFrame,
    windows: list[int],
) -> pd.DataFrame:
    """Compute corners won/conceded rolling features.

    Extracts per-team corner stats from the matches table,
    then applies rolling mean with shift(1).

    Args:
        matches: Match-level DataFrame with corner columns.
        windows: Rolling window sizes.

    Returns:
        Per-team per-game DataFrame with corner rolling columns.
    """
    if matches.empty:
        return pd.DataFrame()

    required = {"home_won_corners", "away_won_corners"}
    if not required.issubset(set(matches.columns)):
        logger.warning("Corner columns not found, skipping")
        return pd.DataFrame()

    per_team = _extract_corner_per_team(matches)
    return _roll_corner_features(per_team, windows)


def _extract_corner_per_team(matches: pd.DataFrame) -> pd.DataFrame:
    """Extract per-team corner data (two rows per match).

    Args:
        matches: Match DataFrame with corner columns.

    Returns:
        DataFrame with team, corners_won, opponent_corners.
    """
    home = pd.DataFrame({
        "league": matches["league"],
        "season": matches["season"],
        "game": matches["game"],
        "date": matches["date"],
        "team": matches["home_team"],
        "corners_won": matches["home_won_corners"],
        "opponent_corners": matches["away_won_corners"],
    })
    away = pd.DataFrame({
        "league": matches["league"],
        "season": matches["season"],
        "game": matches["game"],
        "date": matches["date"],
        "team": matches["away_team"],
        "corners_won": matches["away_won_corners"],
        "opponent_corners": matches["home_won_corners"],
    })
    return pd.concat([home, away], ignore_index=True)


def _roll_corner_features(
    per_team: pd.DataFrame,
    windows: list[int],
) -> pd.DataFrame:
    """Apply rolling to corner stats per team-season.

    Args:
        per_team: Per-team per-game corner stats.
        windows: Rolling window sizes.

    Returns:
        DataFrame with rolling corner columns.
    """
    stats = ["corners_won", "opponent_corners"]
    frames: list[pd.DataFrame] = []

    for (_team, _season), group in per_team.groupby(["team", "season"]):
        rolled = _roll_stats_for_group(group, stats, windows)
        frames.append(rolled)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


# -------------------------------------------------------------------
# Opponent timing features (goals conceded in time periods)
# -------------------------------------------------------------------


def _add_opponent_timing(
    timing: pd.DataFrame,
    matches: pd.DataFrame,
) -> pd.DataFrame:
    """Add opponent timing goals to timing DataFrame.

    For each team-game, looks up the opponent's goals in the
    same time period as "goals conceded".

    Args:
        timing: Per-team timing goal features.
        matches: Match DataFrame for opponent lookup.

    Returns:
        Timing DataFrame with conceded columns added.
    """
    if timing.empty or matches.empty:
        return timing

    opponent_map = _build_opponent_lookup(matches)
    return _merge_opponent_timing(timing, opponent_map)


def _build_opponent_lookup(matches: pd.DataFrame) -> pd.DataFrame:
    """Build a (game, team) -> opponent mapping.

    Args:
        matches: Match DataFrame.

    Returns:
        DataFrame with game, team, opponent columns.
    """
    home = pd.DataFrame({
        "game": matches["game"],
        "team": matches["home_team"],
        "opponent": matches["away_team"],
    })
    away = pd.DataFrame({
        "game": matches["game"],
        "team": matches["away_team"],
        "opponent": matches["home_team"],
    })
    return pd.concat([home, away], ignore_index=True)


def _merge_opponent_timing(
    timing: pd.DataFrame,
    opponent_map: pd.DataFrame,
) -> pd.DataFrame:
    """Merge opponent's timing goals as conceded columns.

    Args:
        timing: Per-team timing stats.
        opponent_map: Game-team-opponent mapping.

    Returns:
        DataFrame with conceded timing columns.
    """
    merged = timing.merge(opponent_map, on=["game", "team"], how="left")
    opp_timing = timing[
        ["game", "team", "goals_first_15min", "goals_last_15min"]
    ].rename(columns={
        "team": "opponent",
        "goals_first_15min": "goals_conceded_first_15min",
        "goals_last_15min": "goals_conceded_last_15min",
    })
    result = merged.merge(opp_timing, on=["game", "opponent"], how="left")
    result = result.drop(columns=["opponent"], errors="ignore")
    return result


# -------------------------------------------------------------------
# Join per-team features to match rows (home/away prefix)
# -------------------------------------------------------------------


def _join_team_features_to_matches(
    match_df: pd.DataFrame,
    team_features: pd.DataFrame,
    feature_cols: list[str],
) -> pd.DataFrame:
    """Join per-team features to match rows with home/away prefix.

    Args:
        match_df: Match-level DataFrame.
        team_features: Per-team per-game features.
        feature_cols: Column names to join.

    Returns:
        Match DataFrame with home_* and away_* feature columns.
    """
    if team_features.empty:
        return match_df.copy()

    result = match_df.copy()
    result = _join_one_side(result, team_features, feature_cols, "home")
    result = _join_one_side(result, team_features, feature_cols, "away")
    return result


def _join_one_side(
    df: pd.DataFrame,
    features: pd.DataFrame,
    feature_cols: list[str],
    side: str,
) -> pd.DataFrame:
    """Join features for one side (home or away).

    Args:
        df: Match DataFrame.
        features: Per-team features with game and team columns.
        feature_cols: Columns to join.
        side: "home" or "away".

    Returns:
        DataFrame with side-prefixed feature columns.
    """
    available = [c for c in feature_cols if c in features.columns]
    if not available:
        return df

    subset = features[["game", "team", *available]].copy()
    rename = {col: f"{side}_{col}" for col in available}
    rename["team"] = f"{side}_team"
    subset = subset.rename(columns=rename)

    return df.merge(
        subset, on=["game", f"{side}_team"], how="left",
    )


# -------------------------------------------------------------------
# Orchestrator
# -------------------------------------------------------------------


def add_form_features(
    df: pd.DataFrame,
    db: FootballDatabase,
    windows: list[int] | None = None,
    shots_df: pd.DataFrame | None = None,
    player_matches_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Add form streaks and advanced match features.

    Computes streaks, timing-based goals, discipline,
    xG chain, and corner rolling features. Joins everything
    back to the match DataFrame with home/away prefixes.

    Args:
        df: Match-level DataFrame.
        db: FootballDatabase for loading shots/player_matches.
        windows: Rolling window sizes (default: [3, 5, 10]).
        shots_df: Pre-loaded shots DataFrame (skips DB load).
        player_matches_df: Pre-loaded player_matches (skips DB load).

    Returns:
        DataFrame with all form feature columns added.
    """
    if df.empty:
        return df.copy()

    if windows is None:
        windows = _DEFAULT_WINDOWS

    result = df.copy()
    result = _add_streak_features(result)
    result = _add_timing_features(result, db, windows, shots_df=shots_df)
    result = _add_discipline_features(
        result, db, windows, player_matches_df=player_matches_df,
    )
    result = _add_xg_chain_features(
        result, db, windows, player_matches_df=player_matches_df,
    )
    result = _add_corner_features(result, windows)

    new_cols = len(result.columns) - len(df.columns)
    logger.info("Added %d form feature columns", new_cols)
    return result


def _add_streak_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add streak features to match DataFrame.

    Args:
        df: Match DataFrame.

    Returns:
        DataFrame with streak columns added.
    """
    histories = _build_streak_histories(df)
    if histories.empty:
        return df

    streaked = _compute_all_streaks(histories)
    streak_cols = [
        "win_streak", "unbeaten_streak", "losing_streak",
        "draw_streak", "scoring_streak", "clean_sheet_streak",
    ]
    return _join_team_features_to_matches(df, streaked, streak_cols)


def _add_timing_features(
    df: pd.DataFrame,
    db: FootballDatabase,
    windows: list[int],
    shots_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Add timing-based goal features from shots table.

    Args:
        df: Match DataFrame.
        db: FootballDatabase instance.
        windows: Rolling window sizes.
        shots_df: Pre-loaded shots DataFrame (skips DB load).

    Returns:
        DataFrame with timing features added.
    """
    try:
        shots = shots_df if shots_df is not None else db.read_table("shots")
    except Exception as exc:
        logger.warning("Could not load shots: %s", exc)
        return df

    if shots.empty:
        return df

    timing = _compute_timing_goals(shots, windows)
    if timing.empty:
        return df

    timing = _add_opponent_timing(timing, df)
    rolling_cols = [c for c in timing.columns if "rolling" in c]
    return _join_team_features_to_matches(df, timing, rolling_cols)


def _add_discipline_features(
    df: pd.DataFrame,
    db: FootballDatabase,
    windows: list[int],
    player_matches_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Add discipline rolling features from player_matches.

    Args:
        df: Match DataFrame.
        db: FootballDatabase instance.
        windows: Rolling window sizes.
        player_matches_df: Pre-loaded player_matches (skips DB load).

    Returns:
        DataFrame with discipline features added.
    """
    try:
        player_matches = (
            player_matches_df if player_matches_df is not None
            else db.read_table("player_matches")
        )
    except Exception as exc:
        logger.warning("Could not load player_matches: %s", exc)
        return df

    if player_matches.empty:
        return df

    discipline = _compute_discipline_rolling(player_matches, windows)
    if discipline.empty:
        return df

    rolling_cols = [c for c in discipline.columns if "rolling" in c]
    return _join_team_features_to_matches(df, discipline, rolling_cols)


def _add_xg_chain_features(
    df: pd.DataFrame,
    db: FootballDatabase,
    windows: list[int],
    player_matches_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Add xG chain/buildup rolling features from player_matches.

    Args:
        df: Match DataFrame.
        db: FootballDatabase instance.
        windows: Rolling window sizes.
        player_matches_df: Pre-loaded player_matches (skips DB load).

    Returns:
        DataFrame with xG chain features added.
    """
    try:
        player_matches = (
            player_matches_df if player_matches_df is not None
            else db.read_table("player_matches")
        )
    except Exception as exc:
        logger.warning("Could not load player_matches: %s", exc)
        return df

    if player_matches.empty:
        return df

    xg_chain = _compute_xg_chain_rolling(player_matches, windows)
    if xg_chain.empty:
        return df

    rolling_cols = [c for c in xg_chain.columns if "rolling" in c]
    return _join_team_features_to_matches(df, xg_chain, rolling_cols)


def _add_corner_features(
    df: pd.DataFrame,
    windows: list[int],
) -> pd.DataFrame:
    """Add corner rolling features from the match DataFrame.

    Args:
        df: Match DataFrame (may contain corner columns).
        windows: Rolling window sizes.

    Returns:
        DataFrame with corner features added.
    """
    corners = _compute_corners_rolling(df, windows)
    if corners.empty:
        return df

    rolling_cols = [c for c in corners.columns if "rolling" in c]
    return _join_team_features_to_matches(df, corners, rolling_cols)
