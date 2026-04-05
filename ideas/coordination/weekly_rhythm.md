# Weekly Rhythm

**Owner:** Lead
**Cel:** Rytm koordynacyjny dla 6-osobowego zespołu działającego często asynchronicznie, ale potrzebującego punktów synchronizacji.

## Filozofia

1. **Asynchroniczność jako default** — synchroniczne meetings tylko gdy async nie działa
2. **Krótkie meetingi, jasne cele** — żadnego "catch-up" bez agendy
3. **Demo-driven** — pokazujemy co zrobiliśmy, nie mówimy o tym
4. **Retrospektywa cotygodniowa** — ciągła poprawa procesu
5. **Protect focus time** — engineering potrzebuje deep work, meetings ograniczone

## Core hours

**Ustalone w P0.17** (może zmieniać się per zespół).

**Proponowane core hours:** **10:00 - 14:00 CET** (Mon-Fri)
- W core hours: wszyscy są "reachable" dla sync questions (Slack odpowiedzi w < 30 min)
- Poza core hours: async, deep work, personal time
- Wyjątek: on-call (P5+)

**Czasowe wyzwanie:** Jeśli zespół jest w różnych time zones (np. Lead w UK, DrMat w Niemczech), core hours mogą być węższe (np. 10-13 CET).

## Weekly schedule

### Monday — Planning Day

**08:00 — 10:00 (async)**
- Każdy member reviewuje swoje Linear issues na cycle
- Przegląd notatek z ostatniego retro (piątek)
- Priorytetyzacja własnych tasków

**10:00 — 10:30 — Sprint Planning Meeting (sync)**
- **Obecni:** wszyscy
- **Czas:** 30 min max
- **Format:**
  - Lead: przegląd celów cycle + stan previous cycle
  - Każdy member: co planuje zrobić w tym tygodniu (2 min/osoba)
  - Zespół: identyfikacja blokerów i zależności
  - Lead: final priorytyzacja
- **Output:** Linear cycle updated, każdy ma jasne priorytety

**10:30 — 14:00 — Focus time (core hours, deep work)**

### Tuesday — Execution Day

**No meetings.** Full focus.

Async updates w Linear tylko.

### Wednesday — Demo Day

**10:00 — 10:30 — Mid-week Demo (sync)**
- **Obecni:** wszyscy
- **Czas:** 30 min max
- **Format:**
  - Każdy member pokazuje 2-minutowy demo tego co zrobił
  - Designer pokazuje mockupy/prototypes
  - Lead komentuje, zespół feedbacks
  - Identyfikacja "show-stoppers"
- **Cel:** Wczesne wykrycie problemów, celebracja progressu

**No decisions w demo** — decisions w innych meetingach.

### Thursday — Execution Day

**No meetings.** Full focus.

### Friday — Retrospective Day

**13:00 — 13:30 — Retrospective (sync)**
- **Obecni:** wszyscy
- **Czas:** 30 min max
- **Format (Start/Stop/Continue):**
  - **Start:** co powinniśmy zacząć robić?
  - **Stop:** co przestać?
  - **Continue:** co działa i robimy dalej?
- **Output:** 3-5 action items w Linear (assigned), tracked w następnym cycle

**13:30 — 14:00 — Demo Dla Lead (optional)**
- Tylko Lead + 1-2 osoby z konkretnym progressem
- Pokazanie "big ticket items" które wymagają strategic feedback

### Weekend — Off (domyślnie)

Wyjątki:
- Incident response (P5+, on-call)
- Personal choice deep work (nigdy nie wymagamy)

## Cycle (2 tygodnie)

Linear cycles = 2-tygodniowe sprinty.

### Cycle Start (Monday week 1)
- Planning meeting rozszerzone do 60 min
- Review previous cycle velocity
- Set cycle goals (top 3-5 deliverables)
- Identify risks

### Mid-cycle (Monday week 2)
- Quick check-in (15 min w sprint planning)
- Adjust if needed

### Cycle End (Friday week 2)
- Retrospective rozszerzone do 60 min
- Demo wszystkich completed items (30 min)
- Velocity calculation
- Blockers analysis
- Plan next cycle

## Async communication

### Linear (primary)
- Issue updates, comments, decisions
- Daily async standup:
  ```
  ## Daily Standup 2026-04-07
  
  **Yesterday:** Completed XYZ feature, started ABC refactor
  **Today:** Finish ABC refactor, start review on #LIN-123
  **Blockers:** Waiting on design for #LIN-456
  ```

### Slack (secondary)
- **#general** — team announcements
- **#engineering** — technical discussions
- **#design** — design discussions
- **#data** — scraping, pipeline
- **#sales** — customer conversations
- **#random** — off-topic
- **#incidents** (P5+) — critical alerts
- **#linear-activity** (muted) — auto from Linear
- **#demos** — screen recordings, quick wins
- **#research** — papers, interesting findings

**Response SLA:**
- Urgent DM: 1h during core hours
- @mention w channel: 4h during core hours
- Regular: 24h
- Outside core hours: next business day

### Figma comments
- Designer posts design reviews
- Engineers comment na specific elements
- Resolved gdy addressed

### Email (tertiary)
- Tylko dla external communication (klienci, partnerzy, vendors)
- Team nie używa email do internal communication

## Meetings (full list)

