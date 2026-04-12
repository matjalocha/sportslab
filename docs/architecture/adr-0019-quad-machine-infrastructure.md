# ADR-0019: Quad-machine infrastructure (Pi + Dev PC + Laptop + VM)

- **Status**: Proposed
- **Date**: 2026-04-12
- **Deciders**: Architect, Lead, SWE, DataEng

## Context

ADR-0017 established a dual-machine architecture: Raspberry Pi 4 (production) and Dev PC
(training/experiments). The founder now has access to two additional machines:

1. **Laptop** -- capable of running 24/7, more powerful than Pi (8-16 GB RAM, x86_64)
2. **Free powerful VM** -- remote, powerful CPU/RAM, free of charge, persistence TBD

This ADR extends ADR-0017 to assign roles to all four machines, establishing which components
run where, how data flows between them, and what the failure modes are.

### Available machines

| Machine | CPU | RAM | Storage | Always-on? | Network | OS |
|---------|-----|-----|---------|------------|---------|-----|
| **Dev PC** | x86_64, powerful | 16+ GB | Large SSD | No (working hours) | LAN | Windows |
| **Raspberry Pi 4** | ARM aarch64, 1.5 GHz | 4 GB | USB SSD (~120 GB) | Yes (24/7) | LAN | Ubuntu Server 24.04 |
| **Laptop** | x86_64, mid-range | 8-16 GB [DO SPRAWDZENIA] | SSD | Capable (TBD) | LAN + WiFi | TBD [DO SPRAWDZENIA] |
| **Free VM** | x86_64, powerful | Large [DO SPRAWDZENIA] | TBD [DO SPRAWDZENIA] | TBD [DO SPRAWDZENIA] | Remote | Linux |

### Key unknowns [DO SPRAWDZENIA]

Before this ADR can move to Accepted, the founder must confirm:

1. **VM persistence**: Is the VM guaranteed to stay running? Can it be terminated without
   warning? Is data persistent across reboots?
2. **VM network**: Does it have a public IP? Can the Pi reach it? Is Tailscale or SSH
   tunneling feasible?
3. **VM specs**: Exact CPU cores, RAM, disk space, GPU (if any).
4. **VM usage policy**: Is commercial use allowed? Is there a usage time limit?
5. **Laptop specs**: Exact RAM, OS (Windows or Linux), battery health.
6. **Laptop always-on feasibility**: Can it run 24/7 on a shelf without overheating? Can
   battery charge be limited to prevent degradation?

## Options considered

1. **Dual-machine only (Pi + Dev PC) -- status quo ADR-0017**
   - Pros: proven, simple, already documented.
   - Cons: wastes two available machines, Dev PC must handle all training, no redundancy.

2. **Triple-machine (Pi + Dev PC + VM) -- laptop stays idle**
   - Pros: VM handles training + MLflow, Dev PC focuses on development. Pi unchanged.
   - Cons: no backup for Pi. Laptop hardware wasted.

3. **Triple-machine (Pi + Dev PC + Laptop) -- no VM**
   - Pros: laptop as backup for Pi, laptop as scraping fallback. All machines on LAN.
   - Cons: no powerful remote compute for training. Dev PC still handles heavy compute.

4. **Quad-machine (Pi + Dev PC + VM + Laptop) -- all machines have roles**
   - Pros: optimal workload distribution. Pi = production. VM = heavy compute. Dev PC =
     development. Laptop = standby + overflow. Maximum utilization of owned hardware.
   - Cons: four machines to think about. Complexity of data flow between four nodes.

## Decision

We choose **Option 4: Quad-machine architecture** with the following role assignments:

### Role matrix

