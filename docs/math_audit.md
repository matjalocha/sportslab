# Mathematical Audit — `ml_in_sports` (pre-P2)

> **Task**: P0.20 from `ideas/phase_0_foundations/tasks.md`
> **Linear issue**: [SPO-20](https://linear.app/sportslab/issue/SPO-20/p020-audyt-matematyczny-obecnych-modeli-nb01-nb30)
> **Auditor**: Claude Code `drmat` subagent (Doctor of applied mathematics persona)
> **Date**: 2026-04-05
> **Scope**: Research codebase at `c:/Users/Estera/Mateusz/ml_in_sports/`, ~29 active scripts, 18 notebooks, 5 leagues, seasons 1415-2526
> **Method**: Read-only. Prioritized `src/models/`, NB04 (calibration), NB15/NB24/NB26/NB28/NB29 (main training/backtest runners), `src/features/rolling_features.py`, `src/features/betting_features.py`, `src/processing/extractors.py`
> **Status**: Awaits review by MLEng/Lead before acceptance of SPO-20 DoD
> **Related**: [docs/tech_debt_audit.md](tech_debt_audit.md) (P0.19, code-quality audit companion)

---

## 1. Executive Summary

**Verdict:** The current stack is a **conventional but honestly-built ML baseline** with two non-trivial mathematical strengths (walk-forward calibration in NB04, Kelly with ECE shrinkage in `value_betting.py`) and several specific, fixable flaws. It is a **solid base for P2**, not a redesign candidate. The critical gap is that the CLV result is **negative** (-1.38% mean over 4,964 bets) — i.e. the model currently loses to Pinnacle closing line, which means any claim of "yield" in backtests is not supported by the strongest statistical test we have.

**Soundness scores (1-5):**

| Dimension                 | Score | One-line verdict                                                                          |
|---------------------------|-------|-------------------------------------------------------------------------------------------|
| Calibration               | 3.5   | Platt + isotonic implemented walk-forward in NB04; abandoned in NB15 because it hurt LL   |
| Kelly / stake sizing      | 3.0   | Fractional Kelly with ECE shrinkage — mathematically clean, but per-bet, no portfolio    |
| CLV methodology           | 4.0   | Correct definition, Pinnacle closing, walk-forward, 5k bets — verdict is honest (-1.38%) |
| Data leakage (features)   | 4.5   | `shift(1)` throughout rolling features; closing odds excluded from training              |
| CV strategy               | 3.0   | Walk-forward by season in NB04/NB26, but NB24 stacking uses shuffled KFold — leak         |
| Statistical significance  | 1.5   | No DeLong, no bootstrap, no paired test anywhere. LL deltas reported as scalars          |
| Ensembling                | 2.5   | ENS4 weights = `1/val_LL` fixed, NB28 blend-weight tuned on test set (selection leak)     |
| Goals / Poisson model     | 2.5   | Basic Poisson + Dixon-Coles exist (NB19 artifact), but not wired into production          |
| SHAP stability            | 2.0   | SHAP computed once in NB02, no retrain-stability measurement                              |
| Novelty / IP potential    | 2.0   | Conventional GBM + LR + Platt + flat Kelly; nothing patentable yet                        |

**Top 3 risks:**

1. **Selection-on-test in NB28/NB29 ENS5 blend** — TabPFN blend weight is optimized on the same validation split whose LL is then reported; reported LL improvement is upward-biased.
2. **Shuffled KFold in NB24 stacking OOF** — L2 meta-features are built by `StratifiedKFold(shuffle=True)` on chronologically ordered matches; the L2 LogReg sees near-future matches during OOF training.
3. **No significance testing of LL deltas** — the "best" model (ENS4 LL 0.9359) is chosen by comparing scalar log-losses on one validation season. Differences of 0.001-0.002 are within bootstrap noise for ~1,800 matches.

**Top 3 strengths:**

1. **NB04 walk-forward discipline** — 5 expanding folds, separate train/cal/test, closing-odds columns explicitly excluded from features (notebook cell: list `["maxc", "avgc", "ah_", "ahc"]`). This is the gold-standard scaffold for P2 to build on.
2. **Rolling features all use `shift(1)`** — `src/features/rolling_features.py:250, 310, 376, 460`. Zero target leakage via rolling windows.
3. **Kelly with variance shrinkage** — `src/models/value_betting.py:32` implements `p_conservative = max(p_model - z * ece, 0.01)` before Kelly. This is a defensible (if simple) approximation of Bayesian shrinkage and is the seed for the "Hybrid Calibrated Portfolio Kelly" IP claim.

---

## 2. Calibration

**[PEWNE]** Both Platt scaling and isotonic regression are implemented per-class in `notebooks/04_calibration_value_betting.ipynb` (cells around lines 386-447, `platt_scale()` and `isotonic_calibrate()`), fit on a separate calibration season, normalized across classes so rows sum to 1.

**[PEWNE]** ECE is defined in NB04 (line 450-474) using equal-width bins, one-vs-rest averaged across three classes (line 668, 678). Formula is `ece = sum over bins of (n_bin * |avg_pred - avg_true|) / n_total`. This is the standard ECE-L1 and is mathematically correct.

**[PEWNE]** NB04 walk-forward structure is **exemplary**: 5 expanding folds (train 1415-1819 → cal 1920 → test 2021, etc.), with completely disjoint calibration and test seasons. No leakage between cal fit and test evaluation.

**[RYZYKO]** In NB04 (fold-level LL results printed around line 502-530), Platt calibration **made LL worse** on 3 of 5 folds (fold0: 0.9805→0.9752 better; fold1: 0.9748→0.9770 worse; fold2: 0.9512→0.9560 worse; fold3: 0.9397→0.9450 worse; fold4: 0.9430→0.9456 worse). Isotonic is even worse on fold4. This suggests the **raw LightGBM probabilities were already near-optimally calibrated on those seasons**, and Platt is over-correcting.

**[RYZYKO]** NB15 (`scripts/run_nb15.py:186-256`) implements a one-shot Platt calibration gated by `ll_platt < ll_raw - 0.001`, meaning **calibration is silently skipped in production runs**. The ECE value printed as "from NB04/NB17" (ECE_1X2 = 0.020, `scripts/kelly_stakes.py:21`) is therefore the **raw ensemble ECE**, not a calibrated one — which is fine as long as the Kelly shrinkage uses the *actual* ECE of the probabilities it receives.

**[HIPOTEZA]** The "Platt hurts" result in 3/5 folds likely stems from (i) 3-class multinomial Platt being over-parameterized for ~1,700 cal samples (the NB15 implementation fits 3×4 = 12 weights + biases on ~1,800 rows), and (ii) LGB's objective already being multiclass log-loss, so its raw probs are already local MLE. **Test:** fit a **temperature-scaling** single-parameter calibration (just divide logits by T) and compare — expected to beat Platt when the base model is already well-calibrated. Measure: ECE delta, LL delta, bootstrapped CI.

**[DO SPRAWDZENIA]** Reliability diagrams exist in NB04 (saved "last fold" data for plotting) but there is no measurement of **per-league** or **per-season** calibration. For P2 targets ("ECE < 2% per league per season"), this granularity is absent. Who/how: MLEng produces a 5×5 grid of ECE values and a per-league reliability-diagram panel from the NB04 walk-forward run.

**Target vs current:**

- **P2 target:** ECE < 2% per league per season on hold-out.
- **Current:** Aggregate ECE ≈ 2% (from `kelly_stakes.py:21`), per-league never measured. Platt makes LL worse on most folds. Baseline ENS4 is probably already at ~1.5-2.5% ECE without any calibrator, but it has not been shown rigorously.

---

## 3. Kelly / Stake Sizing

**[PEWNE]** `src/models/value_betting.py:8-41` implements fractional Kelly with ECE shrinkage:

- `p_conservative = max(p_model - z * ece, 0.01)` (line 32)
- `f_star = (b * p_conservative - (1 - p_conservative)) / b` where `b = odds - 1` (lines 33-34)
- Final stake = `min(fraction * f_star * bankroll, max_stake_pct * bankroll)` (lines 39-40), with defaults `fraction=0.25`, `max_stake_pct=0.02`, `z=1.0`.

This is per-bet Kelly with (a) explicit fractional multiplier (quarter-Kelly by default), (b) ECE-based probability shrinkage, (c) hard 2%-of-bankroll cap.

**[PEWNE]** Tests in `tests/test_value_betting.py` cover 8 cases including zero-edge, break-even, max cap, bankroll scaling, fraction scaling, ECE shrinkage, ECE-eliminates-edge. Good coverage of the scalar function.

**[RYZYKO]** **No portfolio Kelly.** Each bet is sized independently, then `scale_to_budget()` (lines 44-67) applies a single proportional rescale when the total exceeds the weekly budget. This ignores: (i) correlation between bets (e.g. 1X2 Home + O/U Over on the same match are strongly positively correlated), (ii) simultaneous exposure constraint (the canonical Kelly assumes sequential independent bets), (iii) accumulator decomposition.

**[RYZYKO]** **ECE-as-variance-proxy is an ad-hoc heuristic.** The shrinkage `p - z*ece` treats ECE (a scalar calibration metric) as if it were one standard deviation of `p_model` — but ECE is the *average* absolute miscalibration across bins, not a per-probability uncertainty. A high-confidence prediction (p=0.85) and a coin-flip (p=0.5) receive the same shrinkage. **Formal problem:** ECE is an expectation over bins; the correct per-prediction variance needs either (a) a full Bayesian posterior, (b) conformal prediction intervals, or (c) per-bin ECE lookup.

**[HIPOTEZA]** A cleaner shrinkage is per-bin ECE: `p_conservative = p_model - z * ece_bin(p_model)` where `ece_bin` is a piecewise-constant function learned from the reliability diagram. **Test:** compare retrospective log-growth on NB04 CLV dataset between the current global-ECE shrinkage and per-bin shrinkage. Expected gain: small (few bp), but fundamentally more defensible.

**[RYZYKO]** Accumulator (parlay) handling in `scripts/kelly_stakes.py:85-92` combines legs via `p_combined = product of p_i` and `odds_combined = product of odds_i`, then uses `mean_ece` as the shrinkage. **This assumes independence of legs**, which is violated when (i) legs are on the same match, (ii) legs are correlated via day-of-the-week or league-wide scoring environment, (iii) legs share common latent factors (weather, referee). The mean-ECE is also the wrong aggregation — variance in a product of independent estimates grows multiplicatively, not additively.

**Target vs current:**

- **P2 target:** Portfolio Kelly with correlation matrix, Bayesian shrinkage.
- **Current:** Per-bet fractional Kelly with global-ECE shrinkage and flat budget scaling.

---

## 4. CLV (Closing Line Value)

**[PEWNE]** CLV is computed in `notebooks/04_calibration_value_betting.ipynb` (cells ~1287-1405) as `clv = (odds_placed / pinnacle_closing) - 1`. Closing source: Pinnacle (`psc_home/psc_draw/psc_away`), loaded from `match_odds` table separately from the feature parquet. Coverage 93.8% (19,768/21,085 matches, per line 186).

**[PEWNE]** **The current model has negative CLV.** NB04 output (line 1307-1310): 4,964 bets across 5 walk-forward folds, **mean CLV = -1.38%**, median -1.07%, only 41.6% positive. Output in `data/artifacts/04_clv_bets.csv`.

**[RYZYKO]** Methodology uses the ratio form `odds_placed/closing - 1` rather than implied-probability-difference `(1/closing - 1/placed)` or log-odds. The ratio form is correct for expected cash-flow CLV but **asymmetric**: a 10% gain (e.g. 2.20 → 2.42) and a 10% loss (2.20 → 2.00) produce different profit semantics. The log-odds form `log(odds_placed) - log(closing)` is symmetric and is the sharper bettor's standard. **[DO SPRAWDZENIA]** Recompute with log-odds form and see whether the -1.38% result changes materially.

**[RYZYKO]** Placed odds are `avg_*` (mean across bookmakers, per line 1372 using `avg_odds_placed`). Comparing the cross-bookmaker **average opening odds** against the **Pinnacle closing sharp line** is the right thing to do if the bettor would have actually taken `avg_*` — but a real bettor can only take **one** bookmaker's price. For SportsLab production, CLV should be computed against the **actual taken odds** (e.g. STS, Superbet for Polish market) vs Pinnacle closing.

**[PEWNE]** Sample size (4,964 bets, 5 seasons) is **statistically adequate** to rule out "zero CLV" at any reasonable confidence. SE of the mean for 4,964 bets with individual CLV std ≈ 10% is ~0.14%, so -1.38% is many sigma below zero. This is the single most reliable verdict in the audit: **the model, as evaluated, is not beating the closing line.**

**[HIPOTEZA]** The negative CLV is concentrated in low-edge bets. In NB04 output around line 1312 ("CLV by Edge Bucket") the data likely shows a gradient — bets with edge > 10% may have positive CLV while edge < 5% drags the mean down. **[DO SPRAWDZENIA]** Extract the `clv_by_edge` table from `data/artifacts/04_clv_bets.csv` and test whether high-edge sub-populations clear the bar.

**Target vs current:**

- **P2 target:** Mean CLV > 0 over 100+ walk-forward bets.
- **Current:** Mean CLV = -1.38% over 4,964 bets (strongly, significantly negative). **This is the central problem P2 must solve.**

---

## 5. Data Leakage Risks

**[PEWNE]** Rolling features use `shift(1)` before rolling, in every rolling helper I inspected: `src/features/rolling_features.py:250` (`shifted = group[stat_name].shift(1)`), `:310` (goals std expanding), `:376` (venue rolling), `:460` (elo form). This is leak-safe.

**[PEWNE]** Closing odds columns (`b365c_*`, `avgc_*`, `psc_*`, `maxc_*`, `ahc_*`) are **explicitly excluded from training features** in NB04 cell at line 137 (`"maxc", "avgc", "ah_", "ahc"` in drop list). Feature list in `data/artifacts/03_final_features.json` confirmed to contain only `implied_prob_*` / `fair_prob_*` / `consensus_*` derived from **opening** `avg_*` / `b365_*`, which is pre-match.

**[PEWNE]** In `src/processing/extractors.py:642-746`, the column mapping distinguishes opening (`B365H` → `b365_home`, `AvgH` → `avg_home`) from closing (`B365CH` → `b365c_home`, `AvgCH` → `avgc_home`). The schema separation is clean.

**[RYZYKO]** `fillna(0)` is used pervasively in training code (e.g. `run_nb15.py:110, 112, 194, 196; run_nb26_optuna.py:421, 426; run_nb28_ens5_check.py:177-179`). This is **not a leakage risk**, but it is a **signal-distortion risk**: for variables where 0 is a plausible value (e.g. `home_cumul_gd` at season start), the model cannot distinguish "missing" from "zero goal-difference". For P2, move to NaN-native LightGBM (supported) and NaN-aware imputation for LogReg (median + indicator).

**[HIPOTEZA]** The NB04 walk-forward uses `fillna(-999)` instead (lines 554, 555, 928, 929, 1338, 1339), which is leak-safe and LGB-friendly (LGB treats -999 as a distinct category). This is actually correct. The inconsistency between NB04 (`-999`) and NB15/NB26/NB28 (`0`) means **two different model realizations exist** depending on which script generated the probabilities.

**[RYZYKO] — NB24 stacking OOF leak.** `scripts/run_nb24_catboost_stacking.py:245` creates OOF meta-features via `StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)`. For a time-ordered dataset this means the L2 LogReg's "train" data includes matches whose labels were generated by a L1 model that saw **future matches**. The magnitude is typically small (5-fold shuffled OOF on a stationary target is not catastrophic), but it biases the reported L2-stacked LL downward by an unknown amount. **Fix:** use time-series CV (`TimeSeriesSplit` or purged K-fold).

**[RYZYKO] — NB28 blend-weight selection-on-test.** `scripts/run_nb28_ens5_check.py:223-229` sweeps `w_pfn in [0, 0.05, ..., 1.0]` and reports `best_blend_ll = min over w_pfn of log_loss(labels, blend)`. Both the sweep and the report use the **same** `labels` (validation set). The reported "ENS5 best LL" is an upward-biased estimate of the true held-out LL. To fix: split 2425/2526 into a weight-search half and an evaluation half, or use nested CV.

---

## 6. Cross-Validation Strategy

**[PEWNE]** NB04 uses proper **expanding walk-forward by season**, 5 folds, disjoint train/cal/test. This is the correct CV for a time-ordered dataset.

**[PEWNE]** NB26 Optuna (`scripts/run_nb26_optuna.py:413-416`) uses a **two-fold walk-forward**: optimization on fold1 (train < 2425, val = 2425), validation on fold2 (train < 2526, val = 2526). Strategy params are picked on fold1 and re-evaluated on fold2 — correct walk-forward discipline. Delta-yield between fold1 and fold2 is reported (line 514), which is a partial hedge against over-fitting to fold1.

**[RYZYKO]** Optuna uses **50 trials on a single validation season** (fold1 = 2425, ~1,800 matches). With 5 continuous hyperparameters the effective search space is large enough that 50 trials can find a yield-maximizing point by chance alone. The fold2 delta is reported but not used as a stopping criterion. **Hypothesis:** some of the "B_optuna" / "C_optuna" yield claims are within the noise band of the 50-trial search. **Test:** rerun Optuna with 5 different seeds, report yield distribution, compute CI.

**[RYZYKO]** NB24 stacking uses shuffled StratifiedKFold (see §5). Bug.

**[PEWNE]** NB29 backtest (`scripts/run_nb29_tabpfn_backtest3.py`) is a proper rolling-window walk-forward at the **matchweek** level — for each of the last 3 rounds of 2526, TabPFN is retrained on matches before that round and predicts only that round. This is the most rigorous backtest in the codebase, and should be the template for P2's production evaluation. Sample size is small (3 rounds × ~40 matches).

**[HIPOTEZA]** NB29's TabPFN-on-10k training set suggests a **recency vs data-volume** trade-off that has not been formally tested. With 20k+ matches available, why cap at 10k? Some of it is TabPFN's memory limit, but the recency argument (non-stationarity of football) needs a formal test. **Test:** for ENS4 (no TabPFN memory limit), compare LL at training sizes 5k/10k/20k/all; if more data is strictly better, recency concerns are unfounded.

---

## 7. Statistical Significance

**[PEWNE]** **No statistical tests anywhere.** Grep for `delong|bootstrap|pvalue|wilcoxon|mcnemar|paired_t` (case-insensitive) across all `.py` / `.ipynb` returned only documentation files (expert reports, `team_work_plan.md`). No test is actually executed in code.

**[PEWNE]** LL improvements are reported as scalars: NB15 comparison "raw vs Platt: delta +0.0022" (line 247-248), NB28 "ENS4_full vs ENS5_best", NB29 ENS4 vs TabPFN vs blend. Deltas of 0.002-0.004 on ~1,800 rows are within bootstrap noise (empirical rule: LL std-error on ~1,800 is ~0.005).

**[RYZYKO]** The claim in `scripts/run_nb15.py:567-568` that "model beats market (delta -0.0359)" (ENS4 LL 0.9383 vs market 0.9742) is **large enough to be real** (7-sigma for 1,800 rows). But every smaller comparison between model variants is not. The headline number "best ensemble is ENS4 with LL 0.9359" vs "TabPFN 0.94" is a ~0.004 gap — **not distinguishable from noise** without a paired test.

**[HIPOTEZA]** Effective sample size per league-season is ~380 matches. For 1X2 multiclass LL, the standard error on per-fold LL is approximately `std(log p_true) / sqrt(N) ≈ 1.0/sqrt(380) ≈ 0.051`. That means **any LL delta below ~0.01 between two models trained on the same fold is within one SE and should not be called an improvement**. The tech-debt audit number "ENS4 best at 0.9359 vs TabPFN ~0.94" clearly fails this bar.

**Validation plan (for P2):**

- Add **paired bootstrap** (1,000 resamples of match indices) around every LL comparison.
- Add **DeLong test** for ROC-AUC comparisons (when used for binary markets BTTS/OU).
- Report LL delta + 95% CI, not scalar delta.
- Add **pre-registered decision rule**: "adopt new model only if 95% CI of LL delta excludes zero AND delta > 0.002".

---

## 8. Ensembling

**[PEWNE]** ENS4 in `scripts/run_nb15.py:174-179` and `run_nb26_optuna.py:106-111`: `w_lgb = 1/lgb_val_ll`, `w_xgb = 1/xgb_val_ll`, `w_lr = 1/1.05`, `w_cb = 1/0.9354`, normalized to sum to 1. This is **inverse-loss weighting**, a non-optimal but standard heuristic.

**[RYZYKO]** The weights `w_lr = 1/1.05` and `w_cb = 1/0.9354` are **hardcoded from prior fold runs** — they are not re-computed per fold. In a walk-forward setting, these are stale constants. The ENS weights are also **not tuned on validation** (which would be a different leakage risk) — they are just frozen from NB14/NB24 outputs.

**[RYZYKO]** Inverse-loss weighting is sub-optimal vs **optimal convex combination**. The optimal weights are the solution to `min_w LL(sum_i w_i p_i, y)` subject to `w_i ≥ 0`, `sum w_i = 1`, fit on a held-out set. This is a convex optimization (LL is convex in the weights for fixed probs). **Expected gain:** small but real, maybe 0.001-0.003 on LL.

**[RYZYKO] — NB28 blend-weight selection leak.** `run_nb28_ens5_check.py:223-229`: best ENS5 weight `w_pfn` is picked by `argmin` over the same validation fold whose LL is then reported. Selection-on-test bias. See §5.

**[PEWNE]** NB24 implements proper meta-stacking (L1 = LGB/XGB/CB/LR, L2 = LogReg on OOF meta-features). Mathematically correct structure; the bug is only in the CV scheme (see §5, §6).

**[HIPOTEZA]** For three-class 1X2 with four base learners, the L2 LogReg has 4×3 = 12 input features and 3 output classes → 39 parameters. With ~15k training rows, this is far from overfitting. The stacking approach is **more principled than inverse-loss averaging** and should become the default after the KFold bug is fixed.

---

## 9. Goals / Poisson Models

**[PEWNE]** A Poisson and Dixon-Coles model exist: `data/artifacts/19_poisson_results.csv` shows:

- fold1: Poisson LL_1x2 = 0.9695, Poisson_DC LL_1x2 = 0.9676
- fold2: Poisson LL_1x2 = 0.9754, Poisson_DC LL_1x2 = 0.9738

So Dixon-Coles improves 1X2 LL by ~0.002 over raw Poisson, and also feeds O/U (LL ~0.68) and BTTS (LL ~0.69). Small but consistent improvement.

**[RYZYKO]** Both Poisson and DC LLs on 1X2 are **worse than ENS4** (0.9676/0.9738 vs 0.9359). So Poisson is not currently used as the main 1X2 model, only as a **secondary market derivation** (1X2 → O/U → BTTS from a single goals distribution).

**[HIPOTEZA]** The 0.002 DC-over-Poisson gain is exactly the Dixon-Coles low-score correction term (τ on 0-0, 1-0, 0-1, 1-1). For 1X2, this correction rarely changes the argmax; for BTTS and O/U 2.5 it is more important (because 0-0 and 1-0 sit exactly on the boundary). **Test:** break down the DC gain by market — I expect the gain to concentrate in BTTS.

**[RYZYKO]** No bivariate Poisson, no NB (negative binomial), no zero-inflated variants. The dispersion parameter of football goals (ratio of variance to mean) is typically ~1.1-1.2 — Poisson's assumed ratio of 1.0 is slightly too tight. For P2 goals model, fitting NB or ZIP would be a ~1-day exercise with a measurable ECE improvement.

**[DO SPRAWDZENIA]** Is the Poisson fit per-team offensive / defensive strength (classical Maher 1982) or is it a GBM-regression to expected goals? Need to read `scripts/_archive/` around NB19. Who: MLEng, when they unpack the archive during P1 migration.

---

## 10. SHAP Stability

**[PEWNE]** SHAP values are computed once in NB02 (`data/artifacts/02_shap_importance.csv`) and used as a feature-selection input for `03_final_features.json` (baseline_100 feature set).

**[RYZYKO]** **No stability measurement.** SHAP is computed on one training run. There is no:

- cross-fold SHAP aggregation (mean + std of |SHAP| per feature across folds),
- Jaccard similarity of top-K features across retrains,
- Spearman rank correlation of feature importance between folds.

**[RYZYKO]** **Feature selection loop may be leaky.** The selection in `03_final_features.json` was done via SHAP on one model run, then **the same features are used for all subsequent CV folds**. Strictly, the selection should be inside each walk-forward fold (select on train, evaluate on test). This is a common ML mistake and is **mildly** biasing — the selected 100 features are optimal in-sample over the full dataset, which slightly inflates out-of-sample LL claims.

**[HIPOTEZA]** Given the large feature pool (~175) and the relatively small per-feature contribution, fold-internal SHAP selection would change the chosen set by 10-20 features. **Test:** implement fold-internal SHAP selection and compare final LL — expected ~0.001 degradation (acknowledging the honest number) but a more trustworthy model.

---

## 11. Novelty / IP Potential

**[PEWNE]** **The current stack is conventional.** ENS4 = LGB + XGB + CatBoost + LogReg averaged by inverse-loss weights is the textbook football-betting ML recipe (Bunker-Thabtah 2019, Hubáček et al. 2019, Berrar et al. 2019). Nothing here would survive a novelty search at a betting-ML conference.

**[PEWNE]** **The only distinctive piece is the Kelly+ECE shrinkage in `value_betting.py`**. This is a mild original contribution (ECE-as-variance-proxy) but not patentable as-is — it is an obvious approximation any practitioner would write down.

**[HIPOTEZA]** **What "Hybrid Calibrated Portfolio Kelly" needs to become IP:**

1. **Calibration layer** that is explicitly per-league and per-market (Dirichlet regression, or a hierarchical Bayesian calibrator with league-specific shrinkage toward a global prior).
2. **Portfolio Kelly with explicit correlation matrix** — use closing-line co-movement to estimate `corr(bet_i, bet_j)` and solve the multi-dimensional Kelly QP (Thorp 2006, Chapman 2007).
3. **Conformal prediction** for per-bet uncertainty, not ECE — this replaces the ad-hoc `p - z*ece` shrinkage with a principled prediction interval that has coverage guarantees.
4. **Whitepaper with the closed-form link** between (ECE, conformal width, portfolio correlation) and the resulting growth rate. This is the publishable story — none of (1)-(4) on their own are novel, but the integration is.

**[RYZYKO]** None of (1)-(4) exist today. The IP moat claimed in `ideas/ip_moat.md` is currently **aspirational**, not realized. The audit shows the foundation is good enough to build on; the moat itself still has to be built.

---

## 12. Gaps vs SportsLab P2 targets

| Dimension | P2 Target | Current state | Delta | Effort to close |
|---|---|---|---|---|
| ECE (aggregate) | < 2% | ~2% (raw ENS4, Platt hurts 3/5 folds) | ~0pp aggregate, but per-league unknown | Low — measure per-league, try temperature scaling |
| ECE (per league-season) | < 2% uniform | Not measured | Unknown | Medium — 5×5 grid, 2-3 days MLEng |
| CLV mean | > 0 over 100+ bets | **-1.38% over 4,964 bets** | **-1.38pp, strongly negative** | **High — root cause is the model's edges don't survive market closing. Requires either better features (closing-line movement, lineup info), better calibration, or tighter selection (only bet edge > 10%).** |
| LL improvement vs baseline | ≥ 0.002, stat. significant | No significance tests exist | Statistical infrastructure gap | Low — add paired bootstrap utility, 1 day |
| Portfolio Kelly | Correlation-aware | Per-bet independent | Full design needed | Medium — 1 week including simulation |
| Goals model | Poisson / DC / NB wired into BTTS + OU + CS | DC exists in archive, not production | Integration + NB upgrade | Medium — 1 week |
| SHAP stability | Top-K Jaccard > 0.7 | Not measured | Instrumentation gap | Low — 2 days |
| CV discipline | Walk-forward everywhere, no shuffled KFold | NB04/NB26 ok, NB24 broken, NB28 leak | 2 localized bugs | Low — 1 day fix each |
| Statistical testing | Bootstrap CI on every LL delta | Zero tests | Missing | Low — reusable utility, 1 day |

---

## 13. Recommendations for P2 (prioritized)

**P2-1 [PEWNE] — Fix NB28 blend-weight selection-on-test.**
Split validation fold into halves; search weight on half A, report LL on half B. Or implement nested CV. Before this fix, **any "ENS5 beats ENS4" claim is invalid**.
File: `scripts/run_nb28_ens5_check.py:223-229`.

**P2-2 [PEWNE] — Fix NB24 stacking OOF.**
Replace `StratifiedKFold(shuffle=True)` with `TimeSeriesSplit(n_splits=5)` or time-respecting purged K-fold.
File: `scripts/run_nb24_catboost_stacking.py:245`.

**P2-3 [PEWNE] — Add paired bootstrap infrastructure.**
Single utility `compare_ll(probs_A, probs_B, labels, n_boot=1000) -> (delta, ci_low, ci_high, p_value)`. Enforce: every new model claim goes through it. This alone kills a lot of noise.

**P2-4 [PEWNE] — Measure per-league, per-season ECE grid.**
5 leagues × 5 hold-out seasons = 25 ECE values from NB04 walk-forward. Reliability diagrams per cell. This is the P2 acceptance criterion and needs to be the first thing measured.

**P2-5 [HIPOTEZA] — Replace Platt with temperature scaling.**
Single-parameter T calibration, fit on cal set. Expected to outperform 3-class Platt on well-calibrated LGB bases. Validation: LL and ECE on all 5 NB04 folds + bootstrap CI.

**P2-6 [HIPOTEZA] — Root-cause the -1.38% CLV.**
Split bets by edge bucket, by league, by odds range, by time-to-kickoff. The hypothesis is that CLV is positive on edge > 10% bets and strongly negative on edge < 3% bets (mean-reversion effect). If confirmed, the production filter becomes `edge > threshold` learned from CLV, not from yield.
Source data: `data/artifacts/04_clv_bets.csv`.

**P2-7 [RYZYKO] — Replace ECE-shrinkage with per-bin lookup or conformal.**
Current `p - z*ece` is a global heuristic. Per-bin ECE (piecewise correction from the reliability diagram) is a strict upgrade. Long-term: conformal prediction intervals with guaranteed coverage.
File: `src/models/value_betting.py:32`.

**P2-8 [RYZYKO] — Portfolio Kelly with correlation matrix.**
Estimate `corr(bet_i, bet_j)` from (a) same-match indicator (correlation = 1 on same match, 0 otherwise as a first pass), (b) shared-day bookmaker margin movements, (c) league-wide volatility. Solve the QP. Fractional Kelly multiplier `α = 0.25` stays.

**P2-9 [HIPOTEZA] — Fold-internal feature selection.**
Move SHAP selection inside each walk-forward fold. Expected to slightly degrade reported LL (0.001-0.003) but remove a silent bias. Required for the final P2 audit story.

**P2-10 [DO SPRAWDZENIA] — Poisson/NB goals model integration.**
Verify whether the existing NB19 Poisson/DC model uses Maher-style team strengths or a regression. If Maher: upgrade to bivariate Poisson (Karlis-Ntzoufras 2003). If regression: swap to NB for the modest dispersion gain. Wire outputs into BTTS and O/U 2.5 markets and compare to current LogReg-based models on LL + ECE.
Who: MLEng, after unpacking `scripts/_archive/` in P1 migration.

**P2-11 [HIPOTEZA] — Drop the `fillna(0)` convention across all scripts.**
Use `fillna(-999)` (as NB04 does) or native NaN handling in LightGBM. The inconsistency between NB04 and NB15/NB26/NB28 means multiple "ENS4" models exist. Standardize first, benchmark second.

**P2-12 [RYZYKO] — Rotate the TabPFN JWT token exposed in source.**
`scripts/run_nb28_ens5_check.py:38` contains a hardcoded JWT token. Out of math scope but flagged because it blocks the P1 repo migration to `packages/ml-in-sports/`. Procedure in `memory/feedback_secrets_in_chat.md`.

---

## Files referenced (absolute paths)

- `c:/Users/Estera/Mateusz/ml_in_sports/src/models/value_betting.py`
- `c:/Users/Estera/Mateusz/ml_in_sports/src/models/schemas.py`
- `c:/Users/Estera/Mateusz/ml_in_sports/src/features/rolling_features.py`
- `c:/Users/Estera/Mateusz/ml_in_sports/src/features/betting_features.py`
- `c:/Users/Estera/Mateusz/ml_in_sports/src/processing/extractors.py`
- `c:/Users/Estera/Mateusz/ml_in_sports/src/utils/database.py`
- `c:/Users/Estera/Mateusz/ml_in_sports/tests/test_value_betting.py`
- `c:/Users/Estera/Mateusz/ml_in_sports/notebooks/04_calibration_value_betting.ipynb`
- `c:/Users/Estera/Mateusz/ml_in_sports/scripts/run_nb15.py`
- `c:/Users/Estera/Mateusz/ml_in_sports/scripts/run_nb24_catboost_stacking.py`
- `c:/Users/Estera/Mateusz/ml_in_sports/scripts/run_nb26_optuna.py`
- `c:/Users/Estera/Mateusz/ml_in_sports/scripts/run_nb28_ens5_check.py`
- `c:/Users/Estera/Mateusz/ml_in_sports/scripts/run_nb29_tabpfn_backtest3.py`
- `c:/Users/Estera/Mateusz/ml_in_sports/scripts/kelly_stakes.py`
- `c:/Users/Estera/Mateusz/ml_in_sports/data/artifacts/04_clv_bets.csv`
- `c:/Users/Estera/Mateusz/ml_in_sports/data/artifacts/19_poisson_results.csv`
- `c:/Users/Estera/Mateusz/ml_in_sports/data/artifacts/03_final_features.json`
