# Team — 6 osób + braki kompetencyjne

## 1. Lead / Founder-Engineer (`Lead`)

**Profil:** Założyciel, 10+ lat w startupach, code-first leadership. Zbudował 2+ firmy, sprzedał min. 1. Umie programować (Python/TypeScript), ale jego główną rolą jest **decyzja produktowa, finansowa, strategiczna i koordynacyjna**.

**Odpowiedzialności:**
- Wizja produktowa, roadmapa, priorytetyzacja (ostateczny decydent)
- Relacje z pierwszymi klientami (sales B2B)
- Finanse (budżet, cashflow, pensje, reinwestycje)
- Rekrutacja kolejnych osób do zespołu (gdy pojawią się gaps)
- Koordynacja tygodniowa (planning, retro, demo)
- Własność Linear workspace + GitHub org
- Pitch inwestorski (gdy nadejdzie potrzeba)

**Nie robi:**
- Nie implementuje feature'ów (chyba że prototyp/spike)
- Nie optymalizuje modeli (to ML Eng)
- Nie projektuje UI (to Designer)

**Narzędzia:** Linear (power user), Notion, Stripe dashboard, Google Analytics, Miro

---

## 2. Dr matematyki, specjalizacja sporty (`DrMat`)

**Profil:** Doktorat z matematyki stosowanej lub statystyki. 20 lat zainteresowania sportem (aktywny obserwator piłki, tenisa, koszykówki). Pisze publikacje o modelowaniu wyników sportowych. Zna teorię Kelly'ego, Bayesa, probability calibration do poziomu akademickiego.

**Odpowiedzialności:**
- **IP matematyczne projektu** — wymyślenie i udokumentowanie autorskiego podejścia (`ip_moat.md`)
- Kalibracja modeli (Platt, isotonic, beta, dirichlet)
- Portfolio Kelly z ograniczeniami + shrinkage Bayesowski
- Weryfikacja statystyczna modeli (CLV vs Pinnacle, walk-forward, SHAP stability)
- Design eksperymentów (Optuna searches, cross-validation strategies)
- Collaborations z ML Eng przy feature engineering
- Goals/Poisson model, Dixon-Coles, Bradley-Terry dla tenisa
- Consulting przy custom research dla klientów (P6)

**Nie robi:**
- Nie pisze production kodu (ML Eng robi implementacje)
- Nie touchuje infrastruktury (DevOps, CI/CD)
- Nie projektuje UI

**Narzędzia:** Jupyter, LaTeX, R (jeśli preferuje), PyMC, Stan, Scipy

---

## 3. Senior ML Engineer (`MLEng`)

**Profil:** 20 lat doświadczenia. Pracował w finansach/adtech/sportach. Zbudował min. 1 production ML system obsługujący >1M requestów dziennie. Zna MLOps — MLflow, model registry, feature store, monitoring driftu.

**Odpowiedzialności:**
- Architektura modeli (ensemble, stacking, meta-learning)
- Implementacja IP od DrMat (zamienia whiteboard na kod)
- Feature engineering pipeline (`src/ml_in_sports/features/`)
- Model training pipelines (retraining cadence, versioning)
- Model registry + versioning (MLflow / DVC)
- Feature store (Feast lub własny na Postgres)
- Monitoring modeli — ECE, feature drift, label drift, odds drift
- Eksperymentacja (TabPFN, CatBoost, stacking ensemble)
- Performance optimization (GPU inference, batch prediction)
- Współpraca z Data Eng przy schemacie features

**Nie robi:**
- Nie projektuje matematycznie (to DrMat)
- Nie touchuje frontendu
- Nie obsługuje bukmacherów

**Narzędzia:** Python, LightGBM/XGBoost/CatBoost, TabPFN, PyTorch, MLflow, DVC, Optuna, SHAP

---

## 4. Senior Data Engineer (`DataEng`)

**Profil:** 20 lat doświadczenia. Zbudował hurtownie danych, pipeline'y ETL, orkiestrację Airflow/Prefect/Dagster. Zna SQL (Postgres, Timescale), DuckDB, Parquet, streaming (Kafka/Redpanda opcjonalnie).

**Odpowiedzialności:**
- Scrapery — architektura, rate limiting, retry, proxy rotation, monitoring
- Integracje z API bukmacherów (LVBet, Superbet, Fortuna, Betclic, STS, Pinnacle)
- Orkiestracja pipeline'ów (Prefect / Dagster)
- Schema DB — migracje (Alembic), widoki, indeksy
- Migracja SQLite → Postgres 16 + Timescale
- Data quality monitoring (Great Expectations lub własny)
- Backup strategy (daily → S3/Backblaze)
- Cost optimization (ile GB, ile calls, ile compute)
- Analytical layer (DuckDB dla raportów, Parquet na S3)

**Nie robi:**
- Nie trenuje modeli
- Nie projektuje frontendu
- Nie obsługuje billingu

