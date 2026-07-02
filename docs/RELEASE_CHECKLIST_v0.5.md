# AGC v0.5.0-beta — Release Checklist

**Version:** v0.5.0-beta
**Environment:** ___________________________
**Release Engineer:** ___________________________
**Date:** ___________________________

Mark each item ✅ before tagging the release.

---

## 1. Version Audit

| # | Check | Expected | Status |
|---|-------|----------|--------|
| 1.1 | `backend/app/config/config.py` `APP_VERSION` default | `0.5.0-beta` | |
| 1.2 | `frontend/package.json` `version` | `0.5.0-beta` | |
| 1.3 | `README.md` version badge | `v0.5.0-beta` | |
| 1.4 | `CHANGELOG.md` top entry | `[v0.5.0-beta]` | |
| 1.5 | `backend/.env.example` `APP_VERSION` | `0.5.0-beta` | |
| 1.6 | `docs/PRIVATE_BETA.md` version | `v0.5.0-beta` | |
| 1.7 | `docs/BETA_CHECKLIST.md` title | `v0.5.0-beta` | |
| 1.8 | `docs/RELEASE_NOTES_v0.5.0-beta.md` exists | Present | |

---

## 2. Repository Audit

| # | Check | Expected | Status |
|---|-------|----------|--------|
| 2.1 | No `*.pyc` or `__pycache__` tracked in git | `git ls-files \| grep pyc` returns empty | |
| 2.2 | No `venv/` tracked | Not in git index | |
| 2.3 | No `.env` tracked | Not in git index | |
| 2.4 | No SQLite `.db` files tracked | `git ls-files \| grep \.db` returns empty | |
| 2.5 | No log files tracked | `git ls-files \| grep \.log` returns empty | |
| 2.6 | No uploaded videos tracked | `backend/storage/` not in git | |
| 2.7 | No thumbnails or highlights tracked | `storage/thumbnails/`, `storage/highlights/` not in git | |
| 2.8 | No benchmark output artifacts tracked | `benchmark/outputs/`, `benchmark/storage/` gitignored | |
| 2.9 | No `benchmark/results/` outputs tracked | Only `.gitkeep` tracked | |
| 2.10 | No `node_modules/` tracked | `frontend/node_modules/` not in git | |
| 2.11 | No `.next/` build output tracked | Not in git | |

---

## 3. Backend Checklist

| # | Check | Expected | Status |
|---|-------|----------|--------|
| 3.1 | `pip install -r requirements.txt` completes without error | Exit code 0 | |
| 3.2 | `uvicorn app.main:app` starts without error | No import errors, no crash | |
| 3.3 | Startup log shows DB initialized | `✅ SQLite Database Initialized` | |
| 3.4 | `GET /health` returns 200 | `{"status": "ok"}` | |
| 3.5 | `GET /ready` returns 200 | Ready response | |
| 3.6 | `GET /metrics` returns 200 | Metrics payload | |
| 3.7 | `GET /version` returns `0.5.0-beta` | Version in response body | |
| 3.8 | `GET /docs` loads Swagger UI | 200, all endpoints visible | |
| 3.9 | `/feedback` router present in Swagger | `POST /feedback` listed | |
| 3.10 | Game profile detection active | SnowRunner filename → SnowRunner profile in explain block | |
| 3.11 | Explanation block on ranked highlights | `explanation` key present in pipeline result | |
| 3.12 | `JWT_SECRET_KEY` loaded from `.env`, not hardcoded | Confirmed via code review | |
| 3.13 | No `.env` file committed | `git ls-files backend/.env` returns empty | |

---

## 4. Frontend Checklist

| # | Check | Expected | Status |
|---|-------|----------|--------|
| 4.1 | `npm install` completes without error | Exit code 0 | |
| 4.2 | `npm run build` completes without error | No TypeScript errors, no build failure | |
| 4.3 | `npm run lint` passes | No lint errors | |
| 4.4 | Login page loads | Renders without console errors | |
| 4.5 | Register page loads | Renders without console errors | |
| 4.6 | Dashboard loads after login | Renders without console errors | |
| 4.7 | `FeedbackCard` renders after highlight generation | Feedback form visible | |
| 4.8 | PostHog analytics disabled when key absent | No analytics network calls when `NEXT_PUBLIC_POSTHOG_KEY` empty | |
| 4.9 | `NEXT_PUBLIC_API_URL` loaded from env, not hardcoded | Confirmed via code review | |
| 4.10 | No `.env.local` committed | Not in git | |

---

## 5. Deployment Checklist

| # | Check | Expected | Status |
|---|-------|----------|--------|
| 5.1 | `backend/.env` populated on server | All required vars set | |
| 5.2 | `ENVIRONMENT=production` on server | Set in `.env` | |
| 5.3 | `HTTPS_ENABLED=true` on server | Set in `.env` | |
| 5.4 | `JWT_SECRET_KEY` is a strong random hex string | Not the placeholder value | |
| 5.5 | `frontend/.env.local` set to production API URL | `NEXT_PUBLIC_API_URL=https://api.highlightai.in` | |
| 5.6 | Nginx config deployed and test passes | `nginx -t` prints `syntax is ok` | |
| 5.7 | SSL cert valid on all three domains | `https://highlightai.in`, `https://www.highlightai.in`, `https://api.highlightai.in` | |
| 5.8 | HTTP → HTTPS redirect active | `curl http://highlightai.in` returns 301 | |
| 5.9 | Ports 3000 and 8000 blocked externally | UFW `deny 3000`, `deny 8000` | |
| 5.10 | Backend running under systemd or supervisor | Survives reboot | |
| 5.11 | Frontend running under pm2 or systemd | Survives reboot | |
| 5.12 | `GET /health` returns 200 from public internet | `curl https://api.highlightai.in/health` → 200 | |
| 5.13 | HSTS header present in production | `Strict-Transport-Security` in response headers | |

---

## 6. Rollback Checklist

If the release must be rolled back to v0.4.0-beta:

| # | Step | Status |
|---|------|--------|
| 6.1 | Identify the last known-good commit hash for v0.4.0-beta | `git log --oneline` → find `AGC v0.4.0-beta` tag or commit | |
| 6.2 | Stop the backend service on the server | `systemctl stop agc-backend` | |
| 6.3 | Check out the v0.4.0-beta commit | `git checkout v0.4.0-beta` or `git checkout <hash>` | |
| 6.4 | Reinstall backend dependencies | `pip install -r requirements.txt` | |
| 6.5 | Rebuild frontend | `npm run build` | |
| 6.6 | Restart backend and frontend services | `systemctl start agc-backend` | |
| 6.7 | Verify `/health` and `/version` | Confirm old version is live | |
| 6.8 | Note: SQLite schema is backward compatible — no migration needed | No DB rollback required | |

---

## 7. Git Readiness

| # | Check | Expected | Status |
|---|-------|----------|--------|
| 7.1 | All v0.5.0-beta source files committed | `git status` shows clean working tree | |
| 7.2 | Release commit message follows convention | Starts with `AGC v0.5.0-beta —` | |
| 7.3 | Git tag created | `git tag v0.5.0-beta` | |
| 7.4 | Tag pushed to remote | `git push origin v0.5.0-beta` | |
| 7.5 | `git log --oneline -5` shows the release commit at HEAD | Confirmed | |

---

## Sign-Off

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tester | | | |
| Product Owner | | | |
