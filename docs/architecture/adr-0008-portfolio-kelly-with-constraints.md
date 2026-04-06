# ADR-0008: Portfolio Kelly with shrinkage and constraints

- **Status**: Accepted
- **Date**: 2026-04-06
- **Deciders**: `architect`, `drmat`, `mleng`

## Context

The Kelly criterion is mathematically optimal for bankroll growth but assumes independent bets,
perfect calibration, and known edge -- none of which hold in practice. Naive full Kelly on
correlated football bets (e.g., multiple matches in the same round, same league, same team) leads
to catastrophic drawdowns and potential ruin. A production staking system must constrain Kelly to
survive real-world conditions.

## Options considered

1. **Naive (full) Kelly** -- Stake = edge / odds for each bet independently.
   - Pros: mathematically optimal under ideal assumptions.
   - Cons: extreme volatility, 50%+ drawdowns common, assumes independence (football matches
     in the same round are correlated), amplifies calibration errors.

2. **Fixed fractional Kelly** -- Always use 1/4 Kelly (quarter-Kelly).
   - Pros: simple, reduces volatility by ~75%, well-studied.
   - Cons: does not address correlation or exposure concentration.

3. **Portfolio Kelly with shrinkage + constraints** -- Quarter-Kelly default with per-match,
   per-round, per-league, and per-team exposure caps, plus shrinkage toward market-implied
   probabilities.
   - Pros: handles correlation via exposure caps, handles calibration uncertainty via shrinkage,
     quarter-Kelly reduces base volatility, constraints are configurable per risk appetite.
   - Cons: more parameters to tune, requires walk-forward validation of constraint thresholds.

## Decision

We choose **Portfolio Kelly with shrinkage and constraints**. Default configuration:
- **Quarter-Kelly** (fraction = 0.25) as base
- **Per-match cap**: max 3% of bankroll on any single bet
- **Per-round cap**: max 10% of bankroll on concurrent matches
- **Per-league cap**: max 15% of bankroll in one league
- **Shrinkage**: blend model probability toward market-implied probability (configurable weight)

All thresholds are configurable via `pydantic-settings` (ADR-0003) and validated via walk-forward
backtesting (ADR-0006). **[PEWNE]** quarter-Kelly is the industry standard compromise between
growth and survival. **[HIPOTEZA]** exposure caps are based on initial analysis and will be
refined after R3 live paper-trading.

## Consequences

- **Positive**: dramatically reduces ruin probability and drawdown depth compared to naive Kelly.
  Exposure caps prevent correlated blow-ups.
- **Negative**: suboptimal growth rate compared to theoretical full Kelly. Acceptable -- survival
  matters more than theoretical optimality.
- **Neutral**: constraint thresholds are initial estimates. They will be validated during R3
  paper-trading and adjusted based on observed drawdown characteristics.
