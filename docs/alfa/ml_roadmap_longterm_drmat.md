# ML Research Roadmap Long-Term — DrMat

**Author:** DrMat (math/stats authority)
**Date:** 2026-04-22
**Scope:** 24-month mathematical research program. Alpha is baseline; this document is what comes after.

---

## 1. TL;DR — 15 research highlights across phases

1. **[PEWNE]** Alpha closed the calibration question for ≤3-class football: Dirichlet with temperature fallback, ECE ≤ 0.05 with bootstrap CI. All further research is meta-calibration (conditioning on context), not base-calibration.
2. **[HIPOTEZA]** Beta's headline bet: **hierarchical Bayesian calibration** with a shared prior across leagues. Expected ECE drop 0.005-0.010 on low-volume leagues (Tier-2 with n_val < 1000). Foundation: Kull 2017 + Gelman partial-pooling.
3. **[HIPOTEZA]** Beta's portfolio bet: **Bayes-corrected Kelly** with 10× bagging for predictive variance. Expected log-growth gain +5-15% at equal drawdown. Foundation: §4.3 of the alpha draft, MacLean-Ziemba-Thorp 1992.
4. **[HIPOTEZA]** V1's calibration bet: **neural (MLP) calibrator conditioned on meta features** (raw_p, market, league, minutes-to-kickoff, odds-move-since-open). Expected ECE 0.02 → 0.010 when meta features carry signal; redundant with Dirichlet otherwise. Fallback: conformal prediction.
5. **[HIPOTEZA]** V1's portfolio bet: **full portfolio Kelly** with Ledoit-Wolf covariance shrinkage on simultaneous bets. Expected drawdown reduction 20-30% at equal growth. Foundation: Merton allocation under log-utility + Ledoit-Wolf 2004.
6. **[HIPOTEZA]** V1's goals bet: **Bayesian bivariate Poisson Dixon-Coles in NumPyro**. Expected gain on AH, Correct Score, non-2.5 O/U lines. Foundation: Dixon-Coles 1997, Karlis-Ntzoufras 2003.
7. **[DO SPRAWDZENIA]** V2's calibration bet: **online conformal prediction** giving distribution-free confidence intervals on every pick. Foundation: Vovk 2005, Angelopoulos-Bates 2023.
8. **[DO SPRAWDZENIA]** V2's portfolio bet: **regime-switching Kelly** — detect bear/bull regimes in our own P&L and adapt α ∈ [0.10, 0.25] dynamically. Foundation: Hamilton 1989 Markov-switching.
9. **[DO SPRAWDZENIA]** V2's market bet: **market impact modeling** — how our own bets move the line, Kyle 1985 adapted to betting exchanges.
10. **[DO SPRAWDZENIA]** V3's blue-sky bet: **defensive forecasting (Vovk)** — game-theoretic guarantees against adversarial (steamed) market, worst-case calibration.
11. **[DO SPRAWDZENIA]** V3's blue-sky bet: **multi-task Bayesian** with shared team-quality latent across sports where there is team overlap (rare in our scope; mostly cross-sport features like travel, rest).
12. **[RYZYKO]** Neural calibration, defensive forecasting, causal A/B testing, and in-play real-time updates are the four areas where MLEng will push back hardest on cost. Documented with explicit bailout criteria.
13. **[PEWNE]** Infrastructure evolution is mandatory: scipy → Pyro (Beta) → NumPyro/JAX (V1) → Stan for batch + NumPyro for online (V2). Without this, V1-V3 stays theoretical.
14. **[HIPOTEZA]** Two "white whale" problems where we have a credible shot: (a) **adaptive closing-line inversion** — backing out the book's real vig from movement, and (b) **sport-agnostic calibration transfer** — Dirichlet params learned on football priors for tennis/basketball cold-start.
15. **[RYZYKO]** Patent strategy is realistic only for the *composition* (Hybrid Calibrated Portfolio Kelly pipeline) in the US; each individual component (Dirichlet, Kelly, Ledoit-Wolf) is prior art. Per-component patents in the EU are unrealistic.

---

## 2. Theoretical foundation — math backbone per phase

