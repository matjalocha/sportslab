"""Contextual features for match prediction.

Computes venue-specific season-to-date stats, fatigue/scheduling
features, and head-to-head historical features. All features use
shift(1) or exclude the current match to prevent lookahead bias.
"""

import numpy as np
import pandas as pd
import structlog

from ml_in_sports.features._shared import (
    compute_match_points as _compute_match_points,
)
from ml_in_sports.features._shared import (
    ensure_datetime as _ensure_datetime,
)

logger = structlog.get_logger(__name__)

_H2H_WINDOWS: list[int] = [5, 10]


# -------------------------------------------------------------------
# Public orchestrator
# -------------------------------------------------------------------

def add_contextual_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add all contextual features to a match DataFrame.

    Combines venue-specific STD, fatigue, and head-to-head features.

    Args:
        df: DataFrame with match-level data including date, teams,
            goals, season columns.

    Returns:
        DataFrame with contextual feature columns added.
    """
    if df.empty:
        return df.copy()

    result = df.copy()
    result = _ensure_datetime(result)
    result = _add_venue_std_features(result)
    result = _add_fatigue_features(result)
    result = _add_h2h_features(result)

    new_cols = len(result.columns) - len(df.columns)
    logger.info("Added %d contextual feature columns", new_cols)
    return result


# -------------------------------------------------------------------
# Venue-specific season-to-date features
# -------------------------------------------------------------------

def _add_venue_std_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add venue-specific season-to-date features.

    Computes expanding means for home-only and away-only stats
    grouped by (team, season). Uses shift(1) to prevent lookahead.

    Args:
        df: Match DataFrame with date, season, teams, goals.

    Returns:
        DataFrame with venue STD columns added.
    """
    if df.empty:
        return df.copy()

    result = df.copy()
    result = _ensure_datetime(result)
    result = _compute_venue_side_std(result, "home")
    result = _compute_venue_side_std(result, "away")
    return result


def _compute_venue_side_std(
    df: pd.DataFrame,
    venue: str,
) -> pd.DataFrame:
    """Compute all venue STD stats for one side (home or away).

    Args:
        df: Match DataFrame sorted by date.
        venue: "home" or "away".

    Returns:
        DataFrame with venue STD columns for the given side.
    """
    team_col = f"{venue}_team"
    goals_for = f"{venue}_goals"
    goals_against = "away_goals" if venue == "home" else "home_goals"

    df = _compute_single_venue_std(
        df, team_col, goals_for, f"{venue}_venue_goals_scored_std",
    )
    df = _compute_single_venue_std(
        df, team_col, goals_against,
        f"{venue}_venue_goals_conceded_std",
    )
    df = _compute_venue_derived_std(df, venue)
    return df


def _compute_single_venue_std(
    df: pd.DataFrame,
    team_col: str,
    stat_col: str,
    target_col: str,
) -> pd.DataFrame:
    """Compute expanding mean for a single stat at a venue.

    Args:
        df: Match DataFrame.
        team_col: Column for team name (home_team or away_team).
        stat_col: Column with the raw stat value.
        target_col: Name for the output column.

    Returns:
        DataFrame with the target column added.
    """
    group_keys = [team_col, "season"]
    df[target_col] = np.nan

    for _keys, group in df.groupby(group_keys):
        sorted_group = group.sort_values("date")
        shifted = sorted_group[stat_col].shift(1)
        expanded = shifted.expanding(min_periods=1).mean()
        df.loc[sorted_group.index, target_col] = expanded.values

    return df


def _compute_venue_derived_std(
    df: pd.DataFrame,
    venue: str,
) -> pd.DataFrame:
    """Compute derived venue STD features (win rate, clean sheets, ppg).

    Args:
        df: Match DataFrame.
        venue: "home" or "away".

    Returns:
        DataFrame with derived venue STD columns.
    """
    team_col = f"{venue}_team"
    goals_for = f"{venue}_goals"
    goals_against = "away_goals" if venue == "home" else "home_goals"

    df = _compute_venue_binary_std(
        df, team_col, goals_for, goals_against,
        f"{venue}_venue_clean_sheets_std", "clean_sheet",
    )
    df = _compute_venue_binary_std(
        df, team_col, goals_for, goals_against,
        f"{venue}_venue_win_rate_std", "win",
    )
    df = _compute_venue_points_std(
        df, team_col, goals_for, goals_against,
        f"{venue}_venue_points_per_game_std",
    )
    return df


