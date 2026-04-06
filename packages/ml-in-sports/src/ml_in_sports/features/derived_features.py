"""Derived and interaction features for match prediction.

Computes calendar/temporal features, home-vs-away difference features,
lag features (t-1, t-2, t-3), interaction products, and percentile
ranks within leagues. Operates on columns already present from other
feature modules (rolling, tactical, betting, etc.).
"""

import numpy as np
import pandas as pd
import structlog

from ml_in_sports.features._shared import ensure_datetime as _ensure_datetime

logger = structlog.get_logger(__name__)

_DEFAULT_LAGS: list[int] = [1, 2, 3]

_LAG_STATS: list[str] = [
    "goals_scored",
    "goals_conceded",
    "xg_for",
    "xg_against",
    "points",
]

_INTERACTIONS: list[tuple[str, str, str]] = [
    ("elo_x_form_home", "home_elo", "home_rolling_points_5"),
    ("elo_x_form_away", "away_elo", "away_rolling_points_5"),
    ("elo_x_xg_home", "home_elo", "home_rolling_xg_for_5"),
    ("elo_x_xg_away", "away_elo", "away_rolling_xg_for_5"),
    (
        "xg_x_conversion_home",
        "home_rolling_xg_for_5",
        "home_rolling_shot_conversion_5",
    ),
    (
        "xg_x_conversion_away",
        "away_rolling_xg_for_5",
        "away_rolling_shot_conversion_5",
    ),
    ("diff_elo_x_form", "diff_elo", "diff_rolling_points_5"),
]

_PERCENTILE_STATS: list[str] = [
    "goals_scored_std",
    "goals_conceded_std",
    "xg_for_std",
]


# -------------------------------------------------------------------
# Public orchestrator
# -------------------------------------------------------------------


def add_derived_features(
    df: pd.DataFrame,
    lags: list[int] | None = None,
) -> pd.DataFrame:
    """Add all derived features to a match DataFrame.

    Computes calendar, differences, lags, interactions, and
    percentile ranks. Operates on columns already present from
    other feature modules.

    Args:
        df: DataFrame with match-level data and existing feature
            columns.
        lags: Lag offsets for individual match values
            (default: [1, 2, 3]).

    Returns:
        DataFrame with derived feature columns added.
    """
    if df.empty:
        return df.copy()

    if lags is None:
        lags = _DEFAULT_LAGS

    result = df.copy()
    result = _add_calendar_features(result)
    result = _add_difference_features(result)
    result = _add_lag_features(result, lags)
    result = _add_interaction_features(result)
    result = _add_percentile_features(result)

    new_cols = len(result.columns) - len(df.columns)
    logger.info("Added %d derived feature columns", new_cols)
    return result


# -------------------------------------------------------------------
# Calendar / temporal features
# -------------------------------------------------------------------


def _add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add calendar and temporal features from date and round.

    Args:
        df: DataFrame with date and optionally round columns.

    Returns:
        New DataFrame with calendar feature columns added.
    """
    result = df.copy()
    if "date" not in result.columns:
        return result

    dates = pd.to_datetime(result["date"])
    result["month"] = dates.dt.month
    result["day_of_week"] = dates.dt.dayofweek
    result["is_weekend"] = (dates.dt.dayofweek >= 5).astype(int)
    result["is_holiday_period"] = _compute_holiday_period(dates)
    result = _add_season_phase(result)
    result = _add_round_number(result)
    return result


def _compute_holiday_period(dates: pd.Series) -> pd.Series:
    """Flag matches during Dec 20 - Jan 3 holiday period.

    Args:
        dates: Series of datetime values.

    Returns:
        Series of int (1 = holiday, 0 = not).
    """
    month = dates.dt.month
    day = dates.dt.day
    dec_holiday = (month == 12) & (day >= 20)
    jan_holiday = (month == 1) & (day <= 3)
    return (dec_holiday | jan_holiday).astype(int)  # type: ignore[no-any-return]  # pandas bool ops return Series


def _add_season_phase(df: pd.DataFrame) -> pd.DataFrame:
    """Add season_phase based on round column.

    Early (0): rounds 1-12, Mid (1): rounds 13-26, Late (2): 27+.

    Args:
        df: DataFrame with optional round column.

    Returns:
        DataFrame with season_phase column added.
    """
    if "round" not in df.columns:
        return df

    round_vals = pd.to_numeric(df["round"], errors="coerce")
    conditions = [round_vals <= 12, round_vals <= 26]
    choices = [0, 1]
    df["season_phase"] = np.select(
        conditions, choices, default=2,
    )
    return df


def _add_round_number(df: pd.DataFrame) -> pd.DataFrame:
    """Add round_number as integer from round column.

    Args:
        df: DataFrame with optional round column.

    Returns:
        DataFrame with round_number column added.
    """
    if "round" not in df.columns:
        return df

    df["round_number"] = pd.to_numeric(
        df["round"], errors="coerce",
    )
    return df


# -------------------------------------------------------------------
# Difference features (home - away)
# -------------------------------------------------------------------


def _add_difference_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add home-minus-away difference features.

    Auto-detects matching home_*/away_* column pairs and computes
    their difference.

    Args:
        df: DataFrame with home_* and away_* columns.

    Returns:
        New DataFrame with diff_* columns added.
    """
    result = df.copy()
    pairs = _find_home_away_pairs(result)

    for suffix, home_col, away_col in pairs:
        diff_col = f"diff_{suffix}"
        result[diff_col] = result[home_col] - result[away_col]

    if pairs:
        logger.debug("Added %d difference features", len(pairs))
    return result


