# AGC Production Deployment Guide

Target: single Ubuntu 22.04 VPS at `45.94.209.92`
Domain: `vedzovi.com` (frontend) · `api.vedzovi.com` (backend API)

---

## 0 — Server Prerequisites

Install system packages on the VPS before any application setup:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git ffmpeg
```

Install Node.js 18+ via NodeSource:

```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

Verify:

```bash
python3 --version    # 3.10+
node --version       # 18+
ffmpeg -version
ffprobe -version
```

---

## 1 — DNS

Add the following A records in your DNS provider (TTL 300):

| Record | Type | Value |
|--------|------|-------|
| `vedzovi.com` | A | `45.94.209.92` |
| `www.vedzovi.com` | A | `45.94.209.92` |
| `api.vedzovi.com` | A | `45.94.209.92` |

Verify propagation before proceeding:

```bash
dig +short vedzovi.com
dig +short api.vedzovi.com
```

Both must return `45.94.209.92`.

---

## 2 — Firewall

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (Let's Encrypt + redirect)
sudo ufw allow 443/tcp   # HTTPS
sudo ufw deny 3000/tcp   # block direct frontend access
sudo ufw deny 8000/tcp   # block direct backend access
sudo ufw enable
sudo ufw status
```

Ports 3000 and 8000 must **not** be publicly reachable — all traffic flows through nginx.

---

## 3 — Nginx Installation

```bash
sudo apt update && sudo apt install -y nginx
sudo systemctl enable nginx
```

Deploy the config:

```bash
sudo cp nginx/agc.conf /etc/nginx/sites-available/agc
sudo ln -sf /etc/nginx/sites-available/agc /etc/nginx/sites-enabled/agc
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t          # must print: syntax is ok / test is successful
```

---

## 4 — SSL with Let's Encrypt

```bash
sudo apt install -y certbot python3-certbot-nginx

# Issue cert for all three names in one certificate
sudo certbot --nginx \
  -d vedzovi.com \
  -d www.vedzovi.com \
  -d api.vedzovi.com \
  --agree-tos \
  --email admin@vedzovi.com \
  --no-eff-email
```

Certbot will edit the nginx config to point to the new cert paths and reload nginx automatically.

Verify the cert:

```bash
sudo nginx -t && sudo systemctl reload nginx
curl -Is https://vedzovi.com | head -5
# Expect: HTTP/2 200
```

---

## 5 — SSL Auto-Renewal

Let's Encrypt certs expire every 90 days. Certbot installs a systemd timer automatically:

```bash
sudo systemctl status certbot.timer   # should show: active (waiting)
```

Test renewal without issuing:

```bash
sudo certbot renew --dry-run
```

Certbot reloads nginx automatically post-renewal. No cron job needed.

---

## 6 — Backend Deployment

### Environment variables (`backend/.env`)

```dotenv
ENVIRONMENT=production
HTTPS_ENABLED=true

JWT_SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
JWT_ALGORITHM=HS256
JWT_EXPIRY_HOURS=24
# Required when ENVIRONMENT=production — the backend now refuses to start
# without it (a missing key would otherwise fall back to a random per-process
# secret, invalidating every session on each restart).

FRONTEND_URL=https://vedzovi.com
PRODUCTION_URL=https://vedzovi.com
WWW_PRODUCTION_URL=https://www.vedzovi.com
```

### Create the virtual environment and install dependencies

```bash
cd /path/to/AGC_AI_Highlight_Creator/backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Start the backend

```bash
cd /path/to/AGC_AI_Highlight_Creator/backend
source venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

For production, run under `systemd` or `supervisor` so it survives reboots.

Startup log should show:

```
✅ SQLite Database Initialized
✅ Startup Validation Completed
```

If you see the `⚠️ WARNING` line, `HTTPS_ENABLED=true` is missing from `.env`.

---

## 7 — Frontend Deployment

### Environment variables (`frontend/.env.local` on the server)

```dotenv
NEXT_PUBLIC_API_URL=https://api.vedzovi.com
```

This is the only value that must change between dev and production. No other API URL is hardcoded in the frontend code.

### Build and start

```bash
cd /path/to/AGC_AI_Highlight_Creator/frontend
npm install
npm run build
npm start -- --port 3000
```

Run under `systemd` or `pm2` for persistence.

---

## 8 — Health Verification Checklist

Run these after every deployment or cert renewal:

- [ ] `curl -Is https://vedzovi.com | head -1` → `HTTP/2 200`
- [ ] `curl -Is https://www.vedzovi.com | head -1` → `HTTP/2 301` (redirects to apex)
- [ ] `curl -Is https://api.vedzovi.com/health` → `HTTP/2 200`
- [ ] `curl -Is http://vedzovi.com | head -1` → `HTTP/1.1 301` (redirects to HTTPS)
- [ ] `curl -Is http://api.vedzovi.com | head -1` → `HTTP/1.1 301`
- [ ] Browser: open `https://vedzovi.com` — padlock visible, no mixed-content warnings
- [ ] Browser: login and upload a video — pipeline runs to completion
- [ ] Response headers include `Strict-Transport-Security` (check DevTools → Network → response headers)
- [ ] Response headers include `X-Content-Type-Options: nosniff`
- [ ] SSL Labs grade: `curl https://www.ssllabs.com/ssltest/analyze.html?d=vedzovi.com` (or visit in browser) — aim for A or A+

---

## 9 — Safe Deployment (Maintenance Mode)

AGC-084 adds a file-based maintenance sentinel so planned deployments don't
land mid-request. `MaintenanceService` (`backend/app/services/maintenance_service.py`)
does a live, uncached check of `MAINTENANCE_FLAG_PATH` (default
`storage/maintenance.flag` under `backend/`) on every `/upload` and
`/pipeline/start` request. Toggle it over SSH with `scripts/maintenance.sh`
— there is no public toggle endpoint and no admin auth surface; the SSH
session is the operator trust boundary.

Every planned deployment must follow this exact sequence:

1. **Maintenance ON** — `bash scripts/maintenance.sh on`
2. **Confirm maintenance ON** through the public status endpoint —
   `curl -s https://api.vedzovi.com/maintenance-status` must return
   `{"maintenance": true}`
3. **Stable drain** — `bash scripts/maintenance.sh drain` (blocks until 0
   active jobs are observed on 3 consecutive checks; see below)
4. **Confirm drained** — the `drain` command only exits 0 once stable
5. **Pull / deploy code** — `git pull`, install dependencies, build frontend
6. **Restart backend** — `systemctl restart agc-backend` (or equivalent)
7. **Verify backend health/readiness** — `curl -Is https://api.vedzovi.com/health`
   and `/ready` both return `200`
8. **Restart frontend** — `systemctl restart agc-frontend` (or equivalent)
9. **Verify frontend** — `curl -Is https://vedzovi.com` returns `200`
10. **Keep maintenance ON during all validation above** — do not turn it
    off until health/readiness and the frontend are confirmed working
11. **Maintenance OFF** — `bash scripts/maintenance.sh off`
12. **Confirm maintenance OFF** — `/maintenance-status` returns
    `{"maintenance": false}`
13. **Verify new upload/pipeline processing is available** — upload and run
    a short test video end-to-end

### The drain race — documented, not eliminated

Turning maintenance ON and then checking that active jobs == 0 once is
**not** sufficient proof of a stable drain: a `/pipeline/start` request can
read maintenance OFF immediately before the flag is created, then still
reach `JobService.create_job()` after maintenance turns ON. `drain` does
not make this race mathematically impossible — it mitigates it
operationally by waiting a ~3s grace period, then polling the real
`jobs` table (`status IN ('pending', 'processing')`) and requiring 0 for 3
consecutive checks, ~2s apart, resetting the counter if a nonzero count
reappears. This bounds the race window; it does not close it. `drain`
never kills jobs, modifies job rows, marks jobs failed, or refunds
credits — that is unplanned-interruption recovery and is **AGC-085
scope**, not AGC-084's. AGC-084 protects planned deployments only.

### Operational notes

- The maintenance flag is a plain file — its state survives backend
  restarts. **Forgetting step 11 (maintenance OFF) leaves new uploads and
  pipeline starts paused indefinitely** even after a successful deploy.
- Existing uploaded files, history, projects, results, and file downloads
  are never affected by maintenance mode — only new `/upload` and
  `/pipeline/start` requests are blocked (`503 MAINTENANCE_MODE`).
- The frontend dashboard polls `/maintenance-status` every ~5s and shows a
  calm banner while ON; it fails open (does not force `maintenance=true`)
  if that poll itself fails, so a transient status-endpoint hiccup never
  blocks access to history/results. The backend's `503 MAINTENANCE_MODE`
  response remains the authoritative enforcement path regardless of what
  the frontend has polled.

---

## 10 — Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| `502 Bad Gateway` on API | Backend not running on port 8000 | `systemctl status agc-backend` |
| Mixed-content warning | `NEXT_PUBLIC_API_URL` still set to `http://` | Update `frontend/.env.local` to `https://api.vedzovi.com` and rebuild |
| Cert not found | DNS not propagated when certbot ran | Re-run `certbot --nginx -d ...` after DNS propagates |
| Upload fails with `413` | `client_max_body_size` too low | Already set to `500m` in `nginx/agc.conf` |
| CORS errors in browser | `PRODUCTION_URL` not set in backend `.env` | Add `PRODUCTION_URL=https://vedzovi.com` to `backend/.env` |
