"""CLI command: compute Kelly stakes for betting opportunities.

Wraps the research script ``scripts/kelly_stakes.py`` using
production imports from ``ml_in_sports.models.value_betting``.

NOTE: Bet definitions are currently hardcoded in the research script
and change weekly. This command exposes only the Kelly computation
parameters. A future version (P4+) will read bet definitions from
a database or YAML file.
"""

from typing import Annotated

import structlog
import typer

from ml_in_sports.models.value_betting import compute_kelly_stake, scale_to_budget

logger = structlog.get_logger(__name__)

kelly_app = typer.Typer(no_args_is_help=True)


def _round_to_nearest_ten(value: float) -> int:
    """Round to nearest 10 for practical bet sizing, minimum 10."""
    return max(10, round(value / 10) * 10)


@kelly_app.command("compute")
def compute(
    bankroll: Annotated[
        float,
        typer.Option("--bankroll", help="Total bankroll in currency units."),
    ] = 10_000.0,
    budget: Annotated[
        float,
        typer.Option("--budget", help="Maximum total stake per week."),
    ] = 1_000.0,
    fraction: Annotated[
        float,
        typer.Option("--fraction", help="Kelly fraction (0.25 = quarter-Kelly)."),
    ] = 0.25,
    max_stake_pct: Annotated[
        float,
        typer.Option(
            "--max-stake-pct",
            help="Hard cap per bet as fraction of bankroll.",
        ),
    ] = 0.02,
) -> None:
    """Compute variance-constrained Kelly stakes.

    Currently requires bet definitions to be loaded from a source file.
    A database-backed bet definition store is planned for P4+.

    This command validates that the Kelly computation engine works with
    the provided parameters by running a demonstration calculation.
    """
    # TODO SPO-TBD: Load bet definitions from database or YAML instead
    # of hardcoded values. For now, demonstrate the computation with
    # example parameters.
    logger.info(
        "kelly_compute_start",
        bankroll=bankroll,
        budget=budget,
        fraction=fraction,
        max_stake_pct=max_stake_pct,
    )

    # Demonstration: compute a single Kelly stake to verify the engine
    demo_p_model = 0.55
    demo_odds = 2.0
    demo_ece = 0.02

    p_conservative, f_star, stake = compute_kelly_stake(
        p_model=demo_p_model,
        odds=demo_odds,
        ece=demo_ece,
        bankroll=bankroll,
        fraction=fraction,
        max_stake_pct=max_stake_pct,
    )

    logger.info(
        "kelly_demo_result",
        p_model=demo_p_model,
        p_conservative=round(p_conservative, 4),
        odds=demo_odds,
        f_star=round(f_star, 4),
        raw_stake=round(stake, 2),
    )

    # Demonstrate budget scaling
    demo_stakes = [stake, stake * 0.8, stake * 0.5]
    scaled = scale_to_budget(demo_stakes, budget)
    rounded = [_round_to_nearest_ten(s) for s in scaled]

    logger.info(
        "kelly_budget_scaled",
        raw_total=round(sum(demo_stakes), 2),
        budget=budget,
        scaled_stakes=rounded,
        scaled_total=sum(rounded),
    )

    logger.info("kelly_compute_done")
