# AGC-081 — Product Analytics & Conversion Funnel

This document describes the PostHog event funnel added in AGC-081. It builds on the
existing PostHog integration described in [`docs/analytics.md`](./analytics.md) — same
setup, same env vars, same `track()` / `identify()` / `reset()` helper in
`frontend/services/analytics.ts`. No new dependency was added and no backend changes were made
(AGC-081 was frontend-only; see [VED-ANALYTICS-005 — Backend-Authoritative Pipeline
Lifecycle](#ved-analytics-005--backend-authoritative-pipeline-lifecycle) below for the events that
were later moved server-side).

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
| `Upload Started` / `upload_started` **(backend-authoritative)** | Upload passes every validation gate (maintenance, disk space, filename, extension, size, MIME, rate limit) and the backend commits to processing it | `backend/app/routers/upload.py` |
| `Upload Completed` / `upload_completed` **(backend-authoritative)** | Backend has written the file to disk, validated duration, and cached the upload | `backend/app/routers/upload.py` |
| `Pipeline Started` / `pipeline_started` **(backend-authoritative)** | Job actually transitions `pending` → `processing` on a worker thread — not merely created, and not tied to frontend polling | `backend/app/services/job_service.py` (`JobService.start_processing`) |
| `Pipeline Completed` / `pipeline_completed` **(backend-authoritative)** | Job reaches the authoritative `completed` state; `Pipeline Completed` additionally carries `processing_time_seconds` when available | `backend/app/services/job_service.py` (`JobService.complete_job`) |
| `pipeline_failed` **(backend-authoritative)** | Job reaches the authoritative `failed` state; carries `status: "failed"` only, never the raw error | `backend/app/services/job_service.py` (`JobService.fail_job`) |
| `Highlights Generated` **(backend-authoritative)** | Same `complete_job()` transition as `Pipeline Completed`; includes `highlights_found` count | `backend/app/services/job_service.py` (`JobService.complete_job`) |
| `Download Reel` | User downloads a horizontal or vertical reel (dashboard result, project card, or results panel) | `frontend/app/dashboard/page.tsx`, `frontend/components/ProjectsPanel.tsx`, `frontend/components/ResultPanel.tsx` |
| `Download Thumbnail` | User downloads a thumbnail | same files as above |
| `Project Deleted` | User confirms project deletion | `frontend/components/ProjectsPanel.tsx` |
| `Upgrade Button Clicked` | User clicks "Upgrade to Pro" on the pricing page | `frontend/app/pricing/page.tsx` |
| `Checkout Started` | Razorpay order created and checkout modal is opening | `frontend/app/pricing/page.tsx` |
| `Payment Success` | Payment verified and Pro plan activated | `frontend/app/pricing/page.tsx` |
| `Payment Failed` | Order creation fails, or Razorpay reports `payment.failed`; includes a `reason` string and a `failure_category` (see below) | `frontend/app/pricing/page.tsx` |
| `Logout` | User signs out | `frontend/app/dashboard/page.tsx` |
| `pricing_page_viewed` | Pricing page (`/pricing`) mounts | `frontend/app/pricing/page.tsx` |
| `credits_exhausted_cta_viewed` | The "out of credits / Upgrade to Pro" CTA on the dashboard upload panel first becomes visible in a given mount | `frontend/components/UploadPanel.tsx` |
| `credits_exhausted_cta_clicked` | User clicks the "Upgrade to Pro" link inside that CTA | `frontend/components/UploadPanel.tsx` |
| `dashboard_first_visit_empty` | Authenticated dashboard mounts and `jobStats` has loaded with zero jobs in every status (queued/running/completed/failed) | `frontend/app/dashboard/page.tsx` |
| `upload_ui_seen` | The upload UI becomes actually usable (not blocked by maintenance mode, still-loading subscription, or exhausted credits) for a user with zero jobs | `frontend/components/UploadPanel.tsx` |
| `file_selected` | User picks a video file via the file picker or drag-and-drop, for any user (not gated to zero-job users) | `frontend/components/UploadPanel.tsx` |

**Note on pre-existing events:** several events from AGC-081's spec already had a differently-named
equivalent firing in the codebase (e.g. `upload_started`, `pipeline_completed`, `logout`,
`User Registered`, `User Logged In`, `Project Downloaded`). Per the "never remove business logic /
preserve existing behavior" rule, those original calls were **left in place** and the new
canonical event names were added alongside them at the same call sites, using the same `track()`
helper. Nothing was renamed or removed, so no existing PostHog dashboard breaks. VED-ANALYTICS-005
carried this same dual-naming forward when moving these events server-side: both names are still
sent, just from `AnalyticsService` instead of `track()` — see the dedicated section below.

**Note on payment verification retries:** when a payment is captured by Razorpay but the
backend verification call fails or times out (`verification_unconfirmed` state, with a manual
"Retry Verification" button), that path is **not** tagged `Payment Failed` — the payment itself
succeeded, only confirmation is pending, and mislabeling it would corrupt revenue-funnel counts.
It resolves into `Payment Success` once verification succeeds.

---

## GROW-007 — Conversion Funnel Truth

### `Payment Failed.failure_category`

`Payment Failed` now carries a `failure_category` alongside the existing `reason` string. Only
categories the current architecture can prove are used — both are derived deterministically from
which stage of `handleUpgrade` (`frontend/app/pricing/page.tsx`) was in flight when the failure
occurred, not from parsing error text:

| Value | Fires when |
|---|---|
| `order_creation_failed` | `createPaymentOrder` throws before a Razorpay order exists |
| `checkout_failed` | Razorpay checkout fails to open, or Razorpay itself reports `payment.failed` after the modal opened |

There is no `verification_failed` category: as noted above, a verification failure/timeout is
intentionally **not** tagged `Payment Failed` (the payment already succeeded), so no call site
exists to attribute that category to.

### `pricing_page_viewed` / credit-exhaustion CTA dedup

- `pricing_page_viewed` fires from a `useEffect(() => { ... }, [])` on mount, the same pattern as
  `Landing Page Viewed` and `Dashboard Viewed` — a checkout-state re-render never re-triggers it.
  (`pipeline_failed`'s dedup used to live here too, via the polling branch that observed a
  terminal `job.status === "failed"`; VED-ANALYTICS-005 moved it server-side — see below.)
- `credits_exhausted_cta_viewed` fires once per `UploadPanel` mount, guarded by a ref that flips
  the first time `outOfCredits` becomes `true`; it does not re-fire on subsequent renders while the
  CTA stays visible.
- `credits_exhausted_cta_clicked` fires from the CTA `Link`'s `onClick`, in addition to (not instead
  of) its normal navigation to `/pricing`. It is a distinct signal from `Upgrade Button Clicked`,
  which is preserved unchanged and only fires from the pricing page itself.

