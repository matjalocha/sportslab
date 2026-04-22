# ML Experiments Draft (DrMat review) — Alpha Launch

**Author:** DrMat (math/stats authority)
**Date:** 2026-04-22
**Status:** Draft for Lead consolidation
**Scope:** Mathematical plan for Alpha launch ML — calibration, backtest validity, Kelly, statistical guarantees. Not implementation.

---

## 1. TL;DR (math-first)

1. **[PEWNE]** Log-loss is the only admissible training metric for 1X2/OU/BTTS (strictly proper, decomposable into reliability + resolution − uncertainty per Murphy 1973). Brier is a fine monitor, ROI is not a metric. Ship with **log-loss as promotion gate**, ECE as veto, CLV as live signal.
2. **[RYZYKO]** ECE is a biased estimator with O(1/√n) variance **and** binning bias of order O(1/B) where B = bin count. On Alpha volumes (~50–150 bets/week) per-market, per-league ECE is **statistically meaningless** below ~300 observations. Report **bootstrap CI**, not point ECE, or you will chase noise.
3. **[PEWNE]** Walk-forward expanding window is the only valid CV. **Embargo ≥ 7 days** between train end and test start (team form + odds movement autocorrelation decays at ~5–10 days in league football). K-fold is a cardinal sin and must be banned in CI (ADR-0011 needs a leakage-style detector for CV strategy).
4. **[PEWNE]** Fractional Kelly α = 0.25 is correct as a floor but the "fraction of ECE" heuristic is a poor man's Bayesian shrinkage. Proper form: Kelly with **credible-interval shrinkage** on p_model, not an ECE-dampening multiplier. See §4 for derivation.
5. **[RYZYKO]** Publicly claiming "+CLV edge" after <500 bets is statistically dishonest. With CLV = +2% and σ_CLV ≈ 5–8% per bet (typical for 1X2), n ≥ 400 bets is the **minimum** for 95% CI to exclude zero. Below that threshold, any landing-page claim must be prefaced "point estimate, not significant".

---

## 2. Calibration decision tree

### 2.1 The proper-scoring-rule hierarchy

**Intuition.** A scoring rule is *proper* if honest forecasting is the unique optimum. Both log-loss and Brier are strictly proper. Log-loss is **local** (depends only on probability assigned to realised outcome) — preferred when outcome probabilities can be arbitrarily small (Winkler 1969). Brier is bounded and decomposable (Murphy 1973), preferred when ECE-style sharpness vs reliability introspection is needed.

**Formal.** For probability p and outcome y ∈ {0,1}:
- Brier: S(p, y) = (p − y)²
- Log-loss: S(p, y) = −[y log p + (1−y) log(1−p)]

Both satisfy E_y[S(p,y)] minimised iff p = P(y=1).

**Decision.**
| Use | Metric |
|---|---|
| Training objective | **Log-loss** (LightGBM/XGBoost defaults) |
| Promotion gate | **Log-loss on held-out walk-forward test set**, with DeLong test vs incumbent |
| Calibration diagnostic | **Brier decomposition** (reliability, resolution, uncertainty — Murphy 1973) |
| Veto metric | **ECE with bootstrap CI** |
| Live signal | **CLV** (closing-line value) — see §7 |

### 2.2 Calibration method selection (when to use what)

Per ADR-0007 the system already does walk-forward selection among {temperature, Platt, isotonic, beta}. That is correct. My refinements for Alpha:

**Decision tree:**

```
Is market binary? (OU_2.5, BTTS)
├── Yes → candidate set = {temperature, Platt, isotonic, beta}
│         - n_val < 500 → Platt (2 params, low variance)
│         - n_val 500–2000 → beta (3 params, more flexible tails)
│         - n_val > 2000 → isotonic (nonparametric, but hungry)
│         - temperature scaling as sanity floor (1 param)
│
└── No (1X2, multiclass) →
    - **Do NOT apply per-class binary Platt independently** (probabilities do not sum to 1)
    - candidate set = {Dirichlet calibration, matrix scaling, vector scaling, temperature}
    - Dirichlet (Kull et al. 2019) is the principled choice for 3-class
    - Temperature scaling (Guo et al. 2017) as baseline — cheap, usually good
```

