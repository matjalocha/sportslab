# ML Experiments Plan — Alpha Launch (Consolidated)

> **Status:** Final v1 · 2026-04-22
> **Reviewed by:** mleng_a (practical), mleng_b (product/trust), drmat (math)
> **Arbitrated by:** Lead (founder-engineer)
> **Scope:** Alpha launch (2-3 week runway), 5-10 beta users on Telegram
> **Supersedes:** `ml_experiments_draft_mleng_a.md`, `ml_experiments_draft_mleng_b.md`, `ml_experiments_draft_drmat.md`

---

## TL;DR — 10 executive decisions

1. **[SHIP] 1X2 + OU_2.5 at launch** · BTTS deferred to week 3-4 retrain · **all three markets already in API contract, but BTTS only activated once ECE CI stable <0.05**
2. **[SHIP] Single LightGBM + CalibrationSelector** · ensemble (LGBM+XGB+CatBoost) added post-alpha as v2 candidate via MLflow A/B
3. **[SHIP] Dirichlet calibration for 1X2 with temperature-scaling fallback** when n_val<2000 per fold · beta for OU binary markets
4. **[SHIP] Walk-forward expanding window with 7-day embargo** · minimum 3 folds per experiment · BH-FDR q=0.1 for multiple testing
5. **[SHIP] Fractional Kelly α=0.25 with ECE-dampening** · Bayesian posterior adjustment DEFERRED to post-alpha (3-5% growth gain not worth engineering risk in 2 weeks)
6. **[SHIP] CLV as hero metric, wording tiered by n_bets** (drmat §7.1 rules are non-negotiable legal/ethical floor)
7. **[SHIP] Bi-weekly retrain with human co-sign** (founder + drmat sign-off) for first 30 days · weekly after
8. **[SHIP] MCE alarm at 0.12, ECE vetoat 0.08 7-day rolling, CLV rollback at -3% after 50 bets**
9. **[DEFER] Per-league calibration, per-minute odds, Dixon-Coles goals model, Bayesian Kelly, TabPFN**
10. **[CUT] K-fold CV, calibration fit on training set, per-class binary Platt with renormalization, full Kelly, "70% win rate" in marketing copy**

---

## 1. Markets shipping at launch

### Decyzja 1.1: Ile markets na week 1

**Opinia mleng_a:** 1X2 only — jedno sprawdzone, CLV pipeline stable, not over-engineering.
**Opinia mleng_b:** 2-3 markets — "thin product" z 1 market wygląda na brak wartości dla tipstera.
**Opinia drmat:** Zależy od danych — Dirichlet wymaga n_val≥2000, więc 1X2 wchodzi gdy top-5 lig × 5 sezonów daje próbki.

**Decyzja Leada:** **1X2 + OU_2.5 na week 1, BTTS na week 3 (po walidacji)**.

**Uzasadnienie:** Panel ma 3 markets w mock data — użytkownik zobaczy jeden `market` column i 5-10 picks dziennie z jednego markta wygląda biednie. Ale 3 markets × 14 lig × 2 weeks = nie ma czasu na walidację wszystkich 3. Kompromis: ship 2 (1X2 + OU, oba już w API), BTTS dodajemy po pierwszym cyklu retrain gdy mamy CLV 100+ bets i możemy obronić pełny scope.

### Markets table

| Market | Ship week | Calibration | Rationale |
|---|---|---|---|
| **1X2** | Week 1 | Dirichlet (n_val≥2000) lub temperature (fallback) | Core football market, liquidity, long data history |
| **OU_2.5** | Week 1 | Beta (n_val 500-2000) lub Platt (<500) | Binary easier to calibrate than 3-class, natural daily volume |
| **BTTS** | Week 3 | Beta lub Platt | Technically trivial (target już w `targets.py`), ale ECE CI wymaga 500+ bets z live data |
| ~~AH, Double Chance, CS, HT~~ | **[CUT]** | — | Post-alpha scope — każdy dodatkowy market to nowy CLV pipe, kalibracja, monitoring |

### Coverage

14 lig z istniejącego scope (5 Top-5 + 9 Tier 2). **Nie dodajemy nowych lig w alpha** — scope jest już mocno rozciągnięty, więcej lig = więcej ECE CI pracy.

