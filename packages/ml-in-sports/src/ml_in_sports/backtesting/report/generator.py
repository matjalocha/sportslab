"""Build pre-computed report data from backtest results.

Transforms raw ``BacktestResult`` into a ``ReportData`` dataclass with
all chart data, verdicts, and summary tables ready for rendering by
the HTML or terminal report modules.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import structlog

from ml_in_sports.backtesting.runner import BacktestResult, FoldResult

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Semaphore thresholds (from design spec section B)
# ---------------------------------------------------------------------------

_CLV_GREEN = 0.0
_CLV_YELLOW = -0.01
_ECE_GREEN = 0.015
_ECE_YELLOW = 0.03
_ROI_GREEN = 0.02
_ROI_YELLOW = -0.02


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class LeagueRow:
    """CLV summary row for a single league."""

    league: str
    n_bets: int
    mean_clv: float
    pct_positive: float
    roi: float


@dataclass
class ModelComparisonRow:
    """One row of the model comparison table."""

    model: str
    log_loss: float
    ece: float
    clv: float
    roi: float
    sharpe: float
    hit_rate: float
    n_bets: int


@dataclass
class FoldDetailRow:
    """Per-season breakdown row."""

    test_season: str
    model: str
    log_loss: float
    ece: float
    clv: float
    roi: float
    n_bets: int


@dataclass
class ReportData:
    """Pre-computed report data ready for rendering.

    All chart series and tables are computed upfront so that
    renderers (HTML, terminal) only need to format and display.
    """

    experiment_name: str
    generated_at: datetime
    duration_seconds: float
    git_hash: str | None

    hero_metrics: dict[str, float]
    verdict_text: str
    semaphore: dict[str, str]

    cumulative_clv: dict[str, list[float]]
    clv_per_league: list[LeagueRow]

    reliability_data: dict[str, list[tuple[float, float]]]
    ece_heatmap: list[dict[str, object]]
    reliability_chart: str
    ece_heatmap_chart: str

    equity_curves: dict[str, list[float]]
    drawdown_series: dict[str, list[float]]
    monthly_returns: list[dict[str, object]]

    kelly_distribution_chart: str
    edge_per_market_chart: str
    bets_heatmap_chart: str

    radar_chart: str
    pairwise_chart: str

    model_comparison: list[ModelComparisonRow]
    fold_details: list[FoldDetailRow]

    n_folds: int
    seasons: list[str]


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def build_report_data(result: BacktestResult) -> ReportData:
    """Transform a BacktestResult into renderable ReportData.

    Args:
        result: Raw backtest result from the walk-forward runner.

    Returns:
        ReportData with all chart data and verdicts pre-computed.
    """
    # Deferred import to avoid circular dependency (charts imports generator types)
    from ml_in_sports.backtesting.report.charts import (
        build_bets_heatmap,
        build_clv_per_league,
        build_cumulative_clv,
        build_ece_heatmap_data,
        build_ece_heatmap_from_data,
        build_edge_per_market,
        build_equity_and_drawdown,
        build_kelly_distribution,
        build_model_comparison,
        build_pairwise_matrix,
        build_radar_chart,
        build_reliability_data,
        build_reliability_diagram,
    )

    aggregate = result.aggregate_metrics
    best_model = _pick_best_model(aggregate) if aggregate else None
    hero = _build_hero_metrics(aggregate, result.fold_results)
    semaphore = _build_semaphore(hero)
    verdict = _build_verdict_text(hero, semaphore)
    equity_curves, drawdown_series = build_equity_and_drawdown(result.fold_results)
    reliability_data = build_reliability_data(result.fold_results)
    ece_heatmap = build_ece_heatmap_data(result.fold_results, model_name=best_model)
    model_comparison = build_model_comparison(aggregate, result.fold_results)

    return ReportData(
        experiment_name=result.config.name,
        generated_at=result.generated_at,
        duration_seconds=result.duration_seconds,
        git_hash=result.git_hash,
        hero_metrics=hero,
        verdict_text=verdict,
        semaphore=semaphore,
        cumulative_clv=build_cumulative_clv(result.fold_results),
        clv_per_league=build_clv_per_league(result.fold_results),
        reliability_data=reliability_data,
        ece_heatmap=ece_heatmap,
        reliability_chart=build_reliability_diagram(result.fold_results),
        ece_heatmap_chart=build_ece_heatmap_from_data(ece_heatmap),
        equity_curves=equity_curves,
        drawdown_series=drawdown_series,
        monthly_returns=[],
        kelly_distribution_chart=build_kelly_distribution(
            result.fold_results, odds=None, model_name=best_model
        ),
        edge_per_market_chart=build_edge_per_market(result.fold_results, model_name=best_model),
        bets_heatmap_chart=build_bets_heatmap(result.fold_results, model_name=best_model),
        radar_chart=build_radar_chart(model_comparison),
        pairwise_chart=build_pairwise_matrix(aggregate),
        model_comparison=model_comparison,
        fold_details=_build_fold_details(result.fold_results),
        n_folds=len({fr.fold_idx for fr in result.fold_results}),
        seasons=result.config.data.seasons,
    )


# ---------------------------------------------------------------------------
# Hero metrics and verdict
# ---------------------------------------------------------------------------


def _build_hero_metrics(
    aggregate: dict[str, dict[str, float]],
    fold_results: list[FoldResult],
) -> dict[str, float]:
    """Build hero metric values from the best model's aggregates."""
    if not aggregate:
        return _empty_hero()

    best_model = _pick_best_model(aggregate)
    metrics = aggregate[best_model]
    n_bets = sum(len(fr.actuals) for fr in fold_results if fr.model_name == best_model)

    return {
        "clv": metrics.get("clv_mean", 0.0),
        "roi": metrics.get("roi", 0.0),
        "sharpe": metrics.get("sharpe", 0.0),
        "ece": metrics.get("ece", 0.0),
        "log_loss": metrics.get("log_loss", 0.0),
        "brier_score": metrics.get("brier_score", 0.0),
        "n_bets": float(n_bets),
        "max_drawdown": metrics.get("max_drawdown", 0.0),
    }


