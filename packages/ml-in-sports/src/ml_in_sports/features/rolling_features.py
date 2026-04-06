"""Advanced per-team rolling features for match prediction.

Tracks team performance across all matches (home and away),
computes rolling statistics with configurable windows, and
handles season boundary resets. All features use shift(1) to
prevent lookahead bias.
"""

import pandas as pd
import structlog

from ml_in_sports.features._shared import compute_match_points as _compute_match_points

logger = structlog.get_logger(__name__)

_DEFAULT_WINDOWS: list[int] = [3, 5, 10]

_TEAM_STATS: list[str] = [
    "goals_scored",
    "goals_conceded",
    "xg_for",
    "xg_against",
    "shots_on_target",
    "points",
    "clean_sheets",
]


def add_rolling_features(
    df: pd.DataFrame,
    windows: list[int] | None = None,
    include_season_to_date: bool = True,
) -> pd.DataFrame:
    """Add all advanced rolling features to a match DataFrame.

    Combines per-team rolling stats, home/away splits, elo form,
    and season-to-date aggregates.

    Args:
        df: DataFrame with match-level data including date, teams, goals.
        windows: Rolling window sizes (default: [3, 5, 10]).
        include_season_to_date: Whether to add season-to-date features.

    Returns:
        DataFrame with rolling feature columns added.
    """
    if df.empty:
        return df.copy()

    if windows is None:
        windows = _DEFAULT_WINDOWS

    result = df.copy()
    result = result.sort_values("date").reset_index(drop=True)
    result = compute_team_rolling_features(
        result, windows, include_season_to_date,
    )
    result = compute_home_away_split_features(result, windows)
    result = compute_elo_form(result, windows)

    logger.info(
        "Added rolling features: %d new columns",
        len(result.columns) - len(df.columns),
    )
    return result


def compute_team_rolling_features(
    df: pd.DataFrame,
    windows: list[int],
    include_season_to_date: bool = False,
) -> pd.DataFrame:
    """Compute rolling stats per team across all their matches.

    For each team, builds a chronological match history combining
    home and away appearances, then computes rolling means.

    Args:
        df: Match DataFrame sorted by date.
        windows: Rolling window sizes.
        include_season_to_date: Whether to add STD features.

    Returns:
        DataFrame with per-team rolling feature columns.
    """
    result = df.copy()
    histories = _build_team_histories(result)

    for stat_name in _TEAM_STATS:
        if stat_name not in histories.columns:
            continue
        rolled = _roll_stat_all_teams(histories, stat_name, windows)
        result = _assign_rolled_to_matches(result, rolled, stat_name)

    if include_season_to_date:
        std_rolled = _compute_season_to_date(histories)
        result = _assign_rolled_to_matches(
            result, std_rolled, "goals_scored_std",
        )

    return result


def _build_team_histories(df: pd.DataFrame) -> pd.DataFrame:
    """Build a unified per-team match history from home/away rows.

    Each match generates two rows: one for the home team and one
    for the away team, with stats normalized to the team's perspective.

    Args:
        df: Match DataFrame with home/away columns.

    Returns:
        DataFrame with one row per team per match, sorted by date.
    """
    home_records = _extract_home_records(df)
    away_records = _extract_away_records(df)
    history = pd.concat([home_records, away_records], ignore_index=True)
    return history.sort_values("date").reset_index(drop=True)


def _extract_home_records(df: pd.DataFrame) -> pd.DataFrame:
    """Extract team records from the home team perspective.

    Args:
        df: Match DataFrame.

    Returns:
        DataFrame with normalized team stats for home teams.
    """
    records = pd.DataFrame({
        "match_idx": df.index,
        "date": df["date"].values,
        "season": df["season"].values,
        "team": df["home_team"].values,
        "venue": "home",
        "goals_scored": df["home_goals"].values,
        "goals_conceded": df["away_goals"].values,
    })
    records["points"] = _compute_match_points(
        df["home_goals"], df["away_goals"],
    ).values
    records["clean_sheets"] = (df["away_goals"] == 0).astype(float).values
    records = _add_optional_stat(records, df, "xg_for", "home_xg")
    records = _add_optional_stat(records, df, "xg_against", "away_xg")
    records = _add_optional_stat(
        records, df, "shots_on_target", "home_shots_on_target",
    )
    records = _add_optional_stat(records, df, "elo", "home_elo")
    return records


