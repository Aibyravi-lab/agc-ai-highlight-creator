#!/usr/bin/env bash
# AGC-072 — Production restore script for Vedzovi (AGC AI Highlight Creator)
#
# Run this ON THE VPS as root:
#   sudo bash scripts/restore.sh /opt/vedzovi-backups/2026-07-10_020000
#
# Restores from a backup produced by scripts/backup.sh:
#   - SQLite database, uploads, generated highlights
#   - backend/.env, nginx site config, systemd unit files, Let's Encrypt certs
#
# Every archive's SHA256 checksum (checksums.sha256, written by backup.sh) is
# verified before any archive is extracted — the restore aborts immediately
# if any checksum fails.
#
# Existing files are saved with a .pre-restore.bak suffix before being
# overwritten. Services are only restarted after every step has completed,
# and only with explicit confirmation. See docs/RESTORE_GUIDE.md.

set -euo pipefail

# ─── Configuration (override via env vars if needed) ────────────────────────
APP_DIR="${APP_DIR:-/home/agc/agc-ai-highlight-creator}"
BACKEND_DIR="${BACKEND_DIR:-${APP_DIR}/backend}"
NGINX_CONF_NAME="${NGINX_CONF_NAME:-agc}"
BACKEND_SERVICE="${BACKEND_SERVICE:-agc-backend}"
LETSENCRYPT_DIR="${LETSENCRYPT_DIR:-/etc/letsencrypt}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
fail() { log "FAIL: $*"; exit 1; }

BACKUP_DIR="${1:-}"
[ -n "$BACKUP_DIR" ] || fail "usage: $0 /opt/vedzovi-backups/<timestamp>"
[ -d "$BACKUP_DIR" ] || fail "backup directory not found: $BACKUP_DIR"

log "== AGC-072 restore starting from: $BACKUP_DIR =="

