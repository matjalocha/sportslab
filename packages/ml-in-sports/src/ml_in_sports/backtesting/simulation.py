"""Metric computation and bet simulation helpers for the runner.

Pure functions that compute fold-level metrics and simulate flat
betting outcomes. Used internally by ``WalkForwardRunner``.
"""

from __future__ import annotations

import numpy as np
import structlog

from ml_in_sports.backtesting.metrics import (
    compute_brier_score,
    compute_clv_mean,
    compute_ece,
    compute_log_loss,
    compute_max_drawdown,
    compute_max_losing_streak,
    compute_roi,
    compute_sharpe,
)

logger = structlog.get_logger(__name__)


def compute_fold_metrics(
    predictions: np.ndarray,
    actuals: np.ndarray,
    odds: np.ndarray | None,
    requested_metrics: list[str],
) -> dict[str, float]:
    """Compute all requested metrics for a single fold.

    Args:
        predictions: Predicted probabilities, shape (n, n_classes).
        actuals: True labels, shape (n,).
        odds: Closing odds, shape (n, n_classes) or None.
        requested_metrics: List of metric names to compute.

    Returns:
        Dict of metric_name -> value.
    """
    results: dict[str, float] = {}

    for metric_name in requested_metrics:
        try:
            value = _compute_single_metric(
                metric_name,
                predictions,
                actuals,
                odds,
            )
            results[metric_name] = value
        except Exception:
            logger.warning(
                "metric_computation_failed",
                metric=metric_name,
                exc_info=True,
            )
            results[metric_name] = float("nan")

    return results


def _compute_single_metric(
    metric_name: str,
    predictions: np.ndarray,
    actuals: np.ndarray,
    odds: np.ndarray | None,
) -> float:
    """Dispatch to the appropriate metric function."""
    if metric_name == "log_loss":
        return compute_log_loss(actuals, predictions)

    if metric_name == "ece":
        return compute_ece(actuals, predictions)

    if metric_name == "brier_score":
        pred_binary = predictions[:, 1] if predictions.ndim == 2 else predictions
        actual_binary = (actuals == 1).astype(int)
        return compute_brier_score(actual_binary, pred_binary)

    if metric_name == "clv_mean":
        if odds is None:
            return float("nan")
        pred_for_actual = _gather_predicted_probs(predictions, actuals)
        odds_for_actual = _gather_odds(odds, actuals)
        return compute_clv_mean(pred_for_actual, odds_for_actual)

    if metric_name == "roi":
        stakes, returns = simulate_flat_betting(predictions, actuals, odds)
        return compute_roi(stakes, returns)

    if metric_name == "sharpe":
        _, returns = simulate_flat_betting(predictions, actuals, odds)
        return compute_sharpe(returns)

    if metric_name == "max_drawdown":
        _, returns = simulate_flat_betting(predictions, actuals, odds)
        cumulative = np.cumsum(returns) + 1000.0
        return compute_max_drawdown(cumulative)

    if metric_name == "max_losing_streak":
        outcomes = simulate_bet_outcomes(predictions, actuals)
        return float(compute_max_losing_streak(outcomes))

    msg = f"Unknown metric: {metric_name}"
    raise ValueError(msg)


def _gather_predicted_probs(
    predictions: np.ndarray,
    actuals: np.ndarray,
) -> np.ndarray:
    """Extract predicted probability for the actual outcome class."""
    if predictions.ndim == 1:
        return predictions
    result: np.ndarray = predictions[np.arange(len(actuals)), actuals.astype(int)]
    return result


def _gather_odds(
    odds: np.ndarray,
    actuals: np.ndarray,
) -> np.ndarray:
    """Extract closing odds for the actual outcome class."""
    if odds.ndim == 1:
        return odds
    result: np.ndarray = odds[np.arange(len(actuals)), actuals.astype(int)]
    return result


def simulate_flat_betting(
    predictions: np.ndarray,
    actuals: np.ndarray,
    odds: np.ndarray | None,
) -> tuple[np.ndarray, np.ndarray]:
    """Simulate flat-unit betting on the highest-confidence outcome.

    Returns stakes (all 1.0) and net returns per bet.
    """
    n = len(actuals)
    stakes = np.ones(n)

    if odds is None:
        default_odds = np.full(n, 2.0)
        bet_class = (
            predictions.argmax(axis=1)
            if predictions.ndim == 2
            else ((predictions > 0.5).astype(int))
        )
        won = (bet_class == actuals).astype(float)
        returns = won * (default_odds - 1.0) - (1.0 - won)
        return stakes, returns

    bet_class = (
        predictions.argmax(axis=1) if predictions.ndim == 2 else ((predictions > 0.5).astype(int))
    )

    bet_odds = odds[np.arange(n), bet_class] if odds.ndim == 2 else odds

    won = (bet_class == actuals).astype(float)
    returns = won * (bet_odds - 1.0) - (1.0 - won)

    return stakes, returns


