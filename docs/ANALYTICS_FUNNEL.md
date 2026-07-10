# AGC-081 — Product Analytics & Conversion Funnel

This document describes the PostHog event funnel added in AGC-081. It builds on the
existing PostHog integration described in [`docs/analytics.md`](./analytics.md) — same
setup, same env vars, same `track()` / `identify()` / `reset()` helper in
`frontend/services/analytics.ts`. No new dependency was added and no backend changes were made.

---

## Tracked Events

| Event | Fires when | File |
|---|---|---|
| `Landing Page Viewed` | Landing page (`/`) mounts | `frontend/app/page.tsx` |
| `Signup Started` | User submits the register form (validation passed) | `frontend/app/register/page.tsx` |
| `Signup Completed` | Account creation succeeds | `frontend/app/register/page.tsx` |
| `Email Verified` | `/verify-email` confirms the token successfully | `frontend/app/verify-email/page.tsx` |
| `Login Success` | Login succeeds | `frontend/app/login/page.tsx` |
| `Dashboard Viewed` | Dashboard content mounts (authenticated) | `frontend/app/dashboard/page.tsx` |
| `Upload Started` | Video upload begins | `frontend/hooks/usePipeline.ts` |
| `Upload Completed` | Video upload finishes | `frontend/hooks/usePipeline.ts` |
| `Pipeline Started` | AI pipeline job is created | `frontend/hooks/usePipeline.ts` |
| `Pipeline Completed` | AI pipeline job finishes successfully | `frontend/hooks/usePipeline.ts` |
| `Highlights Generated` | Same moment as Pipeline Completed; includes `highlights_found` count | `frontend/hooks/usePipeline.ts` |
| `Download Reel` | User downloads a horizontal or vertical reel (dashboard result, project card, or results panel) | `frontend/app/dashboard/page.tsx`, `frontend/components/ProjectsPanel.tsx`, `frontend/components/ResultPanel.tsx` |
| `Download Thumbnail` | User downloads a thumbnail | same files as above |
| `Project Deleted` | User confirms project deletion | `frontend/components/ProjectsPanel.tsx` |
| `Upgrade Button Clicked` | User clicks "Upgrade to Pro" on the pricing page | `frontend/app/pricing/page.tsx` |
| `Checkout Started` | Razorpay order created and checkout modal is opening | `frontend/app/pricing/page.tsx` |
| `Payment Success` | Payment verified and Pro plan activated | `frontend/app/pricing/page.tsx` |
| `Payment Failed` | Order creation fails, or Razorpay reports `payment.failed`; includes a `reason` string | `frontend/app/pricing/page.tsx` |
| `Logout` | User signs out | `frontend/app/dashboard/page.tsx` |

**Note on pre-existing events:** several events from AGC-081's spec already had a differently-named
equivalent firing in the codebase (e.g. `upload_started`, `pipeline_completed`, `logout`,
`User Registered`, `User Logged In`, `Project Downloaded`). Per the "never remove business logic /
preserve existing behavior" rule, those original calls were **left in place** and the new
canonical event names were added alongside them at the same call sites, using the same `track()`
helper. Nothing was renamed or removed, so no existing PostHog dashboard breaks.

**Note on payment verification retries:** when a payment is captured by Razorpay but the
backend verification call fails or times out (`verification_unconfirmed` state, with a manual
"Retry Verification" button), that path is **not** tagged `Payment Failed` — the payment itself
succeeded, only confirmation is pending, and mislabeling it would corrupt revenue-funnel counts.
It resolves into `Payment Success` once verification succeeds.

---

## User Properties

Set via `identify(userId, properties)` in `frontend/components/PostHogProvider.tsx`, called
whenever auth state or subscription data changes. PostHog `$set` merges partial updates, so
properties fill in as they become available (subscription loads slightly after auth).

| Property | Source |
|---|---|
| `credits_remaining` | `AuthUser.credits_remaining` |
| `verified_email` | `AuthUser.email_verified` |
| `plan` | `SubscriptionInfo.plan` (`FREE` \| `PRO`) |
| `subscription_status` | `SubscriptionInfo.status` (`ACTIVE` \| `EXPIRED` \| `CANCELLED`) |

The distinct ID used for `identify()` remains the backend user ID (integer), unchanged from the
existing implementation. Anonymous (pre-login) events use PostHog's default anonymous ID.

---

## Privacy

Confirmed not sent to PostHog anywhere in this change:
- Email address
- Video filename or file contents
- JWT / auth tokens
- Razorpay payment secrets or signatures (only a human-readable failure `reason` string is sent
  on `Payment Failed`)

Only anonymous/user IDs already used by PostHog, event names, and the properties listed above are sent.

---

## Suggested PostHog Funnels

1. **Activation funnel**
   `Landing Page Viewed` → `Signup Started` → `Signup Completed` → `Email Verified` → `Login Success` → `Dashboard Viewed`

2. **Time-to-value funnel**
   `Dashboard Viewed` → `Upload Started` → `Upload Completed` → `Pipeline Started` → `Pipeline Completed` → `Highlights Generated` → `Download Reel` (or `Download Thumbnail`)

3. **Monetization funnel**
   `Upgrade Button Clicked` → `Checkout Started` → `Payment Success`
   (break out `Payment Failed` as an exclusion/drop-off branch)

---

## Suggested Dashboards

- **Activation**: signup → verified-email conversion rate, login success rate, drop-off between each activation step.
- **Pipeline health**: Upload Started → Upload Completed → Pipeline Started → Pipeline Completed conversion, split by day, to catch upload/pipeline reliability regressions.
- **Engagement**: Highlights Generated per user per week, Download Reel / Download Thumbnail counts, Project Deleted rate.
- **Revenue**: Upgrade Button Clicked → Checkout Started → Payment Success conversion, Payment Failed reasons breakdown, plan/subscription_status distribution (from user properties).
- **Retention**: Dashboard Viewed weekly/monthly active users, segmented by `plan` and `subscription_status` user properties.

---

## Implementation Files

| File | Role |
|---|---|
| `frontend/services/analytics.ts` | `track()`, `identify()`, `reset()` — all calls wrapped in `try/catch` so analytics failures are silent and never block the UI |
| `frontend/components/PostHogProvider.tsx` | Identifies the user and sets `plan` / `credits_remaining` / `subscription_status` / `verified_email` properties |
| `frontend/app/page.tsx` | `Landing Page Viewed` |
| `frontend/app/register/page.tsx` | `Signup Started`, `Signup Completed` |
| `frontend/app/verify-email/page.tsx` | `Email Verified` |
| `frontend/app/login/page.tsx` | `Login Success` |
| `frontend/app/dashboard/page.tsx` | `Dashboard Viewed`, `Logout`, `Download Reel` / `Download Thumbnail` (primary result download) |
| `frontend/hooks/usePipeline.ts` | `Upload Started`, `Upload Completed`, `Pipeline Started`, `Pipeline Completed`, `Highlights Generated` |
| `frontend/components/ProjectsPanel.tsx` | `Download Reel`, `Download Thumbnail`, `Project Deleted` |
| `frontend/components/ResultPanel.tsx` | `Download Reel`, `Download Thumbnail` |
| `frontend/app/pricing/page.tsx` | `Upgrade Button Clicked`, `Checkout Started`, `Payment Success`, `Payment Failed` |