def _empty_hero() -> dict[str, float]:
    """Return zeroed hero metrics for empty results."""
    return {
        "clv": 0.0,
        "roi": 0.0,
        "sharpe": 0.0,
        "ece": 0.0,
        "log_loss": 0.0,
        "brier_score": 0.0,
        "n_bets": 0.0,
        "max_drawdown": 0.0,
    }


def _pick_best_model(aggregate: dict[str, dict[str, float]]) -> str:
    """Pick the model with the highest CLV, or first model."""
    best_name = next(iter(aggregate))
    best_clv = float("-inf")
    for model_name, metrics in aggregate.items():
        clv = metrics.get("clv_mean", float("-inf"))
        if clv > best_clv:
            best_clv = clv
            best_name = model_name
    return best_name


def _build_semaphore(hero: dict[str, float]) -> dict[str, str]:
    """Build traffic-light semaphore from hero metrics."""
    clv = hero.get("clv", 0.0)
    ece = hero.get("ece", 0.0)
    roi = hero.get("roi", 0.0)

    def _clv_color(v: float) -> str:
        if v > _CLV_GREEN:
            return "green"
        return "yellow" if v >= _CLV_YELLOW else "red"

    def _ece_color(v: float) -> str:
        if v < _ECE_GREEN:
            return "green"
        return "yellow" if v <= _ECE_YELLOW else "red"

    def _roi_color(v: float) -> str:
        if v > _ROI_GREEN:
            return "green"
        return "yellow" if v >= _ROI_YELLOW else "red"

    return {
        "clv": _clv_color(clv),
        "ece": _ece_color(ece),
        "roi": _roi_color(roi),
    }


def _build_verdict_text(
    hero: dict[str, float],
    semaphore: dict[str, str],
) -> str:
    """Generate auto-verdict text based on semaphore colors."""
    clv = hero.get("clv", 0.0)
    roi = hero.get("roi", 0.0)
    ece = hero.get("ece", 0.0)

    clv_pct = f"{clv * 100:+.2f}%"
    roi_pct = f"{roi * 100:+.2f}%"
    ece_pct = f"{ece * 100:.2f}%"

    if semaphore["clv"] == "green" and semaphore["roi"] == "green":
        return (
            f"Model beats the closing line (CLV {clv_pct}) with positive "
            f"ROI ({roi_pct}). Calibration ECE at {ece_pct}. "
            f"Results suggest a durable edge."
        )

    if semaphore["clv"] == "red" and semaphore["roi"] == "green":
        return (
            f"Model shows positive ROI ({roi_pct}), but CLV is negative "
            f"({clv_pct}), suggesting profit may stem from variance rather "
            f"than a sustainable edge."
        )

    if semaphore["clv"] == "green" and semaphore["roi"] != "green":
        return (
            f"Model beats the closing line (CLV {clv_pct}), but ROI is "
            f"not yet positive ({roi_pct}). Edge may exist but staking "
            f"or sample size needs review."
        )

    return (
        f"Model does not beat the closing line (CLV {clv_pct}) and ROI "
        f"is {roi_pct}. ECE at {ece_pct}. Consider model or feature "
        f"improvements before live deployment."
    )


def _build_fold_details(fold_results: list[FoldResult]) -> list[FoldDetailRow]:
    """Build per-fold per-model breakdown for season table."""
    rows: list[FoldDetailRow] = []
    for fr in fold_results:
        test_season = fr.test_seasons[-1] if fr.test_seasons else "?"
        rows.append(
            FoldDetailRow(
                test_season=test_season,
                model=fr.model_name,
                log_loss=fr.metrics.get("log_loss", 0.0),
                ece=fr.metrics.get("ece", 0.0),
                clv=fr.metrics.get("clv_mean", 0.0),
                roi=fr.metrics.get("roi", 0.0),
                n_bets=len(fr.actuals),
            )
        )
    return rows
