# ADR-0012: Framer for landing page, Next.js for dashboard

- **Status**: Accepted
- **Date**: 2026-04-06
- **Deciders**: `architect`, `designer`, `swe`

## Context

SportsLab needs two distinct web properties in R6: a marketing landing page (attract B2B leads)
and a product dashboard (display backtest results, calibration, portfolio analytics to paying
clients). These have very different requirements -- the landing page is mostly static content
with animations, while the dashboard is a data-heavy interactive application.

## Options considered

1. **Next.js for both** -- Single framework, shared deployment.
   - Pros: one stack, shared components, unified deployment.
   - Cons: building a marketing landing page in Next.js is slow compared to no-code tools;
     a solo founder should not spend days on hero sections and CTA animations.

2. **Framer for landing, Next.js for dashboard** -- Best tool for each job.
   - Pros: Framer builds polished landing pages 10x faster (drag-and-drop, built-in animations,
     CMS for testimonials), hosted on Framer's CDN ($30/mo); Next.js handles the data-heavy
     dashboard with shadcn/ui + Tremor charts.
   - Cons: two deployment targets, Framer vendor lock-in for the landing page.

3. **WordPress/Webflow for landing** -- Traditional CMS approach.
   - Pros: familiar, huge plugin ecosystem.
   - Cons: WordPress is overkill and a security surface; Webflow is more expensive than Framer
     for comparable output.

## Decision

We choose **Framer** ($30/month) for the marketing landing page and **Next.js + shadcn/ui +
Tremor** for the product dashboard. The landing page is a separate domain/subdomain with no
shared code. Vendor lock-in on Framer is acceptable -- the landing page can be rebuilt in
Next.js in a few days if needed, and the content is the valuable part (copywriting, testimonials),
not the implementation. **[PEWNE]** a solo founder's time is the bottleneck; Framer eliminates
weeks of frontend work for the landing page.

## Consequences

- **Positive**: landing page ships in days instead of weeks. Dashboard uses production-grade
  React tooling appropriate for complex data visualization.
- **Negative**: two hosting targets, two deployment pipelines. Acceptable at this scale.
- **Neutral**: dashboard tech stack (Next.js App Router, TanStack Query, shadcn/ui, Tremor,
  Tailwind) is specified in `ideas/tech_stack.md` and will be detailed when R6 begins.
