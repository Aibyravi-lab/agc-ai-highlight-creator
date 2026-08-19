#!/usr/bin/env bash
# VED-BACKUP-INTEGRITY-001 — behavioral tests for
# scripts/verify_backup_integrity.sh.
#
# Pure bash, no external test framework (bats is not a repo dependency),
# mirroring scripts/tests/test_self_recovery_watchdog.sh's approach: the
# real script runs unmodified as a fresh subprocess. BACKUP_ROOT is
# overridden via env var to point at a disposable fixture directory (the
# script's sudoers rule strips this in production via sudo's default
# env_reset — see the script's own header comment). `id` is shadowed on
# PATH so the script's root-check passes without actually needing root.
#
# Run:
#   bash scripts/tests/test_verify_backup_integrity.sh

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VERIFIER="$REPO_ROOT/scripts/verify_backup_integrity.sh"

PASS=0
FAIL=0

pass() { PASS=$((PASS + 1)); echo "  PASS: $1"; }
fail() { FAIL=$((FAIL + 1)); echo "  FAIL: $1"; }

assert_eq() {
    local actual="$1" expected="$2" desc="$3"
    if [ "$actual" = "$expected" ]; then pass "$desc"; else fail "$desc (expected [$expected], got [$actual])"; fi
}

assert_contains() {
    local haystack="$1" needle="$2" desc="$3"
    if [[ "$haystack" == *"$needle"* ]]; then pass "$desc"; else fail "$desc (expected to find: $needle in: $haystack)"; fi
}

# ─── Fixture: fake root via a shadowed `id`, disposable BACKUP_ROOT ─────────
setup_fixture() {
    FIXTURE_DIR="$(mktemp -d)"
    BACKUP_ROOT="$FIXTURE_DIR/backups"
    BIN_DIR="$FIXTURE_DIR/bin"
    mkdir -p "$BACKUP_ROOT" "$BIN_DIR"

    cat > "$BIN_DIR/id" <<'MOCK'
#!/usr/bin/env bash
if [ "${1:-}" = "-u" ]; then
    echo "${MOCK_UID:-0}"
    exit 0
fi
exit 1
MOCK
    chmod +x "$BIN_DIR/id"
}

teardown_fixture() {
    rm -rf "$FIXTURE_DIR"
}

make_backup_dir() {
    local ts="$1"
    mkdir -p "$BACKUP_ROOT/$ts"
    echo "dummy" > "$BACKUP_ROOT/$ts/database.tar.gz"
}

write_valid_checksums() {
    local ts="$1"
    ( cd "$BACKUP_ROOT/$ts" && sha256sum -- *.tar.gz > checksums.sha256 )
}

run_verifier() {
    PATH="$BIN_DIR:$PATH" BACKUP_ROOT="$BACKUP_ROOT" MOCK_UID="${MOCK_UID:-0}" "$VERIFIER" "$@"
}

# ─── Test 1: healthy on a valid backup with correct checksums ──────────────
setup_fixture
make_backup_dir "2026-08-18_020000"
write_valid_checksums "2026-08-18_020000"
OUTPUT="$(run_verifier)"; CODE=$?
assert_contains "$OUTPUT" "status=healthy" "healthy: status line"
assert_contains "$OUTPUT" "verified=true" "healthy: verified line"
assert_contains "$OUTPUT" "backup_dir=2026-08-18_020000" "healthy: backup_dir line"
assert_eq "$CODE" "0" "healthy: exit code 0"
teardown_fixture

# ─── Test 2: unhealthy on checksum mismatch ─────────────────────────────────
setup_fixture
make_backup_dir "2026-08-18_020000"
write_valid_checksums "2026-08-18_020000"
echo "tampered" >> "$BACKUP_ROOT/2026-08-18_020000/database.tar.gz"
OUTPUT="$(run_verifier)"; CODE=$?
assert_contains "$OUTPUT" "status=unhealthy" "checksum mismatch: status line"
assert_contains "$OUTPUT" "reason=checksum_mismatch" "checksum mismatch: reason line"
assert_eq "$CODE" "1" "checksum mismatch: exit code 1"
teardown_fixture

# ─── Test 3: missing checksums.sha256 reports unhealthy (not unknown) ──────
setup_fixture
make_backup_dir "2026-08-18_020000"
OUTPUT="$(run_verifier)"; CODE=$?
assert_contains "$OUTPUT" "status=unhealthy" "missing checksum file: status line"
assert_contains "$OUTPUT" "reason=no_checksum_file" "missing checksum file: reason line"
assert_eq "$CODE" "1" "missing checksum file: exit code 1"
teardown_fixture

