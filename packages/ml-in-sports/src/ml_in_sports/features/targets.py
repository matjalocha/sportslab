"""Extended target variables for football match prediction.

Provides core targets (1X2, over/under, BTTS) plus additional
targets for alternative betting lines, double chance, half-time
markets, margin, and total goals.
"""

import numpy as np
import pandas as pd
import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Core targets
# ---------------------------------------------------------------------------

def compute_result_1x2(
    home_goals: pd.Series,
    away_goals: pd.Series,
) -> pd.Series:
    """Compute full-time 1X2 match result.

    Args:
        home_goals: Home team goal counts.
        away_goals: Away team goal counts.

    Returns:
        Series with 'H', 'D', or 'A' values (NaN where goals missing).
    """
    conditions = [
        home_goals > away_goals,
        home_goals == away_goals,
        home_goals < away_goals,
    ]
    choices = ["H", "D", "A"]
    result = pd.Series(
        np.select(conditions, choices, default=""),
        index=home_goals.index,
        dtype="object",
    )
    return result.where(home_goals.notna() & away_goals.notna())


def compute_over_under(
    home_goals: pd.Series,
    away_goals: pd.Series,
    threshold: float,
) -> pd.Series:
    """Compute over/under target for a given goal threshold.

    Args:
        home_goals: Home team goal counts.
        away_goals: Away team goal counts.
        threshold: Goal line (e.g. 1.5, 2.5, 3.5).

    Returns:
        Boolean Series (True if total > threshold, NaN where missing).
    """
    total = home_goals + away_goals
    return (total > threshold).where(total.notna())


def compute_btts(
    home_goals: pd.Series,
    away_goals: pd.Series,
) -> pd.Series:
    """Compute both-teams-to-score target.

    Args:
        home_goals: Home team goal counts.
        away_goals: Away team goal counts.

    Returns:
        Boolean Series (True if both scored, NaN where missing).
    """
    both_valid = home_goals.notna() & away_goals.notna()
    return ((home_goals > 0) & (away_goals > 0)).where(both_valid)


# ---------------------------------------------------------------------------
# Additional targets
# ---------------------------------------------------------------------------

def compute_home_goals_over_1_5(home_goals: pd.Series) -> pd.Series:
    """Compute whether home team scored over 1.5 goals.

    Args:
        home_goals: Home team goal counts.

    Returns:
        Boolean Series (True if home_goals > 1.5, NaN where missing).
    """
    return (home_goals > 1.5).where(home_goals.notna())


def compute_away_goals_over_0_5(away_goals: pd.Series) -> pd.Series:
    """Compute whether away team scored over 0.5 goals.

    Args:
        away_goals: Away team goal counts.

    Returns:
        Boolean Series (True if away_goals > 0.5, NaN where missing).
    """
    return (away_goals > 0.5).where(away_goals.notna())


def compute_double_chance(
    result_1x2: pd.Series,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Compute double chance columns from 1X2 result.

    Args:
        result_1x2: Series with 'H', 'D', 'A' values.

    Returns:
        Tuple of (home_or_draw, home_or_away, draw_or_away) boolean Series.
    """
    valid = result_1x2.notna()
    home_or_draw = result_1x2.isin(["H", "D"]).where(valid)
    home_or_away = result_1x2.isin(["H", "A"]).where(valid)
    draw_or_away = result_1x2.isin(["D", "A"]).where(valid)
    return home_or_draw, home_or_away, draw_or_away


def compute_margin(
    home_goals: pd.Series,
    away_goals: pd.Series,
) -> pd.Series:
    """Compute signed goal margin (home - away).

    Args:
        home_goals: Home team goal counts.
        away_goals: Away team goal counts.

    Returns:
        Integer Series (positive = home win, NaN where missing).
    """
    return (home_goals - away_goals).where(
        home_goals.notna() & away_goals.notna(),
    )


def compute_total_goals(
    home_goals: pd.Series,
    away_goals: pd.Series,
) -> pd.Series:
    """Compute total goals scored in match.

    Args:
        home_goals: Home team goal counts.
        away_goals: Away team goal counts.

    Returns:
        Integer Series (NaN where goals missing).
    """
    return (home_goals + away_goals).where(
        home_goals.notna() & away_goals.notna(),
    )


# ---------------------------------------------------------------------------
# Half-time targets
# ---------------------------------------------------------------------------

def compute_ht_result_1x2(
    ht_home_goals: pd.Series,
    ht_away_goals: pd.Series,
) -> pd.Series:
    """Compute half-time 1X2 result.

    Args:
        ht_home_goals: Half-time home goals.
        ht_away_goals: Half-time away goals.

    Returns:
        Series with 'H', 'D', or 'A' values.
    """
    return compute_result_1x2(ht_home_goals, ht_away_goals)


def compute_ht_over_0_5(
    ht_home_goals: pd.Series,
    ht_away_goals: pd.Series,
) -> pd.Series:
    """Compute whether over 0.5 goals were scored at half-time.

    Args:
        ht_home_goals: Half-time home goals.
        ht_away_goals: Half-time away goals.

    Returns:
        Boolean Series (True if HT total > 0.5).
    """
    return compute_over_under(ht_home_goals, ht_away_goals, 0.5)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def _has_halftime_columns(df: pd.DataFrame) -> bool:
    """Check if DataFrame contains half-time goal columns."""
    return "ht_home_goals" in df.columns and "ht_away_goals" in df.columns


def add_all_targets(df: pd.DataFrame) -> pd.DataFrame:
    """Add all target columns to the DataFrame.

    Adds core targets (1X2, over/under lines, BTTS), double chance,
    margin, total goals, and half-time targets (when HT data available).

    Args:
        df: DataFrame with home_goals and away_goals columns.

    Returns:
        New DataFrame with all target columns added.
    """
    result = df.copy()
    home = result["home_goals"]
    away = result["away_goals"]

    result["result_1x2"] = compute_result_1x2(home, away)
    result["over_2_5"] = compute_over_under(home, away, 2.5)
    result["btts"] = compute_btts(home, away)
    result["over_1_5"] = compute_over_under(home, away, 1.5)
    result["over_3_5"] = compute_over_under(home, away, 3.5)
    result["home_goals_over_1_5"] = compute_home_goals_over_1_5(home)
    result["away_goals_over_0_5"] = compute_away_goals_over_0_5(away)

    home_or_draw, home_or_away, draw_or_away = compute_double_chance(
        result["result_1x2"],
    )
    result["home_or_draw"] = home_or_draw
    result["home_or_away"] = home_or_away
    result["draw_or_away"] = draw_or_away

    result["margin"] = compute_margin(home, away)
    result["total_goals"] = compute_total_goals(home, away)

    if _has_halftime_columns(result):
        ht_home = result["ht_home_goals"]
        ht_away = result["ht_away_goals"]
        result["ht_result_1x2"] = compute_ht_result_1x2(ht_home, ht_away)
        result["ht_over_0_5"] = compute_ht_over_0_5(ht_home, ht_away)

    target_count = sum(
        1 for col in result.columns if col not in df.columns
    )
    logger.info("Added %d target columns", target_count)
    return result
