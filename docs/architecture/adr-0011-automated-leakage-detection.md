# ADR-0011: Automated leakage detection module

- **Status**: Accepted
- **Date**: 2026-04-06
- **Deciders**: `architect`, `mleng`, `drmat`

## Context

The features parquet file contains 400+ engineered features, a mix of pre-match statistics
(valid for betting) and post-match data (goals scored, final xG -- information not available
before kickoff). If post-match features leak into training, the model learns to "predict" using
information it would never have in production, producing useless edge estimates. Manual audit of
400+ columns is error-prone and not repeatable when features are added or renamed.

## Options considered

1. **Manual audit** -- Analyst reviews each feature column and flags post-match ones.
   - Pros: human judgment catches subtle cases.
   - Cons: 400+ features, tedious, error-prone, must be repeated every time features change,
     not scalable.

2. **Name-based heuristic only** -- Flag features whose names contain "goals", "result", "score".
   - Pros: simple, fast.
   - Cons: misses encoded or derived post-match features that don't have obvious names.

3. **4-strategy automated detection** -- Combine multiple signals:
   (a) Feature importance spike detection (features that are unrealistically important),
   (b) Target correlation analysis (features with suspiciously high correlation to outcome),
   (c) Name heuristics (known post-match keywords),
   (d) Combined scoring with configurable thresholds.
   - Pros: catches leakage that any single strategy would miss, repeatable, runs as part of
     CI/pipeline, produces an audit report.
   - Cons: may produce false positives (legitimate strong predictors flagged as leaky), requires
     threshold tuning.

## Decision

We choose the **4-strategy automated detection module**. It runs as a pipeline step before model
training and produces a leakage audit report (HTML). Features flagged by 2+ strategies are
auto-excluded; features flagged by 1 strategy are warned for manual review. Thresholds are
configurable via settings (ADR-0003). **[PEWNE]** automated detection is the only scalable
approach for 400+ features. **[HIPOTEZA]** the 2-strategy threshold balances false positives
and missed leakage -- to be validated during R2 backtest runs.

## Consequences

- **Positive**: leakage is caught automatically and reproducibly. New features are checked on
  every pipeline run. Audit trail for clients showing due diligence.
- **Negative**: initial threshold tuning requires manual validation of flagged features.
  One-time cost during R2.
- **Neutral**: the module produces a report that feeds into the backtest report (ADR-0004,
  ADR-0015), so clients see leakage analysis alongside performance metrics.
