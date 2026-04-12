# ADR-0017: Dual-machine architecture (Raspberry Pi 4 + Dev PC)

- **Status**: Accepted
- **Date**: 2026-04-06
- **Deciders**: `lead`, `architect`

## Context

The original alpha launch plan (see `docs/alpha_launch_plan.md`) specified a Hetzner CX32 VPS
(22 EUR/month) as the single production server for training, inference, scraping, Postgres, and
Telegram delivery. The founder decided to replace this with a dual-machine setup using hardware
already owned:

1. **Raspberry Pi 4 (4 GB RAM, ARM aarch64)** -- production: daily pipeline, inference, Postgres,
   Telegram notifications.
2. **Dev PC (powerful, x86_64)** -- training, experiments, feature engineering, MLflow server.

This eliminates the 22 EUR/month Hetzner cost and introduces MLflow as the model registry
(previously deferred to R5 in the plan, now pulled forward because the dual-machine topology
requires explicit model promotion).

### Key constraints

- Pi 4 has 4 GB RAM and an ARM CPU. TabPFN requires PyTorch (~2 GB), which is impractical on
  the Pi. **[PEWNE]** TabPFN is already an optional dependency (ADR-0014) so the Pi installs
  without it.
- Training LightGBM on 95k rows requires ~2-3 GB RAM. Combined with Postgres overhead on a
  4 GB device, this is too tight. **[RYZYKO]** Training must stay on the dev PC.
- Inference (loading a pre-trained model + predicting on today's matches) requires <500 MB.
  This fits on the Pi.
- The dev PC is not always on. It runs when the founder is experimenting. The Pi runs 24/7.
- The two machines must be on the same LAN for SSH model transfer, or the dev PC must push
  models to the Pi before going offline.

## Options considered

1. **Hetzner CX32 VPS (original plan)** -- single cloud server for everything.
   - Pros: always-on, no LAN dependency, public IP for Cloudflare Tunnel, simple single-machine
     architecture.
   - Cons: 22 EUR/month recurring, still no experiment tracking, dev PC sits idle.

2. **Raspberry Pi 4 only** -- everything on the Pi (training + inference + Postgres).
   - Pros: zero cost, single machine.
   - Cons: 4 GB RAM is insufficient for training + Postgres simultaneously, ARM excludes
     TabPFN entirely, no room for MLflow, training would take 5-10x longer than dev PC.

3. **Dual-machine: Pi (production) + Dev PC (training/experiments)** -- split by workload.
   - Pros: zero recurring cost, dev PC handles heavy compute, Pi handles lightweight 24/7
     production, MLflow on dev PC provides experiment tracking for free.
   - Cons: model sync between machines needs a mechanism (SSH/SCP), dev PC must be on for
     training sessions, two machines to maintain.

4. **Dev PC only with Docker** -- run everything on the dev PC, no Pi.
   - Pros: maximum compute, single machine.
   - Cons: dev PC must be on 24/7 for cron pipeline (impractical -- Windows sleep, reboots,
     power cost), not designed as a server.

## Decision

We choose **Option 3: Dual-machine architecture (Pi + Dev PC)** because:

1. **Cost**: eliminates 22 EUR/month Hetzner bill. Total recurring cost drops to ~1 EUR/month
   (domain only). The Pi and dev PC are already owned.
2. **Separation of concerns**: the Pi is a production appliance (always-on, minimal software,
   deterministic cron). The dev PC is a workbench (experiments, MLflow, heavy training). These
   are different failure domains with different uptime requirements.
3. **MLflow comes free**: the dev PC has ample resources to run MLflow. This accelerates
   experiment tracking from "deferred to R5" to "available now." Supersedes the prior plan's
   "no MLflow" stance (section 3.1 of the old alpha launch plan, section 4.4).
4. **ARM-compatible stack**: LightGBM and XGBoost both have ARM wheels. The inference-only
   path (`model.predict()`) works natively on aarch64. TabPFN is excluded by ADR-0014's
   optional dependency pattern.

### Model sync mechanism

**SCP over SSH (Option a)** is the chosen transfer method. After promoting a model to
"Production" in the MLflow Model Registry, the founder (or a script) runs:

```bash
scp /path/to/mlflow-artifacts/model.pkl pi@<pi-ip>:/app/models/production/model.pkl
```

This is the simplest mechanism that works on a LAN. No shared folders (SMB/NFS adds config
complexity), no MLflow model serving over HTTP (overkill for one consumer), no git-lfs (adds
repo bloat). **[PEWNE]** SCP over SSH is the boring, proven choice.

**Why not MLflow model serving?** MLflow's `mlflow models serve` runs a Flask server that
serves predictions over HTTP. This would mean running MLflow on the Pi (defeats the purpose)
or keeping the dev PC always-on as a model server (unreliable). SCP decouples the two machines:
the model file is a static artifact on the Pi's filesystem.

### MLflow configuration

MLflow runs on the dev PC with the simplest possible backend:

- **Tracking URI**: `sqlite:///mlflow.db` (SQLite file, zero maintenance)
- **Artifact store**: `./mlflow-artifacts/` (local filesystem)
- **UI**: `http://localhost:5000` (accessible only from dev PC)

No remote tracking server, no S3 artifact store, no Postgres backend for MLflow. These are
all upgrades that can be made later if needed. **[HIPOTEZA]** if the founder wants to access
MLflow UI from another device on the LAN, binding to `0.0.0.0:5000` is a one-flag change.

## Consequences

- **Positive**: monthly cost drops from ~23 EUR to ~1 EUR. MLflow experiment tracking is
  available immediately instead of being deferred to R5. Clean separation between production
  (stable, minimal) and development (experimental, heavy).
- **Positive**: Pi's low power consumption (~5W) means 24/7 operation costs essentially nothing
  in electricity.
- **Negative**: model sync is a manual step (or scripted but still initiated by the founder).
  If the founder forgets to push a new model, the Pi runs the old one. Mitigated by: the Pi
  logs which model file it loaded (path + hash) in the morning pipeline output.
- **Negative**: two machines to maintain (OS updates, disk space, network). Acceptable for a
  solo founder who already owns both devices.
- **Negative**: Pi 4 with 4 GB RAM leaves ~2-2.5 GB for the application after OS + Postgres.
  This is sufficient for inference but leaves no headroom for accidental memory spikes.
  **[RYZYKO]** If Postgres + inference exceeds 3.5 GB, the OOM killer fires. Mitigation:
  configure Postgres `shared_buffers=256MB`, `work_mem=32MB` (conservative settings for 4 GB).
- **Neutral**: Hetzner CX32 remains an option. If the Pi proves unreliable (network issues,
  SD card corruption, thermal throttling), the migration to Hetzner is a half-day task:
  provision VPS, restore from B2 backup, update cron.

## Supersedes

- Section 2.1 of `docs/alpha_launch_plan.md` (Hetzner CX32 specification)
- Section 3.1 of `docs/alpha_launch_plan.md` (file-based model storage, no MLflow)
- Section 4.4 of `docs/alpha_launch_plan.md` (MLflow deferred to R5)
- Linear issue SPO-71 (R4.1 -- Hetzner VPS setup) needs to be updated to reflect Pi setup
- Section 12 row "MLflow vs custom model registry" is no longer deferred

## References

- ADR-0010: Solo founder roadmap
- ADR-0013: Cron over Prefect for orchestration
- ADR-0014: TabPFN as optional dependency
- `docs/alpha_launch_plan.md`
- Linear: SPO-71 (R4.1), SPO-72 (R4.2), SPO-73 (R4.3)