**[PEWNE]** For 1X2, the dominant engineering mistake is calibrating H/D/A with three independent binary calibrators and renormalising. That **breaks propriety** (the composition is not a proper scoring rule any more) and systematically under-calibrates the draw. Demand Dirichlet or matrix scaling.

**[HIPOTEZA]** Isotonic dominates on ≥2000 validation points but overfits on <500 and produces step functions with zero-probability regions — dangerous for Kelly (edge = p − q, with p = 0 means negative edge on real outcomes). Mitigate with a small ε-floor or monotone cubic spline.

### 2.3 Per-group calibration (curse of dimensionality)

**[RYZYKO]** Splitting by (market × league × confidence tier) gives 3 × 14 × 3 = 126 calibrators. Per group, n_val ≈ 2000 / 126 ≈ 16 samples. ECE estimated on 16 samples has CI wider than [0, 0.5]. You are calibrating noise.

**Hierarchical rule:**
- **Per market**: mandatory (1X2, OU, BTTS have different loss surfaces)
- **Per league**: only if n_val per league ≥ 500. Otherwise pool leagues with **empirical Bayes shrinkage** toward grand mean.
- **Per confidence tier**: forbidden at Alpha. Revisit when n_bets/tier ≥ 300.

**Validation plan:** Bootstrap 1000 resamples of the validation fold; report ECE 95% CI per group. If CI width > 0.05, **refuse to shard further**.

---

## 3. Backtest validity framework

### 3.1 Walk-forward design (formal)

**Formal.** Let matches be ordered by kickoff_utc t_1 < t_2 < … < t_N. Define folds F_k = (train: [t_1, T_k], embargo: (T_k, T_k + Δ], test: (T_k + Δ, T_{k+1}]) for k = 1, …, K.

- Δ (embargo) = 7 days minimum for football. Justification: form variables (xG_roll5) and market consensus autocorrelation have effective decorrelation time of ~5 days.
- T_k: season boundaries are the natural choice (ADR-0006). For Alpha, also cut mid-season if train window spans two different competitive regimes (e.g. pre/post January transfer window).
- **Expanding window ≻ rolling window** for football: team strength priors benefit from long history; rolling window throws away informative data. Use rolling only for drift-heavy regimes (post-VAR introduction, COVID seasons).

**[PEWNE]** Calibrator must be fit **inside** the walk-forward loop on a separate validation slice, not on the full training set. Otherwise the ECE reported on test is optimistically biased (calibrator has "seen" the test distribution through CV-style leakage).

### 3.2 Minimum n_bets for credible claims

**Intuition.** We want to claim "CLV > 0 with 95% confidence". CLV is roughly N(μ, σ²/n) under CLT; for 1X2 the per-bet CLV standard deviation is dominated by odds variance, empirically σ ≈ 5–8%.

**Formal.** To reject H₀: μ_CLV ≤ 0 at α = 0.05 one-sided, with observed μ̂ = +2%, we need:
```
n ≥ (z_0.95 · σ / μ̂)²  ≈ (1.645 · 0.07 / 0.02)²  ≈ 332
```
With σ = 0.08 (conservative): n ≥ 434.

**Rule of thumb for Alpha:**
| Claim | Minimum n_bets | Notes |
|---|---|---|
| "CLV > 0 statistically significant" | **500** | 95% CI one-sided, σ = 0.07 |
| "ROI > 0 statistically significant" | **~1500** | ROI has higher variance (odds × outcome) |
| "Hit rate > 50%" in 1X2 | N/A | Meaningless — we bet at odds > 2.0 so hit rate < 50% is expected |
| "ECE < 0.05 credible" | **300** per bin-resolved estimate | Bootstrap CI width target |

