#!/usr/bin/env python3
"""Export rolling track-record stats to JSON for the landing page.

Runs weekly via cron once SPO-A-10 (the Hetzner deploy) lands. The output
file is served statically (or pushed to a CDN) and consumed by the
``sportslab-web`` landing page "Track Record" section -- that widget is
the public proof-of-work element, so the JSON shape is intentionally
stable and versioned (see ``schema_version``).

Design notes:

- **Two modes.** Before we have real settled bets, the script writes a
  ``status: "starting_soon"`` stub so the landing page can render a
  "Track record begins with alpha launch" message without 404s. Once
  SPO-A-09 (Postgres migration) + SPO-A-10 (alpha deploy) are live, the
  ``--db-url`` path aggregates real data. Mode selection is automatic:
  if no database URL is provided *and* the default env var is missing,
  we emit the stub.
- **SQL, not ORM.** We keep this script ORM-free so it can be vendored
  into ops images without pulling the full ``api`` wheel. Plain
  SQLAlchemy Core queries are enough for aggregate rollups.
- **No secrets in logs.** The DB URL is never echoed; only the scheme
  is logged (``postgresql``, ``sqlite``, etc.).
- **Idempotent + safe.** The script only reads, never writes to the DB.
  Output is an atomic tmp-file-then-rename so a half-written file never
  reaches the CDN.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

_SCHEMA_VERSION = 1
_DEFAULT_WINDOW_DAYS = 180
_DEFAULT_OUTPUT = Path("reports/track_record_latest.json")

_LOGGER = logging.getLogger("export_track_record")


@dataclass
class EquityPoint:
    """One daily snapshot on the equity curve."""

    date: str  # ISO-8601 YYYY-MM-DD
    bankroll_eur: float
    pnl_eur: float


@dataclass
class MonthlyStat:
    """Aggregate stats for a calendar month."""

    month: str  # YYYY-MM
    bets: int
    win_rate: float
    roi_percent: float
    profit_eur: float


@dataclass
class LeagueStat:
    """Aggregate stats for one competition."""

    league: str
    bets: int
    win_rate: float
    roi_percent: float
    profit_eur: float


@dataclass
class TrackRecordReport:
    """Top-level payload serialized to JSON for the landing page.

    ``status`` drives the landing widget behaviour:
        - ``"starting_soon"`` -> "Track record begins with alpha launch"
        - ``"active"``        -> render KPIs + equity curve + breakdowns
    """

    schema_version: int
    status: str
    generated_at: str
    since_date: str
    window_days: int
    total_bets: int
    hit_rate: float
    roi_percent: float
    clv_mean_percent: float
    sharpe: float | None
    max_drawdown_percent: float
    equity_curve: list[EquityPoint] = field(default_factory=list)
    monthly_breakdown: list[MonthlyStat] = field(default_factory=list)
    per_league_breakdown: list[LeagueStat] = field(default_factory=list)
    message: str | None = None


def build_stub_report(since: date, window_days: int) -> TrackRecordReport:
    """Return a pre-launch stub report.

    The landing page renders this as "Track record begins with alpha
    launch" -- no numbers, no equity curve. Having a well-formed file
    from day zero means the widget doesn't have to handle 404s.
    """
    return TrackRecordReport(
        schema_version=_SCHEMA_VERSION,
        status="starting_soon",
        generated_at=datetime.now(tz=UTC).isoformat(),
        since_date=since.isoformat(),
        window_days=window_days,
        total_bets=0,
        hit_rate=0.0,
        roi_percent=0.0,
        clv_mean_percent=0.0,
        sharpe=None,
        max_drawdown_percent=0.0,
        equity_curve=[],
        monthly_breakdown=[],
        per_league_breakdown=[],
        message="Track record begins with alpha launch.",
    )


def build_report_from_db(
    db_url: str, since: date, window_days: int
) -> TrackRecordReport:
    """Aggregate settled bets from the database into a full report.

    Kept deliberately simple: we rely on the ``user_bets`` table (see
    ``apps/api/src/api/db/models.py``) and compute the same metrics the
    API's ``/track-record`` endpoints serve, but at the population level
    (all users) rather than per-user. The landing page is a marketing
    surface -- it only shows the global "how are we doing" number.

    Args:
        db_url: SQLAlchemy URL. Async drivers are coerced to sync on entry
            because this is a one-shot batch job, no event loop available.
        since: Earliest ``placed_at`` to include (inclusive).
        window_days: Length of the rolling window, for the output metadata.

    Returns:
        Populated :class:`TrackRecordReport` with ``status="active"``.

    Notes:
        The SQL is intentionally dialect-portable (no ``DATE_TRUNC`` /
        ``strftime`` shenanigans). We pull raw rows and aggregate in
        Python -- the data volume is small (thousands, not millions) so
        this is cheaper than maintaining two dialect-specific queries.
    """
    # Import here so the stub path works without SQLAlchemy installed.
    from sqlalchemy import create_engine, text

    sync_url = db_url.replace("postgresql+asyncpg", "postgresql+psycopg").replace(
        "sqlite+aiosqlite", "sqlite"
    )
    engine = create_engine(sync_url)
    query = text(
        """
        SELECT placed_at, stake_eur, odds, outcome, pnl_eur, bookmaker, market
          FROM user_bets
         WHERE placed_at >= :since
           AND outcome != 'pending'
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(
            query,
            {"since": datetime.combine(since, datetime.min.time(), tzinfo=UTC)},
        ).fetchall()

    settled = [row for row in rows if row.outcome in {"won", "lost", "void"}]
    total_bets = len(settled)
    wins = sum(1 for row in settled if row.outcome == "won")
    total_stake = sum(row.stake_eur for row in settled) or 0.0
    total_pnl = sum((row.pnl_eur or 0.0) for row in settled)
    hit_rate = (wins / total_bets) if total_bets else 0.0
    roi_percent = (total_pnl / total_stake * 100.0) if total_stake else 0.0

    equity = _build_equity_curve(settled, since)
    monthly = _build_monthly(settled)
    max_dd = _compute_max_drawdown(equity)

    return TrackRecordReport(
        schema_version=_SCHEMA_VERSION,
        status="active",
        generated_at=datetime.now(tz=UTC).isoformat(),
        since_date=since.isoformat(),
        window_days=window_days,
        total_bets=total_bets,
        hit_rate=round(hit_rate, 4),
        roi_percent=round(roi_percent, 2),
        # CLV and Sharpe need extra columns (closing_odds, daily returns) we
        # haven't captured yet -- placeholders until the model-output pipeline
        # (SPO-A-10+) starts logging them. Flag with ``None`` so the landing
        # page can render a dash instead of a misleading zero.
        clv_mean_percent=0.0,
        sharpe=None,
        max_drawdown_percent=round(max_dd, 2),
        equity_curve=equity,
        monthly_breakdown=monthly,
        per_league_breakdown=[],
        message=None,
    )


