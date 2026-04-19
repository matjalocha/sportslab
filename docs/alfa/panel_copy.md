# SportsLab — Panel Microcopy

> **Status:** Ready for Lovable (A-25)
> **Audience:** Alpha users (tipsters, ML-literate bettors, personal network) inside the authenticated panel
> **Language:** English
> **Tone:** data-forward, humble, no exclamation marks, no emoji in UI copy (emoji only in Telegram), action-first
> **Consumed by:** TASK-A-25 (Lovable panel prototype), TASK-A-29 (Next.js panel build)
> **Last updated:** 2026-04-19

---

## Copy guide (one-liner reminders)

- Per `vision.md`: transparent over reassuring. "No picks today" is a feature, not a failure.
- Per `panel_spec`: hero metric is CLV. Empty states must educate, not apologize.
- Every error message names the cause and offers a next step.
- Destructive actions use explicit verbs ("Delete bet", "Sign out"), never vague ("Confirm").
- No "Oops", no "Uh-oh", no "Something went wrong" alone without context.

---

## 1. Empty states

### 1.1 Dashboard — new user, no bets yet

- **Title:** Your dashboard starts here.
- **Body:** You will see your rolling CLV, today's bet slip, and recent results on this page. The first picks land after you confirm your Telegram handle and the next daily run completes (around 14:00 CET).
- **CTA:** Confirm Telegram

### 1.2 Today's Predictions — no picks today

- **Title:** No value bets today.
- **Body:** The model found no matches where its calibrated probability beats the best available odds by a meaningful edge. We do not force picks when no edge is detected — that is how you keep a positive CLV over time.
- **CTA:** View yesterday's slip

### 1.3 Track Record — fewer than 50 bets

- **Title:** Track record is building.
- **Body:** Metrics become statistically meaningful after roughly 50 bets and reliable after 200. You have {N} logged so far. Check back after a few weeks — or watch today's slip update in real time.
- **CTA:** See today's slip

### 1.4 My Bets — empty log

- **Title:** Log your first bet.
- **Body:** Mark a pick from today's slip as placed to start tracking your personal results against the model. You can also add bets placed outside SportsLab to compare your own edge.
- **Primary CTA:** Go to today's slip
- **Secondary CTA:** Add manual bet

### 1.5 Alerts — no alerts

- **Title:** No alerts right now.
- **Body:** We notify you when model calibration drifts, a new league goes live, or an unusually large edge appears. Silence here means everything is running within normal bounds.
- **CTA:** Review alert settings

### 1.6 Settings — API key not generated (Enterprise placeholder)

- **Title:** API access is part of the Enterprise plan.
- **Body:** During the alpha, API access is not enabled. Once paid tiers launch, Enterprise subscribers can generate a key here to pull predictions and track-record data programmatically.
- **CTA:** Notify me when API opens

*Design note: empty states are `--c-surface` cards with 48px vertical padding, centered copy, muted icon (80×80) above title. CTA button `--c-brand`, secondary ghost.*

---

## 2. Error messages

### 2.1 401 — session expired / not signed in

- **Headline:** Session expired.
- **Body:** You were signed out for inactivity. Sign in again to continue.
- **Primary action:** Sign in

### 2.2 403 — no active subscription or admin-only

- **Headline:** Access not available on your plan.
- **Body:** This area is reserved for active subscribers or admin users. If you think you should have access, reach out and we will check.
- **Primary action:** Contact support
- **Secondary action:** Back to dashboard

### 2.3 404 — page not found

- **Headline:** We could not find that page.
- **Body:** The link may be out of date or the page was removed. Use the navigation to find what you were looking for.
- **Primary action:** Back to dashboard

### 2.4 500 — server error

- **Headline:** Something broke on our end.
- **Body:** A server error stopped this page from loading. We log these automatically and are already looking. You can retry, or come back in a few minutes.
- **Primary action:** Retry
- **Secondary action:** Back to dashboard

### 2.5 503 — maintenance or pipeline down

- **Headline:** Data pipeline is running late.
- **Body:** Today's predictions are delayed while the model completes its run. Expected back online within 30 minutes. Telegram subscribers will be notified when the slip is published.
- **Primary action:** Refresh

### 2.6 Network timeout

- **Headline:** Connection timed out.
- **Body:** We could not reach our servers. Check your internet connection and try again.
- **Primary action:** Retry

### 2.7 Validation error — form field

- **Inline pattern:** "{Field name} — {specific issue in plain language}."
- **Examples:**
  - "Email — this does not look like a valid email address."
  - "Bankroll — must be a positive number."
  - "Telegram handle — use the format @your_handle."

*Design note: error card uses `--c-bad` as 2px left border, not full background. Body text stays `--c-text`. Icon 40×40 muted. Action button inline right on desktop, below on mobile.*

---

## 3. Confirmation dialogs

### 3.1 Delete bet from My Bets log

- **Title:** Delete this bet from your log?
- **Body:** This removes the bet from your personal tracking. Your model performance history is not affected. This cannot be undone.
- **Confirm button:** Delete bet
- **Cancel button:** Keep it

### 3.2 Save settings (bankroll change)

- **Title:** Save new bankroll amount?
- **Body:** Future Kelly stakes will be calculated against {new_amount} EUR starting from the next daily run. Bets already placed are not re-sized.
- **Confirm button:** Save changes
- **Cancel button:** Cancel

### 3.3 Save settings (league or market change)

- **Title:** Apply new preferences?
- **Body:** You will start seeing picks for the leagues and markets you selected from tomorrow's slip onward. Today's picks stay unchanged.
- **Confirm button:** Save preferences
- **Cancel button:** Cancel