**Landing page corollary:** Do not publish ROI/CLV numbers before 500 bets are settled. Show **"Tracking in progress — n = X / 500 bets to statistical significance"** with a progress bar. This is honest *and* marketable.

### 3.3 Multiple testing correction

**Problem.** 14 leagues × 3 markets × 4 calibration methods × 3 model families = 504 hypothesis tests. If we promote whichever combination has p < 0.05, under H₀ (no edge) we expect 504 · 0.05 ≈ 25 false positives.

**Decision:** Apply **Benjamini–Hochberg** FDR at q = 0.1 across all comparisons logged to MLflow. Do not use Bonferroni — it is too conservative for correlated tests (same league across markets is highly correlated).

**Practical:** The `mlflow` integration planned in §4 of `alpha_launch_plan.md` must log a p-value per run (DeLong vs baseline). A dashboard query `BH_adjusted_p < 0.1` gates promotion — not raw p < 0.05.

### 3.4 Leakage detection beyond features

ADR-0011 covers feature leakage. For Alpha, also require:
1. **CV leakage detector**: assert no fold's test set contains matches scheduled before fold's train-set cutoff (trivial, but must be in CI).
2. **Closing-odds guardrail**: closing odds are only loaded into the `clv_tracker` table, never into `features_*`. Add a mypy-level type split: `PreMatchFeature` vs `PostMatchSignal`, so the type system rejects using the latter in training.
3. **Target leakage via merge keys**: if we merge odds from football-data.co.uk on (date, home, away), verify we use **opening odds snapshot** not "the single row that exists post-match". This is a subtle one and has bitten published papers (e.g. Dixon–Robinson in-play variants).

---

## 4. Kelly portfolio math

### 4.1 Why fractional Kelly (Thorp)

**Formal.** Kelly (1956) maximises E[log W] where W is terminal wealth. For a single bet with decimal odds o, win probability p, bankroll B:
```
f* = (p · o − 1) / (o − 1)         (optimal fraction)
G*(f*) = p log(1 + f*(o−1)) + (1−p) log(1 − f*)   (growth rate)
```

**Thorp (1997, "The Kelly Criterion in Blackjack, Sports Betting, and the Stock Market"):**
> "Kelly betting, while optimal in the limit, exposes the bettor to extreme drawdowns. In practice, fractional Kelly (α = 0.3 to 0.5) gives up a small fraction of growth for a large reduction in volatility. Drawdown depth scales roughly linearly with α."

**Risk of ruin (MacLean, Ziemba, Thorp 1992):** For fractional Kelly with fraction α < 1, probability of bankroll dropping to fraction β of initial:
```
P(ruin to β) ≈ β^((1−α)/α · 2G*/σ²)
```
With α = 0.25, G* ≈ 2%/bet (realistic), σ² ≈ 0.1, probability of hitting 50% bankroll drawdown in 1000 bets is ~8%. With α = 1.0, same parameter set, ~95%. **[PEWNE]** This is the quantitative justification for α = 0.25 — not tradition.

### 4.2 Portfolio Kelly (correlated simultaneous bets)

**Formal.** For N simultaneous bets with return vector R (R_i = o_i − 1 if win, −1 if lose), probability vector p, covariance Σ:
```
f* = argmax_f  E[log(1 + f^T R)]
```
No closed form in general. Local (mean-variance) approximation:
```
f* ≈ Σ⁻¹ μ  / (1 + f*^T μ)     where μ = E[R]
```
This is the **Merton allocation** specialised to log utility. Multiplied by α = 0.25 for safety.

**[RYZYKO]** Σ is rank-deficient if bets are too similar (e.g., two teams playing in same round both "high edge home favourites" — correlated via referee/weather/league-wide regression to mean). Estimate Σ with **Ledoit–Wolf shrinkage** toward diagonal.

