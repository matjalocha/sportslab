# Tooling — Phase 0

**Cel:** Ustawić wszystkie narzędzia, których zespół będzie używał przez kolejne fazy. Decyzje, dostępy, konfiguracje.

## Narzędzia według kategorii

### 1. Koordynacja pracy
| Narzędzie | Zastosowanie | Cost | Owner |
|---|---|---|---|
| **Linear** | Task tracking, sprinty, issues | Free < 10 users, Plus $8/user | Lead |
| **Slack** (lub Discord) | Komunikacja sync + async | Slack Free / Pro $7.25, Discord free | Lead |
| **Notion** | Wiki, notatki, planowanie luźne | Free Personal, Plus $10/user | Lead |
| **Google Workspace** | Email, Docs, Drive, Meet | $6/user/m-c Business Starter | Lead |
| **Figma** | Design, wireframes, handoff | Free 3 projects, Pro $12/editor | Designer |

### 2. Kod i wersjonowanie
| Narzędzie | Zastosowanie | Cost | Owner |
|---|---|---|---|
| **GitHub** | Repo, PRs, Actions, Projects | Free Public, Team $4/user | SWE |
| **uv** | Python package manager | Free | SWE |
| **pnpm** | JS package manager | Free | SWE |
| **pre-commit** | Git hooks | Free | SWE |
| **ruff** | Python linter + formatter | Free | MLEng |
| **mypy** | Python type checker | Free | MLEng |
| **eslint + prettier** | TS linting + formatting | Free | SWE |

### 3. ML / Data
| Narzędzie | Zastosowanie | Cost | Owner |
|---|---|---|---|
| **MLflow** | Model registry + tracking | Free (self-hosted) | MLEng |
| **DVC** (opcjonalnie) | Data versioning | Free + cloud storage | MLEng |
| **Jupyter** | Research notebooks | Free | DrMat |
| **Optuna** | Hyperparameter search | Free | MLEng |
| **Weights & Biases** (opcjonalnie) | Eksperymentacja | Free Personal, Team $50/m-c | MLEng |
| **Great Expectations** | Data quality | Free | DataEng |
| **Prefect** lub **Dagster** | Orkiestracja (Faza 5) | Free self-hosted, Cloud $0-$450/m-c | DataEng |

### 4. Infrastruktura
| Narzędzie | Zastosowanie | Cost | Owner |
|---|---|---|---|
| **Hetzner Cloud** | VPS | €4-50/m-c per VPS | SWE |
| **Cloudflare** | DNS, CDN, DDoS | Free | SWE |
| **Backblaze B2** | Object storage (backup) | $6/TB/m-c | DataEng |
| **Doppler** | Secrets management | Free, Team $7/user | SWE |
| **1Password Teams** | Credentials | $7.99/user/m-c | Lead |
| **Better Stack** | Monitoring + logs | Free, Pro $22/m-c | SWE |
| **Grafana Cloud** (alternatywa) | Monitoring | Free 10k series | SWE |
| **RunPod / Lambda** | GPU on-demand (TabPFN) | ~$0.20-0.50/h | MLEng |

### 5. Billing / Sales (Faza 6)
| Narzędzie | Zastosowanie | Cost | Owner |
|---|---|---|---|
| **Stripe** | Payments + invoicing | 1.4% + 0.25€ per transaction | Lead |
| **Clerk** lub **Auth0** | Auth | Clerk free 10k MAU, Auth0 free 7.5k MAU | SWE |
| **Customer.io** lub **Resend** | Transactional emails | Resend $20/m-c 50k emails | SWE |
| **Tally** lub **Typeform** | Forms (leadgen, waitlist) | Free / $29/m-c | Lead |
| **Calendly** | Sales call booking | Free / $10/m-c | Lead |

## Dostępy i role

### Linear
- **Admin**: Lead
- **Members**: wszyscy z zespołu + prawnik (read-only, opcjonalnie)
- **Projekty**: P0 Foundations, P1 Code Cleanup, ..., P6 Product & App
- **Labels**: `type:task`, `type:bug`, `type:research`, `type:spike`, `priority:urgent/high/med/low`, `persona:lead/drmat/mleng/dataeng/swe/designer`

### GitHub
- **Admin**: Lead
- **Maintainers**: SWE, DataEng, MLEng
- **Members**: DrMat, Designer (write access), reszta (read)
- **Teams**: `engineering` (MLEng, DataEng, SWE), `research` (DrMat, MLEng), `design` (Designer, SWE)

### 1Password vaults
- **Personal**: każdy użytkownik (osobiste)
- **Infrastructure**: SWE, DataEng, Lead (API keys, VPS SSH)
- **Bookmakers**: Lead, DataEng (login credentials)
- **Marketing/Sales**: Lead (Stripe, analytics)
- **Shared**: wszyscy (Figma, Slack, Linear creds)

### Domain + Email
- **Główna domena**: `sportslab.xyz` (lub inna, decyzja P0.24)
- **Email**: `hello@`, `support@`, `sales@`, `engineering@`, indywidualne `<imię>@`
- **Alternatywne domeny**: `.com` (rezerwa, brandingowa), `.ai` (premium, marketing)

## Szacunkowy koszt miesięczny narzędzi (P0-P2)

| Kategoria | Koszt (€/m-c) |
|---|---|
| Google Workspace (6 users × Business Starter) | ~35 |
| Slack Pro (6 users) | ~40 |
| Linear Plus (gdy zacznie brakować free) | ~50 |
| GitHub Team | ~25 |
| Figma (2 editors: Designer + SWE) | ~22 |
| 1Password Teams (6 users) | ~50 |
| Hetzner VPS (1 staging CX32) | ~20 |
| Cloudflare | 0 |
| Backblaze B2 (100 GB backup) | ~1 |
| Doppler (team) | ~40 |
| Domain + SSL | ~2 |
| **RAZEM (P0-P2)** | **~285 €/m-c** |

**P3+**: dodajemy production VPS (~€50), większe Backblaze (~€20), może Grafana Cloud (€0-60). **Razem ~€370 €/m-c.**

**P5+**: dodajemy GPU bursts (zmienne, ~€50-200), Prefect Cloud (€0-450). **Razem ~€500-1000 €/m-c.**

**P6+**: dodajemy Stripe (% od transakcji), Clerk/Auth0 (free), email provider (~€20), monitoring Pro (~€50). **Razem ~€600-1200 €/m-c.**

## Checklista setup P0

- [ ] Linear workspace utworzony, projekty P0-P6 założone
- [ ] GitHub organization utworzona, monorepo zainicjalizowane
- [ ] 1Password Teams vault utworzony, struktura vaultów gotowa
- [ ] Google Workspace skonfigurowany, email dla zespołu
- [ ] Figma team utworzony, szablony gotowe
- [ ] Slack workspace + kanały podstawowe
- [ ] Domain kupiona, DNS skonfigurowany w Cloudflare
- [ ] SSL dla wildcard `*.sportslab.xyz`
- [ ] Doppler projekt dla dev/staging/prod
- [ ] Hetzner account + pierwszy staging VPS
- [ ] Backblaze bucket dla backupów
- [ ] Stripe test mode account (produkcja w P6)
- [ ] pre-commit hooks skonfigurowane w root monorepo
