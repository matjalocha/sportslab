"""Equity curve and drawdown chart builders.

Computes flat-staking and Kelly-strategy equity curves with drawdown
series for each model in the backtest.
"""

from __future__ import annotations

import numpy as np
import structlog

from ml_in_sports.backtesting.runner import FoldResult
from ml_in_sports.backtesting.simulation import simulate_kelly_betting

logger = structlog.get_logger(__name__)

_KELLY_STRATEGIES: list[tuple[str, float]] = [
    ("Quarter-Kelly", 0.25),
    ("Half-Kelly", 0.50),
]


def build_equity_and_drawdown(
    fold_results: list[FoldResult],
    initial_bankroll: float = 1000.0,
) -> tuple[dict[str, list[float]], dict[str, list[float]]]:
    """Build equity curves and drawdown series per model per strategy.

    For each model three strategies are computed:

    * **Flat (1 unit)** -- the original flat-stake approach where
      every bet risks one unit regardless of edge or bankroll.
    * **Quarter-Kelly** -- Kelly fraction multiplied by 0.25.
    * **Half-Kelly** -- Kelly fraction multiplied by 0.50.

    The returned dict keys are formatted as ``"<model> | <strategy>"``
    (e.g. ``"hybrid_v1 | Quarter-Kelly"``).  The flat-bet key is
    ``"<model> | Flat (1 unit)"``.

    Args:
        fold_results: Per-fold per-model results from the walk-forward runner.
        initial_bankroll: Starting bankroll for Kelly simulations.

    Returns:
        ``(equity_curves, drawdown_series)`` -- dicts mapping the
        composite key to a list of floats.
    """
    model_folds: dict[str, list[FoldResult]] = {}
    for fr in fold_results:
        model_folds.setdefault(fr.model_name, []).append(fr)

    equity_curves: dict[str, list[float]] = {}
    drawdown_series: dict[str, list[float]] = {}

    for model_name, folds in model_folds.items():
        flat_equity, flat_drawdown = _build_flat_equity(folds, initial_bankroll)
        flat_key = f"{model_name} | Flat (1 unit)"
        equity_curves[flat_key] = flat_equity
        drawdown_series[flat_key] = flat_drawdown

        for strategy_label, fraction in _KELLY_STRATEGIES:
            kelly_key = f"{model_name} | {strategy_label}"
            kelly_equity, kelly_drawdown = _build_kelly_equity(
                folds, fraction, initial_bankroll
            )
            equity_curves[kelly_key] = kelly_equity
            drawdown_series[kelly_key] = kelly_drawdown

            logger.debug(
                "kelly_equity_curve_built",
                model=model_name,
                strategy=strategy_label,
                final_bankroll=round(kelly_equity[-1], 2) if kelly_equity else 0.0,
                n_bets=len(kelly_equity),
            )

    return equity_curves, drawdown_series


def _build_flat_equity(
    folds: list[FoldResult],
    initial_bankroll: float,
) -> tuple[list[float], list[float]]:
    """Compute flat-staking equity curve and drawdown.

    Each bet risks one unit regardless of edge or bankroll size.

    Args:
        folds: Fold results for a single model, in chronological order.
        initial_bankroll: Starting bankroll value.

    Returns:
        ``(equity_list, drawdown_list)`` as plain Python lists.
    """
    flat_returns: list[float] = []
    for fr in folds:
        actuals = fr.actuals
        bet_class = (
            fr.predictions.argmax(axis=1)
            if fr.predictions.ndim == 2
            else (fr.predictions > 0.5).astype(int)
        )

        if fr.odds is not None and fr.odds.ndim == 2:
            bet_odds = fr.odds[np.arange(len(actuals)), bet_class]
        elif fr.odds is not None:
            bet_odds = fr.odds
        else:
            bet_odds = np.full(len(actuals), 2.0)

        won = (bet_class == actuals).astype(float)
        returns = won * (bet_odds - 1.0) - (1.0 - won)
        flat_returns.extend(returns.tolist())

    flat_arr = np.array(flat_returns)
    flat_equity = initial_bankroll + np.cumsum(flat_arr)
    return flat_equity.tolist(), _compute_drawdown(flat_equity).tolist()


def _build_kelly_equity(
    folds: list[FoldResult],
    kelly_fraction: float,
    initial_bankroll: float,
) -> tuple[list[float], list[float]]:
    """Compute Kelly-strategy equity curve and drawdown.

    Runs the Kelly simulation fold-by-fold, carrying the final bankroll
    forward to the next fold for realistic compounding.

    Args:
        folds: Fold results for a single model, in chronological order.
        kelly_fraction: Kelly multiplier (e.g. 0.25 for quarter-Kelly).
        initial_bankroll: Starting bankroll value.

    Returns:
        ``(equity_list, drawdown_list)`` as plain Python lists.
    """
    kelly_bankroll_parts: list[np.ndarray] = []
    running_bankroll = initial_bankroll

    for fr in folds:
        bankroll_hist, _bet_returns = simulate_kelly_betting(
            predictions=fr.predictions,
            actuals=fr.actuals,
            odds=fr.odds,
            kelly_fraction=kelly_fraction,
            initial_bankroll=running_bankroll,
        )
        kelly_bankroll_parts.append(bankroll_hist)
        running_bankroll = float(bankroll_hist[-1])

    kelly_equity = np.concatenate(kelly_bankroll_parts)
    return kelly_equity.tolist(), _compute_drawdown(kelly_equity).tolist()


def _compute_drawdown(equity: np.ndarray) -> np.ndarray:
    """Compute fractional drawdown series from an equity curve.

    Args:
        equity: Bankroll values over time.

    Returns:
        Array of the same length where each element is the fraction
        the equity is below its running maximum.
    """
    running_max = np.maximum.accumulate(equity)
    drawdown: np.ndarray = (running_max - equity) / np.maximum(running_max, 1e-10)
    return drawdown