---

## 2. Model architecture

### Decyzja 2.1: Single model vs ensemble

**Opinia mleng_a:** Single LightGBM (multiclass 1X2, binary OU/BTTS) · ensemble post-alpha · Pi 4GB RAM constraint.
**Opinia mleng_b:** Single LGBM w alpha + ensemble jako v2 candidate w MLflow · A/B test w tle podczas alpha.
**Opinia drmat:** Log-loss training, LightGBM objective correct · **10× bagging dla predictive variance** (wymaga do §4.3 Bayesian Kelly — ale ta część deferred, więc bagging optional).

**Decyzja Leada:** **Single LightGBM, BEZ 10× bagging na start**. Bagging włącza się w retrain 2 gdy mamy live telemetry.

**Uzasadnienie:** Bagging × 10 × 3 markets × 14 leagues × 3 seeds × 18 walk-forward folds = 22,680 runs dla hyperparameter search. Nawet jeśli single run = 30s na Dev PC, to 190h pracy. Nie mamy tego budżetu. **Single model z seed=42 reproducibility + early stopping** wystarczy na alpha. Bagging włączamy gdy drmat pchnie Bayes-corrected Kelly w v2.

### Architecture config (canonical)

```yaml
model:
  type: lightgbm
  objective:
    1x2: multiclass  # num_class=3
    ou_2_5: binary
    btts: binary
  n_estimators: 2000
  learning_rate: 0.03
  max_depth: 6
  num_leaves: 31
  min_child_samples: 20
  reg_alpha: 0.1
  reg_lambda: 0.1
  feature_fraction: 0.8
  bagging_fraction: 0.8
  bagging_freq: 5
  early_stopping: 100
  seed: 42
features:
  pool: 935  # z packages/ml-in-sports
  max_after_selection: 200
  selection: shap_quantile_0.8  # first-pass LightGBM trained on train only
```

**Forbidden:**
- `bagging: 10` (defer)
- Stacked ensemble (defer)
- TabPFN (Pi ARM constraint + overconfidence risk per research backlog)
- Neural nets

---

## 3. Calibration strategy

### Decyzja 3.1: Dirichlet vs simpler dla 1X2

**Opinia mleng_a:** Isotonic + Platt fallback — dostajemy ECE<0.05 bez adding dependencies.
**Opinia drmat:** **Dirichlet calibration dla 1X2 jest principled choice** · per-class binary Platt + renormalize **breaks propriety** · systematycznie under-calibrates draw.
**Opinia mleng_b:** (Zgadza się z drmat na calibrację · product story "calibrated probabilities" wymaga nie tylko ECE≤0.05 ale też wymaga pokazania reliability diagram per-market).

**Decyzja Leada:** **Dirichlet dla 1X2 GDY n_val≥2000, temperature scaling jako automatyczny fallback gdy mniej**. Zero per-class binary Platt — drmat's hard rule.

**Uzasadnienie:** Drmat jest right że per-class binary + renormalize jest numerycznie złe — to nie opinion, to proof. Dirichlet gain jest umiarkowany (ECE drop 0.003-0.008) ale ADR-0007 już ma selector pattern — wystarczy dodać `dirichlet` do candidates. Cost = zero (selector picks best per fold). Temperature scaling jest 1-param floor safe nawet w early folds.

### Calibration matrix

| Market | Primary method | Fallback trigger | Fallback |
|---|---|---|---|
| 1X2 | Dirichlet | n_val<2000 | Temperature scaling |
| OU_2.5 | Beta | n_val<500 | Platt |
| BTTS | Beta | n_val<500 | Platt |

**Per-league calibration: DEFERRED** (drmat §2.3 — per-group granularity with n_val ≈ 16 samples calibrates noise). Pool leagues until n_league≥500 per market.

### ECE variant for reporting

**Use ACE (Adaptive Calibration Error, equal-mass bins, 15 bins)** for promotion gates — reduces variance on skewed p distributions.
**Use ECE** on landing page (audience recognition).
**Use MCE (Maximum Calibration Error)** for safety alarm — worst bin triggers rollback.

---

