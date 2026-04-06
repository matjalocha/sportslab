"""Shared utility functions for feature engineering modules.

Extracted from duplicated implementations across modules to
follow DRY principle.
"""

import numpy as np
import pandas as pd


def compute_match_points(
    goals_for: pd.Series,
    goals_against: pd.Series,
) -> pd.Series:
    """Compute match points: 3 for win, 1 for draw, 0 for loss.

    Args:
        goals_for: Goals scored by the team.
        goals_against: Goals conceded by the team.

    Returns:
        Series of float points (3.0/1.0/0.0).
    """
    conditions = [
        goals_for > goals_against,
        goals_for == goals_against,
    ]
    choices = [3.0, 1.0]
    return pd.Series(
        np.select(conditions, choices, default=0.0),
        index=goals_for.index,
        dtype=float,
    )


def ensure_datetime(df: pd.DataFrame) -> pd.DataFrame:
    """Convert date column to datetime if not already.

    Args:
        df: DataFrame with a date column.

    Returns:
        DataFrame with date as datetime type.
    """
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    return df
