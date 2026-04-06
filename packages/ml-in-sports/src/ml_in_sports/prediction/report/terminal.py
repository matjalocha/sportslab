"""Rich terminal renderer for daily bet slips."""

from __future__ import annotations

import io

from rich.console import Console
from rich.table import Table

from ml_in_sports.prediction.daily import BetRecommendation


def print_terminal_bet_slip(
    predictions: list[BetRecommendation],
    console: Console | None = None,
) -> str:
    """Print a Rich bet slip table and return captured output.

    Args:
        predictions: Bet recommendations to render.
        console: Optional Rich console. A standard console is created when omitted.

    Returns:
        Rendered terminal output as a string, useful for tests.
    """
    buffer = io.StringIO()
    capture_console = Console(file=buffer, force_terminal=True, width=120)

    if console is None:
        console = Console(width=120)

    _render_to_console(predictions, console)
    _render_to_console(predictions, capture_console)
    return buffer.getvalue()


def render_terminal_bet_slip_string(predictions: list[BetRecommendation]) -> str:
    """Render a bet slip to a string without printing to stdout."""
    buffer = io.StringIO()
    console = Console(file=buffer, force_terminal=True, width=120)
    _render_to_console(predictions, console)
    return buffer.getvalue()


def print_bet_slip_terminal(bets: list[BetRecommendation]) -> None:
    """Compatibility wrapper that prints the bet slip using Rich."""
    print_terminal_bet_slip(bets)


def _render_to_console(predictions: list[BetRecommendation], console: Console) -> None:
    total_stake = sum(prediction.stake_eur for prediction in predictions)
    ev = sum(
        prediction.stake_eur * (prediction.model_prob * prediction.best_odds - 1.0)
        for prediction in predictions
    )
    ev_style = "green" if ev >= 0.0 else "red"
    console.print(
        "[bold]Daily Bet Slip[/bold] | "
        f"Bets: [bold]{len(predictions)}[/bold] | "
        f"Stake: [bold]EUR {total_stake:.2f}[/bold] | "
        f"EV: [{ev_style}]{ev:+.2f} EUR[/{ev_style}]"
    )

    if not predictions:
        console.print("[dim]Zero betów dzisiaj. Model nie znalazł wartości.[/dim]")
        return

    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    table.add_column("Match", min_width=24)
    table.add_column("League", min_width=18)
    table.add_column("Kickoff", justify="right", min_width=16)
    table.add_column("Market", min_width=10)
    table.add_column("Edge", justify="right", min_width=8)
    table.add_column("Kelly", justify="right", min_width=8)
    table.add_column("Stake", justify="right", min_width=10)
    table.add_column("Agreement", justify="center", min_width=9)
    table.add_column("Bookmaker", min_width=18)

    for prediction in predictions:
        table.add_row(
            f"{prediction.home_team} vs {prediction.away_team}",
            prediction.league,
            prediction.kickoff_dt.strftime("%Y-%m-%d %H:%M"),
            prediction.market,
            _format_edge(prediction.edge),
            f"{prediction.kelly_fraction:.2%}",
            f"EUR {prediction.stake_eur:.2f}",
            _format_agreement(prediction.model_agreement),
            f"{prediction.best_bookmaker} @ {prediction.best_odds:.2f}",
        )

    console.print(table)


def _format_edge(edge: float) -> str:
    style = "green" if edge >= 0.0 else "red"
    return f"[{style}]{edge:+.1%}[/{style}]"


def _format_agreement(model_agreement: int) -> str:
    if model_agreement >= 3:
        return "[bold green]3/3[/bold green]"
    if model_agreement == 2:
        return "[yellow]2/3[/yellow]"
    return "[dim]1/3[/dim]"