def _extract_away_records(df: pd.DataFrame) -> pd.DataFrame:
    """Extract team records from the away team perspective.

    Args:
        df: Match DataFrame.

    Returns:
        DataFrame with normalized team stats for away teams.
    """
    records = pd.DataFrame({
        "match_idx": df.index,
        "date": df["date"].values,
        "season": df["season"].values,
        "team": df["away_team"].values,
        "venue": "away",
        "goals_scored": df["away_goals"].values,
        "goals_conceded": df["home_goals"].values,
    })
    records["points"] = _compute_match_points(
        df["away_goals"], df["home_goals"],
    ).values
    records["clean_sheets"] = (df["home_goals"] == 0).astype(float).values
    records = _add_optional_stat(records, df, "xg_for", "away_xg")
    records = _add_optional_stat(records, df, "xg_against", "home_xg")
    records = _add_optional_stat(
        records, df, "shots_on_target", "away_shots_on_target",
    )
    records = _add_optional_stat(records, df, "elo", "away_elo")
    return records


def _add_optional_stat(
    records: pd.DataFrame,
    source: pd.DataFrame,
    target_col: str,
    source_col: str,
) -> pd.DataFrame:
    """Add a column from source to records if it exists.

    Args:
        records: Target DataFrame to add the column to.
        source: Source DataFrame that may contain the column.
        target_col: Name for the new column in records.
        source_col: Name of the column in source.

    Returns:
        Records DataFrame with optional column added.
    """
    if source_col in source.columns:
        records[target_col] = source[source_col].values
    return records


def _roll_stat_all_teams(
    histories: pd.DataFrame,
    stat_name: str,
    windows: list[int],
) -> pd.DataFrame:
    """Compute rolling means for a stat across all team-season groups.

    Args:
        histories: Per-team match history with match_idx and venue.
        stat_name: Column name to roll.
        windows: Window sizes.

    Returns:
        DataFrame with match_idx, venue, and rolling columns.
    """
    result_frames: list[pd.DataFrame] = []
    for (_team, _season), group in histories.groupby(["team", "season"]):
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

    Uses direct index-based assignment instead of merge to
    avoid duplicate-row issues.

    Args:
        df: Match DataFrame (index = 0..N-1).
        rolled: Rolled DataFrame with match_idx and venue columns.
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


def _compute_season_to_date(
    histories: pd.DataFrame,
) -> pd.DataFrame:
    """Compute expanding (season-to-date) mean for goals scored.

    Uses all prior matches in the current season (no fixed window).

    Args:
        histories: Per-team match history.

    Returns:
        DataFrame with match_idx, venue, and STD column.
    """
    result_frames: list[pd.DataFrame] = []
    for (_team, _season), group in histories.groupby(["team", "season"]):
        std_row = group[["match_idx", "venue"]].copy()
        shifted = group["goals_scored"].shift(1)
        std_row["rolling_goals_scored_std"] = shifted.expanding(
            min_periods=1,
        ).mean()
        result_frames.append(std_row)

    if not result_frames:
        return pd.DataFrame()
    return pd.concat(result_frames, ignore_index=True)


def compute_home_away_split_features(
    df: pd.DataFrame,
    windows: list[int],
) -> pd.DataFrame:
    """Compute rolling features using only home or away matches.

    Tracks home form (performance in home matches only) and
    away form (performance in away matches only).

    Args:
        df: Match DataFrame sorted by date.
        windows: Rolling window sizes.

    Returns:
        DataFrame with home_form_* and away_form_* columns.
    """
    result = df.copy()
    result = _compute_venue_split(result, "home", "goals_scored", windows)
    result = _compute_venue_split(result, "home", "goals_conceded", windows)
    result = _compute_venue_split(result, "away", "goals_scored", windows)
    result = _compute_venue_split(result, "away", "goals_conceded", windows)
    return result