| Phase | Core math | Key references | Tools |
|---|---|---|---|
| **Alpha** | Proper scoring rules, fractional Kelly, walk-forward CV, DeLong, BH-FDR | Murphy 1973; Kelly 1956; Thorp 1997; DeLong 1988; Benjamini-Hochberg 1995; Guo 2017; Kull 2017, 2019 | scipy, sklearn, lightgbm, manual calibration |
| **Beta** | Hierarchical Bayesian, empirical Bayes shrinkage, bagged predictive variance, DC bivariate Poisson | Gelman-Hill 2006; Dixon-Coles 1997; Karlis-Ntzoufras 2003; MacLean-Ziemba-Thorp 1992 | Pyro (PyTorch), pymc as backup |
| **V1** | Portfolio Kelly with covariance, neural calibration, variational inference, Ledoit-Wolf | Merton 1969; Ledoit-Wolf 2004; Kull 2019 (extended); Blei-Kucukelbir 2017 | NumPyro + JAX, optax, flax |
| **V2** | Online conformal prediction, regime-switching, sequential testing (SPRT), multi-armed bandits, Kyle 1985 | Vovk-Gammerman-Shafer 2005; Angelopoulos-Bates 2023; Hamilton 1989; Wald 1945; Lai-Robbins 1985; Kyle 1985 | NumPyro online + Stan batch, ecos/cvxpy for portfolio QP |
| **V3** | Defensive forecasting, normalizing flows, causal inference, value-of-information | Vovk 2001, 2007; Rezende-Mohamed 2015; Pearl 2009; Howard 1966 | Custom JAX ops, pyro+normflows, DoWhy |

**[PEWNE]** The progression is deliberate: each phase's math is a conservative extension of the previous phase's validated results. Never adopt a method whose *baseline* (previous-phase equivalent) is not already shipped and honest.

**[RYZYKO]** The biggest cost is infrastructure transitions. Pyro → NumPyro rewrite is ~3 weeks of MLEng time. Stan integration is another 2 weeks. Budget these before committing to the roadmap.

---

## 3. Alpha research — what we've validated (closed)

### 3.1 Closed questions

| Question | Answer | Reference |
|---|---|---|
| Training objective for 1X2/OU/BTTS | Log-loss (strictly proper, decomposable) | Murphy 1973 |
| Calibration for 1X2 | Dirichlet when n_val ≥ 2000, temperature scaling fallback | Kull 2019 |
| Calibration for binary (OU/BTTS) | Beta when n_val ≥ 500, Platt fallback | Kull 2017, Platt 1999 |
| Per-class binary Platt for 1X2 | **Forbidden** — breaks propriety | derivation in alpha draft §2.2 |
| Per-league calibration | Deferred (curse of dim: n_val ≈ 16 per group) | alpha draft §2.3 |
| CV strategy | Walk-forward expanding, 7-day embargo, ≥3 folds | alpha draft §3.1 |
| K-fold on time-series | Cardinal sin, banned in CI | — |
| Multiple testing correction | BH-FDR at q = 0.1 | Benjamini-Hochberg 1995 |
| Kelly fraction | α = 0.25 with ECE-dampening, per-match 3% / per-round 10% / per-league 15% / total 25% | Thorp 1997, MacLean-Ziemba-Thorp 1992 |
| Full Kelly α = 1.0 | **Forbidden** — ruin probability 95% in 1000 bets | derivation in alpha draft §4.1 |
| Hero metric | CLV (unbiased, 10× lower variance than ROI) | Levitt 2004, Forrest-Simmons 2008 |
| Min n_bets for CLV claim | 500 (one-sided 95% CI, σ = 0.07) | alpha draft §3.2 |

### 3.2 Explicit deferrals (addressed in Beta)

- Bayesian posterior Kelly via bagging
- Dirichlet per-league (wait for n_league ≥ 500)
- Dixon-Coles goals model
- Weekly retrain cadence
- Full covariance shrinkage

### 3.3 Meta-lessons from alpha