def _find_home_away_pairs(
    df: pd.DataFrame,
) -> list[tuple[str, str, str]]:
    """Find matching home_*/away_* column pairs.

    Only includes numeric columns whose suffix contains
    'rolling_', 'elo', or '_std' to avoid diffing non-stat
    columns like home_team.

    Args:
        df: DataFrame to scan for column pairs.

    Returns:
        List of (suffix, home_col, away_col) tuples.
    """
    home_cols = [c for c in df.columns if c.startswith("home_")]
    pairs: list[tuple[str, str, str]] = []

    for home_col in home_cols:
        suffix = home_col[5:]
        away_col = f"away_{suffix}"
        if away_col not in df.columns:
            continue
        if not _is_diffable_column(suffix):
            continue
        if not _is_numeric_pair(df, home_col, away_col):
            continue
        pairs.append((suffix, home_col, away_col))

    return pairs


def _is_diffable_column(suffix: str) -> bool:
    """Check if a column suffix represents a stat worth diffing.

    Args:
        suffix: Column suffix after removing home_/away_ prefix.

    Returns:
        True if the column should be diffed.
    """
    patterns = ["rolling_", "elo", "_std"]
    return any(pattern in suffix for pattern in patterns)


def _is_numeric_pair(
    df: pd.DataFrame,
    col_a: str,
    col_b: str,
) -> bool:
    """Check if both columns are numeric.

    Args:
        df: DataFrame containing the columns.
        col_a: First column name.
        col_b: Second column name.

    Returns:
        True if both columns have numeric dtype.
    """
    return (
        pd.api.types.is_numeric_dtype(df[col_a])
        and pd.api.types.is_numeric_dtype(df[col_b])
    )


# -------------------------------------------------------------------
# Lag features (t-1, t-2, t-3)
# -------------------------------------------------------------------


def _add_lag_features(
    df: pd.DataFrame,
    lags: list[int],
) -> pd.DataFrame:
    """Add lag features for key stats per team.

    Builds team histories and shifts raw match values by lag
    offsets. Groups by (team, season) for boundary resets.

    Args:
        df: Match DataFrame with goals, xg, etc.
        lags: Lag offsets (e.g. [1, 2, 3]).

    Returns:
        New DataFrame with lag feature columns added.
    """
    if df.empty:
        return df.copy()

    result = df.copy()
    result = _ensure_datetime(result)
    result = result.sort_values("date").reset_index(drop=True)
    histories = _build_lag_histories(result)

    if histories.empty:
        return result

    for stat in _LAG_STATS:
        if stat not in histories.columns:
            continue
        lagged = _compute_lag_for_stat(histories, stat, lags)
        result = _assign_lags_to_matches(result, lagged, stat, lags)

    return result


def _build_lag_histories(df: pd.DataFrame) -> pd.DataFrame:
    """Build per-team match history for lag computation.

    Each match creates two rows: one for home team and one for
    the away team with stats from their perspective.

    Args:
        df: Match DataFrame.

    Returns:
        Per-team history sorted by date.
    """
    home = _extract_lag_home_records(df)
    away = _extract_lag_away_records(df)
    combined = pd.concat([home, away], ignore_index=True)
    return combined.sort_values("date").reset_index(drop=True)


def _extract_lag_home_records(df: pd.DataFrame) -> pd.DataFrame:
    """Extract home team records for lag features.

    Args:
        df: Match DataFrame.

    Returns:
        DataFrame with team stats from home perspective.
    """
    records: dict[str, object] = {
        "match_idx": df.index,
        "date": df["date"].values,
        "team": df["home_team"].values,
        "venue": "home",
        "goals_scored": df["home_goals"].values,
        "goals_conceded": df["away_goals"].values,
    }
    if "season" in df.columns:
        records["season"] = df["season"].values

    result = pd.DataFrame(records)
    result = _add_optional_lag_stat(result, df, "xg_for", "home_xg")
    result = _add_optional_lag_stat(
        result, df, "xg_against", "away_xg",
    )
    result = _add_points_column(result, df, "home_goals", "away_goals")
    return result


