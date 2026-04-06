"""Tactical and efficiency rolling features for match prediction.

Computes rolling statistics for tactical metrics (PPDA, possession,
deep completions) and efficiency ratios (shot conversion, pass
accuracy, tackle success rate, etc.). All features use shift(1) to
prevent lookahead bias, with season boundary resets via groupby.
"""

import numpy as np
import pandas as pd
import structlog

logger = structlog.get_logger(__name__)

_DEFAULT_WINDOWS: list[int] = [3, 5, 10]

_RAW_TACTICAL_STATS: list[str] = [
    "ppda",
    "possession",
    "deep_completions",
    "interceptions",
]

_RATIO_DEFINITIONS: list[dict[str, str]] = [
    {
        "name": "shot_conversion",
        "numerator": "goals_scored",
        "denominator": "total_shots",
    },
    {
        "name": "xg_overperformance",
        "numerator": "xg_overperformance_raw",
        "denominator": "",
    },
    {
        "name": "sot_ratio",
        "numerator": "shots_on_target",
        "denominator": "total_shots",
    },
    {
        "name": "pass_accuracy",
        "numerator": "accurate_passes",
        "denominator": "total_passes",
    },
    {
        "name": "cross_accuracy",
        "numerator": "accurate_crosses",
        "denominator": "total_crosses",
    },
    {
        "name": "long_ball_accuracy",
        "numerator": "accurate_long_balls",
        "denominator": "total_long_balls",
    },
    {
        "name": "tackle_success",
        "numerator": "effective_tackles",
        "denominator": "total_tackles",
    },
    {
        "name": "clearance_effectiveness",
        "numerator": "effective_clearance",
        "denominator": "total_clearance",
    },
    {
        "name": "blocked_shots_ratio",
        "numerator": "blocked_shots",
        "denominator": "opp_total_shots",
    },
    {
        "name": "saves_ratio",
        "numerator": "saves",
        "denominator": "opp_shots_on_target",
    },
    {
        "name": "penalty_conversion",
        "numerator": "penalty_kick_goals",
        "denominator": "penalty_kick_shots",
    },
]

_MOMENTUM_STATS: list[str] = [
    "ppda",
    "possession",
    "deep_completions",
    "shot_conversion",
    "xg_overperformance",
    "pass_accuracy",
    "tackle_success",
]


def add_tactical_features(
    df: pd.DataFrame,
    windows: list[int] | None = None,
) -> pd.DataFrame:
    """Add all tactical and efficiency rolling features.

    Args:
        df: DataFrame with match-level data including date, teams.
        windows: Rolling window sizes (default: [3, 5, 10]).

    Returns:
        DataFrame with tactical feature columns added.
    """
    if df.empty:
        return df.copy()

    if windows is None:
        windows = _DEFAULT_WINDOWS

    result = df.copy()
    result = result.sort_values("date").reset_index(drop=True)
    result = compute_raw_tactical_rolling_features(result, windows)
    result = compute_ratio_rolling_features(result, windows)
    result = compute_momentum_features(result)

    logger.info(
        "Added tactical features: %d new columns",
        len(result.columns) - len(df.columns),
    )
    return result


def compute_raw_tactical_rolling_features(
    df: pd.DataFrame,
    windows: list[int],
) -> pd.DataFrame:
    """Compute rolling means for raw tactical stats per team.

    Args:
        df: Match DataFrame sorted by date.
        windows: Rolling window sizes.

    Returns:
        DataFrame with raw tactical rolling columns added.
    """
    result = df.copy()
    histories = _build_tactical_histories(result)

    for stat_name in _RAW_TACTICAL_STATS:
        if stat_name not in histories.columns:
            continue
        rolled = _roll_stat_all_teams(histories, stat_name, windows)
        result = _assign_rolled_to_matches(result, rolled, stat_name)

    return result


