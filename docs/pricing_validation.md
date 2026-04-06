# Pricing Validation — SKU 1/2/3 vs Live Market

> **Task**: P0.25 from `ideas/phase_0_foundations/tasks.md`
> **Linear issue**: [SPO-29](https://linear.app/sportslab/issue/SPO-29/p025-pricing-research-konkurenci-b2b)
> **Scope**: Validate drafted prices in `ideas/phase_6_product_app/product_offerings.md` (SKU 1 Value Feed API, SKU 2 Data Lake, SKU 3 Probabilities API) against live market rates from 3 comparable vendors
> **Out of scope**: Enterprise/club products (SKU 4-6, 8) — those compete with Stats Perform/Opta/Statsbomb Enterprise, whose pricing is not public. SKU 7 (Backtest-as-a-Service), SKU 9 (Telegram B2C) — no directly comparable vendors in transparent tier
> **Method**: Live WebFetch of vendor pricing pages (2026-04-05)
> **Author**: Claude Code main agent (not subagent — subagent `lead` attempted this task but was blocked by WebFetch permissions; after granting access, main agent completed validation)

---

## TL;DR

**Verdict**: SKU 1-3 draft prices are **2-5× above API-first market rates**. Not necessarily wrong — depends on positioning — but the user must know it's a **premium anchor**, not a market-rate anchor.

- **SKU 1 Basic (€99)** vs API-Football Pro ($19 ≈ €17.5): **5.6× premium**
- **SKU 1 Pro (€299)** vs The Odds API 100K ($59 ≈ €54.5): **5.5× premium**
- **SKU 2 Researcher (€49)** vs Sportmonks Starter (€29): **1.7× premium**
- **SKU 2 Professional (€199)** vs Sportmonks Growth (€99): **2.0× premium**
- **SKU 3 Starter (€79)** vs API-Football Pro ($19 ≈ €17.5): **4.5× premium**

Two interpretations, both valid:
1. **[HIPOTEZA — pro-SportsLab]** SportsLab sells **value bets + predictions**, not raw data. That is a higher-margin product (analytics, not commodity). Premium is justified if ML quality is provably better than customer building their own on raw data. Pinnacle/Betfair-grade CLV tracking + calibrated probabilities is a different category than Sportmonks stats.
2. **[RYZYKO — cautionary]** API-first buyers are price-sensitive and commoditized. If SportsLab enters with €99 basic vs €17 alternatives, conversion will be brutal unless value proposition is differentiated **loudly** (calibration metrics, CLV receipts, free trial with real data).

---

## Vendor data — API-first tier (SKU 1-3 comparables)

### 1. [API-Football](https://www.api-football.com/pricing)

Transparent tiers, confirmed 2026-04-05:

| Tier | Monthly USD | ≈ EUR | Daily calls | Coverage |
|---|---:|---:|---:|---|
| Free | $0 | €0 | 100 | All endpoints, limited seasons |
| Pro | $19 | €17.5 | 7,500 | All endpoints, full seasons |
| Ultra | $29 | €26.5 | 75,000 | Same |
| Mega | $39 | €36 | 150,000 | Same |
| Custom | — | — | up to 1.5M | Negotiated |

Annual discount: up to -30%. Covers football + multi-sport (AFL, Baseball, Basketball, F1, Handball, Hockey, MMA, NBA, NFL, Rugby, Volleyball).

**Positioning**: Cheapest credible B2B sports data API. Developer-first, commodity pricing.

### 2. [The Odds API](https://the-odds-api.com/#get-access)

Transparent tiers, confirmed 2026-04-05:

| Tier | Monthly USD | ≈ EUR | Monthly credits | Coverage |
|---|---:|---:|---:|---|
| Starter | $0 | €0 | 500 | All sports, bookmakers, markets, historical |
| 20K | $30 | €27.6 | 20,000 | Same |
| 100K | $59 | €54.5 | 100,000 | Same |
| 5M | $119 | €109.5 | 5,000,000 | Same |
| 15M | $249 | €229 | 15,000,000 | Same |

Covers 70+ sports, 40+ bookmakers globally (DraftKings, FanDuel, BetMGM, William Hill, Betfair, Sportsbet, TAB). Markets: H2H, spreads, totals, outrights, player props.

**Positioning**: Closest direct competitor to SKU 1 (Value Feed API). They aggregate odds, SportsLab would aggregate odds + add value signal.

### 3. [Sportmonks Football API](https://www.sportmonks.com/football-api/plans-pricing/)

Transparent tiers, confirmed 2026-04-05 (via [search](https://www.sportmonks.com/football-api/plans-pricing/) — direct fetch returned 404, data from web search):

| Tier | Monthly EUR | Yearly EUR/m | League coverage | API calls/hour |
|---|---:|---:|---|---:|
| Free | €0 | — | Danish Superliga + Scottish Premiership | n/a |
| Starter | €29 | €24 | Pick any 5 leagues | 2,000/entity |
| Growth | €99 | €79 | Pick any 30 leagues | 2,500/entity |
| Pro | €249 | €199 | Pick any 120 leagues | 3,000/entity |
| Enterprise | Custom | Custom | All 2,300+ leagues | 5,000/entity |

All plans: fixtures, live scores, team/player info, advanced stats. 14-day free trial on paid plans. Annual billing -20% vs monthly.

**Positioning**: Direct competitor to SKU 2 (Data Lake). Same value prop: "one API for football data, historical + live".

### 4. [Statsbomb / Hudl](https://www.hudl.com/products/statsbomb) — reference for enterprise

- **Pricing**: **Not public** — enterprise-only, contact sales
- **Customer base**: 330+ professional clubs and organizations
- **Product**: Event data (3,400 events/match), 360° tracking data, 190+ competitions
- **Acquired by Hudl** — no longer independent
- **Free tier**: Open data only (research/public use, limited leagues)
- **Educational**: £60 course as loss-leader

**Relevance**: SKU 4 (Club Analytics Dashboard) explicitly positions "Statsbomb-quality at €500-3000/mo vs €50k/yr". This narrative is supported by the absence of public Statsbomb pricing — they don't want small clubs even asking. SportsLab's target (lower-tier leagues, academies) is genuinely underserved.

---

## Head-to-head — SKU 1 (Value Feed API)

SportsLab SKU 1 draft pricing:

| Plan | Calls/month | Price | Overage |
|---|---:|---:|---|
| Basic | 1,000 | €99/mo | €0.01/call |
| Pro | 10,000 | €299/mo | €0.01/call |
| Enterprise | Unlimited | €999/mo | — |

**Closest comparable**: The Odds API (because they also aggregate odds, not just stats).

| Metric | SportsLab Basic | The Odds API 20K | Ratio |
|---|---|---|---|
| Price | €99/mo | €27.6/mo | **3.6× premium** |
| Calls | 1,000/mo | 20,000/mo | SportsLab 20× less |
| Coverage | 3 sports × 10 leagues | 70+ sports, all markets | SportsLab much narrower |
| Differentiator | Value bet signal (ML) | Raw odds | SportsLab analytics-first |

**[RYZYKO]** At current draft pricing, a price-sensitive buyer doing a spreadsheet comparison will walk. The "value signal" story must be demonstrable in a **7-day free trial with real bets and real CLV**, not marketing copy. Otherwise SKU 1 Basic conversion will be <1%.

**[HIPOTEZA]** If SportsLab can show **CLV > 0 over 100+ bets** as a public receipt (e.g., on landing page, updated daily), the premium is defensible. CLV-based proof is the only hard metric that separates analytics vendors from raw data vendors.

**Recommended adjustment** [DO SPRAWDZENIA]: consider repositioning Basic as "Trial + Proof" at €49/mo with **200 value bets/mo** (not 1000 calls) — match the granularity that matters (bets, not calls). 10-bet free trial, €0.25/bet overage. This reframes the comparison from "I pay €99 for 1000 API calls" to "I pay €49 for 200 curated value bets" — the latter is worth more to a solo tipster than the former.

---

## Head-to-head — SKU 2 (Data Lake Access)

SportsLab SKU 2 draft pricing:

| Plan | Queries/day | Download/mo | Price |
|---|---:|---:|---:|
| Researcher | 100 | 1 GB | €49/mo |
| Professional | 1,000 | 10 GB | €199/mo |
| Enterprise | Unlimited | 100 GB | €599/mo |

**Closest comparable**: Sportmonks (both position as "raw football data API").

| Metric | SportsLab Researcher | Sportmonks Starter | Ratio |
|---|---|---|---|
| Price | €49/mo | €29/mo | **1.7× premium** |
| Coverage | 10 leagues × 4 sports | 5 football leagues | SportsLab broader (if delivered) |
| Historical | Yes | Yes | Even |
| API rate | 100/day | 2,000/hour/entity (~48k/day) | Sportmonks far higher |

**[PEWNE]** The €49 Researcher tier is priced **reasonably close** to market. 1.7× premium is justifiable if multi-sport (football + tennis + basketball + hockey) is real — Sportmonks is football-only. Solo academics and fantasy devs **will pay €49 over €29 for multi-sport if coverage is equivalent**.

**[RYZYKO]** The €199 Professional tier is **2× Sportmonks Growth (€99)** with fewer queries (1,000/day vs ~60,000/day equivalent). Unless SportsLab's data is demonstrably **richer** (xG, predictions, calibration metrics), this tier gets commoditized. Consider adjusting Professional to €149/mo or doubling query limits.

**[HIPOTEZA]** The €599 Enterprise tier is defensible — Sportmonks Enterprise is "Custom pricing" (likely €500-1500+/mo based on league count). SportsLab at €599 with direct Postgres access is actually a reasonable price point for lower-tier enterprise.

---

## Head-to-head — SKU 3 (Probabilities API)

SportsLab SKU 3 draft pricing:

| Plan | Calls/month | Price |
|---|---:|---:|
| Starter | 1,000 | €79/mo |
| Growth | 20,000 | €399/mo |
| Scale | 200,000 | €1,499/mo |

**No direct API-first competitor**. Stats Perform, Statsbomb, and Opta sell probabilities to enterprise only (no public API tier). Sportmonks offers "predictions" but not calibrated probabilities at scale. This is a **potential greenfield** in the API tier space.

**[HIPOTEZA]** SKU 3 could be **SportsLab's strongest API differentiator** — nobody else ships calibrated probabilities with ECE receipts via transparent API pricing. But:

**[RYZYKO]** If SKU 3 Starter (€79) is priced alongside API-Football Pro (€17.5, includes "predictions" as part of "all endpoints"), the naive buyer picks API-Football. The differentiator must be **ECE metric + model version tracking + historical predictions for backtesting** — these are in the SKU 3 spec but will be invisible unless the landing page leads with them.

**[DO SPRAWDZENIA]** Verify exactly what "predictions" API-Football ships at €17.5/mo. If it's uncalibrated class predictions (H/D/A outputs), the SKU 3 €79 tier still has daylight. If it's calibrated probabilities with any ECE metric, SKU 3 is in trouble.

---

## Market positioning summary

SportsLab's 9 SKU portfolio lives in **three distinct markets**:

| Market | SKUs | Competition | Pricing pressure |
|---|---|---|---|
| **API commodity** | SKU 1, 2, 3 | API-Football (€17), The Odds API (€27), Sportmonks (€29) | **HIGH** — market expects €20-100/mo at starter tier |
| **Mid-market clubs** | SKU 4, 5 | Statsbomb/Hudl (enterprise only, opaque), Wyscout/Instat (closed) | **LOW** — underserved, €500-3000/mo is a real gap in the market |
| **Enterprise / custom** | SKU 6, 8 | Stats Perform, Genius Sports, Sportradar | **HIGH but different** — not price, relationship-driven sales |
| **B2C** | SKU 9 | Telegram tipster bots (varied, €10-100/mo) | **HIGH** — acquisition cost problem |

The **SKU 4 Club Analytics Dashboard** (€499-2999/mo) is the most strategically sound pricing in the 9-SKU portfolio. It's in a market segment where competitors hide pricing exactly because they target enterprise — leaving mid-market clubs (Ekstraklasa, Championship lower, 2 Bundesliga, etc.) genuinely without options. This matches the target described in `product_offerings.md` SKU 4.

---

## Recommendations

### [PEWNE] Actions

1. **Keep SKU 4 pricing as-is**. €499-2999/mo is well-anchored vs enterprise-only competitors. This is likely the **real revenue driver** (€18.5k MRR target in the draft plan), not the API SKUs.
2. **Document the price research** (this file) and link it from `product_offerings.md` so future pricing decisions have a baseline.
3. **Flag the gap in SKU 1-3 pricing** — user must consciously choose between premium positioning (requires strong CLV proof) or market alignment (requires lowering prices).

### [HIPOTEZA] Actions to validate in P6.0

4. **Rethink SKU 1 Basic** — either reposition as "value bets, not calls" (€49 for 200 bets) or accept €99 only with a strong CLV proof on the landing page.
5. **Reduce SKU 2 Professional from €199 to €149/mo** — closes the gap to Sportmonks Growth while keeping the multi-sport premium.
6. **Verify what "predictions" competitors ship** — specifically API-Football, Sportmonks, SportRadar — before committing to SKU 3 pricing.

### [RYZYKO] Actions to de-risk

7. **Never launch SKU 1-3 without a free trial**. Every major competitor has a free tier (API-Football, The Odds API, Sportmonks all give free starter credits). A SportsLab API SKU without a free tier in this market = 0 signups.
8. **CLV receipts on landing page** — start tracking closing-line value **now** (well before P6) on every paper-traded bet, so by launch time SportsLab has 6-12 months of public CLV history as social proof. No CLV history = no premium pricing power for SKU 1.

### [DO SPRAWDZENIA] Open questions

- Is the €656k ARR target (from `product_offerings.md`) achievable if SKU 1-3 prices drop 30-50% to match market? (Napkin math: ~€45k MRR instead of €55k — still viable for break-even >€30k.)
- Are there enterprise buyers for SKU 6 (Custom Research) who would justify the €5-50k engagements? Market research on Polish and European football clubs needed.
- Statsbomb/Hudl acquired Statsbomb — is their mid-tier offering (if any) now priced more aggressively? Check quarterly.

---

## References

- [API-Football pricing page](https://www.api-football.com/pricing) (fetched 2026-04-05)
- [The Odds API pricing page](https://the-odds-api.com/#get-access) (fetched 2026-04-05)
- [Sportmonks plans & pricing](https://www.sportmonks.com/football-api/plans-pricing/) (via search, 2026-04-05)
- [Sportmonks Football API landing](https://www.sportmonks.com/football-api/) (fetched 2026-04-05)
- [Hudl Statsbomb product page](https://www.hudl.com/products/statsbomb) (fetched 2026-04-05, pricing enterprise-only)
- [Statsbomb acquisition by Hudl](https://worldsoccerdaily.com/news/statsbomb-acquired-by-hudl-after-11-years-as-a-soccer-blog/) (context)
- [API-Football vs Sportmonks comparison](https://www.best-footballdata-api.com/api-football-vs-sportmonks/) (context)
- Source file being validated: `ideas/phase_6_product_app/product_offerings.md`
- Related audit: `docs/tech_debt_audit.md` (P0.19 — what we can actually deliver with current codebase)