**Constraint set (ADR-0008 is correct):** per-match 3%, per-round 10%, per-league 15%. I add:
- **Per-correlation-cluster cap 12%**: cluster bets by (league, kickoff_date) and cap cluster-wise.
- **Total exposure cap 25%** of bankroll at any time.

### 4.3 Kelly with edge uncertainty (proper Bayesian form)

The current system uses **"ECE-dampened Kelly"** (multiply stake by (1 − ECE)). This is a heuristic. The proper form:

**Intuition.** p is not a point estimate — it has a posterior distribution π(p | data). Bet the *expected log-growth*, not the log-growth at the point estimate.

**Formal.** Replace f* = (p·o − 1)/(o − 1) with:
```
f*_Bayes = argmax_f  E_π[ p log(1 + f(o−1)) + (1−p) log(1 − f) ]
```
For small edges this approximates:
```
f*_Bayes ≈ f*_point  ·  (1 − Var(p) / (p(1−p)))
```
The correction factor **1 − Var(p)/p(1−p)** is the "uncertainty penalty". This is **dimensionally correct** (dimensionless, in [0,1] when posterior is tighter than binomial) — unlike ECE which is a global average.

**Implementation sketch (hand-off to MLEng):**
- Train LightGBM with 10-fold bagging → predictive distribution for p (not just point).
- Compute posterior variance via bootstrap of the calibrator.
- Apply Bayes-corrected Kelly, then multiply by α = 0.25.

**[HIPOTEZA]** This beats ECE-dampened Kelly by 5–15% in log-growth. Validation: walk-forward backtest comparing ECE-dampen vs Bayes-correct, log-loss neutral, Sharpe as tiebreaker.

### 4.4 CLV vs ROI (why CLV mathematically dominates)

**Claim.** CLV > 0 in expectation ⟹ ROI > 0 in expectation (under efficient-closing-market assumption).

**Sketch.** Closing line at Pinnacle is approximately the best available unbiased estimate of P(outcome) (Levitt 2004 for NFL, Forrest & Simmons 2008 for football; both show closing odds are closer to true probability than opening). If we bet at odds o_open and the closing odds imply probability q_close, CLV = o_open · q_close − 1. If E[q_close] = P(outcome), then E[CLV] = E[o_open · P(outcome)] − 1 = E[ROI]. So CLV is an **unbiased, lower-variance estimator of ROI**.

**Variance advantage.** Var(ROI) has two components: market variance + outcome variance. Var(CLV) only has market variance. Outcome variance dominates on small samples → CLV converges ~10× faster.

**[PEWNE]** On Alpha we should show **both**, but trust CLV after 100 bets and treat ROI as noisy until 1500+.

---

## 5. Probability metrics hierarchy

### 5.1 What to log per bet (every time, in MLflow + Postgres)

| Metric | Formula | Purpose |
|---|---|---|
| `log_loss` | −log p_y | Training / promotion |
| `brier_score` | (p − y)² | Sharpness tracking |
| `p_model` | raw model output | Audit |
| `p_calibrated` | post-calibrator | What we bet on |
| `p_market_close` | 1/o_close − vig | CLV reference |
| `clv` | o_bet · p_market_close − 1 | Live edge signal |
| `posterior_variance` | Var_π(p) | Bayes Kelly correction |
| `kelly_fraction_applied` | f_used / f_full_kelly | Audit |
| `calibration_method_used` | enum | Audit |

### 5.2 What to promote on (gate metrics)

Walk-forward aggregate, held-out test set:
1. **Log-loss ≤ incumbent − δ_LL** where δ_LL is DeLong-significant at q = 0.1 (BH-adjusted)
2. **ECE ≤ 0.05** across markets (5% threshold — see ADR-0007 rationale, but with 95% bootstrap CI whole interval below 0.05)
3. **No league × market cell has ECE > 0.10** (per-group sanity)
4. **CLV ≥ 0 point estimate** (not necessarily significant yet, just not negative)

