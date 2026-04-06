# ADR-0005: Typer for CLI framework

- **Status**: Accepted
- **Date**: 2026-04-06
- **Deciders**: `architect`, `swe`

## Context

The research codebase used `argparse` in standalone scripts with no consistent CLI structure.
The production codebase needs a unified CLI (`sl`) with subcommands for pipeline execution,
feature engineering, backtesting, Kelly staking, and data refresh. The CLI is the primary
interface during R1-R4 (before any web UI exists).

## Options considered

1. **argparse** -- stdlib, no dependencies.
   - Pros: zero deps, familiar.
   - Cons: verbose boilerplate, no type inference, manual help text, poor subcommand ergonomics,
     no auto-completion generation.

2. **click** -- Decorator-based CLI framework, mature ecosystem.
   - Pros: widely adopted, good docs, plugin ecosystem.
   - Cons: decorators duplicate type information (decorator params vs function signature),
     not type-safe by default, requires `click.testing.CliRunner` for tests.

3. **Typer** -- Built on click, type-hint-driven CLI.
   - Pros: CLI arguments inferred from function type hints (DRY), auto-generated `--help` from
     docstrings, subcommand pattern via `app.add_typer()`, shell completion, built-in testing
     support, familiar to anyone who knows FastAPI's style.
   - Cons: depends on click (transitive), slightly less flexible than raw click for edge cases.

## Decision

We choose **Typer** with a subcommand pattern: `sl pipeline`, `sl features`, `sl backtest`,
`sl kelly`, `sl refresh`. Each subcommand maps to a module in `packages/ml-in-sports/src/
ml_in_sports/cli/`. Type hints on function parameters define CLI arguments and options --
no duplication between code and CLI schema. **[PEWNE]** Typer is maintained by the FastAPI
author (tiangolo) and follows the same "type hints as the source of truth" philosophy.

## Consequences

- **Positive**: CLI is self-documenting, type-safe, and testable. Adding a new subcommand is
  one function with type hints.
- **Negative**: transitive dependency on click; acceptable since click is stable and widely used.
- **Neutral**: shell completion scripts can be generated for bash/zsh/fish via
  `typer --install-completion` -- nice for daily use during R3-R4.
