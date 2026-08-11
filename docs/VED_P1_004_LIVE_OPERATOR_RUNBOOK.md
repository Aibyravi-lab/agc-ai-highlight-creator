# VED-P1-004 — Live Operator Runbook

**Unblock large (1-2GB) customer uploads by routing them around Cloudflare's
Free-plan 100MB proxied-body cap, via a new DNS-only `upload.vedzovi.com`
hostname.**

This runbook is for a human operator (or an agent with real SSH/Cloudflare
access) to execute on the actual production system. It was not executed by
Claude — the session that produced it had no working SSH key for `agc-vps`
and no Cloudflare API credentials, so every command below is unexecuted and
unverified against live state. Repo-side prerequisites (nginx config,
frontend/backend code, docs) are already committed at `a0feb27` on `main`,
not pushed.

Every command is labeled:
- **[LOCAL REPO]** — run from a checkout of this repo (already done, shown for reference)
- **[VPS]** — run over SSH on `agc-vps` (`agc@45.94.209.92`)
- **[CLOUDFLARE DASHBOARD]** — done in the Cloudflare web UI or via Cloudflare API/CLI, not on the VPS

Stop and do not proceed to the next section if any check in the current
section fails. §M (Rollback) tells you how to back out from any point.

---

## A. Pre-change: record current state

**[VPS]**
```bash
ssh agc-vps
cd /home/agc/agc-ai-highlight-creator
git status
git rev-parse HEAD
git log -1 --oneline
```
Record the output. This is what you roll back to in §M if anything fails.

**[VPS]** Confirm what's actually running (not just what's checked out):
```bash
curl -s https://api.vedzovi.com/health | python3 -m json.tool
```
Record `build.git_commit` (or equivalent field) from the response.

**[VPS]** Backup/recovery check — confirm the existing disaster-recovery
tooling is functional before touching anything (per `scripts/backup.sh`,
`docs/DISASTER_RECOVERY.md`):
```bash
bash scripts/backup.sh --dry-run 2>&1 | tail -20   # or the real backup flag if no dry-run mode exists — check the script first
ls -la /path/to/backup/destination | tail -5        # confirm a recent backup exists and is non-empty
```
If `scripts/backup.sh` has no dry-run mode, run a real backup now and
confirm it completes and produces a non-empty artifact before proceeding.

**[VPS]** Confirm no active jobs would be disrupted by entering maintenance
(informational only at this point — §B does the actual drain):
```bash
sqlite3 backend/data/agc.db "SELECT status, COUNT(*) FROM jobs WHERE status IN ('pending','processing') GROUP BY status;"
```

**[VPS]** Record current Nginx config:
```bash
sudo nginx -T > ~/agc-nginx-backup-$(date +%Y%m%d-%H%M%S).conf
cat /etc/nginx/sites-enabled/agc   # should match repo's nginx/agc.conf pre-VED-P1-004
```

**[CLOUDFLARE DASHBOARD]** Record current DNS state for the zone
`vedzovi.com`: list all records, note proxy status (orange/grey cloud) for
`vedzovi.com`, `www.vedzovi.com`, `api.vedzovi.com`. Screenshot or export
(DNS → Overview → Export DNS records) before making changes.

**[VPS]** Record current frontend/backend env values relevant to this change:
```bash
grep -E "^(FRONTEND_URL|PRODUCTION_URL|WWW_PRODUCTION_URL|MAX_UPLOAD_SIZE_MB)=" backend/.env
grep -E "^NEXT_PUBLIC_(API_URL|UPLOAD_API_URL)=" frontend/.env.local
```
Record these exact values — §M restores them verbatim.

---

## B. Enter maintenance mode

**[VPS]**
```bash
cd /home/agc/agc-ai-highlight-creator
bash scripts/maintenance.sh on
bash scripts/maintenance.sh status   # confirm ON
```

**[VPS]** Drain — wait for active jobs to finish, do not kill anything:
```bash
bash scripts/maintenance.sh drain
```
This blocks until 3 consecutive zero-active-job readings, per the script's
documented drain-race mitigation. Let it finish naturally; do not Ctrl-C and
force through.