def _extract_lag_away_records(df: pd.DataFrame) -> pd.DataFrame:
    """Extract away team records for lag features.

    Args:
        df: Match DataFrame.

    Returns:
        DataFrame with team stats from away perspective.
    """
    records: dict[str, object] = {
        "match_idx": df.index,
        "date": df["date"].values,
        "team": df["away_team"].values,
        "venue": "away",
        "goals_scored": df["away_goals"].values,
        "goals_conceded": df["home_goals"].values,
    }
    if "season" in df.columns:
        records["season"] = df["season"].values

    result = pd.DataFrame(records)
    result = _add_optional_lag_stat(result, df, "xg_for", "away_xg")
    result = _add_optional_lag_stat(
        result, df, "xg_against", "home_xg",
    )
    result = _add_points_column(result, df, "away_goals", "home_goals")
    return result


def _add_optional_lag_stat(
    records: pd.DataFrame,
    source: pd.DataFrame,
    target_col: str,
    source_col: str,
) -> pd.DataFrame:
    """Add a column from source if it exists.

    Args:
        records: Target DataFrame.
        source: Source DataFrame.
        target_col: Name for the new column.
        source_col: Column name in source.

    Returns:
        Records with optional column added.
    """
    if source_col in source.columns:
        records[target_col] = source[source_col].values
    return records


def _add_points_column(
    records: pd.DataFrame,
    source: pd.DataFrame,
    goals_for_col: str,
    goals_against_col: str,
) -> pd.DataFrame:
    """Add match points (3/1/0) to records.

    Args:
        records: Target DataFrame.
        source: Source DataFrame with goal columns.
        goals_for_col: Column for goals scored.
        goals_against_col: Column for goals conceded.

    Returns:
        Records with points column added.
    """
    gf = source[goals_for_col]
    ga = source[goals_against_col]
    conditions = [gf > ga, gf == ga]
    choices = [3.0, 1.0]
    records["points"] = np.select(conditions, choices, default=0.0)
    return records


def _compute_lag_for_stat(
    histories: pd.DataFrame,
    stat: str,
    lags: list[int],
) -> pd.DataFrame:
    """Compute lagged values for a stat across team-season groups.

    Args:
        histories: Per-team match history.
        stat: Column name to lag.
        lags: Lag offsets.

    Returns:
        DataFrame with match_idx, venue, and lag columns.
    """
    group_cols = ["team"]
    if "season" in histories.columns:
        group_cols.append("season")

    frames: list[pd.DataFrame] = []
    for _keys, group in histories.groupby(group_cols):
        lagged = _lag_single_group(group, stat, lags)
        frames.append(lagged)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _lag_single_group(
    group: pd.DataFrame,
    stat: str,
    lags: list[int],
) -> pd.DataFrame:
    """Apply shift(lag) for each lag offset to one group.

    Args:
        group: Single team-season chronological history.
        stat: Column to lag.
        lags: Lag offsets.

    Returns:
        DataFrame with match_idx, venue, and lag columns.
    """
    sorted_group = group.sort_values("date")
    result = sorted_group[["match_idx", "venue"]].copy()
    for lag in lags:
        col = f"{stat}_lag{lag}"
        result[col] = sorted_group[stat].shift(lag).values
    return result


def _assign_lags_to_matches(
    df: pd.DataFrame,
    lagged: pd.DataFrame,
    stat: str,
    lags: list[int],
) -> pd.DataFrame:
    """Assign lagged values back to match rows.

    Args:
        df: Match DataFrame.
        lagged: Lagged DataFrame with match_idx and venue.
        stat: Stat name for column naming.
        lags: Lag offsets used.

    Returns:
        DataFrame with home_*_lag and away_*_lag columns.
    """
    if lagged.empty:
        return df

    lag_cols = [f"{stat}_lag{lag}" for lag in lags]

    for venue in ["home", "away"]:
        venue_data = lagged[lagged["venue"] == venue].copy()
        venue_data = venue_data.set_index("match_idx")
        for col in lag_cols:
            target = f"{venue}_{col}"
            if col in venue_data.columns:
                df[target] = venue_data[col].reindex(df.index)

    return df


# -------------------------------------------------------------------
# Interaction features (products of two features)
# -------------------------------------------------------------------


