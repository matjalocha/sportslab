"""Chart data builders for the backtest report.

Transforms fold-level data into pre-computed series suitable for
Plotly rendering or tabular display in the terminal report.
"""

from __future__ import annotations

import numpy as np
import structlog

from ml_in_sports.backtesting.report.generator import LeagueRow, ModelComparisonRow
from ml_in_sports.backtesting.runner import FoldResult
from ml_in_sports.backtesting.simulation import simulate_kelly_betting

logger = structlog.get_logger(__name__)

_KELLY_STRATEGIES: list[tuple[str, float]] = [
    ("Quarter-Kelly", 0.25),
    ("Half-Kelly", 0.50),
]


def build_cumulative_clv(
    fold_results: list[FoldResult],
) -> dict[str, list[float]]:
    """Build cumulative CLV series per model."""
    model_clvs: dict[str, list[float]] = {}

    for fr in fold_results:
        if fr.odds is None:
            continue

        actuals = fr.actuals
        n = len(actuals)
        idx = np.arange(n)

        pred_prob = (
            fr.predictions[idx, actuals.astype(int)] if fr.predictions.ndim == 2 else fr.predictions
        )
        actual_odds = fr.odds[idx, actuals.astype(int)] if fr.odds.ndim == 2 else fr.odds
        clv_per_bet = pred_prob - (1.0 / actual_odds)

        if fr.model_name not in model_clvs:
            model_clvs[fr.model_name] = []
        model_clvs[fr.model_name].extend(clv_per_bet.tolist())

    return {model_name: np.cumsum(clvs).tolist() for model_name, clvs in model_clvs.items()}


def build_clv_per_league(
    fold_results: list[FoldResult],
) -> list[LeagueRow]:
    """Aggregate CLV stats per league across all folds and models."""
    league_data: dict[str, dict[str, list[float]]] = {}

    for fr in fold_results:
        if fr.odds is None or fr.leagues is None:
            continue

        actuals = fr.actuals
        n = len(actuals)
        idx = np.arange(n)

        pred_prob = (
            fr.predictions[idx, actuals.astype(int)] if fr.predictions.ndim == 2 else fr.predictions
        )
        actual_odds = fr.odds[idx, actuals.astype(int)] if fr.odds.ndim == 2 else fr.odds
        clv_per_bet = pred_prob - (1.0 / actual_odds)

        bet_class = (
            fr.predictions.argmax(axis=1)
            if fr.predictions.ndim == 2
            else (fr.predictions > 0.5).astype(int)
        )
        bet_odds = fr.odds[idx, bet_class] if fr.odds.ndim == 2 else fr.odds
        won = (bet_class == actuals).astype(float)
        returns = won * (bet_odds - 1.0) - (1.0 - won)

        for i, league in enumerate(fr.leagues):
            league_str = str(league)
            if league_str not in league_data:
                league_data[league_str] = {"clv": [], "returns": []}
            league_data[league_str]["clv"].append(float(clv_per_bet[i]))
            league_data[league_str]["returns"].append(float(returns[i]))

    rows: list[LeagueRow] = []
    for league_name in sorted(league_data.keys()):
        clvs = np.array(league_data[league_name]["clv"])
        rets = np.array(league_data[league_name]["returns"])
        rows.append(
            LeagueRow(
                league=league_name,
                n_bets=len(clvs),
                mean_clv=float(np.mean(clvs)),
                pct_positive=float((clvs > 0).mean() * 100),
                roi=float(np.sum(rets) / len(rets)) if len(rets) > 0 else 0.0,
            )
        )

    return rows


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
        fold_results: Per-fold per-model results from the walk-forward
            runner.
        initial_bankroll: Starting bankroll for Kelly simulations.

    Returns:
        ``(equity_curves, drawdown_series)`` -- dicts mapping the
        composite key to a list of floats.
    """
    # --- Collect per-model fold data in chronological order ---
    model_folds: dict[str, list[FoldResult]] = {}
    for fr in fold_results:
        model_folds.setdefault(fr.model_name, []).append(fr)

    equity_curves: dict[str, list[float]] = {}
    drawdown_series: dict[str, list[float]] = {}

    for model_name, folds in model_folds.items():
        # --- Flat (1 unit) equity curve ---
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

        flat_key = f"{model_name} | Flat (1 unit)"
        flat_arr = np.array(flat_returns)
        flat_equity = initial_bankroll + np.cumsum(flat_arr)
        equity_curves[flat_key] = flat_equity.tolist()
        drawdown_series[flat_key] = _compute_drawdown(flat_equity).tolist()

        # --- Kelly strategies ---
        for strategy_label, fraction in _KELLY_STRATEGIES:
            kelly_key = f"{model_name} | {strategy_label}"
            kelly_bankroll_parts: list[np.ndarray] = []
            running_bankroll = initial_bankroll

            for fr in folds:
                bankroll_hist, _bet_returns = simulate_kelly_betting(
                    predictions=fr.predictions,
                    actuals=fr.actuals,
                    odds=fr.odds,
                    kelly_fraction=fraction,
                    initial_bankroll=running_bankroll,
                )
                kelly_bankroll_parts.append(bankroll_hist)
                # Carry the final bankroll forward to the next fold
                running_bankroll = float(bankroll_hist[-1])

            kelly_equity = np.concatenate(kelly_bankroll_parts)
            equity_curves[kelly_key] = kelly_equity.tolist()
            drawdown_series[kelly_key] = _compute_drawdown(kelly_equity).tolist()

            logger.debug(
                "kelly_equity_curve_built",
                model=model_name,
                strategy=strategy_label,
                final_bankroll=round(float(kelly_equity[-1]), 2),
                n_bets=len(kelly_equity),
            )

    return equity_curves, drawdown_series


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


def build_model_comparison(
    aggregate: dict[str, dict[str, float]],
    fold_results: list[FoldResult],
) -> list[ModelComparisonRow]:
    """Build model comparison table rows sorted by CLV descending."""
    rows: list[ModelComparisonRow] = []

    for model_name, metrics in aggregate.items():
        n_bets = sum(len(fr.actuals) for fr in fold_results if fr.model_name == model_name)
        rows.append(
            ModelComparisonRow(
                model=model_name,
                log_loss=metrics.get("log_loss", 0.0),
                ece=metrics.get("ece", 0.0),
                clv=metrics.get("clv_mean", 0.0),
                roi=metrics.get("roi", 0.0),
                sharpe=metrics.get("sharpe", 0.0),
                n_bets=n_bets,
            )
        )

    return sorted(rows, key=lambda r: r.clv, reverse=True)