- Temperature scaling is a *floor*, not a ceiling. Ship temp even when Dirichlet is primary.
- Bootstrap CI on ECE non-negotiable; point ECE reporting on n < 2000 is misleading.
- Engineering-math compromise: heuristics (ECE-dampening) acceptable for alpha but must be flagged in code with "HEURISTIC — see drmat §X" + Linear issue for replacement.

---

## 4. Beta research program (3-6 months post-alpha)

**Timeline:** ~July-October 2026. Infrastructure: add Pyro (PyTorch-based probabilistic programming).

### 4.1 Hierarchical Bayesian calibration

**Hypothesis:** Shared prior across leagues outperforms per-league independent calibrators on low-n leagues, matches high-n.

**Formal statement:**
```
For each league l ∈ {1..14}:
  θ_l ~ N(μ, τ²)
μ ~ N(μ_0, σ_0²)
τ ~ HalfCauchy(1)
y_l | θ_l ~ Dirichlet-Multinomial(softmax(θ_l · z_l))
```

**Success:** ECE per league CI upper ≤ 0.06 on n_val ∈ [200, 500]; no regression on high-n leagues; log-loss +0.002 BH-adjusted.

**Failure response tree:**
- τ → 0 → degenerates to pooled, OK
- τ blows up → pooled fails, use independent + fallback
- VI convergence slow → NUTS (PyMC) for 14-league small problem
- Theoretically hopeless → **empirical Bayes James-Stein shrinkage** (closed-form, no MCMC)

**Bailout:** >8 weeks, 0.5 FTE-month, 2 retrainings underperforming pooled → ship per-market Dirichlet, document, re-open when n_league ≥ 2000 for all.

### 4.2 Bayes-corrected Kelly via bagging

**Hypothesis:** `f*_Bayes = f*_point × (1 − Var(p)/(p(1-p)))` beats ECE-dampening by 5-15% log-growth at equal drawdown.

**Formal statement:**
```
Given LightGBM bagged predictions p̂_1...p̂_10:
  p̂ = mean
  Var(p̂) = sample variance
  correction = max(0, 1 − Var(p̂) / (p̂·(1−p̂)))
  f*_Bayes = f*_point · correction · α  (α = 0.25)
```

**Success:** Walk-forward log-growth +5% at equal drawdown; Sharpe +10%; stable across folds.

**Failure response tree:**
- LGBM variance too small → MC Dropout equivalent (feature_fraction/bagging_fraction at inference)
- Correlation wrong → Bayesian Neural Net with informative prior
- Theoretically hopeless → keep ECE-dampening (acceptable alpha floor)

**Bailout:** >10w no Sharpe improvement; Pi inference >10s; 3 consecutive "ECE-dampen matches or beats" → document and keep ECE-dampen.

### 4.3 Bayesian Dixon-Coles for AH, O/U, Correct Score

**Hypothesis:** Bayesian bivariate Poisson DC with hierarchical team-quality priors outperforms independent Poisson on non-1X2 markets.

**Formal statement:**
```
y_home_i ~ Poisson(λ_home_i), y_away_i ~ Poisson(λ_away_i)
log(λ_home) = α_0 + α_h − δ_a + home_advantage
log(λ_away) = α_0 + α_a − δ_h
α, δ ~ N(0, σ²);  σ ~ HalfCauchy(2.5)
DC correction: P(y_h, y_a) *= τ(y_h, y_a; ρ)
ρ ~ N(-0.1, 0.05²)
```

**Success:** Log-loss on AH beats LightGBM baseline −0.003 DeLong p<0.05; CS log-loss beats Poisson-independent −0.005; HDI coverage matches empirical within 2pp.

**Failure response tree:**
- MCMC too slow → VI (AutoGuide)
- VI underestimates variance → SVGD
- λ_3 not identified → drop bivariate, keep DC correction only
- Theoretically hopeless → frequentist DC with James-Stein + ClubElo priors

**Bailout:** >12w no beat-baseline on any non-1X2 market; training >8h per retrain; 3 seasons of underperformance.

### 4.4-4.7 Shorter directions

**§4.4 CRPS per market** — hypothesis that continuous-ranked probability score beats line-binarized log-loss for generic OU lines. Bailout 6w, not committed (research spike).

**§4.5 SPRT for online A/B** — Wald 1945 sequential testing terminates model comparisons early. Bailout 6w on implementation reliability.

