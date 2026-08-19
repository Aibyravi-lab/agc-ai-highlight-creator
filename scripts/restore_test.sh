#!/usr/bin/env bash
# VED-BACKUP-FIX — Non-destructive restore test for Vedzovi (AGC AI Highlight
# Creator) backups.
#
# Run this ON THE VPS (cron or manual):
#   sudo bash scripts/restore_test.sh
#
# What this proves that scripts/backup.sh's own checksum step and
# HealthService.verify_backup_archive_integrity() do NOT: that the latest
# backup's archives actually extract and that the SQLite database inside
# them passes PRAGMA integrity_check as a *restored* copy — not just that
# the compressed bytes match their checksum.
#
# This is a TEST, not a restore:
#   - identifies the latest valid backup under BACKUP_ROOT
#   - re-verifies checksums.sha256 (defense in depth; backup.sh/restore.sh
#     already do this too)
#   - extracts every archive into a throwaway directory under /tmp
#   - runs PRAGMA integrity_check against the extracted SQLite copy
#   - checks the extracted uploads/highlights/config archives landed the
#     files/directories backup.sh is expected to have written
#   - deletes the throwaway directory unconditionally (trap on EXIT)
#
# It NEVER touches, reads for writing, or overwrites any of:
#   backend/data/agc.db, backend/storage/, backend/.env, nginx, systemd,
#   Let's Encrypt certificates, or any running production service.
# It never invokes scripts/restore.sh.
#
# Result is written to BACKUP_ROOT/last_restore_test_status, the same
# pattern scripts/backup.sh uses for last_backup_status:
#   "SUCCESS <ts>: <backup_dir>"
#   "FAILED <ts>: <backup_dir_or_unknown> - <reason>"
# HealthService.get_restore_test_status() reads this file read-only.

set -euo pipefail

# ─── Configuration (override via env vars if needed) ────────────────────────
BACKUP_ROOT="${BACKUP_ROOT:-/opt/vedzovi-backups}"

TIMESTAMP="$(date +%Y-%m-%d_%H%M%S)"
STATUS_FILE="${BACKUP_ROOT}/last_restore_test_status"
BACKUP_DIR_NAME="unknown"
WORK=""

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

cleanup() {
    [ -n "$WORK" ] && rm -rf "$WORK" 2>/dev/null || true
}
trap cleanup EXIT

fail() {
    log "FAIL: $*"
    echo "FAILED ${TIMESTAMP}: ${BACKUP_DIR_NAME} - $*" > "$STATUS_FILE"
    exit 1
}

log "== restore test starting: ${TIMESTAMP} =="

# ─── 0. Locate the latest valid backup directory ────────────────────────────
[ -d "$BACKUP_ROOT" ] || fail "backup root not found: $BACKUP_ROOT"

LATEST_DIR="$(
    find "$BACKUP_ROOT" -maxdepth 1 -mindepth 1 -type d \
        -name '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]_*' \
    | sort -r | head -n1
)" || true
[ -n "$LATEST_DIR" ] || fail "no timestamped backup directories found under $BACKUP_ROOT"
BACKUP_DIR_NAME="$(basename "$LATEST_DIR")"
log "testing latest backup: $BACKUP_DIR_NAME"

# ─── 1. Re-verify archive checksums before extracting anything ─────────────
[ -f "$LATEST_DIR/checksums.sha256" ] || fail "checksums.sha256 not found in $LATEST_DIR"
command -v sha256sum >/dev/null 2>&1 || fail "sha256sum is required to verify checksums.sha256"
( cd "$LATEST_DIR" && sha256sum -c checksums.sha256 >/dev/null ) \
    || fail "checksum verification failed for $BACKUP_DIR_NAME — archive(s) corrupted or modified"
log "checksums verified"

# ─── 2. Extract into a throwaway directory under /tmp only ─────────────────
WORK="$(mktemp -d "${TMPDIR:-/tmp}/agc-restore-test.XXXXXX")"
log "working directory: $WORK (deleted on exit)"

