# ADR-0006: Walk-forward CV (not k-fold) for backtesting

- **Status**: Accepted
- **Date**: 2026-04-06
- **Deciders**: `architect`, `drmat`, `mleng`

## Context

Sports match data is inherently temporal -- team form, player transfers, tactical trends, and
bookmaker line movements all evolve over time. Any cross-validation strategy that ignores temporal
ordering risks data leakage: the model sees future information during training, producing
artificially inflated accuracy that does not translate to live betting performance. This is the
single most dangerous failure mode for a value-betting system.

## Options considered

1. **k-fold CV** -- Randomly shuffle all matches, split into k folds.
   - Pros: maximizes data usage, standard in ML tutorials.
   - Cons: **fatal for temporal data** -- a model trained on 2023 data and tested on 2021 data
     has already "seen the future." Any reported edge is unreliable.

2. **Walk-forward CV** -- Train on seasons 1..N, validate on N+1. Slide the window forward.
   - Pros: respects temporal ordering, simulates real deployment (you only bet on future matches),
     detected leakage is real leakage. Calibration and Kelly decisions are also walk-forward.
   - Cons: fewer effective training folds (one per season boundary), cannot use most recent data
     for training in the final fold.

3. **Expanding window with purge** -- Like walk-forward but with a gap between train and test
   to account for delayed features.
   - Pros: handles feature lag.
   - Cons: adds complexity; not needed when features are strictly pre-match (our case after
     leakage detection in ADR-0011).

## Decision

We choose **walk-forward CV** as the only valid backtesting strategy. Train on seasons 1..N,
test on season N+1. Calibration method selection (ADR-0007) and Kelly parameter tuning (ADR-0008)
also use walk-forward -- no component in the pipeline sees future data. **[PEWNE]** this is
standard practice in quantitative finance and sports analytics; k-fold on temporal data is a
known anti-pattern.

## Consequences

- **Positive**: reported edge, ROI, and calibration metrics reflect realistic live performance.
  No "too good to be true" backtests.
- **Negative**: fewer evaluation folds means higher variance in performance estimates. Mitigated
  by reporting confidence intervals and using multiple seasons of data.
- **Neutral**: walk-forward is already implemented in the research codebase; this ADR formalizes
  the requirement and prohibits k-fold in production pipelines.
