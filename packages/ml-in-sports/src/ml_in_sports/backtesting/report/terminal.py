"""Rich terminal summary for backtest results.

Produces a compact ~25-line summary matching the design spec.
Uses Rich for styled console output with tables and panels.
"""

from __future__ import annotations

import io
from collections import defaultdict

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ml_in_sports.backtesting.report.generator import ReportData
from ml_in_sports.backtesting.runner import BacktestResult

_SEMAPHORE_ICONS = {"green": "[OK]", "yellow": "[~]", "red": "[X]"}
_SEMAPHORE_STYLES = {"green": "bold green", "yellow": "bold yellow", "red": "bold red"}


def print_terminal_report(
    data: ReportData,
    console: Console | None = None,
    backtest_result: BacktestResult | None = None,
) -> str:
    """Print backtest summary to terminal and return as string.

    Args:
        data: Pre-computed report data from the generator.
        console: Optional Rich Console. If None, creates one that
            captures output to a string buffer.
        backtest_result: Optional raw backtest result. When provided,
            calibration method per model is rendered in the report.

    Returns:
        The rendered terminal output as a plain string (useful for
        testing and logging).
    """
    buffer = io.StringIO()
    capture_console = Console(file=buffer, force_terminal=True, width=80)

    if console is None:
        console = Console(width=80)

    _render_to_console(data, console, backtest_result)
    _render_to_console(data, capture_console, backtest_result)

    return buffer.getvalue()


def render_terminal_string(
    data: ReportData,
    backtest_result: BacktestResult | None = None,
) -> str:
    """Render terminal report to string without printing.

    Args:
        data: Pre-computed report data.
        backtest_result: Optional raw backtest result for calibration info.

    Returns:
        Rendered terminal output as string.
    """
    buffer = io.StringIO()
    console = Console(file=buffer, force_terminal=True, width=80)
    _render_to_console(data, console, backtest_result)
    return buffer.getvalue()


def _render_to_console(
    data: ReportData,
    console: Console,
    backtest_result: BacktestResult | None = None,
) -> None:
    """Render all report sections to a Rich console."""
    _render_header(data, console)
    _render_verdict(data, console)
    _render_hero_metrics(data, console)
    _render_model_comparison(data, console)
    _render_calibration_methods(backtest_result, console)
    _render_clv_per_league(data, console)
    _render_footer(data, console)


def _render_header(data: ReportData, console: Console) -> None:
    """Render the report title header."""
    timestamp = data.generated_at.strftime("%Y-%m-%d %H:%M")
    header_text = Text()
    header_text.append("SPORTSLAB BACKTEST REPORT\n", style="bold")
    header_text.append(
        f"Experiment: {data.experiment_name} | {timestamp}",
        style="dim",
    )
    console.print(Panel(header_text, border_style="blue"))


def _render_verdict(data: ReportData, console: Console) -> None:
    """Render the verdict banner line."""
    clv = data.hero_metrics.get("clv", 0.0)
    clv_color = data.semaphore.get("clv", "yellow")

    if clv_color == "green":
        style = "bold green"
        label = f"MODEL BEATS CLOSING LINE (CLV {clv * 100:+.2f}%)"
    elif clv_color == "yellow":
        style = "bold yellow"
        label = f"MARGINAL CLV (CLV {clv * 100:+.2f}%)"
    else:
        style = "bold red"
        label = f"MODEL DOES NOT BEAT CLOSING LINE (CLV {clv * 100:+.2f}%)"

    console.print(f"\nVERDICT: [{style}]{label}[/{style}]")


def _render_hero_metrics(data: ReportData, console: Console) -> None:
    """Render 2x4 hero metric grid."""
    h = data.hero_metrics
    sem = data.semaphore

    console.print("\n[bold]HERO METRICS[/bold]")

    rows = [
        [
            _format_metric("CLV", h.get("clv", 0), "%", sem.get("clv")),
            _format_metric("ROI", h.get("roi", 0), "%", sem.get("roi")),
        ],
        [
            _format_metric("Sharpe", h.get("sharpe", 0), ""),
            _format_metric("ECE", h.get("ece", 0), "%", sem.get("ece")),
        ],
        [
            _format_metric("Log Loss", h.get("log_loss", 0), "f4"),
            _format_metric("Brier", h.get("brier_score", 0), "f3"),
        ],
        [
            _format_metric("N Bets", h.get("n_bets", 0), "n"),
            _format_metric("Max DD", h.get("max_drawdown", 0), "%neg"),
        ],
    ]

    for left, right in rows:
        console.print(f"  {left:<36}|  {right}")