**§4.6 ECE variance/power analysis** — diagnostic study; always produces answer. OU/BTTS should hit ≤0.04 (tighter than 1X2 0.05) on n_val ≥ 500.

**§4.7 Empirical cluster constraints** — Ledoit-Wolf on bet correlation matrix → hierarchical clustering. Bailout 6w if clusters unstable or obvious; keep (league, date) heuristic.

---

## 5. V1 research program (6-12 months post-alpha)

**Timeline:** ~Nov 2026 - May 2027. Infrastructure: Pyro → NumPyro (JAX backend), add optax + flax.

### 5.1 Neural meta-calibration

**Hypothesis:** MLP calibrator conditioned on `(raw_p, market, league, minutes_to_kickoff, odds_move_since_open, day_of_week, n_matches_same_round)` drops ECE from ~0.02 (Dirichlet) to ~0.010.

**Formal statement:**
```
z = MLP(raw_logits, meta_features)  # 2-layer, hidden 64
p_cal = softmax(z)
L = cross_entropy + λ · ECE_penalty  (λ = 0.1)
```

**Success:** ECE < 0.012 with CI upper ≤ 0.015; log-loss +0.01 BH-adjusted; segment-uniform calibration.

**Failure response tree:**
- Overfits → L2 + dropout + smaller network
- No improvement over Dirichlet → audit meta features via SHAP on calibrator
- Destructive interference → redundant with Dirichlet
- Theoretically hopeless → **PIVOT to conformal prediction (V2 §6.1)**

**Bailout:** >12w no stable improvement; >1 FTE-month; 3 consecutive no-signal experiments → retain Dirichlet + temperature.

### 5.2 Portfolio Kelly with Ledoit-Wolf covariance

**Hypothesis:** Merton allocation with LW-shrunk Σ beats diagonal + per-cluster heuristic by 10-20% risk-adjusted log-growth.

**Formal statement:**
```
f* ≈ Σ̂⁻¹ μ / (1 + f*ᵀμ)
Σ̂ = (1 − δ) Σ_sample + δ · tr(Σ)/N · I  (Ledoit-Wolf)
Subject to: f_i ≥ 0, Σf_i ≤ 0.25, f_i ≤ 0.03
```

**Success:** Risk-adjusted log-growth +15%; max drawdown ≤ baseline; turnover ≤ 2×.

**Failure response tree:**
- Σ noisy at n~1000 → graphical lasso (sparse precision)
- Operational friction → sequential once-daily optimization
- Theoretically hopeless → diagonal + per-cluster heuristic

**Bailout:** >10w no Sharpe improvement; QP solver instability.

### 5.3 Variational inference for Bayesian neural calibration

**Hypothesis:** BNN calibrator (mean-field VI) gives better-calibrated uncertainty than deterministic MLP + bagging, enables direct Bayes-corrected Kelly.

**Formal statement:**
```
q_φ(W) = Π_i N(μ_i, σ_i²)  (mean-field Gaussian)
L_ELBO = E_q[log p(y|x,W)] − KL(q || p_W)
Predictive: p(y|x) ≈ (1/K) Σ p(y|x, W_k), K=50 MC samples
Var(p) = variance over MC samples
```

**Success:** ECE comparable to §5.1 deterministic (within 0.003); 90% predictive interval empirical coverage ≥ 88%; Kelly +5% vs bagged-variance.

**Failure response tree:**
- Mean-field too tight → SVGD (Liu-Wang 2016)
- Still inadequate → **Laplace approximation** (Daxberger 2021, laplace-torch)
- Theoretically hopeless → 10× deterministic MLP ensemble

**Bailout:** >10w without calibrated posterior variance; Pi inference >5s.

### 5.4-5.7 Shorter directions

**§5.4 CRPS for joint goals** — extends §4.4 Beta to bivariate Poisson with energy score. Single model win on ≥4 of 7 markets. Bailout 10w.

**§5.5 MAB Thompson sampling for model A/B** — adaptive allocation to better model. Cumulative regret ≤30% of fixed A/B. Bailout 8w.

