# ADR-0016: Alpha delivery via Telegram channel

- **Status**: Proposed
- **Date**: 2026-04-06
- **Deciders**: Architect, Lead

## Context

SportsLab is launching a free alpha to validate the prediction model live and build a waitlist
for the paid product (R6). We need to decide how to deliver daily predictions to alpha users
(25-50 people) with minimal new infrastructure.

The system already has: `TelegramNotifier` class, `sl notify bet-slip` and `sl notify results`
CLI commands, Telegram bet slip and results renderers (Markdown format), daily pipeline
orchestrator calling these commands.

## Options considered

1. **Telegram channel (private, invite-only)**
   - Pros: Already implemented (zero new code). Polish betting community is Telegram-native.
     Invite-only provides access control. Push notifications on mobile.
   - Cons: No programmatic access for users. Limited formatting (Markdown only). Vendor lock-in
     on Telegram platform.

2. **Email (SendGrid / Resend)**
   - Pros: Universal delivery. HTML formatting. Easy to track opens.
   - Cons: Requires new integration (email service, templates, deliverability config).
     1-2 days of additional work. Spam risk. No real-time push.

3. **Discord server**
   - Pros: Similar to Telegram. Better for community building (threads, channels).
   - Cons: Requires new Discord bot integration. Smaller footprint in Polish betting community.
     Not built yet.

4. **Web dashboard (FastAPI + frontend)**
   - Pros: Rich formatting, interactive charts, user accounts.
   - Cons: Weeks of work. Requires auth, hosting, frontend. Massively premature for alpha.

5. **API (FastAPI + API keys)**
   - Pros: Programmatic access. Foundation for paid product.
   - Cons: Weeks of work. Alpha users are evaluating, not integrating. Premature.

## Decision

We chose **Telegram channel** because the delivery mechanism is already fully implemented
and tested. The code path is: `daily_pipeline.py` -> `sl notify bet-slip` -> `TelegramNotifier`
-> Telegram Bot API -> private channel. Zero new code, zero new infrastructure, zero new
dependencies.

Building any alternative would delay alpha launch by days (email) to weeks (dashboard/API)
for zero additional value at this stage.

## Consequences

- Positive: Alpha can launch without any delivery-related code changes.
- Positive: Natural mobile experience with push notifications.
- Positive: Invite-only channel = built-in access control without auth infrastructure.
- Negative: No programmatic access for alpha users (they cannot query predictions via API).
  Acceptable because alpha users are evaluating quality, not building integrations.
- Negative: Limited to Markdown formatting. Mitigated by linking to hosted HTML reports
  for detailed charts and analysis.
- Neutral: Telegram becomes one delivery channel among many when the API launches in R6.
  It does not create technical debt.

## References

- `packages/ml-in-sports/src/ml_in_sports/notification/telegram.py`
- `packages/ml-in-sports/src/ml_in_sports/cli/notify_cmd.py`
- `packages/ml-in-sports/src/ml_in_sports/prediction/report/telegram.py`
- `infra/daily_pipeline.py`
- `docs/alpha_launch_plan.md` (Section 11)
