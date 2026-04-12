# Panel & Pricing Spec — Summary

> Pełna specyfikacja: output agenta designer z 2026-04-12 (2000+ linii).
> Ten plik zawiera kluczowe decyzje i wireframes.

## Kluczowe decyzje

| Decyzja | Wybór |
|---------|-------|
| Hero metric | **CLV (30d rolling)** — nie ROI, nie win rate |
| Dark mode | Domyślny dla app, light dla landing/reports |
| Mobile-first | Tak (tipsterzy sprawdzają na telefonie) |
| Tables vs cards | Tables dla bet slipów, cards tylko dla KPI |
| Pricing | Invite-only alpha → €19 early adopter → €49/199 launch |
| Free tier | 1 liga, delayed T+1, no API |
| Admin panel | Desktop-only, functional > pretty. Grafana jako alternatywa |
| Native app | Nie. PWA w V2 jeśli potrzebne |
| Social features | Nie. Dopiero po PMF |

## User Panel — 6 widoków

1. **Dashboard** — hero CLV, 4 KPI cards z sparklines, today's bets table, recent results
2. **Today's Predictions** — full bet slip z filtrami, "Mark as placed", model breakdown expandable
3. **Track Record** — CLV chart, monthly heatmap, per-league table, transparency banner, CSV download
4. **My Bets** — personal tracking, "vs Model" comparison, manual bet entry
5. **Settings** — bankroll, leagues, markets, notifications, API key, odds format, theme
6. **Alerts** — notification center, CLV degradation warning

## Admin Panel — 6 widoków

1. **System Health** — pipeline status, model quality KPIs, infra (CPU/RAM/disk/temp Pi)
2. **Users** — list, plan, engagement, invite, disable
3. **Model Management** — current production, history, rollback, retrain trigger
4. **Content** — prediction notes, league/market enable/disable per plan
5. **Revenue** — MRR chart, plan distribution, Stripe link
6. **Analytics** — DAU/WAU/MAU, feature usage, conversion funnel, retention cohorts

## Pricing tiers (post-alpha launch)

| Tier | Cena | Co dostaje |
|------|------|-----------|
| **Free** | €0 | 1 liga, opóźnione T+1, 30d track record, brak API |
| **Pro** | €49/mies. | 16 lig, real-time, pełny track record, Telegram, My Bets |
| **Enterprise** | €199/mies. | Pro + API (1000 calls/day), webhooks, priority support |

Annual: -20% (Pro €39/mies., Enterprise €159/mies.)

## Timeline

| Phase | Okres | Cena | Users |
|-------|-------|------|-------|
| Alpha (invite-only) | Mies. 1-3 | Free | 20-50 |
| Early adopter | Mies. 3-6 | €19/mies. | 50-80 |
| Launch | Mies. 6-9 | €49/199 | 100-200 |
| Growth | Mies. 9-12 | €49/199 | 200-500, MRR €4-5k |

## MVP effort: 22-33 dni (4-5 tygodni)

Tyg 1-2: FastAPI + Clerk auth + Dashboard + Predictions
Tyg 3: Track Record + My Bets + Telegram
Tyg 4: Admin basics + Settings + Landing page
Tyg 5: Mobile responsive + polish + bug fixes

## Design system: Dark mode tokens

```
--bg-primary: #0B0D14
--bg-secondary: #12141D
--text-primary: #E8EAF0
--brand-primary: #5B67F2
--color-positive: #22C55E
--color-negative: #EF4444
--font-mono: JetBrains Mono
--font-body: Inter
```

## Competitive insight

CLV transparency = jedyny differentiator. Każdy Telegram tipster mówi "85% win rate".
My mówimy "CLV +2.3% vs Pinnacle closing, verified, including losing periods."
To jest trust moat którego nikt nie kopiuje bo wymaga prawdziwego edge'u.
