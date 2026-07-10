#!/usr/bin/env bash
# AGC-072 — Production backup script for Vedzovi (AGC AI Highlight Creator)
#
# Run this ON THE VPS as root (nginx / systemd / Let's Encrypt paths require it):
#   sudo bash scripts/backup.sh
#
# Backs up, into a timestamped folder under /opt/vedzovi-backups/:
#   - SQLite database         (backend/data/agc.db) — verified with
#                              PRAGMA integrity_check before archiving
#   - uploads                 (backend/storage/uploads/)
#   - generated highlights    (backend/storage/highlights/)
#   - backend/.env, nginx site config, systemd unit files, Let's Encrypt certs
#   - manifest.txt            (backup metadata: host, git commit, versions)
#   - checksums.sha256        (SHA256 of every archive, for restore-time verification)
#
# Deliberately excluded (regenerable, not disaster-recovery state):
#   .git, node_modules, venv, __pycache__, logs, temp files, AI model cache,
#   build cache, storage/frames, storage/thumbnails, storage/jobs (see
#   docs/BACKUP_STRATEGY.md for why these are excluded).
#
# See docs/BACKUP_STRATEGY.md for full rationale and docs/RESTORE_GUIDE.md
# for how to restore from what this script produces.

set -euo pipefail

# ─── Versioning (AGC-072 revision 5) ─────────────────────────────────────────
# Bump BACKUP_FORMAT_VERSION only if the archive/manifest layout changes in a
# way that breaks restore.sh's assumptions. Bump BACKUP_SCRIPT_VERSION on any
# other change to this script.
BACKUP_FORMAT_VERSION=1
BACKUP_SCRIPT_VERSION="1.1.0"

# ─── Configuration (override via env vars if needed) ────────────────────────
APP_DIR="${APP_DIR:-/home/agc/agc-ai-highlight-creator}"
BACKEND_DIR="${BACKEND_DIR:-${APP_DIR}/backend}"
BACKUP_ROOT="${BACKUP_ROOT:-/opt/vedzovi-backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
LOG_RETENTION_DAYS="${LOG_RETENTION_DAYS:-30}"
MIN_FREE_PERCENT="${MIN_FREE_PERCENT:-15}"
NGINX_CONF_NAME="${NGINX_CONF_NAME:-agc}"
SYSTEMD_UNIT_GLOB="${SYSTEMD_UNIT_GLOB:-agc-*.service}"
LETSENCRYPT_DIR="${LETSENCRYPT_DIR:-/etc/letsencrypt}"

TIMESTAMP="$(date +%Y-%m-%d_%H%M%S)"
DEST="${BACKUP_ROOT}/${TIMESTAMP}"
WORK="${DEST}/.tmp"
LOG_DIR="${BACKUP_ROOT}/logs"
LOG_FILE="${LOG_DIR}/backup_${TIMESTAMP}.log"
STATUS_FILE="${BACKUP_ROOT}/last_backup_status"

# ─── Logging ─────────────────────────────────────────────────────────────────
mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

fail() {
    log "FAIL: $*"
    echo "FAILED ${TIMESTAMP}: $*" > "$STATUS_FILE"
    rm -rf "$WORK" 2>/dev/null || true
    exit 1
}

trap 'fail "unexpected error at line $LINENO"' ERR

log "== AGC-072 backup starting: ${TIMESTAMP} =="

# ─── 0. Pre-flight checks ────────────────────────────────────────────────────
[ "$(id -u)" -eq 0 ] || log "WARNING: not running as root — nginx/systemd/letsencrypt steps may fail on permission"

command -v tar >/dev/null 2>&1 || fail "tar is required but not found"

[ -d "$BACKEND_DIR" ] || fail "backend directory not found at $BACKEND_DIR (set APP_DIR/BACKEND_DIR)"

mkdir -p "$BACKUP_ROOT" || fail "cannot create backup root $BACKUP_ROOT"

# Revision 4: abort if free space on the backup filesystem is below
# MIN_FREE_PERCENT (default 15%), not just an absolute MB floor.
read -r FS_TOTAL_MB FS_AVAILABLE_MB FS_MOUNT <<< "$(df -Pm "$BACKUP_ROOT" | awk 'NR==2 {print $2, $4, $6}')"
[ -n "$FS_TOTAL_MB" ] && [ -n "$FS_AVAILABLE_MB" ] && [ "$FS_TOTAL_MB" -gt 0 ] \
    || fail "could not determine free disk space for $BACKUP_ROOT"
