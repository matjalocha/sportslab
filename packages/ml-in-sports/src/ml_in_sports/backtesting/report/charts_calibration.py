"""Calibration chart builders: reliability diagram and ECE heatmap.

Transforms fold-level prediction data into Plotly reliability diagrams
and ECE heatmaps for the backtest HTML report.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from ml_in_sports.backtesting.metrics import compute_ece
from ml_in_sports.backtesting.report.charts_utils import (
    BRAND_BORDER,
    COLOR_NEGATIVE,
    COLOR_POSITIVE,
    as_float,
    calibration_vectors,
    compute_multiclass_brier,
    empty_chart,
    model_color,
    nearest_bin_start,
    season_label,
)
from ml_in_sports.backtesting.runner import FoldResult


def build_reliability_data(
    fold_results: list[FoldResult],
    n_bins: int = 10,
) -> dict[str, list[tuple[float, float]]]:
    """Build reliability-curve ``(predicted, actual)`` points per model."""
    bins_by_model = _build_reliability_bins(fold_results, n_bins=n_bins)
    return {
        model_name: [
            (float(point["predicted_mean"]), float(point["actual_frequency"]))
            for point in points
        ]
        for model_name, points in bins_by_model.items()
    }


def build_reliability_diagram(fold_results: list[FoldResult]) -> str:
    """Build a Plotly reliability diagram from fold-level predictions."""
    return _render_reliability_diagram(_build_reliability_bins(fold_results))


def build_reliability_diagram_from_data(
    reliability_data: dict[str, list[tuple[float, float]]],
) -> str:
    """Build a Plotly reliability diagram from pre-computed report data."""
    bins_by_model: dict[str, list[dict[str, float]]] = {}
    for model_name, points in reliability_data.items():
        bins_by_model[model_name] = [
            {
                "bin_start": nearest_bin_start(predicted_mean),
                "bin_end": min(nearest_bin_start(predicted_mean) + 0.1, 1.0),
                "n_samples": float("nan"),
                "predicted_mean": predicted_mean,
                "actual_frequency": actual_frequency,
            }
            for predicted_mean, actual_frequency in points
        ]
    return _render_reliability_diagram(bins_by_model)


def build_ece_heatmap_data(
    fold_results: list[FoldResult],
    model_name: str | None = None,
) -> list[dict[str, object]]:
    """Build ECE rows (league x season) for the selected model."""
    if not fold_results:
        return []

    target_model = model_name or fold_results[0].model_name
    grouped_actuals: dict[tuple[str, str], list[np.ndarray]] = {}
    grouped_predictions: dict[tuple[str, str], list[np.ndarray]] = {}

    for fr in fold_results:
        if fr.model_name != target_model:
            continue
        season = season_label(fr)
        leagues = fr.leagues if fr.leagues is not None else np.full(len(fr.actuals), "All")
        for league in sorted({str(value) for value in leagues}):
            mask = leagues.astype(str) == league
            if not np.any(mask):
                continue
            key = (league, season)
            grouped_actuals.setdefault(key, []).append(fr.actuals[mask])
            grouped_predictions.setdefault(key, []).append(fr.predictions[mask])

    rows: list[dict[str, object]] = []
    for (league, season), actual_parts in sorted(grouped_actuals.items()):
        predictions = np.concatenate(grouped_predictions[(league, season)])
        actuals = np.concatenate(actual_parts)
        rows.append({
            "league": league,
            "season": season,
            "ece": float(compute_ece(actuals, predictions)),
            "n_matches": len(actuals),
            "brier": compute_multiclass_brier(actuals, predictions),
        })
    return rows


def build_ece_heatmap(fold_results: list[FoldResult]) -> str:
    """Build a Plotly ECE heatmap from fold-level predictions."""
    return build_ece_heatmap_from_data(build_ece_heatmap_data(fold_results))


def build_ece_heatmap_from_data(ece_heatmap: list[dict[str, object]]) -> str:
    """Build a Plotly ECE heatmap from pre-computed ECE rows."""
    if not ece_heatmap:
        return empty_chart("ECE heatmap unavailable")

    seasons = sorted({str(row["season"]) for row in ece_heatmap})
    leagues = sorted({str(row["league"]) for row in ece_heatmap})
    cell_by_key = {(str(row["league"]), str(row["season"])): row for row in ece_heatmap}

    z: list[list[float | None]] = []
    customdata: list[list[list[float]]] = []
    for league in leagues:
        z_row: list[float | None] = []
        custom_row: list[list[float]] = []
        for season in seasons:
            row = cell_by_key.get((league, season))
            if row is None:
                z_row.append(None)
                custom_row.append([float("nan"), 0.0])
                continue
            z_row.append(as_float(row["ece"]))
            custom_row.append(
                [as_float(row.get("brier", float("nan"))), as_float(row["n_matches"], 0.0)]
            )
        z.append(z_row)
        customdata.append(custom_row)

    fig = go.Figure(
        data=go.Heatmap(
            x=seasons, y=leagues, z=z, customdata=customdata,
            colorscale=[
                [0.0, COLOR_POSITIVE], [0.5, COLOR_POSITIVE],
                [2.0 / 3.0, "#FFFFFF"], [1.0, COLOR_NEGATIVE],
            ],
            zmin=0.0, zmax=0.03,
            colorbar={"title": "ECE", "tickformat": ".1%"},
            hovertemplate=(
                "<span style='font-family: JetBrains Mono'>"
                "League: %{y}<br>Season: %{x}<br>"
                "ECE: %{z:.2%}<br>Brier: %{customdata[0]:.4f}<br>"
                "n_matches: %{customdata[1]:,.0f}"
                "</span><extra></extra>"
            ),
        )
    )
    fig.update_layout(
        title="ECE Heatmap by League x Season",
        template="plotly_white",
        font={"family": "Inter, sans-serif", "size": 12},
        hoverlabel={"font": {"family": "JetBrains Mono, monospace", "size": 12}},
        height=420,
        margin={"t": 60, "r": 30, "b": 50, "l": 120},
        xaxis={"title": "Season", "gridcolor": BRAND_BORDER, "gridwidth": 0.5,
               "tickfont": {"family": "Inter, sans-serif", "size": 12}},
        yaxis={"title": "League", "gridcolor": BRAND_BORDER, "gridwidth": 0.5,
               "tickfont": {"family": "Inter, sans-serif", "size": 12}},
    )
    return str(fig.to_html(full_html=False, include_plotlyjs=False))


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _build_reliability_bins(
    fold_results: list[FoldResult],
    n_bins: int = 10,
) -> dict[str, list[dict[str, float]]]:
    """Build detailed reliability bins for hover-rich Plotly rendering."""
    model_probabilities: dict[str, list[np.ndarray]] = {}
    model_outcomes: dict[str, list[np.ndarray]] = {}

    for fr in fold_results:
        probabilities, outcomes = calibration_vectors(fr.predictions, fr.actuals)
        model_probabilities.setdefault(fr.model_name, []).append(probabilities)
        model_outcomes.setdefault(fr.model_name, []).append(outcomes)

    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    bins_by_model: dict[str, list[dict[str, float]]] = {}

    for model_name, probability_parts in model_probabilities.items():
        probabilities = np.concatenate(probability_parts)
        outcomes = np.concatenate(model_outcomes[model_name])
        model_bins: list[dict[str, float]] = []
        for i in range(n_bins):
            lower, upper = float(bin_edges[i]), float(bin_edges[i + 1])
            mask = (
                (probabilities >= lower) & (probabilities <= upper)
                if i == n_bins - 1
                else (probabilities >= lower) & (probabilities < upper)
            )
            if not np.any(mask):
                continue
            model_bins.append({
                "bin_start": lower,
                "bin_end": upper,
                "n_samples": float(mask.sum()),
                "predicted_mean": float(probabilities[mask].mean()),
                "actual_frequency": float(outcomes[mask].mean()),
            })
        bins_by_model[model_name] = model_bins
    return bins_by_model


def _render_reliability_diagram(
    bins_by_model: dict[str, list[dict[str, float]]],
) -> str:
    """Render detailed reliability bins as a Plotly HTML div."""
    if not bins_by_model:
        return empty_chart("Reliability diagram unavailable")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[0.0, 1.0], y=[0.0, 1.0], mode="lines",
        name="Perfect calibration",
        line={"color": "rgba(0,0,0,0.5)", "dash": "dash", "width": 1},
        hoverinfo="skip",
    ))

    for idx, (model_name, points) in enumerate(bins_by_model.items()):
        if not points:
            continue
        fig.add_trace(go.Scatter(
            x=[p["predicted_mean"] for p in points],
            y=[p["actual_frequency"] for p in points],
            customdata=[[p["bin_start"], p["bin_end"], p["n_samples"]] for p in points],
            mode="lines+markers", name=model_name,
            line={"color": model_color(model_name, idx), "width": 2},
            marker={"size": 7, "color": model_color(model_name, idx)},
            hovertemplate=(
                "<span style='font-family: JetBrains Mono'>"
                "Bin: %{customdata[0]:.0%}-%{customdata[1]:.0%}<br>"
                "n_samples: %{customdata[2]:,.0f}<br>"
                "predicted mean: %{x:.2%}<br>actual freq: %{y:.2%}"
                "</span><extra>%{fullData.name}</extra>"
            ),
        ))

    fig.update_layout(
        title="Reliability Diagram",
        xaxis_title="Predicted probability", yaxis_title="Actual frequency",
        template="plotly_white",
        font={"family": "Inter, sans-serif", "size": 12},
        hoverlabel={"font": {"family": "JetBrains Mono, monospace", "size": 12}},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02,
                "x": 0.5, "xanchor": "center"},
        height=420, margin={"t": 70, "r": 30, "b": 55, "l": 70},
        xaxis={"range": [0.0, 1.0], "tickformat": ".0%",
               "gridcolor": BRAND_BORDER, "gridwidth": 0.5,
               "tickfont": {"family": "Inter, sans-serif", "size": 12}},
        yaxis={"range": [0.0, 1.0], "tickformat": ".0%",
               "gridcolor": BRAND_BORDER, "gridwidth": 0.5,
               "tickfont": {"family": "Inter, sans-serif", "size": 12}},
    )
    return str(fig.to_html(full_html=False, include_plotlyjs=False))