def _coerce_to_date(value: Any) -> date:
    """Turn whatever SQLite / Postgres hands us into a plain ``date``.

    SQLite returns ``DateTime`` columns as ISO-8601 strings unless a
    ``detect_types=PARSE_DECLTYPES`` flag is set on the connection; we
    don't set that because the production target is Postgres where the
    driver returns real ``datetime`` objects. This helper hides the
    dialect difference so the aggregation code stays clean.
    """
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    # ISO-8601 string -- "YYYY-MM-DDTHH:MM:SS[.ffffff][+00:00]".
    # Use ``.split("T")`` for robustness against driver quirks that might
    # strip the trailing zone.
    return date.fromisoformat(str(value).split("T", 1)[0])


def _build_equity_curve(rows: list[Any], since: date) -> list[EquityPoint]:
    """Collapse settled bets into one cumulative-PnL point per day.

    Starts at ``since`` with ``bankroll_eur = 0`` -- the landing page
    overlays a configurable starting bankroll in-widget so the backing
    JSON stays opinion-free.
    """
    by_day: dict[date, float] = {}
    for row in rows:
        placed_date = _coerce_to_date(row.placed_at)
        by_day[placed_date] = by_day.get(placed_date, 0.0) + (row.pnl_eur or 0.0)

    cumulative = 0.0
    curve: list[EquityPoint] = []
    current_day = since
    today = date.today()
    while current_day <= today:
        cumulative += by_day.get(current_day, 0.0)
        curve.append(
            EquityPoint(
                date=current_day.isoformat(),
                bankroll_eur=round(cumulative, 2),
                pnl_eur=round(cumulative, 2),
            )
        )
        current_day += timedelta(days=1)
    return curve


