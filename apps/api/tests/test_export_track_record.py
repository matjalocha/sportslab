"""Tests for ``scripts/export_track_record.py``.

Two paths to cover:

1. **Stub mode** -- no DB configured, script writes the pre-launch
   placeholder. This is what runs every Monday morning from right now
   until SPO-A-10 ships. If this ever regresses the landing page goes
   back to 404.
2. **Real mode** -- SQLite in-memory DB seeded with a handful of settled
   bets. We don't verify exact numerics to the cent (float aggregation
   is platform-dependent); we do verify shape, monotonic equity curve
   behaviour, and that status flips to ``active``.

The script lives at the monorepo root, one level above ``apps/api``, so
the test resolves it by path and imports as a plain module.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import ModuleType

import pytest
from sqlalchemy import create_engine

# Path resolution: apps/api/tests/test_*.py -> monorepo root -> scripts/
_API_ROOT = Path(__file__).resolve().parents[1]
_MONOREPO_ROOT = _API_ROOT.parent.parent
_EXPORTER_PATH = _MONOREPO_ROOT / "scripts" / "export_track_record.py"


def _load_exporter() -> ModuleType:
    """Load the exporter script as a module for direct function access."""
    spec = importlib.util.spec_from_file_location(
        "export_track_record", _EXPORTER_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["export_track_record"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def exporter() -> ModuleType:
    """Imported-once exporter module -- no state to reset between cases."""
    return _load_exporter()


def test_stub_report_has_starting_soon_status(exporter: ModuleType) -> None:
    """Pre-launch stub must announce itself so the landing widget can branch."""
    since = date.today() - timedelta(days=180)

    report = exporter.build_stub_report(since=since, window_days=180)

    assert report.status == "starting_soon"
    assert report.total_bets == 0
    assert report.equity_curve == []
    assert report.monthly_breakdown == []
    assert report.per_league_breakdown == []
    assert report.message is not None
    assert "alpha" in report.message.lower()


def test_cli_stub_mode_writes_valid_json(
    exporter: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CLI call with no DB produces a well-formed, parseable JSON file."""
    output = tmp_path / "track_record_latest.json"
    monkeypatch.delenv("SPORTSLAB_DATABASE_URL", raising=False)

    exit_code = exporter.main(["--output", str(output), "--days", "90"])

    assert exit_code == 0
    assert output.exists()
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "starting_soon"
    assert payload["schema_version"] == 1
    assert payload["window_days"] == 90
    assert payload["total_bets"] == 0


def test_cli_force_stub_overrides_db_url(
    exporter: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``--force-stub`` wins over an env-configured DB -- ops escape hatch."""
    output = tmp_path / "track_record_latest.json"
    monkeypatch.setenv(
        "SPORTSLAB_DATABASE_URL", "postgresql://nonexistent/not_a_real_db"
    )

    # Without --force-stub this would try to connect and blow up. With it,
    # we never touch the DB at all.
    exit_code = exporter.main(["--output", str(output), "--force-stub"])

    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "starting_soon"


def test_real_report_aggregates_seeded_sqlite(
    exporter: ModuleType, tmp_path: Path
) -> None:
    """Seed a SQLite DB with settled bets; verify shape + basic correctness."""
    db_path = tmp_path / "seed.db"
    db_url = f"sqlite:///{db_path}"

    # Build schema from the initial migration rather than re-declaring it here.
    from alembic import command
    from alembic.config import Config

    alembic_ini = _API_ROOT / "alembic.ini"
    config = Config(str(alembic_ini))
    config.set_main_option("script_location", str(_API_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", db_url)
    config.cmd_opts = type("_O", (), {"x": [f"db_url={db_url}"]})()
    command.upgrade(config, "head")

    # Seed one user + five settled bets mixed win/loss.
    engine = create_engine(db_url)
    now = datetime.now(tz=UTC)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO users (id, email, leagues_selected, markets_selected,"
            " notifications) VALUES ('u1', 'a@b.c', '[]', '[]', '{}')"
        )
        bets = [
            # (id, outcome, stake, pnl, days_ago)
            ("b1", "won", 10.0, 8.5, 30),
            ("b2", "lost", 10.0, -10.0, 25),
            ("b3", "won", 10.0, 12.0, 20),
            ("b4", "lost", 10.0, -10.0, 15),
            ("b5", "won", 10.0, 5.0, 10),
        ]
        for bet_id, outcome, stake, pnl, days_ago in bets:
            placed = (now - timedelta(days=days_ago)).isoformat()
            connection.exec_driver_sql(
                "INSERT INTO user_bets (id, user_id, match_id, market, selection,"
                " stake_eur, odds, bookmaker, placed_at, outcome, pnl_eur,"
                " follows_model) VALUES (?, 'u1', 'm1', '1X2', 'home', ?, 2.0,"
                " 'stub', ?, ?, ?, 0)",
                (bet_id, stake, placed, outcome, pnl),
            )

    report = exporter.build_report_from_db(
        db_url=db_url, since=date.today() - timedelta(days=60), window_days=60
    )

    assert report.status == "active"
    assert report.total_bets == 5
    # 3 wins out of 5 settled bets.
    assert report.hit_rate == pytest.approx(0.6, rel=1e-3)
    # Net PnL = 8.5 - 10 + 12 - 10 + 5 = 5.5 / total_stake 50 = 11%.
    assert report.roi_percent == pytest.approx(11.0, rel=1e-2)
    assert report.window_days == 60
    assert report.equity_curve, "equity curve should have at least one point"
    # Curve length = days from `since` to today, inclusive.
    expected_length = 60 + 1
    assert len(report.equity_curve) == expected_length
    # The final point's cumulative PnL matches total_pnl (sum over all bets).
    assert report.equity_curve[-1].pnl_eur == pytest.approx(5.5, rel=1e-3)


def test_max_drawdown_helper_is_non_positive(exporter: ModuleType) -> None:
    """Drawdown of a monotonically rising curve is zero; of a dip, negative."""
    point = exporter.EquityPoint

    flat_curve = [point(date="2026-01-01", bankroll_eur=0.0, pnl_eur=0.0)]
    assert exporter._compute_max_drawdown(flat_curve) == 0.0

    rising_curve = [
        point(date=f"2026-01-0{i}", bankroll_eur=float(i * 10), pnl_eur=float(i))
        for i in range(1, 5)
    ]
    assert exporter._compute_max_drawdown(rising_curve) == 0.0

    dip_curve = [
        point(date="2026-01-01", bankroll_eur=100.0, pnl_eur=0.0),
        point(date="2026-01-02", bankroll_eur=120.0, pnl_eur=20.0),
        point(date="2026-01-03", bankroll_eur=90.0, pnl_eur=-10.0),
    ]
    # Peak 120 -> trough 90 = -25%.
    assert exporter._compute_max_drawdown(dip_curve) == pytest.approx(-25.0, rel=1e-3)