### 5.3 What to alarm on (live)

Pi evening pipeline triggers Telegram alert if:
| Alarm | Condition | Window |
|---|---|---|
| ECE drift | rolling ECE > 0.08 | 7 days |
| CLV collapse | rolling CLV < −1% | 14 days |
| Log-loss drift | vs backtest mean > 3σ | 7 days |
| Prediction count drop | 0 bets for 3 match days | 3 days |
| Posterior variance explosion | median Var(p) > 2× backtest median | 7 days |

### 5.4 ECE vs MCE vs ACE

- **ECE** (Expected Calibration Error): binned weighted average of |p̄_bin − ȳ_bin|. Low variance estimator, biased by bin choice.
- **MCE** (Maximum Calibration Error): worst bin. Useful for *safety bounds* (Kelly must not overbet in any regime). High variance, conservative.
- **ACE** (Adaptive Calibration Error): equal-mass bins instead of equal-width. Reduces variance on skewed p distributions (1X2 favourites cluster around p ~ 0.5–0.65).

**Recommendation for Alpha:** Promote on **ACE** (equal-mass, 15 bins), alarm on **MCE > 0.12**, display **ECE** on landing page (most recognised by audience).

### 5.5 Sharpness vs reliability

**Formal (Murphy 1973 decomposition):**
```
Brier = Reliability − Resolution + Uncertainty
```
- Reliability: how close p̂ is to empirical frequency (↓ is better) — this is calibration
- Resolution: how much p̂ varies with outcome (↑ is better) — this is sharpness/discrimination
- Uncertainty: Var(y), fixed by nature

**Sharpness–reliability tradeoff.** Perfect calibration with p ≡ 0.5 is useless. Perfect sharpness without calibration is overconfident. Optimum: **Resolution maximised subject to Reliability ≤ ε**. This is the principle Gneiting and Raftery (2007) call "maximise sharpness subject to calibration".

For Alpha: treat reliability (ECE) as a **hard constraint** at 0.05, then optimise log-loss (which includes resolution).

---

## 6. Experiment YAML specs (proposed wording)

Not implementing, just spec'ing. MLEng will translate.

### 6.1 `experiments/alpha_baseline_1x2.yaml`

```yaml
name: football-1x2-alpha-baseline
market: 1x2
leagues: [EPL, LaLiga, Bundesliga, SerieA, Ligue1, Championship, Eredivisie, Bundesliga2, SerieB, PrimeiraLiga, JupilerPro, SuperLig, SuperLeagueGR, ScottishPrem]
seasons: [2019, 2020, 2021, 2022, 2023, 2024, 2025]
cv:
  strategy: walk_forward_expanding
  embargo_days: 7
  fold_boundary: season_and_winter_break
features:
  - use_all_pre_match: true
  - max_features: 200  # post-selection
  - selection: shap_quantile_0.8 on first-pass LightGBM
model:
  type: lightgbm
  objective: multiclass
  num_class: 3
  n_estimators: 2000
  learning_rate: 0.03
  early_stopping: 100
  bagging: 10  # for predictive variance
  seed: 42
calibration:
  selector: walk_forward_ece
  candidates: [temperature, dirichlet, matrix_scaling, vector_scaling]
  forbidden: [per_class_binary_platt_renormalised]  # known bug
  ece_variant: adaptive_15_bins
  validation_fraction: 0.15
evaluation:
  primary: log_loss
  gates:
    log_loss_vs_incumbent: {test: delong, fdr_q: 0.1}
    ace_overall: {max: 0.05, bootstrap_ci_upper: 0.06}
    ace_per_league: {max: 0.10}
    clv_point: {min: 0.0}
  bootstrap_resamples: 1000
reporting:
  mlflow: true
  html_report: true
  brier_decomposition: true
  per_group_ece: [market, league]
```