**§5.6 Conformal prediction baseline** — bridge to V2. Split-conformal with 90% coverage, efficient sets for 1X2 ≤1.5 avg. No hard bailout (exploratory).

**§5.7 CLV decomposition** — selection vs timing vs model-edge components. Diagnostic, always produces output.

---

## 6. V2 research program (12-18 months, exploratory)

**Timeline:** ~May-Nov 2027. Infrastructure: add Stan (batch) + custom JAX.

### 6.1 Online conformal prediction (ACI)

Adaptive Conformal Inference (Gibbs-Candes 2021) maintains coverage under regime shift.

**Formal:**
```
α_{t+1} = α_t + γ · (1{y_t ∉ C_{α_t}(x_t)} − α)
```

Success: within 2pp nominal coverage over 1 year; intervals bounded.

**Bailout:** >12w no reliable online deployment.

### 6.2 Regime-switching Kelly

Hamilton 1989 HMM with α ∈ [0.10, 0.25] adapted to bull/bear P&L regimes.

Success: max drawdown ≤70% of fixed-α; log-growth within 5% of fixed.

**Failure response:** α_t diverges → EWMA as simpler heuristic.

**Bailout:** >8w no stable regime detection; whiplash from false regime changes.

### 6.3 Causal A/B testing (diff-in-diff)

Card-Krueger 1994 DiD for interventions confounded with market-wide changes.

**Failure response:** Parallel trends violated → synthetic control (Abadie 2010).

**Bailout:** >8w no implementable treatment assignment.

### 6.4 Market impact modeling

Kyle 1985 adapted: λ from `Δp = λ · (Volume_us / Volume_total) + ε`.

**Failure modes:** Our volume too small → λ unidentifiable, document and spread across books.

**Bailout:** λ not statistically different from 0 after 2000 bets.

### 6.5 Adversarial calibration against steamed lines

Detector `z_steam = odds_move_5min / historical_vol > k`; when steamed, shrink p toward p_close, τ=0.5 on Kelly.

Success: CLV on steamed bets non-negative; non-steam unchanged.

### 6.6 Value-of-information for features

Howard 1966 VoI upper bound via mutual information. Rank features before engineering investment.

### 6.7 Normalizing flows for flexible posteriors

Neural Spline Flows (Durkan 2019) for multimodal/heavy-tailed team-strength posteriors.

Success: ECE drop >0.005 vs mean-field VI; Kelly +3% log-growth.

---

## 7. V3 research program (18-24 months, blue sky)

**Timeline:** ~Nov 2027 - May 2028. 50% bailout rate expected — success = "found one that moves the needle".

### 7.1 Defensive forecasting against adversarial markets

Vovk 2001, 2007 minimax regret. Likely vacuous operationally at our scale — keep as marketing narrative, not trading strategy.

### 7.2 Multi-task Bayesian across sports

Shared team-quality latent across football/tennis/basketball. Faster cold-start.

**White whale potential:** calibrator shape-parameters transfer even if model-level doesn't.

### 7.3 Causal inference for team strength

Pearl 2009 SCM on lineup/manager changes. B2B value: clubs ask counterfactuals.

**Failure modes:** Unmeasured confounders (coaching ↔ lineup quality).

### 7.4 Information asymmetry modeling (PIN)

Easley-O'Hara 1987 on betting exchange order book. Depends on exchange data access.

**Likely bailout** without quality order-book data.

### 7.5 Counterfactual odds

Inverse problem: solve for bookmaker's utility function rationalizing historical odds. Theoretical ceiling on CLV.

**Likely bailout** — non-identifiability common.

---

## 8. Academic publication pipeline

Every 6 months, publish something.

### Paper 1 (Beta end) — "Hybrid Calibrated Portfolio Kelly for Sports Betting"

- Target: arXiv → ICML/NeurIPS 2027 workshop
- Novelty: Dirichlet > per-class-Platt empirical demonstration; ECE-dampening → Bayesian Kelly bridge; portfolio constraint set tailored for betting
- Length: 15-20 pages

### Paper 2 (V1 end) — "Meta-Calibration with Market Context"

- Target: AISTATS 2028 / ICLR workshop
- Novelty: market-observable meta features for calibration conditioning