**Narzędzia:** Python, SQL, Postgres, Timescale, DuckDB, Parquet, Prefect, Alembic, Great Expectations, Selenium, Playwright

---

## 5. Senior Software Engineer (`SWE`)

**Profil:** 20 lat doświadczenia. Fullstack z fokusem na backend. Zbudował min. 1 produkt SaaS z autentykacją, billingiem, multi-tenancy. Zna FastAPI, Django, Next.js, Docker, VPS/cloud deployment.

**Odpowiedzialności:**
- Backend API (FastAPI / NestJS)
- Autentykacja + multi-tenancy (Clerk, Auth0 lub własne)
- Billing (Stripe B2B invoicing, usage-based, subscriptions)
- API token management + rate limiting
- Frontend (Next.js + TanStack Query)
- Docker + docker-compose
- CI/CD (GitHub Actions)
- VPS setup (Hetzner, Backblaze, Cloudflare)
- Secrets management (Doppler / 1Password Connect)
- Observability (Grafana, Loki, Better Stack)
- Integracja z designerem — implementacja designów

**Nie robi:**
- Nie trenuje modeli (to MLEng)
- Nie scrapuje (to DataEng)
- Nie projektuje UX (to Designer, on implementuje)

**Narzędzia:** TypeScript, Python, Next.js, FastAPI, Postgres, Docker, GitHub Actions, Stripe, Clerk, Cloudflare

---

## 6. Senior UI/UX Designer (`Designer`)

**Profil:** 20 lat doświadczenia w projektowaniu produktów B2B SaaS. Zbudował design systemy dla min. 2 produktów live. Zna Figma do poziomu automatyzacji (tokens, components, variants). Rozumie data visualization (D3, Observable).

**Odpowiedzialności:**
- User research (wywiady z klubami, tipsterami, trenerami w P6.0)
- Design system (tokens, components, Figma library)
- Wireframes → high-fidelity → handoff do SWE
- Dashboardy (dla klubów, dla tipsterów, dla bettorów)
- Landing page + brand identity (logo, kolory, typografia)
- Raport designs (PDF export, export-ready templates)
- Data visualization (radar charts, xG flow, pitch maps, court heat maps)
- Email templates (dla notyfikacji, raportów)
- Responsive web + PWA flow
- Copy/microcopy na landing page

**Nie robi:**
- Nie pisze kodu frontendu (SWE robi z jego designów)
- Nie robi animacji bardzo zaawansowanych (opcjonalnie, przez SWE + Framer Motion)
- Nie obsługuje marketingu/SEO/content

**Narzędzia:** Figma, FigJam, Miro, Notion, Whimsical, Penpot (backup), Rive (optional animacje)

---

## Braki kompetencyjne (rekrutacja potrzebna w późniejszych fazach)

### P0-P2 (obecny zespół wystarczy)
Zespół 6 osób obsługuje wszystko od code cleanup po modelowanie.

### P3-P4 (może wymagać wsparcia)
- **Sports domain expert per dyscyplina** — tenisa/koszykówki/hokeja. **Opcja: doradca zewnętrzny, pół etatu.**

### P5 (prawdopodobnie tak)
- **DevOps / SRE** — gdy maszynka rośnie, SWE może nie wystarczyć. **Opcja: fractional DevOps 0.5 FTE.**

### P6 (zdecydowanie tak — 2-3 osoby)
- **Growth / Marketing B2B** — leadgen, content, SEO, cold outreach do klubów i tipsterów. **Pełen etat od P6.0.**
- **Prawnik specjalista od hazardu i GDPR** — regulacje w UE/PL. **Kontrakt + retainer.**
- **Sales B2B** (opcjonalnie) — jeśli Lead nie ogarnie sam wszystkich leadów. **Commision-based na start.**
- **Content creator / copywriter** — blog, case studies, email marketing. **Freelance lub pół etatu.**

### P6+ (gdy się udaje)
- **Customer success manager** — onboarding klientów B2B, support
- **Data analyst** (junior/mid) — wspiera klientów z custom queries
- **Additional ML engineers** — gdy skala wymaga (2-3 sporty, 10+ lig)

---

## Macierz odpowiedzialności RACI (skrócona)

| Obszar | Lead | DrMat | MLEng | DataEng | SWE | Designer |
|---|---|---|---|---|---|---|
| Wizja produktowa | **R/A** | C | C | C | C | C |
| IP matematyczne | A | **R** | C | — | — | — |
| Modele ML | A | C | **R** | C | — | — |
| Pipeline danych | A | — | C | **R** | C | — |
| API + App | A | — | C | C | **R** | C |
| UI/UX | A | — | — | — | C | **R** |
| Infra / DevOps | A | — | — | C | **R** | — |
| Sales B2B | **R/A** | C | — | — | — | C |
| Compliance | **R/A** | — | — | C | C | — |

**R** = Responsible (wykonuje), **A** = Accountable (odpowiada), **C** = Consulted (konsultowany), — = nie uczestniczy.