### Regularne (recurring)
| Meeting | Frequency | Duration | Obligatoryjne |
|---|---|---|---|
| Sprint Planning | Monday weekly | 30 min | ✅ wszyscy |
| Mid-week Demo | Wednesday weekly | 30 min | ✅ wszyscy |
| Retrospective | Friday weekly | 30 min | ✅ wszyscy |
| Cycle Planning | Every 2 weeks Monday | 60 min | ✅ wszyscy |
| Cycle Retro | Every 2 weeks Friday | 60 min | ✅ wszyscy |
| 1:1 Lead ↔ team member | Weekly | 30 min | Per osoba |
| Phase Gate Review | Per phase transition | 60 min | ✅ wszyscy |
| Monthly Business Review | Monthly | 60 min | Lead + senior roles |

### Ad-hoc
- **Design reviews** — po zakończeniu high-fidelity designs
- **Architecture reviews** — przed dużymi zmianami strukturalnymi
- **Incident calls** — P5+ gdy critical issue
- **Customer calls** — Lead + opcjonalnie engineer dla technical demo

## 1:1 Lead ↔ team member

**Frequency:** Weekly (30 min)
**Format:** Personal, structured:
- Praca: blokery, workload, satisfaction
- Wzrost: czego się chcą nauczyć, co chcą robić
- Feedback: od member do Lead i vice versa
- Personal: jak się czują (opcjonalnie)

**Zasady:**
- Bez agendy = nieefektywne (member przygotowuje 3 punkty)
- No-laptop rule (focus on conversation)
- Notes w Notion, private

## Phase Gate Reviews

Przed każdym przejściem faza N → faza N+1:

**Czas:** 60 min
**Obecni:** Wszyscy + opcjonalnie external advisor (mentor, inwestor przyjazny)

**Agenda:**
1. Status wszystkich DoD kryteriów (15 min)
2. Blockers i unresolved issues (10 min)
3. Kluczowe lekcje z fazy (10 min)
4. Plan następnej fazy — highlights (15 min)
5. Go/No-Go decision Lead (5 min)
6. Action items (5 min)

**Output:** Gate review document w `ideas/phase_X/gate_review_YYYY-MM-DD.md`

## Monthly Business Review

**Frequency:** Ostatni piątek miesiąca
**Czas:** 60 min
**Obecni:** Lead, wszyscy seniorzy (DrMat, MLEng, DataEng, SWE, Designer)

**Agenda:**
1. Financial: costs, revenue, runway (Lead, 10 min)
2. Metrics: velocity, ROI, CLV, uptime (MLEng/DataEng, 15 min)
3. Customers: acquired, churned, feedback (Lead, 10 min)
4. Team: mood, blockers, hiring needs (Lead + open floor, 10 min)
5. Strategic decisions (15 min)

**Output:** Monthly report w Notion, shared z zespołem.

## Ceremonie (soft rituals)

### **Celebration moments**
- Gdy gate review passes → team dinner / drinks (symbolic, budget min.)
- Gdy pierwszy płacący klient → bigger celebration
- Gdy first profitable month → team bonus

### **Kudos w Friday retro**
- Każdy member zostawia 1-2 kudos dla innego (niespodzianka + motivation)

### **Lessons learned publication**
- Po każdej fazie Lead pisze krótki blog post (internal) z 3-5 lekcjami
- Dla IP/credibility — opcjonalnie publikujemy zewnętrznie (P6+)

## Avoidance patterns (czego nie robimy)

### ❌ Meetings bez agendy
Każdy meeting ma agenda w kalendarzu. Brak agendy = cancel.

### ❌ "Catch-up meetings"
Zastąpione async w Linear.

### ❌ "Check-in meetings" z Leadem
Zastąpione 1:1 w jasnym slotcie.

### ❌ All-hands meetings codziennie
Zabija productivity. Planning, Demo, Retro wystarczą.

### ❌ Slack spam
Threads dla dyskusji, @channel tylko dla urgent, kanały tematyczne.

### ❌ Po-godzinowa komunikacja
Poza core hours = Linear comments (async), nie DM.

## Calendar tools

- **Google Calendar** (via Google Workspace) — shared calendars
- **Calendly** — booking dla customer calls (P6+)
- **Clockwise** lub **Cron** — smart scheduling (opcjonalnie)

## Time zone strategy

### Scenariusz 1: Wszyscy w CET (domyślne)
- Core hours: 10:00-14:00 CET
- Full standard schedule

### Scenariusz 2: Rozproszony zespół (P3+ opcjonalne)
- Core hours overlap: 14:00-16:00 CET (2h)
- Więcej async, mniej sync
- Meetingi tylko w overlapie
- Każdy member ma 2-3h async time przed i po

### Scenariusz 3: Fully remote + async
- Minimal sync (1x/week all-hands, 30 min)
- Wszystko w Linear + Slack threads
- Decisions z 48h comment period
- **Risk:** slower velocity, communication gaps
- **Reward:** global talent pool

## Retrospektywa co miesiąc na meta-level

Raz w miesiącu retro o **procesie samym w sobie**:
- Czy rytm działa?
- Czy meetings są wartościowe?
- Czy brakuje jakiegoś ceremonii?
- Czy coś można usunąć?

Zmiany procesowe wprowadzane od następnego cycle.

## Pierwsze 4 tygodnie (ustalenie rytmu)

- **Week 1:** Standard schedule, observacja
- **Week 2:** Pierwsze cycle retro, adjusty
- **Week 3:** Standard schedule
- **Week 4:** Cycle retro + miesięczne meta-retro
- **Month 1 end:** Decyzja Lead: czy rytm działa, co zmieniamy
