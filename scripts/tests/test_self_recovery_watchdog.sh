#!/usr/bin/env bash
# VED-P1-018 — policy tests for scripts/self_recovery_watchdog.sh.
#
# Pure bash, no external test framework (bats is not a repo dependency).
# Every test runs the real watchdog script as a fresh subprocess with
# curl/systemctl/sudo/python shadowed by mocks placed first on PATH — the
# watchdog's own code is never modified or stubbed out for testing. No
# real network call or systemctl/sudo action ever happens.
#
# Run:
#   bash scripts/tests/test_self_recovery_watchdog.sh

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WATCHDOG="$REPO_ROOT/scripts/self_recovery_watchdog.sh"

PASS=0
FAIL=0

pass() { PASS=$((PASS + 1)); echo "  PASS: $1"; }
fail() { FAIL=$((FAIL + 1)); echo "  FAIL: $1"; }

assert_contains() {
    local haystack="$1" needle="$2" desc="$3"
    if [[ "$haystack" == *"$needle"* ]]; then pass "$desc"; else fail "$desc (expected to find: $needle)"; fi
}

assert_eq() {
    local actual="$1" expected="$2" desc="$3"
    if [ "$actual" = "$expected" ]; then pass "$desc"; else fail "$desc (expected [$expected], got [$actual])"; fi
}

# ─── Fixture: isolated STATE_DIR/BACKEND_DIR + mocked curl/systemctl/sudo ──
setup_fixture() {
    FIXTURE_DIR="$(mktemp -d)"
    STATE_DIR="$FIXTURE_DIR/state"
    BIN_DIR="$FIXTURE_DIR/bin"
    CTRL_DIR="$FIXTURE_DIR/ctrl"
    BACKEND_DIR="$FIXTURE_DIR/backend"
    mkdir -p "$STATE_DIR" "$BIN_DIR" "$CTRL_DIR" "$BACKEND_DIR/storage" "$BACKEND_DIR/scripts"

    echo 200 > "$CTRL_DIR/backend_code"
    echo 200 > "$CTRL_DIR/frontend_code"
    : > "$CTRL_DIR/systemctl.log"

    # Mock curl: last argument is always the URL (matches how the watchdog
    # invokes it). Returns the HTTP code from the control file, or fails
    # outright (nonzero exit, like a real connection failure) when the
    # control file says "DOWN".
    cat > "$BIN_DIR/curl" <<'MOCK'
#!/usr/bin/env bash
url="${@: -1}"
if [[ "$url" == *"backend.test"* ]]; then
    code_file="$CTRL_DIR/backend_code"
else
    code_file="$CTRL_DIR/frontend_code"
fi
code=$(cat "$code_file" 2>/dev/null || echo 200)
if [ "$code" = "DOWN" ]; then
    exit 7
fi
printf '%s' "$code"
exit 0
MOCK
    chmod +x "$BIN_DIR/curl"

    # Mock systemctl: logs every invocation. When RECOVER_ON_RESTART=1, a
    # `restart` call "fixes" the corresponding service by flipping its
    # control file back to 200, simulating a successful recovery.
    cat > "$BIN_DIR/systemctl" <<'MOCK'
#!/usr/bin/env bash
echo "systemctl $*" >> "$CTRL_DIR/systemctl.log"
case "$1" in
    restart)
        if [ "${RECOVER_ON_RESTART:-0}" = "1" ]; then
            case "$2" in
                *backend*) echo 200 > "$CTRL_DIR/backend_code" ;;
                *frontend*) echo 200 > "$CTRL_DIR/frontend_code" ;;
            esac
        fi
        exit 0
        ;;
    is-active)
        echo "active"
        exit 0
        ;;
esac
exit 0
MOCK
    chmod +x "$BIN_DIR/systemctl"

    # Mock sudo: strips a leading -n and execs the rest, so `sudo -n
    # systemctl ...` reaches the mock systemctl above exactly like real
    # sudo would reach the real systemctl.
    cat > "$BIN_DIR/sudo" <<'MOCK'
#!/usr/bin/env bash
echo "sudo $*" >> "$CTRL_DIR/sudo.log"
args=("$@")
if [ "${args[0]:-}" = "-n" ]; then
    args=("${args[@]:1}")
fi
"${args[@]}"
MOCK
    chmod +x "$BIN_DIR/sudo"

    # Mock python (VENV_PYTHON): stands in for backend/scripts/record_recovery_alert.py
    # without needing a real backend venv/database in the test environment.
    cat > "$BIN_DIR/mock-python" <<'MOCK'
#!/usr/bin/env bash
echo "python $*" >> "$CTRL_DIR/python.log"
exit 0
MOCK
    chmod +x "$BIN_DIR/mock-python"
    : > "$BACKEND_DIR/scripts/record_recovery_alert.py"
}

teardown_fixture() {
    rm -rf "$FIXTURE_DIR"
}

