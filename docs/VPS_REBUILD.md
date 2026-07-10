# AGC-072 — VPS Rebuild Guide

Full procedure to stand up Vedzovi on a **fresh Ubuntu 22.04 VPS** after
total loss of the previous server, restoring from a backup produced by
`scripts/backup.sh`. This combines the baseline setup from
[deploy.md](deploy.md) with the restore step, in the order needed for a
clean disaster recovery.

Prerequisite: you have a backup directory available (copied off the old
VPS beforehand, or from an off-site copy — see
[DISASTER_RECOVERY.md](DISASTER_RECOVERY.md#off-site-copies)). Without one,
you can still follow this guide to stand up a *fresh* deployment, but user
data (accounts, uploads, highlights, purchase history) will not be
recoverable.

Numbered steps below match [RECOVERY_CHECKLIST.md](RECOVERY_CHECKLIST.md) —
use that file to tick off progress as you go.

---

## 1 — Provision a fresh Ubuntu VPS

Provision an Ubuntu 22.04 VPS and point DNS at it (or reuse the existing
`vedzovi.com` / `api.vedzovi.com` A records once the new IP is known — see
[deploy.md](deploy.md) §1).

Create the application user matching the existing systemd unit
(`backend/scripts/agc-backend.service` runs as user `agc`):

```bash
sudo adduser --disabled-password --gecos "" agc
```

## 2 — Install dependencies

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git ffmpeg nginx certbot python3-certbot-nginx

curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

python3 --version    # 3.10+
node --version       # 18+
ffmpeg -version
ffprobe -version
```

Firewall (see [deploy.md](deploy.md) §2):

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 3000/tcp
sudo ufw deny 8000/tcp
sudo ufw enable
```

## 3 — Clone the repository

The production systemd unit expects the repo at
`/home/agc/agc-ai-highlight-creator` (confirmed against the live server as
of AGC-045.2 — this is the actual path in use, not the generic
`/path/to/AGC_AI_Highlight_Creator` placeholder in deploy.md):

```bash
sudo -u agc git clone <repo-url> /home/agc/agc-ai-highlight-creator
cd /home/agc/agc-ai-highlight-creator
```

## 4 — Create the Python virtual environment

The confirmed production layout keeps the venv at the **repo root**, not
`backend/venv` (see the header comment in `backend/scripts/agc-backend.service`):

```bash
cd /home/agc/agc-ai-highlight-creator
sudo -u agc python3 -m venv venv
sudo -u agc bash -c "source venv/bin/activate && pip install --upgrade pip && pip install -r backend/requirements.txt"
```

## 5 — Restore application data and configuration

Copy the backup archive onto the new VPS (e.g. `scp` from wherever it was
stored off-site), then run the restore script from the freshly cloned repo:

```bash
sudo bash scripts/restore.sh /path/to/copied-backup/2026-07-10_020000
```

This single step restores, in order (see [RESTORE_GUIDE.md](RESTORE_GUIDE.md)
for the full mechanics):

- **`.env`** → `backend/.env`
- **SQLite database** → `backend/data/agc.db`
- **uploads** → `backend/storage/uploads/`
- **generated highlights** → `backend/storage/highlights/`
- **nginx configuration** → `/etc/nginx/sites-available/agc` (+ `sites-enabled` symlink)
- **systemd service files** → `/etc/systemd/system/agc-*.service`
- **SSL certificates** → `/etc/letsencrypt/`

Decline the "restart services now?" prompt at the end — dependencies
(nginx site enabled, frontend built) aren't in place yet.

If you have **no backup** to restore (fresh deployment, not a disaster
recovery), instead follow [deploy.md](deploy.md) §3–§6 to create these
files from scratch.

## 6 — Restart services

```bash
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl daemon-reload
sudo systemctl enable agc-backend
sudo systemctl restart agc-backend
sudo systemctl reload nginx
```

If certs were restored, they should already match `vedzovi.com`. If
certbot's renewal timer isn't active on the new box:

```bash
sudo systemctl status certbot.timer   # should show: active (waiting)
sudo certbot renew --dry-run
```

If no certs were restored (fresh deployment), issue new ones per
[deploy.md](deploy.md) §4.

## 7 — Build and start the frontend

```bash
cd /home/agc/agc-ai-highlight-creator/frontend
sudo -u agc npm install
sudo -u agc npm run build
sudo -u agc npm start -- --port 3000   # run under systemd or pm2 for persistence — see deploy.md §7
```

Confirm `frontend/.env.local` has:

```dotenv
NEXT_PUBLIC_API_URL=https://api.vedzovi.com
```

## 8–20 — Verify everything works

Move to [RECOVERY_CHECKLIST.md](RECOVERY_CHECKLIST.md) items 13–20
(restart/verify backend, frontend, login, upload, pipeline, Razorpay,
subscriptions, downloads).

## Related documents

- [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md) — when to use this guide vs. an in-place restore
- [RESTORE_GUIDE.md](RESTORE_GUIDE.md) — details of the restore step (step 5 above)
- [BACKUP_STRATEGY.md](BACKUP_STRATEGY.md) — what's in the backup being restored
- [deploy.md](deploy.md) — original from-scratch deployment guide (used above for anything not covered by the backup)
