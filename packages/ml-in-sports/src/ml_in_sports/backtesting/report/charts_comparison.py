"""Model comparison chart builders: radar chart, pairwise matrix, and table.

Produces Plotly radar and heatmap charts that compare model performance
across multiple metrics, plus the ``ModelComparisonRow`` table builder.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from ml_in_sports.backtesting.report.charts_utils import (
    BRAND_BORDER,
    COLOR_NEGATIVE,
    COLOR_POSITIVE,
    base_chart_layout,
    empty_chart,
    hex_to_rgba,
    model_color,
    percentile_scores,
)
from ml_in_sports.backtesting.report.generator import ModelComparisonRow
from ml_in_sports.backtesting.runner import FoldResult
from ml_in_sports.backtesting.simulation import simulate_bet_outcomes


def build_model_comparison(
    aggregate: dict[str, dict[str, float]],
    fold_results: list[FoldResult],
) -> list[ModelComparisonRow]:
    """Build model comparison table rows sorted by CLV descending.

    Args:
        aggregate: Aggregate metrics keyed by model name.
        fold_results: Per-fold per-model results for computing hit rate.

    Returns:
        Sorted list of ``ModelComparisonRow`` (best CLV first).
    """
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
                hit_rate=_compute_hit_rate_for_model(fold_results, model_name),
                n_bets=n_bets,
            )
        )

    return sorted(rows, key=lambda r: r.clv, reverse=True)


def build_radar_chart(model_comparison: list[ModelComparisonRow]) -> str:
    """Build a Plotly radar chart from model comparison rows.

    Normalizes each metric to a 0--1 percentile scale so that models
    can be compared visually across heterogeneous metrics.

    Args:
        model_comparison: Rows from ``build_model_comparison``.

    Returns:
        Plotly HTML div string.
    """
    if not model_comparison:
        return empty_chart("Radar chart unavailable")

    dimensions = [
        ("log_loss", "Log Loss inv", True),
        ("ece", "ECE inv", True),
        ("clv", "CLV", False),
        ("roi", "ROI", False),
        ("sharpe", "Sharpe", False),
        ("hit_rate", "Hit Rate", False),
    ]
    labels = [label for _key, label, _invert in dimensions]
    scores_by_metric = {
        key: percentile_scores(
            [float(getattr(row, key)) for row in model_comparison],
            lower_is_better=invert,
        )
        for key, _label, invert in dimensions
    }

    fig = go.Figure()
    for idx, row in enumerate(model_comparison):
        values = [scores_by_metric[key][idx] for key, _label, _invert in dimensions]
        closed_values = [*values, values[0]]
        closed_labels = [*labels, labels[0]]
        fig.add_trace(
            go.Scatterpolar(
                r=closed_values,
                theta=closed_labels,
                fill="toself",
                name=row.model,
                line={"color": model_color(row.model, idx), "width": 2},
                fillcolor=hex_to_rgba(model_color(row.model, idx), 0.12),
                customdata=[
                    row.log_loss,
                    row.ece,
                    row.clv,
                    row.roi,
                    row.sharpe,
                    row.hit_rate,
                    row.log_loss,
                ],
                hovertemplate=(
                    "<span style='font-family: JetBrains Mono'>"
                    "%{theta}<br>"
                    "score: %{r:.2f}<br>"
                    "raw: %{customdata:.4f}"
                    "</span><extra>%{fullData.name}</extra>"
                ),
            )
        )

    fig.update_layout(
        title="Model Comparison Radar",
        polar={
            "radialaxis": {
                "visible": True,
                "range": [0.0, 1.0],
                "gridcolor": BRAND_BORDER,
                "gridwidth": 0.5,
                "tickfont": {"family": "Inter, sans-serif", "size": 12},
            },
            "angularaxis": {
                "gridcolor": BRAND_BORDER,
                "gridwidth": 0.5,
                "tickfont": {"family": "Inter, sans-serif", "size": 12},
            },
        },
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "x": 0.5,
            "xanchor": "center",
        },
        **base_chart_layout(height=430, margin={"t": 80, "r": 30, "b": 40, "l": 30}),
    )
    return str(fig.to_html(full_html=False, include_plotlyjs=False))


def build_pairwise_matrix(aggregate_metrics: dict[str, dict[str, float]]) -> str:
    """Build a triangular pairwise log-loss delta heatmap.

    Lower-triangle cells show ``column_log_loss - row_log_loss``.
    Positive values (green) mean the row model is better.

    Args:
        aggregate_metrics: Aggregate metrics keyed by model name.

    Returns:
        Plotly HTML div string.
    """
    if len(aggregate_metrics) < 2:
        return empty_chart("Pairwise matrix requires at least two models")

    models = list(aggregate_metrics)
    deltas: list[float] = []
    z: list[list[float | None]] = []
    customdata: list[list[list[float | str]]] = []

    for row_idx, row_model in enumerate(models):
        z_row: list[float | None] = []
        custom_row: list[list[float | str]] = []
        row_ll = float(aggregate_metrics[row_model].get("log_loss", float("nan")))
        for col_idx, col_model in enumerate(models):
            col_ll = float(aggregate_metrics[col_model].get("log_loss", float("nan")))
            if row_idx <= col_idx or not np.isfinite(row_ll) or not np.isfinite(col_ll):
                z_row.append(None)
                custom_row.append([row_ll, col_ll, ""])
                continue

            delta = col_ll - row_ll
            z_row.append(delta)
            deltas.append(abs(delta))
            custom_row.append([row_ll, col_ll, "row better" if delta > 0 else "column better"])
        z.append(z_row)
        customdata.append(custom_row)

    max_abs_delta = max(deltas) if deltas else 0.001
    fig = go.Figure(
        data=go.Heatmap(
            x=models,
            y=models,
            z=z,
            customdata=customdata,
            colorscale=[
                [0.0, COLOR_NEGATIVE],
                [0.5, "#FFFFFF"],
                [1.0, COLOR_POSITIVE],
            ],
            zmin=-max_abs_delta,
            zmax=max_abs_delta,
            colorbar={"title": "Delta LL", "tickformat": ".4f"},
            hovertemplate=(
                "<span style='font-family: JetBrains Mono'>"
                "row: %{y}<br>"
                "column: %{x}<br>"
                "delta LL: %{z:.4f}<br>"
                "row LL: %{customdata[0]:.4f}<br>"
                "column LL: %{customdata[1]:.4f}<br>"
                "%{customdata[2]}"
                "</span><extra></extra>"
            ),
        )
    )
    fig.update_layout(
        title="Pairwise Log Loss Matrix",
        xaxis_title="Column model",
        yaxis_title="Row model",
        **base_chart_layout(height=430, margin={"t": 70, "r": 30, "b": 90, "l": 110}),
    )
    fig.update_xaxes(gridcolor=BRAND_BORDER, gridwidth=0.5)
    fig.update_yaxes(gridcolor=BRAND_BORDER, gridwidth=0.5, autorange="reversed")
    return str(fig.to_html(full_html=False, include_plotlyjs=False))


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _compute_hit_rate_for_model(
    fold_results: list[FoldResult],
    model_name: str,
) -> float:
    """Compute hit rate for model-selected outcomes across all folds.

    Args:
        fold_results: All fold results.
        model_name: Target model name.

    Returns:
        Float hit rate in ``[0, 1]``.
    """
    outcomes = [
        simulate_bet_outcomes(fr.predictions, fr.actuals)
        for fr in fold_results
        if fr.model_name == model_name
    ]
    if not outcomes:
        return 0.0
    return float(np.mean(np.concatenate(outcomes)))
