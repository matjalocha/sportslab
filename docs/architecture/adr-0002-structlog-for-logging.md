# ADR-0002: structlog over loguru/stdlib logging

- **Status**: Accepted
- **Date**: 2026-04-06
- **Deciders**: `architect`, `mleng`

## Context

The research codebase (`ml_in_sports`) used `logging.getLogger()` across 19 source files with
inconsistent formatting, no structured output, and no correlation IDs. The production codebase
needs machine-readable logs (JSON) for future observability (Grafana/Loki in R5) while staying
readable in local development. A logging library decision affects every package and app.

## Options considered

1. **stdlib `logging`** -- Already in use; zero new deps.
   - Pros: no dependency, familiar API.
   - Cons: JSON output requires custom formatters, no structured key-value context by default,
     verbose configuration boilerplate.

2. **loguru** -- Drop-in replacement with nicer DX.
   - Pros: beautiful console output, zero-config, lazy formatting.
   - Cons: replaces stdlib entirely (monkey-patches), poor integration with libraries that use
     stdlib logging, JSON output is an add-on, not a first-class citizen.

3. **structlog** -- Structured logging that wraps stdlib.
   - Pros: JSON output is native, key-value context binding, works *with* stdlib (not against it),
     processors pipeline for filtering/enriching, widely adopted in Python backend services.
   - Cons: slightly higher learning curve than loguru, one new dependency.

## Decision

We choose **structlog** with JSON output in production and console renderer in development.
Configuration lives in `packages/config/` and is shared across all packages and apps. All
production code uses `structlog.get_logger()` with key-value context -- no `print()`, no bare
`logging.getLogger()`. **[PEWNE]** structlog's stdlib integration means third-party library logs
(e.g., SQLAlchemy, httpx) are automatically captured and formatted consistently.

## Consequences

- **Positive**: logs are structured JSON from day one, ready for Loki/Grafana without parsing.
  Local development stays readable via `ConsoleRenderer`.
- **Negative**: contributors must learn `logger.info("event_name", key=value)` style instead of
  f-string messages. Mitigated by linting rule and examples in CONTRIBUTING.md.
- **Neutral**: existing `logging.getLogger()` calls in migrated code are rewritten incrementally
  during R1 module migration (one module at a time, not a big-bang rewrite).