# Runs the real watchdog script once against the current fixture and env
# overrides, and prints its combined stdout/stderr.
run_watchdog() {
    CTRL_DIR="$CTRL_DIR" \
    PATH="$BIN_DIR:$PATH" \
    STATE_DIR="$STATE_DIR" \
    BACKEND_DIR="$BACKEND_DIR" \
    BACKEND_HEALTH_URL="http://backend.test/health" \
    FRONTEND_URL="http://frontend.test/" \
    MAINTENANCE_FLAG_PATH="$BACKEND_DIR/storage/maintenance.flag" \
    VENV_PYTHON="$BIN_DIR/mock-python" \
    RECORD_ALERT_SCRIPT="$BACKEND_DIR/scripts/record_recovery_alert.py" \
    RECOVERY_FAILURE_THRESHOLD="${TEST_THRESHOLD:-3}" \
    RECOVERY_COOLDOWN_SECONDS="${TEST_COOLDOWN:-900}" \
    RECOVERY_MAX_ATTEMPTS_PER_HOUR="${TEST_MAX_ATTEMPTS:-2}" \
    HEALTH_TIMEOUT_SECONDS=5 \
    VERIFY_WAIT_SECONDS=0 \
    RECOVER_ON_RESTART="${RECOVER_ON_RESTART:-0}" \
    bash "$WATCHDOG" 2>&1
}

restart_count() {
    if [ -f "$CTRL_DIR/systemctl.log" ]; then
        grep -c "restart $1" "$CTRL_DIR/systemctl.log"
    else
        echo 0
    fi
}

# ─── 1. healthy backend + frontend -> no restart ───────────────────────────
test_healthy_no_restart() {
    setup_fixture
    out=$(run_watchdog)
    assert_contains "$out" "SELF_RECOVERY_HEALTHY" "healthy run logs SELF_RECOVERY_HEALTHY"
    assert_eq "$(restart_count agc-backend.service)" "0" "no backend restart when healthy"
    assert_eq "$(restart_count agc-frontend.service)" "0" "no frontend restart when healthy"
    teardown_fixture
}

# ─── 2/3. one and two failed checks -> no restart ──────────────────────────
test_one_failure_no_restart() {
    setup_fixture
    echo DOWN > "$CTRL_DIR/backend_code"
    out=$(run_watchdog)
    assert_contains "$out" "SELF_RECOVERY_BACKEND_FAILURE threshold=1/3" "first failure logs threshold=1/3"
    assert_eq "$(restart_count agc-backend.service)" "0" "no restart on a single transient failure"
    teardown_fixture
}

test_two_failures_no_restart() {
    setup_fixture
    echo DOWN > "$CTRL_DIR/backend_code"
    run_watchdog >/dev/null
    out=$(run_watchdog)
    assert_contains "$out" "SELF_RECOVERY_BACKEND_FAILURE threshold=2/3" "second consecutive failure logs threshold=2/3"
    assert_eq "$(restart_count agc-backend.service)" "0" "still no restart below threshold"
    teardown_fixture
}

# ─── 4. three consecutive failures -> restart ──────────────────────────────
test_three_failures_triggers_restart() {
    setup_fixture
    echo DOWN > "$CTRL_DIR/backend_code"
    run_watchdog >/dev/null
    run_watchdog >/dev/null
    out=$(run_watchdog)
    assert_contains "$out" "SELF_RECOVERY_ACTION backend_restart" "third consecutive failure triggers a restart"
    assert_eq "$(restart_count agc-backend.service)" "1" "systemctl restart agc-backend.service was invoked exactly once"
    teardown_fixture
}

# ─── 5. recovery succeeds ───────────────────────────────────────────────────
test_recovery_succeeds() {
    setup_fixture
    echo DOWN > "$CTRL_DIR/backend_code"
    RECOVER_ON_RESTART=1 run_watchdog >/dev/null
    RECOVER_ON_RESTART=1 run_watchdog >/dev/null
    out=$(RECOVER_ON_RESTART=1 run_watchdog)
    assert_contains "$out" "SELF_RECOVERY_RESULT backend_recovered" "a restart that heals the service reports backend_recovered"
    teardown_fixture
}

# ─── 6. recovery fails ──────────────────────────────────────────────────────
test_recovery_fails() {
    setup_fixture
    echo DOWN > "$CTRL_DIR/backend_code"
    run_watchdog >/dev/null
    run_watchdog >/dev/null
    out=$(run_watchdog)
    assert_contains "$out" "SELF_RECOVERY_RESULT backend_recovery_failed" "a restart that doesn't heal the service reports backend_recovery_failed"
    assert_contains "$(cat "$CTRL_DIR/python.log" 2>/dev/null || true)" "open backend" "a failed recovery records a monitoring alert via record_recovery_alert.py"
    teardown_fixture
}

# ─── 7. maintenance ON -> no restart ────────────────────────────────────────
test_maintenance_skips() {
    setup_fixture
    echo DOWN > "$CTRL_DIR/backend_code"
    : > "$BACKEND_DIR/storage/maintenance.flag"
    out=$(run_watchdog)
    assert_contains "$out" "SELF_RECOVERY_SKIPPED_MAINTENANCE" "maintenance ON short-circuits the run"
    assert_eq "$(restart_count agc-backend.service)" "0" "no restart attempted during maintenance"
    teardown_fixture
}

