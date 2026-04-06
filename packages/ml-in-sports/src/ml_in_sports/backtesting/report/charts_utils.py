"""Shared helpers, color constants, and layout utilities for report charts.

All chart submodules import from this file rather than duplicating
brand tokens or helper functions.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from ml_in_sports.backtesting.runner import FoldResult

# ---------------------------------------------------------------------------
# Brand color tokens
# ---------------------------------------------------------------------------

BRAND_BORDER = "#E2E5EA"
COLOR_POSITIVE = "#1A7F37"
COLOR_NEGATIVE = "#CF222E"

MODEL_COLORS: dict[str, str] = {
    "lgb": "#2D7DD2",
    "lightgbm": "#2D7DD2",
    "xgb": "#E36209",
    "xgboost": "#E36209",
    "tabpfn": "#8250DF",
    "hybrid": "#1B2A4A",
    "ens": "#1B2A4A",
    "baseline": "#AFB8C1",
    "market": "#AFB8C1",
}

FALLBACK_COLORS = ["#2D7DD2", "#E36209", "#8250DF", "#1B2A4A", "#AFB8C1"]


# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------


def model_color(model_name: str, idx: int = 0) -> str:
    """Return the design-spec hex color for a model name (case-insensitive substring match)."""
    normalized = model_name.lower()
    for token, color in MODEL_COLORS.items():
        if token in normalized:
            return color
    return FALLBACK_COLORS[idx % len(FALLBACK_COLORS)]


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    """Convert ``#RRGGBB`` to ``rgba(r,g,b,alpha)`` for translucent Plotly fills."""
    hex_clean = hex_color.lstrip("#")
    r = int(hex_clean[0:2], 16)
    g = int(hex_clean[2:4], 16)
    b = int(hex_clean[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# ---------------------------------------------------------------------------
# Plotly layout helpers
# ---------------------------------------------------------------------------


def empty_chart(title: str) -> str:
    """Render a compact Plotly empty-state placeholder with the given message."""
    fig = go.Figure()
    fig.add_annotation(
        text=title,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"family": "Inter, sans-serif", "size": 13, "color": "#656D76"},
    )
    fig.update_layout(
        template="plotly_white",
        height=260,
        margin={"t": 30, "r": 30, "b": 30, "l": 30},
        xaxis={"visible": False},
        yaxis={"visible": False},
    )
    return str(fig.to_html(full_html=False, include_plotlyjs=False))


def base_chart_layout(height: int, margin: dict[str, int]) -> dict[str, object]:
    """Return shared Plotly layout keyword dict (template, font, hoverlabel, etc.)."""
    return {
        "template": "plotly_white",
        "font": {"family": "Inter, sans-serif", "size": 12},
        "hoverlabel": {"font": {"family": "JetBrains Mono, monospace", "size": 12}},
        "height": height,
        "margin": margin,
        "xaxis": {"tickfont": {"family": "Inter, sans-serif", "size": 12}},
        "yaxis": {"tickfont": {"family": "Inter, sans-serif", "size": 12}},
    }


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------


def as_float(value: object, default: float = float("nan")) -> float:
    """Coerce a report-row value to float, returning *default* on failure."""
    if value is None:
        return default
    if isinstance(value, str | int | float):
        return float(value)
    return default


def percentile_scores(values: list[float], lower_is_better: bool) -> list[float]:
    """Return 0--1 percentile scores (average-rank ties) for radar charts."""
    if not values:
        return []
    if len(values) == 1:
        return [1.0]

    scoring_values = [-value if lower_is_better else value for value in values]
    scores: list[float] = []
    denominator = len(values) - 1
    for value in scoring_values:
        lower_count = sum(other < value for other in scoring_values)
        equal_count = sum(other == value for other in scoring_values)
        average_rank = lower_count + (equal_count - 1) / 2.0
        scores.append(float(average_rank / denominator))
    return scores


def season_label(fold_result: FoldResult) -> str:
    """Return a display label for a fold's test season (e.g. ``"2023-24"``)."""
    if not fold_result.test_seasons:
        return "?"
    if len(fold_result.test_seasons) == 1:
        return fold_result.test_seasons[0]
    return "+".join(fold_result.test_seasons)


def select_model_folds(
    fold_results: list[FoldResult],
    model_name: str | None = None,
) -> list[FoldResult]:
    """Filter fold results to a single model (defaults to first present)."""
    if not fold_results:
        return []

    target_model = model_name or fold_results[0].model_name
    return [fr for fr in fold_results if fr.model_name == target_model]


def bet_prob_and_odds(
    fold_result: FoldResult,
    odds: np.ndarray | None,
) -> tuple[np.ndarray, np.ndarray] | None:
    """Return ``(bet_prob, bet_odds)`` for one fold, or ``None`` if odds missing."""
    active_odds = fold_result.odds
    if active_odds is None and odds is not None and len(odds) == len(fold_result.actuals):
        active_odds = odds
    if active_odds is None:
        return None

    n = len(fold_result.actuals)
    bet_class = (
        fold_result.predictions.argmax(axis=1)
        if fold_result.predictions.ndim == 2
        else (fold_result.predictions > 0.5).astype(int)
    )

    bet_prob = (
        fold_result.predictions[np.arange(n), bet_class]
        if fold_result.predictions.ndim == 2
        else fold_result.predictions
    )
    bet_odds = active_odds[np.arange(n), bet_class] if active_odds.ndim == 2 else active_odds
    return np.asarray(bet_prob, dtype=np.float64), np.asarray(bet_odds, dtype=np.float64)


def inferred_market_label(predictions: np.ndarray) -> str:
    """Infer a human-readable market label from prediction array shape."""
    if predictions.ndim == 1 or predictions.shape[1] == 2:
        return "Binary (inferred)"
    if predictions.shape[1] == 3:
        return "1X2 (inferred)"
    return f"{predictions.shape[1]}-way (inferred)"


# ---------------------------------------------------------------------------
# Calibration data helpers (used by charts_calibration)
# ---------------------------------------------------------------------------


def calibration_vectors(
    predictions: np.ndarray,
    actuals: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Flatten multiclass predictions into 1-D ``(probabilities, outcomes)`` arrays."""
    probabilities = np.asarray(predictions, dtype=np.float64)
    labels = np.asarray(actuals, dtype=int)

    if probabilities.ndim == 1:
        return probabilities, labels.astype(np.float64)

    n_classes = probabilities.shape[1]
    one_hot = (labels[:, None] == np.arange(n_classes)).astype(np.float64)
    return probabilities.reshape(-1), one_hot.reshape(-1)


def nearest_bin_start(probability: float) -> float:
    """Return the lower bin edge for a 10-bin calibration grid (e.g. 0.3 for 0.35)."""
    return float(np.floor(np.clip(probability, 0.0, 1.0) * 10.0) / 10.0)


def compute_multiclass_brier(actuals: np.ndarray, predictions: np.ndarray) -> float:
    """Compute mean multiclass Brier score (used for heatmap hover context)."""
    probabilities = np.asarray(predictions, dtype=np.float64)
    labels = np.asarray(actuals, dtype=int)

    if probabilities.ndim == 1:
        return float(np.mean((labels.astype(np.float64) - probabilities) ** 2))

    n_classes = probabilities.shape[1]
    one_hot = (labels[:, None] == np.arange(n_classes)).astype(np.float64)
    per_match = np.sum((probabilities - one_hot) ** 2, axis=1) / n_classes
    return float(np.mean(per_match))
