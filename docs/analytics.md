# AGC Analytics

AGC uses [PostHog](https://posthog.com) for lightweight product analytics. Analytics are **optional** — the app runs normally with no errors if PostHog is not configured.

---

## Setup

1. Create a PostHog account at [app.posthog.com](https://app.posthog.com).
2. Create a project and copy the **Project API Key**.
3. Add the following to `frontend/.env.local`:

```
NEXT_PUBLIC_POSTHOG_KEY=phc_xxxxxxxxxxxxxxxxxxxx
NEXT_PUBLIC_POSTHOG_HOST=https://app.posthog.com
```

4. Restart the dev server (`npm run dev`).

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `NEXT_PUBLIC_POSTHOG_KEY` | No | PostHog project API key |
| `NEXT_PUBLIC_POSTHOG_HOST` | No | PostHog ingest host (default: `https://app.posthog.com`) |

Both variables must be set for analytics to activate. If either is missing or empty, PostHog is never initialized and no data is sent.

---

## Tracked Events

| Event | When it fires |
|---|---|
| `Landing Viewed` | User loads the landing page (`/`) |
| `Login Clicked` | User clicks a Login link on the landing page |
| `Register Clicked` | User clicks a Register / Start Free Beta link on the landing page |
| `User Logged In` | User successfully authenticates via the login form |
| `User Registered` | User successfully creates a new account |
| `Upload Started` | User initiates a video upload |
| `Upload Completed` | Video file upload to the server succeeds |
| `Pipeline Started` | AI pipeline job is created and begins processing |
| `Pipeline Completed` | AI pipeline job finishes successfully |
| `Project Downloaded` | User downloads a reel or thumbnail from My Projects |
| `Project Deleted` | User confirms and deletes a project |
| `User Logged Out` | User clicks Sign Out |

---

## User Identification

After login or registration, PostHog automatically identifies the session using the backend **user ID** (integer). No personally identifiable information beyond the ID is sent. Identification is handled in `PostHogProvider` by watching auth state.

On logout, `posthog.reset()` is called to clear the identity for the session.

---

## Privacy

- No passwords are tracked.
- No JWT tokens are tracked.
- No uploaded filenames or video paths are tracked.
- No video metadata is tracked.
- No personal content is ever sent to PostHog.
- Only product usage events (listed above) are captured.

---

## How to Disable Analytics

Remove or leave blank either PostHog variable in `.env.local`:

```
NEXT_PUBLIC_POSTHOG_KEY=
NEXT_PUBLIC_POSTHOG_HOST=
```

Analytics will disable themselves silently with no runtime errors. No code changes are needed.

---

## Implementation Files

| File | Role |
|---|---|
| `frontend/instrumentation-client.ts` | Initializes PostHog before the app mounts (reads env vars; skips if missing) |
| `frontend/services/analytics.ts` | `track()`, `identify()`, `reset()` — thin wrappers over posthog-js |
| `frontend/components/PostHogProvider.tsx` | Wraps the app; auto-identifies the authenticated user via `useAuth()` |
| `frontend/app/layout.tsx` | Mounts `PostHogProvider` inside `AuthProvider` |