def _format_metric(
    label: str,
    value: float,
    fmt: str,
    semaphore_color: str | None = None,
) -> str:
    """Format a single metric for terminal display."""
    if fmt == "%":
        formatted = f"{value * 100:+.2f}%"
    elif fmt == "%neg":
        formatted = f"{value * 100:-.1f}%"
    elif fmt == "f4":
        formatted = f"{value:.4f}"
    elif fmt == "f3":
        formatted = f"{value:.3f}"
    elif fmt == "n":
        formatted = f"{int(value):,}"
    else:
        formatted = f"{value:.2f}"

    icon = ""
    if semaphore_color:
        icon = f" {_SEMAPHORE_ICONS.get(semaphore_color, '')}"

    return f"{label:<10}{formatted:>10}{icon}"


def _render_model_comparison(data: ReportData, console: Console) -> None:
    """Render model comparison table."""
    if not data.model_comparison:
        return

    console.print("\n[bold]MODEL COMPARISON[/bold]")

    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    table.add_column("Model", style="bold", min_width=14)
    table.add_column("LL", justify="right", min_width=8)
    table.add_column("ECE", justify="right", min_width=8)
    table.add_column("CLV", justify="right", min_width=8)
    table.add_column("ROI", justify="right", min_width=8)
    table.add_column("N Bets", justify="right", min_width=8)

    for row in data.model_comparison:
        clv_style = "green" if row.clv >= 0 else "red"
        roi_style = "green" if row.roi >= 0 else "red"

        table.add_row(
            row.model,
            f"{row.log_loss:.4f}",
            f"{row.ece * 100:.2f}%",
            f"[{clv_style}]{row.clv * 100:+.2f}%[/{clv_style}]",
            f"[{roi_style}]{row.roi * 100:+.2f}%[/{roi_style}]",
            f"{row.n_bets:,}",
        )

    console.print(table)


def _render_calibration_methods(
    backtest_result: BacktestResult | None,
    console: Console,
) -> None:
    """Render calibration method per model per fold.

    Shows which calibration method was selected for each model across
    folds. Skipped when no backtest result is provided or no calibration
    was applied.

    Args:
        backtest_result: Raw backtest result with fold-level calibration info.
        console: Rich console to render to.
    """
    if backtest_result is None:
        return

    # Collect calibration methods per model across folds
    model_methods: dict[str, list[str | None]] = defaultdict(list)
    for fold in backtest_result.fold_results:
        model_methods[fold.model_name].append(fold.calibration_method)

    # Skip if no calibration was applied anywhere
    all_methods = [m for methods in model_methods.values() for m in methods]
    if not any(all_methods):
        return

    console.print("\n[bold]CALIBRATION[/bold]")

    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    table.add_column("Model", style="bold", min_width=14)
    table.add_column("Method", min_width=12)
    table.add_column("Folds", justify="right", min_width=8)

    for model_name, methods in model_methods.items():
        applied = [m for m in methods if m is not None]
        if not applied:
            table.add_row(model_name, "[dim]none[/dim]", f"0/{len(methods)}")
            continue

        # Count most common method
        method_counts: dict[str, int] = defaultdict(int)
        for method in applied:
            method_counts[method] += 1

        dominant_method = max(method_counts, key=lambda m: method_counts[m])
        folds_applied = len(applied)

        if len(method_counts) == 1:
            method_display = dominant_method
        else:
            parts = [f"{m}({c})" for m, c in sorted(method_counts.items())]
            method_display = ", ".join(parts)

        table.add_row(model_name, method_display, f"{folds_applied}/{len(methods)}")

    console.print(table)


def _render_clv_per_league(data: ReportData, console: Console) -> None:
    """Render CLV per league table."""
    if not data.clv_per_league:
        return

    console.print("\n[bold]CLV PER LEAGUE[/bold]")

    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    table.add_column("League", min_width=20)
    table.add_column("N Bets", justify="right", min_width=8)
    table.add_column("Mean CLV", justify="right", min_width=10)
    table.add_column("% Pos", justify="right", min_width=8)
    table.add_column("ROI", justify="right", min_width=8)

    for row in data.clv_per_league:
        clv_style = "green" if row.mean_clv >= 0 else "red"
        roi_style = "green" if row.roi >= 0 else "red"

        table.add_row(
            row.league,
            f"{row.n_bets:,}",
            f"[{clv_style}]{row.mean_clv * 100:+.2f}%[/{clv_style}]",
            f"{row.pct_positive:.1f}%",
            f"[{roi_style}]{row.roi * 100:+.2f}%[/{roi_style}]",
        )

    console.print(table)


def _render_footer(data: ReportData, console: Console) -> None:
    """Render footer with report path hint."""
    console.print(
        f"\n[dim]Full report: reports/backtest_{data.generated_at:%Y-%m-%d}"
        f"_{data.experiment_name.lower().replace(' ', '_')}.html[/dim]",
    )