# ─── 3. Database: extract + PRAGMA integrity_check on the restored copy ────
if [ -f "$LATEST_DIR/database.tar.gz" ]; then
    command -v sqlite3 >/dev/null 2>&1 || fail "sqlite3 is required to validate the restored database"
    mkdir -p "$WORK/database"
    tar -xzf "$LATEST_DIR/database.tar.gz" -C "$WORK/database" \
        || fail "failed to extract database.tar.gz"
    [ -f "$WORK/database/agc.db" ] || fail "database.tar.gz did not contain agc.db"

    INTEGRITY_RESULT="$(sqlite3 "$WORK/database/agc.db" "PRAGMA integrity_check;" 2>&1)"
    [ "$INTEGRITY_RESULT" = "ok" ] \
        || fail "PRAGMA integrity_check on restored database failed (expected 'ok', got: $INTEGRITY_RESULT)"
    log "database extracted and integrity_check: ok"
else
    log "WARNING: no database.tar.gz in $BACKUP_DIR_NAME — skipping database restore-test"
fi

# ─── 4. Uploads / highlights: extraction must succeed and land content ─────
for pair in "uploads.tar.gz:uploads" "highlights.tar.gz:highlights"; do
    archive_name="${pair%%:*}"
    top_dir="${pair##*:}"
    archive_path="$LATEST_DIR/$archive_name"

    if [ -f "$archive_path" ]; then
        extract_dir="$WORK/$top_dir"
        mkdir -p "$extract_dir"
        tar -xzf "$archive_path" -C "$extract_dir" \
            || fail "failed to extract $archive_name"
        [ -d "$extract_dir/$top_dir" ] \
            || fail "$archive_name did not extract the expected '$top_dir' directory"
        log "$archive_name extracted and validated"
    else
        log "no $archive_name in $BACKUP_DIR_NAME — skipping"
    fi
done

# ─── 5. Config bundle: extraction must succeed; report which parts landed ──
if [ -f "$LATEST_DIR/config.tar.gz" ]; then
    mkdir -p "$WORK/config"
    tar -xzf "$LATEST_DIR/config.tar.gz" -C "$WORK/config" \
        || fail "failed to extract config.tar.gz"

    FOUND_CONFIG_ITEMS=0
    [ -f "$WORK/config/backend.env" ] && FOUND_CONFIG_ITEMS=$((FOUND_CONFIG_ITEMS + 1))
    [ -d "$WORK/config/nginx" ] && FOUND_CONFIG_ITEMS=$((FOUND_CONFIG_ITEMS + 1))
    [ -d "$WORK/config/systemd" ] && FOUND_CONFIG_ITEMS=$((FOUND_CONFIG_ITEMS + 1))
    [ -d "$WORK/config/letsencrypt" ] && FOUND_CONFIG_ITEMS=$((FOUND_CONFIG_ITEMS + 1))
    [ "$FOUND_CONFIG_ITEMS" -gt 0 ] || fail "config.tar.gz extracted but contained none of the expected items (backend.env, nginx/, systemd/, letsencrypt/)"
    log "config bundle extracted and validated ($FOUND_CONFIG_ITEMS expected item(s) present)"
else
    log "WARNING: no config.tar.gz in $BACKUP_DIR_NAME — skipping config restore-test"
fi

# ─── 6. Manifest sanity check ────────────────────────────────────────────────
if [ -f "$LATEST_DIR/manifest.txt" ]; then
    [ -s "$LATEST_DIR/manifest.txt" ] || fail "manifest.txt exists but is empty"
    log "manifest.txt present"
else
    log "WARNING: no manifest.txt in $BACKUP_DIR_NAME"
fi

# ─── 7. Success ───────────────────────────────────────────────────────────────
echo "SUCCESS ${TIMESTAMP}: ${BACKUP_DIR_NAME}" > "$STATUS_FILE"
log "== restore test passed: $BACKUP_DIR_NAME =="
exit 0
