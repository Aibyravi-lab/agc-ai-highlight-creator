# AGC v0.5.0-beta — Beta Verification Checklist

Complete this checklist on a fresh staging or production environment before announcing the public beta.

**Environment:** ___________________________
**Tester:** ___________________________
**Date:** ___________________________

---

## 1. Authentication

| # | Test | Expected Result | Status | Notes | Date Verified |
|---|------|-----------------|--------|-------|---------------|
| 1.1 | Register new account | 201 response, user stored in DB | | | |
| 1.2 | Register with duplicate email | 409 or 422 error response | | | |
| 1.3 | Register with invalid email format | 422 validation error | | | |
| 1.4 | Register with empty password | 422 validation error | | | |
| 1.5 | Login with correct credentials | 200 response with JWT token | | | |
| 1.6 | Login with wrong password | 401 unauthorized | | | |
| 1.7 | Login with unknown email | 401 unauthorized | | | |
| 1.8 | Access protected endpoint without token | 401 unauthorized | | | |
| 1.9 | Access protected endpoint with expired token | 401 unauthorized | | | |
| 1.10 | Access protected endpoint with valid token | 200 success | | | |
| 1.11 | Passwords stored as bcrypt hash (not plaintext) | Verify in SQLite: `password_hash` starts with `$2b$` | | | |

---

## 2. Upload

| # | Test | Expected Result | Status | Notes | Date Verified |
|---|------|-----------------|--------|-------|---------------|
| 2.1 | Upload valid MP4 | 200 response, file stored in `storage/uploads/` | | | |
| 2.2 | Upload valid MOV | 200 response | | | |
| 2.3 | Upload valid WebM | 200 response | | | |
| 2.4 | Upload valid AVI | 200 response | | | |
| 2.5 | Upload valid MKV | 200 response | | | |
| 2.6 | Upload file with wrong extension but valid video bytes | Accepted based on MIME header | | | |
| 2.7 | Upload a .jpg renamed to .mp4 | 415 or 422 rejection (MIME validation) | | | |
| 2.8 | Upload file > 500 MB | 413 rejection | | | |
| 2.9 | Upload same file twice within 10 minutes | Second upload returns dedup response | | | |
| 2.10 | Upload same file after 10-minute window | Accepted as new upload | | | |
| 2.11 | Upload without authentication | 401 unauthorized | | | |

---

## 3. Pipeline

| # | Test | Expected Result | Status | Notes | Date Verified |
|---|------|-----------------|--------|-------|---------------|
| 3.1 | Trigger pipeline on uploaded video | 202 Accepted, job ID returned | | | |
| 3.2 | Pipeline extracts metadata | FFprobe data returned (duration, FPS, resolution, codec) | | | |
| 3.3 | Pipeline extracts frames | Frames written to `storage/frames/` | | | |
| 3.4 | Pipeline runs vision analysis | Highlight moments scored per frame | | | |
| 3.5 | Pipeline runs audio extraction | WAV file created | | | |
| 3.6 | Pipeline runs Whisper transcription | Transcription result available | | | |
| 3.7 | Pipeline runs scoring | Multi-signal scores computed for each moment | | | |
| 3.8 | Pipeline generates clips | Clip files written to `storage/highlights/` | | | |
| 3.9 | Pipeline generates thumbnails | Thumbnail images in `storage/thumbnails/` | | | |
| 3.10 | Pipeline runs to completion | Job status changes to `completed` | | | |
| 3.11 | Pipeline on an unsupported video format | Job fails gracefully with error message | | | |
| 3.12 | Pipeline with no audio track | Whisper skipped, pipeline continues | | | |
| 3.13 | Trigger pipeline without authentication | 401 unauthorized | | | |

---

## 4. Background Jobs

| # | Test | Expected Result | Status | Notes | Date Verified |
|---|------|-----------------|--------|-------|---------------|
| 4.1 | Job starts async — API returns immediately | 202 response before processing completes | | | |
| 4.2 | Job status endpoint returns current state | `pending` → `running` → `completed` | | | |
| 4.3 | Two concurrent jobs per user allowed | Both jobs run | | | |
| 4.4 | Third concurrent job per user rejected | 429 or queue rejection | | | |
| 4.5 | Job for User A not visible to User B | 404 or 403 when User B queries User A's job | | | |
| 4.6 | Failed job status reflected | Status `failed` with error detail | | | |
| 4.7 | API remains responsive during job processing | Other endpoints return < 200ms while job runs | | | |

---

## 5. History

| # | Test | Expected Result | Status | Notes | Date Verified |
|---|------|-----------------|--------|-------|---------------|
| 5.1 | History endpoint returns user's completed jobs | List of jobs with results | | | |
| 5.2 | History scoped to authenticated user | User A's jobs not visible to User B | | | |
| 5.3 | History without authentication | 401 unauthorized | | | |
| 5.4 | Empty history for new user | Empty list, no error | | | |
| 5.5 | History contains clip URLs | URLs resolve to downloadable clips | | | |
| 5.6 | History contains highlight scores | Scores present in result payload | | | |

---

## 6. Projects

| # | Test | Expected Result | Status | Notes | Date Verified |
|---|------|-----------------|--------|-------|---------------|
| 6.1 | Create a new project | 201 response, project ID returned | | | |
| 6.2 | List projects for user | Returns only the user's projects | | | |
| 6.3 | Projects scoped to authenticated user | User A cannot see User B's projects | | | |
| 6.4 | Associate job result with project | Job result linked to project | | | |
| 6.5 | Delete project | Project and associations removed | | | |
| 6.6 | Access projects without authentication | 401 unauthorized | | | |

