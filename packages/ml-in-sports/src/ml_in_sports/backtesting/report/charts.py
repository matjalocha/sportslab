"""Chart builders for the backtest report -- thin re-export facade.

All chart functions are implemented in submodules (``charts_calibration``,
``charts_clv``, ``charts_equity``, ``charts_comparison``,
``charts_distribution``).  This module re-exports every public name so
that existing ``from ...charts import X`` statements keep working.
"""

from __future__ import annotations

# --- Calibration ---
from ml_in_sports.backtesting.report.charts_calibration import (
    build_ece_heatmap,
    build_ece_heatmap_data,
    build_ece_heatmap_from_data,
    build_reliability_data,
    build_reliability_diagram,
    build_reliability_diagram_from_data,
)

# --- CLV ---
from ml_in_sports.backtesting.report.charts_clv import (
    build_clv_per_league,
    build_cumulative_clv,
)

# --- Comparison ---
from ml_in_sports.backtesting.report.charts_comparison import (
    build_model_comparison,
    build_pairwise_matrix,
    build_radar_chart,
)

# --- Distribution ---
from ml_in_sports.backtesting.report.charts_distribution import (
    build_bets_heatmap,
    build_edge_per_market,
    build_kelly_distribution,
)

# --- Equity ---
from ml_in_sports.backtesting.report.charts_equity import (
    build_equity_and_drawdown,
)

__all__ = [
    "build_bets_heatmap",
    "build_clv_per_league",
    "build_cumulative_clv",
    "build_ece_heatmap",
    "build_ece_heatmap_data",
    "build_ece_heatmap_from_data",
    "build_edge_per_market",
    "build_equity_and_drawdown",
    "build_kelly_distribution",
    "build_model_comparison",
    "build_pairwise_matrix",
    "build_radar_chart",
    "build_reliability_data",
    "build_reliability_diagram",
    "build_reliability_diagram_from_data",
]