## 4. Walk-forward backtest spec

### Decyzja 4.1: Embargo length

**Opinia mleng_a:** 7 days (standard).
**Opinia drmat:** **7 days minimum, non-negotiable** · team form + odds autocorrelation ~5-10 days.
**Opinia mleng_b:** N/A — deferred to mleng_a/drmat.

**Decyzja Leada:** **7 days embargo, hard requirement w CI** (walk-forward CV leakage detector w ADR-0011).

### Walk-forward config (canonical)

```yaml
cv:
  strategy: walk_forward_expanding
  embargo_days: 7
  min_folds: 3
  fold_boundary: season_and_winter_break  # mid-season if regime change
  window: expanding  # NOT rolling (football signal structural)
validation_split:
  fraction: 0.15
  location: inside_fold  # NOT on full train — drmat §3.1 hard no on leakage
seasons_included: [2019, 2020, 2021, 2022, 2023, 2024, 2025]
```

### Multiple testing correction

**BH-FDR at q=0.1** across all runs logged to MLflow. `BH_adjusted_p < 0.1` gates promotion — not raw p<0.05. This is drmat §3.3 rule, non-negotiable.

### Leakage detection

Beyond ADR-0011 features leakage, add to CI:
1. **CV fold-order assertion** — test set matches always post-train cutoff
2. **`PreMatchFeature` vs `PostMatchSignal` type split** — mypy-level separation so closing odds can never reach training
3. **Opening odds snapshot validation** — merge keys use opening odds, not single-row post-match

---

## 5. Kelly portfolio strategy

### Decyzja 5.1: Fractional Kelly α

**Opinia mleng_a:** 25% α, 3% per-match cap (ADR-0008 standard).
**Opinia mleng_b:** **Quarter-Kelly jako "podatek pokory"** — user retention > log-growth w niewalidowanym modelu.
**Opinia drmat:** 25% OK ale "fraction of ECE" jest heurystyką · principled form: Bayes-corrected Kelly via predictive variance · **+5-15% growth upside po validation**.

**Decyzja Leada:** **α=0.25 z ECE-dampening w alpha. Bayesian posterior Kelly DEFERRED do v2 model** (post-alpha iteration 2).

**Uzasadnienie:** Drmat ma rację że Bayesian jest lepszy math-wise, ale potrzebuje 10× bagging infrastructure którego nie shipujemy (§2.1). Engineering cost > mathematical gain w 2-tygodniowym oknie. ECE-dampening jest "acceptable floor" per drmat §9 point 2.

### Constraint set (final)

```yaml
kelly:
  fraction: 0.25  # base α
  uncertainty_adjustment: ece_dampen  # (1 - ECE) multiplier
  # bayes_posterior_var deferred to post-alpha
  constraints:
    per_match: 0.03  # 3% bankroll
    per_round: 0.10
    per_league: 0.15
    per_correlation_cluster: 0.12  # cluster by (league, kickoff_date) — drmat §4.2
    total_exposure: 0.25  # hard cap
```

### Portfolio covariance

**Simple diagonal Σ w alpha** (assume uncorrelated). Ledoit-Wolf shrinkage deferred. Constraints alone dają ~80% benefit per drmat §10.

---

## 6. Experiment YAML specs (create these files)

Dla mleng — konkretne files do utworzenia w `experiments/` w monorepo:

### 6.1 `experiments/alpha_baseline_1x2.yaml`

Użyj spec z drmat §6.1 verbatim. To jest canonical Alpha config.

### 6.2 `experiments/alpha_baseline_ou25.yaml`

Identyczny do 1x2 ale:
- `market: ou_2_5`
- `objective: binary`
- `num_class: 2`
- `calibration.candidates: [temperature, platt, beta]`
- `gates.ace_overall.max: 0.04` (tighter, binary easier)

### 6.3 `experiments/alpha_calibration_ablation.yaml`

Użyj spec z drmat §6.2 — grid search nad calibration methods. Trzeba uruchomić **przed** baseline żeby validate że CalibrationSelector dobrze się zachowuje.

### 6.4 `experiments/alpha_kelly_variants.yaml`

