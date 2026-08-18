# VED-P1-018 — Self-Recovery Watchdog

External, out-of-process reachability watchdog for Vedzovi's `agc-backend.service`
and `agc-frontend.service`. Runs every minute as a systemd timer, restarts a
service only after a deterministic policy is satisfied, and never touches
anything outside that narrow scope.

---

## 1 — Why this exists

`HealthSchedulerService` (VED-P1-002) already evaluates detailed application
health — but it runs **inside** the backend process. If the backend process
itself is wedged or down, that scheduler is down with it and cannot recover
anything. `agc-backend.service` already has `Restart=always` in systemd,
which handles a crashed *process*, but not a process that is still running
while wedged (hung event loop, deadlocked worker, etc.) and returning no
response or a non-200 `/health`.

This watchdog is a small, independent systemd timer + shell script that can
observe and restart both services from outside the backend process
entirely.

---

## 2 — Architecture

```
systemd timer (every 1 min)
        │
        ▼
vedzovi-self-recovery.service (oneshot, User=agc)
        │
        ▼
scripts/self_recovery_watchdog.sh
        │
        ├─ mkdir-based lock (STATE_DIR/watchdog.lock.d) — no overlap
        ├─ maintenance sentinel check (same file scripts/maintenance.sh uses)
        ├─ curl https://api.vedzovi.com/health   (timeout HEALTH_TIMEOUT_SECONDS)
        ├─ curl https://vedzovi.com/              (timeout HEALTH_TIMEOUT_SECONDS)
        ├─ state file: STATE_DIR/state.env (consecutive failures, last
        │   recovery timestamp, last result, last action)
        ├─ STATE_DIR/{backend,frontend}_recovery_attempts.log (rolling-hour
        │   attempt history, used for the hourly cap)
        ├─ sudo systemctl restart agc-{backend,frontend}.service
        │   (scoped sudoers rule, or bare systemctl if already root)
        └─ backend/scripts/record_recovery_alert.py (best-effort bridge
            into the existing monitoring_alerts table via
            AlertEngineService.record_alert/resolve_alert)
```

Nothing here duplicates `HealthEngineService`/`AlertEngineService`
(VED-P1-002). This watchdog knows exactly two facts — "is backend
reachable" and "is frontend reachable" — and one action — "restart the
unit". Everything else (disk, memory, CPU, SQLite integrity, payments,
email, AI pipeline failure rate, backups) stays owned by `HealthEngineService`
and is alert-only, as designed.

---

## 3 — Recovery policy

**AUTO-RECOVER ONLY:**

| # | Condition | Action |
|---|-----------|--------|
| A | Backend unavailable (connection failure/timeout) | Restart `agc-backend.service` |
| B | Backend `/health` returns HTTP non-200 | Restart `agc-backend.service` |
| C | Frontend unavailable | Restart `agc-frontend.service` |

**Never auto-recovered (alert-only, handled by HealthEngineService/AlertEngineService):**

- SQLite integrity failures
- Disk failures / critically low disk
- FFmpeg failures
- Payment failures
- Email failures
- CPU / memory warnings
- AI pipeline failure rate
- Backup failures

