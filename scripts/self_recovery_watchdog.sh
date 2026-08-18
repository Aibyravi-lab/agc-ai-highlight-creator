#!/usr/bin/env bash
# VED-P1-018 — External self-recovery watchdog for Vedzovi (AGC AI Highlight Creator)
#
# Run every minute by systemd/vedzovi-self-recovery.timer as the agc user
# (see systemd/vedzovi-self-recovery.service). Can also be run manually:
#
#   bash scripts/self_recovery_watchdog.sh
#
# ─── Why this exists ──────────────────────────────────────────────────────
# HealthSchedulerService already evaluates health, but it runs INSIDE the
# backend process — if the backend process itself is down, that scheduler
# is down with it and cannot recover anything. This script is a tiny,
# independent (systemd timer + shell) watchdog that can restart the backend
# and frontend services from outside the backend process.
#
# ─── Recovery policy (deterministic, see docs/SELF_RECOVERY.md) ──────────
# AUTO-RECOVER ONLY:
#   A) Backend unavailable
#   B) Backend /health returns HTTP non-200
#   C) Frontend unavailable
# Everything else (SQLite integrity, disk, FFmpeg, payments, email, CPU,
# memory, AI pipeline failure rate, backups) is explicitly out of scope —
# this script never even checks for those conditions. HealthEngineService/
# AlertEngineService remain the sole owners of that detailed application
# health; this script only knows "is backend/frontend reachable".
#
# ─── Loop prevention ───────────────────────────────────────────────────────
#   - 3 consecutive failed checks required before any restart (no action on
#     a single transient network blip).
#   - A fresh re-check runs immediately before pulling the trigger, so a
#     service that recovered on its own between the threshold-crossing
#     check and now is never restarted needlessly.
#   - Minimum 15-minute cooldown between restarts of the same service.
#   - Maximum 2 automatic recoveries per service per rolling hour.
# State backing these rules is plain files under STATE_DIR — no SQLite.
#
# ─── Maintenance safety ────────────────────────────────────────────────────
# Reads the exact same file-based sentinel as scripts/maintenance.sh
# (MAINTENANCE_FLAG_PATH). If it is present, this script exits immediately
# and touches nothing — it must never fight an intentional maintenance
# operation.

set -uo pipefail
# Deliberately no `set -e`: curl/systemctl/sudo/python calls below are
# expected to fail sometimes (that is the condition being tested), and
# their exit codes are always checked explicitly. `set -e` combined with
# `var=$(cmd)` assignment statements would abort the script on the very
# failures it exists to detect.

# ─── Configuration (override via env vars — same convention as
#      scripts/maintenance.sh / scripts/backup.sh) ─────────────────────────
APP_DIR="${APP_DIR:-/home/agc/agc-ai-highlight-creator}"
BACKEND_DIR="${BACKEND_DIR:-${APP_DIR}/backend}"

# Must match backend/app/config/config.py's MAINTENANCE_FLAG_PATH default,
# and scripts/maintenance.sh's own default — same sentinel, same file.
MAINTENANCE_FLAG_PATH="${MAINTENANCE_FLAG_PATH:-${BACKEND_DIR}/storage/maintenance.flag}"

BACKEND_HEALTH_URL="${BACKEND_HEALTH_URL:-https://api.vedzovi.com/health}"
FRONTEND_URL="${FRONTEND_URL:-https://vedzovi.com/}"

BACKEND_SERVICE_UNIT="${BACKEND_SERVICE_UNIT:-agc-backend.service}"
FRONTEND_SERVICE_UNIT="${FRONTEND_SERVICE_UNIT:-agc-frontend.service}"

RECOVERY_FAILURE_THRESHOLD="${RECOVERY_FAILURE_THRESHOLD:-3}"
RECOVERY_COOLDOWN_SECONDS="${RECOVERY_COOLDOWN_SECONDS:-900}"
RECOVERY_MAX_ATTEMPTS_PER_HOUR="${RECOVERY_MAX_ATTEMPTS_PER_HOUR:-2}"
HEALTH_TIMEOUT_SECONDS="${HEALTH_TIMEOUT_SECONDS:-10}"
VERIFY_WAIT_SECONDS="${VERIFY_WAIT_SECONDS:-10}"

