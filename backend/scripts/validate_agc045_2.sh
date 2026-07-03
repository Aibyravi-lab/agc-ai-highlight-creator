#!/usr/bin/env bash
# AGC-045.2 production validation — Deployment Hardening
# Run this ON THE VPS (agc-vps):
#   ssh agc-vps
#   sudo bash /home/agc/agc-ai-highlight-creator/backend/scripts/validate_agc045_2.sh
#
# Scope: systemd services, restart recovery, graceful shutdown, nginx routing,
# health endpoints, permissions, disk usage, log rotation, startup behavior.
# Does NOT repeat AGC-045.1 (worker pool / concurrent inference).
#
# Two tiers of test:
#   - Safe checks (systemd state, permissions, disk usage, nginx, health,
#     graceful shutdown + startup behavior via a normal `systemctl restart`)
#     run by default.
#   - The crash-recovery test forcibly `kill -9`s the live backend process to
#     prove restart recovery works. It briefly interrupts real traffic and is
#     gated behind RUN_CRASH_TEST=yes — it will NOT run unless you opt in.

set -uo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
SERVICE_NAME="${SERVICE_NAME:-agc-backend}"
UNIT_PATH="/etc/systemd/system/${SERVICE_NAME}.service"
REPO_UNIT="${REPO_UNIT:-/home/agc/agc-ai-highlight-creator/backend/scripts/agc-backend.service}"
APP_DIR="${APP_DIR:-/home/agc/agc-ai-highlight-creator/backend}"
TEST_VIDEO="${TEST_VIDEO:-/home/agc/agc-ai-highlight-creator/backend/storage/uploads/76a3a7b3_valid_87d52c22.mp4}"
DOMAIN="${DOMAIN:-highlightai.in}"
API_DOMAIN="${API_DOMAIN:-api.highlightai.in}"
RUN_CRASH_TEST="${RUN_CRASH_TEST:-no}"
SHUTDOWN_POLL_INTERVAL="${SHUTDOWN_POLL_INTERVAL:-2}"
SHUTDOWN_HEALTH_TIMEOUT="${SHUTDOWN_HEALTH_TIMEOUT:-30}"
SHUTDOWN_JOB_TIMEOUT="${SHUTDOWN_JOB_TIMEOUT:-120}"
STAMP=$(date +%s)

command -v jq >/dev/null || { echo "jq is required"; exit 1; }

FAILS=0
note_fail() { echo "  FAIL: $1"; FAILS=$((FAILS+1)); }

# Directives that actually affect runtime behavior. Comments, Description,
# Type, Group, Environment/PATH formatting, KillSignal, and TimeoutStopSec
# are deployment style/tuning choices, not functional mismatches, so they
# are intentionally excluded from this comparison.
UNIT_FUNCTIONAL_KEYS="ExecStart WorkingDirectory User Restart"

unit_directive() {
  grep -E "^${2}=" "$1" 2>/dev/null | tail -1 | cut -d'=' -f2- | sed 's/[[:space:]]*$//'
}

echo "================================================================"
echo "1. SYSTEMD SERVICE"
echo "================================================================"
if [ -f "$UNIT_PATH" ]; then
  echo "  unit file present: $UNIT_PATH"
  if [ -f "$REPO_UNIT" ]; then
    UNIT_MISMATCH=0
    for KEY in $UNIT_FUNCTIONAL_KEYS; do
      INSTALLED_VAL=$(unit_directive "$UNIT_PATH" "$KEY")
      REPO_VAL=$(unit_directive "$REPO_UNIT" "$KEY")
      if [ "$INSTALLED_VAL" != "$REPO_VAL" ]; then
        note_fail "systemd $KEY differs — installed: '$INSTALLED_VAL' vs repo: '$REPO_VAL'"
        UNIT_MISMATCH=1
      fi
    done
    if [ "$UNIT_MISMATCH" -eq 0 ]; then
      echo "  OK: installed unit is functionally equivalent to repo copy ($UNIT_FUNCTIONAL_KEYS match)"
    fi
  else
    echo "  WARN: repo unit not found at $REPO_UNIT, skipping comparison"
  fi
