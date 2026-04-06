"""Set-piece effectiveness features for match prediction.

Computes per-team rolling and season-to-date set-piece metrics
from the shots and matches tables. Covers corners, free kicks,
open play, and overall set-piece dependency ratios.
"""

import numpy as np
import pandas as pd
import structlog

from ml_in_sports.utils.database import FootballDatabase

logger = structlog.get_logger(__name__)

_DEFAULT_WINDOWS: list[int] = [3, 5, 10]

_SITUATION_CORNER = "From Corner"
_SITUATION_FREEKICK = "Direct Freekick"
_SITUATION_SETPIECE = "Set Piece"
_SITUATION_OPEN_PLAY = "Open Play"

_RESULT_GOAL = "Goal"


# ---------------------------------------------------------------------------
# Shot-level aggregation per team per game
# ---------------------------------------------------------------------------

def _load_shots(db: FootballDatabase) -> pd.DataFrame:
    """Load all shots from the database.

    Args:
        db: FootballDatabase instance.

    Returns:
        DataFrame with shot-level data.
    """
    return db.read_table("shots")


def _load_matches(db: FootballDatabase) -> pd.DataFrame:
    """Load all matches from the database.

    Args:
        db: FootballDatabase instance.

    Returns:
        DataFrame with match-level data.
    """
    return db.read_table("matches")


def _is_setpiece_situation(situation: str) -> bool:
    """Check if a shot situation is a set piece.

    Args:
        situation: Shot situation string.

    Returns:
        True if the shot came from a corner, free kick, or set piece.
    """
    return situation in {
        _SITUATION_CORNER, _SITUATION_FREEKICK, _SITUATION_SETPIECE,
    }


def _build_team_shot_stats(shots: pd.DataFrame) -> pd.DataFrame:
    """Aggregate shot data per team per game.

    Computes goals, shot counts, and xG totals broken down by
    situation type (corner, free kick, set piece, open play).

    Args:
        shots: Raw shots DataFrame with team, game, situation,
               result, xG columns.

    Returns:
        DataFrame with one row per team per game with shot stats.
    """
    if shots.empty:
        return pd.DataFrame()

    records: list[dict[str, object]] = []
    grouped = shots.groupby(["league", "season", "game", "team"])
    for _keys, group in grouped:
        records.append(_aggregate_shot_group(group).to_dict())  # type: ignore[arg-type]  # Series.to_dict returns dict[Hashable, Any]

    return pd.DataFrame(records)


def _aggregate_shot_group(group: pd.DataFrame) -> pd.Series:
    """Aggregate a single team-game shot group into summary stats.

    Args:
        group: Shot rows for one team in one game.

    Returns:
        Series with set-piece and open-play shot statistics.
    """
    is_goal = group["result"] == _RESULT_GOAL

    corner_shots = group["situation"] == _SITUATION_CORNER
    fk_shots = group["situation"] == _SITUATION_FREEKICK
    sp_shots = group["situation"].apply(_is_setpiece_situation)
    open_shots = group["situation"] == _SITUATION_OPEN_PLAY

    return pd.Series({
        "league": group["league"].iloc[0],
        "season": group["season"].iloc[0],
        "game": group["game"].iloc[0],
        "team": group["team"].iloc[0],
        "goals_from_corners": (corner_shots & is_goal).sum(),
        "shots_from_corners": corner_shots.sum(),
        "xg_from_corners": group.loc[corner_shots, "xg"].sum(),
        "goals_from_fk": (fk_shots & is_goal).sum(),
        "shots_from_fk": fk_shots.sum(),
        "xg_from_fk": group.loc[fk_shots, "xg"].sum(),
        "goals_from_setpieces": (sp_shots & is_goal).sum(),
        "shots_from_setpieces": sp_shots.sum(),
        "xg_from_setpieces": group.loc[sp_shots, "xg"].sum(),
        "goals_open_play": (open_shots & is_goal).sum(),
        "shots_open_play": open_shots.sum(),
        "xg_open_play": group.loc[open_shots, "xg"].sum(),
        "total_goals": is_goal.sum(),
        "total_shots": len(group),
    })