# Recovery state (loop-prevention counters) — plain files, not SQLite, per
# VED-P1-018 §5. Never put this under the app's own storage/ tree so a bad
# `scripts/restore.sh` run can never clobber watchdog state or vice versa.
STATE_DIR="${STATE_DIR:-/var/lib/vedzovi-recovery}"

# Best-effort bridge into the existing AlertEngineService/monitoring_alerts
# table (VED-P1-002) — see backend/scripts/record_recovery_alert.py. Never
# required for the recovery logic itself to function.
VENV_PYTHON="${VENV_PYTHON:-${APP_DIR}/venv/bin/python}"
RECORD_ALERT_SCRIPT="${RECORD_ALERT_SCRIPT:-${BACKEND_DIR}/scripts/record_recovery_alert.py}"

# ─── Logging (journald captures this service's stdout automatically) ──────
log() {
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $*"
}

# ─── Lock: prevent overlapping runs (VED-P1-018 §4) ────────────────────────
# `mkdir` is atomic on every POSIX filesystem, which makes it a portable,
# dependency-free equivalent of flock for a script that only needs to
# exclude a second copy of itself — no util-linux dependency required.
LOCK_DIR="${STATE_DIR}/watchdog.lock.d"
LOCK_ACQUIRED=0

release_lock() {
    if [ "$LOCK_ACQUIRED" -eq 1 ]; then
        rmdir "$LOCK_DIR" 2>/dev/null || true
    fi
}

acquire_lock() {
    mkdir -p "$STATE_DIR" 2>/dev/null || true
    if mkdir "$LOCK_DIR" 2>/dev/null; then
        LOCK_ACQUIRED=1
        trap release_lock EXIT
        return 0
    fi
    return 1
}

# ─── Maintenance sentinel (VED-P1-018 §6) ──────────────────────────────────
is_maintenance_on() {
    [ -f "$MAINTENANCE_FLAG_PATH" ]
}

# ─── Reachability checks ────────────────────────────────────────────────────
# Split out as functions (not inlined) so tests can shadow `curl` on PATH
# with a mock and exercise every branch without touching the network.
check_backend() {
    local code status
    code=$(curl -sS -o /dev/null -w '%{http_code}' -m "$HEALTH_TIMEOUT_SECONDS" "$BACKEND_HEALTH_URL" 2>/dev/null)
    status=$?
    [ "$status" -eq 0 ] && [ "$code" = "200" ]
}

check_frontend() {
    local code status
    code=$(curl -sS -o /dev/null -w '%{http_code}' -m "$HEALTH_TIMEOUT_SECONDS" "$FRONTEND_URL" 2>/dev/null)
    status=$?
    [ "$status" -eq 0 ] && [ -n "$code" ] && [ "$code" -ge 100 ] && [ "$code" -lt 500 ]
}

# ─── Privileged systemctl actions (VED-P1-018 §3) ──────────────────────────
# Runs as root only for these two exact operations, via a tightly scoped
# sudoers rule (systemd/vedzovi-self-recovery.sudoers) when not already
# root — never broad/unrestricted sudo.
run_privileged() {
    if [ "$(id -u)" -eq 0 ]; then
        "$@"
    else
        sudo -n "$@"
    fi
}

restart_unit() {
    run_privileged systemctl restart "$1"
}

unit_is_active() {
    run_privileged systemctl is-active "$1" 2>/dev/null || true
}

# ─── Rolling-hour attempt tracking (loop prevention, VED-P1-018 §5) ────────
attempts_log_file() {
    echo "${STATE_DIR}/${1}_recovery_attempts.log"
}

record_attempt() {
    local service="$1" now="$2"
    echo "$now" >> "$(attempts_log_file "$service")"
}

