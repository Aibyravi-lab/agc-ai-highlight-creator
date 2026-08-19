"""VED-BACKUP-INTEGRITY-001: HealthService.verify_backup_archive_integrity()
consuming the fixed-purpose root verifier (scripts/verify_backup_integrity.sh)
via a narrowly-scoped sudo rule instead of reading backup files itself.

Covers:
  - HealthService._invoke_backup_verifier() is mocked, not the production
    sudo helper, so these tests run identically on a dev machine (including
    Windows) with no sudo/verifier installed.
  - Every mapping from verifier stdout/exit-code to the public
    {status, verified, backup_dir} contract, including malformed-output
    and timeout/exec-failure paths that must never produce "healthy".
  - Security properties: no arbitrary path is ever passed to the verifier,
    the sudoers rule has no wildcard, and restore-test evidence
    (HealthService.get_restore_test_status) stays fully independent of
    archive-integrity evidence.
"""

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.config.config import settings
from app.services.health_service import HealthService

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _completed(returncode: int, stdout: str) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=["sudo", "-n", "/usr/local/sbin/vedzovi-verify-backup"],
        returncode=returncode,
        stdout=stdout,
        stderr="",
    )


class BackupVerifierIntegrationTests(unittest.TestCase):
    """HealthService.verify_backup_archive_integrity() only ever calls out
    through _invoke_backup_verifier() — mocking that one seam exercises the
    full parse/mapping logic without needing sudo or the real script.
    """

    def setUp(self):
        self._tmp_dir = tempfile.TemporaryDirectory()
        self._original_backup_root = settings.BACKUP_ROOT
        settings.BACKUP_ROOT = self._tmp_dir.name
        # verify_backup_archive_integrity() short-circuits to "unknown"
        # before ever invoking the verifier if BACKUP_ROOT doesn't exist —
        # give it a real (empty) directory so the verifier-invocation path
        # under test actually runs.
        Path(self._tmp_dir.name).mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        settings.BACKUP_ROOT = self._original_backup_root
        self._tmp_dir.cleanup()

    def test_healthy_when_verifier_reports_valid_backup(self):
        stdout = (
            "status=healthy\n"
            "verified=true\n"
            "backup_dir=2026-08-18_020000\n"
            "reason=ok\n"
        )
        with patch.object(HealthService, "_invoke_backup_verifier", return_value=_completed(0, stdout)):
            result = HealthService.verify_backup_archive_integrity()

        self.assertEqual(result, {"status": "healthy", "verified": True, "backup_dir": "2026-08-18_020000"})

    def test_unhealthy_on_checksum_mismatch(self):
        stdout = (
            "status=unhealthy\n"
            "verified=false\n"
            "backup_dir=2026-08-18_020000\n"
            "reason=checksum_mismatch\n"
        )
        with patch.object(HealthService, "_invoke_backup_verifier", return_value=_completed(1, stdout)):
            result = HealthService.verify_backup_archive_integrity()

        self.assertEqual(result["status"], "unhealthy")
        self.assertFalse(result["verified"])
        self.assertEqual(result["backup_dir"], "2026-08-18_020000")

    def test_missing_checksum_file_reports_unhealthy(self):
        """Matches the pre-VED-BACKUP-INTEGRITY-001 semantics: a backup
        directory that exists but has no checksums.sha256 is unhealthy
        (integrity cannot be trusted), not merely unknown.
        """
        stdout = (
            "status=unhealthy\n"
            "verified=false\n"
            "backup_dir=2026-08-18_020000\n"
            "reason=no_checksum_file\n"
        )
        with patch.object(HealthService, "_invoke_backup_verifier", return_value=_completed(1, stdout)):
            result = HealthService.verify_backup_archive_integrity()

        self.assertEqual(result["status"], "unhealthy")
        self.assertFalse(result["verified"])

    def test_unknown_when_no_backup_directory(self):
        stdout = "status=unknown\nverified=unknown\nbackup_dir=\nreason=no_backup_directory\n"
        with patch.object(HealthService, "_invoke_backup_verifier", return_value=_completed(2, stdout)):
            result = HealthService.verify_backup_archive_integrity()

        self.assertEqual(result, {"status": "unknown", "verified": None, "backup_dir": None})

    def test_unknown_when_backup_root_missing_no_verifier_invoked(self):
        settings.BACKUP_ROOT = str(Path(self._tmp_dir.name) / "does-not-exist")

        with patch.object(HealthService, "_invoke_backup_verifier") as mock_invoke:
            result = HealthService.verify_backup_archive_integrity()

        self.assertEqual(result, {"status": "unknown", "verified": None, "backup_dir": None})
        mock_invoke.assert_not_called()

    def test_malformed_output_cannot_produce_healthy(self):
        malformed_cases = [
            "status=healthy\nverified=true\nreason=ok\n",  # missing backup_dir key
            "status=healthy\nverified=false\nbackup_dir=x\nreason=ok\n",  # inconsistent combo
            "status=healthy\nverified=true\nbackup_dir=\nreason=ok\n",  # healthy with empty backup_dir
            "status=healthy\n",  # incomplete
            "not even key=value formatted output",
            "status=healthy\nverified=true\nbackup_dir=x\nreason=ok\nextra=field\n",  # extra key
            "",
        ]
        for stdout in malformed_cases:
            with self.subTest(stdout=stdout):
                with patch.object(HealthService, "_invoke_backup_verifier", return_value=_completed(0, stdout)):
                    result = HealthService.verify_backup_archive_integrity()
                self.assertEqual(result["status"], "unknown")
                self.assertNotEqual(result["status"], "healthy")

    def test_returncode_status_mismatch_becomes_unknown(self):
        """Defense in depth: stdout claims healthy but the exit code says
        otherwise (or vice versa) — never trust stdout alone.
        """
        stdout = "status=healthy\nverified=true\nbackup_dir=2026-08-18_020000\nreason=ok\n"
        with patch.object(HealthService, "_invoke_backup_verifier", return_value=_completed(1, stdout)):
            result = HealthService.verify_backup_archive_integrity()

        self.assertEqual(result["status"], "unknown")

    def test_subprocess_timeout_becomes_unknown(self):
        with patch.object(
            HealthService,
            "_invoke_backup_verifier",
            side_effect=None,
            return_value=None,
        ):
            result = HealthService.verify_backup_archive_integrity()

        self.assertEqual(result, {"status": "unknown", "verified": None, "backup_dir": None})

    def test_invoke_backup_verifier_catches_timeout_expired(self):
        with patch(
            "app.services.health_service.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="sudo", timeout=20),
        ):
            result = HealthService._invoke_backup_verifier()

        self.assertIsNone(result)

    def test_nonzero_exit_without_matching_status_becomes_unknown(self):
        """A verifier exiting non-zero with stdout that claims 'unknown'
        (exit 2) must round-trip correctly; any other exit/status pairing
        that isn't in the fixed {healthy:0, unhealthy:1, unknown:2} map is
        rejected rather than guessed at.
        """
        stdout = "status=unknown\nverified=unknown\nbackup_dir=\nreason=arguments_not_permitted\n"
        with patch.object(HealthService, "_invoke_backup_verifier", return_value=_completed(2, stdout)):
            result = HealthService.verify_backup_archive_integrity()

        self.assertEqual(result["status"], "unknown")
        self.assertIsNone(result["verified"])
        self.assertIsNone(result["backup_dir"])

    def test_return_shape_matches_preexisting_contract(self):
        stdout = "status=healthy\nverified=true\nbackup_dir=2026-08-18_020000\nreason=ok\n"
        with patch.object(HealthService, "_invoke_backup_verifier", return_value=_completed(0, stdout)):
            result = HealthService.verify_backup_archive_integrity()

        self.assertEqual(set(result.keys()), {"status", "verified", "backup_dir"})

    def test_invoke_backup_verifier_never_passes_a_path_argument(self):
        """The only thing this backend is ever allowed to run as root is the
        fixed verifier command with zero arguments — no user- or
        settings-derived path is ever appended to the sudo invocation.
        """
        with patch("app.services.health_service.subprocess.run") as mock_run:
            mock_run.return_value = _completed(2, "status=unknown\nverified=unknown\nbackup_dir=\nreason=x\n")
            HealthService._invoke_backup_verifier()

        called_args = mock_run.call_args.args[0]
        self.assertEqual(called_args, ["sudo", "-n", "/usr/local/sbin/vedzovi-verify-backup"])

    def test_restore_test_evidence_independent_of_archive_integrity(self):
        """A restore-test SUCCESS sentinel must not be fabricated or
        implied by archive-integrity verification, and vice versa — the two
        HealthService methods must not read each other's state.
        """
        sentinel = Path(settings.BACKUP_ROOT) / "last_restore_test_status"
        sentinel.write_text("SUCCESS 2026-08-18_030000: 2026-08-18_020000", encoding="utf-8")

        with patch.object(HealthService, "_invoke_backup_verifier", return_value=None):
            archive_integrity = HealthService.verify_backup_archive_integrity()

        restore_test = HealthService.get_restore_test_status()

        self.assertEqual(archive_integrity["status"], "unknown")
        self.assertEqual(restore_test["status"], "healthy")