# ─── 8. cooldown active -> no restart ───────────────────────────────────────
test_cooldown_blocks_restart() {
    setup_fixture
    echo DOWN > "$CTRL_DIR/backend_code"
    run_watchdog >/dev/null
    run_watchdog >/dev/null
    run_watchdog >/dev/null    # 3rd failure -> first restart (does not heal)
    out=$(run_watchdog)        # 4th failure, immediately after -> within cooldown
    assert_contains "$out" "SELF_RECOVERY_COOLDOWN" "a repeat breach inside the cooldown window is skipped"
    assert_eq "$(restart_count agc-backend.service)" "1" "cooldown kept the restart count at 1"
    teardown_fixture
}

# ─── 9. hourly recovery limit reached -> no restart ────────────────────────
test_hourly_limit_blocks_restart() {
    setup_fixture
    echo DOWN > "$CTRL_DIR/backend_code"
    TEST_COOLDOWN=0
    run_watchdog >/dev/null    # 1
    run_watchdog >/dev/null    # 2
    run_watchdog >/dev/null    # 3 -> restart #1
    run_watchdog >/dev/null    # 4 -> restart #2 (cooldown disabled for this test)
    out=$(run_watchdog)        # 5 -> should hit the hourly cap
    assert_contains "$out" "SELF_RECOVERY_LIMIT_REACHED" "a third breach within the rolling hour is blocked by the hourly cap"
    assert_eq "$(restart_count agc-backend.service)" "2" "hourly cap held the restart count at RECOVERY_MAX_ATTEMPTS_PER_HOUR"
    teardown_fixture
}

# ─── 10. frontend failure -> frontend restart (backend untouched) ─────────
test_frontend_failure_triggers_restart() {
    setup_fixture
    echo DOWN > "$CTRL_DIR/frontend_code"
    run_watchdog >/dev/null
    run_watchdog >/dev/null
    out=$(run_watchdog)
    assert_contains "$out" "SELF_RECOVERY_ACTION frontend_restart" "three frontend failures trigger a frontend restart"
    assert_eq "$(restart_count agc-frontend.service)" "1" "systemctl restart agc-frontend.service was invoked"
    assert_eq "$(restart_count agc-backend.service)" "0" "backend was not touched by a frontend-only failure"
    teardown_fixture
}

# ─── 11/12/13. SQLite / FFmpeg / payment failures are out of scope ─────────
test_out_of_scope_failures_never_restart() {
    # Policy: this watchdog only ever evaluates two conditions (reachability
    # of backend/frontend) and only ever restarts two units. Assert that
    # structurally, rather than grepping for keywords (which would also
    # match the policy explanation in this script's own header comment).
    check_fn_count=$(grep -cE '^check_[a-z_]+\(\)' "$WATCHDOG")
    assert_eq "$check_fn_count" "2" "watchdog defines exactly two health checks (backend, frontend) — no sqlite/ffmpeg/payment check exists"

    restart_call_count=$(grep -c 'restart_unit "\$unit"' "$WATCHDOG")
    assert_eq "$restart_call_count" "1" "the only restart call site is the generic per-service recovery path (no separate sqlite/ffmpeg/payment restart path)"

    setup_fixture
    out=$(run_watchdog)
    assert_eq "$(restart_count agc-backend.service)" "0" "reachability-only checks never restart for sqlite/ffmpeg/payment conditions"
    assert_eq "$(restart_count agc-frontend.service)" "0" "reachability-only checks never restart for sqlite/ffmpeg/payment conditions (frontend)"
    teardown_fixture
}

# ─── 14. lock prevents overlapping execution ───────────────────────────────
test_lock_prevents_overlap() {
    setup_fixture
    mkdir -p "$STATE_DIR/watchdog.lock.d"
    out=$(run_watchdog)
    assert_contains "$out" "SELF_RECOVERY_SKIPPED_LOCKED" "a held lock causes the run to be skipped"
    assert_eq "$(restart_count agc-backend.service)" "0" "no systemctl activity while the lock is held"

    rmdir "$STATE_DIR/watchdog.lock.d"
    out2=$(run_watchdog)
    assert_contains "$out2" "SELF_RECOVERY_HEALTHY" "watchdog resumes normal runs once the lock is released"
    teardown_fixture
}

echo "== VED-P1-018 self_recovery_watchdog.sh policy tests =="
echo
for t in \
    test_healthy_no_restart \
    test_one_failure_no_restart \
    test_two_failures_no_restart \
    test_three_failures_triggers_restart \
    test_recovery_succeeds \
    test_recovery_fails \
    test_maintenance_skips \
    test_cooldown_blocks_restart \
    test_hourly_limit_blocks_restart \
    test_frontend_failure_triggers_restart \
    test_out_of_scope_failures_never_restart \
    test_lock_prevents_overlap \
    ; do
    echo "-- ${t} --"
    "$t"
done

echo
echo "== ${PASS} passed, ${FAIL} failed =="
[ "$FAIL" -eq 0 ]