# ─── Test 4: no backup directory at all reports unknown ────────────────────
setup_fixture
OUTPUT="$(run_verifier)"; CODE=$?
assert_contains "$OUTPUT" "status=unknown" "no backup dir: status line"
assert_contains "$OUTPUT" "reason=no_backup_directory" "no backup dir: reason line"
assert_eq "$CODE" "2" "no backup dir: exit code 2"
teardown_fixture

# ─── Test 5: BACKUP_ROOT itself missing reports unknown ────────────────────
setup_fixture
rm -rf "$BACKUP_ROOT"
OUTPUT="$(run_verifier)"; CODE=$?
assert_contains "$OUTPUT" "status=unknown" "no backup root: status line"
assert_contains "$OUTPUT" "reason=no_backup_root" "no backup root: reason line"
assert_eq "$CODE" "2" "no backup root: exit code 2"
teardown_fixture

# ─── Test 6: picks the LATEST of multiple timestamped directories ──────────
setup_fixture
make_backup_dir "2026-08-16_020000"
write_valid_checksums "2026-08-16_020000"
make_backup_dir "2026-08-18_020000"
write_valid_checksums "2026-08-18_020000"
make_backup_dir "2026-08-17_020000"
write_valid_checksums "2026-08-17_020000"
OUTPUT="$(run_verifier)"
assert_contains "$OUTPUT" "backup_dir=2026-08-18_020000" "latest: picks most recent timestamp"
teardown_fixture

# ─── Test 7: no arbitrary path argument is accepted ─────────────────────────
setup_fixture
make_backup_dir "2026-08-18_020000"
write_valid_checksums "2026-08-18_020000"
OUTPUT="$(run_verifier /etc/passwd)"; CODE=$?
assert_contains "$OUTPUT" "status=unknown" "argument rejected: status line"
assert_contains "$OUTPUT" "reason=arguments_not_permitted" "argument rejected: reason line"
assert_eq "$CODE" "2" "argument rejected: exit code 2"
teardown_fixture

# ─── Test 8: checksums.sha256 referencing a path outside the backup dir
#             is rejected rather than followed ─────────────────────────────
setup_fixture
make_backup_dir "2026-08-18_020000"
echo "0000000000000000000000000000000000000000000000000000000000000000  ../../../etc/passwd.tar.gz" \
    > "$BACKUP_ROOT/2026-08-18_020000/checksums.sha256"
OUTPUT="$(run_verifier)"; CODE=$?
assert_contains "$OUTPUT" "status=unhealthy" "traversal metadata: status line"
assert_contains "$OUTPUT" "reason=checksum_metadata_invalid" "traversal metadata: reason line"
assert_eq "$CODE" "1" "traversal metadata: exit code 1"
teardown_fixture

# ─── Test 9: refuses to run when not root ───────────────────────────────────
setup_fixture
make_backup_dir "2026-08-18_020000"
write_valid_checksums "2026-08-18_020000"
MOCK_UID=1000
OUTPUT="$(run_verifier)"; CODE=$?
assert_contains "$OUTPUT" "status=unknown" "not root: status line"
assert_contains "$OUTPUT" "reason=not_root" "not root: reason line"
assert_eq "$CODE" "2" "not root: exit code 2"
teardown_fixture

# ─── Test 10: never writes anything under BACKUP_ROOT ──────────────────────
setup_fixture
make_backup_dir "2026-08-18_020000"
write_valid_checksums "2026-08-18_020000"
BEFORE="$(find "$BACKUP_ROOT" -type f -exec sha256sum {} \; | sort)"
run_verifier >/dev/null
AFTER="$(find "$BACKUP_ROOT" -type f -exec sha256sum {} \; | sort)"
assert_eq "$AFTER" "$BEFORE" "no writes: backup tree unchanged after run"
teardown_fixture

# ─── Test 11: never touches backup directory permissions ───────────────────
setup_fixture
make_backup_dir "2026-08-18_020000"
write_valid_checksums "2026-08-18_020000"
chmod 700 "$BACKUP_ROOT/2026-08-18_020000"
BEFORE_MODE="$(stat -c '%a' "$BACKUP_ROOT/2026-08-18_020000" 2>/dev/null || stat -f '%Lp' "$BACKUP_ROOT/2026-08-18_020000")"
run_verifier >/dev/null
AFTER_MODE="$(stat -c '%a' "$BACKUP_ROOT/2026-08-18_020000" 2>/dev/null || stat -f '%Lp' "$BACKUP_ROOT/2026-08-18_020000")"
assert_eq "$AFTER_MODE" "$BEFORE_MODE" "no permission changes: backup dir mode unchanged"
teardown_fixture

# ─── Summary ─────────────────────────────────────────────────────────────────
echo ""
echo "test_verify_backup_integrity.sh: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
