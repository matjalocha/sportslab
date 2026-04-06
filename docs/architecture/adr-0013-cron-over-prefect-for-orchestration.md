# ADR-0013: cron over Prefect/Dagster for orchestration (R4)

- **Status**: Accepted
- **Date**: 2026-04-06
- **Deciders**: `architect`, `dataeng`, `swe`

## Context

The R4 daily pipeline (fetch odds, run model, generate stakes, notify) needs to run automatically
on a schedule. The original P5 plan specified Prefect for orchestration, but the adapted solo
founder roadmap (ADR-0010) questions whether a workflow orchestrator is justified for a single
daily pipeline on one VPS.

## Options considered

1. **Prefect** -- Python-native workflow orchestrator with UI, retries, observability.
   - Pros: DAG visualization, built-in retries, task-level observability, good Python DX.
   - Cons: requires Prefect server or Prefect Cloud ($), adds operational complexity (another
     service to run/monitor), significant dependency for one pipeline. **YAGNI at this scale.**

2. **Dagster** -- Asset-based orchestration with strong typing.
   - Pros: asset-centric model fits data pipelines well, good testing story.
   - Cons: even heavier than Prefect, requires Dagster daemon + webserver, overkill for one
     daily job.

3. **cron + Python script** -- System cron on Hetzner VPS triggers a Python entry point.
   - Pros: zero infrastructure overhead, trivially debuggable, logs to a file + structlog JSON,
     retry logic in 10 lines of Python, health check via simple HTTP ping to UptimeRobot.
   - Cons: no DAG visualization, no built-in retry UI, manual log inspection.

## Decision

We choose **cron + Python script** for R4 orchestration. A single crontab entry runs
`sl pipeline daily` (Typer CLI, ADR-0005) once per day. Retries are handled in Python with
exponential backoff. Logs are structured JSON (ADR-0002) written to a rotating file. Health
monitoring via UptimeRobot ping on successful completion. **[PEWNE]** one pipeline, one VPS,
one person -- cron is the right tool. **[HIPOTEZA]** if pipeline count grows beyond 3-4
interdependent jobs (R5+), we revisit Prefect. Until then, YAGNI.

## Consequences

- **Positive**: zero operational overhead, no extra services to maintain, trivially portable
  between VPS providers.
- **Negative**: no visual DAG, no built-in retry UI. Acceptable for a solo operator who reads
  logs directly.
- **Neutral**: the Python entry point (`sl pipeline daily`) is framework-agnostic -- switching
  to Prefect later means wrapping the same function in a `@flow` decorator, not rewriting logic.