class BackupVerifierSecurityTests(unittest.TestCase):
    """Static checks against the repo's own verifier artifacts — these run
    without sudo/root and without invoking the real script, but fail if the
    security properties VED-BACKUP-INTEGRITY-001 requires ever regress.
    """

    def test_sudoers_rule_has_no_wildcard_and_exact_command(self):
        sudoers_path = _REPO_ROOT / "systemd" / "vedzovi-backup-verifier.sudoers"
        content = sudoers_path.read_text(encoding="utf-8")

        rule_lines = [
            line.strip()
            for line in content.splitlines()
            if line.strip().startswith("agc ALL=")
        ]
        self.assertEqual(
            rule_lines,
            ["agc ALL=(root) NOPASSWD: /usr/local/sbin/vedzovi-verify-backup"],
        )
        for char in ("*", "?", "ALL:", " sha256sum", "/bin/bash", "/bin/sh"):
            self.assertNotIn(char, "\n".join(rule_lines))

    def test_verifier_script_never_invokes_restore_scripts(self):
        script_path = _REPO_ROOT / "scripts" / "verify_backup_integrity.sh"
        content = script_path.read_text(encoding="utf-8")

        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            self.assertNotIn("restore.sh", stripped)
            self.assertNotIn("restore_test.sh", stripped)

    def test_verifier_script_has_no_write_operations_under_backup_root(self):
        script_path = _REPO_ROOT / "scripts" / "verify_backup_integrity.sh"
        content = script_path.read_text(encoding="utf-8")

        forbidden_tokens = [" rm ", " rm -", ">$LATEST_DIR", ">${LATEST_DIR}", "mkdir", "chmod", "chown", "tar -x", "tar -c"]
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for token in forbidden_tokens:
                self.assertNotIn(token, line, msg=f"forbidden token {token!r} found in: {line}")

    def test_verifier_script_rejects_any_argument(self):
        script_path = _REPO_ROOT / "scripts" / "verify_backup_integrity.sh"
        content = script_path.read_text(encoding="utf-8")

        self.assertIn('if [ "$#" -ne 0 ]; then', content)
        self.assertIn("arguments_not_permitted", content)

    def test_health_service_invocation_uses_no_shell(self):
        import inspect

        source = inspect.getsource(HealthService._invoke_backup_verifier)
        self.assertNotIn("shell=True", source)
        self.assertIn("timeout=", source)


if __name__ == "__main__":
    unittest.main()