else
  note_fail "$UNIT_PATH not found — service is not installed from the repo unit"
fi

systemctl is-enabled "$SERVICE_NAME" >/dev/null 2>&1 && echo "  OK: enabled (survives reboot)" || note_fail "$SERVICE_NAME not enabled"
systemctl is-active "$SERVICE_NAME" >/dev/null 2>&1 && echo "  OK: active" || note_fail "$SERVICE_NAME not active"

echo
echo "================================================================"
echo "2. PERMISSIONS"
echo "================================================================"
for d in "$APP_DIR/storage/uploads" "$APP_DIR/storage/jobs" "$APP_DIR/logs"; do
  if [ -d "$d" ]; then
    PERMS=$(stat -c "%U:%G %a" "$d")
    echo "  $d -> $PERMS"
    MODE=$(stat -c "%a" "$d")
    if [ "${MODE: -1}" = "7" ] || [ "${MODE: -1}" = "6" ] || [ "${MODE: -1}" = "2" ]; then
      note_fail "$d is world-writable (mode $MODE)"
    fi
  else
    echo "  $d does not exist yet (not necessarily a problem pre-first-run)"
  fi
done

if [ -f "$APP_DIR/.env" ]; then
  ENV_PERMS=$(stat -c "%U:%G %a" "$APP_DIR/.env")
  echo "  $APP_DIR/.env -> $ENV_PERMS"
  ENV_MODE=$(stat -c "%a" "$APP_DIR/.env")
  OTHER_BIT="${ENV_MODE: -1}"
  if [ "$OTHER_BIT" != "0" ]; then
    note_fail ".env is readable by 'other' (mode $ENV_MODE) — should be 600 or 640"
  else
    echo "  OK: .env not world-readable"
  fi
else
  note_fail "$APP_DIR/.env not found"
fi

echo "  -- network exposure: backend binds 0.0.0.0:8000, must be firewalled --"
if command -v ufw >/dev/null 2>&1; then
  UFW_STATUS=$(sudo ufw status 2>/dev/null)
  if echo "$UFW_STATUS" | grep -q "^Status: active"; then
    if echo "$UFW_STATUS" | grep -qE "8000/tcp\s+DENY"; then
      echo "  OK: ufw active and port 8000/tcp is denied externally"
    else
      note_fail "ufw is active but no explicit DENY rule for 8000/tcp found — backend on 0.0.0.0:8000 may be publicly reachable"
    fi
  else
    note_fail "ufw is not active — backend on 0.0.0.0:8000 is likely publicly reachable, bypassing nginx entirely"
  fi
else
  echo "  WARN: ufw not found, cannot verify port 8000 is firewalled — check manually"
fi

echo
echo "================================================================"
echo "3. DISK USAGE"
echo "================================================================"
df -h "$APP_DIR" 2>/dev/null
echo "  -- directory sizes --"
for d in "$APP_DIR/storage/uploads" "$APP_DIR/storage/jobs" "$APP_DIR/storage/frames" "$APP_DIR/storage/thumbnails" "$APP_DIR/logs"; do
  [ -d "$d" ] && du -sh "$d" 2>/dev/null
done

if [ -f "$APP_DIR/logs/agc.log" ]; then
  LOG_SIZE_MB=$(du -m "$APP_DIR/logs/agc.log" | cut -f1)
  echo "  logs/agc.log size: ${LOG_SIZE_MB}MB (no log rotation configured yet — flag only, not a hard fail)"
  if [ "$LOG_SIZE_MB" -gt 500 ]; then
    note_fail "logs/agc.log is ${LOG_SIZE_MB}MB with no rotation in place — this needs addressing, not just flagging"
  fi
