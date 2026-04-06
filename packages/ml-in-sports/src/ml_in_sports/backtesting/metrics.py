"""Evaluation metrics for sports betting backtests.

All functions are pure: take arrays, return scalars. No state, no side effects.
Designed for use in the walk-forward backtest runner and report generator.
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import brier_score_loss, log_loss


def compute_log_loss(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    """Compute log loss (cross-entropy) of probability predictions.

    Supports both binary (1D y_prob) and multiclass (2D y_prob).

    Args:
        y_true: True labels (int class indices or binary 0/1).
        y_prob: Predicted probabilities. Shape (n,) for binary or (n, k) for multiclass.

    Returns:
        Log loss value (lower is better).

    Raises:
        ValueError: If inputs are empty.
    """
    if len(y_true) == 0:
        msg = "y_true must not be empty"
        raise ValueError(msg)
    clipped = np.clip(y_prob, 1e-15, 1 - 1e-15)
    return float(log_loss(y_true, clipped))


def compute_ece(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int = 10,
) -> float:
    """Compute Expected Calibration Error.

    Uses equal-width bins. For multiclass, averages per-class ECE.
    ECE < 2% is considered good calibration for sports betting.

    Args:
        y_true: True labels (int class indices or binary 0/1).
        y_prob: Predicted probabilities. Shape (n,) for binary or (n, k) for multiclass.
        n_bins: Number of equal-width probability bins.

    Returns:
        ECE as a fraction (e.g. 0.02 = 2%).

    Raises:
        ValueError: If inputs are empty.
    """
    if len(y_true) == 0:
        msg = "y_true must not be empty"
        raise ValueError(msg)

    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob, dtype=np.float64)

    if y_prob.ndim == 1:
        return _ece_binary(y_true, y_prob, n_bins)

    n_classes = y_prob.shape[1]
    ece_sum = 0.0
    for c in range(n_classes):
        binary_true = (y_true == c).astype(int)
        ece_sum += _ece_binary(binary_true, y_prob[:, c], n_bins)
    return float(ece_sum / n_classes)


def _ece_binary(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int,
) -> float:
    """ECE for binary predictions."""
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n_total = len(y_true)

    for i in range(n_bins):
        mask = (y_prob > bin_edges[i]) & (y_prob <= bin_edges[i + 1])
        if i == 0:
            mask = mask | (y_prob == bin_edges[i])
        n_bin = mask.sum()
        if n_bin == 0:
            continue
        avg_confidence = float(y_prob[mask].mean())
        avg_accuracy = float(y_true[mask].mean())
        ece += (n_bin / n_total) * abs(avg_accuracy - avg_confidence)

    return ece


def compute_brier_score(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    """Compute Brier score (mean squared probability error).

    For binary classification only. For multiclass, compute per-class
    and average externally.

    Args:
        y_true: True binary labels (0 or 1).
        y_prob: Predicted probabilities for the positive class.

    Returns:
        Brier score (lower is better, 0 = perfect).

    Raises:
        ValueError: If inputs are empty.
    """
    if len(y_true) == 0:
        msg = "y_true must not be empty"
        raise ValueError(msg)
    return float(brier_score_loss(y_true, y_prob))


def compute_clv(
    model_prob: np.ndarray,
    closing_odds: np.ndarray,
) -> np.ndarray:
    """Compute per-bet Closing Line Value.

    CLV = model implied probability - market implied probability.
    Positive CLV means the model identified value before the market corrected.

    Args:
        model_prob: Model's predicted probabilities.
        closing_odds: Pinnacle closing decimal odds.

    Returns:
        Array of per-bet CLV values.

    Raises:
        ValueError: If inputs are empty or different lengths.
    """
    if len(model_prob) == 0:
        msg = "model_prob must not be empty"
        raise ValueError(msg)
    if len(model_prob) != len(closing_odds):
        msg = "model_prob and closing_odds must have same length"
        raise ValueError(msg)
    market_implied = 1.0 / np.asarray(closing_odds, dtype=np.float64)
    return np.asarray(model_prob, dtype=np.float64) - market_implied


def compute_clv_mean(
    model_prob: np.ndarray,
    closing_odds: np.ndarray,
) -> float:
    """Compute mean CLV across all bets.

    Args:
        model_prob: Model's predicted probabilities.
        closing_odds: Pinnacle closing decimal odds.

    Returns:
        Mean CLV (positive = model beats closing line).
    """
    return float(compute_clv(model_prob, closing_odds).mean())


def compute_roi(stakes: np.ndarray, returns: np.ndarray) -> float:
    """Compute Return on Investment.

    ROI = sum(returns) / sum(stakes).

    Args:
        stakes: Amount staked per bet.
        returns: Net profit/loss per bet (positive = win, negative = loss).

    Returns:
        ROI as a fraction (e.g. 0.05 = 5% profit).

    Raises:
        ValueError: If inputs are empty or total stakes is zero.
    """
    if len(stakes) == 0:
        msg = "stakes must not be empty"
        raise ValueError(msg)
    total_staked = float(np.sum(stakes))
    if total_staked == 0:
        msg = "total stakes must be positive"
        raise ValueError(msg)
    return float(np.sum(returns)) / total_staked


def compute_sharpe(returns: np.ndarray) -> float:
    """Compute Sharpe ratio of bet returns.

    Not annualized — caller is responsible for annualization if needed.

    Args:
        returns: Per-bet net returns (positive = profit).

    Returns:
        Sharpe ratio (mean / std). Returns 0.0 if std is zero.

    Raises:
        ValueError: If inputs are empty.
    """
    if len(returns) == 0:
        msg = "returns must not be empty"
        raise ValueError(msg)
    std = float(np.std(returns, ddof=1)) if len(returns) > 1 else 0.0
    if std == 0:
        return 0.0
    return float(np.mean(returns)) / std


def compute_max_drawdown(cumulative_pnl: np.ndarray) -> float:
    """Compute maximum peak-to-trough drawdown.

    Args:
        cumulative_pnl: Cumulative profit/loss series (not returns, but equity).

    Returns:
        Max drawdown as a positive fraction (e.g. 0.12 = 12% drawdown).
        Returns 0.0 if equity is monotonically increasing.

    Raises:
        ValueError: If input is empty.
    """
    if len(cumulative_pnl) == 0:
        msg = "cumulative_pnl must not be empty"
        raise ValueError(msg)
    equity = np.asarray(cumulative_pnl, dtype=np.float64)
    running_max = np.maximum.accumulate(equity)
    drawdowns = running_max - equity
    if running_max.max() == 0:
        return 0.0
    return float(drawdowns.max() / running_max.max()) if running_max.max() > 0 else 0.0


def compute_max_losing_streak(outcomes: np.ndarray) -> int:
    """Compute longest consecutive losing bets.

    Args:
        outcomes: Per-bet outcomes (1 = win, 0 = loss).

    Returns:
        Length of longest losing streak. 0 if empty or all wins.
    """
    if len(outcomes) == 0:
        return 0
    max_streak = 0
    current = 0
    for outcome in outcomes:
        if outcome == 0:
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 0
    return max_streak


def compute_hit_rate(outcomes: np.ndarray) -> float:
    """Compute fraction of winning bets.

    Args:
        outcomes: Per-bet outcomes (1 = win, 0 = loss).

    Returns:
        Hit rate as a fraction (e.g. 0.45 = 45% win rate).

    Raises:
        ValueError: If inputs are empty.
    """
    if len(outcomes) == 0:
        msg = "outcomes must not be empty"
        raise ValueError(msg)
    return float(np.mean(outcomes))


def compute_yield(total_profit: float, total_staked: float) -> float:
    """Compute yield (profit per unit staked).

    Args:
        total_profit: Total net profit.
        total_staked: Total amount staked.

    Returns:
        Yield as a fraction.

    Raises:
        ValueError: If total_staked is zero.
    """
    if total_staked == 0:
        msg = "total_staked must be positive"
        raise ValueError(msg)
    return total_profit / total_staked
