#!/usr/bin/env bash
# AGC-084 — Maintenance mode control for Vedzovi (AGC AI Highlight Creator)
#
# Run this ON THE VPS over SSH — that SSH session is the operator trust
# boundary. There is no public toggle endpoint and no admin auth surface.
#
#   bash scripts/maintenance.sh on
#   bash scripts/maintenance.sh off
#   bash scripts/maintenance.sh status
#   bash scripts/maintenance.sh drain
#
# Maintenance mode is a file-based sentinel flag. MaintenanceService
# (backend/app/services/maintenance_service.py) does a live, uncached
# existence check of this file on every request, so `on`/`off` take
# effect on the very next request — no backend restart required. The
# flag's state survives backend restarts (it's just a file), so
# maintenance stays ON across `on -> deploy -> restart -> off`.
#
# ─── The drain race (documented, not eliminated) ─────────────────────────
# A /pipeline/start request can read maintenance OFF immediately before
# this script creates the flag, then still reach JobService.create_job()
# after maintenance turns ON. `drain` does NOT make this race
# mathematically impossible — it is an MVP operational mitigation:
#   1. Wait a short grace period after the flag is confirmed ON, so any
#      request that read OFF just before the flag existed has time to
#      finish creating its job row.
#   2. Poll the actual active-job count (status IN ('pending','processing')
#      in the jobs table) and require it to read zero on 3 consecutive
#      checks, a few seconds apart, before declaring the system drained.
#   3. Reset the consecutive-zero counter the moment a nonzero count is
#      seen, so a job that slips in after an earlier zero reading does
#      not get missed.
#
# `drain` never kills jobs, modifies job rows, marks jobs failed, or
# refunds credits — that is unplanned-interruption recovery, which is
# AGC-085 scope, not this script's.

set -euo pipefail

# ─── Configuration (override via env vars if needed) ────────────────────────
APP_DIR="${APP_DIR:-/home/agc/agc-ai-highlight-creator}"
BACKEND_DIR="${BACKEND_DIR:-${APP_DIR}/backend}"

# Must match backend/app/config/config.py's MAINTENANCE_FLAG_PATH default
# (storage/maintenance.flag, relative to the backend's working directory —
# see docs/deploy.md's "Start the backend" step, which runs uvicorn from
# $BACKEND_DIR). Override MAINTENANCE_FLAG_PATH here if it was overridden
# there via the backend's .env.
MAINTENANCE_FLAG_PATH="${MAINTENANCE_FLAG_PATH:-${BACKEND_DIR}/storage/maintenance.flag}"

# Must match backup.sh's DB_PATH convention.
DB_PATH="${DB_PATH:-${BACKEND_DIR}/data/agc.db}"

DRAIN_GRACE_SECONDS="${DRAIN_GRACE_SECONDS:-3}"
DRAIN_POLL_INTERVAL_SECONDS="${DRAIN_POLL_INTERVAL_SECONDS:-2}"
DRAIN_REQUIRED_ZERO_CHECKS="${DRAIN_REQUIRED_ZERO_CHECKS:-3}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

usage() {
    echo "Usage: $0 {on|off|status|drain}" >&2
    exit 1
}

is_maintenance_on() {
    [ -f "$MAINTENANCE_FLAG_PATH" ]
}

# ─── on ───────────────────────────────────────────────────────────────────
cmd_on() {
    mkdir -p "$(dirname "$MAINTENANCE_FLAG_PATH")"

    if is_maintenance_on; then
        log "maintenance already ON (${MAINTENANCE_FLAG_PATH})"
    else
        : > "$MAINTENANCE_FLAG_PATH"
        log "maintenance turned ON (${MAINTENANCE_FLAG_PATH})"
    fi
}

# ─── off ──────────────────────────────────────────────────────────────────
cmd_off() {
    if is_maintenance_on; then
        rm -f "$MAINTENANCE_FLAG_PATH"
        log "maintenance turned OFF"
    else
        log "maintenance already OFF"
    fi
}

# ─── status ───────────────────────────────────────────────────────────────
cmd_status() {
    if is_maintenance_on; then
        echo "maintenance: ON"
    else
        echo "maintenance: OFF"
    fi
}

# ─── drain ────────────────────────────────────────────────────────────────
active_job_count() {
    [ -f "$DB_PATH" ] || { log "ERROR: database not found at ${DB_PATH}"; exit 1; }
    command -v sqlite3 >/dev/null 2>&1 || { log "ERROR: sqlite3 is required for drain"; exit 1; }

    sqlite3 "$DB_PATH" \
        "SELECT COUNT(*) FROM jobs WHERE status IN ('pending', 'processing');"
}

cmd_drain() {
    is_maintenance_on || {
        log "ERROR: maintenance must be ON before draining. Run: $0 on"
        exit 1
    }

    log "waiting ${DRAIN_GRACE_SECONDS}s grace period for pre-flag in-flight requests"
    sleep "$DRAIN_GRACE_SECONDS"

    consecutive_zero=0

    while [ "$consecutive_zero" -lt "$DRAIN_REQUIRED_ZERO_CHECKS" ]; do
        count="$(active_job_count)"

        if [ "$count" -eq 0 ]; then
            consecutive_zero=$((consecutive_zero + 1))
            log "active jobs: 0 (stable check ${consecutive_zero}/${DRAIN_REQUIRED_ZERO_CHECKS})"
        else
            if [ "$consecutive_zero" -gt 0 ]; then
                log "active jobs: ${count} — resetting stable-zero counter"
            else
                log "active jobs: ${count} — waiting"
            fi
            consecutive_zero=0
        fi

        if [ "$consecutive_zero" -lt "$DRAIN_REQUIRED_ZERO_CHECKS" ]; then
            sleep "$DRAIN_POLL_INTERVAL_SECONDS"
        fi
    done

    log "drain confirmed: 0 active jobs for ${DRAIN_REQUIRED_ZERO_CHECKS} consecutive checks"
}

case "${1:-}" in
    on) cmd_on ;;
    off) cmd_off ;;
    status) cmd_status ;;
    drain) cmd_drain ;;
    *) usage ;;
esac