---

## VED-GROWTH-001 Slice 2 — Verified→First-Upload Diagnostic

Measurement-only instrumentation to understand why verified users do not reach their first
upload. No backend/database/payment/pipeline changes; no onboarding UX or dashboard redesign.

- `dashboard_first_visit_empty` fires from a `useEffect(() => { ... }, [jobStats])` in
  `frontend/app/dashboard/page.tsx`, gated on `jobStats !== null` (job counts have loaded) and the
  sum of `queued + running + completed + failed` being zero. `jobStats` starts `null` until
  `usePipeline`'s mount effect resolves, so the event cannot fire before job data is known, and it
  never fires for a user who has any job in any status. A `useRef` guard fires it at most once per
  mount even though the effect re-runs on every `jobStats` poll (the 5s interval in `usePipeline`).
- `upload_ui_seen` fires from a `useEffect` in `frontend/components/UploadPanel.tsx`, gated on the
  same zero-jobs signal (passed down as the `zeroJobs` prop) **and** the upload UI being actually
  usable: `!maintenanceMode && !subscriptionLoading && !outOfCredits`. `subscriptionLoading` is
  checked explicitly because `outOfCredits` alone reads as `false` while the subscription is still
  resolving, which would otherwise let the event fire before credit status is actually known. Its
  own `useRef` guard fires it at most once per mount.
