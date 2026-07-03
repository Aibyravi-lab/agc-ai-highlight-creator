#!/usr/bin/env bash
# AGC-045.1 production re-validation
# Run this ON THE VPS (agc-vps), e.g.:
#   ssh agc-vps
#   bash /home/agc/agc-ai-highlight-creator/backend/scripts/validate_agc045_1.sh
#
# Scope (per AGC-045.1 re-validation request): worker pool behavior,
# concurrent AI inference stability, background job completion.
# Does NOT repeat the full smoke test.

set -uo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
SERVICE_NAME="${SERVICE_NAME:-agc-backend}"
TEST_VIDEO="${TEST_VIDEO:-/home/agc/agc-ai-highlight-creator/backend/storage/uploads/76a3a7b3_valid_87d52c22.mp4}"
NUM_USERS=3            # 3 users x 2 jobs = 6 jobs > MAX_CONCURRENT_JOBS (4) -> forces queuing
JOBS_PER_USER=2
POLL_INTERVAL=5
POLL_TIMEOUT=1200       # 20 min ceiling for all jobs to finish
STAMP=$(date +%s)

command -v jq >/dev/null || { echo "jq is required"; exit 1; }
[ -f "$TEST_VIDEO" ] || { echo "TEST_VIDEO not found at $TEST_VIDEO — set TEST_VIDEO=/path/to/clip.mp4"; exit 1; }

declare -a TOKENS
declare -a VIDEO_PATHS
declare -a JOB_IDS

echo "== 0. Pre-check: service + health =="
systemctl is-active "$SERVICE_NAME" || { echo "FAIL: $SERVICE_NAME not active"; exit 1; }
ps -eo pid,cmd | grep -c "[u]vicorn" | xargs -I{} echo "uvicorn process count: {}"
curl -sf "$BASE_URL/health" | jq . || { echo "FAIL: /health not OK"; exit 1; }

echo "== 1. Register $NUM_USERS test users and upload test video for each =="
for i in $(seq 1 "$NUM_USERS"); do
  EMAIL="agc045-val-${STAMP}-${i}@example.com"
  RESP=$(curl -sf -X POST "$BASE_URL/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"val-user-$i\",\"email\":\"$EMAIL\",\"password\":\"ValidatePass123\"}")
  TOKEN=$(echo "$RESP" | jq -r .access_token)
  TOKENS+=("$TOKEN")

  UPLOAD_RESP=$(curl -sf -X POST "$BASE_URL/upload/" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@${TEST_VIDEO};filename=val_${STAMP}_${i}.mp4")
  VPATH=$(echo "$UPLOAD_RESP" | jq -r .location)
  VIDEO_PATHS+=("$VPATH")
  echo "  user $i registered, uploaded -> $VPATH"
done

echo "== 2. Submit $((NUM_USERS*JOBS_PER_USER)) jobs (global pool caps at 4 workers) =="
for i in $(seq 0 $((NUM_USERS-1))); do
  for j in $(seq 1 "$JOBS_PER_USER"); do
    START_RESP=$(curl -s -X POST "$BASE_URL/pipeline/start?video_path=${VIDEO_PATHS[$i]}" \
      -H "Authorization: Bearer ${TOKENS[$i]}")
    JID=$(echo "$START_RESP" | jq -r .job_id)
    if [ "$JID" = "null" ] || [ -z "$JID" ]; then
      echo "  WARN user $((i+1)) job $j did not start: $START_RESP"
    else
      JOB_IDS+=("$JID:${TOKENS[$i]}")
      echo "  user $((i+1)) job $j -> $JID"
    fi
  done
done

TOTAL_JOBS=${#JOB_IDS[@]}
echo "Submitted $TOTAL_JOBS jobs total."

echo "== 3. Poll job status + /metrics until drained (queue behavior / starvation check) =="
START_TS=$(date +%s)
declare -A DONE
while true; do
  ALL_DONE=1
  for entry in "${JOB_IDS[@]}"; do
    JID="${entry%%:*}"
    TOK="${entry#*:}"
    [ -n "${DONE[$JID]:-}" ] && continue
    STATUS_RESP=$(curl -sf "$BASE_URL/pipeline/job/$JID" -H "Authorization: Bearer $TOK")
    STATUS=$(echo "$STATUS_RESP" | jq -r '.data.status')
    PROGRESS=$(echo "$STATUS_RESP" | jq -r '.data.progress')
    if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
      DONE[$JID]="$STATUS:$PROGRESS"
      echo "  [$(date +%H:%M:%S)] $JID -> $STATUS (progress=$PROGRESS)"
    else
      ALL_DONE=0
    fi
  done

  METRICS=$(curl -sf "$BASE_URL/metrics")
  echo "  metrics: $(echo "$METRICS" | jq -c '{active_jobs,completed_jobs,failed_jobs}')"

  [ "$ALL_DONE" -eq 1 ] && break
  NOW=$(date +%s)
  if [ $((NOW-START_TS)) -gt "$POLL_TIMEOUT" ]; then
    echo "FAIL: timed out after ${POLL_TIMEOUT}s waiting for jobs to drain (possible starvation/stuck queue)"
    break
  fi
  sleep "$POLL_INTERVAL"
done

echo "== 4. Post-check: service still up, no crash in logs =="
systemctl is-active "$SERVICE_NAME" || echo "FAIL: $SERVICE_NAME not active after load"
ps -eo pid,cmd | grep -c "[u]vicorn" | xargs -I{} echo "uvicorn process count after: {}"
curl -sf "$BASE_URL/health" | jq . || echo "FAIL: /health not OK after load"

echo "  -- journalctl since test start, filtered for crash/error signatures --"
sudo journalctl -u "$SERVICE_NAME" --since "-15min" 2>/dev/null | \
  grep -iE "traceback|segfault|core dump|Job Failed|clip_service|whisper_service" || echo "  (no matching lines found)"

echo "== 5. Summary =="
PASS=0
FAIL_COUNT=0
for entry in "${JOB_IDS[@]}"; do
  JID="${entry%%:*}"
  RESULT="${DONE[$JID]:-TIMEOUT}"
  STATUS="${RESULT%%:*}"
  PROGRESS="${RESULT#*:}"
  if [ "$STATUS" = "completed" ] && [ "$PROGRESS" = "100" ]; then
    PASS=$((PASS+1))
  else
    FAIL_COUNT=$((FAIL_COUNT+1))
    echo "  NOT CLEAN: $JID -> $RESULT"
  fi
done
echo "Jobs completed cleanly (status=completed, progress=100): $PASS / $TOTAL_JOBS"
echo "Jobs failed/timed out: $FAIL_COUNT"
[ "$FAIL_COUNT" -eq 0 ] && echo "RESULT: PASS" || echo "RESULT: FAIL"
