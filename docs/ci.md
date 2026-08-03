# CI Quality Gate (VED-P1-001)

Two workflows run on every push to `main` and every pull request targeting `main`:

- **`.github/workflows/build.yml`** — "Build Verification": backend compiles, frontend builds.
- **`.github/workflows/quality-gate.yml`** — "CI Quality Gate": tests, coverage, type checking,
  lint, and workflow validation.

## Jobs

| Job | What it checks | Scope |
|---|---|---|
| `backend-tests` | `pytest` over `backend/tests/`, with coverage report | full suite |
| `frontend-typecheck` | `tsc --noEmit` | full project |
| `frontend-tests` | `node --test` (native Node test runner, via `tsx` for TS) with coverage | full suite |
| `frontend-lint-changed` | `eslint` | only files changed in the PR/push (see below) |
| `workflow-lint` | `actionlint` against `.github/workflows/*.yml` | full |

## Required checks (branch protection)

To make this a real gate, mark these as required status checks on `main` in
GitHub repo settings → Branches → Branch protection rules:

- `Backend Tests + Coverage`
- `Frontend TypeScript`
- `Frontend Tests + Coverage`
- `Frontend Lint (changed files)`
- `Validate Workflow Files`
- `Backend Build Check` / `Frontend Build Check` (from `build.yml`)

This repo change does not itself configure branch protection — that's a
repo-settings change with its own blast radius and needs an explicit,
separate decision by someone with admin access.

## Why lint is scoped to changed files, not the whole repo

At the time this gate was built, `npm run lint` on the full repo reported
11 pre-existing errors (`@typescript-eslint/no-explicit-any` in
`services/api.ts`, a `react-hooks/set-state-in-effect` violation in
`hooks/useSubscription.ts`, plus related warnings). None of these are
introduced by this sprint, and gating the whole repo on them would block
unrelated work until someone does a separate cleanup pass.

Instead, `frontend-lint-changed` diffs the PR (or push) against its base
commit and runs ESLint only on the `.ts`/`.tsx` files that changed. This
means:

- A PR that doesn't touch `api.ts` or `useSubscription.ts` is unaffected
  by their existing errors.
- A PR that *does* touch one of those files will see ESLint run against
  the whole file (ESLint doesn't have a "only my changed lines" mode),
  so fixing pre-existing errors in a file you're already editing is
  expected — this is the standard "leave it better than you found it"
  bar, not a demand to fix unrelated files.

Backend tests, frontend tests, and `tsc --noEmit` are **not** scoped this
way — they were verified clean (0 failures / 0 errors) on the current
baseline before this gate was added, so a full-repo run only fails on an
actual regression, never on legacy debt.

## Coverage

- Backend: `pytest-cov` (`backend/requirements-dev.txt`), uploaded as the
  `backend-coverage` workflow artifact (`coverage.xml`). Baseline is ~61%
  line coverage — no enforced minimum yet; this is visibility, not a gate.
- Frontend: Node's built-in `--experimental-test-coverage`, printed to the
  job log. No artifact upload (Node's coverage reporter doesn't emit lcov
  by default without extra config) — revisit if/when frontend test count
  grows enough to justify a coverage service.

Neither coverage number is enforced as a failing threshold. Enforcing one
now would fail the gate on pre-existing gaps rather than new regressions,
which is exactly what this sprint is scoped to avoid. Add a
`--cov-fail-under` (backend) once the team picks a real target.

## Environment validation

`backend/tests/test_config_environment_validation.py` exercises the
production fail-fast guard in `backend/app/config/config.py`: importing
the config module with `ENVIRONMENT=production` and no `JWT_SECRET_KEY`
must raise immediately (not fall back to a random per-process secret,
which would silently invalidate every session on restart). This guard
existed before this sprint but had no test coverage; it's included here
because it's exactly the kind of "does the app fail loudly on
misconfiguration" check a CI environment-validation step is meant to
catch, and it's real behavior in `config.py`, not new logic invented for
CI.

## Running the same checks locally

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
pytest --cov=app --cov-report=term-missing

# Frontend
cd frontend
npm ci
npm run typecheck
npm run test:coverage
npm run lint            # whole repo — will show the pre-existing baseline errors above
```

## Known gaps (not in scope for VED-P1-001)

- No branch protection configured (see "Required checks" above).
- No coverage-percentage gate (backend or frontend).
- The 11 pre-existing ESLint errors in `services/api.ts` and
  `hooks/useSubscription.ts` are untouched — tracked as separate cleanup,
  not blocked by or blocking this gate.