fi

MOUNT_USE=$(df -h "$APP_DIR" | tail -1 | awk '{print $5}' | tr -d '%')
if [ "$MOUNT_USE" -ge 85 ]; then
  note_fail "disk usage on $APP_DIR's mount is ${MOUNT_USE}% — approaching capacity"
else
  echo "  OK: disk usage at ${MOUNT_USE}%"
fi

echo
echo "================================================================"
echo "4. NGINX ROUTING"
echo "================================================================"
sudo nginx -t 2>&1 | sed 's/^/  /'
echo "  -- checklist from docs/deploy.md section 8 --"
check_status() {
  local desc="$1" url="$2" expect="$3"
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" "$url")
  if [ "$code" = "$expect" ]; then
    echo "  OK: $desc -> $code"
  else
    note_fail "$desc -> got $code, expected $expect ($url)"
  fi
}
check_status "https://$DOMAIN"          "https://$DOMAIN"          "200"
check_status "https://www.$DOMAIN"      "https://www.$DOMAIN"      "301"
check_status "https://$API_DOMAIN/health" "https://$API_DOMAIN/health" "200"
check_status "http://$DOMAIN (redirect)"  "http://$DOMAIN"           "301"
check_status "http://$API_DOMAIN (redirect)" "http://$API_DOMAIN"    "301"

echo
echo "================================================================"
echo "5. HEALTH ENDPOINTS"
echo "================================================================"
curl -sf "$BASE_URL/health" | jq . || note_fail "/health did not return 200"
curl -sf "$BASE_URL/ready"  | jq . || note_fail "/ready did not return 200"
curl -sf "$BASE_URL/metrics" | jq . || note_fail "/metrics did not return 200"

echo
echo "================================================================"
echo "6. GRACEFUL SHUTDOWN + STARTUP BEHAVIOR (via systemctl restart)"
echo "================================================================"
echo "  Submitting a short job, then issuing a normal 'systemctl restart'"
echo "  (SIGTERM, not kill -9) — job should be allowed to finish before"
echo "  the old process exits, and fresh startup logs should follow."

EMAIL="agc045-2-val-${STAMP}@example.com"
REG_RESP=$(curl -sf -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"val-shutdown\",\"email\":\"$EMAIL\",\"password\":\"ValidatePass123\"}")
TOKEN=$(echo "$REG_RESP" | jq -r .access_token)

