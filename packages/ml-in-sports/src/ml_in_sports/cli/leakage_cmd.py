"""CLI command: run automated leakage detection on features parquet.

Usage::

    sl leakage-check --data data/features/all_features.parquet
    sl leakage-check --data data/features/all_features.parquet --output docs/feature_leakage_audit.md
    sl leakage-check --data data/features/all_features.parquet --importance-threshold 8.0
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import numpy as np
import structlog
import typer
from rich.console import Console
from rich.table import Table

logger = structlog.get_logger(__name__)

leakage_app = typer.Typer(no_args_is_help=True)

console = Console()


@leakage_app.command("run")
def run(
    data: Annotated[
        Path,
        typer.Option("--data", help="Path to features parquet file."),
    ] = Path("data/features/all_features.parquet"),
    output: Annotated[
        Path,
        typer.Option("--output", help="Path for markdown report output."),
    ] = Path("docs/feature_leakage_audit.md"),
    importance_threshold: Annotated[
        float,
        typer.Option(
            "--importance-threshold",
            help="Multiplier for importance spike detection.",
        ),
    ] = 10.0,
    correlation_threshold: Annotated[
        float,
        typer.Option(
            "--correlation-threshold",
            help="Correlation threshold for suspicious features.",
        ),
    ] = 0.3,
) -> None:
    """Run automated leakage detection on features parquet."""
    from ml_in_sports.backtesting.data import BacktestDataLoader
    from ml_in_sports.backtesting.leakage import (
        generate_leakage_report,
        run_leakage_check,
    )

    logger.info(
        "leakage_check_cli_start",
        data_path=str(data),
        output_path=str(output),
    )

    loader = BacktestDataLoader(parquet_path=data)
    df = loader.load()
    feature_cols = loader.get_feature_columns()

    x = df[feature_cols]
    y = np.asarray(df["target"].values)

    console.print(
        f"\n[bold]Leakage Check[/bold]: {len(feature_cols)} features, "
        f"{len(y)} samples\n",
    )

    results = run_leakage_check(
        x,
        y,
        importance_threshold=importance_threshold,
        correlation_threshold=correlation_threshold,
    )

    # Terminal summary
    leakers = results[results["final_verdict"] == "leaker"]
    suspicious = results[results["final_verdict"] == "suspicious"]
    safe = results[results["final_verdict"] == "safe"]

    console.print(f"[green]Safe[/green]: {len(safe)}")
    console.print(f"[yellow]Suspicious[/yellow]: {len(suspicious)}")
    console.print(f"[red]Leakers[/red]: {len(leakers)}")
    console.print()

    if len(leakers) > 0:
        table = Table(title="Confirmed Leakers", show_lines=True)
        table.add_column("Feature", style="red")
        table.add_column("Importance Ratio", justify="right")
        table.add_column("Correlation", justify="right")
        table.add_column("Name Class")
        table.add_column("Reasons")

        for _, row in leakers.iterrows():
            table.add_row(
                str(row["feature"]),
                f"{row['importance_ratio']:.1f}x",
                f"{row['correlation']:.3f}",
                str(row["name_class"]),
                str(row["reasons"]),
            )
        console.print(table)
        console.print()

    if len(suspicious) > 0:
        table = Table(title="Suspicious Features", show_lines=True)
        table.add_column("Feature", style="yellow")
        table.add_column("Importance Ratio", justify="right")
        table.add_column("Correlation", justify="right")
        table.add_column("Name Class")
        table.add_column("Reasons")

        for _, row in suspicious.iterrows():
            table.add_row(
                str(row["feature"]),
                f"{row['importance_ratio']:.1f}x",
                f"{row['correlation']:.3f}",
                str(row["name_class"]),
                str(row["reasons"]),
            )
        console.print(table)
        console.print()

    # Generate markdown report
    report_path = generate_leakage_report(results, output)
    console.print(f"[bold]Report saved[/bold]: {report_path}\n")

    logger.info("leakage_check_cli_complete", report_path=str(report_path))
