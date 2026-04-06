"""Self-contained HTML renderer for daily bet slips."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path

import structlog
from jinja2 import BaseLoader, Environment, select_autoescape

from ml_in_sports.prediction.daily import BetRecommendation
from ml_in_sports.prediction.report._utils import infer_report_date_from_recommendations
from ml_in_sports.report_theme import (
    BRAND_BORDER,
    BRAND_CARD,
    BRAND_PRIMARY,
    BRAND_SURFACE,
    COLOR_MUTED,
    COLOR_NEGATIVE,
    COLOR_NEUTRAL,
    COLOR_POSITIVE,
)

logger = structlog.get_logger(__name__)

_EMPTY_STATE = "Zero betów dzisiaj. Model nie znalazł wartości."


_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Daily Bet Slip - {{ report_date }}</title>
<style>
:root {
  --brand-primary: {{ brand_primary }};
  --brand-surface: {{ brand_surface }};
  --brand-card: {{ brand_card }};
  --brand-border: {{ brand_border }};
  --color-positive: {{ color_positive }};
  --color-negative: {{ color_negative }};
  --color-neutral: {{ color_neutral }};
  --color-muted: {{ color_muted }};
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: var(--brand-surface);
  color: var(--brand-primary);
  line-height: 1.5;
}
.container { max-width: 1180px; margin: 0 auto; padding: 24px; }
.header {
  display: flex; justify-content: space-between; align-items: flex-start;
  padding-bottom: 20px; border-bottom: 2px solid var(--brand-primary);
  margin-bottom: 28px;
}
.header h1 { margin: 0; font-size: 30px; font-weight: 750; }
.header-meta {
  font-family: "JetBrains Mono", Consolas, monospace;
  color: var(--color-muted); font-size: 12px; text-align: right;
}
.summary-grid {
  display: grid; grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px; margin-bottom: 28px;
}
.summary-card {
  background: var(--brand-card); border: 1px solid var(--brand-border);
  border-left: 4px solid var(--brand-primary); border-radius: 10px;
  padding: 18px;
}
.summary-label {
  color: var(--color-muted); font-size: 12px; text-transform: uppercase;
  letter-spacing: 0.06em; margin-bottom: 6px;
}
.summary-value {
  font-family: "JetBrains Mono", Consolas, monospace;
  font-size: 24px; font-weight: 600;
}
.summary-positive { border-left-color: var(--color-positive); }
.summary-negative { border-left-color: var(--color-negative); }
.section {
  background: var(--brand-card); border: 1px solid var(--brand-border);
  border-radius: 10px; padding: 20px; margin-bottom: 24px;
}
.section h2 { margin: 0 0 16px; font-size: 20px; }
.empty-state {
  padding: 28px; text-align: center; color: var(--color-muted);
  border: 1px dashed var(--brand-border); border-radius: 8px;
}
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; }
th {
  background: var(--brand-primary); color: #fff; text-align: left;
  padding: 10px 12px; font-size: 11px; text-transform: uppercase;
  letter-spacing: 0.05em; white-space: nowrap;
}
td {
  padding: 10px 12px; border-bottom: 1px solid var(--brand-border);
  font-size: 13px; vertical-align: middle;
}
tr:last-child td { border-bottom: 0; }
.mono { font-family: "JetBrains Mono", Consolas, monospace; }
.muted { color: var(--color-muted); }
.edge-cell { font-weight: 700; color: var(--color-positive); }
.agreement {
  display: inline-block; min-width: 40px; padding: 3px 8px; border-radius: 999px;
  font-family: "JetBrains Mono", Consolas, monospace; font-size: 12px;
}
.agreement-3 { color: var(--color-positive); background: #dcfce7; font-weight: 700; }
.agreement-2 { color: var(--color-neutral); background: #fef9c3; font-weight: 600; }
.agreement-1 { color: var(--color-muted); background: #f6f8fa; }
.glossary-grid {
  display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px;
}
.glossary-item {
  padding: 12px; border: 1px solid var(--brand-border);
  border-radius: 8px; background: #fff;
}
.glossary-item strong {
  display: block; margin-bottom: 4px; font-size: 12px; text-transform: uppercase;
  letter-spacing: 0.05em; color: var(--color-muted);
}
@media (max-width: 800px) {
  .header { display: block; }
  .header-meta { text-align: left; margin-top: 10px; }
  .summary-grid, .glossary-grid { grid-template-columns: 1fr; }
}
</style>
</head>
<body>
<div class="container">
  <header class="header">
    <div>
      <h1>Daily Bet Slip</h1>
      <div class="muted">Bet recommendations for {{ report_date }}</div>
    </div>
    <div class="header-meta">
      Generated {{ generated_at }}<br>
      Quarter-Kelly staking
    </div>
  </header>

  <section class="summary-grid" aria-label="Summary">
    <div class="summary-card">
      <div class="summary-label">N Bets</div>
      <div class="summary-value">{{ summary.n_bets }}</div>
    </div>
    <div class="summary-card">
      <div class="summary-label">Total Stake</div>
      <div class="summary-value">EUR {{ "%.2f"|format(summary.total_stake) }}</div>
    </div>
    <div class="summary-card {{ 'summary-positive' if summary.ev >= 0 else 'summary-negative' }}">
      <div class="summary-label">EV</div>
      <div class="summary-value">{{ "%+.2f"|format(summary.ev) }} EUR</div>
    </div>
  </section>

  <section class="section">
    <h2>Recommendations</h2>
    {% if rows %}
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Match</th><th>League</th><th>Kickoff</th><th>Market</th>
            <th>Model P</th><th>Book P</th><th>Edge</th><th>Kelly %</th>
            <th>Stake EUR</th><th>Agreement</th><th>Bookmaker</th>
          </tr>
        </thead>
        <tbody>
          {% for row in rows %}
          <tr>
            <td><strong>{{ row.match }}</strong></td>
            <td>{{ row.league }}</td>
            <td class="mono">{{ row.kickoff }}</td>
            <td class="mono">{{ row.market }}</td>
            <td class="mono">{{ row.model_prob }}</td>
            <td class="mono">{{ row.bookmaker_prob }}</td>
            <td class="mono edge-cell" style="{{ row.edge_style }}">{{ row.edge }}</td>
            <td class="mono">{{ row.kelly }}</td>
            <td class="mono">{{ row.stake }}</td>
            <td><span class="agreement agreement-{{ row.agreement_level }}">{{ row.agreement }}</span></td>
            <td>{{ row.bookmaker }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    {% else %}
    <div class="empty-state">{{ empty_state }}</div>
    {% endif %}
  </section>

  <section class="section">
    <h2>Glossary</h2>
    <div class="glossary-grid">
      <div class="glossary-item"><strong>Edge</strong>Model probability minus bookmaker implied probability. Positive edge means the model sees value.</div>
      <div class="glossary-item"><strong>Kelly %</strong>Constrained fractional Kelly stake as a percentage of bankroll.</div>
      <div class="glossary-item"><strong>CLV</strong>Closing Line Value: whether the bet beat the market closing price, usually Pinnacle.</div>
      <div class="glossary-item"><strong>Model Agreement</strong>How many model families support the recommendation, from 1/3 to 3/3.</div>
    </div>
  </section>
</div>
</body>
</html>
"""