def _compute_venue_binary_std(
    df: pd.DataFrame,
    team_col: str,
    goals_for_col: str,
    goals_against_col: str,
    target_col: str,
    stat_type: str,
) -> pd.DataFrame:
    """Compute expanding mean for a binary venue stat.

    Args:
        df: Match DataFrame.
        team_col: Team column name.
        goals_for_col: Goals scored column.
        goals_against_col: Goals conceded column.
        target_col: Output column name.
        stat_type: "clean_sheet" or "win".

    Returns:
        DataFrame with the binary STD column added.
    """
    df[target_col] = np.nan
    group_keys = [team_col, "season"]

    for _keys, group in df.groupby(group_keys):
        sorted_group = group.sort_values("date")
        binary = _compute_binary_stat(
            sorted_group, goals_for_col, goals_against_col, stat_type,
        )
        shifted = binary.shift(1)
        expanded = shifted.expanding(min_periods=1).mean()
        df.loc[sorted_group.index, target_col] = expanded.values

    return df


def _compute_binary_stat(
    group: pd.DataFrame,
    goals_for_col: str,
    goals_against_col: str,
    stat_type: str,
) -> pd.Series:
    """Compute a binary stat series from goals data.

    Args:
        group: Match group DataFrame.
        goals_for_col: Goals scored column.
        goals_against_col: Goals conceded column.
        stat_type: "clean_sheet" or "win".

    Returns:
        Series of 1.0/0.0 values.
    """
    if stat_type == "clean_sheet":
        return (group[goals_against_col] == 0).astype(float)
    return (group[goals_for_col] > group[goals_against_col]).astype(float)


def _compute_venue_points_std(
    df: pd.DataFrame,
    team_col: str,
    goals_for_col: str,
    goals_against_col: str,
    target_col: str,
) -> pd.DataFrame:
    """Compute expanding mean of points at a specific venue.

    Args:
        df: Match DataFrame.
        team_col: Team column name.
        goals_for_col: Goals scored column.
        goals_against_col: Goals conceded column.
        target_col: Output column name.

    Returns:
        DataFrame with points STD column added.
    """
    df[target_col] = np.nan
    group_keys = [team_col, "season"]

    for _keys, group in df.groupby(group_keys):
        sorted_group = group.sort_values("date")
        points = _compute_match_points(
            sorted_group[goals_for_col],
            sorted_group[goals_against_col],
        )
        shifted = points.shift(1)
        expanded = shifted.expanding(min_periods=1).mean()
        df.loc[sorted_group.index, target_col] = expanded.values

    return df


# -------------------------------------------------------------------
# Fatigue features
# -------------------------------------------------------------------

