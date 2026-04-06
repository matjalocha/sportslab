"""Formation and tactical matchup features for match prediction.

Parses formation strings from tm_games, computes per-team formation
stability, win rates with specific formations, performance against
N-back systems, and per-match tactical matchup features. All rolling
and season-to-date features use shift(1) to prevent lookahead bias.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import structlog

from ml_in_sports.features._shared import ensure_datetime as _ensure_datetime
from ml_in_sports.utils.team_names import normalize_team_name

if TYPE_CHECKING:
    from ml_in_sports.utils.database import FootballDatabase

logger = structlog.get_logger(__name__)

_STABILITY_WINDOWS: list[int] = [5, 10]
_FORMATION_GROUPS: list[str] = ["3back", "4back", "5back"]


# -------------------------------------------------------------------
# Public orchestrator
# -------------------------------------------------------------------

def add_formation_features(
    df: pd.DataFrame,
    db: FootballDatabase | None = None,
    tm_games_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Add all formation and tactical matchup features.

    Joins tm_games formation data to the match DataFrame, then
    computes parsed formation stats, rolling stability, win rates,
    performance vs N-back systems, and matchup features.

    Args:
        df: DataFrame with match-level data (matches table schema).
        db: FootballDatabase instance (used if tm_games_df is None).
        tm_games_df: Pre-loaded tm_games DataFrame (for testing).

    Returns:
        DataFrame with formation feature columns added.
    """
    if df.empty:
        return df.copy()

    tm_games = _load_tm_games(db, tm_games_df)
    if tm_games.empty:
        logger.warning("No tm_games data available for formation features")
        return df.copy()

    result = df.copy()
    result = _ensure_datetime(result)
    merged = _join_formations_to_matches(result, tm_games)
    merged = _add_parsed_formation_columns(merged)

    _build_formation_history(tm_games)
    stability = _compute_formation_stability(
        tm_games, windows=_STABILITY_WINDOWS,
    )
    win_rate_formation = _compute_win_rate_current_formation(tm_games)
    win_rate_nback = _compute_win_rate_vs_nback(tm_games)
    goals_nback = _compute_goals_scored_vs_nback(tm_games)

    merged = _assign_team_features(
        merged, tm_games, stability,
        win_rate_formation, win_rate_nback, goals_nback,
    )
    merged = _compute_matchup_features(merged)

    new_cols = len(merged.columns) - len(df.columns)
    logger.info("Added %d formation feature columns", new_cols)
    return merged


# -------------------------------------------------------------------
# Data loading
# -------------------------------------------------------------------

def _load_tm_games(
    db: object | None,
    tm_games_df: pd.DataFrame | None,
) -> pd.DataFrame:
    """Load tm_games from database or use pre-loaded DataFrame.

    Args:
        db: FootballDatabase instance.
        tm_games_df: Pre-loaded DataFrame.

    Returns:
        tm_games DataFrame.
    """
    if tm_games_df is not None:
        return tm_games_df.copy()
    if db is not None:
        return db.read_table("tm_games")  # type: ignore[attr-defined,no-any-return]
    return pd.DataFrame()


# -------------------------------------------------------------------
# Formation parsing
# -------------------------------------------------------------------

def parse_formation(formation: object) -> dict[str, object]:
    """Parse a formation string into structured components.

    Extracts the number of defenders, midfielders, and forwards
    from formation strings like '4-2-3-1', '3-5-2 flat',
    '4-3-3 Attacking', '4-4-2 double 6'.

    Args:
        formation: Formation string or None/NaN.

    Returns:
        Dict with num_defenders, num_midfielders, num_forwards,
        and formation_group keys.
    """
    empty_result: dict[str, object] = {
        "num_defenders": np.nan,
        "num_midfielders": np.nan,
        "num_forwards": np.nan,
        "formation_group": None,
    }
    if not _is_valid_formation(formation):
        return empty_result

    numbers = _extract_formation_numbers(str(formation))
    if len(numbers) < 3:
        return empty_result

    defenders = numbers[0]
    forwards = numbers[-1]
    midfielders = sum(numbers[1:-1])
    group = _classify_formation_group(defenders)

    return {
        "num_defenders": defenders,
        "num_midfielders": midfielders,
        "num_forwards": forwards,
        "formation_group": group,
    }


