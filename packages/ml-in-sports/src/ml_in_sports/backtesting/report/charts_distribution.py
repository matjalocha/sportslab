"""Distribution chart builders: Kelly fractions, edge per market, bets heatmap.

Builds Plotly histograms, box plots, and heatmaps that show the
distribution of betting activity across the backtest.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from ml_in_sports.backtesting.report.charts_utils import (
    BRAND_BORDER,
    FALLBACK_COLORS,
    base_chart_layout,
    bet_prob_and_odds,
    empty_chart,
    inferred_market_label,
    season_label,
    select_model_folds,
)
from ml_in_sports.backtesting.runner import FoldResult


def build_kelly_distribution(
    fold_results: list[FoldResult],
    odds: np.ndarray | None = None,
    model_name: str | None = None,
) -> str:
    """Build a Plotly histogram of quarter-Kelly stake fractions.

    Args:
        fold_results: Per-fold per-model results from the walk-forward runner.
        odds: Optional external odds array override.
        model_name: Which model to compute for; defaults to first model.

    Returns:
        Plotly HTML div string.
    """
    fractions = _collect_kelly_fractions(fold_results, odds=odds, model_name=model_name)
    if len(fractions) == 0:
        return empty_chart("Kelly distribution unavailable (odds missing)")

    percentages = fractions * 100.0
    mean_pct = float(np.mean(percentages))
    median_pct = float(np.median(percentages))

    fig = go.Figure(
        data=go.Histogram(
            x=percentages,
            nbinsx=20,
            marker={"color": "#2D7DD2", "line": {"color": "#FFFFFF", "width": 1}},
            hovertemplate=(
                "<span style='font-family: JetBrains Mono'>"
                "Kelly fraction: %{x:.2f}%<br>"
                "count: %{y:,}"
                "</span><extra></extra>"
            ),
        )
    )
    fig.add_vline(
        x=mean_pct,
        line_dash="dash",
        line_color="#1B2A4A",
        opacity=0.7,
        annotation_text=f"mean {mean_pct:.2f}%",
        annotation_position="top right",
    )
    fig.add_vline(
        x=median_pct,
        line_dash="dot",
        line_color="#9A6700",
        opacity=0.7,
        annotation_text=f"median {median_pct:.2f}%",
        annotation_position="top left",
    )
    fig.update_layout(
        title="Kelly Fraction Distribution",
        xaxis_title="Kelly fraction (%)",
        yaxis_title="Count",
        **base_chart_layout(height=360, margin={"t": 70, "r": 25, "b": 55, "l": 55}),
    )
    fig.update_xaxes(rangemode="tozero", gridcolor=BRAND_BORDER, gridwidth=0.5)
    fig.update_yaxes(rangemode="tozero", gridcolor=BRAND_BORDER, gridwidth=0.5)
    return str(fig.to_html(full_html=False, include_plotlyjs=False))


def build_edge_per_market(
    fold_results: list[FoldResult],
    model_name: str | None = None,
) -> str:
    """Build a Plotly box plot of edge by market type.

    Args:
        fold_results: Per-fold per-model results from the walk-forward runner.
        model_name: Which model to compute for; defaults to first model.

    Returns:
        Plotly HTML div string.
    """
    market_edges = _collect_edge_by_market(fold_results, model_name=model_name)
    if not market_edges:
        return empty_chart("Edge per market unavailable (odds missing)")

    fig = go.Figure()
    for idx, (market, edges) in enumerate(sorted(market_edges.items())):
        fig.add_trace(
            go.Box(
                x=[market] * len(edges),
                y=(np.asarray(edges) * 100.0).tolist(),
                name=market,
                marker={"color": FALLBACK_COLORS[idx % len(FALLBACK_COLORS)]},
                line={"color": FALLBACK_COLORS[idx % len(FALLBACK_COLORS)]},
                boxmean=True,
                hovertemplate=(
                    "<span style='font-family: JetBrains Mono'>"
                    "market: %{x}<br>"
                    "edge: %{y:.2f}%"
                    "</span><extra></extra>"
                ),
            )
        )

    fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.3)
    fig.update_layout(
        title="Edge Distribution per Market (inferred)",
        xaxis_title="Market type",
        yaxis_title="Edge (%)",
        showlegend=False,
        **base_chart_layout(height=360, margin={"t": 70, "r": 25, "b": 55, "l": 60}),
    )
    fig.update_xaxes(gridcolor=BRAND_BORDER, gridwidth=0.5)
    fig.update_yaxes(zeroline=True, gridcolor=BRAND_BORDER, gridwidth=0.5)
    return str(fig.to_html(full_html=False, include_plotlyjs=False))


def build_bets_heatmap(
    fold_results: list[FoldResult],
    model_name: str | None = None,
) -> str:
    """Build a Plotly heatmap of bet counts by league and season.

    Args:
        fold_results: Per-fold per-model results from the walk-forward runner.
        model_name: Which model to compute for; defaults to first model.

    Returns:
        Plotly HTML div string.
    """
    selected = select_model_folds(fold_results, model_name=model_name)
    if not selected:
        return empty_chart("Bets heatmap unavailable")

    counts: dict[tuple[str, str], int] = {}
    for fr in selected:
        season = season_label(fr)
        fold_leagues = (
            fr.leagues if fr.leagues is not None else np.full(len(fr.actuals), "All")
        )
        for league in fold_leagues:
            key = (str(league), season)
            counts[key] = counts.get(key, 0) + 1

    if not counts:
        return empty_chart("Bets heatmap unavailable")

    seasons = sorted({season for _league, season in counts})
    leagues = sorted({league for league, _season in counts})
    z = [[counts.get((league, season), 0) for season in seasons] for league in leagues]

    fig = go.Figure(
        data=go.Heatmap(
            x=seasons,
            y=leagues,
            z=z,
            colorscale=[[0.0, "#FFFFFF"], [1.0, "#2D7DD2"]],
            colorbar={"title": "Bets"},
            hovertemplate=(
                "<span style='font-family: JetBrains Mono'>"
                "League: %{y}<br>"
                "Season: %{x}<br>"
                "Bets: %{z:,}"
                "</span><extra></extra>"
            ),
        )
    )
    fig.update_layout(
        title="Bets per League x Season",
        xaxis_title="Season",
        yaxis_title="League",
        **base_chart_layout(height=360, margin={"t": 70, "r": 25, "b": 55, "l": 110}),
    )
    fig.update_xaxes(gridcolor=BRAND_BORDER, gridwidth=0.5)
    fig.update_yaxes(gridcolor=BRAND_BORDER, gridwidth=0.5)
    return str(fig.to_html(full_html=False, include_plotlyjs=False))


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _collect_kelly_fractions(
    fold_results: list[FoldResult],
    odds: np.ndarray | None = None,
    model_name: str | None = None,
    kelly_fraction: float = 0.25,
    max_exposure_per_match: float = 0.03,
) -> np.ndarray:
    """Collect capped quarter-Kelly fractions for the selected model."""
    parts: list[np.ndarray] = []
    for fr in select_model_folds(fold_results, model_name=model_name):
        bet_data = bet_prob_and_odds(fr, odds)
        if bet_data is None:
            continue
        fold_bet_prob, fold_bet_odds = bet_data

        raw_fraction = np.zeros_like(fold_bet_odds, dtype=np.float64)
        valid_odds = fold_bet_odds > 1.0
        raw_fraction[valid_odds] = np.maximum(
            (fold_bet_prob[valid_odds] * fold_bet_odds[valid_odds] - 1.0)
            / (fold_bet_odds[valid_odds] - 1.0),
            0.0,
        )
        parts.append(np.minimum(raw_fraction * kelly_fraction, max_exposure_per_match))

    if not parts:
        return np.array([], dtype=np.float64)
    return np.concatenate(parts)


def _collect_edge_by_market(
    fold_results: list[FoldResult],
    model_name: str | None = None,
) -> dict[str, list[float]]:
    """Collect selected-bet edge values under inferred market categories."""
    edges_by_market: dict[str, list[float]] = {}
    for fr in select_model_folds(fold_results, model_name=model_name):
        bet_data = bet_prob_and_odds(fr, odds=None)
        if bet_data is None:
            continue
        fold_bet_prob, fold_bet_odds = bet_data
        market = inferred_market_label(fr.predictions)
        edges = fold_bet_prob - (1.0 / fold_bet_odds)
        edges_by_market.setdefault(market, []).extend(edges.tolist())

    return edges_by_market