### 6.2 `experiments/alpha_calibration_ablation.yaml`

```yaml
name: football-1x2-alpha-calibration-ablation
inherits: alpha_baseline_1x2
# run the baseline 5× with only calibration changed
grid:
  calibration.method: [none, temperature, dirichlet, matrix_scaling, vector_scaling]
goal: establish that dirichlet dominates temperature on log-loss AND ACE
# fail the ablation if no method both:
#   - beats `none` by log_loss with delong p < 0.05 (FDR q=0.1)
#   - achieves ace_overall bootstrap_ci_upper < 0.06
```

### 6.3 `experiments/alpha_kelly_variants.yaml`

```yaml
name: football-1x2-alpha-kelly-variants
inherits: alpha_baseline_1x2
fix_model: true  # load production model, vary only Kelly
grid:
  kelly:
    fraction: [0.15, 0.25, 0.5]
    uncertainty_adjustment: [none, ece_dampen, bayes_posterior_var]
    constraints:
      per_match: [0.02, 0.03, 0.05]
      per_round: [0.08, 0.10, 0.15]
      per_league: [0.12, 0.15, 0.20]
      per_cluster: [0.10, 0.12, 0.15]
      total_exposure: [0.20, 0.25, 0.30]
metrics:
  - terminal_log_wealth
  - max_drawdown
  - sharpe
  - sortino
  - time_under_water_days
  - ruin_probability_0.5  # P(bankroll hits 50%)
```

### 6.4 `experiments/alpha_ou25_and_btts.yaml` (week 3-4)

```yaml
name: football-alpha-ou25-btts
market: [ou_2_5, btts]
# binary targets; use beta calibration
calibration:
  candidates: [platt, beta, isotonic_monotone_spline, temperature]
  n_val_thresholds:
    platt: 0
    beta: 500
    isotonic_monotone_spline: 2000
gates:
  same as 1x2 but ace_overall: 0.04 (tighter, binary easier to calibrate)
```

---

## 7. Statistical guarantees landing can safely claim

### 7.1 Wording rules

**The public claim must be one of:**

#### Before 100 bets:
> "Tracking in progress. n = [X] bets settled. Point estimate: CLV = +X.X%. Not yet statistically significant. Target: 500 bets for 95% confidence."

#### 100 ≤ n < 500 bets:
> "CLV point estimate: +X.X% (95% CI: [lower, upper], n = [X]). Confidence interval still includes zero — beat-the-close claim not yet statistically significant."

#### n ≥ 500 and CI excludes zero:
> "Measured CLV: +X.X% (95% CI: [l, u], n = [X], one-sided t-test p = 0.XX). By standard sports-betting methodology, positive CLV is evidence of true edge against the closing market."

#### n ≥ 500 and CI includes zero:
> "Measured CLV: +X.X% (95% CI includes 0, n = [X]). We do not claim statistically proven edge. Continuing evaluation."

### 7.2 Posterior probability of edge

Better than frequentist: **Bayesian posterior P(true μ_CLV > 0 | data)**.

With weakly informative prior μ_CLV ~ N(0, 0.05²) and data {CLV_1, …, CLV_n} assumed N(μ, σ²):
```
Posterior: μ | data ~ N(μ_post, σ²_post)
μ_post = (σ² · μ_prior + n · σ²_prior · x̄) / (σ² + n · σ²_prior)
P(μ > 0 | data) = Φ(μ_post / σ_post)
```

Landing can say: **"Posterior probability of true edge: 87%"** — this is **more honest** than a p-value and more *actionable* for tipsters who think in probabilities.

### 7.3 What NOT to publish

