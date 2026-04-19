# SportsLab — Landing Page Copy

> **Status:** Ready for Lovable (A-37)
> **Audience:** B2B prospects who understand value betting — tipsters, ML-literate hobbyists, small analytical syndicates
> **Language:** English (international reach via Reddit r/sportsbook, Twitter/X, Discord)
> **Tone (per `ideas/vision.md` + `docs/alfa/panel_and_pricing_spec_summary.md`):** data-forward, transparent, humble, no hype, no gambling aesthetics
> **Consumed by:** TASK-A-37 (Lovable landing build), TASK-A-36 (marketing graphics)
> **Last updated:** 2026-04-19

---

## Copy guide (one-liner reminders for Lovable)

- Per `vision.md`: no hype, no "guaranteed wins", no gambling imagery.
- Per `panel_spec`: hero metric is **CLV**, not ROI, not win rate.
- Always show method before promise: "we calibrate probabilities" beats "we win".
- Humble framing: "edge is small but measurable" is better than "dominant edge".

---

## 1. Meta

- **Page title:** SportsLab — Calibrated football predictions with verifiable CLV
- **OG title:** SportsLab — ML-driven value bets with transparent track record
- **OG description:** Calibrated probabilities and portfolio-Kelly stakes across 14 European football leagues. We measure edge by Closing Line Value, not marketing claims. (160 chars)
- **Meta description:** Machine learning predictions for 14 European football leagues with calibrated probabilities, portfolio Kelly sizing, and a public CLV-based track record. Free alpha.
- **Keywords:** value betting, sports analytics, ML predictions, CLV tracking, football model, calibrated probabilities, Kelly criterion, Closing Line Value
- **Canonical URL:** https://sportslab.xxx
- **Theme color:** `#0B0D14` (dark)

*Design note: favicon is SL monogram, green on dark (see A-36).*

---

## 2. Hero

- **Eyebrow (small pill above headline):** Invite-only alpha · Free during 2026
- **Headline:** Football predictions measured by Closing Line Value, not marketing.
- **Subheadline:** We publish calibrated probabilities, fractional-Kelly stakes, and every result — wins and losses — across 14 European leagues.
- **Primary CTA:** Join alpha
- **Secondary CTA:** View methodology
- **Trust microcopy (below CTA row):** 14 leagues · 935 features · ECE ≤ 0.05 · CLV tracked weekly
- **Hero image placement note:** Dark abstract data viz, green/blue accents, no footballs, no dice. Reference A-36 hero asset (1920×1080). Place right-of-headline on desktop, behind on mobile with 70% overlay.

*Design note: H1 in Inter 56/64, subheadline Inter 20/28 muted. Primary CTA filled brand, secondary ghost with scroll-to-methodology anchor.*

---

## 3. How It Works

**Section headline:** Three stages, one bet slip.
**Section subcopy:** What happens between kickoff odds and the message we send you.

1. **Data** — Every morning we ingest results, odds movements, xG, lineups, and form from 14 European leagues across multiple sources, deduplicated and timestamped against kickoff.
2. **Model** — A LightGBM + XGBoost ensemble runs on 935 engineered features, then temperature and isotonic calibration align predicted probabilities with reality (target ECE ≤ 0.05).
3. **Bet Slip** — You receive a daily Telegram message with matches, model probabilities, best available odds, fractional-Kelly stakes, and a confidence tier — or no picks when no edge is detected.

*Design note: three-column grid on desktop, stacked on mobile. Each step gets a 120×120 icon from A-36 (features / calibration / slip). Number badges (01/02/03) in brand color.*

---

## 4. Methodology

**Section headline:** The four decisions that make this different.
**Section subcopy:** Not "proprietary AI". Four deliberate choices you can check.

### Card 1 — 935 Features

**Anchor metric:** 935 engineered features per match
**Body:** Rolling xG differentials, odds-movement deltas, lineup strength, rest days, weather, head-to-head shape, league-relative form. Every feature is derived from raw data with no leakage: training uses only information available at kickoff.
**Footnote link:** See feature catalog in methodology page

### Card 2 — Calibrated Probabilities

**Anchor metric:** ECE ≤ 0.05 (rolling 30 days)
**Body:** Raw model outputs lie. A "70%" prediction that wins 55% of the time loses you money even if it feels accurate. We apply temperature scaling and isotonic regression so that when we say 70%, it means 70% over the long run. Calibration is re-checked per league, per week.
**Footnote link:** What is Expected Calibration Error?

### Card 3 — Portfolio Kelly