def simulate_kelly_betting(
    predictions: np.ndarray,
    actuals: np.ndarray,
    odds: np.ndarray | None,
    kelly_fraction: float = 0.25,
    max_exposure_per_match: float = 0.03,
    initial_bankroll: float = 1000.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Simulate Kelly-criterion staking with per-match exposure cap.

    For each bet the function:
        1. Picks the highest-confidence outcome class.
        2. Computes the raw Kelly fraction: ``(p*b - 1) / (b - 1)``
           where *p* = model probability and *b* = decimal odds.
        3. Multiplies by ``kelly_fraction`` (e.g. 0.25 for quarter-Kelly).
        4. Caps at ``max_exposure_per_match`` (fraction of bankroll).
        5. Stakes that fraction of the *current* bankroll.
        6. Updates the bankroll based on the outcome.

    When ``odds`` is ``None``, falls back to flat-bet simulation via
    ``simulate_flat_betting`` with the bankroll starting at
    ``initial_bankroll``.

    Args:
        predictions: Model probabilities, shape ``(n,)`` or ``(n, n_classes)``.
        actuals: True class labels, shape ``(n,)``.
        odds: Decimal odds, shape ``(n, n_classes)`` or ``None``.
        kelly_fraction: Global multiplier (0.25 = quarter-Kelly,
            0.50 = half-Kelly).
        max_exposure_per_match: Maximum fraction of bankroll risked on a
            single bet.
        initial_bankroll: Starting bankroll in currency units.

    Returns:
        Tuple of ``(bankroll_history, bet_returns)`` -- both arrays of
        length *n*.  ``bankroll_history[i]`` is the bankroll **after**
        bet *i* is settled.  ``bet_returns[i]`` is the signed P&L of
        bet *i* in currency units.
    """
    n = len(actuals)

    if odds is None:
        logger.info(
            "kelly_simulation_fallback_flat",
            reason="odds_missing",
            kelly_fraction=kelly_fraction,
        )
        _stakes, flat_returns = simulate_flat_betting(predictions, actuals, odds)
        bankroll_history = initial_bankroll + np.cumsum(flat_returns)
        return bankroll_history, flat_returns

    bet_class = (
        predictions.argmax(axis=1) if predictions.ndim == 2 else (predictions > 0.5).astype(int)
    )

    # Model probability for the chosen outcome
    bet_prob = predictions[np.arange(n), bet_class] if predictions.ndim == 2 else predictions

    # Decimal odds for the chosen outcome
    bet_odds = odds[np.arange(n), bet_class] if odds.ndim == 2 else odds

    bankroll = initial_bankroll
    bankroll_history = np.empty(n, dtype=np.float64)
    bet_returns = np.empty(n, dtype=np.float64)

    for i in range(n):
        p = float(bet_prob[i])
        b = float(bet_odds[i])

        # Raw Kelly: f* = (p*b - 1) / (b - 1), floored at 0
        raw_f = 0.0 if b <= 1.0 else max((p * b - 1.0) / (b - 1.0), 0.0)

        # Apply fraction multiplier and exposure cap
        stake_frac = min(raw_f * kelly_fraction, max_exposure_per_match)
        stake = stake_frac * bankroll

        won = int(bet_class[i]) == int(actuals[i])
        pnl = stake * (b - 1.0) if won else -stake

        bankroll += pnl
        bankroll_history[i] = bankroll
        bet_returns[i] = pnl

    return bankroll_history, bet_returns


def simulate_bet_outcomes(
    predictions: np.ndarray,
    actuals: np.ndarray,
) -> np.ndarray:
    """Return binary win/loss array for the model's best bet."""
    bet_class = (
        predictions.argmax(axis=1) if predictions.ndim == 2 else ((predictions > 0.5).astype(int))
    )
    result: np.ndarray = (bet_class == actuals).astype(int)
    return result