def _add_fatigue_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add fatigue and scheduling features.

    Builds a per-team match timeline and computes days since
    last match and match counts within recent windows.

    Args:
        df: Match DataFrame with date, home_team, away_team.

    Returns:
        DataFrame with fatigue feature columns added.
    """
    if df.empty:
        return df.copy()

    result = df.copy()
    result = _ensure_datetime(result)
    timeline = _build_team_timeline(result)

    result = _assign_days_since_last(result, timeline)
    result = _assign_matches_in_window(result, timeline, 14)
    result = _assign_matches_in_window(result, timeline, 7)
    return result


def _build_team_timeline(df: pd.DataFrame) -> pd.DataFrame:
    """Build a per-team match timeline from home/away rows.

    Each match creates two entries: one for the home team
    and one for the away team.

    Args:
        df: Match DataFrame with date, home_team, away_team.

    Returns:
        DataFrame with team, date, match_idx columns.
    """
    home = pd.DataFrame({
        "team": df["home_team"].values,
        "date": df["date"].values,
        "match_idx": df.index,
        "venue": "home",
    })
    away = pd.DataFrame({
        "team": df["away_team"].values,
        "date": df["date"].values,
        "match_idx": df.index,
        "venue": "away",
    })
    timeline = pd.concat([home, away], ignore_index=True)
    return timeline.sort_values("date").reset_index(drop=True)


def _assign_days_since_last(
    df: pd.DataFrame,
    timeline: pd.DataFrame,
) -> pd.DataFrame:
    """Assign days-since-last-match for home and away teams.

    Args:
        df: Match DataFrame.
        timeline: Per-team match timeline.

    Returns:
        DataFrame with days_since_last columns added.
    """
    days_map = _compute_days_since_last(timeline)
    df = _merge_fatigue_stat(df, days_map, "days_since_last")
    return df


def _compute_days_since_last(
    timeline: pd.DataFrame,
) -> pd.DataFrame:
    """Compute days since previous match for each team entry.

    Args:
        timeline: Per-team match timeline sorted by date.

    Returns:
        DataFrame with match_idx, venue, days_since_last.
    """
    result_frames: list[pd.DataFrame] = []
    for _team, group in timeline.groupby("team"):
        sorted_group = group.sort_values("date")
        days_diff = sorted_group["date"].diff().dt.days  # type: ignore[arg-type]  # pandas-stubs: dt accessor on timedelta Series
        frame = pd.DataFrame({
            "match_idx": sorted_group["match_idx"].values,
            "venue": sorted_group["venue"].values,
            "days_since_last": days_diff.values,
        })
        result_frames.append(frame)

    if not result_frames:
        return pd.DataFrame()
    return pd.concat(result_frames, ignore_index=True)


def _assign_matches_in_window(
    df: pd.DataFrame,
    timeline: pd.DataFrame,
    window_days: int,
) -> pd.DataFrame:
    """Assign match count in a time window for home/away teams.

    Args:
        df: Match DataFrame.
        timeline: Per-team match timeline.
        window_days: Number of days to look back.

    Returns:
        DataFrame with matches_last_{window}d columns added.
    """
    counts = _compute_matches_in_window(timeline, window_days)
    col_name = f"matches_last_{window_days}d"
    df = _merge_fatigue_stat(df, counts, col_name)
    return df


def _compute_matches_in_window(
    timeline: pd.DataFrame,
    window_days: int,
) -> pd.DataFrame:
    """Count matches within a time window for each team entry.

    Counts how many prior matches the team played within
    window_days before the current match (excluding current).

    Args:
        timeline: Per-team match timeline sorted by date.
        window_days: Number of days to look back.

    Returns:
        DataFrame with match_idx, venue, count column.
    """
    col_name = f"matches_last_{window_days}d"
    result_frames: list[pd.DataFrame] = []

    for _team, group in timeline.groupby("team"):
        sorted_group = group.sort_values("date").reset_index(drop=True)
        counts = _count_window_for_group(sorted_group, window_days)
        frame = pd.DataFrame({
            "match_idx": sorted_group["match_idx"].values,
            "venue": sorted_group["venue"].values,
            col_name: counts,
        })
        result_frames.append(frame)

    if not result_frames:
        return pd.DataFrame()
    return pd.concat(result_frames, ignore_index=True)


def _count_window_for_group(
    group: pd.DataFrame,
    window_days: int,
) -> list[int]:
    """Count prior matches within a window for one team group.

    Args:
        group: Sorted team timeline group.
        window_days: Days to look back.

    Returns:
        List of match counts per row.
    """
    dates = group["date"].values
    counts: list[int] = []
    for i in range(len(dates)):
        current_date = dates[i]
        cutoff = current_date - np.timedelta64(window_days, "D")
        prior = dates[:i]
        count = int(((prior >= cutoff) & (prior < current_date)).sum())
        counts.append(count)
    return counts


def _merge_fatigue_stat(
    df: pd.DataFrame,
    stat_df: pd.DataFrame,
    col_name: str,
) -> pd.DataFrame:
    """Merge a fatigue stat back to match rows for both venues.

    Args:
        df: Match DataFrame.
        stat_df: Stat DataFrame with match_idx, venue, stat column.
        col_name: Name of the stat column.

    Returns:
        DataFrame with home_{col} and away_{col} columns.
    """
    if stat_df.empty:
        return df

    for venue in ["home", "away"]:
        venue_data = stat_df[stat_df["venue"] == venue].copy()
        venue_data = venue_data.set_index("match_idx")
        target = f"{venue}_{col_name}"
        if col_name in venue_data.columns:
            df[target] = venue_data[col_name].reindex(df.index)

    return df


# -------------------------------------------------------------------
# Head-to-head features
# -------------------------------------------------------------------

def _add_h2h_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add head-to-head historical features.

    For each match, looks up past meetings between the same
    two teams and computes rolling H2H stats.

    Args:
        df: Match DataFrame with date, home_team, away_team, goals.

    Returns:
        DataFrame with H2H feature columns added.
    """
    if df.empty:
        return df.copy()

    result = df.copy()
    result = _ensure_datetime(result)
    result = result.sort_values("date").reset_index(drop=True)
    h2h_history = _build_h2h_history(result)

    for window in _H2H_WINDOWS:
        result = _compute_h2h_window(result, h2h_history, window)

    return result


def _build_h2h_history(df: pd.DataFrame) -> pd.DataFrame:
    """Build a matchup history keyed by team pair.

    Creates a normalized pair key so Arsenal-Chelsea and
    Chelsea-Arsenal map to the same pair.

    Args:
        df: Match DataFrame sorted by date.

    Returns:
        DataFrame with pair_key, date, match results.
    """
    history = df[
        ["date", "home_team", "away_team", "home_goals", "away_goals"]
    ].copy()
    history["pair_key"] = history.apply(
        _make_pair_key, axis=1,
    )
    history["total_goals"] = (
        history["home_goals"] + history["away_goals"]
    )
    history["btts"] = (
        (history["home_goals"] > 0) & (history["away_goals"] > 0)
    ).astype(float)
    history["home_win"] = (
        history["home_goals"] > history["away_goals"]
    ).astype(float)
    history.index = df.index
    return history


