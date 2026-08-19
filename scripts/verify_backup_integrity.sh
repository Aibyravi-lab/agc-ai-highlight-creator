#!/usr/bin/env bash
# VED-BACKUP-INTEGRITY-001 — fixed-purpose, root-only archive-integrity
# verifier for Vedzovi (AGC AI Highlight Creator) backups.
#
# /opt/vedzovi-backups is intentionally root:root 755, with each timestamped
# backup directory root:root 700 and archives/checksums/manifest root:root
# 600 (see docs/BACKUP_STRATEGY.md) — the `agc` backend user cannot read
# inside it. This script is the ONLY thing `agc` is allowed to run as root
# (systemd/vedzovi-backup-verifier.sudoers) so that
# HealthService.verify_backup_archive_integrity() can get real archive-
# integrity evidence without widening those permissions.
#
# What it does, and ONLY this:
#   - locates the latest timestamped backup directory under the fixed
#     BACKUP_ROOT, using the same naming convention as scripts/backup.sh
#     and scripts/restore_test.sh (YYYY-MM-DD_HHMMSS)
#   - requires checksums.sha256 to exist in that directory
#   - verifies every archive checksums.sha256 lists, restricted to plain
#     *.tar.gz filenames (no paths, no traversal), via `sha256sum -c`
#   - prints a strict, minimal key=value result to stdout and exits
#
# What it NEVER does:
#   - accept a path argument (any argument aborts — BACKUP_ROOT is fixed)
#   - extract any archive
#   - modify, delete, or write anything under BACKUP_ROOT
#   - touch live application data
#   - invoke scripts/restore.sh or scripts/restore_test.sh
#
# Output contract — exactly these four keys, in this order, nothing else:
#   status=healthy|unhealthy|unknown
#   verified=true|false|unknown
#   backup_dir=<YYYY-MM-DD_HHMMSS>|<empty>
#   reason=<short machine-readable code>
#
# Exit codes: 0=healthy, 1=unhealthy, 2=unknown (could not verify at all —
# missing backup/metadata, bad environment, or rejected input).
#
# Install (as root, on the VPS):
#   sudo install -o root -g root -m 0755 scripts/verify_backup_integrity.sh \
#       /usr/local/sbin/vedzovi-verify-backup
# See docs/BACKUP_STRATEGY.md for the full install/rollback sequence.

set -uo pipefail

# BACKUP_ROOT is fixed to the production path by default. The env-var
# override exists only so this script's own test suite
# (scripts/tests/test_verify_backup_integrity.sh) can point it at a fixture
# directory — sudo's default env_reset strips inherited environment
# variables, so this is not attacker-controlled via the sudoers rule, which
# invokes the script with no arguments and no preserved environment.
BACKUP_ROOT="${BACKUP_ROOT:-/opt/vedzovi-backups}"

emit() {
    # $1=status $2=verified $3=backup_dir $4=reason
    printf 'status=%s\nverified=%s\nbackup_dir=%s\nreason=%s\n' "$1" "$2" "$3" "$4"
}

# ─── 0. No arguments accepted, ever — BACKUP_ROOT is fixed, not caller input ─
if [ "$#" -ne 0 ]; then
    emit "unknown" "unknown" "" "arguments_not_permitted"
    exit 2
fi

# ─── 1. Must run as root — this script is only meaningful via the fixed
#        sudoers rule; refuse to silently do something else ─────────────────
if [ "$(id -u)" -ne 0 ]; then
    emit "unknown" "unknown" "" "not_root"
    exit 2
fi

command -v sha256sum >/dev/null 2>&1 || { emit "unknown" "unknown" "" "sha256sum_unavailable"; exit 2; }

# ─── 2. Backup root must exist ──────────────────────────────────────────────
[ -d "$BACKUP_ROOT" ] || { emit "unknown" "unknown" "" "no_backup_root"; exit 2; }

# ─── 3. Locate latest timestamped backup directory (same convention as
#        scripts/backup.sh / scripts/restore_test.sh) ───────────────────────
LATEST_DIR="$(
    find "$BACKUP_ROOT" -maxdepth 1 -mindepth 1 -type d \
        -name '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]_*' 2>/dev/null \
    | sort -r | head -n1
)"
if [ -z "$LATEST_DIR" ]; then
    emit "unknown" "unknown" "" "no_backup_directory"
    exit 2
fi
BACKUP_DIR_NAME="$(basename "$LATEST_DIR")"

# ─── 4. checksums.sha256 is required metadata. Its absence means integrity
#        cannot be trusted — treated as unhealthy, matching the pre-existing
#        HealthService.verify_backup_archive_integrity() semantics this
#        verifier replaces the implementation of, not just "unknown". ──────
CHECKSUM_FILE="${LATEST_DIR}/checksums.sha256"
if [ ! -f "$CHECKSUM_FILE" ]; then
    emit "unhealthy" "false" "$BACKUP_DIR_NAME" "no_checksum_file"
    exit 1
fi

# ─── 5. Every line must reference a plain *.tar.gz filename in this same
#        directory — no paths, no traversal, nothing outside BACKUP_ROOT.
#        Defense in depth: only root can write this file, but a corrupted
#        or tampered checksums.sha256 must never make sha256sum -c read
#        outside the backup directory. ───────────────────────────────────
while IFS= read -r line || [ -n "$line" ]; do
    [ -n "$line" ] || continue
    filename="$(printf '%s' "$line" | awk '{print $2}')"
    filename="${filename#\*}"
    case "$filename" in
        *.tar.gz)
            case "$filename" in
                */*|.*)
                    emit "unhealthy" "false" "$BACKUP_DIR_NAME" "checksum_metadata_invalid"
                    exit 1
                    ;;
            esac
            ;;
        *)
            emit "unhealthy" "false" "$BACKUP_DIR_NAME" "checksum_metadata_invalid"
            exit 1
            ;;
    esac
done < "$CHECKSUM_FILE"

# ─── 6. Verify checksums — read-only, zero extraction, zero writes ─────────
if ( cd "$LATEST_DIR" && sha256sum -c checksums.sha256 ) >/dev/null 2>&1; then
    emit "healthy" "true" "$BACKUP_DIR_NAME" "ok"
    exit 0
else
    emit "unhealthy" "false" "$BACKUP_DIR_NAME" "checksum_mismatch"
    exit 1
fi