def _is_valid_formation(formation: object) -> bool:
    """Check if a formation value is non-null and non-empty.

    Args:
        formation: Value to check.

    Returns:
        True if the formation is a valid non-empty string.
    """
    if formation is None:
        return False
    if isinstance(formation, float) and np.isnan(formation):
        return False
    return str(formation).strip() != ""


def _extract_formation_numbers(formation_str: str) -> list[int]:
    """Extract the numeric parts from a formation string.

    Args:
        formation_str: Formation like '4-2-3-1' or '3-5-2 flat'.

    Returns:
        List of integers from the formation pattern.
    """
    return [int(x) for x in re.findall(r"\d+", formation_str.split(" ")[0])]


def _classify_formation_group(num_defenders: int) -> str:
    """Classify a formation into its N-back group.

    Args:
        num_defenders: Number of defenders.

    Returns:
        Formation group string like '3-back', '4-back', '5-back'.
    """
    return f"{num_defenders}-back"


# -------------------------------------------------------------------
# Join tm_games to matches
# -------------------------------------------------------------------

def _join_formations_to_matches(
    df: pd.DataFrame,
    tm_games: pd.DataFrame,
) -> pd.DataFrame:
    """Join formation data from tm_games to the matches DataFrame.

    Uses normalized team names and date to match rows between
    the two tables.

    Args:
        df: Match DataFrame with home_team, away_team, date.
        tm_games: Transfermarkt games with formation columns.

    Returns:
        DataFrame with formation columns joined.
    """
    tm = tm_games.copy()
    tm["date"] = pd.to_datetime(tm["date"])
    tm["home_norm"] = tm["home_club_name"].apply(normalize_team_name)
    tm["away_norm"] = tm["away_club_name"].apply(normalize_team_name)

    result = df.copy()
    result["_date_str"] = result["date"].dt.strftime("%Y-%m-%d")
    tm["_date_str"] = tm["date"].dt.strftime("%Y-%m-%d")

    lookup = _build_formation_lookup(tm)
    result = _apply_formation_lookup(result, lookup)
    result = result.drop(columns=["_date_str"])
    return result


def _build_formation_lookup(
    tm: pd.DataFrame,
) -> dict[tuple[str, str, str], tuple[str, str]]:
    """Build a lookup dict from (date, home, away) to formations.

    Args:
        tm: Prepared tm_games DataFrame with normalized names.

    Returns:
        Dict mapping (date_str, home_norm, away_norm) to
        (home_formation, away_formation).
    """
    lookup: dict[tuple[str, str, str], tuple[str, str]] = {}
    for _, row in tm.iterrows():
        key = (row["_date_str"], row["home_norm"], row["away_norm"])
        home_f = row.get("home_club_formation")
        away_f = row.get("away_club_formation")
        lookup[key] = (str(home_f) if home_f is not None else "", str(away_f) if away_f is not None else "")
    return lookup


def _apply_formation_lookup(
    df: pd.DataFrame,
    lookup: dict[tuple[str, str, str], tuple[str, str]],
) -> pd.DataFrame:
    """Apply formation lookup to match rows.

    Args:
        df: Match DataFrame with _date_str, home_team, away_team.
        lookup: Formation lookup dict.

    Returns:
        DataFrame with home_formation and away_formation columns.
    """
    home_formations: list[str | None] = []
    away_formations: list[str | None] = []

    for _, row in df.iterrows():
        key = (row["_date_str"], row["home_team"], row["away_team"])
        if key in lookup:
            home_f, away_f = lookup[key]
            home_formations.append(home_f)
            away_formations.append(away_f)
        else:
            home_formations.append(None)
            away_formations.append(None)

    df["home_formation"] = home_formations
    df["away_formation"] = away_formations
    return df


