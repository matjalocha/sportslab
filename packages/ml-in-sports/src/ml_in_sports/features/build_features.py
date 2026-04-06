"""Feature engineering: join raw tables into a model-ready DataFrame.

Reads matches, match_odds, elo_ratings, league_tables from the DB,
joins them into one master DataFrame, adds rolling features and
target variables.
"""

import numpy as np
import pandas as pd
import structlog

from ml_in_sports.utils.database import FootballDatabase

logger = structlog.get_logger(__name__)

ROLLING_STAT_COLUMNS: list[str] = [
    "home_goals", "away_goals", "home_xg", "away_xg",
]

ODDS_JOIN_COLUMNS: list[str] = [
    "b365_home", "b365_draw", "b365_away",
    "avg_home", "avg_draw", "avg_away",
    "b365_over_25", "b365_under_25",
    "avg_over_25", "avg_under_25",
]

LEAGUE_TABLE_COLUMNS: list[str] = [
    "points", "wins", "draws", "losses",
    "goals_for", "goals_against", "goal_difference",
]


def build_master_dataframe(
    league: str,
    season: str,
    db: FootballDatabase,
) -> pd.DataFrame:
    """Join matches, odds, elo, and league tables into one DataFrame.

    Args:
        league: League identifier (e.g. "ENG-Premier League").
        season: Season code (e.g. "2324").
        db: Database instance to read from.

    Returns:
        DataFrame with one row per match, sorted by date.
    """
    matches = db.read_table("matches", league=league, season=season)
    if matches.empty:
        logger.warning(f"No matches found for {league} {season}")
        return pd.DataFrame()

    merged = _join_odds(matches, db, league, season)
    merged = _join_league_table(merged, db, league, season)
    merged = _add_elo_delta(merged)
    merged = merged.sort_values("date").reset_index(drop=True)

    logger.info(
        f"Built master DataFrame: {len(merged)} rows, "
        f"{len(merged.columns)} columns"
    )
    return merged


def _join_odds(
    matches: pd.DataFrame,
    db: FootballDatabase,
    league: str,
    season: str,
) -> pd.DataFrame:
    """Left-join odds columns onto matches by game key.

    Args:
        matches: Base matches DataFrame.
        db: Database instance.
        league: League identifier.
        season: Season code.

    Returns:
        Matches with odds columns added.
    """
    odds = db.read_table("match_odds", league=league, season=season)
    if odds.empty:
        logger.warning("No odds data found, skipping odds join")
        return matches

    available = [c for c in ODDS_JOIN_COLUMNS if c in odds.columns]
    odds_subset = odds[["game", *available]].copy()

    return matches.merge(odds_subset, on="game", how="left")


def _join_league_table(
    matches: pd.DataFrame,
    db: FootballDatabase,
    league: str,
    season: str,
) -> pd.DataFrame:
    """Left-join league table stats for home and away teams.

    Args:
        matches: Matches DataFrame.
        db: Database instance.
        league: League identifier.
        season: Season code.

    Returns:
        Matches with home_league_* and away_league_* columns.
    """
    table = db.read_table("league_tables", league=league, season=season)
    if table.empty:
        logger.warning("No league table data, skipping table join")
        return matches

    available = [c for c in LEAGUE_TABLE_COLUMNS if c in table.columns]
    table_subset = table[["team", *available]].copy()

    home_renamed = _prefix_columns(table_subset, "home_league_", "team")
    matches = matches.merge(
        home_renamed, left_on="home_team",
        right_on="team", how="left",
    ).drop(columns=["team"])

    away_renamed = _prefix_columns(table_subset, "away_league_", "team")
    matches = matches.merge(
        away_renamed, left_on="away_team",
        right_on="team", how="left",
    ).drop(columns=["team"])

    return matches


def _prefix_columns(
    df: pd.DataFrame,
    prefix: str,
    keep_col: str,
) -> pd.DataFrame:
    """Rename all columns except keep_col with a prefix.

    Args:
        df: Source DataFrame.
        prefix: Prefix to add (e.g. "home_league_").
        keep_col: Column name to keep unchanged.

    Returns:
        DataFrame with renamed columns.
    """
    rename_map = {
        col: f"{prefix}{col}"
        for col in df.columns if col != keep_col
    }
    return df.rename(columns=rename_map)


def _add_elo_delta(matches: pd.DataFrame) -> pd.DataFrame:
    """Add elo_delta column (home_elo - away_elo).

    Args:
        matches: DataFrame with home_elo and away_elo columns.

    Returns:
        DataFrame with elo_delta column added.
    """
    if "home_elo" in matches.columns and "away_elo" in matches.columns:
        matches["elo_delta"] = matches["home_elo"] - matches["away_elo"]
    return matches