### 3.4 Regenerate API key

- **Title:** Regenerate your API key?
- **Body:** The current key will stop working immediately. Any scripts or webhooks using it will fail until you update them with the new key.
- **Confirm button:** Regenerate key
- **Cancel button:** Cancel

### 3.5 Sign out

- **Title:** Sign out of SportsLab?
- **Body:** You will need to sign back in to see today's slip and your track record.
- **Confirm button:** Sign out
- **Cancel button:** Stay signed in

### 3.6 Cancel subscription (post-alpha placeholder)

- **Title:** Cancel your subscription?
- **Body:** You keep access until {period_end_date}. After that, you lose real-time picks, full track record, and Telegram. Your logged bets stay in read-only mode.
- **Confirm button:** Cancel subscription
- **Cancel button:** Keep my plan

*Design note: modal centered, 480px max width, `--c-surface-2` background, 24px padding. Destructive confirm buttons use `--c-bad` fill, neutral confirms use `--c-brand`. Cancel is always ghost, left of confirm.*

---

## 4. Button labels (glossary)

| Context | Primary | Secondary | Destructive |
|---|---|---|---|
| Sign-in screen | Sign in | Forgot password | — |
| Sign-up / invite redemption | Redeem invite | Have an account? Sign in | — |
| Onboarding — bankroll step | Continue | Skip for now | — |
| Onboarding — Telegram step | Link Telegram | I will do this later | — |
| Dashboard hero — today's slip empty | Go to predictions | — | — |
| Bet slip row | Mark as placed | View model breakdown | — |
| Bet slip row (already placed) | Mark as result | Undo placement | — |
| Bet slip filters bar | Apply filters | Reset | — |
| Today's Predictions — no picks | Notify me tomorrow | View yesterday's slip | — |
| Track Record | Download CSV | Share public link | — |
| My Bets row | — | View model breakdown | Delete bet |
| My Bets — empty | Add manual bet | Go to today's slip | — |
| Settings — bankroll | Save changes | Cancel | — |
| Settings — preferences | Save preferences | Cancel | — |
| Settings — API key | Regenerate key | Copy key | Revoke key |
| Settings — notifications | Save | Send test message | — |
| Subscription (disabled in alpha) | Upgrade to Pro | Compare plans | Cancel subscription |
| Alerts | Mark all as read | Configure alerts | Dismiss |
| Admin — users list | Invite user | Export CSV | Disable user |
| Admin — model management | Trigger retrain | View history | Roll back |
| Admin — content | Save note | Preview slip | — |
| Admin — revenue | Open Stripe | Export CSV | — |
| Profile menu | Settings | Help | Sign out |
| Contact / support | Send message | — | — |
| Form submission (generic) | Submit | Cancel | — |
| Destructive confirmations | {specific verb} | Cancel | — |

**Rules:**
- Primary buttons use imperative verbs ("Save", "Apply", "Submit"). Never "OK" alone.
- Destructive buttons name the consequence ("Delete bet", not "Delete"). Never "Yes".
- Secondary buttons are nouns or ghost actions ("Cancel", "Compare plans").
- Disabled states in alpha should carry a tooltip: "Available after the alpha ends".

---

## 5. Onboarding tooltips (new user, first Dashboard visit)

Sequence of five tooltips triggered on first Dashboard visit, dismissable with X or Skip tour. Progress indicator "Step N of 5".

### Tooltip 1 — Hero CLV card

- **Points to:** CLV metric card (top-left, largest)
- **Copy:** This is your rolling 30-day Closing Line Value. It measures whether your picks beat the market at kickoff. Above zero means real edge. Below zero means the model is being priced out.
- **Button:** Next

### Tooltip 2 — Today's bet slip

- **Points to:** Today's Predictions table preview on Dashboard
- **Copy:** Your daily slip appears here after the 14:00 CET model run. You can mark each pick as placed once you actually bet it — we track both what the model said and what you did.
- **Button:** Next

### Tooltip 3 — Track record link

- **Points to:** Track Record sidebar link
- **Copy:** Every pick is logged publicly here, including losing streaks. Share the link to prove your edge — or to check whether ours still holds.
- **Button:** Next

### Tooltip 4 — Alerts bell

- **Points to:** Alerts icon in top navigation
- **Copy:** We notify you when calibration drifts, a new league opens, or an unusually large edge appears. You will not get noise from here.
- **Button:** Next

### Tooltip 5 — Settings

- **Points to:** Settings sidebar link
- **Copy:** Set your bankroll, leagues, markets, notifications, and odds format here. Your bankroll drives Kelly sizing in the slip — keep it accurate.
- **Button:** Got it

**Tour footer (fixed to each tooltip):**
- **Skip tour** link bottom-left (muted `--c-text-muted`)
- **Step indicator** bottom-right ("Step 3 of 5")

*Design note: tooltips are 320px wide, `--c-surface-2` background, 1px `--c-brand` border, 12px radius. Arrow pointer aligned to target element. Next button brand-filled, Skip text muted. Mobile: tooltips stack as bottom-sheet cards instead of anchored popovers.*

---

## Checklist for Lovable handoff (A-25)

- [ ] All empty states rendered for their target page
- [ ] Error states reachable via dev-only route (e.g. `/dev/errors/401`)
- [ ] All confirmation modals triggered from respective buttons
- [ ] Button labels match glossary exactly (no "OK", no "Yes")
- [ ] Onboarding tour triggers once per user on first Dashboard visit, dismissable, does not re-trigger after Skip
- [ ] All copy uses sentence case (not Title Case) per design system
- [ ] No exclamation marks in UI copy
- [ ] No emoji in UI copy (reserved for Telegram)