def _make_pair_key(row: pd.Series) -> str:
    """Create a normalized pair key for two teams.

    Args:
        row: DataFrame row with home_team and away_team.

    Returns:
        Alphabetically sorted pair key string.
    """
    teams = sorted([row["home_team"], row["away_team"]])
    return f"{teams[0]}_vs_{teams[1]}"


def _compute_h2h_window(
    df: pd.DataFrame,
    h2h_history: pd.DataFrame,
    window: int,
) -> pd.DataFrame:
    """Compute H2H features for a specific window size.

    Args:
        df: Match DataFrame.
        h2h_history: H2H history with pair keys and stats.
        window: Number of past meetings to consider.

    Returns:
        DataFrame with H2H columns for this window.
    """
    home_wins_col = f"h2h_home_wins_{window}"
    goals_avg_col = f"h2h_goals_avg_{window}"
    btts_rate_col = f"h2h_btts_rate_{window}"
    home_goals_col = f"h2h_home_goals_avg_{window}"

    df[home_wins_col] = np.nan
    df[goals_avg_col] = np.nan
    df[btts_rate_col] = np.nan
    df[home_goals_col] = np.nan

    for idx in df.index:
        row = df.loc[idx]
        pair_key = _make_pair_key(row)
        stats = _get_h2h_stats(
            h2h_history, pair_key, idx,
            row["home_team"], window,
        )
        if stats is not None:
            df.loc[idx, home_wins_col] = stats["home_wins"]
            df.loc[idx, goals_avg_col] = stats["goals_avg"]
            df.loc[idx, btts_rate_col] = stats["btts_rate"]
            df.loc[idx, home_goals_col] = stats["home_goals_avg"]

    return df


def _get_h2h_stats(
    h2h_history: pd.DataFrame,
    pair_key: str,
    current_idx: int,
    current_home_team: str,
    window: int,
) -> dict[str, float] | None:
    """Get H2H stats from past meetings for a single match.

    Args:
        h2h_history: Full H2H history DataFrame.
        pair_key: Normalized pair key.
        current_idx: Index of the current match.
        current_home_team: Home team of the current match.
        window: Number of past meetings to use.

    Returns:
        Dict with H2H stats, or None if insufficient history.
    """
    pair_matches = h2h_history[
        (h2h_history["pair_key"] == pair_key)
        & (h2h_history.index < current_idx)
    ].tail(window)

    if pair_matches.empty:
        return None

    return _aggregate_h2h_stats(pair_matches, current_home_team)


def _aggregate_h2h_stats(
    matches: pd.DataFrame,
    current_home_team: str,
) -> dict[str, float]:
    """Aggregate H2H stats from a set of past meetings.

    Counts wins by the current home team across all past
    meetings, regardless of which venue those meetings were at.

    Args:
        matches: Past meetings between the pair.
        current_home_team: The home team in the current match.

    Returns:
        Dict with home_wins, goals_avg, btts_rate, home_goals_avg.
    """
    home_wins = _count_team_wins(matches, current_home_team)
    goals_avg = matches["total_goals"].mean()
    btts_rate = matches["btts"].mean()
    home_goals_avg = _compute_team_goals_avg(
        matches, current_home_team,
    )
    return {
        "home_wins": home_wins,
        "goals_avg": goals_avg,
        "btts_rate": btts_rate,
        "home_goals_avg": home_goals_avg,
    }


def _count_team_wins(
    matches: pd.DataFrame,
    team: str,
) -> float:
    """Count how many matches a team won in past meetings.

    Args:
        matches: Past H2H meetings.
        team: Team to count wins for.

    Returns:
        Number of wins as float.
    """
    home_mask = matches["home_team"] == team
    away_mask = matches["away_team"] == team

    home_wins = (
        home_mask
        & (matches["home_goals"] > matches["away_goals"])
    ).sum()
    away_wins = (
        away_mask
        & (matches["away_goals"] > matches["home_goals"])
    ).sum()

    return float(home_wins + away_wins)


def _compute_team_goals_avg(
    matches: pd.DataFrame,
    team: str,
) -> float:
    """Compute average goals scored by a team in past meetings.

    Args:
        matches: Past H2H meetings.
        team: Team to compute goals for.

    Returns:
        Average goals scored by the team.
    """
    home_goals = matches.loc[
        matches["home_team"] == team, "home_goals"
    ]
    away_goals = matches.loc[
        matches["away_team"] == team, "away_goals"
    ]
    all_goals = pd.concat([home_goals, away_goals])
    return all_goals.mean() if not all_goals.empty else 0.0
