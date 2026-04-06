"""Rich terminal renderer for weekly performance."""

from __future__ import annotations

import io

from rich.console import Console
from rich.table import Table

from ml_in_sports.prediction.weekly import WeeklyData


def print_weekly_terminal(data: WeeklyData, console: Console | None = None) -> str:
    """Print weekly performance and return captured output."""
    buffer = io.StringIO()
    capture_console = Console(file=buffer, force_terminal=True, width=120)
    if console is None:
        console = Console(width=120)
    _render(data, console)
    _render(data, capture_console)
    return buffer.getvalue()


def render_weekly_terminal_string(data: WeeklyData) -> str:
    """Render weekly performance to a string without printing."""
    buffer = io.StringIO()
    console = Console(file=buffer, force_terminal=True, width=120)
    _render(data, console)
    return buffer.getvalue()


def _render(data: WeeklyData, console: Console) -> None:
    pnl_style = "green" if data.pnl >= 0.0 else "red"
    console.print(
        f"[bold]Weekly Performance[/bold] | {data.week_start} to {data.week_end} | "
        f"Bets: {data.total_bets} | W-L: {data.wins}-{data.losses} | "
        f"P&L: [{pnl_style}]EUR {data.pnl:+.2f}[/{pnl_style}] | ROI: {data.roi_7d:+.2%}"
    )
    _render_rows("Per League", data.per_league, "league", console)
    _render_rows("Per Market", data.per_market, "market", console)


def _render_rows(
    title: str,
    rows: list[dict[str, str | int | float]],
    label_key: str,
    console: Console,
) -> None:
    if not rows:
        console.print(f"[dim]{title}: no data[/dim]")
        return
    table = Table(title=title, show_header=True, header_style="bold", box=None, pad_edge=False)
    table.add_column("Name")
    table.add_column("Bets", justify="right")
    table.add_column("W/L", justify="right")
    table.add_column("P&L", justify="right")
    table.add_column("ROI", justify="right")
    for row in rows:
        pnl = float(row["pnl"])
        style = "green" if pnl >= 0.0 else "red"
        table.add_row(
            str(row[label_key]),
            str(row["bets"]),
            f"{row['wins']}-{row['losses']}",
            f"[{style}]EUR {pnl:+.2f}[/{style}]",
            f"{float(row['roi']):+.2%}",
        )
    console.print(table)
