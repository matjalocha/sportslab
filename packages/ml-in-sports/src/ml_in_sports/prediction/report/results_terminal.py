"""Rich terminal renderer for daily bet results."""

from __future__ import annotations

import io

from rich.console import Console
from rich.table import Table

from ml_in_sports.prediction.results import BetResult


def print_results_terminal(
    results: list[BetResult],
    console: Console | None = None,
) -> str:
    """Print daily bet results and return captured output."""
    buffer = io.StringIO()
    capture_console = Console(file=buffer, force_terminal=True, width=120)
    if console is None:
        console = Console(width=120)
    _render_to_console(results, console)
    _render_to_console(results, capture_console)
    return buffer.getvalue()


def render_results_terminal_string(results: list[BetResult]) -> str:
    """Render daily bet results to a string without printing."""
    buffer = io.StringIO()
    console = Console(file=buffer, force_terminal=True, width=120)
    _render_to_console(results, console)
    return buffer.getvalue()


def _render_to_console(results: list[BetResult], console: Console) -> None:
    wins = sum(1 for result in results if result.hit)
    losses = len(results) - wins
    pnl = sum(result.pnl for result in results)
    clv_values = [result.clv for result in results if result.clv is not None]
    mean_clv = sum(clv_values) / len(clv_values) if clv_values else 0.0
    pnl_style = "green" if pnl >= 0.0 else "red"
    console.print(
        "[bold]Daily Results[/bold] | "
        f"W-L: [bold]{wins}-{losses}[/bold] | "
        f"P&L: [{pnl_style}]EUR {pnl:+.2f}[/{pnl_style}] | "
        f"CLV: {mean_clv:+.2%}"
    )
    if not results:
        console.print("[dim]No bet results to display.[/dim]")
        return

    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    table.add_column("Match", min_width=24)
    table.add_column("Score", justify="center", min_width=6)
    table.add_column("Bet", min_width=10)
    table.add_column("Result", justify="center", min_width=8)
    table.add_column("Odds", justify="right", min_width=6)
    table.add_column("CLV", justify="right", min_width=8)
    table.add_column("P&L", justify="right", min_width=10)
    table.add_column("Bankroll", justify="right", min_width=10)

    for result in results:
        recommendation = result.recommendation
        status = "[bold green]WIN[/bold green]" if result.hit else "[bold red]MISS[/bold red]"
        pnl_color = "green" if result.pnl >= 0.0 else "red"
        table.add_row(
            f"{recommendation.home_team} vs {recommendation.away_team}",
            result.actual_score,
            recommendation.market,
            status,
            f"{recommendation.best_odds:.2f}",
            f"{result.clv:+.2%}" if result.clv is not None else "n/a",
            f"[{pnl_color}]EUR {result.pnl:+.2f}[/{pnl_color}]",
            f"EUR {result.bankroll_after:.2f}",
        )
    console.print(table)