**[VPS]** Re-confirm zero active jobs before proceeding:
```bash
sqlite3 backend/data/agc.db "SELECT COUNT(*) FROM jobs WHERE status IN ('pending','processing');"
```
Must be `0`.

---

## C. Verify backup/recovery is current

**[VPS]** If §A's backup was more than a few minutes old by now, take a
fresh one — the system is idle (drained) so this is a good, safe point:
```bash
bash scripts/backup.sh
```
Confirm success output and a new artifact in the backup destination.

---

## D. DNS: create the upload hostname

**[CLOUDFLARE DASHBOARD]**
1. DNS → Add record
2. Type: `A`
3. Name: `upload`
4. IPv4 address: `45.94.209.92`
5. **Proxy status: DNS only (grey cloud)** — this is the entire point of
   the change. Do not leave it proxied (orange cloud).
6. TTL: Auto (or 300s to match the existing records)
7. Save

**[VPS]** Verify propagation before continuing:
```bash
dig +short upload.vedzovi.com
```
Must return `45.94.209.92`. If it doesn't resolve yet, wait and retry —
don't proceed to cert issuance until it does (HTTP-01 challenge will fail).

**[VPS]** Confirm it's actually not going through Cloudflare's proxy (a
proxied record would resolve to a Cloudflare IP, not the origin):
```bash
dig +short vedzovi.com        # compare — this SHOULD show Cloudflare IPs (proxied)
dig +short upload.vedzovi.com # this SHOULD show 45.94.209.92 directly (DNS-only)
```

---

## E. Certificate: expand to cover upload.vedzovi.com

**[VPS]**
```bash
sudo certbot certonly --nginx \
  -d vedzovi.com \
  -d www.vedzovi.com \
  -d api.vedzovi.com \
  -d upload.vedzovi.com \
  --expand
```

**[VPS]** Verify the new cert covers all four names:
```bash
sudo openssl x509 -in /etc/letsencrypt/live/vedzovi.com/fullchain.pem -noout -text | grep -A2 "Subject Alternative Name"
```
Must list all four hostnames.

---

## F. Deploy Nginx config

**[LOCAL REPO → VPS]** Get the updated `nginx/agc.conf` (commit `a0feb27`)
onto the VPS via your normal deploy path (git pull, scp, rsync — whatever
this project's existing deploy process uses; not prescribed here since no
CD pipeline was found in the repo).

**[VPS]**
```bash
cd /home/agc/agc-ai-highlight-creator
git fetch origin
git log origin/main -1 --oneline   # confirm a0feb27 (or later) is available
git pull origin main               # only if this VPS deploys via git pull — verify against actual deploy process first
sudo cp nginx/agc.conf /etc/nginx/sites-available/agc
sudo nginx -t
```
`nginx -t` **must** print `syntax is ok` / `test is successful` before you
reload. If it fails, stop — do not reload with a broken config. Go to §M.

**[VPS]** Only after `nginx -t` passes:
```bash
sudo systemctl reload nginx
```

---

## G. Deploy backend + frontend config

**[VPS]** Backend — add/update in `backend/.env`:
```bash
# edit backend/.env, set:
MAX_UPLOAD_SIZE_MB=2000
```
Do **not** touch `FRONTEND_URL`, `PRODUCTION_URL`, or `WWW_PRODUCTION_URL` —
§I confirms `https://vedzovi.com` is already present; this deploy makes no
CORS change.

Restart the backend service so the new env value takes effect:
```bash
sudo systemctl restart agc-backend   # actual service/unit name may differ — check with: systemctl list-units | grep -i agc
```

**[VPS]** Frontend — add/update in `frontend/.env.local`:
```bash
NEXT_PUBLIC_UPLOAD_API_URL=https://upload.vedzovi.com
```
Rebuild and restart (Next.js inlines `NEXT_PUBLIC_*` at build time — a
restart alone is not sufficient):
```bash
cd /home/agc/agc-ai-highlight-creator/frontend
npm run build
sudo systemctl restart agc-frontend   # actual service/unit name may differ
```

---

## H. Validate before exiting maintenance

Run every check below. All must pass before §K (exit maintenance).

**[VPS]**
```bash
sudo nginx -t
```

**[VPS]** HTTPS certificate validation:
```bash
curl -Isv https://upload.vedzovi.com/upload/ 2>&1 | grep -E "SSL certificate|subject:|expire"
```

