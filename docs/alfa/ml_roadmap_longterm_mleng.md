# ML Roadmap — Alpha → Beta → V1 → V2 → V3 (ML Engineer Perspective)

> **Status:** Draft v1 · 2026-04-22
> **Author:** mleng (Senior ML Engineer persona)
> **Scope:** Strategic multi-quarter roadmap for SportsLab ML product, assuming `docs/alfa/ml_experiments_alpha.md` as baseline (Alpha = shipped)
> **Audience:** Founder (Lead), DrMat (math authority), future team members joining in V1+
> **Supersedes:** None — extends `ml_experiments_alpha.md` which covers Alpha only
> **Companion docs:** `ideas/phase_2_new_features/`, `ideas/phase_3_more_leagues/`, `ideas/phase_4_more_sports/`, `ideas/ip_moat.md`, `ideas/solo_founder_roadmap.md`

---

## Executive Summary — 10 phase bullets

1. **Alpha (now, month 0-2):** Single LightGBM on 14 football leagues, 1X2 + OU_2.5 + BTTS (week 3), Dirichlet/temperature calibration, fractional Kelly α=0.25, bi-weekly retrain. Single Pi 4GB + Dev PC. Target: CLV ≥ 0 on 500 bets within 90 days. [**SHIPPED** per `ml_experiments_alpha.md`]
2. **Alpha Hardening (month 2-4):** Ship BTTS validated, wire PSI feature drift, enable 10× bagging for predictive variance, add Pinnacle closing odds pipeline as gold standard CLV source. No model architecture change — only measurement infra matures.
3. **Beta (month 4-10):** Ensemble (LGBM + XGBoost + CatBoost) with LogReg stacking meta-learner, per-league calibration gated by n_league≥500 per market, Bayesian posterior Kelly (replaces ECE-dampening), first markets expansion (AH 0/-0.5/-1, Double Chance, DNB, OU_1.5/3.5). Telegram+ API feed.
4. **Beta→V1 transition (month 10-14):** Dixon-Coles goals model (enables Correct Score, all OU lines, AH with goal supremacy), auto-retraining triggered by drift, 10 football leagues in production (adds Eredivisie, Championship, Primeira, MLS, Brasileirão per `ideas/phase_3_more_leagues/`).
5. **V1 (month 14-22):** Multi-sport abstract framework in production. Tennis (Bradley-Terry per surface + LGBM hybrid), basketball (NBA with pace-adjusted + player availability), hockey (NHL with goalie-centric). Hierarchical Bayesian calibration (shared prior across leagues, market-specific). First paid B2B customer.
6. **V1→V2 transition (month 22-28):** Graph neural networks for team representations (team2vec via GNN on passing networks / H2H graphs), social sentiment features (Twitter/Reddit NLP), injury news NLP (Transfermarkt + Sofascore), Portfolio Kelly with Ledoit-Wolf covariance shrinkage.
7. **V2 (month 28-36):** Live/in-play modeling for top-5 football leagues (conditional Dixon-Coles with score state + time remaining), micro-markets (corners, cards), neural network calibration (MLP on logit + meta-features). Feature store (Feast or custom Postgres-backed). Dedicated GPU training box (A100 rental on-demand).
8. **V2→V3 transition (month 36-42):** Transformer-based sequence models for match history representations (last N matches as tokens), online calibration (continuous Bayesian update), multi-user bankroll optimization (portfolio theory with market impact modeling for paid tier scale).
9. **V3 (month 42-54):** Full Bloomberg-for-sports stack. Player props (goalscorer, shots, passes), tactical NLP features (coach interviews), cross-market arbitrage signals, Kubernetes multi-region deploy if customer base requires <500ms latency globally. Research moat: whitepaper published on arXiv, 1-2 open-source contributions, academic collaboration with 1 UK/US quant group.
10. **V3+ (month 54+):** Exit-ready IP portfolio: patent applications on CLV methodology + hierarchical calibration, enterprise API layer for Stripe/Flutter/DraftKings-scale acquirers, research arm producing 2 papers/year as credibility moat.

---

## Timeline — Month-by-month to V3

> **Assumption:** Solo founder + Claude Code model through V1. First external hire (contractor/fractional) at V1 (month 14-22) when scale demands it. Actual hire timing depends on revenue.

| Month | Phase | Key ML deliverable | Gate / KPI target |
|-------|-------|--------------------|-------------------|
| 0 | Alpha | LGBM 1X2 + OU shipped | CLV tracked, 50+ bets settled |
| 1 | Alpha | BTTS validated, added to prod | ECE < 0.05 on BTTS, 100+ bets |
| 2 | Alpha Hardening | Pinnacle closing odds live | 200+ bets with CLV reference |
| 3 | Alpha Hardening | 10× bagging in training | Predictive variance logged, no prod impact yet |
| 4 | Alpha Hardening | PSI feature drift alerts live | 1 false-positive/month ceiling |
| 5 | Beta Kickoff | Ensemble (LGB+XGB+CB) A/B | Challenger matches champion on log-loss |
| 6 | Beta | Bayesian Kelly posterior | +5-15% growth vs ECE-dampen in backtest |
| 7 | Beta | Per-league calibration enabled | ECE drops per top-5 league to ≤ 0.03 |
| 8 | Beta | Stacking meta-learner live | Δlog-loss ≥ 0.001 vs best single model |
| 9 | Beta | Markets: AH 0/-0.5, Double Chance, DNB | +3 markets in production, each ECE ≤ 0.05 |
| 10 | Beta | OU 1.5, OU 3.5, HT BTTS added | +3 more markets; total 8 |
| 11 | Beta→V1 | Dixon-Coles Bayesian goals model | Bites OU ladder; Correct Score ECE ≤ 0.06 |
| 12 | Beta→V1 | Auto-retraining on drift trigger | First auto-retrain in the wild |
| 13 | Beta→V1 | Eredivisie + Championship live | +2 leagues; feature parity validated |
| 14 | V1 | MLS + Primeira + Brasileirão live | 10 football leagues total |
| 15 | V1 | Abstract sport framework scaffolded | Contract tests green on stub sport |
| 16 | V1 | Tennis (ATP/WTA) live | CLV ≥ 0 on 100+ tennis bets |
| 17 | V1 | Hierarchical Bayesian calibration | Shared prior produces calibration on n_league < 500 |
| 18 | V1 | Basketball (NBA) live | CLV ≥ 0 on 200+ NBA bets |
| 19 | V1 | First B2B pilot customer onboarded | Value feed API ships with auth |
| 20 | V1 | Hockey (NHL) live | 3 sports framework proven |
| 21 | V1 | Portfolio Kelly with Ledoit-Wolf | Covariance-aware sizing in production |
| 22 | V1→V2 | Social sentiment features (Reddit/Twitter) | +0.001 log-loss on 1X2 in top-5 |
| 23 | V1→V2 | Injury news NLP feature | Validated on rounds with known absences |
| 24 | V1→V2 | GNN team embeddings (team2vec) prototype | Shadow prediction mode |
| 25 | V2 | GNN embeddings promoted to production | Challenger beats baseline on stability |
| 26 | V2 | Neural net calibration (MLP head) | ECE parity or better vs Bayesian hierarchical |
| 27 | V2 | Feature store (Feast) in prod | Feature serving <50ms p95 |
| 28 | V2 | Live/in-play model shadow mode | Conditional DC validates on historical live odds |
| 30 | V2 | In-play 1X2 + OU live on top-5 | Bet latency < 3s from odds update |
| 32 | V2 | Corners + Cards micro-markets | Per-market ROI ≥ 3% on 500 bets |
| 34 | V2 | Dedicated GPU box rental baseline | <€150/mo on-demand |
| 36 | V2→V3 | Transformer match history encoder prototype | Shadow mode validation |
| 40 | V3 | Transformer encoder in production | Replaces or augments rolling features |
| 42 | V3 | Online calibration (streaming Bayesian) | ECE updates continuously, no batch retrain needed |
| 44 | V3 | Player props live (goalscorer for top-5) | Pilot market, ROI ≥ 2% after 1000 bets |
| 48 | V3 | whitepaper on arXiv | IP credibility boost |
| 50 | V3 | 1 open-source release (calibration library) | Marketing + moat |
| 54 | V3 | Kubernetes multi-region deploy (if needed) | Only if 100+ enterprise customers justify |

**Total span**: ~54 months (4.5 years) from Alpha to V3. **[HIPOTEZA]**: realistic only if founder survives revenue ramp past month 14; if not, V1+ telescopes into a longer timeline or never happens.

---

## Alpha → Beta transition (month 0-10)

### Alpha exit criteria (gate to Beta)

Not calendar-driven. Gate is met when ALL of these are simultaneously true for **30 consecutive days**:

1. **CLV ≥ 0** point estimate on last 200 placed bets (not paper trading — real money)
2. **ECE ≤ 0.05** per-market on rolling 60-day window, across all 14 leagues × 3 markets
3. **Zero rollbacks** triggered in last 30 days (no auto-rollback events per mleng.md pattern 2)
4. **10× bagging infra** exercised in training pipeline (even if not yet promoted to production scoring)
5. **Pinnacle closing odds** pipeline stable for ≥60 days, coverage ≥85% of placed bets
6. **First 3 beta users** either retained (using the Telegram feed) or churned with documented reasons

**If any fails:** Stay in Alpha Hardening. Don't start Beta work. This is the biggest project-killing trap — starting Beta architecture while Alpha baseline is still unstable means you never get clean signal on what's actually working.

### Alpha Hardening sub-phase (month 2-4)

Not new modeling — **measurement infrastructure that Alpha deferred**. Three workstreams in parallel:

#### AH-1: BTTS ship (target month 2.5)

- **Target:** BTTS model in production, validated against same gates as 1X2 and OU_2.5
- **Data:** Already have `btts` target in `packages/ml-in-sports/src/ml_in_sports/processing/targets.py`
- **Model:** Same LGBM binary config as OU_2.5, separate calibrator
- **Calibration:** Beta (n_val ≥ 500) or Platt fallback
- **Gate to promote:** ECE ≤ 0.04 (tighter than 0.05 because binary), CLV ≥ 0 on walk-forward, SHAP top-10 overlap ≥ 70% with OU (both are score-distribution-derived)