- `file_selected` fires directly from `UploadPanel`'s `handleFiles`, covering both the file-picker
  and drag-and-drop paths, for any user — no existing "file selected" event was found to reuse, and
  it isn't gated to zero-job users since it's a generic, reusable upload-interaction signal.
- The fire-once boolean logic for the first two events (`hasZeroJobs`, `shouldTrackDashboardFirstVisitEmpty`,
  `shouldTrackUploadUiSeen`) lives in `frontend/utils/firstUploadDiagnostics.ts`, extracted the same
  way `uploadPanelState.ts` and `resultUpgradeCta.ts` were — this project has no
  jsdom/React-testing-library, so the pure decision functions are what's actually unit-tested
  (`frontend/utils/firstUploadDiagnostics.test.ts`), with static-source drift guards proving the
  components wire up to them.

### Repeat-user definition (corrected)

**Repeat user = an external user with AI jobs on at least 2 distinct calendar dates**
(`COUNT(DISTINCT date(jobs.created_at)) >= 2`, scoped to `is_internal = 0` users with a
resolvable `jobs.user_id`), computed in
`MissionControlService._get_live_metrics` (`backend/app/services/mission_control_service.py`).

Previously this used `COUNT(*) >= 2` — i.e. two-or-more job rows for the same user, with no
date distinction. That counted same-day retries and repeated runs (e.g. re-running the pipeline
twice in one sitting) as "returned", which is not a retention signal. This is a simple MVP
return-usage signal, not a cohort retention model — it says nothing about time-to-return, churn,
or repeat frequency, only whether the user has ever come back on a different day.

---

## VED-ANALYTICS-005 — Backend-Authoritative Pipeline Lifecycle

VED-ANALYTICS-004's forensic audit of a 22→7 (`Upload Started` → `Highlights Generated`) funnel
drop traced most of it to an instrumentation gap, not genuine pipeline failure: `Upload Started`,
`Upload Completed`, `Pipeline Started`, `Pipeline Completed`, and `pipeline_failed` were all fired
from `frontend/hooks/usePipeline.ts`, which depends on the originating browser tab staying open —
for `Pipeline Completed`/`pipeline_failed`, for the entire AI processing duration. VED-ANALYTICS-002
had already fixed this same flaw for `Highlights Generated` by moving it to the backend; this
sprint completes the same reliability model for the rest of the pipeline lifecycle.

### Which events are backend-authoritative vs. client-side

| Backend-authoritative (fires regardless of browser/tab state) | Remains client-side (genuine UI/browser interaction) |
|---|---|
| `Upload Started` / `upload_started` | `Download Reel` / `Download Thumbnail` |
| `Upload Completed` / `upload_completed` | `Upgrade Button Clicked` |
| `Pipeline Started` / `pipeline_started` | `Checkout Started` |
| `Pipeline Completed` / `pipeline_completed` | All other UI/navigation events in the table above |
| `pipeline_failed` | |
| `Highlights Generated` (VED-ANALYTICS-002) | |
| `Payment Success` (VED-ANALYTICS-003) | |

**Why backend lifecycle events are authoritative:** each one is now dispatched from the single
place the underlying state transition actually, durably happens — a DB row flip or a successful
disk write — rather than from a UI effect that only runs if the tab is still open to observe it:

| Event | Authoritative source |
|---|---|
| `Upload Started` | `backend/app/routers/upload.py` — after every validation gate passes, before the file is written |
| `Upload Completed` | `backend/app/routers/upload.py` — after the file is written, duration-validated, and cached |
| `Pipeline Started` | `JobService.start_processing()` — the `pending`→`processing` DB transition, called once from `BackgroundJobService.run_pipeline()` |
| `Pipeline Completed` | `JobService.complete_job()` — the `→ completed` DB transition |
| `pipeline_failed` | `JobService.fail_job()` — the `→ failed` DB transition |
| `Highlights Generated` | `JobService.complete_job()` (unchanged from VED-ANALYTICS-002) |

