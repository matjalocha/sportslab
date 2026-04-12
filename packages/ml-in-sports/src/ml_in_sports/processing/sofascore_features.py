"""Compute rolling features from merged Sofascore match statistics.

Takes a DataFrame with ``sofa_*`` columns (produced by
``merge_sofascore_stats_from_cache``) and computes rolling averages
per team per league with ``shift(1)`` to prevent lookahead bias.

The rolling computation builds a unified per-team match history
(combining home and away appearances) then applies rolling windows.
This mirrors the pattern in ``features/rolling_features.py`` but
operates exclusively on the ``sofa_*`` namespace.

Design decisions:
    - ``shift(1)`` on every rolling window: the current match is
      never included in its own rolling stat.
    - ``min_periods=1``: we emit a value as soon as one prior match
      exists (sparse early-season data is better than NaN).
    - Matches without Sofascore data (``sofa_*`` = NaN) propagate
      NaN into rolling computations, which naturally reduces the
      effective window size via ``min_periods``.
    - All output columns are prefixed ``sofa_`` to avoid collision
      with existing feature columns.
"""

from __future__ import annotations

import pandas as pd
import structlog

logger = structlog.get_logger(__name__)

_DEFAULT_WINDOWS: list[int] = [3, 5, 10]

# Base Sofascore stat names (without home_/away_ prefix) that receive
# rolling treatment.  The list is intentionally comprehensive — if a
# stat column doesn't exist in the data the code silently skips it.
ROLLING_STAT_BASES: list[str] = [
    "expected_goals",
    "possession",
    "total_shots",
    "shots_on_target",
    "tackles",
    "accurate_passes",
    "accurate_passes_pct",
    "accurate_crosses",
    "interceptions",
    "clearances",
    "accurate_long_balls",
    "ground_duels_won",
    "aerial_duels_won",
    "successful_dribbles",
    "saves",
    # Raw Sofascore keys that appear in newer scrapes (e.g. Championship
    # raw cache uses camelCase keys flattened with home_/away_ prefix).
    "ballPossession",
    "totalShotsOnGoal",
    "shotsOnGoal",
    "shotsOffGoal",
    "goalkeeperSaves",
    "cornerKicks",
    "fouls",
    "yellowCards",
    "redCards",
    "offsides",
]


def compute_sofascore_rolling_features(
    df: pd.DataFrame,
    windows: list[int] | None = None,
) -> pd.DataFrame:
    """Add rolling averages for all Sofascore stat columns.

    For each ``sofa_home_*`` / ``sofa_away_*`` column pair the function:

    1. Builds a per-team match log (home and away perspective).
    2. Applies ``shift(1)`` to exclude the current match.
    3. Computes ``rolling(window).mean()`` with ``min_periods=1``.
    4. Joins the result back as ``sofa_{stat}_rolling_{window}``.

    Additionally computes derived features:
    - ``sofa_xg_overperformance`` (actual goals - xG per match)
    - ``sofa_pass_accuracy`` (accurate_passes / total passes proxy)
    - ``sofa_ppda_proxy`` (opponent passes / (tackles + interceptions + fouls))

    Args:
        df: DataFrame with ``sofa_*`` columns and standard match columns
            (``date``, ``league``, ``home_team``, ``away_team``,
            ``home_goals``, ``away_goals``).
        windows: Rolling window sizes. Defaults to ``[3, 5, 10]``.

    Returns:
        DataFrame with rolling feature columns added. Original columns
        are never modified.
    """
    if df.empty:
        return df.copy()

    if windows is None:
        windows = _DEFAULT_WINDOWS

    result = df.copy()
    result["date"] = pd.to_datetime(result["date"])
    result = result.sort_values("date").reset_index(drop=True)

    # Derived per-match features (before rolling)
    result = _add_derived_match_features(result)

    # Discover which sofa stat bases are actually present
    available_bases = _discover_stat_bases(result)
    if not available_bases:
        logger.warning("sofascore_rolling_no_stats_found")
        return result

    logger.info(
        "sofascore_rolling_start",
        stat_bases=len(available_bases),
        windows=windows,
    )

    # Build team history and compute rolling stats
    team_history = _build_sofascore_team_history(result, available_bases)
    rolled = _compute_rolling_for_all_stats(team_history, available_bases, windows)
    result = _assign_rolling_to_matches(result, rolled, available_bases, windows)

    new_cols = len(result.columns) - len(df.columns)
    logger.info("sofascore_rolling_complete", new_columns=new_cols)
    return result


def _discover_stat_bases(df: pd.DataFrame) -> list[str]:
    """Find which Sofascore stat base names exist in the DataFrame.

    Looks for columns matching ``sofa_home_{base}`` or ``sofa_away_{base}``.

    Args:
        df: DataFrame to inspect.

    Returns:
        List of base stat names present in both home and away variants.
    """
    bases: list[str] = []
    for base in ROLLING_STAT_BASES:
        home_col = f"sofa_home_{base}"
        away_col = f"sofa_away_{base}"
        if home_col in df.columns or away_col in df.columns:
            bases.append(base)

    # Also discover any sofa_home_*/sofa_away_* not in the predefined list
    for col in df.columns:
        if col.startswith("sofa_home_"):
            base = col[len("sofa_home_") :]
            if base not in bases and f"sofa_away_{base}" in df.columns:
                bases.append(base)

    return bases


