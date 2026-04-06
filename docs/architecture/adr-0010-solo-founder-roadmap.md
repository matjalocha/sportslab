# ADR-0010: Solo founder roadmap R0-R6 replacing P0-P6

- **Status**: Accepted
- **Date**: 2026-04-06
- **Deciders**: `lead`, `architect`

## Context

The original SportsLab plan (P0-P6) assumed a 6-person team with a budget of 55-80k EUR/month.
Reality: one solo founder with Claude Code as the primary development partner. The original
timeline, task allocation, and infrastructure choices were designed for parallel execution by
specialists. A solo founder cannot run 6 workstreams in parallel and should not pre-invest in
infrastructure that only pays off at team scale.

## Options considered

1. **Keep P0-P6 unchanged** -- Execute the original plan solo, just slower.
   - Pros: no re-planning needed.
   - Cons: many tasks are irrelevant solo (team contracts, role-specific onboarding), infrastructure
     is over-specified (Prefect, Kubernetes, multi-env CI/CD), no validation gate before heavy
     investment.

2. **Adapted roadmap R0-R6** -- Resequence for one person, add a "Proof of Edge" gate (R3),
   defer team-scale infrastructure until after proven profitability.
   - Pros: validates the model before scaling, eliminates wasted effort on team/infra overhead,
     adds R3 as a go/no-go decision point.
   - Cons: requires re-planning, defers some P3/P4 work.

## Decision

We choose the **adapted R0-R6 roadmap**. Key changes from original P0-P6:
- **R0** (Foundations): stripped to solo-relevant tasks, no team contracts
- **R1** (Clean Code): code migration + production standards
- **R2** (Backtest Infra): walk-forward pipeline, reports, leakage detection
- **R3** (Proof of Edge): **new gate** -- paper-trading, CLV analysis, go/no-go for real money
- **R4** (Daily Pipeline): cron-based automation, live betting on Hetzner VPS
- **R5a/R5b** (Multi-sport + Product): deferred from P3/P4, only after proven edge
- **R6** (Product App): landing page + dashboard, only if B2B demand validated

**[PEWNE]** a solo founder must validate edge before building product infrastructure.
**[RYZYKO]** if R3 shows no edge, R4-R6 are cancelled -- this is a feature, not a bug.

## Consequences

- **Positive**: no wasted months building infrastructure for a model that does not beat the market.
  Clear kill criteria at R3.
- **Negative**: some decisions (multi-sport schema, team onboarding) are deferred and may need
  rework if/when a team forms. Acceptable -- premature abstraction is worse than rework.
- **Neutral**: Linear projects renamed from P0-P6 to R0-R6; existing issues re-tagged.