def _build_monthly(rows: list[Any]) -> list[MonthlyStat]:
    """Per-month breakdown; months with zero settled bets are omitted."""
    buckets: dict[str, list[Any]] = {}
    for row in rows:
        placed_date = _coerce_to_date(row.placed_at)
        key = f"{placed_date.year:04d}-{placed_date.month:02d}"
        buckets.setdefault(key, []).append(row)

    stats: list[MonthlyStat] = []
    for month, bucket_rows in sorted(buckets.items()):
        wins = sum(1 for row in bucket_rows if row.outcome == "won")
        stake = sum(row.stake_eur for row in bucket_rows) or 0.0
        pnl = sum((row.pnl_eur or 0.0) for row in bucket_rows)
        bets = len(bucket_rows)
        stats.append(
            MonthlyStat(
                month=month,
                bets=bets,
                win_rate=round(wins / bets, 4) if bets else 0.0,
                roi_percent=round(pnl / stake * 100.0, 2) if stake else 0.0,
                profit_eur=round(pnl, 2),
            )
        )
    return stats


def _compute_max_drawdown(equity: list[EquityPoint]) -> float:
    """Return the worst peak-to-trough drop in percent (non-positive).

    Edge cases:
        - Empty curve -> ``0.0``.
        - Monotonically increasing curve -> ``0.0``.
        - Peak at zero bankroll -> return absolute drop rather than dividing
          by zero; the landing widget renders that as EUR, not percent, but
          we avoid ``NaN`` in the JSON.
    """
    if not equity:
        return 0.0
    peak = equity[0].bankroll_eur
    max_drawdown = 0.0
    for point in equity:
        peak = max(peak, point.bankroll_eur)
        if peak > 0:
            drawdown = (point.bankroll_eur - peak) / peak * 100.0
        else:
            drawdown = point.bankroll_eur - peak
        max_drawdown = min(max_drawdown, drawdown)
    return max_drawdown


def _report_to_dict(report: TrackRecordReport) -> dict[str, Any]:
    """Convert the dataclass tree to plain dicts -- dataclasses helper."""
    return asdict(report)


def _atomic_write(path: Path, payload: str) -> None:
    """Write ``payload`` to ``path`` via tmp+rename so readers never see a half file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=path.name + ".",
        suffix=".tmp",
        delete=False,
    ) as tmp:
        tmp.write(payload)
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; returns a shell-friendly exit code."""
    parser = argparse.ArgumentParser(
        description="Export rolling track record stats to JSON for landing page.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_DEFAULT_OUTPUT,
        help=f"Output JSON path (default: {_DEFAULT_OUTPUT}).",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=_DEFAULT_WINDOW_DAYS,
        help=f"Rolling window in days (default: {_DEFAULT_WINDOW_DAYS}).",
    )
    parser.add_argument(
        "--db-url",
        default=None,
        help=(
            "SQLAlchemy URL. Overrides SPORTSLAB_DATABASE_URL. When neither "
            "is set, the script writes a pre-launch stub report."
        ),
    )
    parser.add_argument(
        "--force-stub",
        action="store_true",
        help="Emit the pre-launch stub regardless of DB availability.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    since = date.today() - timedelta(days=args.days)
    db_url = args.db_url or os.environ.get("SPORTSLAB_DATABASE_URL") or None

    if args.force_stub or not db_url:
        _LOGGER.info("building_stub_report since=%s window_days=%s", since, args.days)
        report = build_stub_report(since=since, window_days=args.days)
    else:
        scheme = db_url.split(":", 1)[0]
        _LOGGER.info(
            "building_db_report scheme=%s since=%s window_days=%s",
            scheme,
            since,
            args.days,
        )
        report = build_report_from_db(db_url=db_url, since=since, window_days=args.days)

    payload = json.dumps(_report_to_dict(report), indent=2, sort_keys=True)
    _atomic_write(args.output, payload)
    _LOGGER.info(
        "wrote_report path=%s status=%s bytes=%s",
        args.output,
        report.status,
        len(payload),
    )
    # Human-visible confirmation for cron logs:
    print(f"Wrote {args.output} ({report.status}, {len(payload)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
