# ADR-0014: TabPFN as optional dependency

- **Status**: Accepted
- **Date**: 2026-04-06
- **Deciders**: `architect`, `mleng`

## Context

TabPFN is a foundation model for tabular data that shows strong performance on small datasets
(typical in sports analytics -- hundreds to low thousands of matches per league). However, it
requires PyTorch as a runtime dependency (~2GB installed), which makes CI pipelines 10x slower,
bloats Docker images, and is unnecessary on machines without GPU support. The model ensemble
should work with and without TabPFN.

## Options considered

1. **Required dependency** -- Always install TabPFN + PyTorch.
   - Pros: simpler code, no conditional imports.
   - Cons: CI installs 2GB+ of PyTorch on every run, Docker images bloated, CPU-only machines
     pay the cost for no benefit, breaks `uv sync` on resource-constrained environments.

2. **Optional dependency with graceful fallback** -- TabPFN is an extra (`pip install
   ml-in-sports[tabpfn]`), ensemble detects its absence and proceeds without it.
   - Pros: CI stays fast, base install is lean, GPU environments opt in, ensemble degrades
     gracefully (uses remaining models).
   - Cons: conditional import logic, must test both paths (with and without TabPFN).

3. **Separate package** -- `packages/ml-in-sports-tabpfn/` as its own workspace member.
   - Pros: clean separation.
   - Cons: premature -- only one model needs this treatment. Rule of Three applies.

## Decision

We choose **optional dependency with graceful fallback**. TabPFN is declared in
`[project.optional-dependencies] tabpfn = ["tabpfn", "torch"]` in `packages/ml-in-sports/
pyproject.toml`. At import time, a `try/except ImportError` sets a module-level flag. The
ensemble builder checks this flag and logs a warning if TabPFN is unavailable. CI runs without
the `tabpfn` extra by default; a separate CI job tests the TabPFN path on GPU runners (when
available). **[PEWNE]** this is a standard Python pattern for heavy optional dependencies.

## Consequences

- **Positive**: base install stays under 500MB, CI runs in < 2 minutes, ensemble works on any
  machine.
- **Negative**: two code paths to test (with/without TabPFN). Mitigated by `pytest.importorskip`
  in TabPFN-specific tests.
- **Neutral**: if more models require heavy deps (e.g., a future transformer model), we may
  revisit the separate-package approach (Option 3) -- but not until the third occurrence.
