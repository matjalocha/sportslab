"""New features: league table position, xG rolling, venue streaks, W/D/L last N.

All features are pre-match (no leakage): rolling values use shift(1),
and table positions are recorded before applying the match result.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import structlog

logger = structlog.get_logger(__name__)

_XG_WINDOWS: tuple[int, ...] = (3, 5, 10)
_METRICS: tuple[str, ...] = ("won", "drew", "lost", "scored", "cs")


def _build_team_log(df: pd.DataFrame) -> pd.DataFrame:
    """Long-format match log with one row per team per match.

    Outcome columns (won/drew/lost/scored/cs) are NaN for upcoming
    matches, so shift(1).rolling() windows use only past results.

    Args:
        df: Full match DataFrame (historical + upcoming rows).

    Returns:
        Long-format DataFrame sorted by team/league/season/date.
    """
    home = df[["date", "league", "season", "home_team",
               "home_goals", "away_goals", "home_xg", "away_xg"]].copy()
    home.columns = ["date", "league", "season", "team",
                    "gf", "ga", "xg_for", "xg_against"]
    home["role"] = "home"
    home["match_idx"] = df.index

    away = df[["date", "league", "season", "away_team",
               "away_goals", "home_goals", "away_xg", "home_xg"]].copy()
    away.columns = ["date", "league", "season", "team",
                    "gf", "ga", "xg_for", "xg_against"]
    away["role"] = "away"
    away["match_idx"] = df.index

    log = pd.concat([home, away], ignore_index=True)
    return _add_outcome_cols(log).sort_values(
        ["team", "league", "season", "date"]
    ).reset_index(drop=True)


def _add_outcome_cols(log: pd.DataFrame) -> pd.DataFrame:
    """Add won/drew/lost/scored/cs columns (NaN for upcoming rows).

    Args:
        log: Team log with gf and ga columns.

    Returns:
        log with outcome columns added in-place.
    """
    played = log["gf"].notna()
    log["won"]    = (log["gf"] > log["ga"]).where(played).astype("float64")
    log["drew"]   = (log["gf"] == log["ga"]).where(played).astype("float64")
    log["lost"]   = (log["gf"] < log["ga"]).where(played).astype("float64")
    log["scored"] = (log["gf"] > 0).where(played).astype("float64")
    log["cs"]     = (log["ga"] == 0).where(played).astype("float64")
    return log


def _rolling_mean(series: pd.Series, n: int) -> pd.Series:
    """Pre-match rolling mean (shift 1, min_periods=1, ffill for upcoming).

    Forward-fill propagates the last completed-match value to all
    subsequent upcoming matches, avoiding NaN cascades when multiple
    unplayed matches exist for the same team in the same window.

    Args:
        series: Input series.
        n: Rolling window size.

    Returns:
        Shifted rolling mean with NaN gaps forward-filled.
    """
    return series.shift(1).rolling(n, min_periods=1).mean().ffill()


def _rolling_sum(series: pd.Series, n: int) -> pd.Series:
    """Pre-match rolling sum (shift 1, min_periods=1, ffill for upcoming).

    Args:
        series: Input series.
        n: Rolling window size.

    Returns:
        Shifted rolling sum with NaN gaps forward-filled.
    """
    return series.shift(1).rolling(n, min_periods=1).sum().ffill()


def _compute_streak(series: pd.Series) -> pd.Series:
    """Consecutive streak count BEFORE current row (pre-match).

    Args:
        series: Binary (0/1/NaN) series for one team-season.

    Returns:
        Series where value at i = consecutive 1s ending at i-1.
    """
    arr = series.values
    result = np.zeros(len(arr))
    for i in range(1, len(arr)):
        result[i] = result[i - 1] + 1 if arr[i - 1] == 1.0 else 0
    return pd.Series(result, index=series.index)


def _rolling_features_for_role(
    team_log: pd.DataFrame,
    role: str,
) -> pd.DataFrame:
    """xG and W/D/L rolling features for one venue role.

    Args:
        team_log: Full team log (home + away rows).
        role: 'home' or 'away'.

    Returns:
        DataFrame indexed by match_idx with role-prefixed column names.
    """
    sub = team_log[team_log["role"] == role].copy()
    grp = sub.groupby(["team", "league", "season"])

    for n in _XG_WINDOWS:
        sub[f"{role}_xg_for_roll{n}"] = grp["xg_for"].transform(
            lambda s, n=n: _rolling_mean(s, n)
        )
        sub[f"{role}_xg_against_roll{n}"] = grp["xg_against"].transform(
            lambda s, n=n: _rolling_mean(s, n)
        )

    for metric in _METRICS:
        for n in (5, 10):
            sub[f"{role}_{metric}_last{n}"] = grp[metric].transform(
                lambda s, n=n: _rolling_sum(s, n)
            )

    new_cols = (
        [f"{role}_xg_for_roll{n}"     for n in _XG_WINDOWS]
        + [f"{role}_xg_against_roll{n}" for n in _XG_WINDOWS]
        + [f"{role}_{m}_last{n}" for m in _METRICS for n in (5, 10)]
    )
    return sub[["match_idx", *new_cols]].set_index("match_idx")


def _venue_streaks_for_role(
    team_log: pd.DataFrame,
    role: str,
) -> pd.DataFrame:
    """Venue-specific streaks and last-10 counts for one venue role.

    Args:
        team_log: Full team log.
        role: 'home' or 'away'.

    Returns:
        DataFrame indexed by match_idx with role-prefixed column names.
    """
    sub = team_log[team_log["role"] == role].copy()
    grp = sub.groupby(["team", "league", "season"])

    for metric in _METRICS:
        sub[f"{role}_venue_{metric}_streak"] = grp[metric].transform(
            lambda s: _compute_streak(s).ffill()
        )
        sub[f"{role}_venue_{metric}_last10"] = grp[metric].transform(
            lambda s: _rolling_sum(s, 10)
        )

    streak_cols = (
        [f"{role}_venue_{m}_streak" for m in _METRICS]
        + [f"{role}_venue_{m}_last10" for m in _METRICS]
    )
    return sub[["match_idx", *streak_cols]].set_index("match_idx")


def _table_for_season(matches: pd.DataFrame) -> pd.DataFrame:
    """Pre-match table positions for all matches in one league-season.

    Positions are recorded before applying the match result, so they
    reflect what was known at kick-off.

    Args:
        matches: All matches (incl. upcoming) for one (league, season).

    Returns:
        DataFrame with table features indexed by original DataFrame index.
    """
    matches = matches.sort_values("date")
    standings: dict[str, dict[str, int]] = {}
    rows: list[dict[str, object]] = []

    for idx, row in matches.iterrows():
        home, away = row["home_team"], row["away_team"]
        for team in (home, away):
            if team not in standings:
                standings[team] = {"pts": 0, "gf": 0, "ga": 0, "mp": 0}

        table = sorted(
            standings.items(),
            key=lambda x: (-x[1]["pts"], -(x[1]["gf"] - x[1]["ga"]), -x[1]["gf"]),
        )
        pos_map = {t: i + 1 for i, (t, _) in enumerate(table)}
        n = len(table)
        top4_pts = table[min(3, n - 1)][1]["pts"] if n >= 4 else 0
        rel_pts  = table[max(n - 4, 0)][1]["pts"] if n >= 4 else 0

        h, a = standings[home], standings[away]
        rows.append({
            "idx":               idx,
            "home_table_pos":    pos_map[home],
            "away_table_pos":    pos_map[away],
            "home_cumul_pts":    h["pts"],
            "away_cumul_pts":    a["pts"],
            "home_cumul_gd":     h["gf"] - h["ga"],
            "away_cumul_gd":     a["gf"] - a["ga"],
            "home_cumul_mp":     h["mp"],
            "away_cumul_mp":     a["mp"],
            "table_pos_diff":    pos_map[home] - pos_map[away],
            "home_pts_gap_top4": h["pts"] - top4_pts,
            "away_pts_gap_top4": a["pts"] - top4_pts,
            "home_pts_gap_rel":  h["pts"] - rel_pts,
            "away_pts_gap_rel":  a["pts"] - rel_pts,
            "n_teams":           n,
        })

        if pd.notna(row.get("home_goals")) and pd.notna(row.get("away_goals")):
            hg, ag = int(row["home_goals"]), int(row["away_goals"])
            standings[home]["gf"] += hg
            standings[home]["ga"] += ag
            standings[home]["mp"] += 1
            standings[away]["gf"] += ag
            standings[away]["ga"] += hg
            standings[away]["mp"] += 1
            if hg > ag:
                standings[home]["pts"] += 3
            elif hg == ag:
                standings[home]["pts"] += 1
                standings[away]["pts"] += 1
            else:
                standings[away]["pts"] += 3

    return pd.DataFrame(rows).set_index("idx")


def _compute_table_positions(df: pd.DataFrame) -> pd.DataFrame:
    """Compute pre-match table positions for all league-seasons.

    Args:
        df: Full match DataFrame (all leagues + seasons).

    Returns:
        DataFrame with table features indexed by original df index.
    """
    parts = [
        _table_for_season(grp)
        for _, grp in df.groupby(["league", "season"])
    ]
    return pd.concat(parts).sort_index()


def _add_diff_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add home-minus-away diff features for xG rolling and table.

    Args:
        df: DataFrame with home and away rolling features already joined.

    Returns:
        df with diff columns appended in-place.
    """
    for n in _XG_WINDOWS:
        df[f"diff_xg_for_roll{n}"] = (
            df[f"home_xg_for_roll{n}"] - df[f"away_xg_for_roll{n}"]
        )
        df[f"diff_xg_against_roll{n}"] = (
            df[f"home_xg_against_roll{n}"] - df[f"away_xg_against_roll{n}"]
        )
    df["diff_cumul_pts"]  = df["home_cumul_pts"]  - df["away_cumul_pts"]
    df["diff_cumul_gd"]   = df["home_cumul_gd"]   - df["away_cumul_gd"]
    df["diff_won_last10"] = df["home_won_last10"]  - df["away_won_last10"]
    return df


def add_new_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add table position, xG rolling, venue streaks, and W/D/L last N features.

    All features are pre-match (no leakage): outcomes are shifted one
    match back before rolling windows, and table positions are recorded
    before the match result is applied.

    Args:
        df: Full match DataFrame sorted by date, including upcoming matches.
            Must have a contiguous integer index (0..n-1).

    Returns:
        Copy of df with new feature columns appended.
    """
    logger.info("Adding new features to %d rows", len(df))
    df = df.copy()
    team_log = _build_team_log(df)

    for role in ("home", "away"):
        roll_df  = _rolling_features_for_role(team_log, role)
        venue_df = _venue_streaks_for_role(team_log, role)
        df = df.join(roll_df,  how="left")
        df = df.join(venue_df, how="left")

    table_df = _compute_table_positions(df)
    df = df.join(table_df, how="left")
    df = _add_diff_features(df)
    logger.info("New features added: %d columns total", len(df.columns))
    return df