### Exactly-once mechanism

`Pipeline Completed` and `Highlights Generated` share `complete_job()`'s existing compare-and-swap
UPDATE (`WHERE status != 'completed'`) — both are gated on the same `became_completed` flip, each
in its own `try`/`except` so a failure in one can never suppress the other. `Pipeline Started` and
`pipeline_failed` got their own new CAS guards following the identical pattern:
`start_processing()` only flips (and fires) on `WHERE status = 'pending'`; `fail_job()` now guards
`WHERE status NOT IN ('completed', 'failed')`, so a job already completed can never be clobbered
into `failed` by a late/duplicate call, and a job already failed never double-fires. `Upload
Started`/`Upload Completed` have no DB row to CAS against — they're a single straight-through
function execution per HTTP request with no retry path, so natural once-per-request execution is
the exactly-once guarantee. In every case, unattributed jobs (`user_id IS NULL` — legacy rows
predating auth-required uploads) are skipped rather than fabricating an analytics identity, same
as `Highlights Generated`.

### Naming convention

Every event that already had both a legacy snake_case name and a PascalCase name when it was
client-side (`upload_started`/`Upload Started`, `pipeline_started`/`Pipeline Started`,
`pipeline_completed`/`Pipeline Completed`) is still dual-tracked from the backend — two separate
PostHog capture calls per lifecycle moment, so no existing dashboard built on either name breaks.
`pipeline_failed` never had a PascalCase counterpart and still doesn't. `Pipeline Completed`
(PascalCase only, matching the retired frontend call site) additionally carries
`processing_time_seconds` when `result.stats.processing_time` is available. `Upload Completed`
(PascalCase only) still carries the idempotent `$set: {first_upload_completed: true}` person
property.

### distinct_id convention

Same as `Highlights Generated`/`Payment Success`: the backend integer `user_id`, stringified
(`str(user_id)`), so backend-originated events land on the same PostHog person timeline as
client-originated ones (see [User Properties](#user-properties) below for the frontend
`identify()` side of this convention).

### Failure isolation

All five events go through `AnalyticsService`'s existing best-effort posture: dispatched on a
2-worker `ThreadPoolExecutor` so a slow/unreachable PostHog call never blocks the request/job
thread, wrapped in `try`/`except` at both the dispatch call site (`upload.py`, `job_service.py`)
and inside `AnalyticsService` itself, and a no-op when `POSTHOG_API_KEY`/`POSTHOG_HOST` aren't
configured. Analytics can never fail an upload, job creation, pipeline execution, or job
completion/failure.

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
| `frontend/components/ProjectsPanel.tsx` | `Download Reel`, `Download Thumbnail`, `Project Deleted` |
| `frontend/components/ResultPanel.tsx` | `Download Reel`, `Download Thumbnail` |
| `frontend/app/pricing/page.tsx` | `Upgrade Button Clicked`, `Checkout Started`, `Payment Failed` (+ `failure_category`), `pricing_page_viewed` |
| `frontend/components/UploadPanel.tsx` | `credits_exhausted_cta_viewed`, `credits_exhausted_cta_clicked`, `upload_ui_seen`, `file_selected` |
| `frontend/utils/firstUploadDiagnostics.ts` | Pure fire-once decisions for `dashboard_first_visit_empty` / `upload_ui_seen` |
| `backend/app/services/mission_control_service.py` | `repeat_users` — distinct-calendar-date definition (GROW-007) |
| `backend/app/services/analytics_service.py` | `AnalyticsService` — all backend-authoritative capture methods (VED-ANALYTICS-002/003/005) |
| `backend/app/routers/upload.py` | `Upload Started` / `upload_started`, `Upload Completed` / `upload_completed` (VED-ANALYTICS-005) |
| `backend/app/services/job_service.py` | `Pipeline Started` / `pipeline_started`, `Pipeline Completed` / `pipeline_completed`, `pipeline_failed`, `Highlights Generated` (VED-ANALYTICS-002/005) |
| `backend/app/services/payment_service.py` | `Payment Success` (VED-ANALYTICS-003) |