**Anchor metric:** Fractional Kelly, 25% of full, capped at 3% per match
**Body:** Full Kelly is mathematically optimal and practically ruinous — a single bad calibration week compounds into a 40% drawdown. We use 25% Kelly, shrunk further by per-market ECE, with per-round exposure caps. You survive the variance that theoretical models ignore.
**Footnote link:** Why not full Kelly?

### Card 4 — Closing Line Value

**Anchor metric:** CLV ≥ 0 vs Pinnacle closing odds
**Body:** Short-term ROI is noise. The sharp-money test is whether your picks beat the closing line at a low-margin book like Pinnacle — if they do, you have real edge, even in a losing week. We publish rolling 30-day CLV per league. It is the only number you can trust before 500+ bets accumulate.
**Footnote link:** CLV vs ROI — why we lead with CLV

*Design note: 2×2 grid desktop, vertical stack mobile. Each card is a `--c-surface` panel with 1px `--c-border`, anchor metric in JetBrains Mono on top-right. Icons from A-36 (120×120) top-left.*

---

## 5. Coverage

**Section headline:** 14 leagues, picked for liquidity and data quality.
**Section subcopy:** We cover the leagues where market odds are sharp enough to be a credible opponent and data is complete enough for honest features. Expansion happens when data quality — not ambition — justifies it.

**Tier 1 — Top-5 (full xG + tactical stats)**
- England — Premier League
- Spain — La Liga
- Germany — Bundesliga
- Italy — Serie A
- France — Ligue 1

**Tier 2 — Selected European leagues (basic stats + odds)**
- England — Championship
- Netherlands — Eredivisie
- Germany — 2. Bundesliga
- Italy — Serie B
- Portugal — Primeira Liga
- Belgium — Jupiler Pro League
- Turkey — Süper Lig
- Greece — Super League
- Scotland — Premiership

**Footer note:** Coverage as of 2026-04. Second divisions of Spain and France under evaluation. We will not add a league until we have three full seasons of clean data.

*Design note: 14-cell grid with country flag + league name. Tier 1 highlighted with subtle `--c-brand` accent border. On mobile: 2-column grid with tier pills.*

---

## 6. Alpha Access

**Section headline:** Free alpha. Invite-only. Small on purpose.

**Intro paragraph:**
The SportsLab alpha is a private Telegram feed with daily bet slips across 14 football leagues, weekly performance reports, and a public track record. It runs free through 2026 because we do not believe in charging for unproven predictions. What you get in return is early access and a direct line to the founder. What you do not get is financial advice, guaranteed profit, or any claim that past calibration predicts the next three months. Betting carries financial risk. Bankroll what you can lose.

**Form title:** Request an invite

**Fields:**

| Field | Type | Label | Placeholder | Required |
|---|---|---|---|---|
| email | email | Email | you@domain.com | Yes |
| telegram | text | Telegram handle | @your_handle — speeds up onboarding | No |
| experience | dropdown | Betting experience | Select one | Yes |
| bankroll | dropdown | Bankroll tier | Select one | Yes |
| source | text | How did you hear about us? | Reddit, Twitter, friend… | No |

**Experience dropdown options:**
- Beginner — I place casual bets, no tracking
- Intermediate — I track ROI, some value-betting concepts
- Experienced — I track CLV, manage bankroll by Kelly
- Professional — I run a syndicate or tipster service

**Bankroll dropdown options:**
- Under 1,000 EUR
- 1,000 – 5,000 EUR
- 5,000 – 25,000 EUR
- 25,000 EUR +

**Submit button label:** Request invite

**GDPR microcopy below button:** We store your email and submission metadata to evaluate alpha fit. No marketing emails without opt-in. Delete anytime: hello@sportslab.xxx.

**Post-submit confirmation (toast or in-place swap):**
> **Request received.**
> We review invites manually and reply within 3 working days. If you are a fit, we send a Telegram invite link and a short onboarding note. If the alpha is full, we will place you on the early-adopter waitlist for the paid tier (launching after the alpha ends).

*Design note: form is left column, intro paragraph right column on desktop. Stacked on mobile. Submit button full-width on mobile, fixed-width desktop. Inline validation, not blocking.*

---

## 7. FAQ

**Section headline:** What we get asked before people sign up.
**Section subcopy:** Short, honest answers. Longer explanations live in the methodology docs.

### 1. Is this gambling advice?
No. SportsLab publishes statistical predictions for informational purposes only. We do not recommend individual bets for individual circumstances, we do not know your bankroll or jurisdiction, and we are not licensed financial or gambling advisors. Treat every output as a data point, not a recommendation. Betting carries financial risk and can become addictive — see responsible gambling resources in the footer.

