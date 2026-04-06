# ADR-0007: CalibrationSelector with walk-forward selection

- **Status**: Accepted
- **Date**: 2026-04-06
- **Deciders**: `architect`, `drmat`, `mleng`

## Context

Model probabilities must be well-calibrated for Kelly staking to work -- if the model says 60%
but the true frequency is 50%, Kelly will systematically overbet. Multiple calibration methods
exist (temperature scaling, Platt scaling, isotonic regression), and empirically no single method
dominates across all leagues, seasons, and model types. Fixing one method risks silent
degradation when conditions change.

## Options considered

1. **Fixed calibration method** -- Always use isotonic regression (or always Platt).
   - Pros: simple, deterministic.
   - Cons: when the fixed method underperforms for a given league/season, calibration degrades
     silently and Kelly overbets. No adaptability.

2. **Manual selection per league** -- Analyst picks method based on calibration plots.
   - Pros: human judgment.
   - Cons: does not scale, requires expert review every season, subjective.

3. **CalibrationSelector with walk-forward ECE** -- Automatically evaluate {temperature, platt,
   isotonic, beta} on each walk-forward fold, select the method with lowest Expected Calibration
   Error (ECE) on the validation set, apply it to the test set.
   - Pros: adapts per fold, fully automated, respects temporal ordering (ADR-0006), transparent
     (logs which method was selected and why).
   - Cons: slightly more complex than fixed method, requires enough validation data per fold.

## Decision

We choose **CalibrationSelector with walk-forward selection**. For each walk-forward fold, all
candidate methods are fit on the training set and evaluated on validation ECE. The best method
is applied to produce calibrated probabilities for the test set. Selection metadata is logged
for auditability. **[PEWNE]** this prevents the "one method fits all" trap that would silently
degrade staking performance.

## Consequences

- **Positive**: calibration adapts to data characteristics per fold. Bad calibration methods are
  automatically excluded. Full audit trail of which method won and why.
- **Negative**: adds ~5 seconds per fold (fitting 4 methods instead of 1). Acceptable for
  offline backtesting.
- **Neutral**: new calibration methods can be added to the candidate set without changing the
  selection logic -- the framework is extensible by design.