---

## 7. Downloads

| # | Test | Expected Result | Status | Notes | Date Verified |
|---|------|-----------------|--------|-------|---------------|
| 7.1 | Download generated clip via URL | File downloads successfully | | | |
| 7.2 | Download thumbnail via URL | Image downloads successfully | | | |
| 7.3 | Download with invalid path | 404 response | | | |
| 7.4 | Path traversal attempt in download URL | 400 or 404 rejection | | | |
| 7.5 | Static file serving via `/storage/` mount | Files accessible without authentication (by design) | | | |

---

## 8. Cleanup

| # | Test | Expected Result | Status | Notes | Date Verified |
|---|------|-----------------|--------|-------|---------------|
| 8.1 | Temp files cleaned after job completion | `storage/frames/` entries for job removed | | | |
| 8.2 | Uploaded source video retained post-processing | Raw upload preserved for re-processing | | | |
| 8.3 | Cleanup does not delete active job files | Running job files untouched | | | |
| 8.4 | Manual cleanup endpoint (if present) | Returns success, removes stale files | | | |

---

## 9. Security

| # | Test | Expected Result | Status | Notes | Date Verified |
|---|------|-----------------|--------|-------|---------------|
| 9.1 | Response headers include `X-Content-Type-Options: nosniff` | Present on all responses | | | |
| 9.2 | Response headers include `X-Frame-Options: SAMEORIGIN` | Present on all responses | | | |
| 9.3 | Response headers include `Referrer-Policy` | Present on all responses | | | |
| 9.4 | Response headers include `Permissions-Policy` | Present on all responses | | | |
| 9.5 | HSTS header present in production (HTTPS) | `Strict-Transport-Security` header present | | | |
| 9.6 | Internal stack traces not exposed in error responses | Error messages are user-safe | | | |
| 9.7 | Path traversal rejected on upload filename | `../` sequences rejected | | | |
| 9.8 | JWT secret not hardcoded — loaded from `.env` | Confirmed via code review | | | |
| 9.9 | `.env` file not committed to git | Absent from `git log` | | | |
| 9.10 | CORS allows only configured origins | Requests from unknown origin rejected | | | |

---

## 10. HTTPS (Production Only)

| # | Test | Expected Result | Status | Notes | Date Verified |
|---|------|-----------------|--------|-------|---------------|
| 10.1 | `https://highlightai.in` loads | HTTP/2 200 | | | |
| 10.2 | `http://highlightai.in` redirects to HTTPS | HTTP 301 redirect | | | |
| 10.3 | `https://www.highlightai.in` redirects to apex | HTTP 301 redirect | | | |
| 10.4 | `https://api.highlightai.in/health` returns 200 | HTTP/2 200 | | | |
| 10.5 | SSL certificate valid | No browser warnings | | | |
| 10.6 | SSL Labs grade A or A+ | Verify at ssllabs.com | | | |
| 10.7 | Browser padlock visible | No mixed-content warnings | | | |
| 10.8 | Direct access to port 3000 blocked | Connection refused | | | |
| 10.9 | Direct access to port 8000 blocked | Connection refused | | | |

---

## 11. Observability

| # | Test | Expected Result | Status | Notes | Date Verified |
|---|------|-----------------|--------|-------|---------------|
| 11.1 | `GET /health` returns 200 | `{"status": "ok"}` or similar | | | |
| 11.2 | `GET /ready` returns 200 when DB is connected | Ready response | | | |
| 11.3 | `GET /metrics` returns runtime metrics | Metrics payload | | | |
| 11.4 | `X-Request-ID` present in every response | UUID in response header | | | |
| 11.5 | Logs written to `backend/logs/agc.log` | Log file populated during requests | | | |
| 11.6 | Log entries include timestamp and level | Structured log format | | | |

---

## 12. Regression

| # | Test | Expected Result | Status | Notes | Date Verified |
|---|------|-----------------|--------|-------|---------------|
| 12.1 | `GET /` returns welcome message | 200 with message | | | |
| 12.2 | `GET /version` returns version | 200 with version info | | | |
| 12.3 | `GET /docs` loads Swagger UI | 200, interactive docs render | | | |
| 12.4 | Full end-to-end: upload → pipeline → history | Highlights available in history | | | |
| 12.5 | Frontend login page loads | Page renders without errors | | | |
| 12.6 | Frontend register page loads | Page renders without errors | | | |
| 12.7 | Frontend to backend communication works | No CORS errors in browser console | | | |

---

## 13. Performance

| # | Test | Expected Result | Status | Notes | Date Verified |
|---|------|-----------------|--------|-------|---------------|
| 13.1 | Upload 100 MB video | Completes in < 30 seconds on local network | | | |
| 13.2 | Pipeline on 10-minute video | Completes within reasonable time (< 15 min) | | | |
| 13.3 | API response time for non-pipeline endpoints | < 200ms under normal load | | | |
| 13.4 | Two concurrent pipelines | Both complete without errors | | | |
| 13.5 | Disk usage after job cleanup | Temp files removed, only highlights retained | | | |

---

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Developer | | | |
| Tester | | | |
| Product Owner | | | |