Użyj spec z drmat §6.3 ale **ogranicz grid**:
- Wywal `bayes_posterior_var` z `uncertainty_adjustment` (nie mamy bagging)
- Testuj tylko `{none, ece_dampen}` żeby nie tracić czasu
- Keep constraints grid żeby walidować defaults

### 6.5 NIE TWORZYĆ w alpha:

- `experiments/alpha_btts.yaml` — deferred do week 3
- `experiments/alpha_ensemble.yaml` — post-alpha v2
- `experiments/alpha_dixon_coles.yaml` — Phase 2 goals model
- `experiments/alpha_bayesian_kelly.yaml` — v2 after 10× bagging

---

## 7. Monitoring + alerting baseline

### Telemetry (every bet logged to Postgres + MLflow)

| Field | Frequency | Purpose |
|---|---|---|
| `log_loss` per pick | per-pick | Training / promotion |
| `brier_score` | per-pick | Sharpness |
| `p_model` raw | per-pick | Audit |
| `p_calibrated` | per-pick | What we bet on |
| `p_market_close` | post-match | CLV reference |
| `clv` | post-match | Live edge signal |
| `kelly_fraction_applied` | per-pick | Audit |
| `calibration_method_used` | per-pick | Audit |

### Alarms (Telegram to founder)

| Alarm | Condition | Window | Action |
|---|---|---|---|
| **ECE drift** | rolling ECE > 0.08 | 7d | Warning · human review |
| **CLV collapse** | rolling CLV < -3% | 14d (post 50 bets) | AUTOMATIC ROLLBACK (mleng.md MLOps rule) |
| **Log-loss drift** | vs backtest mean > 3σ | 7d | Warning |
| **Prediction count drop** | 0 bets for 3 match days | 3d | AUTOMATIC ROLLBACK |
| **MCE alarm** | any bin MCE > 0.12 | 7d | Warning · human review |
| **Posterior variance explosion** | median > 2× backtest median | 7d | Warning (when bagging shipped) |

### Rollback triggers

From mleng.md MLOps pattern 2:
- ECE > 0.08 for 7 consecutive days → rollback + alert
- CLV < -3% on last 50 placed bets → rollback + alert
- 0 predictions for 3 consecutive match days → rollback + alert (pipeline diagnosed broken)

---

## 8. Timeline to launch (realistic)

**Current date: 2026-04-22 · Target launch: 2026-05-06 (2 weeks)**

### Week 1 (2026-04-22 → 2026-04-28)

- **Day 1-2:** Mateusz Pi setup (A-07+A-08)
- **Day 1-3:** mleng creates `experiments/alpha_baseline_1x2.yaml` + runs baseline
- **Day 3-4:** Calibration ablation run, CalibrationSelector validation
- **Day 4-5:** `experiments/alpha_baseline_ou25.yaml` + run
- **Day 5-7:** Kelly variants experiment, pick final constraints

**Deliverable Week 1:** 2 production model candidates (1X2 + OU) w MLflow staging · all ECE CI upper ≤ 0.05 · DeLong BH-adjusted p<0.1 vs naive baseline

### Week 2 (2026-04-29 → 2026-05-05)

- **Day 1-2:** Promotion gate review (drmat + Mateusz co-sign)
- **Day 2-3:** Deploy model to Pi (A-17)
- **Day 3-5:** Smoke test — evening pipeline produces picks, Telegram bot sends
- **Day 5-6:** Monitoring alerts wired (A-13), dashboard screens
- **Day 6-7:** A-37 landing iteration (user), A-48 beta outreach DM prep

**Deliverable Week 2:** Production model on Pi · daily Telegram slip working · monitoring alerts live · first 5-10 beta users invited

### Week 3 (after launch, ongoing)

- First retrain cycle (bi-weekly)
- BTTS model experiment + validation
- Beta user interviews (A-48 execute)
- CLV data accumulates — landing page claims upgrade from "Starting soon" to "n=X bets tracked"

---

## 9. Landing page claims wording

**Non-negotiable — drmat §7.1 rules:**

### Before 100 bets settled
> "Tracking in progress. n=[X] bets settled. Point estimate: CLV=+X.X%. Not yet statistically significant. Target: 500 bets for 95% confidence."