**Failure fallbacks (AH-1):**
- **Target metric:** ECE ≤ 0.04, CLV ≥ 0 on 100+ walk-forward bets
- **Success:** Ship BTTS, mark Alpha 3-market complete
- **Partial success (ECE 0.04-0.06):** Ship BTTS with tighter-than-default Kelly cap (0.015 per-bet instead of 0.03), revisit at month 4
- **Failure (ECE > 0.06 or CLV < -2%):**
  1. Diagnose: is BTTS market asymmetrically priced by books (bookmaker margin higher on BTTS)? Compare margins against 1X2 on same fixtures.
  2. Hipoteza: features may need goalscorer-level granularity that current rolling features don't capture. Sub-experiment: add xG-weighted rolling features specific to "both teams scoring" events.
  3. Pivot: skip BTTS entirely for Beta, focus engineering on Dixon-Coles goals model which covers BTTS derivatively in month 11.
- **Bailout criteria:** 4 weeks of work without ECE ≤ 0.06 → cut BTTS from Alpha scope, document in MLflow, move on. Never defend a market that doesn't calibrate — it burns credibility when live CLV goes negative.

#### AH-2: Pinnacle closing odds pipeline (target month 2-3)

- **Target:** Daily pull of Pinnacle closing odds for every placed bet, joined to bet log for CLV computation
- **Source options (per `ideas/solo_founder_roadmap.md`):**
  1. `football-data.co.uk` — historical CSV, no live
  2. The Odds API free tier (500 calls/month) — live but rate-limited
  3. Betfair Exchange API — alternative sharp market reference
  4. Oddschecker API if available
- **Architecture:** Scraper (DataEng concern but solo means ML owns it) → Postgres `closing_odds` table → `clv_tracking` materialized view
- **Gate:** ≥85% coverage of placed bets get closing odds attached within 48h of match start

**Failure fallbacks (AH-2):**
- **Target:** 85% coverage on placed bets
- **Success:** Pipeline stable, CLV is trustworthy metric
- **Partial (50-85%):** Use only the covered subset for CLV reporting, disclose coverage % on landing page (per drmat §7.1 honesty rules)
- **Failure (<50%):**
  1. Diagnose: which leagues lose coverage? Maybe `football-data.co.uk` doesn't cover Tier-2 leagues on same-day schedule.
  2. Pivot: use **Betfair Exchange closing** as substitute — it's also a sharp market reference. CLV vs Betfair is industry-accepted (e.g., Joseph Buchdahl methodology).
  3. Secondary pivot: compute CLV against our own **opening odds** as weak proxy. **[RYZYKO]**: opening-odds CLV systematically overstates edge because opening is less efficient. Label clearly in UI.
- **Bailout criteria:** 6 weeks of zero progress on Pinnacle-equivalent closing → switch to self-reported win rate + ECE as hero metrics on landing, defer CLV claim until month 12+.

#### AH-3: 10× bagging + predictive variance infrastructure (target month 3-4)

- **Target:** Training pipeline can produce 10-seed bagged ensemble with `predictive_variance` logged per prediction. NOT yet promoted to scoring — just captured in MLflow.
- **Why now:** DrMat's Bayesian Kelly (§4.3 in `ml_experiments_draft_drmat.md`) requires predictive variance. We deferred it in Alpha due to 22,680-run grid explosion (per Alpha §2.1). But we need the infra built before Beta wants to use it.
- **Implementation:** `train_bagged_ensemble(n_seeds=10)` produces `list[LGBMClassifier]`. At inference time, compute mean p and variance p across the 10.
- **Cost estimate:** 10× training time → ~5h per full training cycle on Dev PC (currently ~30min). Bi-weekly retrain → 2×/month × 5h = 10h/month of Dev PC burn. Acceptable.

**Failure fallbacks (AH-3):**
- **Target:** Bagging pipeline runs in training, logs variance per fold
- **Success:** Ready for Bayesian Kelly experiment in Beta month 5
- **Partial (runs but variance looks bogus):** Variance should correlate with known-hard fixtures (tight matchups, early-season games). If flat across all predictions → bagging isn't giving real diversity. Fix: increase feature subsampling, reduce n_estimators, use bigger seed spread.
- **Failure (training OOMs on Dev PC or takes >12h):**
  1. Diagnose: memory footprint per LGBM ~500MB × 10 = 5GB. Dev PC should handle it.
  2. Pivot: reduce to 5× bagging. Still gives ~√2 better variance estimate than single model.
  3. Secondary pivot: rent Hetzner CX32 for training only (€20/mo). Brings V1-tier training infra forward.
- **Bailout criteria:** If after 4 weeks bagging predictive variance has no correlation with prediction error on holdout → bagging isn't helping on our data. Defer Bayesian Kelly permanently and stay on ECE-dampening. Flag to DrMat; expect pushback but numbers win.

#### AH-4: PSI feature drift monitoring (target month 4)