**[VPS]** DNS resolution:
```bash
dig +short upload.vedzovi.com   # → 45.94.209.92
```

**[VPS]** Upload hostname reachability:
```bash
curl -Is https://upload.vedzovi.com/upload/
# Expect a 401/403 (auth required), NOT a connection error or 5xx
```

**[VPS]** Authentication still required (no auth bypass introduced):
```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST https://upload.vedzovi.com/upload/
# Expect 401 or 403 — not 200, not 400 from a missing-file error before auth is checked
```

**[VPS]** Non-upload routes on the upload hostname return 404 (confirms
only `/upload/` is exposed):
```bash
curl -s -o /dev/null -w "%{http_code}\n" https://upload.vedzovi.com/health
curl -s -o /dev/null -w "%{http_code}\n" https://upload.vedzovi.com/pipeline/jobs
curl -s -o /dev/null -w "%{http_code}\n" https://upload.vedzovi.com/
# All three must be 404
```

**[VPS]** Existing `api.vedzovi.com` still works, unaffected:
```bash
curl -Is https://api.vedzovi.com/health   # 200
```

**[VPS]** `vedzovi.com` still works:
```bash
curl -Is https://vedzovi.com   # 200
```

**[VPS]** Confirm no secrets exposed in the new server block's responses
(headers, error bodies):
```bash
curl -Isv https://upload.vedzovi.com/upload/ 2>&1 | grep -iE "x-powered-by|server:|traceback"
# Should show only the standard headers already present on api.vedzovi.com — nothing new
```

**[VPS]** Confirm the upload URL is actually what the built frontend uses:
```bash
grep -r "upload.vedzovi.com" /home/agc/agc-ai-highlight-creator/frontend/.next/ 2>/dev/null | head -3
```
Should find at least one match in the built output — confirms
`NEXT_PUBLIC_UPLOAD_API_URL` was actually inlined at build time.

**[LOCAL REPO]** (already done, for reference — re-run on the VPS checkout
if you want to re-verify at this exact deploy point):
```bash
cd backend && venv/Scripts/python.exe -m pytest tests/ -q   # 312 passed, 1 skipped, verified pre-deploy
cd frontend && npx tsc --noEmit && npm run build             # clean, verified pre-deploy
```

If **any** check in this section fails, do not proceed to §I. Go to §M.

---

## I. CORS verification (no change expected)

**[VPS]** Confirm `https://vedzovi.com` — the actual browser `Origin` on an
upload request — is present in the live backend's CORS allow-list:
```bash
grep -E "^PRODUCTION_URL=" backend/.env
# If unset, the code default (backend/app/config/config.py) is
# https://vedzovi.com — confirm that default is what's actually running:
curl -s -H "Origin: https://vedzovi.com" -H "Access-Control-Request-Method: POST" \
  -X OPTIONS https://api.vedzovi.com/upload/ -i | grep -i "access-control-allow-origin"
```
Expect `access-control-allow-origin: https://vedzovi.com` in the response.

**If and only if** this check fails (i.e., `https://vedzovi.com` is
missing), add `PRODUCTION_URL=https://vedzovi.com` to `backend/.env` and
restart the backend. **Do not** add `https://upload.vedzovi.com` to CORS
under any circumstance — it is never a browser `Origin`, only a `fetch()`
target.

---

## J. Real end-to-end test

Use the existing 1.58 GiB / 21.9-minute gameplay file already on hand from
the customer-#0 investigation.

**[VPS or operator machine with the file]**
```bash
# 1. Authenticate, capture the JWT
TOKEN=$(curl -s -X POST https://api.vedzovi.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"<test-account-email>","password":"<test-account-password>"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")

# 2. Upload via the new hostname, timing it
time curl -X POST https://upload.vedzovi.com/upload/ \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/customer-0-gameplay.mkv" \
  -o upload_response.json -w "\nHTTP %{http_code}\n"
cat upload_response.json | python3 -m json.tool
```
Record wall-clock upload duration and the returned `video_path`/job
reference. Confirm HTTP 200/201 and no 413.

