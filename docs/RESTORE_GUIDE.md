# AGC-072 — Restore Guide

How to run `scripts/restore.sh` against a backup produced by
`scripts/backup.sh`. For the full "VPS is gone" rebuild flow, start at
[VPS_REBUILD.md](VPS_REBUILD.md) instead — this guide covers the restore
step in isolation (e.g. restoring onto an already-provisioned server, or
rolling back a bad deploy).

## Before you start

- Run as **root** (or via `sudo`) — nginx, systemd, and `/etc/letsencrypt`
  are only readable/writable by root.
- Have the backup directory path ready, e.g.
  `/opt/vedzovi-backups/2026-07-10_020000`.
- Know whether the backend service is currently running — the script asks
  before restarting anything, but stopping it first avoids writes to
  `agc.db` racing the restore.

## Running the restore

```bash
sudo systemctl stop agc-backend    # optional but recommended: avoid concurrent DB writes
sudo bash scripts/restore.sh /opt/vedzovi-backups/2026-07-10_020000
```

The script, in order:

1. **Validates every `.tar.gz` in the backup directory** (`tar -tzf`) before
   touching anything on disk. If any archive is corrupt, it aborts
   immediately with no changes made.
2. **Prompts for confirmation** — you must type `yes` to proceed. Nothing is
   restored on a `Ctrl-C`, blank input, or piped/non-interactive run.
3. Restores, in order, only for archives present in the backup:
   - `database.tar.gz` → `backend/data/agc.db`
   - `uploads.tar.gz` → `backend/storage/uploads/`
   - `highlights.tar.gz` → `backend/storage/highlights/`
   - `config.tar.gz` → `backend/.env`, `/etc/nginx/sites-available/agc`,
     `/etc/systemd/system/agc-*.service`, `/etc/letsencrypt/`
4. **Backs up whatever it's about to overwrite** with a `.pre-restore.bak`
   suffix (files) or directory (uploads/highlights/letsencrypt), so a bad
   restore can be manually reverted.
5. Validates the restored nginx config with `nginx -t` before it's live —
   if validation fails, the script stops rather than leaving nginx in a
   broken state.
6. **Only after every step above has completed**, asks whether to restart
   `agc-backend` and reload nginx. Declining leaves the restored files in
   place for manual inspection first.

## Configuration overrides

Same environment variables as `scripts/backup.sh`, if your paths differ
from the defaults:

```bash
sudo APP_DIR=/home/agc/agc-ai-highlight-creator \
    NGINX_CONF_NAME=agc \
    BACKEND_SERVICE=agc-backend \
    LETSENCRYPT_DIR=/etc/letsencrypt \
    bash scripts/restore.sh /opt/vedzovi-backups/2026-07-10_020000
```

## Restoring a single component only

The script restores everything present in the backup. To restore just one
piece (e.g. only the database, after accidentally corrupting it), extract
the relevant archive by hand instead of running the full script:

```bash
# Database only
sudo systemctl stop agc-backend
cp backend/data/agc.db backend/data/agc.db.manual-bak   # safety copy first
tar -xzf /opt/vedzovi-backups/2026-07-10_020000/database.tar.gz -C /tmp/db-restore
cp /tmp/db-restore/agc.db backend/data/agc.db
sudo systemctl start agc-backend
```

## After a restore

Work through [RECOVERY_CHECKLIST.md](RECOVERY_CHECKLIST.md) to confirm the
application is actually functional, not just that files were copied.

## Rolling back a restore

Every overwritten file/directory is preserved alongside the original with
a `.pre-restore.bak` suffix:

```bash
backend/data/agc.db.pre-restore.bak
backend/storage/uploads.pre-restore.bak/
backend/storage/highlights.pre-restore.bak/
backend/.env.pre-restore.bak
/etc/nginx/sites-available/agc.pre-restore.bak
/etc/letsencrypt.pre-restore.bak/
```

To roll back, stop the backend, move the `.pre-restore.bak` copy back over
the restored one, and restart.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Script exits at "corrupt archive" | Backup file truncated/corrupted in transit | Use a different timestamped backup, or re-copy the archive and retry |
| `nginx -t` fails after restore | Restored config references certs that don't exist yet | Restore `config.tar.gz` fully (it includes `/etc/letsencrypt`) before reloading nginx |
| Backend won't start post-restore | `.env` restored but `JWT_SECRET_KEY`/`ENVIRONMENT` missing | Check `backend/.env` matches [deploy.md](deploy.md) §6 |
| Restore prompt never appears | Running non-interactively (e.g. from a script/CI) | Run the restore from an interactive shell; this is intentional — restores must be confirmed by a human |