def _add_derived_match_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived per-match Sofascore features before rolling.

    Computes:
    - ``sofa_home_xg_overperformance``: home_goals - sofa_home_expected_goals
    - ``sofa_away_xg_overperformance``: away_goals - sofa_away_expected_goals
    - ``sofa_home_pass_accuracy``: sofa_home_accurate_passes_pct (passthrough)
    - ``sofa_home_ppda_proxy``: opponent passes / (tackles + interceptions + fouls)

    Args:
        df: DataFrame with sofa_* and standard match columns.

    Returns:
        DataFrame with derived columns added.
    """
    result = df.copy()

    # xG overperformance: actual goals minus expected goals
    xg_home_col = _find_xg_column(result, "home")
    xg_away_col = _find_xg_column(result, "away")

    if xg_home_col is not None and "home_goals" in result.columns:
        result["sofa_home_xg_overperformance"] = result["home_goals"] - result[xg_home_col]
    if xg_away_col is not None and "away_goals" in result.columns:
        result["sofa_away_xg_overperformance"] = result["away_goals"] - result[xg_away_col]

    # PPDA proxy: opponent_passes / (tackles + interceptions + fouls)
    result = _compute_ppda_proxy(result, "home", "away")
    result = _compute_ppda_proxy(result, "away", "home")

    return result


def _find_xg_column(df: pd.DataFrame, side: str) -> str | None:
    """Find the xG column for a given side (home/away).

    Checks for ``sofa_{side}_expected_goals`` and
    ``sofa_{side}_expectedGoals`` variants.

    Args:
        df: DataFrame to inspect.
        side: ``"home"`` or ``"away"``.

    Returns:
        Column name if found, else None.
    """
    candidates = [
        f"sofa_{side}_expected_goals",
        f"sofa_{side}_expectedGoals",
    ]
    for col in candidates:
        if col in df.columns:
            return col
    return None


def _compute_ppda_proxy(
    df: pd.DataFrame,
    team_side: str,
    opponent_side: str,
) -> pd.DataFrame:
    """Compute PPDA proxy for one side.

    PPDA = opponent passes allowed per defensive action.
    Approximated as: opponent_accurate_passes / (tackles + interceptions + fouls).

    Args:
        df: DataFrame with sofa_* columns.
        team_side: ``"home"`` or ``"away"`` (the defending team).
        opponent_side: The other side.

    Returns:
        DataFrame with ``sofa_{team_side}_ppda_proxy`` added.
    """
    opp_passes = _coalesce_column(
        df,
        f"sofa_{opponent_side}_accurate_passes",
        f"sofa_{opponent_side}_accuratePasses",
    )
    tackles = _coalesce_column(
        df,
        f"sofa_{team_side}_tackles",
        f"sofa_{team_side}_totalTackle",
    )
    interceptions = _coalesce_column(
        df,
        f"sofa_{team_side}_interceptions",
        f"sofa_{team_side}_interceptionWon",
    )
    fouls = _coalesce_column(
        df,
        f"sofa_{team_side}_fouls",
    )

    if opp_passes is None:
        return df

    denominator = pd.Series(0.0, index=df.index)
    if tackles is not None:
        denominator = denominator + tackles
    if interceptions is not None:
        denominator = denominator + interceptions
    if fouls is not None:
        denominator = denominator + fouls

    # Avoid division by zero
    denominator = denominator.replace(0, float("nan"))
    df[f"sofa_{team_side}_ppda_proxy"] = opp_passes / denominator

    return df


def _coalesce_column(
    df: pd.DataFrame,
    *candidates: str,
) -> pd.Series | None:
    """Return the first existing column from candidates as a numeric Series.

    Args:
        df: DataFrame to search.
        *candidates: Column name candidates in priority order.

    Returns:
        Numeric Series or None if no candidate exists.
    """
    for col in candidates:
        if col in df.columns:
            return pd.to_numeric(df[col], errors="coerce")
    return None


def _build_sofascore_team_history(
    df: pd.DataFrame,
    stat_bases: list[str],
) -> pd.DataFrame:
    """Build a unified per-team match history from home/away rows.

    Each match generates two rows: one for the home team and one for the
    away team, with stats normalized to the team's perspective.

    Args:
        df: Match DataFrame with ``sofa_*`` columns.
        stat_bases: Base stat names to include.

    Returns:
        DataFrame with columns: match_idx, date, league, team, venue,
        plus one column per stat base named ``stat_{base}``.
    """
    home_records = _extract_side_records(df, "home", stat_bases)
    away_records = _extract_side_records(df, "away", stat_bases)
    history = pd.concat([home_records, away_records], ignore_index=True)
    return history.sort_values(["league", "team", "date"]).reset_index(drop=True)


def _extract_side_records(
    df: pd.DataFrame,
    side: str,
    stat_bases: list[str],
) -> pd.DataFrame:
    """Extract team records from one side (home or away).

    Args:
        df: Match DataFrame.
        side: ``"home"`` or ``"away"``.
        stat_bases: Base stat names to include.

    Returns:
        DataFrame with normalized team stats.
    """
    records: dict[str, list[object]] = {
        "match_idx": list(df.index),
        "date": list(df["date"].values),
        "league": list(df["league"].values),
        "team": list(df[f"{side}_team"].values),
        "venue": [side] * len(df),
    }

    for base in stat_bases:
        col_name = f"sofa_{side}_{base}"
        if col_name in df.columns:
            records[f"stat_{base}"] = list(pd.to_numeric(df[col_name], errors="coerce").values)

    # Also include derived features
    for derived in ["xg_overperformance", "ppda_proxy"]:
        col_name = f"sofa_{side}_{derived}"
        if col_name in df.columns:
            records[f"stat_{derived}"] = list(pd.to_numeric(df[col_name], errors="coerce").values)

    return pd.DataFrame(records)


def _compute_rolling_for_all_stats(
    history: pd.DataFrame,
    stat_bases: list[str],
    windows: list[int],
) -> pd.DataFrame:
    """Compute shifted rolling means for all stats per team per league.

    Args:
        history: Per-team match history from ``_build_sofascore_team_history``.
        stat_bases: Base stat names to compute rolling for.
        windows: Rolling window sizes.

    Returns:
        History DataFrame with added ``rolling_{base}_{window}`` columns.
    """
    all_bases = list(stat_bases) + [
        b for b in ["xg_overperformance", "ppda_proxy"] if f"stat_{b}" in history.columns
    ]

    for base in all_bases:
        stat_col = f"stat_{base}"
        if stat_col not in history.columns:
            continue

        for window in windows:
            col_name = f"rolling_{base}_{window}"
            # shift(1) prevents lookahead, rolling with min_periods=1.
            # Bind window via default arg to avoid B023 loop-variable capture.
            history[col_name] = history.groupby(["league", "team"])[stat_col].transform(
                lambda s, w=window: s.shift(1).rolling(w, min_periods=1).mean()
            )

    return history


def _assign_rolling_to_matches(
    df: pd.DataFrame,
    history: pd.DataFrame,
    stat_bases: list[str],
    windows: list[int],
) -> pd.DataFrame:
    """Join rolling stats back to the match-level DataFrame.

    For each rolling column in the history, creates two match-level
    columns: one for the home team and one for the away team, plus
    a diff column (home - away).

    Args:
        df: Original match DataFrame.
        history: History with rolling columns, keyed by match_idx + venue.
        stat_bases: Base stat names.
        windows: Rolling window sizes.

    Returns:
        Match DataFrame with rolling feature columns added.
    """
    all_bases = list(stat_bases) + [
        b
        for b in ["xg_overperformance", "ppda_proxy"]
        if f"stat_{b}" in history.columns and b not in stat_bases
    ]

    rolling_cols = [
        f"rolling_{base}_{window}"
        for base in all_bases
        for window in windows
        if f"rolling_{base}_{window}" in history.columns
    ]

    if not rolling_cols:
        return df

    # Split history back into home and away, deduplicate index
    home_hist = (
        history[history["venue"] == "home"][["match_idx", *rolling_cols]]
        .drop_duplicates(subset="match_idx")
        .set_index("match_idx")
    )
    away_hist = (
        history[history["venue"] == "away"][["match_idx", *rolling_cols]]
        .drop_duplicates(subset="match_idx")
        .set_index("match_idx")
    )

    # Build all new columns in a dict, then create a single DataFrame
    # to avoid pandas internal state issues from iterative column insertion.
    new_cols: dict[str, pd.Series] = {}

    for col in rolling_cols:
        home_col_name = f"sofa_home_{col}"
        away_col_name = f"sofa_away_{col}"

        # Reindex to match df's integer index via .reindex()
        home_values = home_hist[col].reindex(df.index)
        away_values = away_hist[col].reindex(df.index)

        new_cols[home_col_name] = home_values
        new_cols[away_col_name] = away_values

    # Compute diff columns from the raw numpy arrays
    for base in all_bases:
        for window in windows:
            home_key = f"sofa_home_rolling_{base}_{window}"
            away_key = f"sofa_away_rolling_{base}_{window}"
            diff_key = f"sofa_diff_rolling_{base}_{window}"
            if home_key in new_cols and away_key in new_cols:
                new_cols[diff_key] = pd.Series(
                    new_cols[home_key].to_numpy() - new_cols[away_key].to_numpy(),
                    index=df.index,
                )

    new_df = pd.DataFrame(new_cols, index=df.index)
    return pd.concat([df, new_df], axis=1)
