# AGC-072 — Disaster Recovery Plan

## Objective

- **RTO (Recovery Time Objective): ~30–60 minutes** — time to get Vedzovi
  fully functional again on a working VPS.
- **RPO (Recovery Point Objective): ~24 hours** — with the recommended
  nightly (02:00) backup cadence, worst-case data loss is one day of
  uploads/highlights/database changes. Lower this by scheduling backups
  more frequently (see [BACKUP_STRATEGY.md](BACKUP_STRATEGY.md#scheduling-not-installed-automatically)).

## Scope

This plan covers recovery of the application and its data. It does not
cover: DNS registrar access, domain renewal, or the third-party accounts
(Razorpay, Resend) themselves — those are prerequisites, not part of the
backup/restore system.

## Recovery scenarios

### 1. VPS lost entirely (destroyed, unreachable, provider issue)

Full rebuild required.

→ Follow [VPS_REBUILD.md](VPS_REBUILD.md) start to finish, then
[RECOVERY_CHECKLIST.md](RECOVERY_CHECKLIST.md) to verify.

Requires: the most recent backup from `/opt/vedzovi-backups/` copied off
the dead VPS beforehand, or from an off-site copy (see
[Off-site copies](#off-site-copies) below) — a backup stored only on the
VPS that was lost is not recoverable.

### 2. VPS reachable but corrupted (bad deploy, disk corruption, botched manual change)

No need to re-provision. Restore in place.

```bash
sudo systemctl stop agc-backend
sudo bash scripts/restore.sh /opt/vedzovi-backups/<latest-good-timestamp>
```

→ Follow [RESTORE_GUIDE.md](RESTORE_GUIDE.md), then
[RECOVERY_CHECKLIST.md](RECOVERY_CHECKLIST.md).

### 3. Accidental data deletion (e.g. someone `rm -rf`'d uploads or the DB)

Restore only the affected component — see "Restoring a single component
only" in [RESTORE_GUIDE.md](RESTORE_GUIDE.md), or run the full
`restore.sh`, which skips any archive category not needed and only
overwrites what's present in the backup.

### 4. SSL certificates expired or corrupted

If certbot's renewal timer is intact, this shouldn't happen (see
[deploy.md](deploy.md) §5). If certs are lost:

```bash
sudo bash scripts/restore.sh /opt/vedzovi-backups/<latest-timestamp>   # restores /etc/letsencrypt
sudo nginx -t && sudo systemctl reload nginx
```

If no backup contains valid certs, re-issue from scratch per
[deploy.md](deploy.md) §4.

## Off-site copies

`scripts/backup.sh` writes to `/opt/vedzovi-backups/` on the same VPS. This
protects against application-level disasters (bad deploy, deleted data,
corrupted DB) but **not** against total loss of the VPS/disk itself.

For full protection against VPS loss, the ops owner should periodically
sync `/opt/vedzovi-backups/` to storage outside the VPS (e.g. `rsync` to
another host, or an object storage bucket). This is intentionally **not**
part of AGC-072's scope — flagged here so it isn't assumed to already
exist. Until an off-site sync exists, treat a VPS-level disaster (scenario
1) as **unrecoverable data-wise beyond whatever backup was last manually
copied off the box**.

## Decision tree

```
Is the VPS reachable via SSH?
├─ No  → VPS lost. Get the latest backup from an off-site copy.
│         → VPS_REBUILD.md → RECOVERY_CHECKLIST.md
└─ Yes → Is the application broken (bad deploy / corrupted data)?
          ├─ Yes → RESTORE_GUIDE.md (restore in place)
          │         → RECOVERY_CHECKLIST.md
          └─ No  → No recovery needed
```

## Related documents

- [BACKUP_STRATEGY.md](BACKUP_STRATEGY.md) — what's backed up and why
- [RESTORE_GUIDE.md](RESTORE_GUIDE.md) — restore mechanics
- [VPS_REBUILD.md](VPS_REBUILD.md) — provisioning a fresh VPS
- [RECOVERY_CHECKLIST.md](RECOVERY_CHECKLIST.md) — end-to-end verification steps