# ---------------------------------------------------------------------------
# Corner data from matches table
# ---------------------------------------------------------------------------

def _build_corner_stats(matches: pd.DataFrame) -> pd.DataFrame:
    """Extract per-team per-game corner counts from matches table.

    Produces two rows per match (home perspective and away perspective).

    Args:
        matches: Matches DataFrame with corner columns.

    Returns:
        DataFrame with team, game, corners_won, opponent_corners.
    """
    if matches.empty:
        return pd.DataFrame()

    required = {"home_won_corners", "away_won_corners"}
    if not required.issubset(set(matches.columns)):
        logger.warning("Corner columns not found in matches table")
        return pd.DataFrame()

    home = _extract_home_corners(matches)
    away = _extract_away_corners(matches)
    return pd.concat([home, away], ignore_index=True)


def _extract_home_corners(matches: pd.DataFrame) -> pd.DataFrame:
    """Extract corner stats from home team perspective.

    Args:
        matches: Matches DataFrame.

    Returns:
        DataFrame with home team corner data.
    """
    return pd.DataFrame({
        "league": matches["league"],
        "season": matches["season"],
        "game": matches["game"],
        "team": matches["home_team"],
        "corners_won": matches["home_won_corners"],
        "opponent_corners": matches["away_won_corners"],
    })


def _extract_away_corners(matches: pd.DataFrame) -> pd.DataFrame:
    """Extract corner stats from away team perspective.

    Args:
        matches: Matches DataFrame.

    Returns:
        DataFrame with away team corner data.
    """
    return pd.DataFrame({
        "league": matches["league"],
        "season": matches["season"],
        "game": matches["game"],
        "team": matches["away_team"],
        "corners_won": matches["away_won_corners"],
        "opponent_corners": matches["home_won_corners"],
    })


# ---------------------------------------------------------------------------
# Opponent shot stats (goals conceded from set pieces)
# ---------------------------------------------------------------------------

def _build_opponent_shot_stats(
    shots: pd.DataFrame,
    matches: pd.DataFrame,
) -> pd.DataFrame:
    """Compute goals conceded from set pieces per team per game.

    For each team in each game, looks at the opponent's goals
    from corners and set pieces.

    Args:
        shots: Raw shots DataFrame.
        matches: Matches DataFrame with home_team, away_team.

    Returns:
        DataFrame with team, game, goals_conceded_from_corners,
        goals_conceded_from_setpieces.
    """
    if shots.empty or matches.empty:
        return pd.DataFrame()

    team_shots = _build_team_shot_stats(shots)
    if team_shots.empty:
        return pd.DataFrame()

    opponent_map = _build_opponent_map(matches)
    merged = team_shots.merge(
        opponent_map,
        on=["league", "season", "game", "team"],
        how="inner",
    )

    return _compute_conceded_stats(merged)


def _build_opponent_map(matches: pd.DataFrame) -> pd.DataFrame:
    """Build a mapping from (game, team) to opponent.

    Args:
        matches: Matches DataFrame.

    Returns:
        DataFrame with game, team, opponent columns.
    """
    home = pd.DataFrame({
        "league": matches["league"],
        "season": matches["season"],
        "game": matches["game"],
        "opponent": matches["home_team"],
        "team": matches["away_team"],
    })
    away = pd.DataFrame({
        "league": matches["league"],
        "season": matches["season"],
        "game": matches["game"],
        "opponent": matches["away_team"],
        "team": matches["home_team"],
    })
    return pd.concat([home, away], ignore_index=True)


def _compute_conceded_stats(merged: pd.DataFrame) -> pd.DataFrame:
    """Compute conceded stats by looking at opponent's scoring data.

    Args:
        merged: Shot stats joined with opponent mapping.

    Returns:
        DataFrame with conceded stats per team per game.
    """
    opponent_goals = merged.rename(columns={
        "team": "scoring_team",
        "opponent": "team",
        "goals_from_corners": "goals_conceded_from_corners",
        "goals_from_setpieces": "goals_conceded_from_setpieces",
    })
    return opponent_goals[[
        "league", "season", "game", "team",
        "goals_conceded_from_corners",
        "goals_conceded_from_setpieces",
    ]].copy()


