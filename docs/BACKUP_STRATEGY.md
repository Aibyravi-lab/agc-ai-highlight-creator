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
```

## Related documents

- [RESTORE_GUIDE.md](RESTORE_GUIDE.md) — how to run `scripts/restore.sh`
- [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md) — when to use which recovery path
- [VPS_REBUILD.md](VPS_REBUILD.md) — provisioning a fresh VPS from scratch
- [RECOVERY_CHECKLIST.md](RECOVERY_CHECKLIST.md) — step-by-step recovery checklist
- [deploy.md](deploy.md) — original production deployment guide (DNS, nginx, SSL, systemd)