# -------------------------------------------------------------------
# Add parsed formation columns to match DataFrame
# -------------------------------------------------------------------

def _add_parsed_formation_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add parsed formation columns for home and away teams.

    Args:
        df: DataFrame with home_formation and away_formation columns.

    Returns:
        DataFrame with num_defenders, num_midfielders, num_forwards,
        and formation_group columns for both home and away.
    """
    for venue in ["home", "away"]:
        parsed = df[f"{venue}_formation"].apply(parse_formation)
        parsed_df = pd.DataFrame(parsed.tolist(), index=df.index)
        df[f"{venue}_num_defenders"] = parsed_df["num_defenders"]
        df[f"{venue}_num_midfielders"] = parsed_df["num_midfielders"]
        df[f"{venue}_num_forwards"] = parsed_df["num_forwards"]
        df[f"{venue}_formation_group"] = parsed_df["formation_group"]
    return df


# -------------------------------------------------------------------
# Build per-team formation history from tm_games
# -------------------------------------------------------------------

def _build_formation_history(
    tm_games: pd.DataFrame,
) -> pd.DataFrame:
    """Build unified per-team match history from tm_games.

    Each match generates two rows: one for each team, with
    the team's formation, goals scored/conceded, and the
    opponent's formation group.

    Args:
        tm_games: Transfermarkt games DataFrame.

    Returns:
        DataFrame with team, date, season, formation,
        goals_scored, goals_conceded, opponent_group columns.
    """
    home = _extract_tm_home_records(tm_games)
    away = _extract_tm_away_records(tm_games)
    history = pd.concat([home, away], ignore_index=True)
    history["date"] = pd.to_datetime(history["date"])
    return history.sort_values("date").reset_index(drop=True)


def _extract_tm_home_records(tm_games: pd.DataFrame) -> pd.DataFrame:
    """Extract per-team records from the home perspective.

    Args:
        tm_games: Transfermarkt games DataFrame.

    Returns:
        DataFrame with team-level records for home teams.
    """
    opp_group = tm_games["away_club_formation"].apply(
        lambda f: parse_formation(f)["formation_group"],  # type: ignore[arg-type,return-value]
    )
    won = (
        tm_games["home_club_goals"] > tm_games["away_club_goals"]
    ).astype(float)
    return pd.DataFrame({
        "game_id": tm_games["game_id"].values,
        "team": tm_games["home_club_name"].values,
        "date": tm_games["date"].values,
        "season": tm_games["season"].values,
        "formation": tm_games["home_club_formation"].values,
        "goals_scored": tm_games["home_club_goals"].values,
        "goals_conceded": tm_games["away_club_goals"].values,
        "won": won.values,
        "opponent_group": opp_group.values,
    })


def _extract_tm_away_records(tm_games: pd.DataFrame) -> pd.DataFrame:
    """Extract per-team records from the away perspective.

    Args:
        tm_games: Transfermarkt games DataFrame.

    Returns:
        DataFrame with team-level records for away teams.
    """
    opp_group = tm_games["home_club_formation"].apply(
        lambda f: parse_formation(f)["formation_group"],  # type: ignore[arg-type,return-value]
    )
    won = (
        tm_games["away_club_goals"] > tm_games["home_club_goals"]
    ).astype(float)
    return pd.DataFrame({
        "game_id": tm_games["game_id"].values,
        "team": tm_games["away_club_name"].values,
        "date": tm_games["date"].values,
        "season": tm_games["season"].values,
        "formation": tm_games["away_club_formation"].values,
        "goals_scored": tm_games["away_club_goals"].values,
        "goals_conceded": tm_games["home_club_goals"].values,
        "won": won.values,
        "opponent_group": opp_group.values,
    })


# -------------------------------------------------------------------
# Formation stability (rolling)
# -------------------------------------------------------------------

def _compute_formation_stability(
    tm_games: pd.DataFrame,
    windows: list[int],
) -> pd.DataFrame:
    """Compute formation stability per team.

    Stability is the proportion of last N matches where the team
    used the same formation as the current match. Uses shift(1)
    to prevent lookahead.

    Args:
        tm_games: Transfermarkt games DataFrame.
        windows: Rolling window sizes (e.g. [5, 10]).

    Returns:
        DataFrame with team, date, game_id, and stability columns.
    """
    history = _build_formation_history(tm_games)
    result_frames: list[pd.DataFrame] = []

    for (_team, _season), group in history.groupby(["team", "season"]):
        sorted_group = group.sort_values("date").reset_index(drop=True)
        row_data = sorted_group[["team", "date", "game_id"]].copy()
        for window in windows:
            col = f"formation_stability_{window}"
            row_data[col] = _rolling_stability(
                sorted_group["formation"], window,
            )
        result_frames.append(row_data)

    if not result_frames:
        return pd.DataFrame()
    return pd.concat(result_frames, ignore_index=True)


def _rolling_stability(
    formations: pd.Series,
    window: int,
) -> pd.Series:
    """Compute rolling formation stability with shift(1).

    For each row, looks at the previous N formations and counts
    how many match the current formation.

    Args:
        formations: Series of formation strings.
        window: Number of past matches to consider.

    Returns:
        Series of stability proportions.
    """
    stability = pd.Series(np.nan, index=formations.index)
    for i in range(len(formations)):
        if i < 1:
            continue
        current = formations.iloc[i]
        if not _is_valid_formation(current):
            continue
        start = max(0, i - window)
        past = formations.iloc[start:i]
        if len(past) < window:
            continue
        matches = (past == current).sum()
        stability.iloc[i] = matches / len(past)
    return stability


# -------------------------------------------------------------------
# Win rate with current formation (STD)
# -------------------------------------------------------------------

def _compute_win_rate_current_formation(
    tm_games: pd.DataFrame,
) -> pd.DataFrame:
    """Compute season-to-date win rate when using current formation.

    For each match, computes the expanding win rate using only
    prior matches where the team used the same formation.

    Args:
        tm_games: Transfermarkt games DataFrame.

    Returns:
        DataFrame with team, date, game_id,
        and win_rate_current_formation_std columns.
    """
    history = _build_formation_history(tm_games)
    result_frames: list[pd.DataFrame] = []

    for (_team, _season), group in history.groupby(["team", "season"]):
        sorted_group = group.sort_values("date").reset_index(drop=True)
        row_data = sorted_group[["team", "date", "game_id"]].copy()
        row_data["win_rate_current_formation_std"] = (
            _expanding_win_rate_by_formation(sorted_group)
        )
        result_frames.append(row_data)

    if not result_frames:
        return pd.DataFrame()
    return pd.concat(result_frames, ignore_index=True)


def _expanding_win_rate_by_formation(group: pd.DataFrame) -> pd.Series:
    """Compute expanding win rate filtered by current formation.

    Args:
        group: Sorted team-season history DataFrame.

    Returns:
        Series of win rate values (NaN for insufficient data).
    """
    win_rate = pd.Series(np.nan, index=group.index)
    for i in range(1, len(group)):
        current_formation = group["formation"].iloc[i]
        if not _is_valid_formation(current_formation):
            continue
        prior = group.iloc[:i]
        same_formation = prior[prior["formation"] == current_formation]
        if same_formation.empty:
            continue
        win_rate.iloc[i] = same_formation["won"].mean()
    return win_rate


# -------------------------------------------------------------------
# Performance vs N-back systems (STD)
# -------------------------------------------------------------------

def _compute_win_rate_vs_nback(
    tm_games: pd.DataFrame,
) -> pd.DataFrame:
    """Compute season-to-date win rate vs 3/4/5-back systems.

    Args:
        tm_games: Transfermarkt games DataFrame.

    Returns:
        DataFrame with team, date, game_id, and win_rate_vs_*
        columns.
    """
    history = _build_formation_history(tm_games)
    result_frames: list[pd.DataFrame] = []

    for (_team, _season), group in history.groupby(["team", "season"]):
        sorted_group = group.sort_values("date").reset_index(drop=True)
        row_data = sorted_group[["team", "date", "game_id"]].copy()
        for back_group in _FORMATION_GROUPS:
            col = f"win_rate_vs_{back_group}_std"
            row_data[col] = _expanding_rate_vs_group(
                sorted_group, back_group, "won",
            )
        result_frames.append(row_data)

    if not result_frames:
        return pd.DataFrame()
    return pd.concat(result_frames, ignore_index=True)


def _compute_goals_scored_vs_nback(
    tm_games: pd.DataFrame,
) -> pd.DataFrame:
    """Compute season-to-date goals scored vs 3/4/5-back systems.

    Args:
        tm_games: Transfermarkt games DataFrame.

    Returns:
        DataFrame with team, date, game_id, and goals_scored_vs_*
        columns.
    """
    history = _build_formation_history(tm_games)
    result_frames: list[pd.DataFrame] = []

    for (_team, _season), group in history.groupby(["team", "season"]):
        sorted_group = group.sort_values("date").reset_index(drop=True)
        row_data = sorted_group[["team", "date", "game_id"]].copy()
        for back_group in _FORMATION_GROUPS:
            col = f"goals_scored_vs_{back_group}_std"
            row_data[col] = _expanding_rate_vs_group(
                sorted_group, back_group, "goals_scored",
            )
        result_frames.append(row_data)

    if not result_frames:
        return pd.DataFrame()
    return pd.concat(result_frames, ignore_index=True)


def _expanding_rate_vs_group(
    group: pd.DataFrame,
    back_group: str,
    stat_col: str,
) -> pd.Series:
    """Compute expanding mean of a stat vs a specific formation group.

    Uses shift(1) logic: for row i, only uses data from rows 0..i-1
    where the opponent used the specified formation group.

    Args:
        group: Sorted team-season history DataFrame.
        back_group: Formation group to filter by (e.g. '3back').
        stat_col: Column to compute mean for ('won', 'goals_scored').

    Returns:
        Series of expanding mean values.
    """
    target_group = back_group.replace("back", "-back")
    result = pd.Series(np.nan, index=group.index)

    for i in range(1, len(group)):
        prior = group.iloc[:i]
        vs_group = prior[prior["opponent_group"] == target_group]
        if vs_group.empty:
            continue
        result.iloc[i] = vs_group[stat_col].mean()

    return result


# -------------------------------------------------------------------
# Matchup features (per match)
# -------------------------------------------------------------------

def _compute_matchup_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-match tactical matchup features.

    Args:
        df: DataFrame with home/away num_defenders, num_midfielders,
            num_forwards columns.

    Returns:
        DataFrame with defender_mismatch and midfield_dominance.
    """
    result = df.copy()
    result["defender_mismatch"] = (
        result["home_num_forwards"] - result["away_num_defenders"]
    )
    result["midfield_dominance"] = (
        result["home_num_midfielders"] - result["away_num_midfielders"]
    )
    return result