### Paper 3 (V2 end) — "Online Conformal Prediction for Adversarial Prediction Markets"

- Target: UAI 2028 / NeurIPS workshop
- With academic collaborator

### Paper 4 (V3 end) — "Multi-Task Bayesian Across Sports"

- Target: ICML 2028 main track (aspirational)

---

## 9. Patent landscape

### Realistic (US)

| Concept | Patentability | Cost |
|---|---|---|
| Hybrid Calibrated Portfolio Kelly pipeline (composition) | Moderate | $500-2000 provisional, $15-20k non-provisional |
| Neural calibrator conditioned on market meta features | Moderate | Medium |
| Steam-line detector + robust calibration | Moderate | Medium |
| Multi-sport shared-prior calibration | Moderate | Medium |

### Not patentable (prior art)

Dirichlet, Kelly, Ledoit-Wolf, Conformal prediction, Temperature scaling, Bradley-Terry, Dixon-Coles.

### EU reality

Software as such not patentable (EPC 52). Strategy: trade secrets + copyright.

### Strategic recommendation

- Year 1: **no patents**
- Month 12: one US provisional (Beta validated pipeline)
- Month 24: one US non-provisional (V1 full pipeline + neural calib)
- Zero EU patents
- Budget: ~$25k over 24 months, marketing+defense expense

**[RYZYKO]** Patents produce minimal licensing revenue in this space. Treat as defensive signal, not income.

---

## 10. Collaboration strategy

### Target academic partners

| Institution | Why |
|---|---|
| **Bristol — Flach group** | Kull 2017/2019 calibration canon |
| **Edinburgh — Storkey** | VI, normalizing flows |
| **ETH Zurich — Buhmann** | Multi-task learning |
| **Warwick** | Bayesian DC (Baio/Groll) |
| **Cambridge CMS** | Market microstructure V2 |
| **SGH Warszawa / AGH** | Local MSc thesis pipeline |

### What we offer

Datasets (anonymized), compute spare, real-world validation, co-authorship.

### What we ask

Formal review pre-submission, hiring pipeline, credibility in sales, IP assignment clauses pre-signed.

### Anti-patterns