```bash
# 3. Start the pipeline
JOB=$(curl -s -X POST "https://api.vedzovi.com/pipeline/start?video_path=<video_path_from_step_2>" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['job_id'])")

# 4. Poll until completion
while true; do
  STATUS=$(curl -s "https://api.vedzovi.com/pipeline/job/$JOB" -H "Authorization: Bearer $TOKEN" \
    | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['status'])")
  echo "$(date '+%H:%M:%S') $STATUS"
  [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ] && break
  sleep 15
done
```
Record total processing duration.

```bash
# 5. Verify + download the highlight
curl -s "https://api.vedzovi.com/pipeline/job/$JOB" -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
# Extract final_reel path from the result, then:
curl -s "https://api.vedzovi.com/files/<final_reel_path>" -H "Authorization: Bearer $TOKEN" -o downloaded_highlight.mp4

# 6. ffprobe the downloaded file
ffprobe -v error -show_format -show_streams downloaded_highlight.mp4
```
Confirm the file is a valid, playable video with non-zero duration.

**[VPS]** Inspect logs for errors during the whole E2E run:
```bash
journalctl -u agc-backend --since "-30 minutes" | grep -iE "error|traceback|exception"
tail -100 /var/log/nginx/error.log
```
Both should be clean (or show only pre-existing, unrelated noise).

If the E2E fails at any step, do not exit maintenance — go to §M.

---

## K. Monitor

**[VPS]**
```bash
curl -s https://api.vedzovi.com/api/v1/ops/production-health -H "X-Ops-Key: <ops_api_key>" | python3 -m json.tool
```
Confirm overall health score is nominal (matches pre-change baseline from
§A, no new alerts).

```bash
curl -Is https://upload.vedzovi.com/upload/    # still reachable
curl -Is https://api.vedzovi.com/health        # still 200
```

```bash
sqlite3 backend/data/agc.db "SELECT status, COUNT(*) FROM jobs WHERE created_at > datetime('now','-1 hour') GROUP BY status;"
```
Confirm no unexpected failure spike versus normal baseline.

---

## L. Exit maintenance mode

**[VPS]** Only after §H, §I, §J, and §K are all clean:
```bash
bash scripts/maintenance.sh off
bash scripts/maintenance.sh status   # confirm OFF
```

**[VPS]** Final confirmation of normal operation:
```bash
curl -s https://api.vedzovi.com/maintenance-status
# {"maintenance": false}
```

---

## M. Rollback (if any validation step fails)

**[VPS]** Restore frontend/backend config to the values recorded in §A:
```bash
# backend/.env — restore FRONTEND_URL/PRODUCTION_URL/WWW_PRODUCTION_URL/MAX_UPLOAD_SIZE_MB to §A values
sudo systemctl restart agc-backend

# frontend/.env.local — remove or restore NEXT_PUBLIC_UPLOAD_API_URL to §A value
cd frontend && npm run build
sudo systemctl restart agc-frontend
```

**[CLOUDFLARE DASHBOARD]** Remove the `upload.vedzovi.com` DNS record if
it was the source of the failure (e.g., misconfigured, or you want to fully
back out the change rather than fix forward):
DNS → find the `upload` A record → Delete.

**[VPS]** Restore Nginx:
```bash
cd /home/agc/agc-ai-highlight-creator
git checkout <pre-change-commit-from-§A> -- nginx/agc.conf
sudo cp nginx/agc.conf /etc/nginx/sites-available/agc
sudo nginx -t
```
Must pass before reloading.
```bash
sudo systemctl reload nginx
```

**[VPS]** Validate rollback:
```bash
curl -Is https://api.vedzovi.com/health    # 200
curl -Is https://vedzovi.com               # 200
curl -Is https://upload.vedzovi.com        # should fail/timeout once DNS record is removed and propagated
```

**[VPS]** Exit maintenance only after rollback validation is clean:
```bash
bash scripts/maintenance.sh off
bash scripts/maintenance.sh status
```

---

## Explicitly out of scope for this change

Per the approved plan, none of the following should happen as part of this
deploy:
- Any fix or refactor unrelated to the upload path
- Changing the Cloudflare plan/tier
- Introducing R2/S3 or chunked/resumable uploads
- Any change to `api.vedzovi.com` routing
- Any database schema change
- Adding `https://upload.vedzovi.com` to backend CORS `allow_origins`