# ─── 0. Validate every archive before touching anything on disk ────────────
FOUND_ANY=0
for archive in "$BACKUP_DIR"/*.tar.gz; do
    [ -e "$archive" ] || continue
    FOUND_ANY=1
    tar -tzf "$archive" >/dev/null || fail "corrupt archive, aborting before any changes: $archive"
    log "verified: $(basename "$archive")"
done
[ "$FOUND_ANY" -eq 1 ] || fail "no .tar.gz archives found in $BACKUP_DIR"

# ─── 0b. Verify archive checksums before extracting anything (Revision 3) ───
[ -f "$BACKUP_DIR/checksums.sha256" ] \
    || fail "checksums.sha256 not found in $BACKUP_DIR — cannot verify archive integrity, aborting before any changes"
command -v sha256sum >/dev/null 2>&1 \
    || fail "sha256sum is required to verify checksums.sha256"
( cd "$BACKUP_DIR" && sha256sum -c checksums.sha256 ) \
    || fail "checksum verification failed — one or more archives are corrupted or modified. Aborting before any changes."
log "all archive checksums verified against checksums.sha256"

[ "$(id -u)" -eq 0 ] || log "WARNING: not running as root — nginx/systemd/letsencrypt steps may fail on permission"

# ─── 1. Confirm before overwriting anything ─────────────────────────────────
echo
echo "This will OVERWRITE the following on this machine, where present in the backup:"
echo "  - ${BACKEND_DIR}/data/agc.db"
echo "  - ${BACKEND_DIR}/storage/uploads/"
echo "  - ${BACKEND_DIR}/storage/highlights/"
echo "  - ${BACKEND_DIR}/.env"
echo "  - /etc/nginx/sites-available/${NGINX_CONF_NAME}"
echo "  - /etc/systemd/system/agc-*.service"
echo "  - ${LETSENCRYPT_DIR}"
echo
echo "Existing files are saved with a .pre-restore.bak suffix first."
echo
read -r -p "Type 'yes' to continue: " CONFIRM
[ "$CONFIRM" = "yes" ] || fail "restore aborted by user (confirmation not given)"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# ─── 2. Database ──────────────────────────────────────────────────────────────
if [ -f "$BACKUP_DIR/database.tar.gz" ]; then
    log "restoring database"
    mkdir -p "$BACKEND_DIR/data"
    if [ -f "$BACKEND_DIR/data/agc.db" ]; then
        cp -p "$BACKEND_DIR/data/agc.db" "$BACKEND_DIR/data/agc.db.pre-restore.bak"
    fi
    mkdir -p "$WORK/database"
    tar -xzf "$BACKUP_DIR/database.tar.gz" -C "$WORK/database" || fail "failed to extract database archive"
    [ -f "$WORK/database/agc.db" ] || fail "database archive did not contain agc.db"
    cp -p "$WORK/database/agc.db" "$BACKEND_DIR/data/agc.db" || fail "failed to restore database"
    log "database restored (previous copy saved as agc.db.pre-restore.bak, if it existed)"
else
    log "no database.tar.gz in backup — skipping"
fi

# ─── 3. Uploads ────────────────────────────────────────────────────────────────
if [ -f "$BACKUP_DIR/uploads.tar.gz" ]; then
    log "restoring uploads"
    mkdir -p "$BACKEND_DIR/storage"
    if [ -d "$BACKEND_DIR/storage/uploads" ]; then
        mv "$BACKEND_DIR/storage/uploads" "$BACKEND_DIR/storage/uploads.pre-restore.bak"
    fi
    tar -xzf "$BACKUP_DIR/uploads.tar.gz" -C "$BACKEND_DIR/storage" || fail "failed to restore uploads"
    log "uploads restored (previous copy saved as uploads.pre-restore.bak, if it existed)"
else
    log "no uploads.tar.gz in backup — skipping"
fi

# ─── 4. Generated highlights ────────────────────────────────────────────────────
if [ -f "$BACKUP_DIR/highlights.tar.gz" ]; then
    log "restoring generated highlights"
    mkdir -p "$BACKEND_DIR/storage"
    if [ -d "$BACKEND_DIR/storage/highlights" ]; then
        mv "$BACKEND_DIR/storage/highlights" "$BACKEND_DIR/storage/highlights.pre-restore.bak"
    fi
    tar -xzf "$BACKUP_DIR/highlights.tar.gz" -C "$BACKEND_DIR/storage" || fail "failed to restore highlights"
    log "highlights restored (previous copy saved as highlights.pre-restore.bak, if it existed)"
else
    log "no highlights.tar.gz in backup — skipping"
fi

# ─── 5. Configuration bundle: .env, nginx, systemd, SSL ────────────────────────
if [ -f "$BACKUP_DIR/config.tar.gz" ]; then
    log "restoring configuration bundle"
    mkdir -p "$WORK/config"
    tar -xzf "$BACKUP_DIR/config.tar.gz" -C "$WORK/config" || fail "failed to extract config archive"

    if [ -f "$WORK/config/backend.env" ]; then
        [ -f "$BACKEND_DIR/.env" ] && cp -p "$BACKEND_DIR/.env" "$BACKEND_DIR/.env.pre-restore.bak"
        cp -p "$WORK/config/backend.env" "$BACKEND_DIR/.env"
        log "restored backend/.env (previous copy saved as .env.pre-restore.bak, if it existed)"
    fi

    if [ -f "$WORK/config/nginx/${NGINX_CONF_NAME}" ]; then
        [ -f "/etc/nginx/sites-available/${NGINX_CONF_NAME}" ] \
            && cp -p "/etc/nginx/sites-available/${NGINX_CONF_NAME}" "/etc/nginx/sites-available/${NGINX_CONF_NAME}.pre-restore.bak"
        cp -p "$WORK/config/nginx/${NGINX_CONF_NAME}" "/etc/nginx/sites-available/${NGINX_CONF_NAME}"
        ln -sf "/etc/nginx/sites-available/${NGINX_CONF_NAME}" "/etc/nginx/sites-enabled/${NGINX_CONF_NAME}"
        if command -v nginx >/dev/null 2>&1; then
            nginx -t || fail "restored nginx config failed validation (nginx -t) — fix before reloading nginx"
        fi
        log "restored nginx config (previous copy saved as ${NGINX_CONF_NAME}.pre-restore.bak, if it existed)"
    fi

    if [ -d "$WORK/config/systemd" ] && [ -n "$(ls -A "$WORK/config/systemd" 2>/dev/null)" ]; then
        cp -p "$WORK/config/systemd/"*.service /etc/systemd/system/
        command -v systemctl >/dev/null 2>&1 && systemctl daemon-reload
        log "restored systemd unit files"
    fi

    if [ -d "$WORK/config/letsencrypt" ]; then
        if [ -d "$LETSENCRYPT_DIR" ]; then
            rm -rf "${LETSENCRYPT_DIR}.pre-restore.bak" 2>/dev/null || true
            mv "$LETSENCRYPT_DIR" "${LETSENCRYPT_DIR}.pre-restore.bak"
        fi
        mkdir -p "$(dirname "$LETSENCRYPT_DIR")"
        cp -a "$WORK/config/letsencrypt" "$LETSENCRYPT_DIR"
        chmod -R go-rwx "$LETSENCRYPT_DIR"
        log "restored Let's Encrypt certificates (previous copy saved as $(basename "$LETSENCRYPT_DIR").pre-restore.bak, if it existed)"
    fi
else
    log "no config.tar.gz in backup — skipping"
fi

# ─── 6. Restart services only after every restore step has completed ───────
echo
read -r -p "Restart nginx and ${BACKEND_SERVICE} now? [y/N] " RESTART_CONFIRM
if [ "$RESTART_CONFIRM" = "y" ] || [ "$RESTART_CONFIRM" = "Y" ]; then
    if command -v systemctl >/dev/null 2>&1; then
        systemctl restart "$BACKEND_SERVICE" && log "restarted $BACKEND_SERVICE" \
            || log "WARNING: failed to restart $BACKEND_SERVICE — check with: systemctl status $BACKEND_SERVICE"
        systemctl reload nginx && log "reloaded nginx" \
            || log "WARNING: failed to reload nginx — check with: nginx -t"
    else
        log "WARNING: systemctl not available — restart services manually"
    fi
else
    log "skipped service restart — restart manually when ready"
fi

log "== restore completed: $BACKUP_DIR =="
echo
echo "SUCCESS: restore complete."
echo "Next: walk through docs/RECOVERY_CHECKLIST.md to verify the application end to end."
exit 0