- Give away too much data (share derived aggregates only)
- Commit without IP strategy
- Academic distraction (esoteric methods that don't ship)

---

## 11. Failure register (master index, bailout + pivot per direction)

### Beta

| Direction | Bailout | Pivot |
|---|---|---|
| §4.1 Hierarchical calib | 8w, 0.5 FTE-month | James-Stein shrinkage |
| §4.2 Bayes-corrected Kelly | 10w no Sharpe | MC Dropout; ECE-dampen retained |
| §4.3 Bayesian DC | 12w no beat-baseline | Frequentist DC + ClubElo priors |
| §4.4 CRPS per market | 6w no improvement | Skip (log-loss per market fine) |
| §4.5 SPRT | 6w implementation | Fixed walk-forward |
| §4.6 ECE power | N/A diagnostic | Retain alpha targets |
| §4.7 Empirical clusters | 6w no beat | (league, date) heuristic |

### V1

| Direction | Bailout | Pivot |
|---|---|---|
| §5.1 Neural calib | 12w, 1 FTE-month | Conformal (V2) |
| §5.2 Portfolio Kelly LW | 10w no Sharpe | Diagonal heuristic |
| §5.3 Bayesian NN VI | 10w miscalibrated | Laplace or deep ensemble |
| §5.4 CRPS joint goals | 10w no dominance | Specialist per-market |
| §5.5 MAB A/B | 8w implementation | Fixed A/B |
| §5.6 Conformal baseline | No hard bailout | — |
| §5.7 CLV decomp | Diagnostic | — |

### V2

| Direction | Bailout | Pivot |
|---|---|---|
| §6.1 Online conformal | 12w no deployment | Static split-conformal, monthly refresh |
| §6.2 Regime Kelly | 8w no stable detection | EWMA α heuristic |
| §6.3 Causal DiD | 8w no protocol | Standard A/B |
| §6.4 Market impact | λ non-significant after 2000 bets | Spread across books |
| §6.5 Adversarial cal | Steam detector noisy | Skip; accept tail risk |
| §6.6 VoI features | Diagnostic | Retrospective ranking |
| §6.7 Normalizing flows | 10w no posterior improvement | Mean-field VI |

### V3

At V3, ~50% bailout expected. Success = one direction moves needle, not all.

---

## 12. Math infrastructure evolution

### Stack per phase

| Phase | Primary | Secondary |
|---|---|---|
| Alpha | scipy, sklearn, lightgbm | numpy, pandas |
| Beta | Pyro (PyTorch) | Stan option for small hierarchical |
| V1 | NumPyro (JAX) | Pyro for non-critical experiments |
| V2 | NumPyro + Stan + custom JAX | Pyro sunset |
| V3 | Custom JAX library | Pyro prototyping |

### Transition costs

- scipy → Pyro: 3 weeks
- Pyro → NumPyro: 3 weeks
- V1 → V2 Stan: 2 weeks
- V3 custom lib: 6-12 weeks (only if IP requires)

### Observability

- MCMC diagnostics (R-hat, ESS) per retrain, alert R-hat > 1.05
- VI ELBO convergence monitoring
- Per-fold calibration method selector wins → IP metadata
- Kelly posterior variance distribution drift alerts

### Reproducibility

- Fixed seeds for all published experiments
- Version pins for NumPyro/Stan/JAX
- MLflow logs include infra versions
- uv.lock committed; no floating deps

---

## 13. Intellectual property considerations

### Open strategy (publish publicly)

- Mathematical formulations (Hybrid Calibrated Portfolio Kelly)
- Theoretical derivations (Kelly with edge uncertainty)
- Benchmark datasets (anonymized)
- Evaluation protocols (walk-forward, BH-FDR, bootstrap CI)
- Papers on arXiv + venue submissions

**Why:** priority, credibility, hiring/B2B signal.

### Closed strategy (keep secret)

- Exact hyperparameters per league × market × season
- Specific feature engineering (top 45 of 935)
- Bet-placement protocols + bookmaker account mgmt
- Calibration selector empirical learnings
- Data access details (scraper strategies, API tokens)

### Open-source pieces (marketing)

- `sportslab-probabilistic-utils` — ECE bootstrap, BH-FDR, walk-forward splitter
- Pre-trained calibrator weights (hobbled — closed 2020-2022 only)
- Notebook tutorials replicating key paper figures

### Anti-patterns

- Over-publishing (don't give away revenue pieces)
- Fake openness (missing essential config)
- Copyleft licenses (MIT/Apache 2.0 only)

### Competitive intelligence

- Stats Perform, Opta, Pinnacle: internal research, don't publish → we will strategically
- FiveThirtyEight: methodology open, models closed → good template
- ClubElo: formula open, real-time data closed → good template

---

## 14. Hiring blueprint

| Phase | Hire | Seniority |
|---|---|---|
| Alpha | None (founder + subagents) | — |
| Beta | PhD stats/applied math | 0.5-1 FTE, PostDoc or PhD + 2-3y industry |
| V1 | Senior ML engineer (Bayesian/VI) | 5+y |
| V1 | PhD stats full-time | — |
| V2 | PhD optimization/stochastic control | Specialist |
| V2 | Sr MLOps engineer | 5+y |
| V3 | ML researcher (shared w/ academic) | PhD + publications |
| V3 | IP lawyer (part-time) | — |

### Anti-hires

- Generalist data scientists (will re-solve alpha problems)
- ML engineer w/o Bayesian exposure (screening fail for Beta+)
- Full-stack engineers for math work (separate concerns)

### Collaborate vs hire

- **Hire:** Beta calibration, V1 neural calibration, V2 regime Kelly — product-critical, time-pressured
- **Collaborate:** V2 online conformal, V3 multi-task, V3 causal inference
- **Consult (paid advisor, 5-10h/mo):** V2 market impact

---

## Appendix A — Research direction dependency graph

```
Alpha (closed)
  └─► Beta
       ├─► §4.1 Hierarchical Cal  ─► V1 §5.1 Neural Cal
       ├─► §4.2 Bayes Kelly bag  ─► V1 §5.2 Portfolio Kelly LW
       │                              └─► V1 §5.3 Bayesian NN VI
       ├─► §4.3 Bayesian DC      ─► V1 §5.4 CRPS joint goals
       ├─► §4.4 CRPS per market  ─► V1 §5.4 (merged)
       ├─► §4.5 SPRT             ─► V1 §5.5 MAB
       ├─► §4.6 ECE power (diag) ─► V1 §5.6 Conformal baseline
       └─► §4.7 Empirical clusters ─► V1 §5.2 (merged)

V1 ──► V2
  §5.1 ─► §6.5 Adversarial Cal
  §5.2 ─► §6.2 Regime Kelly
  §5.3 ─► §6.7 Normalizing Flows
  §5.6 ─► §6.1 Online Conformal (ACI)
  §5.7 ─► §6.4 Market Impact

V2 ──► V3
  §6.1 ─► §7.1 Defensive Forecasting
  §6.2 ─► §7.4 PIN
  §6.5 ─► §7.5 Counterfactual Odds
  §6.6 ─► §7.3 Causal Inference
                 ─► §7.2 Multi-task (new branch from V1 §5.3)
```

## Appendix B — Key additional references

Alpha refs in alpha draft §8. New for long-term:

- Gelman-Hill 2006 — hierarchical Bayesian
- Karlis-Ntzoufras 2003 — bivariate Poisson
- Baio-Blangiardo 2010 — hierarchical DC for football
- Breiman 1996 — bagging variance decomposition
- Blei-Kucukelbir-McAuliffe 2017 — VI review
- Gal-Ghahramani 2016 — MC Dropout
- Liu-Wang 2016 — SVGD
- Daxberger et al 2021 — Laplace Redux
- Vovk-Gammerman-Shafer 2005 — conformal prediction textbook
- Angelopoulos-Bates 2023 — conformal modern review
- Gibbs-Candes 2021 — ACI
- Hamilton 1989 — regime switching
- MacLean-Ziemba-Zhao 2011 — dynamic Kelly
- Wald 1945 — SPRT
- Thompson 1933 — Thompson sampling
- Kyle 1985 — microstructure
- Easley-O'Hara 1987 — PIN
- Pearl 2009 — causality
- Howard 1966 — value of information
- Rezende-Mohamed 2015 — flow VI
- Finn-Abbeel-Levine 2017 — MAML

## Appendix C — Semi-annual delivery checklist

Every 6 months:
- [ ] On track for current phase direction?
- [ ] Any bailout criterion hit? Documented?
- [ ] New external research (arXiv scan) to add?
- [ ] Academic collaborations active? Papers submitted?
- [ ] Patent filings on track (1 per 12 months from Beta)?
- [ ] Infrastructure migration on schedule?
- [ ] Hiring aligned with phase?

---

## White whale problems (deeper dive)

### 1. Adaptive closing-line inversion

**Problem:** Bookmakers apply a vig (margin) but publish only final odds. Recovering true implied probability lets us:
- Know sharp-money's true estimate
- Detect steamed lines more precisely
- Sell "fair odds" as B2B product

**Why we can:** We log opening + closing odds and in-between snapshots for 14 leagues. Academic literature (Levitt 2004, Forrest-Simmons 2008) confirms closing odds efficient but treats vig as static. Combining time-series with state-space modeling (Kalman filter on implied prob + vig) is non-trivial but tractable.

**Why no one has:** Most academic papers use aggregated data; commercial books keep vig internal. We have both data and math incentive.

### 2. Sport-agnostic calibration transfer

**Problem:** When adding tennis (P4.1), we start with zero calibration data. Naive approach: 500+ bets to build per-sport from scratch. Better: treat calibration as meta-learning — sports are "tasks".

**Why we can:** 4 sports with same underlying pipeline; structural similarity high (all 2-class or 3-class tasks with similar resolution scales). MAML (Finn 2017) directly applicable.

**Why no one has:** Sports prediction is siloed per-sport; no one builds multi-sport calibration framework. P4 roadmap forces multi-sport infrastructure → we solve it naturally.

**Publication potential:** high, novelty sharp.