### 2. How do I know the track record is real?
Every bet slip we publish is timestamped before kickoff and logged to a public record. We publish wins, losses, bad streaks, and calibration drift — not only the good weeks. CLV is computed against Pinnacle closing odds, a low-margin book that sharp bettors use as the benchmark. If our CLV goes negative, you will see it before we do.

### 3. What happens after the alpha ends?
Alpha users get a permanent early-adopter discount (50% off the launch price) and priority access to new features. The alpha is expected to run 2–3 months; at the end we move to a paid tier (€19/month early adopter, €49/€199 at full launch). Nothing auto-converts to paid — you explicitly opt in.

### 4. How much bankroll should I start with?
Enough to absorb a 30% drawdown without emotional or financial damage. In practice, 1,000 EUR is a realistic minimum to make fractional-Kelly stakes meaningful at typical odds. Below that, betting units become too small to matter and psychology starts driving decisions instead of the model. This is an opinion, not advice.

### 5. Which bookmakers are recommended?
We do not partner with any bookmaker and do not take affiliate money, on purpose. For the model to work you need access to sharp books — Pinnacle if available in your jurisdiction, otherwise the lowest-margin book you can open and keep open. Soft books will limit accounts quickly if you bet value. That is a feature of the business model, not our platform.

### 6. What's the refund policy?
The alpha is free, so the policy is moot during 2026. Once paid tiers launch, monthly subscriptions can be cancelled at any time with access through the end of the paid period. We do not prorate refunds for partial months. Annual plans are non-refundable after 14 days — if you are not sure, start monthly.

### 7. Why should I trust your model over a tipster with 85% win rate?
Short answer: because 85% win rate is meaningless without knowing the odds it was achieved at. 85% at 1.10 odds loses money. 40% at 3.00 odds makes money. The correct metric is Closing Line Value — whether your picks beat the market consensus at kickoff. We publish that. Most tipsters cannot because their edge disappears when measured honestly.

### 8. What if I lose money?
Then we have failed to deliver, and you should leave. We do not claim to be profitable in every week, month, or even every quarter — variance is real and the edge is small. If cumulative CLV goes negative and stays there for 60+ days, that is a signal the model has stopped working and we will say so publicly. Your bankroll is yours to protect; our job is to be honest about what the data shows.

*Design note: collapsible accordion on desktop and mobile. First two questions open by default. Question in Inter 18 semibold, answer in Inter 16 regular. `--c-border` between items.*

---

## 8. Footer

**Columns (desktop, stacked on mobile):**

**Column 1 — Brand**
- SportsLab logo (SL monogram, green on dark)
- Tagline: Calibrated predictions. Verifiable CLV. No hype.
- Copyright: © 2026 SportsLab. All rights reserved.

**Column 2 — Product**
- Methodology
- Track record
- Coverage
- Alpha access

**Column 3 — Company**
- About
- Contact: hello@sportslab.xxx
- Privacy policy
- Terms of service

**Column 4 — Responsible play**
- 18+ only — betting is restricted to adults
- BeGambleAware.org (external link)
- GambleAware.org (external link — UK)
- Hazardowy.pl (external link — PL)

**Legal disclaimer (full-width strip below columns, muted):**
> SportsLab provides statistical predictions and analytics for informational purposes only. Nothing on this site constitutes financial, legal, or gambling advice. Past performance does not guarantee future results. Betting carries financial risk and can be addictive. Users are responsible for complying with the laws of their own jurisdiction. SportsLab does not accept bets and is not a licensed bookmaker. 18+ only.

*Design note: footer background `--c-bg`, slightly darker than section surfaces. Responsible-play column in `--c-warn` accent on the 18+ pill. External links open in new tab.*

---

## Checklist for Lovable handoff (A-37)

- [ ] Meta tags wired to `<head>` (title, OG, description, keywords)
- [ ] Hero image placement aligned with A-36 asset sizes
- [ ] Primary CTA scrolls to Alpha Access form (smooth scroll, 60px offset)
- [ ] Secondary CTA scrolls to Methodology section
- [ ] All 14 leagues listed with country prefix + tier indicator
- [ ] FAQ accordion accessible (aria-expanded, keyboard nav)
- [ ] Form validates email format client-side, submits to Tally.so or native endpoint
- [ ] Post-submit confirmation replaces form in-place (no redirect)
- [ ] Responsible-play links open in new tab with `rel="noopener"`
- [ ] Disclaimer strip visible on every page, not only homepage
