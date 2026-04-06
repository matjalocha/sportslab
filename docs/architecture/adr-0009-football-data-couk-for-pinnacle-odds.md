# ADR-0009: football-data.co.uk for Pinnacle closing odds

- **Status**: Accepted
- **Date**: 2026-04-06
- **Deciders**: `architect`, `dataeng`

## Context

Closing Line Value (CLV) against Pinnacle is the gold standard for measuring a model's predictive
edge. Pinnacle's closing line is widely regarded as the most efficient price in football betting.
However, Pinnacle does not accept customers from Poland (geo-blocked), so direct API access is
not available. We need a reliable source of historical and near-live Pinnacle odds.

## Options considered

1. **Direct Pinnacle API** -- Official API access.
   - Pros: most accurate, real-time data.
   - Cons: **unavailable from Poland** without VPN, requires Pinnacle account with funded balance,
     geo-restriction may violate ToS if circumvented.

2. **football-data.co.uk CSV files** -- Free historical odds data including Pinnacle closing lines.
   - Pros: free, reliable (20+ years of history), updated weekly, includes Pinnacle Max/Avg
     closing odds for major leagues, widely used in academic research.
   - Cons: historical only (not real-time), limited to leagues they cover, ~1 week delay.

3. **The Odds API** -- Aggregator with free tier (500 requests/month).
   - Pros: near-live odds from multiple bookmakers including Pinnacle, REST API, free tier
     sufficient for daily pipeline.
   - Cons: free tier limited, Pinnacle coverage depends on region, no historical archive.

## Decision

We use **football-data.co.uk CSVs** as the primary source for historical Pinnacle closing odds
(backtesting, R1-R3) and **The Odds API free tier** as a supplementary source for near-live odds
(R4 daily pipeline). Both are free, legal, and do not require VPN or Pinnacle account.
**[PEWNE]** football-data.co.uk is the standard academic source for historical football odds.
**[DO SPRAWDZENIA]** whether The Odds API free tier covers all target leagues with Pinnacle
lines -- verify during R4 pipeline setup.

## Consequences

- **Positive**: zero cost, legal compliance, sufficient for both backtesting and live operation.
- **Negative**: football-data.co.uk has ~1 week delay -- not suitable for pre-match live betting
  decisions. Mitigated by The Odds API for near-live use.
- **Neutral**: if Pinnacle becomes available in Poland or via a legal intermediary, we can switch
  to direct API without changing the data schema -- odds are stored in a normalized format.
