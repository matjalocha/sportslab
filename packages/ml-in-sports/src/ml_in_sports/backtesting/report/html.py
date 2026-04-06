"""Self-contained HTML report renderer using Jinja2 and Plotly.

Generates a single HTML file with embedded CSS, Plotly charts loaded
from CDN, and Google Fonts.  Implements Phase 1 sections:
A (header), B (verdict + hero metrics), D (CLV), E (P&L).
"""

from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go
import structlog
from jinja2 import BaseLoader, Environment

from ml_in_sports.backtesting.report.generator import ReportData

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Color tokens (from design spec)
# ---------------------------------------------------------------------------

_BRAND_PRIMARY = "#1B2A4A"
_BRAND_ACCENT = "#2D7DD2"
_BRAND_SURFACE = "#F7F8FA"
_BRAND_CARD = "#FFFFFF"
_BRAND_BORDER = "#E2E5EA"

_COLOR_POSITIVE = "#1A7F37"
_COLOR_NEGATIVE = "#CF222E"
_COLOR_NEUTRAL = "#9A6700"
_COLOR_MUTED = "#656D76"

_MODEL_COLORS: dict[str, str] = {
    "LightGBM": "#2D7DD2",
    "XGBoost": "#E36209",
    "TabPFN": "#8250DF",
    "Hybrid ENS": _BRAND_PRIMARY,
    "Baseline": "#AFB8C1",
}

_FALLBACK_COLORS = ["#2D7DD2", "#E36209", "#8250DF", _BRAND_PRIMARY, "#AFB8C1"]

_SEMAPHORE_MAP = {
    "green": _COLOR_POSITIVE,
    "yellow": _COLOR_NEUTRAL,
    "red": _COLOR_NEGATIVE,
}


# ---------------------------------------------------------------------------
# Plotly chart builders
# ---------------------------------------------------------------------------


def _model_color(model_name: str, idx: int = 0) -> str:
    """Return the brand color for a model, with fallback rotation."""
    return _MODEL_COLORS.get(model_name, _FALLBACK_COLORS[idx % len(_FALLBACK_COLORS)])


def _hex_to_rgba(hex_color: str, alpha: float = 0.1) -> str:
    """Convert a hex color string to rgba() with the given alpha."""
    hex_clean = hex_color.lstrip("#")
    r = int(hex_clean[0:2], 16)
    g = int(hex_clean[2:4], 16)
    b = int(hex_clean[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _build_cumulative_clv_chart(data: ReportData) -> str:
    """Build Plotly cumulative CLV line chart as HTML div."""
    fig = go.Figure()

    for idx, (model_name, series) in enumerate(data.cumulative_clv.items()):
        fig.add_trace(
            go.Scatter(
                x=list(range(len(series))),
                y=series,
                mode="lines",
                name=model_name,
                line={"color": _model_color(model_name, idx), "width": 2},
                fill="tozeroy",
                fillcolor=_hex_to_rgba(_model_color(model_name, idx), 0.1),
            )
        )

    fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.3)

    fig.update_layout(
        title="Cumulative CLV",
        xaxis_title="Bet #",
        yaxis_title="Cumulative CLV",
        template="plotly_white",
        font={"family": "Inter, sans-serif", "size": 12},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0.5, "xanchor": "center"},
        height=400,
        margin={"t": 60, "r": 30, "b": 50, "l": 60},
        xaxis={"gridcolor": _BRAND_BORDER, "gridwidth": 0.5},
        yaxis={"gridcolor": _BRAND_BORDER, "gridwidth": 0.5},
    )

    return str(fig.to_html(full_html=False, include_plotlyjs=False))