# ---------------------------------------------------------------------------
# Merge all per-team-game stats
# ---------------------------------------------------------------------------

def _merge_team_game_stats(
    shot_stats: pd.DataFrame,
    corner_stats: pd.DataFrame,
    conceded_stats: pd.DataFrame,
    matches: pd.DataFrame,
) -> pd.DataFrame:
    """Merge shot stats, corner stats, and conceded stats per team-game.

    Also adds a match count column and sorts by date for rolling.

    Args:
        shot_stats: Per-team shot aggregations.
        corner_stats: Per-team corner counts.
        conceded_stats: Per-team goals conceded from set pieces.
        matches: Matches DataFrame (for date sorting).

    Returns:
        Combined per-team per-game DataFrame sorted by date.
    """
    join_keys = ["league", "season", "game", "team"]

    result = shot_stats.copy()
    result["matches_played"] = 1

    if not corner_stats.empty:
        result = result.merge(corner_stats, on=join_keys, how="left")

    if not conceded_stats.empty:
        result = result.merge(conceded_stats, on=join_keys, how="left")

    result = _fill_missing_numeric_columns(result)

    date_map = matches[["game", "date"]].drop_duplicates()
    result = result.merge(date_map, on="game", how="left")
    result = result.sort_values("date").reset_index(drop=True)

    return result


