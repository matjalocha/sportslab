# ADR-0015: Report design -- Inter + JetBrains Mono + Plotly interactive

- **Status**: Accepted
- **Date**: 2026-04-06
- **Deciders**: `architect`, `designer`

## Context

Backtest reports are SportsLab's primary deliverable in R2-R4 (before any web dashboard exists)
and a key sales artifact for B2B demos. Reports serve two audiences: the founder (diagnostic
detail) and future clients (credibility, clarity). The design must be professional, readable,
and self-contained (single HTML file, no external server).

## Options considered

1. **Jupyter notebook export** -- Render notebooks to HTML.
   - Pros: familiar, code + output together.
   - Cons: looks like a data science notebook, not a professional report; code cells visible,
     inconsistent styling, poor typography.

2. **LaTeX/PDF** -- Academic-style typeset report.
   - Pros: beautiful typography, familiar in academia.
   - Cons: static (no interactive charts), heavy toolchain, hard to embed in email or browser.

3. **Self-contained HTML with design system** -- Custom HTML template with Inter (text),
   JetBrains Mono (numbers/code), Plotly interactive charts, responsive layout.
   - Pros: interactive charts (ADR-0004), professional typography, self-contained (single file,
     fonts from Google Fonts CDN, Plotly from CDN), works in any browser, can be emailed as
     attachment.
   - Cons: requires HTML/CSS template development (one-time cost).

## Decision

We choose **self-contained HTML reports** with the following design spec:
- **Text font**: Inter (Google Fonts CDN) -- clean, professional, excellent readability
- **Monospace font**: JetBrains Mono -- for numbers, tables, code snippets
- **Charts**: Plotly interactive (ADR-0004) -- hover for values, zoom, pan
- **Layout**: responsive, max-width 1200px, dark/light mode support
- **Output**: single `.html` file with all CSS inline, JS from CDN

Full design specification in `docs/design/backtest_report_spec.md`. **[PEWNE]** the report is
the product until R6 -- its design directly impacts B2B sales conversations.

## Consequences

- **Positive**: reports look professional and interactive from R2 onward. Single-file delivery
  is trivial (email, Slack, S3 link).
- **Negative**: initial template development takes ~1 day. One-time cost.
- **Neutral**: the HTML template becomes the foundation for the R6 dashboard design system --
  typography and color choices carry over to the Next.js product.

## References

- `docs/design/backtest_report_spec.md` -- full design specification
- ADR-0004 -- Plotly for chart rendering