FS_FREE_PERCENT=$(( FS_AVAILABLE_MB * 100 / FS_TOTAL_MB ))
if [ "$FS_FREE_PERCENT" -lt "$MIN_FREE_PERCENT" ]; then
    fail "Backup cancelled: filesystem ${FS_MOUNT} has only ${FS_FREE_PERCENT}% free (${FS_AVAILABLE_MB}MB of ${FS_TOTAL_MB}MB), below the required ${MIN_FREE_PERCENT}% threshold. Free up disk space (or raise MIN_FREE_PERCENT if this is expected) before retrying."
fi

mkdir -p "$DEST" "$WORK"
chmod 700 "$DEST"
log "backup destination: $DEST (${FS_FREE_PERCENT}% free on ${FS_MOUNT})"

# ─── 1. SQLite database ──────────────────────────────────────────────────────
DB_PATH="${BACKEND_DIR}/data/agc.db"
DB_FILENAME="N/A"
if [ -f "$DB_PATH" ]; then
    log "backing up SQLite database"
    command -v sqlite3 >/dev/null 2>&1 \
        || fail "sqlite3 is required to create and verify the database backup"
    mkdir -p "$WORK/database"

    # .backup takes a consistent snapshot even if the DB is open/in WAL mode
    sqlite3 "$DB_PATH" ".backup '$WORK/database/agc.db'" \
        || fail "sqlite3 .backup failed for $DB_PATH"

    # Revision 2: verify the backup copy is not corrupt before archiving it.
    # Anything other than "ok" fails the backup immediately.
    log "verifying SQLite backup integrity"
    INTEGRITY_RESULT="$(sqlite3 "$WORK/database/agc.db" "PRAGMA integrity_check;" 2>&1)"
    [ "$INTEGRITY_RESULT" = "ok" ] \
        || fail "SQLite integrity check failed on backup copy (expected 'ok', got: $INTEGRITY_RESULT)"
    log "SQLite integrity check: ok"

    tar -czf "${DEST}/database.tar.gz" -C "$WORK/database" . \
        || fail "failed to compress database backup"
    DB_FILENAME="$(basename "$DB_PATH")"
    log "database backed up"
else
    log "WARNING: no database found at $DB_PATH — skipping"
fi

# ─── 2. Uploads ───────────────────────────────────────────────────────────────
UPLOADS_DIR="${BACKEND_DIR}/storage/uploads"
if [ -d "$UPLOADS_DIR" ] && [ -n "$(ls -A "$UPLOADS_DIR" 2>/dev/null)" ]; then
    log "backing up uploads"
    tar -czf "${DEST}/uploads.tar.gz" -C "$(dirname "$UPLOADS_DIR")" "$(basename "$UPLOADS_DIR")" \
        || fail "failed to compress uploads"
    log "uploads backed up"
else
    log "no uploads found — skipping"
fi

# ─── 3. Generated highlights ──────────────────────────────────────────────────
HIGHLIGHTS_DIR="${BACKEND_DIR}/storage/highlights"
if [ -d "$HIGHLIGHTS_DIR" ] && [ -n "$(ls -A "$HIGHLIGHTS_DIR" 2>/dev/null)" ]; then
    log "backing up generated highlights"
    tar -czf "${DEST}/highlights.tar.gz" -C "$(dirname "$HIGHLIGHTS_DIR")" "$(basename "$HIGHLIGHTS_DIR")" \
        || fail "failed to compress highlights"
    log "highlights backed up"
else
    log "no generated highlights found — skipping"
fi

# ─── 4. Configuration bundle: .env, nginx, systemd, SSL ──────────────────────
mkdir -p "$WORK/config"

ENV_PATH="${BACKEND_DIR}/.env"
if [ -f "$ENV_PATH" ]; then
    cp -p "$ENV_PATH" "$WORK/config/backend.env"
    log "included backend/.env"
else
    log "WARNING: no .env found at $ENV_PATH"
fi

NGINX_LIVE="/etc/nginx/sites-available/${NGINX_CONF_NAME}"
if [ -f "$NGINX_LIVE" ]; then
    mkdir -p "$WORK/config/nginx"
    cp -p "$NGINX_LIVE" "$WORK/config/nginx/"
    log "included nginx config: $NGINX_LIVE"
else
    log "WARNING: nginx config not found at $NGINX_LIVE"
fi

mkdir -p "$WORK/config/systemd"
shopt -s nullglob
UNIT_FILES=(/etc/systemd/system/${SYSTEMD_UNIT_GLOB})
if [ "${#UNIT_FILES[@]}" -gt 0 ]; then
    cp -p "${UNIT_FILES[@]}" "$WORK/config/systemd/"
    log "included ${#UNIT_FILES[@]} systemd unit file(s)"