def compute_ratio_rolling_features(
    df: pd.DataFrame,
    windows: list[int],
) -> pd.DataFrame:
    """Compute rolling means for efficiency ratio stats per team.

    Args:
        df: Match DataFrame sorted by date.
        windows: Rolling window sizes.

    Returns:
        DataFrame with ratio rolling columns added.
    """
    result = df.copy()
    histories = _build_tactical_histories(result)

    for ratio_def in _RATIO_DEFINITIONS:
        stat_name = ratio_def["name"]
        if stat_name not in histories.columns:
            continue
        rolled = _roll_stat_all_teams(histories, stat_name, windows)
        result = _assign_rolled_to_matches(result, rolled, stat_name)

    return result


def compute_momentum_features(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Compute momentum features: rolling_3 minus rolling_10.

    Args:
        df: Match DataFrame with rolling tactical features.

    Returns:
        DataFrame with momentum columns added.
    """
    result = df.copy()
    result = result.sort_values("date").reset_index(drop=True)
    histories = _build_tactical_histories(result)

    for stat_name in _MOMENTUM_STATS:
        if stat_name not in histories.columns:
            continue
        rolled = _roll_stat_all_teams(histories, stat_name, [3, 10])
        momentum = _compute_momentum_from_rolled(rolled, stat_name)
        result = _assign_momentum_to_matches(result, momentum, stat_name)

    return result


def _build_tactical_histories(df: pd.DataFrame) -> pd.DataFrame:
    """Build per-team match history with tactical stats.

    Args:
        df: Match DataFrame with home/away columns.

    Returns:
        DataFrame with one row per team per match, sorted by date.
    """
    home_records = _extract_home_tactical(df)
    away_records = _extract_away_tactical(df)
    history = pd.concat([home_records, away_records], ignore_index=True)
    return history.sort_values("date").reset_index(drop=True)


def _extract_home_tactical(df: pd.DataFrame) -> pd.DataFrame:
    """Extract tactical records from the home team perspective.

    Args:
        df: Match DataFrame.

    Returns:
        DataFrame with tactical stats for home teams.
    """
    records = pd.DataFrame({
        "match_idx": df.index,
        "date": df["date"].values,
        "season": df["season"].values,
        "team": df["home_team"].values,
        "venue": "home",
    })
    records = _add_raw_tactical_stats(records, df, "home", "away")
    records = _add_ratio_stats(records, df, "home", "away")
    return records


def _extract_away_tactical(df: pd.DataFrame) -> pd.DataFrame:
    """Extract tactical records from the away team perspective.

    Args:
        df: Match DataFrame.

    Returns:
        DataFrame with tactical stats for away teams.
    """
    records = pd.DataFrame({
        "match_idx": df.index,
        "date": df["date"].values,
        "season": df["season"].values,
        "team": df["away_team"].values,
        "venue": "away",
    })
    records = _add_raw_tactical_stats(records, df, "away", "home")
    records = _add_ratio_stats(records, df, "away", "home")
    return records


def _add_raw_tactical_stats(
    records: pd.DataFrame,
    source: pd.DataFrame,
    side: str,
    opponent_side: str,
) -> pd.DataFrame:
    """Add raw tactical stat columns from source if present.

    Args:
        records: Target DataFrame to add columns to.
        source: Source match DataFrame.
        side: Team side ("home" or "away").
        opponent_side: Opponent side ("away" or "home").

    Returns:
        Records with raw tactical columns added.
    """
    stat_col_map = {
        "ppda": f"{side}_ppda",
        "possession": f"{side}_possession",
        "deep_completions": f"{side}_deep_completions",
        "interceptions": f"{side}_interceptions",
    }
    for stat_name, col_name in stat_col_map.items():
        if col_name in source.columns:
            records[stat_name] = source[col_name].values
    return records


def _add_ratio_stats(
    records: pd.DataFrame,
    source: pd.DataFrame,
    side: str,
    opponent_side: str,
) -> pd.DataFrame:
    """Compute and add per-match ratio stats to records.

    Args:
        records: Target DataFrame.
        source: Source match DataFrame.
        side: Team side ("home" or "away").
        opponent_side: Opponent side ("away" or "home").

    Returns:
        Records with ratio stat columns added.
    """
    records = _add_shot_conversion(records, source, side)
    records = _add_xg_overperformance(records, source, side)
    records = _add_simple_ratio(
        records, source, "sot_ratio",
        f"{side}_shots_on_target", f"{side}_total_shots",
    )
    records = _add_simple_ratio(
        records, source, "pass_accuracy",
        f"{side}_accurate_passes", f"{side}_total_passes",
    )
    records = _add_simple_ratio(
        records, source, "cross_accuracy",
        f"{side}_accurate_crosses", f"{side}_total_crosses",
    )
    records = _add_simple_ratio(
        records, source, "long_ball_accuracy",
        f"{side}_accurate_long_balls", f"{side}_total_long_balls",
    )
    records = _add_simple_ratio(
        records, source, "tackle_success",
        f"{side}_effective_tackles", f"{side}_total_tackles",
    )
    records = _add_simple_ratio(
        records, source, "clearance_effectiveness",
        f"{side}_effective_clearance", f"{side}_total_clearance",
    )
    records = _add_simple_ratio(
        records, source, "blocked_shots_ratio",
        f"{side}_blocked_shots", f"{opponent_side}_total_shots",
    )
    records = _add_simple_ratio(
        records, source, "saves_ratio",
        f"{side}_saves", f"{opponent_side}_shots_on_target",
    )
    records = _add_simple_ratio(
        records, source, "penalty_conversion",
        f"{side}_penalty_kick_goals", f"{side}_penalty_kick_shots",
    )
    return records


def _add_shot_conversion(
    records: pd.DataFrame,
    source: pd.DataFrame,
    side: str,
) -> pd.DataFrame:
    """Add shot conversion rate (goals / total_shots).

    Args:
        records: Target DataFrame.
        source: Source match DataFrame.
        side: Team side.

    Returns:
        Records with shot_conversion column added.
    """
    goals_col = f"{side}_goals"
    shots_col = f"{side}_total_shots"
    if goals_col in source.columns and shots_col in source.columns:
        goals: np.ndarray = source[goals_col].values.astype(float)  # type: ignore[assignment]
        shots: np.ndarray = source[shots_col].values.astype(float)  # type: ignore[assignment]
        records["shot_conversion"] = _safe_divide(goals, shots)
    return records


def _add_xg_overperformance(
    records: pd.DataFrame,
    source: pd.DataFrame,
    side: str,
) -> pd.DataFrame:
    """Add xG overperformance (goals - xG).

    Args:
        records: Target DataFrame.
        source: Source match DataFrame.
        side: Team side.

    Returns:
        Records with xg_overperformance column added.
    """
    goals_col = f"{side}_goals"
    xg_col = f"{side}_xg"
    if goals_col in source.columns and xg_col in source.columns:
        goals_arr: np.ndarray = source[goals_col].values.astype(float)  # type: ignore[assignment]
        xg_arr: np.ndarray = source[xg_col].values.astype(float)  # type: ignore[assignment]
        records["xg_overperformance"] = goals_arr - xg_arr
    return records


def _add_simple_ratio(
    records: pd.DataFrame,
    source: pd.DataFrame,
    stat_name: str,
    numerator_col: str,
    denominator_col: str,
) -> pd.DataFrame:
    """Add a ratio stat (numerator / denominator) to records.

    Args:
        records: Target DataFrame.
        source: Source match DataFrame.
        stat_name: Name for the new column.
        numerator_col: Column name for the numerator.
        denominator_col: Column name for the denominator.

    Returns:
        Records with ratio column added.
    """
    if numerator_col not in source.columns:
        return records
    if denominator_col not in source.columns:
        return records

    num: np.ndarray = source[numerator_col].values.astype(float)  # type: ignore[assignment]
    denom: np.ndarray = source[denominator_col].values.astype(float)  # type: ignore[assignment]
    records[stat_name] = _safe_divide(num, denom)
    return records


def _safe_divide(
    numerator: np.ndarray,
    denominator: np.ndarray,
) -> np.ndarray:
    """Divide numerator by denominator, returning NaN for zero/missing.

    Args:
        numerator: Array of numerator values.
        denominator: Array of denominator values.

    Returns:
        Array with division results; NaN where denominator is 0.
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        result = np.where(
            denominator > 0,
            numerator / denominator,
            np.nan,
        )
    return result


def _roll_stat_all_teams(
    histories: pd.DataFrame,
    stat_name: str,
    windows: list[int],
) -> pd.DataFrame:
    """Compute rolling means for a stat across all team-season groups.

    Args:
        histories: Per-team match history.
        stat_name: Column name to roll.
        windows: Window sizes.

    Returns:
        DataFrame with match_idx, venue, and rolling columns.
    """
    result_frames: list[pd.DataFrame] = []
    for _, group in histories.groupby(["team", "season"]):
        rolled = _roll_single_group(group, stat_name, windows)
        result_frames.append(rolled)

    if not result_frames:
        return pd.DataFrame()
    return pd.concat(result_frames, ignore_index=True)


def _roll_single_group(
    group: pd.DataFrame,
    stat_name: str,
    windows: list[int],
) -> pd.DataFrame:
    """Apply rolling mean with shift(1) to one team-season group.

    Args:
        group: Single team's chronological match history.
        stat_name: Column to roll.
        windows: Window sizes.

    Returns:
        DataFrame with match_idx, venue, and rolled values.
    """
    rolled = group[["match_idx", "venue"]].copy()
    shifted = group[stat_name].shift(1)
    for window in windows:
        col_name = f"rolling_{stat_name}_{window}"
        rolled[col_name] = shifted.rolling(
            window=window, min_periods=window,
        ).mean()
    return rolled


def _assign_rolled_to_matches(
    df: pd.DataFrame,
    rolled: pd.DataFrame,
    stat_name: str,
) -> pd.DataFrame:
    """Assign rolled stats back to match rows using match_idx.

    Args:
        df: Match DataFrame.
        rolled: Rolled DataFrame with match_idx and venue.
        stat_name: Stat name for column naming.

    Returns:
        DataFrame with home_rolling_* and away_rolling_* columns.
    """
    if rolled.empty:
        return df

    rolling_cols = [c for c in rolled.columns if c.startswith("rolling_")]
    if not rolling_cols:
        return df

    for venue in ["home", "away"]:
        venue_data = rolled[rolled["venue"] == venue].copy()
        venue_data = venue_data.set_index("match_idx")
        for col in rolling_cols:
            target_col = f"{venue}_{col}"
            df[target_col] = venue_data[col].reindex(df.index)

    return df


def _compute_momentum_from_rolled(
    rolled: pd.DataFrame,
    stat_name: str,
) -> pd.DataFrame:
    """Compute momentum (rolling_3 - rolling_10) from rolled data.

    Args:
        rolled: Rolled DataFrame with rolling_*_3 and rolling_*_10.
        stat_name: Stat name.

    Returns:
        DataFrame with match_idx, venue, and momentum column.
    """
    col_3 = f"rolling_{stat_name}_3"
    col_10 = f"rolling_{stat_name}_10"

    if col_3 not in rolled.columns or col_10 not in rolled.columns:
        return pd.DataFrame()

    momentum = rolled[["match_idx", "venue"]].copy()
    momentum[f"momentum_{stat_name}"] = (
        rolled[col_3] - rolled[col_10]
    )
    return momentum


def _assign_momentum_to_matches(
    df: pd.DataFrame,
    momentum: pd.DataFrame,
    stat_name: str,
) -> pd.DataFrame:
    """Assign momentum values back to match rows.

    Args:
        df: Match DataFrame.
        momentum: Momentum DataFrame with match_idx and venue.
        stat_name: Stat name for column naming.

    Returns:
        DataFrame with home_momentum_* and away_momentum_* columns.
    """
    if momentum.empty:
        return df

    col_name = f"momentum_{stat_name}"
    if col_name not in momentum.columns:
        return df

    for venue in ["home", "away"]:
        venue_data = momentum[momentum["venue"] == venue].copy()
        venue_data = venue_data.set_index("match_idx")
        target_col = f"{venue}_{col_name}"
        df[target_col] = venue_data[col_name].reindex(df.index)

    return df
