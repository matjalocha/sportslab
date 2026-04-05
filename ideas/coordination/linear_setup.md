# Linear Setup

**Owner:** Lead
**Status:** P0.11 task
**Cel:** Skonfigurowanie Linear workspace tak żeby zespół 6 osób mógł efektywnie koordynować prace przez wszystkie 7 faz.

## Workspace

**Nazwa:** `SportsLab` (lub inna, dopasowana do brandu wybranego w P0)

**URL:** `linear.app/sportslab`

## Teams

Linear "Teams" = workspace'y w Linear. Tworzymy minimalnie:

### 1. **Engineering** (key: ENG)
Dla wszystkich zadań technicznych (ML, Data, SWE).

**Members:** Lead, DrMat, MLEng, DataEng, SWE

### 2. **Design** (key: DES)
Dla tasków designerskich (UI/UX, brand, mockups).

**Members:** Lead, Designer, SWE (collaborator)

### 3. **Operations** (key: OPS)
Dla tasków non-technicznych (business, sales, legal, accounting, infra operations).

**Members:** Lead, wszyscy jako collaborators

### (Future) 4. **Research** (key: RES) — może być w P2+
Osobny workspace dla research backlog, eksperymentów, whitepapers. Może być projekt w Engineering team na start.

## Projects

**Linear "Projects"** to container dla related issues, z start/end dates, status, progress tracking.

### Fazy jako projekty (każda faza = 1 projekt)

1. **P0 — Foundations** (Operations team)
2. **P1 — Code Cleanup** (Engineering team)
3. **P2 — New Features** (Engineering team)
4. **P3 — More Leagues** (Engineering team)
5. **P4.1 — Tennis** (Engineering team)
6. **P4.2 — Basketball** (Engineering team)
7. **P4.3 — Hockey** (Engineering team)
8. **P5 — Automation** (Engineering team)
9. **P6.0 — Discovery** (Operations team)
10. **P6.1 — MVP API** (Engineering team)
11. **P6.2 — Dashboards** (Engineering + Design teams)
12. **P6.3 — Sales** (Operations team)
13. **P6.4 — V2 SKU** (Engineering team)

### Cross-phase projekty

- **Infrastructure** (ongoing) — infra maintenance, cost optimization
- **Research Backlog** (ongoing) — hipotezy z research_backlog.md
- **Customer Discovery** (P0, P2, P4, P6) — wywiady, feedback loops
- **Brand & Marketing** (ongoing, Design team)

## Cycles

**Linear "Cycles"** = sprinty, automatyczne ścieżki 2-tygodniowe.

**Konfiguracja:**
- Cycle length: **2 tygodnie**
- Start day: **Monday**
- Cooldown: **1 day** (piątek wieczorem retro + planning następnego cycle)
- Auto-completion: carry over pending issues

## Labels

Labele w Linear to kategoryzacja cross-cutting. Proponowane:

### Typ zadania
- `type:feature` — nowa funkcjonalność
- `type:bug` — naprawa
- `type:refactor` — poprawa kodu bez zmiany zachowania
- `type:research` — eksperyment, spike
- `type:docs` — dokumentacja
- `type:chore` — maintenance, infra
- `type:design` — UI/UX task

### Priorytet (Linear ma wbudowany)
- `Urgent` — krytyczne, teraz
- `High` — do końca cycle
- `Medium` — domyślny
- `Low` — nice to have

### Owner (persona)
- `persona:lead`
- `persona:drmat`
- `persona:mleng`
- `persona:dataeng`
- `persona:swe`
- `persona:designer`
- `persona:external` — gdy potrzebujemy outside help (prawnik, księgowy, agency)

### Obszar
- `area:ml` — modele, kalibracja, features
- `area:data` — pipeline, scraping, DB
- `area:infra` — VPS, CI/CD, monitoring
- `area:api` — backend FastAPI
- `area:web` — frontend Next.js
- `area:docs` — documentation
- `area:sales` — customer discovery, outreach
- `area:legal` — compliance, ToS
- `area:finance` — budget, invoicing

### Sport (od P4)
- `sport:football`
- `sport:tennis`
- `sport:basketball`
- `sport:hockey`

### Liga (od P3, opcjonalnie)
- `league:eredivisie`
- `league:primeira`
- `league:championship`
- `league:mls`
- `league:brasileirao`
- `league:top5` — dla zadań cross-league

## Issue templates

### Template 1: Task
```markdown
## Context
Why this task exists, what problem it solves.

## Acceptance Criteria
- [ ] Criterion 1 (measurable)
- [ ] Criterion 2
- [ ] Tests pass
- [ ] Documentation updated

## Dependencies
Depends on: #ISSUE_ID

## Notes
Any relevant technical details.
```