def _add_interaction_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add interaction features as products of column pairs.

    Only computes interactions where both source columns exist.

    Args:
        df: DataFrame with existing feature columns.

    Returns:
        New DataFrame with interaction columns added.
    """
    result = df.copy()
    added = 0

    for name, col_a, col_b in _INTERACTIONS:
        if col_a not in result.columns or col_b not in result.columns:
            logger.debug(
                "Skipping interaction %s: missing %s or %s",
                name, col_a, col_b,
            )
            continue
        result[name] = result[col_a] * result[col_b]
        added += 1

    if added:
        logger.debug("Added %d interaction features", added)
    return result


# -------------------------------------------------------------------
# Percentile rank within league
# -------------------------------------------------------------------


def _add_percentile_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add percentile rank features within league and round.

    For season-to-date stats, computes the team's percentile
    rank among all teams in the same league at the same round.

    Args:
        df: DataFrame with league, season, and STD columns.

    Returns:
        New DataFrame with percentile rank columns added.
    """
    result = df.copy()

    for stat in _PERCENTILE_STATS:
        home_col = f"home_rolling_{stat}"
        away_col = f"away_rolling_{stat}"
        result = _add_percentile_for_stat(
            result, stat, home_col, away_col,
        )

    return result


def _add_percentile_for_stat(
    df: pd.DataFrame,
    stat: str,
    home_col: str,
    away_col: str,
) -> pd.DataFrame:
    """Add percentile rank for one stat across home and away.

    Args:
        df: DataFrame with league grouping columns.
        stat: Base stat name for output column naming.
        home_col: Column with home team's stat value.
        away_col: Column with away team's stat value.

    Returns:
        DataFrame with pctile columns added.
    """
    if home_col not in df.columns or away_col not in df.columns:
        return df

    group_col = _get_percentile_group_col(df)
    if group_col is None:
        return df

    all_vals = _stack_home_away_values(df, home_col, away_col)
    ranked = _rank_within_groups(all_vals, group_col)
    df = _assign_percentile_columns(df, ranked, stat)
    return df


def _get_percentile_group_col(
    df: pd.DataFrame,
) -> str | None:
    """Determine the grouping column for percentile ranking.

    Args:
        df: DataFrame to check for grouping columns.

    Returns:
        Column name to group by, or None if not available.
    """
    if "league" in df.columns and "season" in df.columns:
        return "league_season"
    if "league" in df.columns:
        return "league"
    return None


def _stack_home_away_values(
    df: pd.DataFrame,
    home_col: str,
    away_col: str,
) -> pd.DataFrame:
    """Stack home and away stat values into a single column.

    Args:
        df: DataFrame with home and away columns.
        home_col: Home team stat column.
        away_col: Away team stat column.

    Returns:
        DataFrame with match_idx, venue, value, and group cols.
    """
    league = df["league"].values if "league" in df.columns else None
    season = df["season"].values if "season" in df.columns else None

    home = pd.DataFrame({
        "match_idx": df.index,
        "venue": "home",
        "value": df[home_col].values,
    })
    away = pd.DataFrame({
        "match_idx": df.index,
        "venue": "away",
        "value": df[away_col].values,
    })

    if league is not None:
        home["league"] = league
        away["league"] = league
    if season is not None:
        home["season"] = season
        away["season"] = season

    stacked = pd.concat([home, away], ignore_index=True)
    if "league" in stacked.columns and "season" in stacked.columns:
        stacked["league_season"] = (
            stacked["league"].astype(str)
            + "_"
            + stacked["season"].astype(str)
        )
    return stacked


def _rank_within_groups(
    stacked: pd.DataFrame,
    group_col: str,
) -> pd.DataFrame:
    """Rank values within groups using percentile rank.

    Args:
        stacked: Stacked home/away values with group column.
        group_col: Column to group by for ranking.

    Returns:
        DataFrame with pctile column added.
    """
    stacked["pctile"] = stacked.groupby(group_col)["value"].rank(
        pct=True, na_option="keep",
    )
    return stacked


def _assign_percentile_columns(
    df: pd.DataFrame,
    ranked: pd.DataFrame,
    stat: str,
) -> pd.DataFrame:
    """Assign percentile ranks back to match rows.

    Args:
        df: Match DataFrame.
        ranked: Ranked DataFrame with match_idx, venue, pctile.
        stat: Stat name for output column naming.

    Returns:
        DataFrame with home_pctile_* and away_pctile_* columns.
    """
    for venue in ["home", "away"]:
        venue_data = ranked[ranked["venue"] == venue].copy()
        venue_data = venue_data.set_index("match_idx")
        target = f"{venue}_pctile_{stat}"
        df[target] = venue_data["pctile"].reindex(df.index)
    return df
