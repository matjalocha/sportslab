"""HTML renderer for weekly performance reports."""

from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go
import structlog
from jinja2 import BaseLoader, Environment
from markupsafe import Markup, escape

from ml_in_sports.prediction.weekly import WeeklyData
from ml_in_sports.report_theme import (
    BRAND_BORDER,
    BRAND_CARD,
    BRAND_PRIMARY,
    BRAND_SURFACE,
    COLOR_MUTED,
    COLOR_NEGATIVE,
    COLOR_POSITIVE,
)

logger = structlog.get_logger(__name__)

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Weekly Performance - {{ data.week_start }} to {{ data.week_end }}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js" charset="utf-8"></script>
<style>
:root { --brand-primary: {{ brand_primary }}; --brand-surface: {{ brand_surface }}; --brand-card: {{ brand_card }}; --brand-border: {{ brand_border }}; --color-positive: {{ color_positive }}; --color-negative: {{ color_negative }}; --color-muted: {{ color_muted }}; }
* { box-sizing: border-box; }
body { margin: 0; font-family: Inter, sans-serif; background: var(--brand-surface); color: var(--brand-primary); }
.container { max-width: 1180px; margin: 0 auto; padding: 24px; }
.header { border-bottom: 2px solid var(--brand-primary); padding-bottom: 18px; margin-bottom: 24px; }
.header h1 { margin: 0; font-size: 30px; }
.summary-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; margin-bottom: 24px; }
.card, .section { background: var(--brand-card); border: 1px solid var(--brand-border); border-radius: 10px; padding: 16px; }
.section { margin-bottom: 24px; }
.label { color: var(--color-muted); font-size: 12px; text-transform: uppercase; letter-spacing: .06em; }
.value { font-family: "JetBrains Mono", monospace; font-size: 22px; font-weight: 600; }
.chart-container { background: var(--brand-card); border: 1px solid var(--brand-border); border-radius: 10px; padding: 16px; margin-bottom: 24px; }
table { width: 100%; border-collapse: collapse; }
th { background: var(--brand-primary); color: #fff; padding: 10px 12px; text-align: left; font-size: 11px; text-transform: uppercase; }
td { padding: 10px 12px; border-bottom: 1px solid var(--brand-border); font-size: 13px; }
.mono { font-family: "JetBrains Mono", monospace; }
.positive { color: var(--color-positive); font-weight: 700; }
.negative { color: var(--color-negative); font-weight: 700; }
@media (max-width: 800px) { .summary-grid { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<div class="container">
  <header class="header">
    <h1>Weekly Performance Report</h1>
    <div>{{ data.week_start }} to {{ data.week_end }}</div>
  </header>

  <section class="summary-grid">
    <div class="card"><div class="label">Bets</div><div class="value">{{ data.total_bets }}</div></div>
    <div class="card"><div class="label">W/L</div><div class="value">{{ data.wins }}-{{ data.losses }}</div></div>
    <div class="card"><div class="label">P&amp;L</div><div class="value">{{ "%+.2f"|format(data.pnl) }} EUR</div></div>
    <div class="card"><div class="label">Bankroll</div><div class="value">EUR {{ "%.2f"|format(data.bankroll_end) }}</div></div>
  </section>

  <div class="chart-container"><h2>Daily P&amp;L</h2>{{ pnl_chart }}</div>

  <section class="section">
    <h2>Per League</h2>
    {{ league_table }}
  </section>
  <section class="section">
    <h2>Per Market</h2>
    {{ market_table }}
  </section>
</div>
</body>
</html>
"""


def render_weekly_html(data: WeeklyData, output_path: Path) -> Path:
    """Render weekly performance as a self-contained HTML report."""
    html = render_weekly_html_string(data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    logger.info("weekly_html_written", path=str(output_path), bets=data.total_bets)
    return output_path


def render_weekly_html_string(data: WeeklyData) -> str:
    """Render weekly performance HTML as a string."""
    env = Environment(loader=BaseLoader(), autoescape=True)
    template = env.from_string(_HTML_TEMPLATE)
    return str(
        template.render(
            data=data,
            pnl_chart=Markup(_build_daily_pnl_chart(data)),
            league_table=Markup(_build_table(data.per_league, "league")),
            market_table=Markup(_build_table(data.per_market, "market")),
            brand_primary=BRAND_PRIMARY,
            brand_surface=BRAND_SURFACE,
            brand_card=BRAND_CARD,
            brand_border=BRAND_BORDER,
            color_positive=COLOR_POSITIVE,
            color_negative=COLOR_NEGATIVE,
            color_muted=COLOR_MUTED,
        )
    )


def _build_daily_pnl_chart(data: WeeklyData) -> str:
    x_values = list(data.daily_pnl.keys())
    y_values = list(data.daily_pnl.values())
    colors = [COLOR_POSITIVE if value >= 0.0 else COLOR_NEGATIVE for value in y_values]
    fig = go.Figure(
        data=[
            go.Bar(
                x=x_values,
                y=y_values,
                marker={"color": colors},
                hovertemplate="%{x}<br>P&L: EUR %{y:.2f}<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        title="Daily P&L",
        template="plotly_white",
        font={"family": "Inter, sans-serif", "size": 12},
        height=360,
        margin={"t": 50, "r": 30, "b": 50, "l": 60},
    )
    return str(fig.to_html(full_html=False, include_plotlyjs=False))


def _build_table(rows: list[dict[str, str | int | float]], label_key: str) -> str:
    if not rows:
        return "<p>No weekly data available.</p>"
    body = []
    for row in rows:
        pnl = float(row["pnl"])
        pnl_class = "positive" if pnl >= 0 else "negative"
        label = escape(str(row[label_key]))
        body.append(
            "<tr>"
            f"<td>{label}</td><td class='mono'>{int(row['bets'])}</td>"
            f"<td class='mono'>{int(row['wins'])}-{int(row['losses'])}</td>"
            f"<td class='mono {pnl_class}'>{pnl:+.2f}</td>"
            f"<td class='mono'>{float(row['roi']):+.2%}</td>"
            f"<td class='mono'>{float(row['clv']):+.2%}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>Name</th><th>Bets</th><th>W/L</th><th>P&L</th>"
        "<th>ROI</th><th>CLV</th></tr></thead><tbody>" + "".join(body) + "</tbody></table>"
    )