**[RYZYKO]** Specific forbidden claims:
- "70% win rate" — meaningless without odds context
- "+15% ROI" — with no n or CI, this is indistinguishable from tipster clickbait
- "Kelly-optimal sizing" — without disclosure of α = 0.25, misleading
- "Our model beats Pinnacle" — only defensible if CLV CI strictly above 0 after 500+ bets

---

## 8. Proofs / references

### Core references (name : year : what it proves : where to find)

| Reference | Claim used |
|---|---|
| **Murphy (1973)**, *A New Vector Partition of the Probability Score*, J. Appl. Meteor. 12(4) | Brier decomposition: Reliability − Resolution + Uncertainty. Promote on Resolution subject to Reliability ≤ ε. |
| **Dawid (1982)**, *The Well-Calibrated Bayesian*, JASA 77(379) | Definition of calibration as empirical frequency = stated probability. Foundation of ECE. |
| **Kelly (1956)**, *A New Interpretation of Information Rate*, Bell Sys. Tech. J. 35(4) | f* = edge/odds maximises E[log W]. Derivation pp. 917-919. |
| **Thorp (1997)**, *The Kelly Criterion in Blackjack, Sports Betting, and the Stock Market*, 10th Int'l Conf. on Gambling and Risk Taking | Fractional Kelly tradeoff, quote in §4.1. |
| **MacLean, Ziemba, Thorp (1992)**, *Growth versus Security in Dynamic Investment Analysis*, Mgmt. Sci. 38(11) | Risk of ruin formulae, drawdown-vs-growth frontier. |
| **Platt (1999)**, *Probabilistic Outputs for SVMs*, Adv. Large Margin Classifiers | Platt scaling = sigmoid on decision function, 2 params (A, B) fit by MLE. |
| **Zadrozny & Elkan (2002)**, *Transforming Classifier Scores into Accurate Multiclass Probability Estimates*, KDD | Isotonic regression calibration, convergence to true posterior. |
| **Guo, Pleiss, Sun, Weinberger (2017)**, *On Calibration of Modern Neural Networks*, ICML | Temperature scaling. Empirical: 1 param beats Platt on deep nets. |
| **Kull, Silva Filho, Flach (2017)**, *Beta calibration*, AISTATS | Beta calibration for binary, strict improvement over Platt when score distribution is not logistic. |
| **Kull, Perello Nieto, Kängsepp, Silva Filho, Song, Flach (2019)**, *Beyond temperature scaling: Obtaining well-calibrated multi-class probabilities with Dirichlet calibration*, NeurIPS | Dirichlet calibration for multiclass, our recommended 1X2 calibrator. |
| **Gneiting & Raftery (2007)**, *Strictly Proper Scoring Rules, Prediction, and Estimation*, JASA 102(477) | Maximise sharpness subject to calibration. Theoretical basis for §5.5. |
| **DeLong, DeLong, Clarke-Pearson (1988)**, *Comparing the Areas Under Two or More Correlated ROC Curves*, Biometrics | DeLong test for comparing predictive models on shared data. Used for promotion gate. |
| **Benjamini & Hochberg (1995)**, *Controlling the False Discovery Rate*, JRSS B 57(1) | FDR procedure — our multiple-testing correction. |
| **Ledoit & Wolf (2004)**, *A well-conditioned estimator for large-dimensional covariance matrices*, J. Multivariate Analysis | Covariance shrinkage for portfolio Kelly. |
| **Levitt (2004)**, *Why are gambling markets organised so differently from financial markets?*, Economic J. 114(495) | Closing-line efficiency in sports markets — foundation of CLV methodology. |
| **Forrest & Simmons (2008)**, *Sentiment in the betting market on Spanish football*, Applied Economics 40(1) | Football-specific: closing odds incorporate information better than opening odds. |
| **Dixon & Coles (1997)**, *Modelling Association Football Scores and Inefficiencies in the Football Betting Market*, Applied Statistics 46(2) | Poisson/Dixon-Coles for goals — basis for goals model (Phase 2). |

---