### Template 2: Bug
```markdown
## Description
What's broken?

## Steps to reproduce
1. Step one
2. Step two
3. See error

## Expected behavior
What should happen instead.

## Environment
- OS: ...
- Python version: ...
- Branch: ...

## Logs / screenshots
```

### Template 3: Research / Spike
```markdown
## Hypothesis
What we believe is true / want to test.

## Success criteria
How we know we've tested it.

## Method
Step-by-step approach.

## Timebox
Max X hours/days before we stop.

## Deliverable
- [ ] Notebook/report in `docs/research/`
- [ ] Recommendation: go / no-go
```

### Template 4: Design task
```markdown
## User story
As a {persona}, I want {feature}, so that {benefit}.

## Scope
- [ ] Wireframes
- [ ] High-fidelity mockups
- [ ] Prototype (optional)
- [ ] Handoff to SWE

## References
Links to inspiration, competitor examples.

## Deliverables
- Figma file link: ...
- Assets exported to `packages/ui/assets/`
```

## Workflow

### Status column
Linear default + customization:

- **Backlog** — nowe, nie zaplanowane
- **Todo** — zaplanowane do current cycle
- **In Progress** — aktywnie wykonywane (limit: 1 per person)
- **In Review** — PR otwarty, czeka na review
- **Blocked** — czeka na zewnętrzną zależność
- **Done** — zrobione, zamknięte
- **Cancelled** — anulowane

### WIP limits
- **In Progress:** max 1 per person (force focus)
- **In Review:** max 3 per person (nie zbieraj PRs)

### Sub-issues
Dla zadań > 2 dni rozbijamy na sub-issues. Parent issue widzi progress sub-issues.

## Integrations

### Linear ↔ GitHub
- Link PR → Linear issue (auto via `Fixes LIN-123` w PR title)
- Auto-close issue po merge
- Linear status sync z PR state (open → In Review, merged → Done)

### Linear ↔ Slack
- Kanał `#linear-activity` z notification o zmianach (mute by default, on-demand check)
- Kanał `#linear-urgent` tylko dla urgent priority (wszyscy subscribed)

### Linear ↔ Figma
- Design issues → Figma link pushed via integration

## Rituals (integration z weekly_rhythm.md)

### Monday — Sprint Planning (30 min)
- Review backlog
- Prioritize for cycle
- Assign issues to team members
- Update cycle goals

### Wednesday — Mid-sprint check
- Async update w Linear
- Blokery flagowane

### Friday — Retro + Demo (60 min)
- Demo completed work
- Retro: what went well, what didn't, action items
- Plan next cycle

### Dziennie — Async standup
- W Linear: każdy dodaje comment do "Daily Standup" issue w swoim team
- Format: "Yesterday / Today / Blockers"

## Views

Predefiniowane widoki dla każdego member:

### "My Issues" (każdy member)
- Assignee = current user
- Status != Done, Cancelled
- Sorted by priority

### "Current Cycle" (team-wide)
- Cycle = current
- All statuses
- Group by status

### "Blocked" (team-wide)
- Status = Blocked
- Age sorted

### "Recently Completed" (team-wide)
- Status = Done
- Last 14 days

### Per persona
- "DrMat's Research" — persona:drmat + type:research
- "SWE's Infra" — persona:swe + area:infra
- etc.

## Reporting

### Linear reports do Lead
- Weekly: cycle progress, velocity, blocker count
- Monthly: velocity trend, issue resolution time, WIP distribution

### Lead weekly review
Every Friday Lead reviews:
1. Current cycle progress
2. Blocked issues (unblock them)
3. Upcoming cycle planning
4. Cross-team dependencies
5. Overall health (team workload, burnout signals)

## Access control

### Admin
- Lead

### Member (full access)
- DrMat, MLEng, DataEng, SWE, Designer

### Guest (read-only, opcjonalnie)
- Prawnik — access do area:legal issues
- Księgowy — access do area:finance issues
- External consultants — per project

## Cost

- **Free tier:** < 10 users, < 250 issues per team, 2 teams max
- **Plus plan:** $8/user/m-c, unlimited issues, advanced features
- **P0-P1:** Free tier wystarcza
- **P2+:** Rozważyć Plus gdy zaczynamy sprints intensywnie
- **P5+:** Plus na pewno (advanced reports)

## Kluczowe zasady

1. **Każdy task ma owner** — zero "unassigned" dłużej niż 24h
2. **Każdy PR linkuje do Linear issue** — enforced by pre-commit
3. **Issue description musi mieć DoD** — bez DoD nie zaczynamy pracy
4. **Daily standup to obowiązek** — 2 minuty, nawet gdy nic się nie zmieniło
5. **Nie kończymy issue bez demo** (dla widocznych prac)
6. **Blocked to alert** — jeśli issue jest Blocked > 24h, Lead dostaje notification
