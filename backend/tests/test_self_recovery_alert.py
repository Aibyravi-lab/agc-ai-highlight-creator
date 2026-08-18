"""VED-P1-018: the external self-recovery watchdog (scripts/self_recovery_watchdog.sh)
bridges into the existing monitoring_alerts table via two additive
AlertEngineService entry points rather than creating a second alert
system. Covers:

  - AlertEngineService.record_alert()/resolve_alert(): dedup-by-open-
    check_id (same rule evaluate_and_raise already uses), correct
    severity/evidence shape, and that resolve on a check_id with no open
    alert is a safe no-op.
  - backend/scripts/record_recovery_alert.py: the actual subprocess the
    bash watchdog invokes, end to end (open -> visible in
    get_open_alerts() -> resolve -> no longer open).
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from app.services.alert_engine_service import AlertEngineService
from app.services.database_service import DatabaseService

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_RECORD_ALERT_SCRIPT = _BACKEND_DIR / "scripts" / "record_recovery_alert.py"


def _make_isolated_db():
    tmp_dir = tempfile.TemporaryDirectory()
    DatabaseService.DB_DIR = Path(tmp_dir.name)
    DatabaseService.DB_PATH = Path(tmp_dir.name) / "test_agc.db"
    DatabaseService.initialize()
    return tmp_dir


class TestAlertEngineRecoveryBridge(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = _make_isolated_db()

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_record_alert_opens_alert_with_expected_shape(self):
        AlertEngineService.record_alert("self_recovery_backend", "restart did not recover the service")

        open_alerts = AlertEngineService.get_open_alerts()
        matching = [a for a in open_alerts if a["check_id"] == "self_recovery_backend"]

        self.assertEqual(len(matching), 1)
        alert = matching[0]
        self.assertEqual(alert["severity"], "critical")
        self.assertIn("restart did not recover the service", alert["root_cause"])
        self.assertIsNone(alert["resolved_at"])
        self.assertIn("suggested_fix", alert)

    def test_record_alert_dedups_open_alert_for_same_check_id(self):
        AlertEngineService.record_alert("self_recovery_backend", "first failure")
        AlertEngineService.record_alert("self_recovery_backend", "second failure")

        open_alerts = [a for a in AlertEngineService.get_open_alerts() if a["check_id"] == "self_recovery_backend"]

        self.assertEqual(len(open_alerts), 1)
        self.assertIn("first failure", open_alerts[0]["root_cause"])

    def test_resolve_alert_closes_the_open_alert(self):
        AlertEngineService.record_alert("self_recovery_frontend", "restart did not recover the service")
        AlertEngineService.resolve_alert("self_recovery_frontend")

        open_alerts = [a for a in AlertEngineService.get_open_alerts() if a["check_id"] == "self_recovery_frontend"]
        resolved_alerts = [a for a in AlertEngineService.list_alerts(resolved=True) if a["check_id"] == "self_recovery_frontend"]

        self.assertEqual(len(open_alerts), 0)
        self.assertEqual(len(resolved_alerts), 1)

    def test_resolve_alert_with_no_open_alert_is_a_safe_no_op(self):
        AlertEngineService.resolve_alert("self_recovery_backend")

        open_alerts = [a for a in AlertEngineService.get_open_alerts() if a["check_id"] == "self_recovery_backend"]
        self.assertEqual(len(open_alerts), 0)

    def test_self_recovery_check_ids_are_distinct_from_health_engine_check_ids(self):
        # HealthEngineService's own in-process "backend"/"frontend" checks
        # (VED-P1-002) must never be resolved by the external watchdog's
        # alerts, and vice versa — see alert_engine_service.py comment.
        AlertEngineService.record_alert("self_recovery_backend", "watchdog restart failed")

        open_ids = {a["check_id"] for a in AlertEngineService.get_open_alerts()}
        self.assertIn("self_recovery_backend", open_ids)
        self.assertNotIn("backend", open_ids)


class TestRecordRecoveryAlertScript(unittest.TestCase):
    """End-to-end: the actual subprocess scripts/self_recovery_watchdog.sh
    invokes, run for real against an isolated SQLite database (passed via
    DATABASE_FOLDER/DATABASE_NAME env vars, the same mechanism
    backend/app/config/config.py already reads)."""

    def setUp(self):
        self._tmp_dir = tempfile.TemporaryDirectory()
        DatabaseService.DB_DIR = Path(self._tmp_dir.name)
        DatabaseService.DB_PATH = Path(self._tmp_dir.name) / "test_agc.db"
        DatabaseService.initialize()

    def tearDown(self):
        self._tmp_dir.cleanup()

    def _run_script(self, *args):
        import os

        env = dict(os.environ)
        env["DATABASE_FOLDER"] = self._tmp_dir.name
        env["DATABASE_NAME"] = "test_agc.db"

        return subprocess.run(
            [sys.executable, str(_RECORD_ALERT_SCRIPT), *args],
            cwd=str(_BACKEND_DIR),
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_open_then_resolve_end_to_end(self):
        result = self._run_script("open", "backend", "integration test failure")
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        open_alerts = [a for a in AlertEngineService.get_open_alerts() if a["check_id"] == "self_recovery_backend"]
        self.assertEqual(len(open_alerts), 1)
        self.assertIn("integration test failure", open_alerts[0]["root_cause"])

        result = self._run_script("resolve", "backend")
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        open_alerts = [a for a in AlertEngineService.get_open_alerts() if a["check_id"] == "self_recovery_backend"]
        self.assertEqual(len(open_alerts), 0)

    def test_invalid_service_name_exits_nonzero(self):
        result = self._run_script("open", "sqlite", "should be rejected")
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