**Why:** restarting a service cannot safely fix a data-integrity, storage,
payment, or pipeline problem — it can only mask or worsen it. The watchdog
script has no code path that even reads those signals (enforced by
`scripts/tests/test_self_recovery_watchdog.sh`'s "out of scope" test).

### Loop prevention

1. **3 consecutive failed checks** required before any restart is even
   considered (`RECOVERY_FAILURE_THRESHOLD`, default 3) — one transient
   network blip never triggers a restart.
2. **Fresh re-check immediately before restarting** — if the service
   recovered on its own between the threshold-crossing check and now, no
   restart happens (logged as `<service>_recovered_before_restart`).
3. **15-minute cooldown** between restarts of the same service
   (`RECOVERY_COOLDOWN_SECONDS`, default 900).
4. **Max 2 automatic recoveries per service per rolling hour**
   (`RECOVERY_MAX_ATTEMPTS_PER_HOUR`, default 2) — tracked via a rolling
   timestamp log, not a fixed clock-hour window. Once exceeded, the
   watchdog logs `SELF_RECOVERY_LIMIT_REACHED` (a CRITICAL
   recovery-exhausted event) and opens a `monitoring_alerts` row instead of
   restarting again.

### Maintenance safety

Before anything else, the script checks the exact same file-based sentinel
`scripts/maintenance.sh` uses (`MAINTENANCE_FLAG_PATH`, default
`backend/storage/maintenance.flag`). If present, the script logs
`SELF_RECOVERY_SKIPPED_MAINTENANCE` and exits immediately — it never fights
an intentional maintenance operation.

---

## 4 — Configuration

All of the following are environment variables the script reads with
sane production defaults; override via `Environment=` lines in
`systemd/vedzovi-self-recovery.service` or an `EnvironmentFile=` if you
need per-host overrides.

| Variable | Default | Meaning |
|---|---|---|
| `RECOVERY_FAILURE_THRESHOLD` | `3` | Consecutive failed checks before a restart is considered |
| `RECOVERY_COOLDOWN_SECONDS` | `900` | Minimum time between restarts of the same service |
| `RECOVERY_MAX_ATTEMPTS_PER_HOUR` | `2` | Max restarts per service per rolling hour |
| `HEALTH_TIMEOUT_SECONDS` | `10` | curl timeout for each reachability check |
| `VERIFY_WAIT_SECONDS` | `10` | Wait after a restart before re-checking health |
| `BACKEND_HEALTH_URL` | `https://api.vedzovi.com/health` | Backend check target |
| `FRONTEND_URL` | `https://vedzovi.com/` | Frontend check target |
| `BACKEND_SERVICE_UNIT` | `agc-backend.service` | Unit restarted for condition A/B |
| `FRONTEND_SERVICE_UNIT` | `agc-frontend.service` | Unit restarted for condition C |
| `STATE_DIR` | `/var/lib/vedzovi-recovery` | Watchdog state (plain files, not SQLite) |
| `MAINTENANCE_FLAG_PATH` | `${BACKEND_DIR}/storage/maintenance.flag` | Same sentinel as `scripts/maintenance.sh` |
| `VENV_PYTHON` | `${APP_DIR}/venv/bin/python` | Used only for the best-effort alert bridge |

---

## 5 — Recovery state

Plain files under `STATE_DIR` (`/var/lib/vedzovi-recovery`), never SQLite:

- `state.env` — `KEY=VALUE` lines: `BACKEND_CONSEC_FAILURES`,
  `FRONTEND_CONSEC_FAILURES`, `BACKEND_LAST_RECOVERY_TS`,
  `FRONTEND_LAST_RECOVERY_TS`, `LAST_BACKEND_RESULT`, `LAST_FRONTEND_RESULT`,
  `LAST_ACTION`, `LAST_ACTION_RESULT`, `LAST_ACTION_TS`.
- `backend_recovery_attempts.log` / `frontend_recovery_attempts.log` — one
  epoch-second timestamp per line per restart attempt, pruned to the
  rolling hour on every run (this is what the hourly cap counts against).
- `watchdog.lock.d/` — an atomic `mkdir`-based lock directory (portable
  equivalent of `flock`, no `util-linux` dependency); present only while a
  run is in progress.

Inspect state manually at any time:

```bash
cat /var/lib/vedzovi-recovery/state.env
cat /var/lib/vedzovi-recovery/backend_recovery_attempts.log
```

---

## 6 — Privilege model

The watchdog runs as the unprivileged `agc` user (same as
`agc-backend.service`/`agc-frontend.service`), **not** root. The only
privileged operations it needs — restarting the two services, and reading
their `systemctl is-active` state as restart-failure evidence — are granted
through a narrowly scoped sudoers rule, not a root-owned systemd unit and
not blanket sudo:

```
agc ALL=(root) NOPASSWD: /bin/systemctl restart agc-backend.service
agc ALL=(root) NOPASSWD: /bin/systemctl restart agc-frontend.service
agc ALL=(root) NOPASSWD: /bin/systemctl is-active agc-backend.service
agc ALL=(root) NOPASSWD: /bin/systemctl is-active agc-frontend.service
```

See `systemd/vedzovi-self-recovery.sudoers` (versioned reference — install
it explicitly, see §7).

---

## 7 — Installation (run on the VPS)

```bash
# 1. Run the existing test suite (must stay green)
cd /home/agc/agc-ai-highlight-creator/backend
source venv/bin/activate
pytest

# 2. Run the new watchdog tests
cd /home/agc/agc-ai-highlight-creator
bash scripts/tests/test_self_recovery_watchdog.sh

# 3. Validate shell syntax
bash -n scripts/self_recovery_watchdog.sh
shellcheck scripts/self_recovery_watchdog.sh   # if shellcheck is installed

# 4. Validate the systemd unit files
sudo systemd-analyze verify systemd/vedzovi-self-recovery.service systemd/vedzovi-self-recovery.timer

# 5. Install the sudoers rule
sudo cp systemd/vedzovi-self-recovery.sudoers /etc/sudoers.d/vedzovi-self-recovery
sudo chmod 440 /etc/sudoers.d/vedzovi-self-recovery
sudo visudo -cf /etc/sudoers.d/vedzovi-self-recovery   # must print "parsed OK"

# 6. Install the systemd units
sudo cp systemd/vedzovi-self-recovery.service /etc/systemd/system/
sudo cp systemd/vedzovi-self-recovery.timer /etc/systemd/system/
sudo chmod +x scripts/self_recovery_watchdog.sh

# 7. Reload systemd
sudo systemctl daemon-reload

# 8. Enable and start the timer
sudo systemctl enable vedzovi-self-recovery.timer
sudo systemctl start vedzovi-self-recovery.timer

# 9. Verify the timer is active
systemctl status vedzovi-self-recovery.timer
systemctl list-timers vedzovi-self-recovery.timer

# 10. Run the watchdog manually once
sudo systemctl start vedzovi-self-recovery.service

# 11. Verify logs
journalctl -u vedzovi-self-recovery.service -n 50 --no-pager
# expect to see: SELF_RECOVERY_HEALTHY (assuming both services are healthy)

# 12. Verify production health remains healthy and maintenance stays OFF
curl -s https://api.vedzovi.com/health
bash scripts/maintenance.sh status   # must print "maintenance: OFF"
systemctl is-active agc-backend.service agc-frontend.service
```

Deployment must **not** toggle maintenance mode, modify payment code, or
change `HealthSchedulerService` behavior — this watchdog is purely additive.

---

## 8 — Manual watchdog execution

```bash
bash scripts/self_recovery_watchdog.sh
journalctl -u vedzovi-self-recovery.service -n 20 --no-pager
```

Safe to run manually at any time — it is idempotent and respects the same
lock/cooldown/hourly-cap rules as the timer-driven runs.

---

## 9 — Troubleshooting

| Symptom | Likely cause | Check |
|---|---|---|
| `SELF_RECOVERY_SKIPPED_LOCKED` every run | A previous run is stuck (e.g. `curl` hanging) | `ps aux \| grep self_recovery_watchdog`; if genuinely stale, `rmdir /var/lib/vedzovi-recovery/watchdog.lock.d` |
| `SELF_RECOVERY_SKIPPED_MAINTENANCE` when you didn't expect it | Maintenance flag left ON from a prior deploy | `bash scripts/maintenance.sh status` / `bash scripts/maintenance.sh off` |
| Restart attempted but `sudo: a password is required` | Sudoers rule not installed or path mismatch | Re-run §7 step 5; confirm `which systemctl` is `/bin/systemctl` |
| `SELF_RECOVERY_LIMIT_REACHED` repeating | Service is failing to stay up after restart — this is a real incident, not a watchdog bug | `journalctl -u agc-backend.service -n 200`; check the `monitoring_alerts` row the watchdog opened (`check_id = self_recovery_backend`) |
| `SELF_RECOVERY_ALERT_SKIPPED reason=python_unavailable` | Backend venv missing/relocated | Confirm `VENV_PYTHON` points at a real interpreter; this never blocks recovery, only the alert bridge |
| Timer not firing | Timer not enabled/started, or disabled by a prior rollback | `systemctl list-timers`; `sudo systemctl enable --now vedzovi-self-recovery.timer` |

---

## 10 — Rollback

The watchdog is fully additive — disabling it never touches
`agc-backend.service`, `agc-frontend.service`, or any existing monitoring:

```bash
sudo systemctl disable --now vedzovi-self-recovery.timer
sudo systemctl daemon-reload
```

To fully remove it:

```bash
sudo systemctl disable --now vedzovi-self-recovery.timer
sudo rm -f /etc/systemd/system/vedzovi-self-recovery.service
sudo rm -f /etc/systemd/system/vedzovi-self-recovery.timer
sudo rm -f /etc/sudoers.d/vedzovi-self-recovery
sudo systemctl daemon-reload
sudo rm -rf /var/lib/vedzovi-recovery
```

`agc-backend.service`/`agc-frontend.service` and their existing
`Restart=always` behavior are never modified by install or rollback.

---

## 11 — Disabling the timer safely (without full rollback)

```bash
sudo systemctl stop vedzovi-self-recovery.timer
```

This stops future runs without removing the units — `sudo systemctl start
vedzovi-self-recovery.timer` resumes it later with no reinstallation
needed.

---

## 12 — Known limitations

- The watchdog can only observe what a public HTTPS reachability check can
  see. It cannot distinguish "backend process healthy but Cloudflare/DNS is
  broken" from "backend process actually down" — in both cases it restarts
  the backend, which is a no-op (not harmful) for the former case.
- Each restart cycle blocks its oneshot service invocation for up to
  roughly `2 × HEALTH_TIMEOUT_SECONDS + VERIFY_WAIT_SECONDS` seconds
  (~30s with defaults) per unhealthy service; `TimeoutStartSec=90` in the
  service unit gives headroom for both services failing in the same run.
- State lives on local disk only (`/var/lib/vedzovi-recovery`) — it is not
  part of `scripts/backup.sh`/`scripts/restore.sh` by design (it is
  operational, not business, data) and resets on VPS rebuild.