# -------------------------------------------------------------------
# Assign team-level features to match rows
# -------------------------------------------------------------------

def _assign_team_features(
    df: pd.DataFrame,
    tm_games: pd.DataFrame,
    stability: pd.DataFrame,
    win_rate_formation: pd.DataFrame,
    win_rate_nback: pd.DataFrame,
    goals_nback: pd.DataFrame,
) -> pd.DataFrame:
    """Assign team-level features to the match DataFrame.

    Maps features computed on the tm_games timeline back to the
    match rows, using normalized team names and date for matching.

    Args:
        df: Match DataFrame with formations joined.
        tm_games: Transfermarkt games DataFrame.
        stability: Formation stability DataFrame.
        win_rate_formation: Win rate with current formation DataFrame.
        win_rate_nback: Win rate vs N-back DataFrame.
        goals_nback: Goals scored vs N-back DataFrame.

    Returns:
        DataFrame with all team-level formation features assigned.
    """
    tm = tm_games.copy()
    tm["date"] = pd.to_datetime(tm["date"])

    feature_dfs = _merge_feature_tables(
        stability, win_rate_formation, win_rate_nback, goals_nback,
    )
    if feature_dfs.empty:
        return df

    tm["home_norm"] = tm["home_club_name"].apply(normalize_team_name)
    tm["away_norm"] = tm["away_club_name"].apply(normalize_team_name)

    lookup = _build_feature_lookup(tm, feature_dfs)
    df = _apply_feature_lookup(df, lookup)
    return df