else
    log "WARNING: no systemd unit files matched /etc/systemd/system/${SYSTEMD_UNIT_GLOB}"
fi
shopt -u nullglob

if [ -d "$LETSENCRYPT_DIR" ]; then
    cp -a "$LETSENCRYPT_DIR" "$WORK/config/letsencrypt" \
        || fail "failed to copy $LETSENCRYPT_DIR"
    log "included Let's Encrypt certificates"
else
    log "WARNING: no Let's Encrypt directory found at $LETSENCRYPT_DIR"
fi

tar -czf "${DEST}/config.tar.gz" -C "$WORK/config" . \
    || fail "failed to compress config bundle"
log "config bundle backed up (.env, nginx, systemd, SSL)"

# ─── 5. Verify archives ───────────────────────────────────────────────────────
for archive in "${DEST}"/*.tar.gz; do
    [ -e "$archive" ] || continue
    tar -tzf "$archive" >/dev/null || fail "archive integrity check failed: $archive"
    log "verified: $(basename "$archive")"
done

# ─── 6. Archive checksums (Revision 3) ───────────────────────────────────────
( cd "$DEST" && sha256sum -- *.tar.gz > checksums.sha256 ) \
    || fail "failed to generate checksums.sha256"
log "checksums.sha256 written"

# ─── 7. Manifest (Revision 1 / Revision 7 git metadata) ─────────────────────
GIT_COMMIT="Unknown"
GIT_TAG="Unknown"
if git -C "$APP_DIR" rev-parse --git-dir >/dev/null 2>&1; then
    GIT_COMMIT="$(git -C "$APP_DIR" rev-parse HEAD 2>/dev/null)" || GIT_COMMIT="Unknown"
    GIT_TAG="$(git -C "$APP_DIR" describe --tags 2>/dev/null)" || GIT_TAG="Unknown"
    [ -n "$GIT_COMMIT" ] || GIT_COMMIT="Unknown"
    [ -n "$GIT_TAG" ] || GIT_TAG="Unknown"
fi

UBUNTU_VERSION="Unknown"
if [ -f /etc/os-release ]; then
    UBUNTU_VERSION="$(. /etc/os-release && echo "${PRETTY_NAME:-Unknown}")"
fi

{
    echo "Backup Timestamp: ${TIMESTAMP}"
    echo "Hostname: $(hostname 2>/dev/null || echo Unknown)"
    echo "Ubuntu Version: ${UBUNTU_VERSION}"
    echo "Git Commit: ${GIT_COMMIT}"
    echo "Git Tag: ${GIT_TAG}"
    echo "Backup Format Version: ${BACKUP_FORMAT_VERSION}"
    echo "Backup Script Version: ${BACKUP_SCRIPT_VERSION}"
    echo "SQLite Database Filename: ${DB_FILENAME}"
    echo "Generated Archives:"
    for archive in "${DEST}"/*.tar.gz; do
        [ -e "$archive" ] || continue
        echo "  - $(basename "$archive")"
    done
    echo "SHA256 Checksum File: checksums.sha256"
} > "${DEST}/manifest.txt" || fail "failed to write manifest.txt"
log "manifest.txt written"

# ─── 8. Clean up temp working directory ──────────────────────────────────────
rm -rf "$WORK"

# ─── 9. Harden permissions (DB, .env, SSL keys and manifest are sensitive) ──
chmod 600 "${DEST}"/*.tar.gz "${DEST}/checksums.sha256" "${DEST}/manifest.txt" 2>/dev/null || true

# ─── 10. Retention cleanup — keep last N days, only touching timestamped dirs ─
log "applying retention policy: keep last ${RETENTION_DAYS} days"
find "$BACKUP_ROOT" -maxdepth 1 -mindepth 1 -type d \
    -name '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]_*' \
    -mtime "+${RETENTION_DAYS}" -print -exec rm -rf {} \; \
    | while read -r removed; do log "removed expired backup: $removed"; done

# ─── 11. Backup log retention (Revision 6) ───────────────────────────────────
find "$LOG_DIR" -maxdepth 1 -type f -name 'backup_*.log' \
    -mtime "+${LOG_RETENTION_DAYS}" -print -delete \
    | while read -r removed; do log "removed expired log: $removed"; done

echo "SUCCESS ${TIMESTAMP}: ${DEST}" > "$STATUS_FILE"
log "== backup completed successfully: ${DEST} =="
exit 0
