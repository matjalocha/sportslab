"""HTML renderer for daily bet results."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path

import structlog
from jinja2 import BaseLoader, Environment, select_autoescape

from ml_in_sports.prediction.report._utils import infer_report_date_from_results
from ml_in_sports.prediction.results import BetResult
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
_EMPTY_STATE = "No bet results to display."

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Daily Results - {{ report_date }}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root {
  --brand-primary: {{ brand_primary }};
  --brand-surface: {{ brand_surface }};
  --brand-card: {{ brand_card }};
  --brand-border: {{ brand_border }};
  --color-positive: {{ color_positive }};
  --color-negative: {{ color_negative }};
  --color-muted: {{ color_muted }};
}
* { box-sizing: border-box; }
body { margin: 0; font-family: Inter, sans-serif; background: var(--brand-surface); color: var(--brand-primary); }
.container { max-width: 1180px; margin: 0 auto; padding: 24px; }
.header { border-bottom: 2px solid var(--brand-primary); padding-bottom: 18px; margin-bottom: 24px; }
.header h1 { margin: 0; font-size: 30px; }
.summary-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; margin-bottom: 24px; }
.card { background: var(--brand-card); border: 1px solid var(--brand-border); border-radius: 10px; padding: 16px; }
.label { color: var(--color-muted); font-size: 12px; text-transform: uppercase; letter-spacing: .06em; }
.value { font-family: "JetBrains Mono", monospace; font-size: 22px; font-weight: 600; }
.section { background: var(--brand-card); border: 1px solid var(--brand-border); border-radius: 10px; padding: 20px; }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; }
th { background: var(--brand-primary); color: #fff; padding: 10px 12px; text-align: left; font-size: 11px; text-transform: uppercase; }
td { padding: 10px 12px; border-bottom: 1px solid var(--brand-border); font-size: 13px; }
.mono { font-family: "JetBrains Mono", monospace; }
.hit-row { background: #dcfce7; }
.miss-row { background: #fef2f2; }
.positive { color: var(--color-positive); font-weight: 700; }
.negative { color: var(--color-negative); font-weight: 700; }
.empty { color: var(--color-muted); text-align: center; padding: 28px; border: 1px dashed var(--brand-border); border-radius: 8px; }
@media (max-width: 800px) { .summary-grid { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<div class="container">
  <header class="header">
    <h1>Daily Results Tracker</h1>
    <div>{{ report_date }}</div>
  </header>

  <section class="summary-grid">
    <div class="card"><div class="label">W/L</div><div class="value">{{ summary.wins }}-{{ summary.losses }}</div></div>
    <div class="card"><div class="label">P&amp;L</div><div class="value">{{ "%+.2f"|format(summary.pnl) }} EUR</div></div>
    <div class="card"><div class="label">Mean CLV</div><div class="value">{{ "%+.2f%%"|format(summary.mean_clv * 100) }}</div></div>
    <div class="card"><div class="label">Bankroll</div><div class="value">EUR {{ "%.2f"|format(summary.bankroll) }}</div></div>
  </section>

  <section class="section">
    <h2>Bet Results</h2>
    {% if rows %}
    <div class="table-wrap">
      <table>
        <thead><tr><th>Match</th><th>Score</th><th>Bet</th><th>Result</th><th>Odds</th><th>CLV</th><th>P&amp;L</th><th>Bankroll</th></tr></thead>
        <tbody>
          {% for row in rows %}
          <tr class="{{ row.row_class }}">
            <td>{{ row.match }}</td><td class="mono">{{ row.score }}</td><td class="mono">{{ row.market }}</td>
            <td class="mono">{{ row.status }}</td><td class="mono">{{ row.odds }}</td><td class="mono">{{ row.clv }}</td>
            <td class="mono {{ row.pnl_class }}">{{ row.pnl }}</td><td class="mono">{{ row.bankroll }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    {% else %}
    <div class="empty">{{ empty_state }}</div>
    {% endif %}
  </section>
</div>
</body>
</html>
"""


@dataclass(frozen=True)
class _Summary:
    wins: int
    losses: int
    pnl: float
    mean_clv: float
    bankroll: float


def render_results_html(
    results: list[BetResult],
    output_path: Path,
    report_date: dt.date | None = None,
) -> Path:
    """Render daily results as a self-contained HTML file."""
    html = render_results_html_string(results, report_date=report_date)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    logger.info("results_html_written", path=str(output_path), results=len(results))
    return output_path


def render_results_html_string(
    results: list[BetResult],
    report_date: dt.date | None = None,
) -> str:
    """Render daily results HTML as a string."""
    resolved_date = report_date or infer_report_date_from_results(results)
    env = Environment(
        loader=BaseLoader(),
        autoescape=select_autoescape(enabled_extensions=("html",)),
    )
    template = env.from_string(_HTML_TEMPLATE)
    return str(
        template.render(
            rows=[_format_row(result) for result in results],
            summary=_build_summary(results),
            report_date=resolved_date.isoformat(),
            empty_state=_EMPTY_STATE,
            brand_primary=BRAND_PRIMARY,
            brand_surface=BRAND_SURFACE,
            brand_card=BRAND_CARD,
            brand_border=BRAND_BORDER,
            color_positive=COLOR_POSITIVE,
            color_negative=COLOR_NEGATIVE,
            color_muted=COLOR_MUTED,
        )
    )


def _build_summary(results: list[BetResult]) -> _Summary:
    wins = sum(1 for result in results if result.hit)
    losses = len(results) - wins
    clv_values = [result.clv for result in results if result.clv is not None]
    return _Summary(
        wins=wins,
        losses=losses,
        pnl=sum(result.pnl for result in results),
        mean_clv=sum(clv_values) / len(clv_values) if clv_values else 0.0,
        bankroll=results[-1].bankroll_after if results else 0.0,
    )


def _format_row(result: BetResult) -> dict[str, str]:
    recommendation = result.recommendation
    return {
        "match": f"{recommendation.home_team} vs {recommendation.away_team}",
        "score": result.actual_score,
        "market": recommendation.market,
        "status": "WIN" if result.hit else "MISS",
        "odds": f"{recommendation.best_odds:.2f}",
        "clv": f"{result.clv * 100:+.2f}%" if result.clv is not None else "n/a",
        "pnl": f"{result.pnl:+.2f}",
        "pnl_class": "positive" if result.pnl >= 0.0 else "negative",
        "bankroll": f"{result.bankroll_after:.2f}",
        "row_class": "hit-row" if result.hit else "miss-row",
    }