def _merge_feature_tables(
    stability: pd.DataFrame,
    win_rate_formation: pd.DataFrame,
    win_rate_nback: pd.DataFrame,
    goals_nback: pd.DataFrame,
) -> pd.DataFrame:
    """Merge all team-level feature tables into one.

    Args:
        stability: Formation stability features.
        win_rate_formation: Win rate with current formation features.
        win_rate_nback: Win rate vs N-back features.
        goals_nback: Goals scored vs N-back features.

    Returns:
        Merged DataFrame with all features keyed by team/date/game_id.
    """
    if stability.empty:
        return pd.DataFrame()

    merge_keys = ["team", "date", "game_id"]
    merged = stability.copy()

    for feature_df in [win_rate_formation, win_rate_nback, goals_nback]:
        if not feature_df.empty:
            extra_cols = [
                c for c in feature_df.columns if c not in merge_keys
            ]
            merged = merged.merge(
                feature_df[merge_keys + extra_cols],
                on=merge_keys,
                how="left",
            )

    return merged


def _build_feature_lookup(
    tm: pd.DataFrame,
    features: pd.DataFrame,
) -> dict[tuple[str, str], dict[str, float]]:
    """Build a lookup from (date_str, team_norm) to feature values.

    Args:
        tm: Prepared tm_games with normalized names.
        features: Merged team-level feature DataFrame.

    Returns:
        Dict mapping (date_str, team_name) to a dict of feature values.
    """
    feature_cols = [
        c for c in features.columns
        if c not in ["team", "date", "game_id"]
    ]
    lookup: dict[tuple[str, str], dict[str, float]] = {}

    for _, row in features.iterrows():
        team = row["team"]
        norm_name = normalize_team_name(team)
        date_str = pd.to_datetime(row["date"]).strftime("%Y-%m-%d")
        key = (date_str, norm_name)
        lookup[key] = {col: row[col] for col in feature_cols}

    return lookup


def _apply_feature_lookup(
    df: pd.DataFrame,
    lookup: dict[tuple[str, str], dict[str, float]],
) -> pd.DataFrame:
    """Apply feature lookup to assign team features to match rows.

    Args:
        df: Match DataFrame.
        lookup: Feature lookup dict.

    Returns:
        DataFrame with home_* and away_* feature columns added.
    """
    if not lookup:
        return df

    sample_features = next(iter(lookup.values()))
    feature_names = list(sample_features.keys())

    for venue in ["home", "away"]:
        team_col = f"{venue}_team"
        for feat_name in feature_names:
            col_name = f"{venue}_{feat_name}"
            values: list[float] = []
            for _, row in df.iterrows():
                date_str = row["date"].strftime("%Y-%m-%d")
                key = (date_str, row[team_col])
                if key in lookup and feat_name in lookup[key]:
                    values.append(lookup[key][feat_name])
                else:
                    values.append(np.nan)
            df[col_name] = values

    return df
