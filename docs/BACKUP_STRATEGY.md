# AGC-072 — Backup Strategy

Target: `vedzovi.com` production VPS (`45.94.209.92`, see [deploy.md](deploy.md)).

This document explains *what* is backed up, *why*, and *how* — the mechanics of
running a restore live in [RESTORE_GUIDE.md](RESTORE_GUIDE.md).

## Goal

If the VPS is lost or corrupted, Vedzovi can be rebuilt on a fresh VPS and
restored to a working state within approximately 30–60 minutes, with at most
one day of user data loss (nightly backup cadence).

## What is backed up

| Component | Source path | Archive |
|---|---|---|
| SQLite database | `backend/data/agc.db` | `database.tar.gz` |
| Uploads | `backend/storage/uploads/` | `uploads.tar.gz` |
| Generated highlights | `backend/storage/highlights/` | `highlights.tar.gz` |
| Backend environment | `backend/.env` | `config.tar.gz` |
| Nginx site config | `/etc/nginx/sites-available/agc` | `config.tar.gz` |
| systemd unit files | `/etc/systemd/system/agc-*.service` | `config.tar.gz` |
| Let's Encrypt certificates | `/etc/letsencrypt/` | `config.tar.gz` |

The database is captured with `sqlite3 .backup`, which produces a
consistent snapshot even if the backend is running and the DB is
mid-write. `sqlite3` is a hard requirement for the backup script: after
the snapshot is taken, the script runs `PRAGMA integrity_check;` against
the backup copy and aborts the entire backup immediately if the result is
anything other than `ok` (see [Integrity and verification](#integrity-and-verification)).

## What is deliberately excluded

- `.git`, `node_modules`, `venv`, `__pycache__`, `.next` build cache — all
  reproduced by `git clone` + `pip install` + `npm install` + `npm run build`.
- Logs (`backend/logs/`) — operational history, not recovery-critical.
- `backend/storage/frames`, `backend/storage/thumbnails`, `backend/storage/jobs` —
  these are the pipeline's own working storage. `CleanupService` already
  deletes frames after 1 day, thumbnails after 1 day, and job working
  directories after `TEMP_CLEANUP_HOURS` (default 24h) regardless of backups;
  they are intermediate/derivable pipeline artifacts, not source-of-truth data.
- AI model cache (Whisper/PyTorch/Transformers weights) — large, and
  re-downloaded automatically on first use after a rebuild.

If this scope needs to change (e.g. a new persistent storage folder is added
to the pipeline), update `scripts/backup.sh` and this table together.

### Included vs. excluded, at a glance

| Item | Included |
|------|----------|
| SQLite | ✅ |
| Uploads | ✅ |
| Highlights | ✅ |
| .env | ✅ |
| Nginx | ✅ |
| systemd | ✅ |
| SSL Certificates | ✅ |
| Logs | ❌ |
| node_modules | ❌ |
| venv | ❌ |
| AI Model Cache | ❌ |
| Temporary Pipeline Storage | ❌ |

## Where backups live

```
/opt/vedzovi-backups/
    2026-07-10_020000/
        database.tar.gz
        uploads.tar.gz
        highlights.tar.gz
        config.tar.gz
        checksums.sha256
        manifest.txt
    2026-07-11_020000/
        ...
    logs/
        backup_2026-07-10_020000.log
        ...
    last_backup_status
    last_restore_test_status
```

Each run's archives and log are stamped with `YYYY-MM-DD_HHMMSS`. Because the
archives contain secrets (`.env` — JWT secret, Razorpay keys; the database —
password hashes; Let's Encrypt private keys), `scripts/backup.sh`:

- creates each timestamped folder `chmod 700`
- writes archives, `checksums.sha256`, and `manifest.txt` `chmod 600`

### Integrity and verification

Every backup directory contains two extra files alongside the archives:

- **`checksums.sha256`** — SHA256 of every `.tar.gz` in the run, generated
  with `sha256sum`. `scripts/restore.sh` verifies every checksum before
  extracting anything and aborts the restore immediately if any archive
  fails verification.
- **`manifest.txt`** — metadata about the run: backup timestamp, hostname,
  Ubuntu version, current git commit (`git rev-parse HEAD`) and tag
  (`git describe --tags`) of the deployed repo, backup format version,
  backup script version, the SQLite database filename, the list of
  generated archives, and the checksum file name. Git metadata is recorded
  as `Unknown` rather than failing the backup if the repo/tag can't be
  determined.

The SQLite backup itself is verified before archiving: `scripts/backup.sh`
runs `PRAGMA integrity_check;` against the freshly-taken `.backup` copy and
fails the entire backup immediately (before any archive is written) if the
result isn't exactly `ok`.

`BACKUP_FORMAT_VERSION` (currently `1`) identifies the layout of the backup
directory itself (which archives/metadata files exist and what they
contain). Bump it in `scripts/backup.sh` only if that layout changes in a
way `scripts/restore.sh` needs to know about. `BACKUP_SCRIPT_VERSION`
tracks the script implementation and can change more freely.

`/opt/vedzovi-backups` itself should be created with restrictive ownership
(root-only) before the first run — it lives outside the git-tracked repo
and outside `/home/agc`, so it isn't wiped if the app user's home directory
is rebuilt.

## Running a backup manually

```bash
sudo bash scripts/backup.sh
```

Override any path via environment variable if your deployment differs from
the defaults baked into the script (`APP_DIR`, `BACKUP_ROOT`,
`RETENTION_DAYS`, `LOG_RETENTION_DAYS`, `MIN_FREE_PERCENT`,
`NGINX_CONF_NAME`, `SYSTEMD_UNIT_GLOB`, `LETSENCRYPT_DIR`):

```bash
sudo APP_DIR=/home/agc/agc-ai-highlight-creator BACKUP_ROOT=/opt/vedzovi-backups \
    bash scripts/backup.sh
```

The script exits non-zero on any failure (`set -euo pipefail` + an `ERR`
trap) and never partially deletes retained backups if the run itself failed.

### Disk space check

Before creating anything, the script computes free space as a percentage
of the backup filesystem's total size (`available / total * 100`, via
`df -Pm`) and aborts with a clear error — before touching any archive — if
free space is below `MIN_FREE_PERCENT` (default **15%**). This replaces an
earlier fixed-MB-floor check: a percentage scales correctly whether
`/opt` is on a 20GB or a 2TB volume.

## Retention policy

- Keeps the last **30** daily backups (by directory mtime, matched only
  against `YYYY-MM-DD_HHMMSS`-named directories — logs and status files are
  never swept).
- Backups older than 30 days are deleted automatically at the end of each
  successful run.
- Override with `RETENTION_DAYS=<n>` if a different window is needed.
- Backup **logs** (`logs/backup_*.log`) are pruned separately once they're
  older than `LOG_RETENTION_DAYS` (default **30**), so `logs/` doesn't grow
  forever independently of how long backup archives themselves are kept.

## Scheduling (not installed automatically)

Per AGC-072 scope, cron is **documented only** — nothing is installed by this
change. To enable nightly backups at 2am server time, the CTO/ops owner
should add this to root's crontab (`sudo crontab -e`):

```cron
0 2 * * * /usr/bin/env bash /home/agc/agc-ai-highlight-creator/scripts/backup.sh >> /opt/vedzovi-backups/logs/cron.log 2>&1
```

Recommended schedule: `0 2 * * *` (02:00 daily, low-traffic window).

After installing, verify it fires:

```bash
sudo crontab -l                                  # confirm the entry is present
cat /opt/vedzovi-backups/last_backup_status       # after the next 2am run
```

### Restore-test (not the same as the checksum check above)

`sha256sum -c checksums.sha256` (run by `scripts/backup.sh` and by
`HealthService.verify_backup_archive_integrity()`) only proves the archive
*bytes* weren't corrupted or modified — it never extracts anything, so it
cannot catch an archive that's checksum-clean but doesn't actually restore
into a usable database.

`scripts/restore_test.sh` closes that gap without touching production: it
extracts the latest backup's archives into a throwaway directory under
`/tmp`, runs `PRAGMA integrity_check;` against the *extracted* SQLite copy,
validates the uploads/highlights/config archives landed their expected
contents, and deletes the throwaway directory unconditionally on exit. It
never invokes `scripts/restore.sh` and never writes to `backend/data/agc.db`,
`backend/storage/`, `backend/.env`, nginx, systemd, or Let's Encrypt.

```bash
sudo bash scripts/restore_test.sh
cat /opt/vedzovi-backups/last_restore_test_status   # "SUCCESS <ts>: <backup_dir>" or "FAILED <ts>: ..."
```

Recommended weekly cron (root's crontab), staggered after the nightly
backup so it always tests the freshest one:

```cron
0 3 * * 0 /usr/bin/env bash /home/agc/agc-ai-highlight-creator/scripts/restore_test.sh >> /opt/vedzovi-backups/logs/restore_test_cron.log 2>&1
```

Like the backup cron itself, this is **documented only** — not installed
automatically by any code change. `HealthEngineService._check_backups()`
reads `last_restore_test_status` read-only via
`HealthService.get_restore_test_status()`: until this file exists, the
`backups` health check reports `warning` ("...restore-test has never been
performed"), never `healthy` — a checksum-clean, fresh backup alone is not
enough to claim the backup is actually restorable.

### Archive-integrity evidence for the backend health check (VED-BACKUP-INTEGRITY-001)

`HealthEngineService._check_backups()` needs the checksum-verification result
above as a machine-readable signal, but the backend runs as the unprivileged
`agc` user, and `/opt/vedzovi-backups` is deliberately root-only (see
[Where backups live](#where-backups-live)) — `agc` cannot traverse into a
`700` timestamped backup directory to read `checksums.sha256` itself.
Backup permissions are **not** weakened to fix this.

Instead, `agc` is granted a single, narrowly-scoped, argument-free `sudo`
rule to run one fixed-purpose root-owned script:

```
agc backend
  -> sudo -n /usr/local/sbin/vedzovi-verify-backup   (no arguments accepted)
  -> scripts/verify_backup_integrity.sh, installed as that binary
  -> fixed BACKUP_ROOT=/opt/vedzovi-backups, no path input from the caller
  -> sha256sum -c against the latest backup's checksums.sha256 only
  -> strict key=value stdout, consumed by HealthService
```

`scripts/verify_backup_integrity.sh`:

- takes no arguments (any argument is rejected)
- never extracts an archive, never writes, deletes, or modifies anything
  under `BACKUP_ROOT`, never touches live application data, and never
  invokes `scripts/restore.sh` or `scripts/restore_test.sh`
- prints exactly four `key=value` lines (`status`, `verified`,
  `backup_dir`, `reason`) and exits `0` (healthy), `1` (unhealthy — the
  archive checksums don't match, or `checksums.sha256` is missing), or `2`
  (unknown — no backup found, or the environment isn't usable)

`HealthService.verify_backup_archive_integrity()` invokes it via
`subprocess.run(["sudo", "-n", ...], ...)` (no shell, bounded timeout) and
strictly parses that output — any malformed, inconsistent, or unreachable
result becomes `status="unknown"`, never a silently-assumed `"healthy"`.
`HealthService._invoke_backup_verifier()` is a single, separately-mockable
method specifically so the backend's unit tests never need real `sudo` or
the production verifier installed.

#### Install (as root, on the VPS)

```bash
# 1. Install the verifier binary
sudo install -o root -g root -m 0755 scripts/verify_backup_integrity.sh \
    /usr/local/sbin/vedzovi-verify-backup

# 2. Install the sudoers rule
sudo cp systemd/vedzovi-backup-verifier.sudoers /etc/sudoers.d/vedzovi-backup-verifier
sudo chmod 440 /etc/sudoers.d/vedzovi-backup-verifier
sudo visudo -cf /etc/sudoers.d/vedzovi-backup-verifier   # must print "parsed OK"

# 3. Verify it works as the agc user
sudo -u agc sudo -n /usr/local/sbin/vedzovi-verify-backup
# expect: status=healthy / unhealthy / unknown lines, matching the current
# backup state — never a password prompt (NOPASSWD) and never a shell
```

#### Rollback

```bash
sudo rm -f /etc/sudoers.d/vedzovi-backup-verifier
sudo rm -f /usr/local/sbin/vedzovi-verify-backup
```

`HealthService.verify_backup_archive_integrity()` degrades to
`status="unknown"` the moment either is removed (the `sudo -n` call simply
fails) — this rollback never affects `scripts/backup.sh`,
`scripts/restore_test.sh`, or backup permissions in any way.

#### Troubleshooting

| Symptom | Likely cause | Check |
|---|---|---|
| Health check shows `archive_integrity.status = "unknown"` | Verifier or sudoers rule not installed, or path mismatch | Re-run the install steps above; confirm `/usr/local/sbin/vedzovi-verify-backup` exists and is `0755 root:root` |
| `sudo: a password is required` when run manually as `agc` | Sudoers rule missing/misconfigured | `sudo visudo -cf /etc/sudoers.d/vedzovi-backup-verifier`; confirm the exact path matches `/usr/local/sbin/vedzovi-verify-backup` |
| `reason=no_checksum_file` | `scripts/backup.sh` didn't complete the checksum step, or was interrupted | Check `BACKUP_ROOT/logs/backup_<ts>.log` for the failed run |
| `reason=checksum_mismatch` | An archive was corrupted or modified after the backup ran | Do not trust that backup for restore; investigate how it was altered, then let the next scheduled `scripts/backup.sh` run produce a fresh one |
| `reason=not_root` | Verifier invoked directly by a non-root user, bypassing `sudo` | Always invoke it through `sudo -n /usr/local/sbin/vedzovi-verify-backup`, never directly |

This is archive-integrity evidence only — it is deliberately independent of
[restore-test evidence](#restore-test-not-the-same-as-the-checksum-check-above);
a `healthy` result here never implies the restore-test has passed, and vice
versa. See `HealthEngineService._check_backups()` for how the three signals
(freshness, archive-integrity, restore-test) combine into one status without
ever conflating them.

## Verifying backups are healthy

```bash
# Latest backup succeeded?
cat /opt/vedzovi-backups/last_backup_status

# Archive integrity (same check the script itself runs)
for f in /opt/vedzovi-backups/2026-07-10_020000/*.tar.gz; do
  tar -tzf "$f" >/dev/null && echo "OK: $f" || echo "CORRUPT: $f"
done

# Checksums (same check restore.sh runs before extracting anything)
( cd /opt/vedzovi-backups/2026-07-10_020000 && sha256sum -c checksums.sha256 )

# Manifest — confirm this backup matches the commit/tag you expect
cat /opt/vedzovi-backups/2026-07-10_020000/manifest.txt

# Spot-check archive contents without extracting
tar -tzf /opt/vedzovi-backups/2026-07-10_020000/database.tar.gz
tar -tzf /opt/vedzovi-backups/2026-07-10_020000/config.tar.gz

# Actual restore-test (extracts + PRAGMA integrity_check, non-destructive)
cat /opt/vedzovi-backups/last_restore_test_status
```

## Related documents

- [RESTORE_GUIDE.md](RESTORE_GUIDE.md) — how to run `scripts/restore.sh`
- [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md) — when to use which recovery path
- [VPS_REBUILD.md](VPS_REBUILD.md) — provisioning a fresh VPS from scratch
- [RECOVERY_CHECKLIST.md](RECOVERY_CHECKLIST.md) — step-by-step recovery checklist
- [deploy.md](deploy.md) — original production deployment guide (DNS, nginx, SSL, systemd)