- **Target:** Daily job computes PSI (Population Stability Index) on top-50 SHAP features, alerts if any > 0.15 for 3 consecutive days
- **Coverage:** All 14 leagues × top-50 features = 700 PSI calcs/day. Cheap (~30s total).
- **Alerts:** Warning to founder Telegram (don't rollback — PSI drift ≠ model broken, just distribution shift worth investigating)
- **Why now:** Alpha listed PSI as "currently TBD" in §7 monitoring table. Beta ensemble + per-league calibration will have way more failure surface area — need drift visibility before adding complexity.

**Failure fallbacks (AH-4):**
- **Target:** PSI alerts fire on known regime changes (COVID-era, international break runs) in backtest validation
- **Success:** Monitoring live, founder sees weekly drift summary
- **Partial (PSI fires too noisily):** Raise threshold from 0.15 to 0.25, or require 5-day persistence instead of 3. Alert fatigue is worse than missed drift.
- **Failure (PSI never fires even in obvious regime changes):** Bug in feature aggregation or binning. Rewrite PSI implementation using `evidently` library as reference. Don't build custom if library exists.
- **Bailout criteria:** 3 weeks, PSI either spams or misses. Cut to simpler KS-test based drift on 10 most critical features. Less theoretically clean but operationally simpler.

### Alpha → Beta transition summary

```
MONTH 0  1  2  3  4   5   6   7   8   9   10
ALPHA    ━━━━━━━━━━━━━
AH-1            ━━━
AH-2         ━━━━━
AH-3            ━━━━
AH-4               ━━━
BETA-1                  ━━━━━━━━━━━━━━━━━━━━━━
```

**Decision gate at month 4:** If all AH-1..AH-4 green + Alpha CLV ≥ 0 on 200 bets → start Beta-1 (ensemble architecture). Otherwise extend hardening.

---

## Beta (month 4-10) — Ensemble, calibration depth, market expansion

### Beta in one sentence

**Transform a working single model into a robust production ensemble with per-league calibration, Bayesian Kelly, and 8 markets — all measured against the Alpha baseline that MUST remain deployable as rollback.**

### Modele

**Architecture: 3-way ensemble + stacking meta-learner**

```yaml
ensemble:
  base_models:
    - lightgbm_v2: seed=42, tuned per-league  # Alpha champion
    - xgboost_v1:  seed=42, depth=7, eta=0.03
    - catboost_v1: seed=42, cat_features native, depth=8
  meta_learner:
    type: logistic_regression  # NOT stacked trees — overfitting risk on OOF
    l2: 0.5
    fit_on: oof_predictions_from_walk_forward
  bagging: 10  # per base model
  serving_mode: average  # weighted-mean on calibrated p
```

**Why LGB + XGB + CatBoost:**
- LGBM: alpha champion, leaf-wise growth, fast inference on Pi
- XGBoost: different split strategy (level-wise), different regularization behavior, diversifies error modes
- CatBoost: native categorical handling (team names, leagues, venue), different ordering-boost mechanism
- **NOT TabPFN**: per Alpha §2.1 and `ideas/phase_2_new_features/research_backlog.md#RB-01`, TabPFN is systematically overconfident on our data. Temperature scaling helps but doesn't close the gap vs tree ensembles.

**Stacking meta-learner:** LogReg on OOF predictions. **[PEWNE]**: stacking with tree meta-learners overfits on OOF because the OOF predictions are already low-variance. LogReg is the right choice mathematically. DrMat will agree here.

### Markety

Beta adds 5 new markets on top of Alpha's 3:

| Market | Month | Calibration | Risk flag |
|--------|-------|-------------|-----------|
| AH 0 (Draw-No-Bet equivalent) | 9 | Beta | Low — same info as 1X2 subset |
| AH -0.5 | 9 | Beta | Medium — goal supremacy |
| AH -1 | 9 | Beta | Medium — needs Dixon-Coles for proper handicap |
| Double Chance (1X, X2, 12) | 9 | Derived from 1X2 (sum calibrated p) | Low |
| OU 1.5 | 10 | Beta | Medium — skewed market, needs goals model |
| OU 3.5 | 10 | Beta | Medium — same |
| BTTS HT | 10 | Beta | High — low-base-rate, hard to calibrate |
| HT 1X2 | 10 | Dirichlet | High — 45min signal weaker than 90min |

**Total Beta markets in production:** Alpha 3 + Beta 5-7 (pick top-performing 5 of these 7 based on AH-2 CLV data) = **8 markets**.

**Order of rollout:** AH 0 and Double Chance are near-free (derivable from 1X2). AH -0.5 and AH -1 need goal supremacy which the Dixon-Coles model in Beta→V1 transition handles properly — so in month 9 ship them with the simpler "LGBM on total goals" proxy, upgrade in month 11.

### Features

No new feature categories in Beta — **stabilize the 935-feature pool from Alpha**. What changes:

- **Feature selection hardens:** SHAP top-quantile-0.8 → top-quantile-0.9, dropping weak features. Target: ~150 features (down from 200).
- **Per-league feature importance audit:** Some features may be strong in Premier League and noise in Bundesliga 2. Audit shows which features to weight down per league.
- **Form normalization across leagues:** A team with 5-match form of +1.2 xG differential means different things in Premier League vs Championship. Add `form_zscore_within_league` feature.

**Deferred to V1:** graph embeddings, team2vec, transformer encoders, social sentiment.

### Calibration

**Per-league calibration (gated by n_league ≥ 500 per market).**

Flow:
1. Train pool-wide ensemble (shared across leagues) — current default
2. If league has ≥500 bets on that market: fit per-league Dirichlet/Beta calibrator on that league's OOF predictions
3. Select best calibrator per (market × league) using validation ACE
4. Fall back to pool calibration for leagues with n < 500

**Target:** ECE drops from ~0.04 (pool) to ~0.025 on top-5 leagues.

### Risk / Kelly

**Bayesian posterior Kelly (replaces ECE-dampening).**

```python
# predictive variance from 10× bagging
sigma2 = np.var([model.predict_proba(X)[:, c] for model in bagged_models], axis=0)
# posterior Kelly: shrinks edge by variance
kelly_fraction = (edge - alpha * sigma2) / (odds - 1)
kelly_fraction = np.clip(kelly_fraction * 0.25, 0, 0.03)
```

**[PEWNE]** (DrMat §4.3): mathematically principled. **[RYZYKO]** (mleng): +5-15% growth projection depends on variance being correctly estimated — if bagging variance is biased low, we bet too big.

**Validation experiment (Beta month 6):** Run Bayesian Kelly and ECE-dampening in parallel on live bets for 4 weeks (shadow mode, logged not acted on). Compare:
- Mean stake per bet
- Variance of stakes
- Hypothetical bankroll if each strategy were acted on
- Correlation between predictive variance and actual error

Only promote Bayesian Kelly if on 200+ bets it shows ≥3% growth advantage with tighter drawdown.

### Infrastructure (Beta)

**Shift from "Pi + Dev PC" to "Pi + Hetzner CX32 training box":**

- Training moves to Hetzner CX32 (€20/mo, 4 vCPU, 8GB RAM, ephemeral)
- Pi remains scoring/serving only (no training)
- MLflow stays local on Dev PC for artifact registry
- New: **atomic deploy script** per mleng.md pattern 4, now scp'ing from Hetzner to Pi instead of from Dev PC

**Total infra cost at Beta exit:** ~€25-30/mo (Pi colo free, Hetzner €20, Dev PC owned, Cloudflare free).

### Monitoring / alerting

Beta adds beyond Alpha:

| Alarm | Condition | Window | Action |
|-------|-----------|--------|--------|
| Ensemble disagreement | top-3 models disagree on argmax > 30% of predictions | 7d | Warning — investigate feature drift |
| Meta-learner weight shift | LogReg coefficients shift > 2σ vs last training | per-retrain | Warning — base model drift |
| Per-league ECE divergence | any league ECE > pool ECE + 0.03 | 14d | Warning — per-league calibrator stale |
| Kelly variance spike | predictive variance median > 2× historical | 7d | Warning — bagged models diverging |

### Cost (Beta)

Monthly, at Beta exit (month 10):
- Hetzner CX32: €20
- Pi 4GB (owned): €0 (one-time cost amortized)
- Internet / electricity: ~€15 (Pi + Dev PC share of household bill)
- Betfair / Odds API / Pinnacle proxy: ~€10 (free tier mostly)
- **Total: ~€45/mo operational**

Bankroll (separate from infra): ~€2,000-3,000 by Beta exit if R3 showed positive CLV, else stays at €1,000.

### Team requirements (Beta)

- Founder: 100% time. No hires.
- Claude Code: primary implementation partner.
- External advisor (ad-hoc): 1-2h/month with a statistician peer to sanity-check Bayesian Kelly math. Could be a Discord/forum relationship, doesn't need to be paid.

**[HIPOTEZA]**: solo through Beta is realistic. First hire trigger is V1 multi-sport framework, not Beta complexity.

### Success KPIs (Beta)

Exit-from-Beta gate:
1. Ensemble beats Alpha LGBM by ≥5% log-loss on last 3 months of live bets (DeLong BH-adjusted p<0.1)
2. ECE ≤ 0.03 on top-5 leagues (tighter than Alpha's 0.05)
3. ≥6 markets in production with ECE ≤ 0.05 and CLV ≥ -1% each
4. Bayesian Kelly either promoted (proven advantage) or formally rejected in MLflow decision log
5. PSI alerting: < 1 false positive/month, caught ≥1 real drift event
6. Auto-rollback triggered 0 times in last 30 days
7. 3 beta users retained AND 1 paying customer OR 5 beta users retained (whichever comes first)

### Failure fallbacks (Beta)

#### Beta experiment: Ensemble (LGB+XGB+CB stacking)

**Target metric:** Δlog-loss ≥ 0.001 vs Alpha LGBM on walk-forward, DeLong BH-adjusted p < 0.1

**Success:** Promote to production month 5, retire Alpha LGBM as champion (keep as rollback)

**Partial success (Δlog-loss 0 to 0.001):**
- Keep Alpha LGBM as champion
- Run ensemble as shadow/challenger for 8 more weeks
- If still flat: ensemble is a wash — likely all three base models are essentially consuming the same signal from 935 features. Feature pool needs diversification (add graph/sequence features earlier — brings V1 work forward).

**Failure (ensemble worse than Alpha):**
1. Diagnose: is the meta-learner overfitting OOF? Check with LeaveOneLeagueOut validation.
2. Hipoteza: stacking on our data doesn't help because base models are too similar in failure modes (all gradient boosters learn similar feature interactions).
3. Pivot A: simple weighted average (grid-search weights on val set) instead of LogReg meta-learner — same diversification benefit, no overfitting risk.
4. Pivot B: drop CatBoost if it's the weak link, run LGB+XGB only. Smaller ensemble, less engineering.
5. Pivot C: train same LGBM on **different feature subsets** (e.g., by feature family: form, odds, weather, lineup) — force diversity.

**Bailout criteria:** 6 weeks ensemble work without Δlog-loss ≥ 0.0005 → abandon ensemble architecture, stay single LGBM. Invest that time in Dixon-Coles goals model (Beta→V1) which opens 5 new markets and is a surer win.

#### Beta experiment: Per-league calibration

**Target metric:** Per-top-5-league ECE improvement from 0.04 (pool) → 0.025 after 500 bets/league

**Success:** Ship per-league calibrators, keep pool as fallback for leagues n<500

**Partial success (ECE drops to 0.025-0.035):** Ship for leagues where improvement is real (likely Premier League, La Liga), keep pool calibration for noisier leagues.

**Failure (ECE unchanged or worse):**
1. Diagnose: is n_league truly 500? Bootstrap CI around ECE shows whether apparent 0.04 vs 0.025 difference is signal or noise.
2. Hipoteza: league effect is already absorbed by cross-league form normalization (from Beta features section). If features are well-normalized, per-league calibration has nothing left to learn.
3. Pivot: try **per-confidence-tier** calibration instead (e.g., bin predictions into low/mid/high confidence, calibrate per bin). Often catches miscalibration that per-group doesn't.
4. Secondary pivot: hierarchical calibration (planned for V1) — brings V1 work forward. Bayesian shared prior across leagues with per-league posteriors.

**Bailout criteria:** >6 weeks of per-league calibration work with no ECE improvement → abandon per-group granularity for Beta, stay pool-based. Invest effort in features (Beta feature selection hardening).

#### Beta experiment: Bayesian posterior Kelly

**Target metric:** ≥3% growth advantage vs ECE-dampen over 200 bets shadow-mode comparison, drawdown tighter by ≥10%

**Success:** Promote Bayesian Kelly to production month 6

**Partial success (growth advantage 0-3%):** Not worth engineering risk. Keep ECE-dampen. Document in MLflow.

**Failure (Bayesian Kelly underperforms ECE-dampen):**
1. Diagnose: is predictive variance calibrated? Compute correlation between variance and error on holdout. If r < 0.3, variance estimates are unreliable → bagging isn't giving real diversity.
2. Hipoteza (DrMat will disagree here, flag for debate): Bayesian Kelly gains disappear because our bagged variance is not a posterior variance in the Bayesian sense — it's just ensemble disagreement, which is different from true parameter uncertainty. 
3. Pivot: try a different variance estimator — e.g., conformal prediction intervals, or quantile regression for lower-bound edge estimates.
4. Secondary pivot: hybrid — use Bayesian Kelly only on "low-confidence" predictions (bottom 20% by max_p), stay on ECE-dampen for high-confidence ones.

**Bailout criteria:** 8 weeks without growth advantage → abandon Bayesian Kelly permanently, add to `docs/negative_results.md` as a documented dead end. This is an expected failure mode in ~30% of Bayesian ensemble projects — don't defend if data says no. **[RYZYKO]**: DrMat will push back; need cleanly documented experiment results to survive that conversation.

#### Beta experiment: Markets expansion (AH, DC, DNB, OU lines)

**Target metric:** Each new market achieves ECE ≤ 0.05 and CLV ≥ -1% on first 100 walk-forward bets

**Success:** Ship 5-7 new markets, total 8 in production

**Partial success (3-4 markets pass):** Ship the 3-4 that pass, log the failures with diagnosis. Don't force products that don't calibrate.

**Failure (only 0-2 markets pass):**
1. Diagnose per market: is the market liquidity low enough that book margin is >5% (vs 2-3% on 1X2)? If so, edge is being taxed away by the vig.
2. Hipoteza: derived markets (Double Chance from 1X2) should work by construction. If they don't, there's a bug in the calibration-renormalization (which Alpha §3 explicitly banned per-class Platt renormalize — maybe we fell into that trap).
3. Pivot: focus on AH -0.5 and AH 0 only (most liquid AH lines), drop -1 and -1.5 until Dixon-Coles handles them.
4. Secondary pivot: skip AH entirely, invest in OU ladder (1.5, 2.5, 3.5) which Dixon-Coles covers naturally.

**Bailout criteria:** If at month 10 we have only 4 markets (Alpha 3 + 1 Beta) → that's acceptable. Don't ship markets that don't calibrate. Focus on Beta→V1 Dixon-Coles which opens 5 markets at once.

---

## Beta → V1 transition (month 10-14) — Dixon-Coles, auto-retrain, 10 leagues

This transition exists because V1 (multi-sport) is a big lift and we need **football to be maximally mature** before diluting attention across sports.

### Dixon-Coles Bayesian goals model (month 11)

**Design (DrMat's territory — I implement his spec):**
- Bayesian Dixon-Coles via PyMC or Stan (variational inference preferred — NUTS too slow)
- Attack + defense strength per team (latent variables with weakly informative priors)
- Time decay per ~1 year half-life
- Output: λ_home, λ_away (expected goals per team) + correlation correction for low-score matches
- Derives: 1X2, AH all lines, OU all lines, Correct Score, BTTS

**Why this unlocks markets:** Currently each market has its own LGBM model. Dixon-Coles gives a **generative goal distribution** that derives ALL goal-based markets from one inference. Massively better data efficiency for niche markets.

**Implementation notes:**
- **[RYZYKO]**: PyMC variational inference on 10 leagues × 20 teams × 10 seasons = 2000 teams-seasons. Could OOM. Plan: season-at-a-time inference with informative priors from previous season.
- **[DO SPRAWDZENIA]**: does VI converge stably across runs? If not, fallback to MAP-only with frequentist Dixon-Coles (Dixon & Coles 1997 original) — less principled but operationally solid.

**Failure fallbacks (Dixon-Coles):**
- **Target:** Beats LGBM baseline on OU 0.5, 1.5, 3.5, 4.5 by Δlog-loss ≥ 0.002. Enables Correct Score ECE ≤ 0.06.
- **Success:** Ship DC, retire LGBM OU models, add Correct Score market
- **Partial (beats on 2-3 lines but not all):** Ship as ensemble member for OU ladder, keep LGBM for the lines where it wins
- **Failure (DC loses on most lines):**
  1. Diagnose: is xG-based λ estimation better than historical goals? (Per `phase_2_new_features/research_backlog.md` RB-09)
  2. Pivot: frequentist Dixon-Coles (faster, simpler, less to tune)
  3. Secondary pivot: skip DC, stay single-model-per-market. Less efficient but ships.
- **Bailout criteria:** 6 weeks without DC beating LGBM on ≥ 2 OU lines → abandon DC as primary model for goals. Keep as research artifact. **[RYZYKO]**: DrMat has put significant math effort here — disagreement likely. Solution: show him the log-loss comparison numbers, let data decide.

### Auto-retraining on drift (month 12)

**Trigger conditions (any one fires retrain):**
1. PSI > 0.20 on any top-10 feature for 5+ days
2. ECE > 0.06 on pool on 7-day rolling
3. CLV < -1.5% on last 100 bets (warning — not yet rollback)
4. Scheduled: every 14 days regardless

**Safety rails:**
- Auto-retrain creates candidate in `Staging`, never auto-promotes to `Production`
- Human co-sign gate still required (founder + DrMat or DrMat-equivalent)
- Audit trail in MLflow: what triggered retrain, what's different in new candidate
- Failed retrain (training error, NaN loss, degenerate calibration) → alert, keep current model

**Failure fallbacks (auto-retrain):**
- **Target:** At least 1 real drift event triggers retrain correctly in first 60 days
- **Success:** Feature drift is no longer a manual babysit
- **Partial:** Fires but candidate never promoted (human rejects every time) — retain as alert mechanism but treat as advisory
- **Failure (fires on noise):** Raise thresholds, add hysteresis. See AH-4 fallback.
- **Bailout:** If month 14 has had 0 or 100+ retrain triggers → something's wrong with thresholds. Cut to scheduled-only retraining.

### 10 football leagues (month 13-14)

Per `ideas/phase_3_more_leagues/overview.md`:
- Add: Eredivisie, Championship, Primeira Liga, MLS, Brasileirão
- Each needs: scraper live, team name normalization, feature parity, backtest CLV ≥ 0, 2+ bookmaker odds sources

**ML-specific workstreams:**
- Each new league gets its own fold in walk-forward (don't pool with top-5 for training — leakage risk from schedule structure)
- Per-league calibration kicks in after n_league ≥ 500 (likely month 18-20 for newer leagues)
- **[RYZYKO]**: Brasileirão has limited xG data coverage per `phase_3_more_leagues/tasks.md` — model will be weaker there. Accept or cut.

### Beta → V1 gate criteria

Exit when:
1. Dixon-Coles in production for at least OU ladder (own 3-5 OU markets)
2. Auto-retrain pipeline has triggered ≥1 real retrain successfully
3. 10 football leagues live, each with CLV ≥ -1% on 100+ walk-forward bets
4. First B2B paying customer onboarded OR 10+ retained beta users
5. Alpha infrastructure (Pi, Hetzner CX32) stable for 90+ days
6. MLflow registry has 10+ models (3 markets × multiple versions), promotion gate framework audited

---

## V1 (month 14-22) — Multi-sport + hierarchical calibration + first B2B revenue

### V1 in one sentence

**Prove SportsLab is a multi-sport platform, not a football bet bot — ship tennis, basketball, hockey with the same quality bar, onboard first paying customer, lay groundwork for neural/graph ML in V2.**

### Modele (V1)

**Sport-specific model families:**

#### Football (continued from Beta/V1 transition)
- Ensemble (LGB+XGB+CB stacking) as baseline
- Dixon-Coles Bayesian for goals-derived markets
- No architecture change — just scale out to 10 leagues

#### Tennis (month 16)
- **Bradley-Terry per surface** (clay/hard/grass/indoor) as base rating
- **LGBM on Sackmann features** (serving %, 1st serve win %, break points converted, fatigue = matches in last 7d, H2H deep)
- **Logistic regression blend** of BT surface rating + LGBM
- Markets: match winner, set betting (2-0, 2-1), games handicap, first set winner

**Hipoteza** (per `ideas/phase_4_more_sports/sport_prioritization.md`): ATP ELO is hard to beat. LGBM on form features + BT per-surface should give ≥0.01 Δlog-loss vs ELO baseline. If not, we're in trouble as tennis is meant to be the "easy" first non-football.

#### Basketball (month 18)
- LGBM on pace-adjusted OffRtg/DefRtg, player availability (load management, injuries), recent form with back-to-back penalty
- **Player availability scraper** (NBA official injury reports) is critical — star-out games flip win probability by 15-20pp
- Markets: moneyline, spread, OU total points

**[RYZYKO]**: NBA Stats API rate limits block daily pipeline. Caching + distributed scraping required. Mitigation: Basketball-Reference as fallback source.

#### Hockey (month 20)
- LGBM on pace-adjusted Corsi/Fenwick/xG, goalie quality (season SV%, last 5 games SV%), special teams (PP%/PK%)
- Goalie is the biggest feature — unusual structure. SHAP to verify.
- Markets: moneyline (regulation + OT), puck line (-1.5/+1.5), OU total goals

### Abstract sport framework (month 15)

Per `ideas/phase_4_more_sports/overview.md`:

```python
# packages/ml-in-sports/src/ml_in_sports/sports/base.py
class SportAdapter(ABC):
    @abstractmethod
    def name(self) -> str: ...
    @abstractmethod
    def get_extractors(self) -> list[BaseExtractor]: ...
    @abstractmethod
    def get_feature_builders(self) -> list[BaseFeatureBuilder]: ...
    @abstractmethod
    def get_default_model(self) -> BaseModel: ...
    @abstractmethod
    def get_markets(self) -> list[str]: ...
    @abstractmethod
    def get_schema(self) -> dict: ...
```

**[RYZYKO]** (per phase_4 risks): abstract framework is prone to over-engineering. Rule: don't add abstraction unless you have 2 concrete implementations that would duplicate code. Tennis is implementation #2, so framework emerges from tennis work, not before it.

### Calibration (V1) — Hierarchical Bayesian

**Motivation:** Per-league calibration in Beta only works when n_league ≥ 500. For new leagues (Brasileirão year 1, Championship year 1) we have n_league < 200. Hierarchical Bayesian calibration **borrows strength from the pool** while still allowing per-league deviation.

**Design (DrMat spec):**
```
θ_league ~ Normal(μ_sport_market, τ)  # per-league calibration params
μ_sport_market ~ weakly_informative_prior
τ ~ HalfCauchy
```

Implementation:
- PyMC model per (sport × market)
- Fit via variational inference (ADVI)
- Posterior mean θ_league used as calibrator params
- Re-fit monthly (not every retrain — too expensive)

**Why not just do per-league calibration with n < 500?** Because fitting Dirichlet on 50 samples calibrates noise (per Alpha §3, DrMat rule). Hierarchical Bayesian regularizes toward the pool, which is the principled fix.

**Failure fallbacks (hierarchical Bayesian calibration):**
- **Target:** ECE on leagues with n_league ∈ [100, 500] drops from pool calibration (0.04) to 0.03
- **Success:** Ship, retire pool-calibration fallback for mid-sample-size leagues
- **Partial (ECE drops to 0.03-0.035):** Ship, document modest gain
- **Failure:**
  1. Diagnose: is ADVI converging? Run with 3 seeds, check ELBO trajectory and posterior mean stability.
  2. Hipoteza: our leagues are too heterogeneous to share a prior effectively (Brasileirão dynamics ≠ Premier League). Hierarchical makes sense only if pooling structure is real.
  3. Pivot: hierarchy grouped by league-tier, not globally (e.g., Top-5 European + Tier-2 European + Americas as 3 groups with separate shared priors).
  4. Secondary pivot: frequentist shrinkage (e.g., empirical Bayes via James-Stein-like estimator) — simpler, less convergence risk.
- **Bailout:** 6 weeks, no convergence or no ECE gain → abandon hierarchical, stay per-league-with-pool-fallback from Beta. **[RYZYKO]**: high-prestige math project for DrMat, disagreement likely on cutting. Resolution: show numbers.

### Markets (V1)

Per sport:

| Sport | Markets at V1 exit |
|-------|-------------------|
| Football | All 8 from Beta + Correct Score, First Half 1X2 (from DC model). Total 10. |
| Tennis | Match winner, set betting, games handicap, first set. Total 4. |
| Basketball | Moneyline, spread, OU total. Total 3. |
| Hockey | Moneyline (reg + OT), puck line, OU total. Total 3. |

**Total markets in V1:** ~20.

### Features (V1)

**Still no graph / transformer / NLP — those are V2.** V1 focuses on **sport-specific feature richness**:

- Tennis: serving breakdown, fatigue (matches in 7/14 days), travel distance, surface transition penalty
- Basketball: pace-adjusted, availability, back-to-back
- Hockey: goalie rolling SV%, special teams, schedule density

**[PEWNE]**: feature engineering is the real work of V1 — per-sport adapters each need 2-4 weeks of feature dev.

### Risk / Kelly (V1) — Portfolio Kelly with Ledoit-Wolf

**Beyond Beta's Bayesian Kelly:** now with **covariance shrinkage**.

Why: Once you have 20 markets × 10 football leagues + 3 other sports, on any given day you may have 50-100 candidate bets. Simple per-bet Kelly ignores correlations (two bets on Real Madrid's match × 1X2 and OU are correlated). Portfolio Kelly with covariance-aware sizing → better risk-adjusted return.

**Ledoit-Wolf shrinkage:** empirical covariance Σ_hat is noisy when n_bets is not >> n_markets. LW shrinks toward a structured target (diagonal or constant-correlation), stabilizing the inversion in the Kelly optimizer.

**Implementation:**
```python
from sklearn.covariance import LedoitWolf
# bet-level returns across historical cohort
Sigma_hat, shrinkage = LedoitWolf().fit(bet_returns).covariance_, LedoitWolf().fit(bet_returns).shrinkage_
# portfolio optimization with constraints
stakes = scipy.optimize.minimize(
    neg_log_growth, x0=fractional_kelly_stakes,
    constraints=[per_match_cap, per_league_cap, total_exposure_cap]
)
```

**[RYZYKO]**: computationally expensive when portfolio is 50+ bets. Optimization takes >5s. Caching + pre-computed scenarios needed.

### Infrastructure (V1)

- **Hetzner CX32 (€20) → Hetzner CX42 (€35)** once basketball + hockey + tennis all running
- **Multi-sport DB schema migration** (Postgres from SQLite at month 17-18)
- **MLflow moves to dedicated instance** (not local Dev PC) — small Hetzner VM with managed volume
- **GPU not needed yet** — tree models + Bayesian calibration fit on CPU comfortably
- **Feature store**: start with Postgres-backed custom (materialized views per sport × league × gameweek). Feast evaluation deferred to V2.

### Monitoring / alerting (V1)

Per-sport dashboards:
- ECE per sport × market (90-day rolling)
- CLV per sport × bookmaker (30-day rolling)
- Prediction count per sport (daily, catches pipeline broken)
- Cost per sport (training + serving compute)

### Cost (V1 exit, month 22)

- Hetzner CX42: €35
- Hetzner CX32 (MLflow): €20
- Postgres managed: €10 (Hetzner volume + backup)
- Cloudflare / domain: €2
- Odds API / data sources: €30 (scaled up with multi-sport)
- **Total: ~€100/mo operational**

Bankroll: €3,000-8,000 (depends on R3 results and any reinvestment).

### Team requirements (V1)

**First external help probably needed in V1:**
- **Sports domain expert (per sport)** — 0.1 FTE each, ad-hoc consulting. Could be Discord/forum relationships or $200 per consult on specific questions.
- **Still no full-time ML hire** — one founder + Claude Code still covers it, but only if Beta-Alpha transition went smoothly and there's no firefighting backlog.
- **Fractional DevOps (0.2 FTE)** may be needed at month 20 when Hetzner setup gets complex.

**[HIPOTEZA]**: if V1 monthly revenue is €500+ by month 20, can afford fractional DevOps. If not, founder does it with Claude Code.

### Success KPIs (V1)

Exit gate:
1. 3 sports live (tennis, basketball, hockey) each with ROI ≥ 5% walk-forward
2. 10 football leagues live, each CLV ≥ 0 on 200+ bets
3. Abstract framework contract tests green — adding 4th sport would take ≤ 4 weeks
4. First paying B2B customer, invoice > €200, sustained 3 months
5. MRR > infrastructure cost (break-even on infra, ~€100/mo)
6. Ensemble + hierarchical Bayesian calibration in production, ECE ≤ 0.03 on n_league ≥ 100
7. Zero rollbacks in last 60 days

### Failure fallbacks (V1)

#### V1 experiment: Abstract sport framework

**Target:** Tennis and basketball implementations both use the same `SportAdapter` interface, adding hockey takes ≤ 4 weeks

**Success:** Framework proven, platform story credible

**Partial (framework works but adding hockey still takes 8+ weeks):** Framework gives some reuse but not enough to claim "4-6 weeks per new sport" (original phase_4 promise). Adjust product messaging.

**Failure (framework becomes bottleneck):**
1. Diagnose: which abstractions are wrong? If every sport has to override 80% of methods, the abstraction is fake.
2. Pivot: drop framework, duplicate code across sports. YAGNI — 3 sports can live as 3 siblings without abstraction.
3. Secondary pivot: shared utilities (calibration, Kelly, drift) as library, but per-sport pipelines as independent apps.

**Bailout:** 4 weeks in, framework is making tennis slower not faster → rip out, duplicate, move on. **[PEWNE]**: premature abstraction is the #1 risk here, and I'd rather ship 3 duplicate-code sports than one beautifully abstract sport.

#### V1 experiment: Tennis model beats ELO baseline

**Target:** Δlog-loss ≥ 0.01 vs ELO baseline on walk-forward 2020-2025

**Success:** Tennis ships, proves non-football works

**Partial (matches ELO):** Ship anyway. ELO-parity with additional features (Kelly sizing, calibration) is still a product. Don't promise edge in marketing.

**Failure (loses to ELO):**
1. Diagnose: is serving data coverage complete per Sackmann? Missing data → feature weakness.
2. Hipoteza: ATP is too efficient for ML to beat ELO+form. Pivot to ATP Challenger + ITF circuits where less betting action means market less efficient.
3. Pivot: WTA often has higher ROI in literature — focus on WTA first, ATP second.

**Bailout:** 8 weeks, tennis model below ELO → tennis ships as "coverage product" without edge claims. We sell the data, not the bets. Pivots revenue model subtly.

#### V1 experiment: First B2B paying customer

**Target:** 1 invoice ≥ €200 by month 22

**Success:** Product-market-fit signal, ML results validated commercially

**Partial (trials but no conversion):** Interview the "no" — is it price, trust, delivery format, feature gap? Iterate SKU before V2.

**Failure (zero revenue in 8 months):**
1. Diagnose: are we talking to wrong persona (bettors vs tipsters vs clubs)?
2. Pivot A: drop B2B, try B2C subscriptions (€20-50/mo tipster service via Telegram).
3. Pivot B: drop paid product entirely, monetize via referral/affiliate to bookmakers.
4. Pivot C: consulting — sell custom backtests to funds/hedge-style operators at higher price per engagement.

**Bailout:** 12 months zero revenue from V1 work → serious strategic rethink. "Is this a business or a hobby?" This is one of three "bet the farm" moments in the roadmap.

---

## V1 → V2 transition (month 22-28) — Graph, NLP, sentiment

V1 proved platform. V2 is where modeling gets ambitious. **[HIPOTEZA]**: by this point either revenue is growing (we can hire) or it's flat (we should optimize cost, not features).

### GNN team embeddings (team2vec)

**Concept:** Teams aren't tabular — they're nodes in a graph of opponents. A team's "identity" is its historical matchups and outcomes. Graph Neural Network on this graph produces `team_embedding` (e.g., 32-dim vector) that captures stylistic similarity.

**Implementation plan:**
- Graph: teams are nodes, edges are matches, edge features are (venue, result, xG for/against)
- GNN: GraphSAGE or GAT with 2-3 layers
- Training: contrastive loss (similar teams should have similar embeddings) or downstream task (predict next match outcome using team_embeddings as features)
- Output: `team_embedding[team_id, season_id]` per gameweek

**How it enters the pipeline:** LGBM/XGB gets `team_embedding_home` and `team_embedding_away` (or their diff) as features. Shadow mode for 3 months, then A/B vs baseline.

**Failure fallbacks (team2vec):**
- **Target:** Δlog-loss ≥ 0.002 on 1X2 when embedding features are added vs without
- **Success:** Promote, retrain ensembles with embeddings
- **Partial (Δ 0-0.002):** Embeddings captured some signal but noisy. Keep as feature family, monitor.
- **Failure (no improvement):**
  1. Diagnose: are embeddings stable across seasons? PCA visualization — if teams cluster meaningfully (e.g., by league, style) it's a real signal.
  2. Hipoteza: rolling features already capture what GNN would capture (form, H2H baked in). GNN is redundant on our data.
  3. Pivot: skip GNN, invest in NLP features (injury news, sentiment) which target different signal.
- **Bailout:** 10 weeks, no Δlog-loss → abandon GNN. Document. Keep as research artifact.

### Social sentiment features

**Concept:** Twitter + Reddit discussion volume/sentiment pre-match may predict outcomes better than pure form. Research backlog RB-10-type feature but for social.

**Implementation plan:**
- Twitter API paid tier (~$100/mo) for 24h pre-match mentions per team
- Reddit scrape (r/soccer, r/nba, etc.) for comment volume / upvote sentiment
- NLP pipeline (HuggingFace transformer for sentiment classification)
- Features: `sentiment_delta_home_vs_away`, `mention_volume_home`, `star_player_mention_count`
- Aggregate to pre-match snapshot (24h cutoff, NO leakage of post-match tweets)

**Failure fallbacks (sentiment):**
- **Target:** Δlog-loss ≥ 0.001 on 1X2 top-5 leagues
- **Success:** Promote
- **Partial:** Keep as optional feature family, useful for narrative in reports even if modest log-loss gain
- **Failure:**
  1. Diagnose: is sentiment noisy because of fanbase size asymmetry? (Manchester United has 10x the Twitter volume of Burnley — dominates signal)
  2. Pivot: per-team normalized sentiment (z-score within team's history)
  3. Secondary pivot: drop sentiment, invest in injury news NLP
- **Bailout:** 8 weeks, noise → abandon. Twitter API cost drops to 0.

### Injury news NLP

**Concept:** Transfermarkt + Sofascore injury reports, processed via NLP, become features like `key_player_doubtful`, `starting_11_unavailability_score`.

**Implementation plan:**
- Scrape Transfermarkt injuries daily
- Match "player X doubtful for match Y" to fixture
- Rate player importance (FIFA rating or market value from Transfermarkt)
- Feature: `weighted_player_unavailability_score = sum(p_importance_i * p_doubtful_i)` over team's expected starting 11

**Failure fallbacks (injury NLP):**
- **Target:** Δlog-loss ≥ 0.002 on 1X2 when rounds with ≥3 reported injuries
- **Success:** High-value feature, ship
- **Partial:** Works on subset — maybe only on top-5 leagues with rich Transfermarkt coverage
- **Failure:**
  1. Diagnose: does closing odds already price in injury news? (Yes, largely — by kickoff the market has absorbed it)
  2. Hipoteza: injury feature value is only for opening-line betting, not closing-line. So the feature + closing-odds-based CLV metric will be flat because the signal is already in odds.
  3. Pivot: use injury feature specifically for **opening-line bet recommendations** (different product segment — early-bird tipster feed).
- **Bailout:** 6 weeks, no Δlog-loss → keep scraper for product display (show users "Bellingham doubtful"), drop as predictive feature.

---

## V2 (month 28-36) — Live, micro-markets, neural calibration

### V2 in one sentence

**Transition from pre-match only to live/in-play, add micro-markets (corners, cards), and introduce neural network components where they earn their keep.**

### Modele (V2)

#### Live/in-play model (month 28-30)

**Concept:** Pre-match model + live score state → conditional expected goals → live implied probabilities.

**Design (DrMat domain — I implement):**
- Conditional Dixon-Coles: λ_remaining_home, λ_remaining_away as function of current score, time remaining, match state (red cards, xG accumulated)
- Bayesian update: prior = pre-match model, likelihood = live match events (goals, shots, cards)
- Output: updated P(home win | state at minute t) every 1-5 minutes

**Scope limits (V2):**
- Top-5 football leagues only (liquidity requirement for live odds)
- 1X2 + OU_2.5 live markets only (enough proof of concept)
- Target: bet placement within 3s of odds update (latency requirement)

**[RYZYKO]**: live is a different game. Odds move every second during scoring plays. Our pipeline needs to be robust to rate limits, API failures, and not bet stale data.

**Failure fallbacks (live/in-play):**
- **Target:** Live CLV ≥ 0 on 500 live bets over 3 months
- **Success:** Ship live product to top paying customers (premium tier)
- **Partial:** Flat CLV → live model matches market, no edge. Ship as "companion to pre-match" not primary.
- **Failure (negative CLV):**
  1. Diagnose: are our live odds stale? Latency from scrape to decision?
  2. Hipoteza: live markets are way more efficient than pre-match. The theoretical edge isn't realizable at our latency (3s minimum).
  3. Pivot: pick specific live market niches — e.g., next goal scorer, next-card prediction, or late-match outcome. These move slower than main market.
- **Bailout:** 12 weeks negative CLV → abandon live, remain pre-match. Live is a deep pocket — don't marry it if it doesn't work fast. **[RYZYKO]**: this is one of three "bet the farm" moments — live can eat months of engineering for no gain.

#### Neural network calibration (month 26-28)

**Motivation:** Hierarchical Bayesian calibration is mathematically nice but assumes functional form (Dirichlet / Beta). Neural net calibrator (MLP on logit + meta-features) is more flexible.

**Design:**
- Input: [logit_pool_calibrated, league_id_embedding, market_id_embedding, n_bets_this_league, time_since_last_retrain]
- Architecture: MLP with 2 hidden layers (64, 32), sigmoid output
- Training: log-loss on calibration holdout

**[RYZYKO]**: MLP calibrator is an extra layer that can fail silently. Must validate ECE improvement or reject.

**Failure fallbacks (MLP calibrator):**
- **Target:** ECE parity with hierarchical Bayesian OR beats it
- **Success:** Promote if cheaper to train and maintain
- **Partial:** Matches but not faster → not worth adding. Stay with HB.
- **Failure (ECE worse):**
  1. Diagnose: overfitting. Try dropout, L2, smaller net.
  2. Hipoteza: MLP doesn't have the inductive bias that HB's explicit mixture structure gives. For probability calibration, explicit parametric forms win on tabular.
  3. Pivot: skip NN calibration, stay HB.
- **Bailout:** 6 weeks, no parity → abandon. Document negative result.

#### Corners + Cards micro-markets (month 30-32)

**Markets:** Corners OU 9.5/10.5/11.5, Cards OU 3.5/4.5/5.5, First Card Team

**Data needed:**
- Historical corners + cards per match (Sofascore has it, FBref partially)
- Referee features (some refs are card-heavy — per research backlog RB-11)
- Team aggression features (fouls committed, tackles)

**Models:** Separate LGBMs or Poisson regression (corners are count-distributed).

**Failure fallbacks (micro-markets):**
- **Target:** Each market ROI ≥ 3% on 500 walk-forward bets
- **Success:** Ship
- **Partial (ROI 0-3%):** Ship with low-Kelly cap, lower-tier product
- **Failure (ROI ≤ 0%):**
  1. Diagnose: bookmaker margin on micro-markets is ~8-10% (vs 2-3% on 1X2) — requires much bigger edge.
  2. Pivot: skip micro-markets for Beta-Kelly audience, sell feature data (corners/cards predictions as data product) to B2B customers (tipsters) who use them as inputs.
- **Bailout:** 10 weeks, no ROI → abandon as bet products. Keep predictions in API as data product.

### Infrastructure (V2)

- **Feature store (Feast or custom):** Requirements now — with in-play, feature serving at <50ms p95 becomes real constraint. Feast with Redis backend or Postgres with heavy indexing.
- **GPU box (on-demand):** for GNN training in V1-V2 transition and for NN calibrator. RunPod A100 at ~$1.50/h, rent when training (~20h/month = $30).
- **Upgrade to Hetzner CX52 (€65) or AX41 (€40)** for main production — live pipeline needs CPU headroom.
- **Redis cache** for live odds state.
- **WebSocket ingestion** for live odds feed (pushes from The Odds API or Betfair Exchange).

### Monitoring (V2)

Additions:
- **Live latency dashboard:** odds update → bet decision end-to-end p50/p95/p99
- **Micro-market ECE + margin-adjusted ROI** (critical given margins eat edge)
- **GPU utilization / spend** (if on-demand GPU used)

### Cost (V2 exit, month 36)

- Hetzner AX41: €40
- Feature store (Redis managed): €20
- GPU on-demand: €30 average
- Odds APIs (paid tier for live): €100
- DB (Postgres + Timescale): €30
- Monitoring (Grafana Cloud free or Better Stack €22)
- **Total: ~€240/mo operational**

Bankroll: depends entirely on revenue trajectory. If B2B revenue is €2-5k/mo by V2, cost is trivial. If still €500-1000/mo, V2 infra is stretching.

### Team requirements (V2)

- **1 part-time ML engineer hire likely needed** if revenue supports it (€3-5k/mo fractional)
- OR Founder stays solo with Claude Code IF Beta-V1 was well-factored and V2 is incremental
- **Sports domain experts (0.1 FTE each)** for ongoing per-sport work
- **Part-time DevOps (0.3 FTE)** — infrastructure complexity now exceeds founder's bandwidth

### Success KPIs (V2)

Exit gate:
1. Live pre-match in production on top-5 football, CLV ≥ 0 over 90 days
2. In-play model either proven (CLV ≥ 0) or formally rejected
3. Corners + cards markets either shipped (ROI ≥ 3%) or formally killed
4. GNN team embeddings in production (if passed V1→V2 gate)
5. Neural calibration either matching HB or formally rejected
6. MRR ≥ €2,000 (2-3 paying B2B customers)
7. Feature store handling 1000+ feature lookups/day at p95 < 50ms
8. 0 catastrophic outages (defined: >2h downtime) in last 90 days

---

## V2 → V3 transition (month 36-42) — Transformers, online calibration, multi-user

### Transformer match history encoder (month 36-40)

**Concept:** Instead of rolling windows (last 5 games stats), encode the sequence of last N matches as tokens → Transformer → fixed-size embedding → feature for LGBM.

**Implementation plan:**
- Sequence: last 20 matches per team, each match encoded as feature vector (xG for/against, result, opponent rating, venue)
- Transformer: 2-layer encoder, 4 heads, 128-dim, positional encoding = relative days since match
- Output: pooled 128-dim embedding per team per gameweek
- Downstream: same LGBM with transformer embedding as features

**Why now:** Tree ensembles are near-peak on our tabular features. Sequence models can capture recency-weighted patterns that rolling windows smooth over.

**[RYZYKO]**: transformer training needs GPU. €30-50/month rental. Feature store latency takes a hit (embedding lookup vs cached).

**Failure fallbacks (transformer encoder):**
- **Target:** Δlog-loss ≥ 0.002 vs best ensemble+GNN baseline
- **Success:** Promote, major ML moat claim for marketing
- **Partial (Δ 0-0.002):** Ship if cheap to maintain, otherwise skip.
- **Failure:**
  1. Diagnose: is our data too small for transformer? (N matches per team per season ~35. Total history per team ~250. Small for attention.)
  2. Hipoteza: our rolling features already capture most of what transformer would capture. Attention needs LOT of data to shine over inductive biases.
  3. Pivot: LSTM with match history — simpler sequence model, less parameter-hungry.
  4. Secondary pivot: skip sequence models, stay tree+GNN.
- **Bailout:** 12 weeks, no Δlog-loss → abandon transformers. Big visible failure — may need founder to re-message ML moat story if it was promised in fundraising.

### Online calibration (month 42)

**Concept:** Instead of batch-retraining calibrator monthly, update it continuously as bets settle. Streaming Bayesian update.

**Why:** Regime changes (season start, COVID-like events, new manager) degrade calibration faster than monthly retrain catches. Online calibration maintains ECE over time without batch lag.

**Design:** Online Bayesian logistic regression on (logit, actual_outcome) pairs, streaming.

**Failure fallbacks (online calibration):**
- **Target:** ECE 14-day rolling beats batch-retrained monthly calibration
- **Success:** Cheaper + better, ship
- **Partial:** ECE parity → ship for cheaper compute, else skip
- **Failure:** Streaming updates amplify noise → hybrid: monthly batch + daily online correction
- **Bailout:** 4 weeks, no clear win → abandon, stay monthly batch. Low-cost experiment.

### Multi-user bankroll optimization (month 42)

**Concept:** If SportsLab has 100+ users acting on same Telegram tips, market impact matters. Bookmakers notice concentrated action → limit accounts.

**Design:** Bet size caps per-market scaled inversely to N_concurrent_users. Or stagger tips: paid tier gets earlier, free tier gets later.

**[RYZYKO]**: this is a product/business concern as much as ML. If we're not at scale to matter, YAGNI.

---

## V3 (month 42-54) — Bloomberg-for-sports stack, research moat

### V3 in one sentence

**Full-platform stack: live, player props, cross-market signals, academic credibility via whitepaper + open-source, enterprise-ready scale.**

### Modele (V3)

#### Player props (month 44-48)

Markets:
- Goalscorer (anytime, first, last)
- Shots over/under per player
- Passes, tackles, assists (football)
- Points over/under per player (basketball)
- Aces, double faults per player (tennis)

**Data:** Per-player historical stats from FBref (football), NBA Stats, ATP Stats.

**Model:** Per-player Poisson regression or LGBM on per-player rolling features. Feature engineering is the real work.

**Failure fallbacks (player props):**
- **Target:** ROI ≥ 2% on 1000 player-prop bets (low bar — props have high margins)
- **Success:** Ship as premium SKU tier
- **Partial:** Works for star players only (lots of data) — restrict to top-N players per league
- **Failure:** High variance, data-hungry, limited edge → abandon, replace with "player stats data product" (sell predictions, not bets)
- **Bailout:** 12 weeks, abandon to data product

#### Cross-market arbitrage signals (month 50)

**Concept:** Find same outcome priced differently across markets (e.g., OU_2.5 on Pinnacle vs implied OU_2.5 from Correct Score 3:2 + 2:3 + 3:1 + ... on Betfair).

**Why:** True arbitrage is rare (<1%), but **near-arbitrage within margin of error** is more common. For our users, even detecting price dislocations is valuable.

**Implementation:** Graph of related markets, automated consistency checks, flag outliers.

#### Tactical NLP (month 50+, exploratory)

**Concept:** Coach press conferences, pre-match interviews → tactical cues → features.

**[HIPOTEZA]**: low ROI. Speculative research. Include as "R&D line item" not core product.

### Research moat (month 48-54)

This is the phase where ML becomes a **marketing and credibility asset**, not just a product feature.

**Actions:**
1. **Whitepaper on arXiv:** "Hybrid Calibrated Portfolio Kelly for Multi-Sport Prediction" — DrMat-led, I contribute empirical validation section
2. **Open-source release:** `sportslab-calibration` Python library (Beta + Dirichlet + hierarchical Bayesian) as PR moat. Cost: 2-3 weeks of cleanup + docs + tests. Reward: every ML person in sports knows our name.
3. **Academic collaboration:** reach out to 1 UK/US quant group (LBS, LSE, Oxford, CMU) for joint research project — co-author a paper in 2027-2028
4. **Conference presentation:** apply to MIT Sloan Sports Analytics Conference (accept rate ~15%) with our methodology

**Failure fallbacks (research moat):**
- **Target:** arXiv paper + 1 OSS library + 1 academic collaboration by month 54
- **Success:** Credibility moat
- **Partial:** Paper only, no OSS or academic → still useful for sales/fundraising
- **Failure (nothing ships):** If DrMat is too slow or founder is too busy → hire a ghost writer / research assistant specifically for this. Don't let marketing debt accumulate.

### Infrastructure (V3)

**Only scale up to Kubernetes multi-region if customer base justifies it.** If we have 100+ enterprise customers demanding <500ms global latency, K8s + multi-region deploy. Otherwise Hetzner AX41 + CDN serves V3 without over-engineering.

**Trigger for K8s:** ≥5 customers demanding SLA > 99.9%, OR global distribution of customers across US/EU/Asia.

### Cost (V3, month 54)

If Kubernetes deployment:
- K8s cluster (DigitalOcean / GKE): €500-1000/mo
- Multi-region DB: €300-500/mo
- Enterprise monitoring (Datadog / NewRelic): €200-500/mo
- **Total: €1,000-2,000/mo infrastructure**

If still single-region Hetzner:
- €300-400/mo total

Variable based on **revenue and customer count**. Revenue per customer at V3 should be €500-2000/mo B2B → 20-40 customers = €10-80k MRR, infrastructure at <5% of revenue.

### Team requirements (V3)

If SportsLab is successful at V3:
- 2-3 ML engineers
- 1 DevOps / SRE
- 1 DataEng
- 1 Designer (part-time)
- 1 Growth / Sales (full-time)
- Founder as CTO/CEO split

If not at revenue level to support team:
- Founder + contractors
- V3 telescoped into 2-3 years instead of 12-18 months

### Success KPIs (V3)

Exit gate (end of roadmap):
1. Multi-sport production at V2 scale + player props + cross-market signals
2. arXiv whitepaper published
3. 1 open-source release with ≥100 GitHub stars
4. MRR ≥ €10,000 (could be 10-40 B2B customers depending on segment)
5. 0 catastrophic outages in 12 months
6. At least 1 acquisition offer discussion OR Series A-ready metrics (MRR growing 15%+/mo, retention 90%+)
7. Founder has successor or clear transition path (if optionality on exit is maintained)

---

## Risk register — by phase

| Phase | Primary risk | Secondary risk | Mitigation |
|-------|--------------|----------------|------------|
| Alpha | CLV < 0 on first 100 live bets → product dead in water | Beta users churn after first losing week | Tight tiered wording per §9 of alpha spec, bi-weekly retrain, human co-sign |
| Alpha Hardening | BTTS doesn't calibrate → ship 2 markets not 3 | Pinnacle closing odds API disappears → no CLV ground truth | Multiple closing odds sources (Betfair fallback), accept 2-market Alpha if needed |
| Beta | Ensemble doesn't beat single LGBM → months of work flat | Per-league calibration calibrates noise | Fallback to ensemble = single LGBM + different feature subsets, abandon per-league at 6-week bailout |
| Beta→V1 | Dixon-Coles VI doesn't converge | Auto-retrain fires on noise | Frequentist DC fallback, higher PSI thresholds |
| V1 | Tennis doesn't beat ELO → non-football story dies | First B2B customer doesn't land → revenue never arrives | WTA-first pivot, B2C pivot, consulting pivot |
| V1→V2 | GNN team2vec gives no edge → ML moat claim weakens | Sentiment features are noise | Abandon, invest in NLP injury or micro-markets |
| V2 | Live model loses money fast → months of engineering dead | Micro-markets don't clear bookmaker margins | Strict 12-week bailout on live, data-product pivot for micro-markets |
| V2→V3 | Transformer encoder disappoints → visible moat claim fails | Online calibration is noisier than batch | LSTM pivot, hybrid batch+online |
| V3 | Research moat doesn't materialize (whitepaper drags) | Founder burnout at 4 years solo | Hire research assistant specifically for publication path, founder-health mandate from Lead |

---

## Failure fallbacks by experiment — MASTER TABLE

Reproduced for quick reference — each listed in prose above with full diagnosis steps.

| # | Experiment | Phase | Target metric | Bailout criteria |
|---|-----------|-------|---------------|------------------|
| 1 | BTTS ship | Alpha Hardening | ECE ≤ 0.04, CLV ≥ 0 on 100+ bets | 4 weeks, ECE > 0.06 → cut |
| 2 | Pinnacle closing odds pipeline | Alpha Hardening | ≥85% coverage on placed bets | 6 weeks, <50% coverage → self-reported metrics |
| 3 | 10× bagging infra | Alpha Hardening | Variance correlates with error (r > 0.3) | 4 weeks, no correlation → defer Bayesian Kelly permanently |
| 4 | PSI drift monitoring | Alpha Hardening | <1 FP/mo, catches real drift | 3 weeks, spams/misses → simpler KS-test |
| 5 | Ensemble (LGB+XGB+CB) | Beta | Δlog-loss ≥ 0.001, BH-FDR p<0.1 | 6 weeks, no Δ → single LGBM stays |
| 6 | Per-league calibration | Beta | ECE 0.04 → 0.025 on top-5 | 6 weeks, no ECE gain → pool stays |
| 7 | Bayesian posterior Kelly | Beta | ≥3% growth advantage, tighter drawdown | 8 weeks, no advantage → permanent abandon |
| 8 | 5-7 new markets | Beta | Each ECE ≤ 0.05, CLV ≥ -1% | Month 10, ≤4 total markets is acceptable |
| 9 | Dixon-Coles goals model | Beta→V1 | Δlog-loss ≥ 0.002 on 2+ OU lines | 6 weeks, no wins → frequentist DC or skip |
| 10 | Auto-retrain on drift | Beta→V1 | 1+ real trigger in 60 days | Month 14, 0 or 100+ triggers → scheduled-only |
| 11 | Eredivisie, Championship, Primeira, MLS, Brasileirão | Beta→V1 | CLV ≥ -1% on 100+ bets per league | Any league failing → document, drop if needed |
| 12 | Abstract sport framework | V1 | Adding hockey ≤ 4 weeks | 4 weeks on tennis, framework slowing → rip out |
| 13 | Tennis model | V1 | Δlog-loss ≥ 0.01 vs ELO | 8 weeks, loses → tennis as data product |
| 14 | Basketball NBA | V1 | ROI ≥ 5% walk-forward | NBA API issues → Basketball-Reference pivot |
| 15 | Hockey NHL | V1 | ROI ≥ 5% walk-forward | NHL short season → accept + SHL bonus |
| 16 | Hierarchical Bayesian calibration | V1 | ECE 0.04 → 0.03 on n_league ∈ [100,500] | 6 weeks, no convergence → per-league+pool from Beta |
| 17 | First B2B paying customer | V1 | 1 invoice ≥ €200 | 12 months, 0 revenue → strategic rethink |
| 18 | Portfolio Kelly Ledoit-Wolf | V1 | Drawdown tighter, growth retained | Computational too expensive → per-market caps only |
| 19 | GNN team embeddings | V1→V2 | Δlog-loss ≥ 0.002 on 1X2 | 10 weeks, no Δ → abandon |
| 20 | Social sentiment features | V1→V2 | Δlog-loss ≥ 0.001 on top-5 | 8 weeks, noise → drop Twitter spend |
| 21 | Injury news NLP | V1→V2 | Δlog-loss ≥ 0.002 on high-injury rounds | 6 weeks, no Δ → display-only feature |
| 22 | Live/in-play model | V2 | CLV ≥ 0 on 500 live bets over 3mo | 12 weeks, negative CLV → abandon live |
| 23 | MLP calibrator | V2 | ECE parity or better vs HB | 6 weeks, worse → stay HB |
| 24 | Corners + Cards markets | V2 | Each ROI ≥ 3% on 500 bets | 10 weeks, no ROI → data product only |
| 25 | Feature store (Feast) | V2 | <50ms p95 feature lookup | Operational complexity too high → stay Postgres materialized views |
| 26 | Transformer encoder | V2→V3 | Δlog-loss ≥ 0.002 vs ensemble+GNN | 12 weeks, no Δ → abandon |
| 27 | Online calibration | V2→V3 | Beats batch-retrained | 4 weeks, noisy → hybrid batch+online |
| 28 | Player props (goalscorer) | V3 | ROI ≥ 2% on 1000 bets | 12 weeks, abandon → data product |
| 29 | Cross-market arbitrage | V3 | ≥5 real signals per week | Hard to validate → advisory feature only |
| 30 | Research moat (paper + OSS) | V3 | arXiv + 1 OSS library + 1 academic collab | Month 54, none of 3 → hire research assistant |

---

## Resource requirements per phase

### Alpha (month 0-2)

- Team: 1 (founder + Claude Code)
- Infra: Pi 4GB + Dev PC (owned)
- Monthly infra cost: €5-10
- Bankroll: €1,000 personal
- Claude Code usage: heavy (implementation partner)

### Alpha Hardening (month 2-4)

- Team: 1
- Infra: same + Hetzner CX32 spin-up
- Monthly infra cost: €25-30
- Bankroll: €1,500 personal

### Beta (month 4-10)

- Team: 1, possibly 0.1 FTE external stat advisor (ad-hoc)
- Infra: Pi + Hetzner CX32 + Dev PC
- Monthly infra cost: €45
- Bankroll: €2,000-3,000 personal
- Claude Code usage: sustained heavy

### Beta→V1 (month 10-14)

- Team: 1
- Infra: + Postgres migration
- Monthly infra cost: €60-80
- Bankroll: €3,000-5,000

### V1 (month 14-22)

- Team: 1-1.3 FTE (founder + 0.2-0.3 FTE fractional DevOps if affordable)
- Infra: Hetzner CX42 + CX32 + Postgres + MLflow
- Monthly infra cost: €100-150
- Bankroll: €5,000-10,000
- Sports domain consulting: €200-500/mo ad-hoc
- **First revenue expected:** month 19-22

### V2 (month 22-36)

- Team: 1-2 FTE (founder + 0.5 FTE ML engineer IF revenue supports)
- Infra: multi-VM + GPU on-demand + feature store
- Monthly infra cost: €200-300
- **Revenue expected:** €2,000+/mo by month 30

### V3 (month 36-54)

- Team: 2-5 FTE depending on revenue
- Infra: scales with customer base; €300-2,000/mo
- **Revenue expected:** €10,000+/mo by month 48

### GPU hours estimate

| Phase | GPU hours/month | Cost |
|-------|----------------|------|
| Alpha | 0 | €0 |
| Beta | 0 | €0 |
| Beta→V1 | 10 (DC Bayesian VI) | €15 |
| V1 | 20 (HB calibration, VI) | €30 |
| V1→V2 | 40 (GNN training) | €60 |
| V2 | 50 (live model inference + NN calibrator) | €75 |
| V2→V3 | 100 (transformer training + backtests) | €150 |
| V3 | 150+ | €225+ |

---

## KPI evolution — what metric dominates at each stage

| Phase | Hero metric | Secondary | Explicit anti-metric |
|-------|-------------|-----------|---------------------|
| Alpha | CLV ≥ 0 on 200+ bets | ECE ≤ 0.05, rollback-free 30d | "Win rate" — forbidden on landing |
| Alpha Hardening | Measurement infra stable | BTTS added, PSI live | Overclaim CLV pre-500-bets |
| Beta | ECE ≤ 0.03 on top-5 + markets count = 8 | Δlog-loss vs Alpha champion | Ensemble without statistical signif |
| Beta→V1 | Markets × leagues coverage (10 × 8+) | Dixon-Coles proven on OU ladder | Cutting corners on leakage tests |
| V1 | # sports in production (3) + 1st revenue | Abstract framework adds 4th sport ≤4 wk | Sport shipped without CLV validation |
| V1→V2 | Graph/NLP signal validated (or killed cleanly) | MRR growing | "Shipped but didn't help" in prod |
| V2 | Live CLV or formally rejected | MRR ≥ €2k | Live pipeline slop (>5s latency) |
| V2→V3 | Transformer advantage proven (or killed) | Online calibration advantage | Overfitting on single-season tests |
| V3 | MRR ≥ €10k + research moat | 0 catastrophic outages | Scaling K8s without customer need |

**Meta-pattern:** early phases dominated by **technical correctness** (CLV, ECE, leakage). Middle phases by **coverage** (markets, leagues, sports). Later phases by **revenue + research credibility**. Each transition needs the previous phase's metric proven before next starts.

---

## Competitive moat analysis — what protects us per phase

### Alpha — moat: none yet
- We're just another sports betting Telegram feed at this stage. No moat beyond "founder is willing to ship and track CLV honestly".
- Copycat cost to build Alpha: ~3 months with existing research code.
- **Protection:** speed. Ship while competitors dither on legal/brand.

### Beta — moat: calibration discipline
- Per-league calibration + Bayesian Kelly + ensemble is **not proprietary** (all published methods) but is **expensive to get right** (6+ months of discipline to validate each piece)
- Copycat cost: 6-9 months with a real ML engineer
- **Protection:** operational rigor + honest reporting (tiered wording per drmat §7.1 is a competitive weapon when competitors overclaim)

### V1 — moat: multi-sport platform story
- Abstract framework + 3 sports live is **structurally harder** to copy than model architecture
- Copycat cost: 12-18 months (need domain expertise per sport, not just ML)
- **Protection:** data coverage breadth (10 football leagues + 3 sports) + B2B customer relationships + case studies

### V2 — moat: live/in-play + feature engineering depth
- GNN, NLP injury, feature store are **engineering moats** — not IP but hard to replicate without team
- Copycat cost: 18-24 months with 3-person team
- **Protection:** accumulated feature library (by V2 we have 2000+ features across sports and markets — nobody starts there)

### V3 — moat: research credibility + patents + customer lock-in
- Whitepaper + OSS + academic citations are **credibility moats** (clubs/funds prefer proven methodology)
- Patent filings (CLV methodology, hierarchical calibration, portfolio Kelly with shrinkage) — **[HIPOTEZA]**: patent enforcement in sports betting is practically weak, but patents as marketing and defensive tools help
- Customer lock-in via historical data integration (they migrate, they lose history)
- Copycat cost: impossible in <3 years once V3 is mature with 20+ customers and case studies

---

## Exit / acquisition considerations

### Who might acquire SportsLab at V2-V3

- **Stake / DraftKings / Flutter Entertainment:** tuck-in acquisition for B2B data feed. Price range: €5-15M depending on MRR and growth. Their margin is already thin; they buy to prevent us from being the next category leader.
- **Sportradar / Stats Perform (if they notice us):** defensive acquisition. They'd pay more (€10-30M) because we threaten their lower-tier product, but probably wouldn't integrate well.
- **Betfair / Pinnacle:** less likely — they're markets, not data-layer plays.
- **ESPN / Athletic-type media:** for data licensing + editorial differentiation. Longer sales cycle.
- **Private equity (sports-focused like RedBird Capital):** roll-up strategy.

### IP to protect pre-exit

1. **Proprietary data sources** — exclusive relationships with 2-3 bookmakers for odds data (even informal)
2. **Calibration methodology** — keep hierarchical Bayesian formalism documented but parameters proprietary
3. **Customer list** — 20+ B2B customers is more valuable than any model
4. **Historical CLV track record** — 5 years of honest CLV reporting is irreproducible

### What to do with IP as V3 approaches

- **File provisional patents** (month 36+) on specific novel methods (CLV + hierarchical calibration combo). Cost €5-15k each. Defensive value.
- **Trademark** "SportsLab" + any product names globally by V2 (€2-5k)
- **Trade secrets** over patents for model weights + feature recipes — patents make them public.
- **Founder equity structure:** if taking investment in V1-V2, preserve ability to walk away with IP if acquirer undervalues. Anti-dilution + board seat matter.

### Red flag: **don't build for acquisition from day 1**

The product-market-fit signal in V1-V2 matters more than acquisition optionality. Every phase reviewer (founder + DrMat + architect + code-reviewer) should ask: "does this serve paying customers first, or exit narrative first?" If the latter, cut it.

---

## Summary — strategic recommendations

### What this roadmap bets on

1. **Discipline over sophistication.** LGBM + good calibration + honest CLV beats fancy architecture shipped sloppy.
2. **Expand before optimize.** Multi-sport in V1 over deep-learning in V1. Platform story > model story for B2B.
3. **Revenue-gated complexity.** V2 and V3 only happen if B2B revenue materializes. If not, we stay at V1 + refinement.
4. **Kill experiments fast.** 20 of 30 experiments in this roadmap will not work as expected. Bailout criteria are mandatory, not optional.

### Three "bet the farm" moments where bad decisions kill the company

See the final report section below for details.

### Where this diverges from `ideas/phase_*` original plans

- `solo_founder_roadmap.md` says "R5 expansion after R4 automation." I say: **Beta→V1 transition (Dixon-Coles, auto-retrain, 10 leagues) should ship before V1 multi-sport** because goal-based markets are where the easy wins are, and multi-sport is a platform bet not a model bet.
- `phase_4_more_sports/overview.md` promises 3 sports in 20-32 weeks total. I'm allocating 8 months (month 14-22) for 3 sports + hierarchical calibration + first revenue — realistic for solo founder + Claude Code.
- `phase_2_new_features/research_backlog.md` RB-17 (Transformer) listed for P3-P4. I push to V2→V3 (month 36-42) because tree ensembles should be exhausted first.

### Where DrMat will push back (flagged explicitly)

- **Bayesian Kelly deferral through Alpha + conditional on variance quality.** DrMat's §4.3 math is right; my concern is bagging variance ≠ Bayesian posterior variance. Need empirical validation before committing.
- **Hierarchical Bayesian calibration in V1, not Beta.** DrMat may want it earlier. My argument: per-league with pool-fallback (Beta) is simpler, validates concept before adding hierarchy.
- **Transformer sequence models skeptical placement (V2→V3).** DrMat may want earlier. My argument: tree models aren't saturated, transformers need lots of data, our match-count is low.

---

**Document status:** Draft v1 — intended for founder review + DrMat review + architect review. Expect 2-3 iterations before locking.

**Next steps (for founder):**
1. Read end-to-end with an eye for the three "bet the farm" moments (below in raport)
2. Choose whether to commit to V1 timeline (month 14-22) or treat V1 as "we'll see"
3. Commission DrMat review specifically of calibration evolution (Alpha → V3)
4. Commission architect review of infrastructure evolution + cost scaling

**Next steps (for mleng, if signed off):**
1. Start Alpha Hardening workstreams (AH-1 to AH-4) per month 2-4 schedule
2. Build experiment tracking template in MLflow that supports phase-tagged runs (`phase=alpha_hardening`, `phase=beta`, etc.) for longitudinal analysis
3. Create `experiments/beta_ensemble.yaml` shell (not runnable yet — documents the planned Beta architecture for future self)