# Prints the count of attempts within the last rolling hour, and prunes
# older entries from the log file as a side effect (keeps it small forever).
count_attempts_last_hour() {
    local service="$1" now cutoff file tmp ts count=0
    now=$(date +%s)
    cutoff=$((now - 3600))
    file="$(attempts_log_file "$service")"

    [ -f "$file" ] || { echo 0; return; }

    tmp="${file}.tmp.$$"
    : > "$tmp"
    while IFS= read -r ts; do
        [ -n "$ts" ] || continue
        if [ "$ts" -ge "$cutoff" ] 2>/dev/null; then
            echo "$ts" >> "$tmp"
            count=$((count + 1))
        fi
    done < "$file"
    mv "$tmp" "$file"

    echo "$count"
}

# ─── AlertEngineService bridge (VED-P1-018 §8) — best-effort, never fatal ──
record_alert_helper() {
    local service="$1" message="$2"

    if [ ! -x "$VENV_PYTHON" ] || [ ! -f "$RECORD_ALERT_SCRIPT" ]; then
        log "SELF_RECOVERY_ALERT_SKIPPED service=${service} reason=python_unavailable"
        return
    fi

    if ( cd "$BACKEND_DIR" && "$VENV_PYTHON" "$RECORD_ALERT_SCRIPT" open "$service" "$message" ) >/dev/null 2>&1; then
        log "SELF_RECOVERY_ALERT_RECORDED service=${service}"
    else
        log "SELF_RECOVERY_ALERT_FAILED service=${service}"
    fi
}

resolve_alert_helper() {
    local service="$1"

    if [ ! -x "$VENV_PYTHON" ] || [ ! -f "$RECORD_ALERT_SCRIPT" ]; then
        return
    fi

    ( cd "$BACKEND_DIR" && "$VENV_PYTHON" "$RECORD_ALERT_SCRIPT" resolve "$service" ) >/dev/null 2>&1 || true
}

# ─── Recovery state (VED-P1-018 §5): consecutive failures, last recovery
#      timestamp, last check/action results — plain KEY=VALUE file. ────────
STATE_FILE="${STATE_DIR}/state.env"

BACKEND_CONSEC_FAILURES=0
FRONTEND_CONSEC_FAILURES=0
BACKEND_LAST_RECOVERY_TS=0
FRONTEND_LAST_RECOVERY_TS=0
LAST_BACKEND_RESULT="unknown"
LAST_FRONTEND_RESULT="unknown"
LAST_ACTION="none"
LAST_ACTION_RESULT="none"
LAST_ACTION_TS=0

load_state() {
    # shellcheck disable=SC1090
    [ -f "$STATE_FILE" ] && source "$STATE_FILE"
    return 0
}

save_state() {
    mkdir -p "$STATE_DIR"
    cat > "$STATE_FILE" <<EOF
BACKEND_CONSEC_FAILURES=${BACKEND_CONSEC_FAILURES}
FRONTEND_CONSEC_FAILURES=${FRONTEND_CONSEC_FAILURES}
BACKEND_LAST_RECOVERY_TS=${BACKEND_LAST_RECOVERY_TS}
FRONTEND_LAST_RECOVERY_TS=${FRONTEND_LAST_RECOVERY_TS}
LAST_BACKEND_RESULT=${LAST_BACKEND_RESULT}
LAST_FRONTEND_RESULT=${LAST_FRONTEND_RESULT}
LAST_ACTION=${LAST_ACTION}
LAST_ACTION_RESULT=${LAST_ACTION_RESULT}
LAST_ACTION_TS=${LAST_ACTION_TS}
EOF
}

# ─── Core policy: evaluate one service, recover if the policy allows it ───
# $1 = service name ("backend" | "frontend")
# $2 = check function name (check_backend | check_frontend)
# $3 = systemd unit name
ACTION_TAKEN_THIS_RUN=0