@dataclass(frozen=True)
class _Summary:
    n_bets: int
    total_stake: float
    ev: float


def render_html_bet_slip(
    predictions: list[BetRecommendation],
    output_path: Path,
    report_date: dt.date | None = None,
) -> Path:
    """Render a self-contained daily bet slip HTML file.

    Args:
        predictions: Bet recommendations to render.
        output_path: Destination HTML file path.
        report_date: Optional report date override.

    Returns:
        The written HTML path.
    """
    html = render_html_bet_slip_string(predictions, report_date=report_date)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    logger.info("bet_slip_html_written", path=str(output_path), bets=len(predictions))
    return output_path


def render_bet_slip_html(
    bets: list[BetRecommendation],
    output_path: Path,
    date_str: str = "",
) -> Path:
    """Compatibility wrapper for rendering a bet slip HTML report."""
    report_date = dt.date.fromisoformat(date_str) if date_str else None
    return render_html_bet_slip(bets, output_path, report_date=report_date)


def render_html_bet_slip_string(
    predictions: list[BetRecommendation],
    report_date: dt.date | None = None,
) -> str:
    """Render a daily bet slip HTML document as a string."""
    resolved_date = report_date or infer_report_date_from_recommendations(predictions)
    env = Environment(
        loader=BaseLoader(),
        autoescape=select_autoescape(enabled_extensions=("html",)),
    )
    template = env.from_string(_HTML_TEMPLATE)
    return str(
        template.render(
            rows=[_format_row(prediction) for prediction in predictions],
            summary=_build_summary(predictions),
            report_date=resolved_date.isoformat(),
            generated_at=dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
            empty_state=_EMPTY_STATE,
            brand_primary=BRAND_PRIMARY,
            brand_surface=BRAND_SURFACE,
            brand_card=BRAND_CARD,
            brand_border=BRAND_BORDER,
            color_positive=COLOR_POSITIVE,
            color_negative=COLOR_NEGATIVE,
            color_neutral=COLOR_NEUTRAL,
            color_muted=COLOR_MUTED,
        )
    )


def _build_summary(predictions: list[BetRecommendation]) -> _Summary:
    total_stake = sum(prediction.stake_eur for prediction in predictions)
    ev = sum(
        prediction.stake_eur * (prediction.model_prob * prediction.best_odds - 1.0)
        for prediction in predictions
    )
    return _Summary(n_bets=len(predictions), total_stake=total_stake, ev=ev)


def _format_row(prediction: BetRecommendation) -> dict[str, str | int]:
    return {
        "match": f"{prediction.home_team} vs {prediction.away_team}",
        "league": prediction.league,
        "kickoff": prediction.kickoff_dt.strftime("%Y-%m-%d %H:%M"),
        "market": prediction.market,
        "model_prob": f"{prediction.model_prob:.1%}",
        "bookmaker_prob": f"{prediction.bookmaker_prob:.1%}",
        "edge": f"{prediction.edge:+.1%}",
        "edge_style": _edge_style(prediction.edge),
        "kelly": f"{prediction.kelly_fraction:.2%}",
        "stake": f"{prediction.stake_eur:.2f}",
        "agreement": f"{prediction.model_agreement}/3",
        "agreement_level": max(1, min(3, prediction.model_agreement)),
        "bookmaker": f"{prediction.best_bookmaker} @ {prediction.best_odds:.2f}",
    }


def _edge_style(edge: float) -> str:
    pct = max(0.0, min(1.0, edge / 0.10))
    alpha = 0.08 + pct * 0.28
    return (
        "background: linear-gradient(90deg, "
        f"rgba(26, 127, 55, {alpha:.2f}) 0%, "
        f"rgba(26, 127, 55, {alpha:.2f}) {pct * 100:.0f}%, "
        "#fff 100%);"
    )