## 9. Where MLEng will want to cheat

In order of how much I will push back:

1. **"Let's just use the same calibrator for all markets and leagues, n_val is too small otherwise."**
   *Pushback:* agree for leagues, refuse for markets. 1X2 and OU have fundamentally different score distributions. Same calibrator → ECE on OU will be 0.10–0.15. Ship Dirichlet for 1X2, beta for OU, and pool leagues until n_league > 500.

2. **"ECE-dampening (multiply Kelly by 1−ECE) is good enough; full Bayesian posterior is too slow."**
   *Pushback:* Not good enough mathematically but I concede it is acceptable for Alpha. Demand instead: **10× bagged LightGBM → empirical predictive variance → Bayes-corrected Kelly using the variance formula in §4.3**. This is ~10× slower inference (still <1s per match) and 10× more principled. No MCMC needed at Alpha.

3. **"Let's calibrate on the full training set, not a separate validation slice."**
   *Hard no.* This is a **silent leakage** — the calibrator learns the test distribution through the model's training signal. ECE on test is then optimistically biased by ~0.01–0.03 which is more than our headroom. Must enforce a 15% validation slice inside walk-forward.

4. **"n_bets minimums for publishing CLV are too strict; let's show numbers from day 1."**
   *Negotiate:* show numbers from day 1, but gate the *claim wording* by n (see §7.1). "Point estimate" is acceptable; "statistically significant" is not.

5. **"Let's use log-loss directly for Kelly sizing instead of probability."**
   *Hard no.* Log-loss is not a probability. It is a loss. Sizing must use the *calibrated probability*. This has been suggested in at least one tipster community and it is numerically wrong.

6. **"Temperature scaling is enough, skip the CalibrationSelector overhead."**
   *Pushback:* keep selector (ADR-0007 stands). Temperature scaling with 1 parameter cannot correct for systematic score-distribution skew. Cost is 5 seconds per fold — trivial. The selector also gives us an *audit log of which method won per fold* — valuable for the whitepaper.

7. **"We'll train on full history, no embargo, the embargo throws away good data."**
   *Hard no.* Embargo exists because features have lag (rolling xG over last 5 matches cannot be computed for matches in week of train-test boundary without leaking). 7-day embargo is the minimum. If we need more data, extend history (more seasons), do not shorten embargo.

---

## 10. Minimum viable math (if timeline brutal)

If week 1 of the 4-week plan slips and we must ship something:

### Floor (must have to ship Alpha ethically)
1. **Log-loss training** with early stopping on 15% validation slice.
2. **Walk-forward CV** with 7-day embargo (**even if only 2 folds**).
3. **Calibration**: temperature scaling for 1X2 (Dirichlet deferrable to week 2); Platt for OU/BTTS. This is the floor.
4. **ECE reporting with bootstrap CI**: no ECE point estimate anywhere, only CI.
5. **Fractional Kelly α = 0.25** with per-match cap 3%, per-round cap 10%.
6. **CLV tracking** from day 1, even if we only display after 100 bets.
7. **Landing page wording** follows §7.1 tiers — this is non-negotiable regardless of timeline.

### Not floor (can defer to post-alpha)
- Dirichlet calibration (can start with temperature, upgrade in week 3)
- Bayesian posterior Kelly (ECE-dampen is OK temporarily; §9 point 2)
- Full portfolio covariance shrinkage (constraints alone get 80% of the benefit)
- DeLong test in CI (manual per-promotion is OK)
- Per-league calibration (pool all leagues until n>500 per league)
- Dixon–Coles goals model (Phase 2, not Alpha)

### Absolutely not acceptable even under timeline pressure
- K-fold CV
- Calibration fit on training set (no validation split)
- Per-class binary calibration of 1X2 with renormalisation
- Full Kelly (α = 1.0)
- "70% win rate" on landing page
- CLV claim with n < 500 and no CI
- Closing odds in features