def _build_equity_curve_chart(data: ReportData) -> str:
    """Build Plotly equity curve line chart as HTML div."""
    fig = go.Figure()

    for idx, (model_name, series) in enumerate(data.equity_curves.items()):
        fig.add_trace(
            go.Scatter(
                x=list(range(len(series))),
                y=series,
                mode="lines",
                name=model_name,
                line={"color": _model_color(model_name, idx), "width": 2},
            )
        )

    fig.add_hline(y=1000, line_dash="dash", line_color="black", opacity=0.3)

    fig.update_layout(
        title="Equity Curve (Flat Staking)",
        xaxis_title="Bet #",
        yaxis_title="Bankroll",
        template="plotly_white",
        font={"family": "Inter, sans-serif", "size": 12},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0.5, "xanchor": "center"},
        height=400,
        margin={"t": 60, "r": 30, "b": 50, "l": 60},
        xaxis={"gridcolor": _BRAND_BORDER, "gridwidth": 0.5},
        yaxis={"gridcolor": _BRAND_BORDER, "gridwidth": 0.5},
    )

    return str(fig.to_html(full_html=False, include_plotlyjs=False))


# ---------------------------------------------------------------------------
# Jinja2 HTML template
# ---------------------------------------------------------------------------

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Backtest Report: {{ data.experiment_name }}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js" charset="utf-8"></script>
<style>
:root {
  --brand-primary: {{ brand_primary }};
  --brand-accent: {{ brand_accent }};
  --brand-surface: {{ brand_surface }};
  --brand-card: {{ brand_card }};
  --brand-border: {{ brand_border }};
  --color-positive: {{ color_positive }};
  --color-negative: {{ color_negative }};
  --color-neutral: {{ color_neutral }};
  --color-muted: {{ color_muted }};
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif;
  background: var(--brand-surface);
  color: var(--brand-primary);
  line-height: 1.5;
}
.container { max-width: 1200px; margin: 0 auto; padding: 24px; }

/* Section A: Header */
.header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 24px 0; border-bottom: 2px solid var(--brand-primary);
  margin-bottom: 32px;
}
.header h1 { font-size: 28px; font-weight: 700; }
.header-meta {
  font-size: 12px; color: var(--color-muted);
  font-family: 'JetBrains Mono', monospace; text-align: right;
}

