# AGC-072 — Recovery Checklist

Print or copy this file and tick off each step during an actual recovery.
Cross-references point to the doc with full detail for that step.

## Setup (VPS lost — full rebuild)

- [ ] **1. Provision fresh Ubuntu VPS** — [VPS_REBUILD.md §1](VPS_REBUILD.md#1--provision-a-fresh-ubuntu-vps)
- [ ] **2. Install dependencies** (python3, ffmpeg, node, nginx, certbot, ufw) — [VPS_REBUILD.md §2](VPS_REBUILD.md#2--install-dependencies)
- [ ] **3. Clone repository** to `/home/agc/agc-ai-highlight-creator` — [VPS_REBUILD.md §3](VPS_REBUILD.md#3--clone-the-repository)
- [ ] **4. Create Python virtual environment** at repo root, install `backend/requirements.txt` — [VPS_REBUILD.md §4](VPS_REBUILD.md#4--create-the-python-virtual-environment)

## Restore (VPS lost, or corrupted in place)

- [ ] **5. Restore `.env`** — `backend/.env` — [RESTORE_GUIDE.md](RESTORE_GUIDE.md)
- [ ] **6. Restore SQLite database** — `backend/data/agc.db` — [RESTORE_GUIDE.md](RESTORE_GUIDE.md)
- [ ] **7. Restore uploads** — `backend/storage/uploads/` — [RESTORE_GUIDE.md](RESTORE_GUIDE.md)
- [ ] **8. Restore generated highlights** — `backend/storage/highlights/` — [RESTORE_GUIDE.md](RESTORE_GUIDE.md)
- [ ] **9. Restore nginx configuration** — `/etc/nginx/sites-available/agc` — [RESTORE_GUIDE.md](RESTORE_GUIDE.md)
- [ ] **10. Restore systemd service files** — `/etc/systemd/system/agc-*.service` — [RESTORE_GUIDE.md](RESTORE_GUIDE.md)
- [ ] **11. Restore SSL certificates** — `/etc/letsencrypt/` — [RESTORE_GUIDE.md](RESTORE_GUIDE.md)

  ```bash
  sudo bash scripts/restore.sh /path/to/backup/<timestamp>
  ```

- [ ] **12. Restart services** — nginx + `agc-backend` (+ frontend process)

  ```bash
  sudo nginx -t && sudo systemctl reload nginx
  sudo systemctl restart agc-backend
  ```

## Verify

- [ ] **13. Verify backend**

  ```bash
  systemctl is-active agc-backend
  curl -sf https://api.vedzovi.com/health
  ```

  Expect `active` and an HTTP 200 with a healthy JSON body.

- [ ] **14. Verify frontend**

  ```bash
  curl -Is https://vedzovi.com | head -1     # expect HTTP/2 200
  curl -Is https://www.vedzovi.com | head -1 # expect HTTP/2 301 (redirect to apex)
  ```

  Then open `https://vedzovi.com` in a browser — padlock visible, no
  mixed-content warnings, homepage renders.

- [ ] **15. Verify login**

  In the browser: log in with a known existing test account (created
  before the disaster). Confirm the dashboard loads and the session
  persists across a page refresh.

- [ ] **16. Verify upload**

  Upload a short test video through the UI. Confirm it appears with a
  valid `location` and no `413`/`500` errors.

- [ ] **17. Verify pipeline**

  Start processing on the uploaded test video and poll until it
  completes:

  ```bash
  curl -sf https://api.vedzovi.com/pipeline/job/<job_id> -H "Authorization: Bearer <token>"
  ```

  Confirm `status` reaches `completed` and at least one highlight clip is
  produced.

- [ ] **18. Verify Razorpay**

  Confirm `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` were restored in
  `backend/.env`. Trigger a test order-creation call (or use Razorpay's
  test mode) and confirm the checkout flow opens without a
  configuration error.

- [ ] **19. Verify subscriptions**

  Confirm an existing subscribed test account still shows the correct
  plan/expiry after restore (proves the database restore preserved
  subscription state).

- [ ] **20. Verify downloads**

  Download a previously generated highlight clip (from before the
  disaster, restored via `highlights.tar.gz`) and a newly generated one
  from step 17. Confirm both play correctly.

## If any step fails

- Steps 5–11 fail → re-check [RESTORE_GUIDE.md](RESTORE_GUIDE.md)
  troubleshooting table.
- Steps 13–20 fail → check `journalctl -u agc-backend -n 100` and
  `sudo nginx -t`, then consult [deploy.md §9](deploy.md#9--common-issues).
- Nothing here recovers the situation → see
  [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md) for scenario-specific
  guidance.