def _compute_venue_split(
    df: pd.DataFrame,
    venue: str,
    stat_name: str,
    windows: list[int],
) -> pd.DataFrame:
    """Compute rolling stats using only matches at a specific venue.

    Args:
        df: Match DataFrame.
        venue: "home" or "away".
        stat_name: Stat to compute (goals_scored, goals_conceded).
        windows: Window sizes.

    Returns:
        DataFrame with venue-specific form columns added.
    """
    team_col = f"{venue}_team"
    stat_col = _get_venue_stat_column(venue, stat_name)

    if stat_col not in df.columns:
        return df

    result_frames: list[pd.DataFrame] = []
    season_col = "season" if "season" in df.columns else None
    group_keys = [team_col]
    if season_col:
        group_keys.append(season_col)

    for _keys, group in df.groupby(group_keys):
        group_sorted = group.sort_values("date")
        shifted = group_sorted[stat_col].shift(1)
        row_data = pd.DataFrame({"orig_idx": group_sorted.index})
        for window in windows:
            col_name = f"{venue}_form_{stat_name}_{window}"
            row_data[col_name] = shifted.rolling(
                window=window, min_periods=window,
            ).mean().values
        result_frames.append(row_data)

    if not result_frames:
        return df

    merged = pd.concat(result_frames, ignore_index=True)
    form_cols = [c for c in merged.columns if c != "orig_idx"]
    for col in form_cols:
        df[col] = merged.set_index("orig_idx").reindex(df.index)[col]
    return df


def _get_venue_stat_column(venue: str, stat_name: str) -> str:
    """Map stat name to the correct DataFrame column for a venue.

    Args:
        venue: "home" or "away".
        stat_name: Logical stat name (goals_scored, goals_conceded).

    Returns:
        Column name in the match DataFrame.
    """
    mapping = {
        ("home", "goals_scored"): "home_goals",
        ("home", "goals_conceded"): "away_goals",
        ("away", "goals_scored"): "away_goals",
        ("away", "goals_conceded"): "home_goals",
    }
    return mapping.get((venue, stat_name), "")


def compute_elo_form(
    df: pd.DataFrame,
    windows: list[int],
) -> pd.DataFrame:
    """Compute rolling elo change (form) per team.

    Tracks how much a team's elo has changed over recent matches.

    Args:
        df: Match DataFrame with home_elo and away_elo columns.
        windows: Rolling window sizes.

    Returns:
        DataFrame with home_elo_form_* and away_elo_form_* columns.
    """
    if "home_elo" not in df.columns or "away_elo" not in df.columns:
        return df.copy()

    result = df.copy()
    histories = _build_team_histories(result)

    if "elo" not in histories.columns:
        return result

    rolled = _roll_elo_diffs(histories, windows)
    result = _assign_elo_form_to_matches(result, rolled, windows)
    return result


def _roll_elo_diffs(
    histories: pd.DataFrame,
    windows: list[int],
) -> pd.DataFrame:
    """Compute rolling mean of elo changes per team-season.

    Args:
        histories: Per-team match history with elo column.
        windows: Rolling window sizes.

    Returns:
        DataFrame with match_idx, venue, and elo_form columns.
    """
    result_frames: list[pd.DataFrame] = []
    for (_team, _season), group in histories.groupby(["team", "season"]):
        row = group[["match_idx", "venue"]].copy()
        elo_diff = group["elo"].diff()
        shifted = elo_diff.shift(1)
        for window in windows:
            col = f"elo_form_{window}"
            row[col] = shifted.rolling(
                window=window, min_periods=window,
            ).mean()
        result_frames.append(row)

    if not result_frames:
        return pd.DataFrame()
    return pd.concat(result_frames, ignore_index=True)


def _assign_elo_form_to_matches(
    df: pd.DataFrame,
    rolled: pd.DataFrame,
    windows: list[int],
) -> pd.DataFrame:
    """Assign rolled elo form values to match rows.

    Args:
        df: Match DataFrame.
        rolled: Rolled elo form DataFrame.
        windows: Window sizes used.

    Returns:
        DataFrame with home_elo_form_* and away_elo_form_* columns.
    """
    elo_cols = [f"elo_form_{w}" for w in windows]

    for venue in ["home", "away"]:
        venue_data = rolled[rolled["venue"] == venue].copy()
        venue_data = venue_data.set_index("match_idx")
        for col in elo_cols:
            if col in venue_data.columns:
                df[f"{venue}_{col}"] = venue_data[col].reindex(df.index)

    return df
