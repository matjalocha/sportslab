# ADR-0003: pydantic-settings for configuration

- **Status**: Accepted
- **Date**: 2026-04-06
- **Deciders**: `architect`, `swe`

## Context

The research codebase had hardcoded paths (`os.environ.get()`, string literals) scattered across
at least 2 files, with no validation, no type safety, and no centralized configuration. Moving to
production requires a single source of truth for settings (database URLs, paths, thresholds, API
keys) that is validated at startup and documented by its schema.

## Options considered

1. **python-dotenv** -- Load `.env` into `os.environ`, access via `os.getenv()`.
   - Pros: minimal, widely used.
   - Cons: no type validation, no schema, no defaults documentation, stringly-typed.

2. **dynaconf** -- Multi-source config with TOML/YAML/env/vault support.
   - Pros: very flexible, supports multiple environments, secrets vaults.
   - Cons: heavy for current needs, learning curve, own DSL for settings files, no Pydantic
     integration out of the box.

3. **pydantic-settings** -- Pydantic models that read from env vars, `.env`, secrets files.
   - Pros: type validation at startup (crash early on bad config), auto-generated JSON Schema,
     `env_prefix` prevents collisions, integrates with existing Pydantic usage across the codebase,
     IDE autocompletion on settings fields.
   - Cons: one more dependency (though pydantic is already required).

## Decision

We choose **pydantic-settings**. Each package or app defines a `Settings` class inheriting from
`BaseSettings` with `env_prefix = "ML_IN_SPORTS_"` (production code) or app-specific prefix.
Settings are validated at import time -- missing or malformed values cause immediate, clear errors.
No `os.environ.get()` or `os.getenv()` in production code. **[PEWNE]** pydantic-settings is
maintained by the Pydantic team and is the documented approach for FastAPI configuration.

## Consequences

- **Positive**: every config value is typed, validated, and documented in one place. New
  contributors see the full config surface by reading the `Settings` class.
- **Negative**: requires `.env` file or env vars to be set before running -- mitigated by
  `.env.example` in repo root with all keys and sensible defaults.
- **Neutral**: secrets management (1Password/Doppler) in R5 will inject env vars that
  pydantic-settings reads transparently -- no code changes needed.