evaluate_and_recover() {
    local service="$1" check_fn="$2" unit="$3"
    local upper consec_var result_var last_recovery_var
    upper=$(echo "$service" | tr '[:lower:]' '[:upper:]')
    consec_var="${upper}_CONSEC_FAILURES"
    result_var="LAST_${upper}_RESULT"
    last_recovery_var="${upper}_LAST_RECOVERY_TS"

    if "$check_fn"; then
        printf -v "$consec_var" '%d' 0
        printf -v "$result_var" '%s' "healthy"
        return
    fi

    local consec
    consec=$(( ${!consec_var} + 1 ))
    printf -v "$consec_var" '%d' "$consec"
    printf -v "$result_var" '%s' "failed"

    log "SELF_RECOVERY_${upper}_FAILURE threshold=${consec}/${RECOVERY_FAILURE_THRESHOLD}"

    if [ "$consec" -lt "$RECOVERY_FAILURE_THRESHOLD" ]; then
        return
    fi

    # Verify the failure is actually still happening right now (VED-P1-018
    # §2 step 5) — a fresh, immediate re-check, not the stale threshold
    # count, is what decides whether we actually restart anything.
    if "$check_fn"; then
        log "SELF_RECOVERY_RESULT ${service}_recovered_before_restart"
        printf -v "$consec_var" '%d' 0
        printf -v "$result_var" '%s' "healthy"
        return
    fi

    local now last_recovery
    now=$(date +%s)
    last_recovery="${!last_recovery_var}"

    if [ "$last_recovery" -gt 0 ] && [ $((now - last_recovery)) -lt "$RECOVERY_COOLDOWN_SECONDS" ]; then
        log "SELF_RECOVERY_COOLDOWN service=${service} remaining_seconds=$((RECOVERY_COOLDOWN_SECONDS - (now - last_recovery)))"
        LAST_ACTION_RESULT="skipped_cooldown"
        ACTION_TAKEN_THIS_RUN=1
        return
    fi

    local attempts_this_hour
    attempts_this_hour=$(count_attempts_last_hour "$service")

    if [ "$attempts_this_hour" -ge "$RECOVERY_MAX_ATTEMPTS_PER_HOUR" ]; then
        log "SELF_RECOVERY_LIMIT_REACHED service=${service} attempts=${attempts_this_hour}/${RECOVERY_MAX_ATTEMPTS_PER_HOUR} CRITICAL recovery-exhausted"
        LAST_ACTION_RESULT="limit_reached"
        ACTION_TAKEN_THIS_RUN=1
        record_alert_helper "$service" "Automatic recovery exhausted: ${attempts_this_hour} restart(s) of ${unit} in the past hour with no sustained recovery."
        return
    fi

    local active_state
    active_state=$(unit_is_active "$unit")

    log "SELF_RECOVERY_ACTION ${service}_restart"
    restart_unit "$unit"
    record_attempt "$service" "$now"
    printf -v "$last_recovery_var" '%d' "$now"
    LAST_ACTION="${service}_restart"
    LAST_ACTION_TS="$now"
    ACTION_TAKEN_THIS_RUN=1

    sleep "$VERIFY_WAIT_SECONDS"

    if "$check_fn"; then
        log "SELF_RECOVERY_RESULT ${service}_recovered"
        LAST_ACTION_RESULT="success"
        printf -v "$consec_var" '%d' 0
        printf -v "$result_var" '%s' "healthy"
        resolve_alert_helper "$service"
    else
        log "SELF_RECOVERY_RESULT ${service}_recovery_failed"
        LAST_ACTION_RESULT="failure"
        record_alert_helper "$service" "Restart of ${unit} did not restore health within ${VERIFY_WAIT_SECONDS}s (systemd unit state: ${active_state:-unknown})."
    fi
}

main() {
    if ! acquire_lock; then
        log "SELF_RECOVERY_SKIPPED_LOCKED"
        exit 0
    fi

    if is_maintenance_on; then
        log "SELF_RECOVERY_SKIPPED_MAINTENANCE"
        exit 0
    fi

    load_state

    evaluate_and_recover "backend" check_backend "$BACKEND_SERVICE_UNIT"
    evaluate_and_recover "frontend" check_frontend "$FRONTEND_SERVICE_UNIT"

    if [ "$ACTION_TAKEN_THIS_RUN" -eq 0 ] && [ "$LAST_BACKEND_RESULT" = "healthy" ] && [ "$LAST_FRONTEND_RESULT" = "healthy" ]; then
        log "SELF_RECOVERY_HEALTHY"
    fi

    save_state
}

# Allow this file to be sourced (for tests) without executing main().
if [ "${SELF_RECOVERY_WATCHDOG_SOURCED:-0}" != "1" ]; then
    main "$@"
fi