### 100 ≤ n < 500 bets
> "CLV point estimate: +X.X% (95% CI: [L, U], n=[X]). Confidence interval still includes zero — beat-the-close claim not yet statistically significant."

### n ≥ 500 and CI excludes zero
> "Measured CLV: +X.X% (95% CI: [L, U], n=[X], one-sided t-test p=0.XX). By standard sports-betting methodology, positive CLV is evidence of true edge against the closing market."

### n ≥ 500 and CI includes zero
> "Measured CLV: +X.X% (95% CI includes 0, n=[X]). We do not claim statistically proven edge. Continuing evaluation."

### Alternative — Bayesian posterior (preferred dla tipster audience)

> "Posterior probability of true edge: XX% (based on n=[X] settled bets, weakly informative prior)."

### **FORBIDDEN on landing page**

- "70% win rate" · "+15% ROI" · "Kelly-optimal sizing" (bez α=0.25 disclosure) · "Our model beats Pinnacle" przed n≥500 z CI strictly >0

---

## 10. Retrain cadence + promotion gates

### Decyzja 10.1: Weekly vs bi-weekly retrain

**Opinia mleng_a:** Monthly — signal strukturalny, weekly = noise chase.
**Opinia mleng_b:** **Bi-weekly** z human co-sign przez pierwsze 30 dni.
**Opinia drmat:** Weekly mathematically prefered dla drift alignment — ale sygnał słaby przy n=60 bets/week.

**Decyzja Leada:** **Bi-weekly z obowiązkową human gate** (founder + drmat co-sign) przez pierwsze 30 dni. Weekly rozważamy po 60 dni gdy mamy stable telemetry.

**Uzasadnienie:** Weekly retrain z słabym sygnałem = weekly risk push silently-worse model. mleng_b's "weekly risk" argument jest engineering-realistic. Drmat sam przyznaje (§9 point 3) że "n<500 bet sygnał do retreningu jest słaby".

### Promotion gates (pre-production)

Kandydat musi przejść **wszystkie**:

1. ✅ `log_loss ≤ incumbent − δ_LL` (DeLong BH-adjusted p < 0.1)
2. ✅ `ACE ≤ 0.05` across markets (bootstrap 95% CI upper < 0.06)
3. ✅ `ACE_per_league ≤ 0.10` (per-group sanity)
4. ✅ `CLV ≥ 0` point estimate na walk-forward
5. ✅ `SHAP top-10 overlap ≥ 70%` vs current production (stability)
6. ✅ `sl leakage run` (ADR-0011) — zero positive signals
7. ✅ Human review: Mateusz + drmat co-sign w MLflow run description

**Zero tolerance na "fix next week"** — per mleng.md MLOps pattern 1.

---

## 11. Risk escalation playbook

Z mleng_b, adopted.

### Tydzień 1 live — CLV negative

- Day 3-5: monitor, no action (variance)
- Day 6-10: if -1% to -3%, human review — check per-league, identify culprit
- Day 11-14: if < -3% @ 50+ bets, AUTOMATIC ROLLBACK per monitoring

### Jeśli ECE drift (>0.08 7d)