def _fill_missing_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Fill NaN in numeric set-piece columns with 0.

    Args:
        df: DataFrame with potential NaN values.

    Returns:
        DataFrame with NaN filled.
    """
    fill_cols = [
        "corners_won", "opponent_corners",
        "goals_conceded_from_corners",
        "goals_conceded_from_setpieces",
    ]
    for col in fill_cols:
        if col in df.columns:
            df[col] = df[col].fillna(np.nan)
    return df


# ---------------------------------------------------------------------------
# Raw feature computation (per team-game row)
# ---------------------------------------------------------------------------

def _compute_raw_features(stats: pd.DataFrame) -> pd.DataFrame:
    """Compute raw set-piece features per team per game.

    Args:
        stats: Merged per-team per-game statistics.

    Returns:
        DataFrame with computed set-piece feature columns added.
    """
    result = stats.copy()
    result = _add_corner_effectiveness(result)
    result = _add_freekick_effectiveness(result)
    result = _add_setpiece_dependency(result)
    result = _add_open_play_efficiency(result)
    result = _add_defensive_vulnerability(result)
    result = _add_xg_per_situation(result)
    return result


def _safe_divide(
    numerator: pd.Series,
    denominator: pd.Series,
) -> pd.Series:
    """Divide two series, returning NaN where denominator is 0.

    Args:
        numerator: Numerator series.
        denominator: Denominator series.

    Returns:
        Result series with safe division.
    """
    return numerator / denominator.replace(0, float("nan"))


def _add_corner_effectiveness(df: pd.DataFrame) -> pd.DataFrame:
    """Add corner attack effectiveness and corner xG efficiency.

    Args:
        df: Per-team per-game stats DataFrame.

    Returns:
        DataFrame with corner effectiveness columns.
    """
    if "corners_won" in df.columns:
        df["corner_attack_effectiveness"] = _safe_divide(
            df["goals_from_corners"], df["corners_won"],
        )
        df["corner_xg_efficiency"] = _safe_divide(
            df["xg_from_corners"], df["corners_won"],
        )
    if "opponent_corners" in df.columns:
        df["corner_defense"] = _safe_divide(
            df["goals_conceded_from_corners"], df["opponent_corners"],
        )
    return df


def _add_freekick_effectiveness(df: pd.DataFrame) -> pd.DataFrame:
    """Add free kick effectiveness feature.

    Args:
        df: Per-team per-game stats DataFrame.

    Returns:
        DataFrame with free kick effectiveness column.
    """
    df["fk_effectiveness"] = _safe_divide(
        df["goals_from_fk"], df["shots_from_fk"],
    )
    return df


def _add_setpiece_dependency(df: pd.DataFrame) -> pd.DataFrame:
    """Add set-piece dependency ratio.

    Args:
        df: Per-team per-game stats DataFrame.

    Returns:
        DataFrame with set-piece dependency column.
    """
    df["setpiece_dependency"] = _safe_divide(
        df["goals_from_setpieces"], df["total_goals"],
    )
    return df


def _add_open_play_efficiency(df: pd.DataFrame) -> pd.DataFrame:
    """Add open play goal efficiency.

    Args:
        df: Per-team per-game stats DataFrame.

    Returns:
        DataFrame with open play efficiency column.
    """
    df["open_play_efficiency"] = _safe_divide(
        df["goals_open_play"], df["shots_open_play"],
    )
    return df


def _add_defensive_vulnerability(df: pd.DataFrame) -> pd.DataFrame:
    """Add set-piece defensive vulnerability (per match).

    Args:
        df: Per-team per-game stats DataFrame.

    Returns:
        DataFrame with defensive vulnerability column.
    """
    if "goals_conceded_from_setpieces" in df.columns:
        df["sp_defensive_vulnerability"] = (
            df["goals_conceded_from_setpieces"]
        )
    return df


def _add_xg_per_situation(df: pd.DataFrame) -> pd.DataFrame:
    """Add average xG per shot by situation type.

    Args:
        df: Per-team per-game stats DataFrame.

    Returns:
        DataFrame with xG per situation columns.
    """
    df["xg_per_corner_shot"] = _safe_divide(
        df["xg_from_corners"], df["shots_from_corners"],
    )
    df["xg_per_fk_shot"] = _safe_divide(
        df["xg_from_fk"], df["shots_from_fk"],
    )
    df["xg_per_open_play_shot"] = _safe_divide(
        df["xg_open_play"], df["shots_open_play"],
    )
    return df


# ---------------------------------------------------------------------------
# Rolling and season-to-date computation
# ---------------------------------------------------------------------------

_ROLLING_FEATURES: list[str] = [
    "corner_attack_effectiveness",
    "corner_defense",
    "corner_xg_efficiency",
    "fk_effectiveness",
    "setpiece_dependency",
    "open_play_efficiency",
    "sp_defensive_vulnerability",
    "xg_per_corner_shot",
    "xg_per_fk_shot",
    "xg_per_open_play_shot",
]


def _compute_rolling_setpiece(
    team_stats: pd.DataFrame,
    windows: list[int],
) -> pd.DataFrame:
    """Compute rolling averages for set-piece features.

    Uses shift(1) to prevent lookahead bias. Computes both
    fixed-window rolling and season-to-date expanding means.

    Args:
        team_stats: Per-team per-game stats with computed features.
        windows: Rolling window sizes.

    Returns:
        DataFrame with rolling and STD feature columns per team-game.
    """
    if team_stats.empty:
        return pd.DataFrame()

    result_frames: list[pd.DataFrame] = []

    for (_team, _season), group in team_stats.groupby(["team", "season"]):
        rolled = _roll_group(group, windows)
        result_frames.append(rolled)

    if not result_frames:
        return pd.DataFrame()
    return pd.concat(result_frames, ignore_index=True)


def _roll_group(
    group: pd.DataFrame,
    windows: list[int],
) -> pd.DataFrame:
    """Apply rolling and expanding means to one team-season group.

    Args:
        group: Single team's chronological game stats.
        windows: Window sizes for rolling mean.

    Returns:
        DataFrame with game, team, and rolled feature columns.
    """
    sorted_group = group.sort_values("date")
    result = sorted_group[["league", "season", "game", "team"]].copy()

    for feature in _ROLLING_FEATURES:
        if feature not in sorted_group.columns:
            continue
        shifted = sorted_group[feature].shift(1)
        result = _add_window_rolls(result, shifted, feature, windows)
        result = _add_season_to_date(result, shifted, feature)

    return result


def _add_window_rolls(
    result: pd.DataFrame,
    shifted: pd.Series,
    feature: str,
    windows: list[int],
) -> pd.DataFrame:
    """Add fixed-window rolling means for a feature.

    Args:
        result: Target DataFrame to add columns to.
        shifted: Shifted (lag-1) feature values.
        feature: Feature name for column naming.
        windows: Window sizes.

    Returns:
        DataFrame with rolling columns added.
    """
    for window in windows:
        col_name = f"sp_{feature}_roll_{window}"
        result[col_name] = shifted.rolling(
            window=window, min_periods=window,
        ).mean().values
    return result


def _add_season_to_date(
    result: pd.DataFrame,
    shifted: pd.Series,
    feature: str,
) -> pd.DataFrame:
    """Add season-to-date expanding mean for a feature.

    Args:
        result: Target DataFrame to add column to.
        shifted: Shifted (lag-1) feature values.
        feature: Feature name for column naming.

    Returns:
        DataFrame with STD column added.
    """
    col_name = f"sp_{feature}_std"
    result[col_name] = shifted.expanding(min_periods=1).mean().values
    return result


# ---------------------------------------------------------------------------
# Join rolled features back to match DataFrame
# ---------------------------------------------------------------------------

def _join_to_matches(
    match_df: pd.DataFrame,
    rolled: pd.DataFrame,
) -> pd.DataFrame:
    """Join rolled set-piece features to match DataFrame.

    Creates home_sp_* and away_sp_* columns by joining on game key
    and team name.

    Args:
        match_df: Match-level DataFrame with home_team, away_team.
        rolled: Rolled set-piece features per team per game.

    Returns:
        Match DataFrame with set-piece feature columns added.
    """
    if rolled.empty:
        return match_df.copy()

    sp_cols = [c for c in rolled.columns if c.startswith("sp_")]
    join_subset = rolled[["game", "team", *sp_cols]].copy()

    result = match_df.copy()
    result = _join_side(result, join_subset, "home")
    result = _join_side(result, join_subset, "away")
    return result


def _join_side(
    df: pd.DataFrame,
    sp_data: pd.DataFrame,
    side: str,
) -> pd.DataFrame:
    """Join set-piece features for one side (home or away).

    Args:
        df: Match DataFrame.
        sp_data: Set-piece data with team and game columns.
        side: "home" or "away".

    Returns:
        DataFrame with side-prefixed set-piece columns.
    """
    team_col = f"{side}_team"
    sp_cols = [c for c in sp_data.columns if c.startswith("sp_")]

    renamed = sp_data.rename(columns={
        col: f"{side}_{col}" for col in sp_cols
    })
    renamed = renamed.rename(columns={"team": team_col})

    return df.merge(
        renamed, on=["game", team_col], how="left",
    )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def add_setpiece_features(
    df: pd.DataFrame,
    db: FootballDatabase,
    windows: list[int] | None = None,
    shots_df: pd.DataFrame | None = None,
    matches_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Add set-piece effectiveness features to a match DataFrame.

    Reads shots and matches from the database, computes per-team
    set-piece stats, applies rolling and season-to-date windows,
    and joins back to the match DataFrame.

    Args:
        df: Match-level DataFrame with game, home_team, away_team.
        db: FootballDatabase instance for reading shots/matches.
        windows: Rolling window sizes (default: [3, 5, 10]).
        shots_df: Pre-loaded shots DataFrame (skips DB load).
        matches_df: Pre-loaded matches DataFrame (skips DB load).

    Returns:
        DataFrame with set-piece feature columns added.
    """
    if df.empty:
        return df.copy()

    if windows is None:
        windows = _DEFAULT_WINDOWS

    shots = shots_df if shots_df is not None else _load_shots(db)
    matches = matches_df if matches_df is not None else _load_matches(db)

    if shots.empty:
        logger.warning("No shots data found, skipping set-piece features")
        return df.copy()

    shot_stats = _build_team_shot_stats(shots)
    if shot_stats.empty:
        logger.warning("Could not build shot stats")
        return df.copy()

    corner_stats = _build_corner_stats(matches)
    conceded_stats = _build_opponent_shot_stats(shots, matches)

    merged = _merge_team_game_stats(
        shot_stats, corner_stats, conceded_stats, matches,
    )

    features = _compute_raw_features(merged)
    rolled = _compute_rolling_setpiece(features, windows)
    result = _join_to_matches(df, rolled)

    new_cols = len(result.columns) - len(df.columns)
    logger.info("Added %d set-piece feature columns", new_cols)

    return result
