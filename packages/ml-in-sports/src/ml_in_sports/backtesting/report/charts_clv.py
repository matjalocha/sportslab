"""CLV chart builders: cumulative CLV and per-league CLV breakdown.

Transforms fold-level prediction and odds data into cumulative CLV
series and league-level summary rows for the backtest report.
"""

from __future__ import annotations

import numpy as np

from ml_in_sports.backtesting.report.generator import LeagueRow
from ml_in_sports.backtesting.runner import FoldResult


def build_cumulative_clv(
    fold_results: list[FoldResult],
) -> dict[str, list[float]]:
    """Build cumulative CLV series per model.

    For each model, computes per-bet CLV (predicted probability minus
    implied probability from odds) and returns the running cumulative sum.

    Args:
        fold_results: Per-fold per-model results from the walk-forward runner.

    Returns:
        Dict mapping model name to cumulative CLV series.
    """
    model_clvs: dict[str, list[float]] = {}

    for fr in fold_results:
        if fr.odds is None:
            continue

        actuals = fr.actuals
        n = len(actuals)
        idx = np.arange(n)

        pred_prob = (
            fr.predictions[idx, actuals.astype(int)]
            if fr.predictions.ndim == 2
            else fr.predictions
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
    """Aggregate CLV stats per league across all folds and models.

    For each league, computes mean CLV, percentage of positive-CLV bets,
    and overall ROI from flat staking.

    Args:
        fold_results: Per-fold per-model results from the walk-forward runner.

    Returns:
        List of ``LeagueRow`` sorted by league name.
    """
    league_data: dict[str, dict[str, list[float]]] = {}

    for fr in fold_results:
        if fr.odds is None or fr.leagues is None:
            continue

        actuals = fr.actuals
        n = len(actuals)
        idx = np.arange(n)

        pred_prob = (
            fr.predictions[idx, actuals.astype(int)]
            if fr.predictions.ndim == 2
            else fr.predictions
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