1. Freeze retrain (don't push new model)
2. Spin up calibration ablation on last 30d data
3. Hotfix calibrator (keep underlying model)
4. Re-deploy within 48h or rollback model

### Jeśli 0 predictions for 3 consecutive days

1. Pipeline diagnosed broken → rollback model + alert
2. Force drift check on features (PSI)
3. Scraper audit: data stale?

### Beta user escalation

Jeśli beta user zgłosi "picks za dużo / za mało" — log feedback w `docs/alfa/beta_feedback_log.md`, nie react indywidualnie (N=1 anegdota).

---

## 12. Explicit anti-goals (NIE robimy w alpha)

### Math rigor anti-goals (drmat zgada się tu z mleng kompromisami)

- Per-class binary Platt + renormalize (breaks propriety)
- K-fold CV na time-series
- Calibrator fit on full training set (leakage)
- Full Kelly α=1.0
- Closing odds w features
- DeLong test automated w CI (manual per-promotion OK)

### Product scope anti-goals (mleng_b agresywny filtering)

- Asian Handicap / Double Chance / Correct Score / HT markets
- Per-minute live odds tracking
- Lineup-based adjustment
- Injury news integration
- TabPFN in production stack (Pi ARM)
- Neural networks
- Real-time inference (daily batch OK)

### Engineering scope anti-goals

- Multi-sport (football only w alpha)
- Multi-tenant model sharding
- Custom MLflow UI extensions
- Auto-hyperparameter search (fixed configs)
- Dixon-Coles goals model (Phase 2)
- Bradley-Terry tennis model (Phase 4)

---

## 13. Open questions (wymagają decyzji post-alpha)

1. **Bankroll unit dla Telegram slip** — per-user bankroll (panel setting) czy notional 10,000 EUR? (mleng_a blind spot #5)
2. **Fixture calendar gaps** — jak Pi wie że jest international break żeby nie triggerować "0 predictions 3 days" rollback? Wymaga fixture lookahead query.
3. **League vs market priority** jeśli ECE drift w jednej kombinacji — czy rollback tylko dla Premier League 1X2 czy globalnie?
4. **Beta feedback loop** — A-48 interviews → jakie sygnały promują model change (vs "user preference")?
5. **First published week imperfection disclosure** (mleng_b kontrowersyjne stanowisko) — ship honest "known miscalibration on Serie B" note, czy udawać perfekcję?

**Founder's answer na #5:** **Ship honest disclosure**. mleng_b ma rację — transparent imperfection buduje trust lepiej niż fabricated perfection. Week 1 debrief PDF dla beta users zawiera sekcję "What didn't work this week".

---

## 14. Decision tags summary

### [SHIP] — must-have przed launch

- 1X2 + OU_2.5 markets
- Single LightGBM + CalibrationSelector
- Dirichlet for 1X2 (fallback temperature), Beta for OU
- Walk-forward 7d embargo + 3 folds min + BH-FDR
- α=0.25 Kelly + ECE-dampening + portfolio constraints
- CLV hero + tiered claims wording
- Bi-weekly retrain + human co-sign 30d
- Monitoring alerts (ECE 0.08, CLV -3% 50bets, 0 preds 3d)

### [DEFER] — post-alpha v2

- BTTS market (week 3)
- 10× bagging + Bayes-corrected Kelly
- Dirichlet per-league (when n_league > 500)
- Ensemble LGBM+XGB+CatBoost (A/B)
- Ledoit-Wolf covariance shrinkage
- Dixon-Coles goals model
- Weekly retrain cadence
- MLflow automation of DeLong test
- PSI drift monitoring (currently TBD)

### [CUT] — explicit anti-goals

- Per-class binary Platt renormalize (math error)
- K-fold CV on time-series (cardinal sin)
- Calibration fit on train set (silent leakage)
- Full Kelly α=1.0 (ruin risk)
- Closing odds w features (target leakage)
- TabPFN in prod (Pi constraints)
- "70% win rate" marketing copy
- Asian Handicap / Double Chance / Correct Score w week 1
- Multi-sport w alpha

---

## Appendix: References to original drafts

- `docs/alfa/ml_experiments_draft_mleng_a.md` — 669 lines, practical engineering perspective
- `docs/alfa/ml_experiments_draft_mleng_b.md` — 481 lines, product/trust-first filtering
- `docs/alfa/ml_experiments_draft_drmat.md` — ~520 lines, math/stats authority

**Lead's judgment calls beyond reviewers (founder opinion):**

1. **Bi-weekly retrain (mleng_b direction)** over weekly (alpha_launch_plan.md spec) — operational safety > theoretical optimum
2. **First-week imperfection disclosure** (mleng_b position) — committing to this as founder
3. **BTTS ship week 3 not week 1** — splitting difference between mleng_a (1X2-only) and mleng_b (3 markets)
4. **Bayesian Kelly deferred** — drmat will push back, but 2-week runway beats 5-15% growth gain

---

**Next operational step for mleng:** Create `experiments/alpha_baseline_1x2.yaml` matching drmat §6.1 spec, run `sl backtest run experiments/alpha_baseline_1x2.yaml --mlflow` with a single seed. Target first MLflow run by 2026-04-24 (2 days).