if [ -f "$TEST_VIDEO" ] && [ -n "$TOKEN" ] && [ "$TOKEN" != "null" ]; then
  UPLOAD_RESP=$(curl -sf -X POST "$BASE_URL/upload/" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@${TEST_VIDEO};filename=val_shutdown_${STAMP}.mp4")
  VPATH=$(echo "$UPLOAD_RESP" | jq -r .location)

  START_RESP=$(curl -s -X POST "$BASE_URL/pipeline/start?video_path=${VPATH}" \
    -H "Authorization: Bearer $TOKEN")
  JID=$(echo "$START_RESP" | jq -r .job_id)
  echo "  submitted job $JID"

  sleep 2
  PRE_RESTART_PID=$(systemctl show -p MainPID --value "$SERVICE_NAME" 2>/dev/null)
  RESTART_TS=$(date +%s)
  sudo systemctl restart "$SERVICE_NAME"

  echo "  waiting for backend to come back up with a new PID (timeout ${SHUTDOWN_HEALTH_TIMEOUT}s)..."
  NEW_PID=""
  BACKEND_UP=0
  ELAPSED=0
  while [ "$ELAPSED" -lt "$SHUTDOWN_HEALTH_TIMEOUT" ]; do
    CURRENT_PID=$(systemctl show -p MainPID --value "$SERVICE_NAME" 2>/dev/null)
    if curl -sf "$BASE_URL/health" >/dev/null 2>&1 \
      && [ -n "$CURRENT_PID" ] && [ "$CURRENT_PID" != "0" ] \
      && [ "$CURRENT_PID" != "$PRE_RESTART_PID" ]; then
      NEW_PID="$CURRENT_PID"
      BACKEND_UP=1
      break
    fi
    sleep "$SHUTDOWN_POLL_INTERVAL"
    ELAPSED=$((ELAPSED + SHUTDOWN_POLL_INTERVAL))
  done

  if [ "$BACKEND_UP" -eq 1 ]; then
    echo "  OK: backend healthy after restart (PID $PRE_RESTART_PID -> $NEW_PID)"
  else
    note_fail "backend did not become healthy with a new PID within ${SHUTDOWN_HEALTH_TIMEOUT}s (PID stuck at $PRE_RESTART_PID) — restart may not have taken effect"
  fi

  echo "  -- journalctl around restart (shutdown/startup log lines) --"
  RESTART_LOG=$(sudo journalctl -u "$SERVICE_NAME" --since "@$RESTART_TS" 2>/dev/null)
  echo "$RESTART_LOG" | grep -iE "shutdown initiated|Startup Validation Passed|Startup Validation Completed|WARNING|Reconciled" | sed 's/^/  /'

  if echo "$RESTART_LOG" | grep -q "JWT_SECRET_KEY not set"; then
    note_fail "JWT_SECRET_KEY warning reappeared on this restart — persistent secret is not being read consistently, sessions will not survive restarts"
  else
    echo "  OK: no JWT_SECRET_KEY warning on this restart"
  fi

  if [ -n "$JID" ] && [ "$JID" != "null" ]; then
    echo "  polling job $JID for a terminal status (timeout ${SHUTDOWN_JOB_TIMEOUT}s)..."
    FINAL_STATUS=""
    JOB_HTTP_CODE=""
    JOB_BODY=""
    ELAPSED=0
    while [ "$ELAPSED" -lt "$SHUTDOWN_JOB_TIMEOUT" ]; do
      JOB_RESP=$(curl -s -w '\n%{http_code}' "$BASE_URL/pipeline/job/$JID" -H "Authorization: Bearer $TOKEN")
      JOB_HTTP_CODE=$(echo "$JOB_RESP" | tail -1)
      JOB_BODY=$(echo "$JOB_RESP" | sed '$d')
      if [ "$JOB_HTTP_CODE" = "200" ]; then
        FINAL_STATUS=$(echo "$JOB_BODY" | jq -r '.data.status' 2>/dev/null)
      else
        FINAL_STATUS=""
      fi
      if [ "$FINAL_STATUS" = "completed" ] || [ "$FINAL_STATUS" = "failed" ]; then
        break
      fi
      sleep "$SHUTDOWN_POLL_INTERVAL"
      ELAPSED=$((ELAPSED + SHUTDOWN_POLL_INTERVAL))
    done

    echo "  job status after graceful restart: $FINAL_STATUS (after ${ELAPSED}s, last HTTP $JOB_HTTP_CODE)"
    if [ "$FINAL_STATUS" = "completed" ]; then
      echo "  OK: in-flight job completed cleanly across a graceful restart"
    elif [ "$FINAL_STATUS" = "failed" ]; then
      note_fail "job was cut off by restart instead of draining gracefully (status=failed) — check TimeoutStopSec vs job duration"
    elif [ -z "$FINAL_STATUS" ]; then
      note_fail "could not read job status after restart — last response was HTTP $JOB_HTTP_CODE: $JOB_BODY (if 401/403, the pre-restart auth token was rejected post-restart — check whether JWT_SECRET_KEY is fixed in .env rather than falling back to a per-process random default)"
    else
      note_fail "job did not reach a terminal state within ${SHUTDOWN_JOB_TIMEOUT}s (status=$FINAL_STATUS) — investigate a genuinely stuck job or raise SHUTDOWN_JOB_TIMEOUT"
    fi
  fi
else
  echo "  SKIPPED: test video or registration unavailable"
fi

echo
echo "================================================================"
echo "7. RESTART RECOVERY (crash simulation) — opt-in"
echo "================================================================"
if [ "$RUN_CRASH_TEST" != "yes" ]; then
  echo "  SKIPPED: set RUN_CRASH_TEST=yes to run this. It force-kills the"
  echo "  live backend process (kill -9) to prove systemd + job"
  echo "  reconciliation recover cleanly. This briefly interrupts real"
  echo "  traffic — only run it with awareness of that impact."
else
  EMAIL2="agc045-2-crash-${STAMP}@example.com"
  REG2=$(curl -sf -X POST "$BASE_URL/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"val-crash\",\"email\":\"$EMAIL2\",\"password\":\"ValidatePass123\"}")
  TOKEN2=$(echo "$REG2" | jq -r .access_token)

  UPLOAD2=$(curl -sf -X POST "$BASE_URL/upload/" \
    -H "Authorization: Bearer $TOKEN2" \
    -F "file=@${TEST_VIDEO};filename=val_crash_${STAMP}.mp4")
  VPATH2=$(echo "$UPLOAD2" | jq -r .location)

  START2=$(curl -s -X POST "$BASE_URL/pipeline/start?video_path=${VPATH2}" \
    -H "Authorization: Bearer $TOKEN2")
  JID2=$(echo "$START2" | jq -r .job_id)
  echo "  submitted job $JID2, killing process in 1s..."
  sleep 1

  MAIN_PID=$(systemctl show -p MainPID --value "$SERVICE_NAME")
  if [ -n "$MAIN_PID" ] && [ "$MAIN_PID" != "0" ]; then
    sudo kill -9 "$MAIN_PID"
    echo "  sent kill -9 to PID $MAIN_PID"
  else
    note_fail "could not resolve MainPID for $SERVICE_NAME"
  fi

  echo "  waiting for systemd to auto-restart (Restart=on-failure)..."
  for i in $(seq 1 30); do
    curl -sf "$BASE_URL/health" >/dev/null 2>&1 && break
    sleep 1
  done
  if curl -sf "$BASE_URL/health" >/dev/null 2>&1; then
    echo "  OK: backend recovered after crash"
  else
    note_fail "backend did not recover after kill -9 within 30s"
  fi

  sleep 2
  RECONCILED_STATUS=$(curl -sf "$BASE_URL/pipeline/job/$JID2" -H "Authorization: Bearer $TOKEN2" | jq -r '.data.status')
  RECONCILED_ERROR=$(curl -sf "$BASE_URL/pipeline/job/$JID2" -H "Authorization: Bearer $TOKEN2" | jq -r '.data.error')
  echo "  killed job status: $RECONCILED_STATUS (error: $RECONCILED_ERROR)"
  if [ "$RECONCILED_STATUS" = "failed" ]; then
    echo "  OK: orphaned job was reconciled to failed, not left stuck"
  else
    note_fail "killed job is still '$RECONCILED_STATUS' — orphan reconciliation did not run"
  fi

  RETRY_RESP=$(curl -s -X POST "$BASE_URL/pipeline/start?video_path=${VPATH2}" \
    -H "Authorization: Bearer $TOKEN2")
  RETRY_JID=$(echo "$RETRY_RESP" | jq -r '.job_id // empty')
  if [ -n "$RETRY_JID" ]; then
    echo "  OK: user can submit a new job after crash (no permanent slot leak)"
  else
    note_fail "user could not submit a new job after crash: $RETRY_RESP"
  fi
fi

echo
echo "================================================================"
echo "SUMMARY"
echo "================================================================"
if [ "$FAILS" -eq 0 ]; then
  echo "RESULT: PASS (0 failures)"
else
  echo "RESULT: FAIL ($FAILS failure(s) above)"
fi