def add_target_variables(df: pd.DataFrame) -> pd.DataFrame:
    """Add prediction target columns to the DataFrame.

    Targets:
        result_1x2: 'H' (home win), 'D' (draw), 'A' (away win)
        over_2_5: True if total goals > 2.5
        btts: True if both teams scored

    Args:
        df: DataFrame with home_goals and away_goals columns.

    Returns:
        DataFrame with target columns added.
    """
    result = df.copy()
    result["result_1x2"] = _compute_result_1x2(
        result["home_goals"], result["away_goals"],
    )
    result["over_2_5"] = _compute_over_2_5(
        result["home_goals"], result["away_goals"],
    )
    result["btts"] = _compute_btts(
        result["home_goals"], result["away_goals"],
    )
    return result


def _compute_result_1x2(
    home_goals: pd.Series,
    away_goals: pd.Series,
) -> pd.Series:
    """Compute 1X2 match result.

    Args:
        home_goals: Home team goal counts.
        away_goals: Away team goal counts.

    Returns:
        Series with 'H', 'D', or 'A' values.
    """
    conditions = [
        home_goals > away_goals,
        home_goals == away_goals,
        home_goals < away_goals,
    ]
    choices = ["H", "D", "A"]
    return pd.Series(
        np.select(conditions, choices, default=""),
        index=home_goals.index,
        dtype="object",
    ).where(home_goals.notna() & away_goals.notna())


def _compute_over_2_5(
    home_goals: pd.Series,
    away_goals: pd.Series,
) -> pd.Series:
    """Compute over/under 2.5 goals target.

    Args:
        home_goals: Home team goal counts.
        away_goals: Away team goal counts.

    Returns:
        Boolean Series (True if total > 2.5).
    """
    total = home_goals + away_goals
    return (total > 2.5).where(total.notna())


def _compute_btts(
    home_goals: pd.Series,
    away_goals: pd.Series,
) -> pd.Series:
    """Compute both-teams-to-score target.

    Args:
        home_goals: Home team goal counts.
        away_goals: Away team goal counts.

    Returns:
        Boolean Series (True if both scored).
    """
    return (
        (home_goals > 0) & (away_goals > 0)
    ).where(home_goals.notna() & away_goals.notna())


def add_rolling_features(
    df: pd.DataFrame,
    windows: list[int] | None = None,
) -> pd.DataFrame:
    """Add rolling average features per team with no lookahead bias.

    Computes rolling means for goals, xG, and form points over
    the specified window sizes. Uses shift(1) to prevent lookahead.

    Args:
        df: DataFrame sorted by date with match-level data.
        windows: List of rolling window sizes (default: [5, 10]).

    Returns:
        DataFrame with rolling feature columns added.
    """
    if windows is None:
        windows = [5, 10]

    result = df.copy()
    result = result.sort_values("date").reset_index(drop=True)
    result = _add_form_points(result)

    for window in windows:
        result = _add_rolling_stats(result, window)
        result = _add_rolling_form(result, window)

    return result


def _add_form_points(df: pd.DataFrame) -> pd.DataFrame:
    """Add per-match points for home and away teams.

    Args:
        df: DataFrame with home_goals and away_goals.

    Returns:
        DataFrame with home_points and away_points columns.
    """
    conditions_home = [
        df["home_goals"] > df["away_goals"],
        df["home_goals"] == df["away_goals"],
    ]
    df["home_points"] = np.select(conditions_home, [3, 1], default=0)

    conditions_away = [
        df["away_goals"] > df["home_goals"],
        df["away_goals"] == df["home_goals"],
    ]
    df["away_points"] = np.select(conditions_away, [3, 1], default=0)

    return df


def _add_rolling_stats(
    df: pd.DataFrame,
    window: int,
) -> pd.DataFrame:
    """Add rolling mean columns for core stats, grouped by team.

    Groups by home_team for home_* columns and away_team for
    away_* columns to prevent cross-team leakage.

    Args:
        df: DataFrame sorted by date.
        window: Rolling window size.

    Returns:
        DataFrame with rolled stat columns.
    """
    for col in ROLLING_STAT_COLUMNS:
        if col not in df.columns:
            continue
        group_col = (
            "home_team" if col.startswith("home_") else "away_team"
        )
        rolled_col = f"{col}_rolled_{window}"
        shifted = df.groupby(group_col)[col].shift(1)
        df[rolled_col] = (
            shifted
            .rolling(window=window, min_periods=window)
            .mean()
        )
    return df


def _add_rolling_form(
    df: pd.DataFrame,
    window: int,
) -> pd.DataFrame:
    """Add rolling form (points average) columns, grouped by team.

    Groups by home_team for home_points and away_team for
    away_points to prevent cross-team leakage.

    Args:
        df: DataFrame with home_points and away_points.
        window: Rolling window size.

    Returns:
        DataFrame with form point columns.
    """
    for side in ["home", "away"]:
        points_col = f"{side}_points"
        if points_col not in df.columns:
            continue
        group_col = f"{side}_team"
        form_col = f"{side}_form_points_{window}"
        shifted = df.groupby(group_col)[points_col].shift(1)
        df[form_col] = (
            shifted
            .rolling(window=window, min_periods=window)
            .mean()
        )
    return df