| Component | Primary machine | Fallback | Rationale |
|-----------|----------------|----------|-----------|
| **Postgres 16 (production)** | Raspberry Pi | Laptop | Pi is 24/7, Linux, stable. Conservative tuning fits 4 GB. |
| **Daily cron pipeline** | Raspberry Pi | Laptop | Lightweight inference, 5W, reliable cron on Linux. |
| **Telegram notifications** | Raspberry Pi | Laptop | Part of daily pipeline, same machine. |
| **healthchecks.io pings** | Raspberry Pi | -- | Integrated in pipeline script. |
| **Backup (pg_dump -> B2)** | Raspberry Pi | -- | Nightly cron, already designed. |
| **Light scraping (FDCOUK, ClubElo)** | Raspberry Pi | -- | Simple HTTP, ARM-compatible. |
| **Model training (LGB/XGB)** | Free VM | Dev PC | VM has more compute; Dev PC is fallback. |
| **TabPFN training** | Free VM | -- | Requires x86_64 + large RAM + optionally GPU. |
| **MLflow server + UI** | Free VM (if persistent) | Dev PC | VM provides always-on MLflow. Dev PC fallback. |
| **Backtest experiments** | Free VM + Dev PC | -- | VM for big runs, Dev PC for quick iterations. |
| **Heavy scraping (Sofascore)** | Dev PC | Laptop | Headless Chrome needs x86_64 + RAM. |
| **Code development (Claude Code)** | Dev PC | -- | IDE + Claude Code, primary work machine. |
| **Standby (Pi backup)** | Laptop | -- | If Pi fails, pipeline moves to laptop in 30 min. |
| **Internal Streamlit dashboard** | Laptop (optional) | -- | Optional monitoring tool, not blocking alpha. |
| **Landing page** | Lovable (hosted) | -- | External, zero local infra. |
| **User panel (post-alpha)** | Lovable or Laptop | -- | Decision deferred to R6. |
| **FastAPI backend (R6)** | Laptop or Hetzner VPS | -- | Not needed for alpha. |

### Data flow

```
+------------------+                    +------------------+
|    FREE VM       |                    |     DEV PC       |
| (compute node)   |                    | (development)    |
|                  |   git pull/push    |                  |
| MLflow server    | <===============> | Claude Code / IDE |
| Model training   |                    | Sofascore scrape |
| Experiments      |                    | Quick experiments |
|                  |                    |                  |
| Tailscale:       |                    | Tailscale:       |
|  100.x.x.1      |                    |  100.x.x.2      |
+--------+---------+                    +--------+---------+
         |                                       |
         | SCP model.pkl                         | SCP sofascore data
         | (after mlflow promote)                | (after scraping)
         v                                       v
+------------------+                    +------------------+
| RASPBERRY PI 4   |                    |     LAPTOP       |
| (production)     |                    | (standby)        |
|                  |                    |                  |
| Postgres 16      |                    | Cold standby     |
| Cron pipeline    |                    | Pi backup         |
| Inference only   |                    | Scraping fallback|
| Telegram notify  |                    | Streamlit (opt)  |
| B2 backup        |                    |                  |
|                  |                    | Tailscale:       |
| Tailscale:       |                    |  100.x.x.4      |
|  100.x.x.3      |                    |                  |
+------------------+                    +------------------+
```

### Networking: Tailscale mesh VPN

**[HIPOTEZA]** Tailscale is the recommended networking layer to connect all four machines:

