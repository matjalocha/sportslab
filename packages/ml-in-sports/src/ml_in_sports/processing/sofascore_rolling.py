"""Rolling computation helpers for Sofascore match statistics.

Builds per-team match histories and computes shifted rolling averages,
then joins results back to match-level DataFrames.  Used exclusively
by ``sofascore_features.compute_sofascore_rolling_features``.
"""

from __future__ import annotations

import pandas as pd


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
