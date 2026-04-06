"""ECE monitoring over time.

Tracks Expected Calibration Error per league, season, and market
over rolling windows to detect calibration degradation.

Reuses the binary ECE implementation from
:mod:`ml_in_sports.backtesting.metrics` to guarantee consistency
between backtest evaluation and production monitoring.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import structlog

from ml_in_sports.backtesting.metrics import compute_ece as _compute_ece

logger = structlog.get_logger(__name__)

_DEFAULT_GROUP_COLS: list[str] = ["league", "season"]


def compute_ece_per_group(
    predictions_df: pd.DataFrame,
    prob_col: str = "model_prob",
    outcome_col: str = "actual",
    group_cols: list[str] | None = None,
    n_bins: int = 10,
) -> pd.DataFrame:
    """Compute ECE grouped by league/season/market.

    Args:
        predictions_df: DataFrame with predictions and outcomes.
        prob_col: Column with predicted probabilities.
        outcome_col: Column with actual binary outcomes (0/1).
        group_cols: Columns to group by.  Default: ``["league", "season"]``.
        n_bins: Number of equal-width probability bins for ECE.

    Returns:
        DataFrame with group columns plus ``ece`` and ``n_bets``.
        Sorted by ECE descending.

    Raises:
        ValueError: If required columns are missing.
    """
    if group_cols is None:
        group_cols = list(_DEFAULT_GROUP_COLS)

    _validate_columns(predictions_df, prob_col, outcome_col, group_cols)

    rows: list[dict[str, object]] = []
    for group_key, group_df in predictions_df.groupby(group_cols, sort=False):
        y_prob = group_df[prob_col].to_numpy(dtype=np.float64)
        y_true = group_df[outcome_col].to_numpy(dtype=np.float64)

        n_bets = len(y_true)
        if n_bets == 0:
            continue

        ece = _compute_ece(y_true, y_prob, n_bins=n_bins)

        # Build the row with group identifiers.
        # pandas groupby returns a scalar for single-key groups,
        # a tuple for multi-key groups.
        group_values = group_key if isinstance(group_key, tuple) else (group_key,)
        row: dict[str, object] = dict(zip(group_cols, group_values, strict=True))

        row["ece"] = ece
        row["n_bets"] = n_bets
        rows.append(row)

        logger.debug(
            "ece_group_computed",
            group=str(group_key),
            ece=round(ece, 6),
            n_bets=n_bets,
        )

    result = pd.DataFrame(rows)
    if result.empty:
        return pd.DataFrame(columns=[*group_cols, "ece", "n_bets"])
    return result.sort_values("ece", ascending=False).reset_index(drop=True)


def compute_rolling_ece(
    predictions_df: pd.DataFrame,
    prob_col: str = "model_prob",
    outcome_col: str = "actual",
    window: int = 200,
    n_bins: int = 10,
) -> pd.DataFrame:
    """Compute rolling ECE over a window of predictions.

    The DataFrame should already be sorted chronologically before calling.
    Each row in the output corresponds to one window ending at that index.

    Args:
        predictions_df: DataFrame sorted by date.
        prob_col: Probability column name.
        outcome_col: Outcome column name (binary 0/1).
        window: Number of predictions per rolling window.
        n_bins: Number of equal-width probability bins for ECE.

    Returns:
        DataFrame with columns ``window_start``, ``window_end``, ``ece``,
        ``n_bets``.  One row per sliding position.

    Raises:
        ValueError: If required columns are missing or window < 2.
    """
    _validate_columns(predictions_df, prob_col, outcome_col, group_cols=[])

    if window < 2:
        msg = "window must be >= 2"
        raise ValueError(msg)

    y_prob = predictions_df[prob_col].to_numpy(dtype=np.float64)
    y_true = predictions_df[outcome_col].to_numpy(dtype=np.float64)
    n_total = len(y_true)

    if n_total < window:
        logger.warning(
            "rolling_ece_insufficient_data",
            n_total=n_total,
            window=window,
        )
        return pd.DataFrame(columns=["window_start", "window_end", "ece", "n_bets"])

    rows: list[dict[str, object]] = []
    for end in range(window, n_total + 1):
        start = end - window
        ece = _compute_ece(y_true[start:end], y_prob[start:end], n_bins=n_bins)
        rows.append({
            "window_start": start,
            "window_end": end - 1,
            "ece": ece,
            "n_bets": window,
        })

    return pd.DataFrame(rows)


def ece_alert(
    ece_results: pd.DataFrame,
    threshold: float = 0.02,
) -> list[dict[str, object]]:
    """Detect groups or windows where ECE exceeds threshold.

    Works with both :func:`compute_ece_per_group` and
    :func:`compute_rolling_ece` outputs -- any DataFrame that has an
    ``ece`` column.

    Args:
        ece_results: Output of :func:`compute_ece_per_group` or
            :func:`compute_rolling_ece`.
        threshold: ECE threshold (default 0.02 = 2%).

    Returns:
        List of alert dicts.  Each dict contains all columns from the
        triggering row plus ``"above_threshold": True``.
        Sorted by ECE descending.
    """
    if ece_results.empty or "ece" not in ece_results.columns:
        return []

    triggered = ece_results[ece_results["ece"] > threshold].copy()
    triggered = triggered.sort_values("ece", ascending=False)

    alerts: list[dict[str, object]] = []
    for _, row in triggered.iterrows():
        alert: dict[str, object] = dict(row)
        alert["above_threshold"] = True
        alerts.append(alert)

    if alerts:
        logger.warning(
            "ece_threshold_exceeded",
            n_alerts=len(alerts),
            threshold=threshold,
            worst_ece=round(float(str(alerts[0]["ece"])), 6),
        )

    return alerts


def _validate_columns(
    df: pd.DataFrame,
    prob_col: str,
    outcome_col: str,
    group_cols: list[str],
) -> None:
    """Check that required columns exist in the DataFrame.

    Raises:
        ValueError: If any required column is missing.
    """
    required = {prob_col, outcome_col, *group_cols}
    missing = required - set(df.columns)
    if missing:
        msg = f"Missing columns in DataFrame: {sorted(missing)}"
        raise ValueError(msg)