- Free for personal use (up to 100 devices)
- Each machine gets a stable 100.x.x.x IP
- Works through NAT, CGNAT, firewalls -- no port forwarding needed
- Pi can reach VM (for potential future API calls)
- Dev PC can reach VM MLflow UI (http://100.x.x.1:5000)
- SSH from any machine to any other via Tailscale IPs
- Zero configuration beyond `tailscale up` on each machine

This eliminates the LAN-only limitation of ADR-0017. The VM (remote) becomes reachable
from the Pi (LAN) without public IP configuration, VPN servers, or SSH tunnels.

### Model sync flow (updated from ADR-0017)

```
VM trains model
  -> MLflow logs run (metrics, params, artifacts)
  -> Founder reviews in MLflow UI (Dev PC browser -> http://100.x.x.1:5000)
  -> Founder promotes to "Production" stage in MLflow
  -> SCP from VM to Pi:
     ssh vm "scp /mlflow-artifacts/<run>/model.pkl pi@100.x.x.3:/app/models/production/"
     (or: founder runs deploy script from Dev PC that orchestrates the transfer)
  -> Pi picks up new model on next cron run (06:00)
```

### Failure scenarios

| Failure | Impact | Recovery | Time |
|---------|--------|----------|------|
| Pi dies | Daily pipeline stops | Move pipeline to Laptop. Restore PG from B2. | 1-2h |
| VM dies | Cannot train new models | Fall back to Dev PC for training. MLflow history lost if not backed up. | 30 min |
| Dev PC dies | Cannot develop code | Use Laptop for development. Training continues on VM. | Immediate |
| Laptop dies | No fallback for Pi | Accept risk. Buy replacement or use Hetzner VPS. | 1 day |
| All LAN machines die | Everything stops | Restore from B2 to Hetzner VPS (emergency). | 2-4h |
| Internet dies | Pi works offline (local Postgres, local model). Telegram fails. | Wait for internet. Predictions queued locally. | N/A |

### Power budget

| Machine | Power draw | Monthly cost (0.80 PLN/kWh) | Always-on? |
|---------|-----------|---------------------------|-----------|
| Raspberry Pi 4 | 5-10W | ~3-6 PLN | Yes |
| Laptop (standby) | 5-15W (sleep/idle) | ~3-9 PLN | Mostly sleep |
| Dev PC | 100-300W | 0 (off when not working) | No |
| Free VM | 0W local | 0 PLN | N/A (remote) |
| **Total** | | **~6-15 PLN/month** | |

Versus Hetzner CX32: ~90 PLN/month. Savings: ~75-84 PLN/month.

## Consequences

- **Positive**: monthly infrastructure cost drops to ~6-15 PLN (electricity) + ~5 PLN (domain)
  versus ~95 PLN for Hetzner CX32. All hardware is already owned.
- **Positive**: MLflow on VM is always-on (if VM is persistent), improving experiment tracking
  availability over the Dev-PC-only approach in ADR-0017.
- **Positive**: Laptop as cold standby for Pi provides disaster recovery without additional cost.
- **Positive**: Tailscale mesh connects all machines regardless of network topology.
- **Negative**: four machines to maintain (OS updates, Tailscale, SSH keys). Acceptable for a
  solo founder who is also the sysadmin.
- **Negative**: data flows between four nodes. Model artifacts must be explicitly transferred
  (SCP). No shared filesystem. Mitigated by: the only regular transfer is one model file
  (model.pkl, ~50 MB) per week.
- **Negative**: VM persistence is unknown [DO SPRAWDZENIA]. If VM is ephemeral, MLflow must
  stay on Dev PC and the architecture degrades to triple-machine (Pi + Dev PC + Laptop).
- **Neutral**: Hetzner CX32 remains the emergency fallback. If local infrastructure proves
  unreliable (Pi SD card corruption, Laptop overheating, VM disappearing), migrating to Hetzner
  is a 1-2 hour task from B2 backup.

## Supersedes

- ADR-0017 Section "Decision" (dual-machine scope). ADR-0017 remains valid for the Pi + Dev PC
  core; this ADR extends it with Laptop and VM roles.
- `docs/alpha_launch_plan.md` Section 2.1 should reference this ADR for the full machine
  topology.

## Status conditions

This ADR moves from **Proposed** to **Accepted** when the founder confirms:

1. VM persistence, specs, and network access
2. Laptop specs and always-on feasibility
3. Tailscale is installable on all four machines

Until then, the **minimum viable architecture** is ADR-0017 (Pi + Dev PC) with the Laptop
as informal standby.

## References

- ADR-0017: Dual-machine architecture (Pi + Dev PC) -- extended by this ADR
- ADR-0013: Cron over Prefect for orchestration
- ADR-0016: Alpha delivery via Telegram
- ADR-0018: Monorepo strategy confirmed
- `docs/alpha_launch_plan.md`
- `docs/team_discussion_infra_2026-04-12.md` -- full analysis
