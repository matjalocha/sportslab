"""Betting-specific features derived from bookmaker odds.

Transforms raw decimal odds into implied probabilities, fair odds,
overround (market margin), and cross-bookmaker consensus signals.
"""

import pandas as pd
import structlog

logger = structlog.get_logger(__name__)

_1X2_AVG_COLS: list[str] = ["avg_home", "avg_draw", "avg_away"]
_1X2_OUTCOMES: list[str] = ["home", "draw", "away"]

_OU_AVG_COLS: list[str] = ["avg_over_25", "avg_under_25"]
_OU_OUTCOMES: list[str] = ["over_25", "under_25"]

_BOOKMAKER_PREFIXES: list[str] = ["b365", "avg"]


def add_betting_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add all betting-derived features to a match DataFrame.

    Computes implied probabilities, overround, fair odds, and
    market consensus from available odds columns.

    Args:
        df: DataFrame with odds columns (avg_home, b365_home, etc.).

    Returns:
        DataFrame with betting feature columns added.
    """
    if df.empty:
        return df.copy()

    result = df.copy()
    result = compute_implied_probabilities(result)
    result = compute_overround(result)
    result = compute_fair_probabilities(result)
    result = compute_market_consensus(result)

    logger.info("Added betting features to DataFrame")
    return result


def compute_implied_probabilities(df: pd.DataFrame) -> pd.DataFrame:
    """Convert average decimal odds to implied probabilities.

    Implied probability = 1 / decimal_odds.

    Args:
        df: DataFrame with avg odds columns.

    Returns:
        DataFrame with implied_prob_* columns added.
    """
    result = df.copy()
    result = _compute_implied_for_market(result, _1X2_AVG_COLS, _1X2_OUTCOMES)
    result = _compute_implied_for_market(result, _OU_AVG_COLS, _OU_OUTCOMES)
    return result


def _compute_implied_for_market(
    df: pd.DataFrame,
    odds_columns: list[str],
    outcome_names: list[str],
) -> pd.DataFrame:
    """Compute implied probabilities for a single market.

    Args:
        df: DataFrame with odds columns.
        odds_columns: Column names containing decimal odds.
        outcome_names: Outcome labels for new column names.

    Returns:
        DataFrame with implied_prob_{outcome} columns added.
    """
    for odds_col, outcome in zip(odds_columns, outcome_names, strict=True):
        if odds_col not in df.columns:
            continue
        odds = df[odds_col]
        df[f"implied_prob_{outcome}"] = (1.0 / odds).where(odds > 0)
    return df


def compute_overround(df: pd.DataFrame) -> pd.DataFrame:
    """Compute bookmaker overround (market margin).

    Overround = sum(implied_probs) - 1. Positive values indicate
    the bookmaker margin built into the odds.

    Args:
        df: DataFrame with implied_prob_* columns.

    Returns:
        DataFrame with overround_1x2 and overround_ou columns.
    """
    result = df.copy()
    result = _compute_overround_for_market(
        result, _1X2_OUTCOMES, "overround_1x2",
    )
    result = _compute_overround_for_market(
        result, _OU_OUTCOMES, "overround_ou",
    )
    return result


def _compute_overround_for_market(
    df: pd.DataFrame,
    outcome_names: list[str],
    target_column: str,
) -> pd.DataFrame:
    """Compute overround for a single market.

    Args:
        df: DataFrame with implied_prob columns.
        outcome_names: Outcomes to sum (e.g. ["home", "draw", "away"]).
        target_column: Name for the overround column.

    Returns:
        DataFrame with overround column added.
    """
    prob_cols = [f"implied_prob_{o}" for o in outcome_names]
    available = [c for c in prob_cols if c in df.columns]
    if not available:
        return df
    df[target_column] = df[available].sum(axis=1, skipna=False) - 1.0
    return df


def compute_fair_probabilities(df: pd.DataFrame) -> pd.DataFrame:
    """Remove overround to get fair (true) probabilities.

    Fair probability = implied_prob / sum(implied_probs).

    Args:
        df: DataFrame with implied_prob_* columns.

    Returns:
        DataFrame with fair_prob_* columns added.
    """
    result = df.copy()
    result = _compute_fair_for_market(result, _1X2_OUTCOMES)
    result = _compute_fair_for_market(result, _OU_OUTCOMES)
    return result


def _compute_fair_for_market(
    df: pd.DataFrame,
    outcome_names: list[str],
) -> pd.DataFrame:
    """Compute fair probabilities for a single market.

    Args:
        df: DataFrame with implied_prob columns.
        outcome_names: Outcomes to normalize.

    Returns:
        DataFrame with fair_prob_{outcome} columns added.
    """
    prob_cols = [f"implied_prob_{o}" for o in outcome_names]
    available = [c for c in prob_cols if c in df.columns]
    if not available:
        return df

    prob_sum = df[available].sum(axis=1)
    safe_sum = prob_sum.where(prob_sum > 0)
    for col in available:
        outcome = col.replace("implied_prob_", "")
        df[f"fair_prob_{outcome}"] = df[col] / safe_sum
    return df


def compute_market_consensus(df: pd.DataFrame) -> pd.DataFrame:
    """Compute cross-bookmaker consensus implied probabilities.

    Averages the implied probability from each available bookmaker
    for each outcome.

    Args:
        df: DataFrame with bookmaker odds columns.

    Returns:
        DataFrame with consensus_* columns added.
    """
    result = df.copy()
    for outcome in _1X2_OUTCOMES:
        result = _compute_consensus_for_outcome(result, outcome)
    return result


def _compute_consensus_for_outcome(
    df: pd.DataFrame,
    outcome: str,
) -> pd.DataFrame:
    """Compute consensus for a single outcome across bookmakers.

    Args:
        df: DataFrame with bookmaker odds columns.
        outcome: Outcome name (e.g. "home", "draw", "away").

    Returns:
        DataFrame with consensus_{outcome} column added.
    """
    bookmaker_cols = [f"{p}_{outcome}" for p in _BOOKMAKER_PREFIXES]
    available = [c for c in bookmaker_cols if c in df.columns]
    if not available:
        return df

    implied_probs = pd.DataFrame({
        col: (1.0 / df[col]).where(df[col] > 0) for col in available
    })
    df[f"consensus_{outcome}"] = implied_probs.mean(axis=1)
    return df
