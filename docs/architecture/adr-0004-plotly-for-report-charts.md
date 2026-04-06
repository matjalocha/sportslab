# ADR-0004: Plotly over matplotlib for report charts

- **Status**: Accepted
- **Date**: 2026-04-06
- **Deciders**: `architect`, `designer`, `mleng`

## Context

Backtest reports are a core deliverable -- both for internal diagnostics and for B2B client demos.
Reports need interactive charts (hover to see exact values, zoom into date ranges, filter by
league) to be useful for non-technical stakeholders. The charting library choice affects every
report template across R2-R6.

## Options considered

1. **matplotlib** -- Standard Python plotting, static PNG/SVG output.
   - Pros: ubiquitous, huge ecosystem, fine-grained control.
   - Cons: static only, no hover/zoom/filter without separate JS layer, verbose API for styled
     output, poor default aesthetics for client-facing reports.

2. **Plotly** -- Interactive charts with CDN-hosted JS, self-contained HTML export.
   - Pros: hover, zoom, pan, filter built-in; self-contained HTML (no server needed); looks
     polished by default; Plotly Express for rapid prototyping; CDN JS keeps file sizes small.
   - Cons: heavier dependency than matplotlib, less control over pixel-perfect layout.

3. **Altair/Vega-Lite** -- Declarative grammar-of-graphics.
   - Pros: elegant API, good for notebooks.
   - Cons: less mature HTML export, smaller ecosystem for custom chart types (e.g., equity curves
     with drawdown shading), fewer examples for financial/sports analytics charts.

## Decision

We choose **Plotly** with CDN-hosted JavaScript, embedded in self-contained HTML reports.
Charts use Plotly Express for standard visualizations and `go.Figure` for custom ones (equity
curves, calibration plots, Kelly allocation waterfalls). Reports are single `.html` files that
can be emailed or served statically. **[PEWNE]** interactivity is a hard requirement for B2B
demos -- static charts are a non-starter for stakeholder presentations.

## Consequences

- **Positive**: reports are interactive, self-contained, and visually polished out of the box.
  Clients can explore data without asking for re-runs.
- **Negative**: Plotly is ~15MB installed; acceptable for a data science project.
- **Neutral**: matplotlib may still be used in research notebooks where interactivity is not
  needed -- this ADR governs production reports only.