/* Section B: Verdict */
.verdict-banner {
  padding: 16px 24px; border-radius: 8px; margin-bottom: 24px;
  font-size: 14px; line-height: 1.6;
}
.verdict-green { background: #dcfce7; border-left: 4px solid var(--color-positive); }
.verdict-yellow { background: #fef9c3; border-left: 4px solid var(--color-neutral); }
.verdict-red { background: #fef2f2; border-left: 4px solid var(--color-negative); }

.semaphore-row {
  display: flex; gap: 12px; margin-bottom: 24px; flex-wrap: wrap;
}
.semaphore-pill {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 14px; border-radius: 20px; font-size: 13px;
  font-weight: 600; color: #fff;
}
.pill-green { background: var(--color-positive); }
.pill-yellow { background: var(--color-neutral); }
.pill-red { background: var(--color-negative); }

.hero-grid {
  display: grid; grid-template-columns: repeat(4, 1fr);
  gap: 16px; margin-bottom: 32px;
}
@media (max-width: 900px) { .hero-grid { grid-template-columns: repeat(2, 1fr); } }

.hero-card {
  background: var(--brand-card); border: 1px solid var(--brand-border);
  border-radius: 8px; padding: 16px; text-align: center;
  transition: box-shadow 0.15s;
}
.hero-card:hover { box-shadow: 0 2px 8px rgba(27,42,74,0.08); }
.hero-label { font-size: 12px; color: var(--color-muted); text-transform: uppercase; letter-spacing: 0.05em; cursor: help; }
.tooltip-text { font-size: 11px; color: var(--color-muted); font-style: italic; margin-top: 2px; display: none; }
.hero-card:hover .tooltip-text { display: block; }
.hero-value {
  font-family: 'JetBrains Mono', monospace; font-size: 22px;
  font-weight: 500; margin: 4px 0;
}
.hero-border-green { border-left: 3px solid var(--color-positive); }
.hero-border-yellow { border-left: 3px solid var(--color-neutral); }
.hero-border-red { border-left: 3px solid var(--color-negative); }
.hero-border-none { border-left: 3px solid var(--brand-border); }

/* Sections */
.section { margin-bottom: 40px; }
.section h2 {
  font-size: 22px; font-weight: 600; margin-bottom: 16px;
  padding-bottom: 8px; border-bottom: 1px solid var(--brand-border);
}

/* Tables */
.report-table {
  width: 100%; border-collapse: collapse;
  background: var(--brand-card); border-radius: 8px;
  overflow: hidden; border: 1px solid var(--brand-border);
}
.report-table th {
  background: var(--brand-primary); color: #fff;
  padding: 10px 14px; font-size: 12px; text-transform: uppercase;
  letter-spacing: 0.05em; text-align: left;
}
.report-table td {
  padding: 10px 14px; font-family: 'JetBrains Mono', monospace;
  font-size: 13px; border-bottom: 1px solid var(--brand-border);
}
.report-table tr:last-child td { border-bottom: none; }
.report-table tr:hover td { background: var(--brand-surface); }
.text-positive { color: var(--color-positive); }
.text-negative { color: var(--color-negative); }
.text-muted { color: var(--color-muted); }

/* Chart containers */
.chart-container {
  background: var(--brand-card); border: 1px solid var(--brand-border);
  border-radius: 8px; padding: 16px; margin-bottom: 24px;
}

/* Footer */
.footer {
  text-align: center; padding: 24px 0; margin-top: 40px;
  border-top: 1px solid var(--brand-border);
  font-size: 12px; color: var(--color-muted);
}
</style>
</head>
<body>
<div class="container">

<!-- Section A: Header -->
<div class="header">
  <div>
    <h1>{{ data.experiment_name }}</h1>
    <span style="font-size:13px;color:var(--color-muted);">Backtest Report</span>
  </div>
  <div class="header-meta">
    {{ data.generated_at.strftime('%Y-%m-%d %H:%M UTC') }}<br>
    Duration: {{ "%.1f"|format(data.duration_seconds) }}s
    {% if data.git_hash %}<br>{{ data.git_hash }}{% endif %}
  </div>
</div>

<!-- Section B: Verdict -->
<div class="section">
  <h2>Executive Summary</h2>

  {% set worst = 'green' %}
  {% for key, color in data.semaphore.items() %}
    {% if color == 'red' %}{% set worst = 'red' %}
    {% elif color == 'yellow' and worst != 'red' %}{% set worst = 'yellow' %}
    {% endif %}
  {% endfor %}
  <div class="verdict-banner verdict-{{ overall_color }}">
    {{ data.verdict_text }}
  </div>

  <div class="semaphore-row">
    {% for key, color in data.semaphore.items() %}
    <span class="semaphore-pill pill-{{ color }}">
      {{ key|upper }}: {{ ("%.2f%%"|format(data.hero_metrics[key] * 100)) if key != 'n_bets' else data.hero_metrics.get(key, 0)|int }}
    </span>
    {% endfor %}
  </div>

  <div class="hero-grid">
    {% for metric_key, label, fmt in hero_cards %}
    <div class="hero-card hero-border-{{ hero_borders.get(metric_key, 'none') }}">
      <div class="hero-label" title="{{ metric_descriptions.get(metric_key, '') }}">{{ label }}</div>
      <div class="hero-value">{{ fmt }}</div>
      <div class="tooltip-text">{{ metric_descriptions.get(metric_key, '') }}</div>
    </div>
    {% endfor %}
  </div>
</div>

<!-- Metric Glossary -->
<div class="section">
  <h2>Glossary</h2>
  <div style="display:grid; grid-template-columns: repeat(2, 1fr); gap: 12px;">
    {% for key, desc in metric_descriptions.items() %}
    <div style="font-size:13px; padding:8px 12px; background:var(--brand-card); border:1px solid var(--brand-border); border-radius:6px;">
      <strong style="text-transform:uppercase; font-size:11px; color:var(--color-muted);">{{ key.replace('_', ' ') }}</strong><br>
      <span>{{ desc }}</span>
    </div>
    {% endfor %}
  </div>
</div>

<!-- Section D: CLV -->
<div class="section">
  <h2>Closing Line Value (CLV)</h2>
  <div class="chart-container">{{ clv_chart }}</div>

  {% if data.clv_per_league %}
  <table class="report-table">
    <thead>
      <tr>
        <th>League</th><th>N Bets</th><th>Mean CLV</th>
        <th>% Positive</th><th>ROI</th>
      </tr>
    </thead>
    <tbody>
      {% for row in data.clv_per_league %}
      <tr>
        <td>{{ row.league }}</td>
        <td>{{ row.n_bets }}</td>
        <td class="{{ 'text-positive' if row.mean_clv >= 0 else 'text-negative' }}">
          {{ "%.2f%%"|format(row.mean_clv * 100) }}
        </td>
        <td>{{ "%.1f%%"|format(row.pct_positive) }}</td>
        <td class="{{ 'text-positive' if row.roi >= 0 else 'text-negative' }}">
          {{ "%+.2f%%"|format(row.roi * 100) }}
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
  {% endif %}
</div>

<!-- Section: Per-Season Breakdown -->
{% if data.fold_details %}
<div class="section">
  <h2>Per-Season Results</h2>
  <p style="font-size:13px; color:var(--color-muted); margin-bottom:16px;">
    Walk-forward backtest: model trained on historical data, tested on each season sequentially.
  </p>
  <table class="report-table">
    <thead>
      <tr>
        <th>Test Season</th><th>Model</th><th>Log Loss</th><th>ECE</th>
        <th>CLV</th><th>ROI</th><th>N Bets</th>
      </tr>
    </thead>
    <tbody>
      {% for fold in data.fold_details %}
      <tr>
        <td>{{ fold.test_season }}</td>
        <td style="font-weight:600;">{{ fold.model }}</td>
        <td>{{ "%.4f"|format(fold.log_loss) }}</td>
        <td>{{ "%.2f%%"|format(fold.ece * 100) }}</td>
        <td class="{{ 'text-positive' if fold.clv >= 0 else 'text-negative' }}">
          {{ "%+.2f%%"|format(fold.clv * 100) }}
        </td>
        <td class="{{ 'text-positive' if fold.roi >= 0 else 'text-negative' }}">
          {{ "%+.2f%%"|format(fold.roi * 100) }}
        </td>
        <td>{{ fold.n_bets }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% endif %}

<!-- Section E: P&L -->
<div class="section">
  <h2>P&amp;L Performance</h2>
  <div class="chart-container">{{ equity_chart }}</div>

  {% if data.model_comparison %}
  <table class="report-table">
    <thead>
      <tr>
        <th>Model</th><th>Log Loss</th><th>ECE</th>
        <th>CLV</th><th>ROI</th><th>Sharpe</th><th>N Bets</th>
      </tr>
    </thead>
    <tbody>
      {% for row in data.model_comparison %}
      <tr>
        <td style="font-weight:600;">{{ row.model }}</td>
        <td>{{ "%.4f"|format(row.log_loss) }}</td>
        <td>{{ "%.2f%%"|format(row.ece * 100) }}</td>
        <td class="{{ 'text-positive' if row.clv >= 0 else 'text-negative' }}">
          {{ "%+.2f%%"|format(row.clv * 100) }}
        </td>
        <td class="{{ 'text-positive' if row.roi >= 0 else 'text-negative' }}">
          {{ "%+.2f%%"|format(row.roi * 100) }}
        </td>
        <td>{{ "%.2f"|format(row.sharpe) }}</td>
        <td>{{ row.n_bets|commaformat }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
  {% endif %}
</div>

<div class="footer">
  SportsLab Backtest Report | Generated {{ data.generated_at.strftime('%Y-%m-%d %H:%M UTC') }}
  {% if data.git_hash %} | {{ data.git_hash }}{% endif %}
</div>

</div>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render_html_report(data: ReportData, output_path: Path) -> Path:
    """Render a self-contained HTML report and write to disk.

    Args:
        data: Pre-computed report data.
        output_path: Path to write the HTML file.

    Returns:
        The output path (for chaining / logging).
    """
    clv_chart = _build_cumulative_clv_chart(data)
    equity_chart = _build_equity_curve_chart(data)

    hero_cards = _prepare_hero_cards(data)
    hero_borders = _prepare_hero_borders(data)
    overall_color = _overall_semaphore_color(data.semaphore)

    metric_descriptions = {
        "clv": "Closing Line Value — did our predictions beat the market's closing odds? Positive = genuine edge.",
        "roi": "Return on Investment — total profit divided by total stakes. Positive = profitable.",
        "sharpe": "Sharpe Ratio — risk-adjusted return (mean return / volatility). Higher = better risk/reward.",
        "ece": "Expected Calibration Error — are predicted probabilities accurate? Below 2% is good.",
        "log_loss": "Log Loss — measures probability prediction quality. Lower = better. Random guessing ≈ 1.10 for 1X2.",
        "brier_score": "Brier Score — mean squared error of probability estimates. Lower = more accurate. 0 = perfect.",
        "n_bets": "Total number of bets placed across all leagues and seasons in this backtest.",
        "max_drawdown": "Maximum Drawdown — worst peak-to-trough loss as % of bankroll. Lower = less risky.",
    }

    env = Environment(loader=BaseLoader(), autoescape=False)
    env.filters["commaformat"] = lambda v: f"{int(v):,}"
    template = env.from_string(_HTML_TEMPLATE)

    html = template.render(
        data=data,
        clv_chart=clv_chart,
        equity_chart=equity_chart,
        hero_cards=hero_cards,
        hero_borders=hero_borders,
        overall_color=overall_color,
        metric_descriptions=metric_descriptions,
        brand_primary=_BRAND_PRIMARY,
        brand_accent=_BRAND_ACCENT,
        brand_surface=_BRAND_SURFACE,
        brand_card=_BRAND_CARD,
        brand_border=_BRAND_BORDER,
        color_positive=_COLOR_POSITIVE,
        color_negative=_COLOR_NEGATIVE,
        color_neutral=_COLOR_NEUTRAL,
        color_muted=_COLOR_MUTED,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")

    logger.info("html_report_written", path=str(output_path))
    return output_path


def _prepare_hero_cards(
    data: ReportData,
) -> list[tuple[str, str, str]]:
    """Prepare (key, label, formatted_value) tuples for hero cards."""
    h = data.hero_metrics
    return [
        ("clv", "CLV (Mean)", f"{h.get('clv', 0) * 100:+.2f}%"),
        ("roi", "ROI", f"{h.get('roi', 0) * 100:+.2f}%"),
        ("sharpe", "Sharpe Ratio", f"{h.get('sharpe', 0):.2f}"),
        ("ece", "ECE", f"{h.get('ece', 0) * 100:.2f}%"),
        ("log_loss", "Log Loss", f"{h.get('log_loss', 0):.4f}"),
        ("brier_score", "Brier Score", f"{h.get('brier_score', 0):.3f}"),
        ("n_bets", "N Bets", f"{int(h.get('n_bets', 0)):,}"),
        ("max_drawdown", "Max Drawdown", f"{h.get('max_drawdown', 0) * 100:.1f}%"),
    ]


def _prepare_hero_borders(data: ReportData) -> dict[str, str]:
    """Map hero metric keys to border color classes."""
    borders: dict[str, str] = {}
    for key in ("clv", "ece", "roi"):
        borders[key] = data.semaphore.get(key, "none")
    return borders


def _overall_semaphore_color(semaphore: dict[str, str]) -> str:
    """Determine the worst semaphore color for the verdict banner."""
    colors = list(semaphore.values())
    if "red" in colors:
        return "red"
    if "yellow" in colors:
        return "yellow"
    return "green"
