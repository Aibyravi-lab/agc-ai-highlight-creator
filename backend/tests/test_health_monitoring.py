"""VED-P1-002: Production Monitoring.

Covers:
  - MonitoringEventService: recording + windowed counting of payment/email
    failures, and that PaymentService/EmailService actually record on their
    existing failure paths (without changing what those methods raise).
  - HealthEngineService: pure scoring math (weights, multipliers, unknown
    exclusion, overall-status thresholds), per-check threshold mapping
    (disk/memory/cpu/queue/ai_pipeline/payments/email/backups), boundary
    edge cases, and fail-isolation (_safe never lets one check crash the
    report).
  - AlertEngineService: alert creation with all four mandated fields
    (severity, root_cause, evidence, suggested_fix) + time, dedup of
    still-open alerts, and auto-resolution on recovery.
  - HealthHistoryService: snapshot persistence, today/yesterday/7d/30d
    range filtering, and trend (avg/min/max/direction) incl. empty state.
  - HealthSchedulerService.run_once(): wires evaluate -> persist -> alert.
  - /admin/health/* endpoints: admin-only auth, response shape.
  - /api/v1/ops/production-health: ops-key auth, response shape, and that
    it does not alter the existing /capabilities or /summary contracts.
"""

import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config.config import settings
from app.dependencies import get_current_user, verify_ops_api_key
from app.routers import admin_health as admin_health_router_module
from app.routers import ops as ops_router_module
from app.services.alert_engine_service import AlertEngineService
from app.services.database_service import DatabaseService
from app.services.email_service import EmailService
from app.services.health_engine_service import CheckStatus, HealthEngineService
from app.services.health_history_service import HealthHistoryService
from app.services.health_scheduler_service import HealthSchedulerService
from app.services.monitoring_event_service import MonitoringEventService
from app.services.ops_service import OpsService
from app.services.payment_service import (
    PaymentGatewayError,
    PaymentService,
)

_TEST_OPS_KEY = "test-ops-key-0123456789abcdef"


def _make_isolated_db():
    tmp_dir = tempfile.TemporaryDirectory()
    DatabaseService.DB_DIR = Path(tmp_dir.name)
    DatabaseService.DB_PATH = Path(tmp_dir.name) / "test_agc.db"
    DatabaseService.initialize()
    HealthEngineService.clear_cache()
    OpsService._cache.clear()
    return tmp_dir


def _create_user(email: str, is_admin: bool = False) -> int:
    connection = DatabaseService.get_connection()
    cursor = connection.cursor()
    now = datetime.utcnow().isoformat()
    cursor.execute(
        "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        ("Test User", email, "hash", now),
    )
    user_id = cursor.lastrowid
    connection.commit()
    connection.close()

    if is_admin:
        connection = DatabaseService.get_connection()
        cursor = connection.cursor()
        cursor.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (user_id,))
        connection.commit()
        connection.close()

    return user_id


def _insert_job(status: str) -> None:
    connection = DatabaseService.get_connection()
    cursor = connection.cursor()
    now = datetime.utcnow().isoformat()
    cursor.execute(
        "INSERT INTO jobs (job_id, status, progress, created_at) VALUES (?, ?, 0, ?)",
        (f"job-{status}-{uuid4().hex}", status, now),
    )
    connection.commit()
    connection.close()


def _insert_monitoring_event(category: str, created_at: str) -> None:
    connection = DatabaseService.get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO monitoring_events (category, detail, created_at) VALUES (?, ?, ?)",
        (category, "test", created_at),
    )
    connection.commit()
    connection.close()


class MonitoringEventServiceTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = _make_isolated_db()

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_record_and_count_within_window(self):
        MonitoringEventService.record_failure(MonitoringEventService.PAYMENT, "gateway_error")
        MonitoringEventService.record_failure(MonitoringEventService.PAYMENT, "gateway_error")

        count = MonitoringEventService.count_recent_failures(MonitoringEventService.PAYMENT, 60)

        self.assertEqual(count, 2)

    def test_events_outside_window_are_excluded(self):
        old = (datetime.utcnow() - timedelta(minutes=120)).isoformat()
        _insert_monitoring_event(MonitoringEventService.EMAIL, old)

        count = MonitoringEventService.count_recent_failures(MonitoringEventService.EMAIL, 60)

        self.assertEqual(count, 0)

    def test_categories_are_isolated(self):
        MonitoringEventService.record_failure(MonitoringEventService.PAYMENT, "x")

        self.assertEqual(MonitoringEventService.count_recent_failures(MonitoringEventService.EMAIL, 60), 0)
        self.assertEqual(MonitoringEventService.count_recent_failures(MonitoringEventService.PAYMENT, 60), 1)

    def test_record_failure_never_raises_on_broken_db(self):
        DatabaseService.DB_PATH = Path("Z:/nonexistent/path/does-not-exist.db")

        try:
            MonitoringEventService.record_failure(MonitoringEventService.PAYMENT, "x")
        except Exception as exc:  # pragma: no cover - failure would fail the test
            self.fail(f"record_failure raised: {exc}")


class PaymentEmailFailureHookTests(unittest.TestCase):
    """Confirms the additive MonitoringEventService.record_failure() calls
    fire on existing failure paths without changing what those methods
    raise or return — CLAUDE.md's 'preserve existing business logic'.
    """

    def setUp(self):
        self._tmp_dir = _make_isolated_db()
        self._original_key_id = settings.RAZORPAY_KEY_ID
        self._original_key_secret = settings.RAZORPAY_KEY_SECRET
        settings.RAZORPAY_KEY_ID = "test-key-id"
        settings.RAZORPAY_KEY_SECRET = "test-key-secret"
        PaymentService._client = None

    def tearDown(self):
        self._tmp_dir.cleanup()
        settings.RAZORPAY_KEY_ID = self._original_key_id
        settings.RAZORPAY_KEY_SECRET = self._original_key_secret
        PaymentService._client = None

    def test_order_creation_failure_still_raises_and_records_event(self):
        broken_client = MagicMock()
        broken_client.order.create.side_effect = RuntimeError("gateway down")

        with patch.object(PaymentService, "get_client", return_value=broken_client):
            with self.assertRaises(PaymentGatewayError):
                PaymentService.create_order(user_id=1, plan="pro")

        self.assertEqual(
            MonitoringEventService.count_recent_failures(MonitoringEventService.PAYMENT, 60), 1
        )

    def test_successful_order_creation_does_not_record_a_failure_event(self):
        working_client = MagicMock()
        working_client.order.create.return_value = {"id": "order_123"}

        with patch.object(PaymentService, "get_client", return_value=working_client):
            PaymentService.create_order(user_id=1, plan="pro")

        self.assertEqual(
            MonitoringEventService.count_recent_failures(MonitoringEventService.PAYMENT, 60), 0
        )

    def test_email_send_failure_still_swallowed_and_records_event(self):
        with patch("app.services.email_service.resend.Emails.send", side_effect=RuntimeError("smtp down")):
            # EmailService.send() must never raise — this call itself is the assertion.
            EmailService.send(to="user@example.com", subject="hi", body="body")

        self.assertEqual(
            MonitoringEventService.count_recent_failures(MonitoringEventService.EMAIL, 60), 1
        )


class HealthEngineScoringTests(unittest.TestCase):
    """Pure math — no DB required."""

    def test_all_healthy_scores_100(self):
        checks = {key: {"status": CheckStatus.HEALTHY} for key in HealthEngineService.WEIGHTS}
        self.assertEqual(HealthEngineService._score(checks), 100)

    def test_all_critical_scores_0(self):
        checks = {key: {"status": CheckStatus.CRITICAL} for key in HealthEngineService.WEIGHTS}
        self.assertEqual(HealthEngineService._score(checks), 0)

    def test_all_unknown_defaults_to_100(self):
        checks = {key: {"status": CheckStatus.UNKNOWN} for key in HealthEngineService.WEIGHTS}
        self.assertEqual(HealthEngineService._score(checks), 100)

    def test_unknown_checks_excluded_from_denominator(self):
        # Every weighted check healthy except one UNKNOWN — score must
        # still be 100 (unknown doesn't get averaged in as a failure).
        checks = {key: {"status": CheckStatus.HEALTHY} for key in HealthEngineService.WEIGHTS}
        checks["disk"] = {"status": CheckStatus.UNKNOWN}
        self.assertEqual(HealthEngineService._score(checks), 100)

    def test_warning_counts_as_half_credit(self):
        checks = {key: {"status": CheckStatus.HEALTHY} for key in HealthEngineService.WEIGHTS}
        checks["database"] = {"status": CheckStatus.WARNING}  # weight 15
        # total weighted = 100, database contributes 15*0.5 instead of 15 -> lose 7.5 -> 92.5 -> rounds to 92 or 93
        score = HealthEngineService._score(checks)
        self.assertTrue(90 <= score <= 95)

    def test_zero_weight_check_never_moves_score(self):
        checks = {key: {"status": CheckStatus.HEALTHY} for key in HealthEngineService.WEIGHTS}
        checks["growth_intelligence"] = {"status": CheckStatus.CRITICAL}
        self.assertEqual(HealthEngineService._score(checks), 100)

    def test_overall_status_healthy(self):
        checks = {key: {"status": CheckStatus.HEALTHY} for key in HealthEngineService.WEIGHTS}
        self.assertEqual(HealthEngineService._overall_status(100, checks), "healthy")

    def test_overall_status_degraded_on_any_warning(self):
        checks = {key: {"status": CheckStatus.HEALTHY} for key in HealthEngineService.WEIGHTS}
        checks["cpu"] = {"status": CheckStatus.WARNING}
        status = HealthEngineService._overall_status(HealthEngineService._score(checks), checks)
        self.assertEqual(status, "degraded")

    def test_overall_status_critical_on_any_critical_even_if_score_high(self):
        # A single critical check (e.g. sqlite_integrity, low weight-share
        # in a mostly-healthy system) must never be masked by an otherwise
        # high score — sprint requires hard-blocker checks to surface.
        checks = {key: {"status": CheckStatus.HEALTHY} for key in HealthEngineService.WEIGHTS}
        checks["email"] = {"status": CheckStatus.CRITICAL}  # small weight, score stays high
        score = HealthEngineService._score(checks)
        self.assertGreaterEqual(score, 90)
        self.assertEqual(HealthEngineService._overall_status(score, checks), "critical")

    def test_safe_wraps_failing_check_as_unknown(self):
        def _boom():
            raise RuntimeError("boom")

        result = HealthEngineService._safe(_boom)

        self.assertEqual(result["status"], CheckStatus.UNKNOWN)


class HealthEngineCheckThresholdTests(unittest.TestCase):
    """Boundary mapping for each check, with underlying reused services
    patched so thresholds can be tested deterministically.
    """

    def test_disk_healthy_below_warning(self):
        with patch("app.services.health_engine_service.HealthService.get_disk_usage", return_value={"percent_free": 20.0}):
            result = HealthEngineService._check_disk()
        self.assertEqual(result["status"], CheckStatus.HEALTHY)

    def test_disk_warning_at_exact_boundary(self):
        # 85% used == HEALTH_DISK_WARNING_PERCENT_USED (85.0) -> warning (>=).
        with patch("app.services.health_engine_service.HealthService.get_disk_usage", return_value={"percent_free": 15.0}):
            result = HealthEngineService._check_disk()
        self.assertEqual(result["status"], CheckStatus.WARNING)

    def test_disk_just_below_warning_boundary_is_healthy(self):
        with patch("app.services.health_engine_service.HealthService.get_disk_usage", return_value={"percent_free": 15.01}):
            result = HealthEngineService._check_disk()
        self.assertEqual(result["status"], CheckStatus.HEALTHY)

    def test_disk_critical_at_exact_boundary(self):
        with patch("app.services.health_engine_service.HealthService.get_disk_usage", return_value={"percent_free": 5.0}):
            result = HealthEngineService._check_disk()
        self.assertEqual(result["status"], CheckStatus.CRITICAL)

    def test_disk_unknown_when_percent_free_missing(self):
        with patch("app.services.health_engine_service.HealthService.get_disk_usage", return_value={"percent_free": None}):
            result = HealthEngineService._check_disk()
        self.assertEqual(result["status"], CheckStatus.UNKNOWN)

    def test_memory_unknown_on_unsupported_platform(self):
        with patch(
            "app.services.health_engine_service.HealthService.get_memory_usage",
            return_value={"status": "unknown", "percent_used": None},
        ):
            result = HealthEngineService._check_memory()
        self.assertEqual(result["status"], CheckStatus.UNKNOWN)

    def test_memory_critical_above_threshold(self):
        with patch(
            "app.services.health_engine_service.HealthService.get_memory_usage",
            return_value={"status": "ok", "percent_used": 96.0},
        ):
            result = HealthEngineService._check_memory()
        self.assertEqual(result["status"], CheckStatus.CRITICAL)

    def test_cpu_warning_above_threshold(self):
        with patch(
            "app.services.health_engine_service.HealthService.get_cpu_usage",
            return_value={"status": "ok", "load_ratio": 0.9},
        ):
            result = HealthEngineService._check_cpu()
        self.assertEqual(result["status"], CheckStatus.WARNING)

    def test_queue_warning_above_multiplier(self):
        with patch(
            "app.services.health_engine_service.OpsService.get_queue",
            return_value={"status": "ok", "queue_depth": 20, "max_concurrent_jobs": 4},
        ):
            result = HealthEngineService._check_queue()
        # threshold = 4 * 3.0 = 12, depth 20 > 12 -> warning
        self.assertEqual(result["status"], CheckStatus.WARNING)

    def test_queue_healthy_within_multiplier(self):
        with patch(
            "app.services.health_engine_service.OpsService.get_queue",
            return_value={"status": "ok", "queue_depth": 5, "max_concurrent_jobs": 4},
        ):
            result = HealthEngineService._check_queue()
        self.assertEqual(result["status"], CheckStatus.HEALTHY)

    def test_ai_pipeline_healthy_with_zero_jobs_no_division_error(self):
        with patch(
            "app.services.health_engine_service.OpsService.get_jobs",
            return_value={"status": "ok", "total_jobs": 0, "failed_jobs": 0},
        ):
            result = HealthEngineService._check_ai_pipeline()
        self.assertEqual(result["status"], CheckStatus.HEALTHY)

    def test_ai_pipeline_critical_above_critical_rate(self):
        with patch(
            "app.services.health_engine_service.OpsService.get_jobs",
            return_value={"status": "ok", "total_jobs": 10, "failed_jobs": 6},
        ):
            result = HealthEngineService._check_ai_pipeline()
        self.assertEqual(result["status"], CheckStatus.CRITICAL)

    def test_ai_pipeline_warning_between_thresholds(self):
        with patch(
            "app.services.health_engine_service.OpsService.get_jobs",
            return_value={"status": "ok", "total_jobs": 10, "failed_jobs": 3},
        ):
            result = HealthEngineService._check_ai_pipeline()
        self.assertEqual(result["status"], CheckStatus.WARNING)

    def test_payments_unknown_when_not_configured(self):
        with patch("app.services.health_engine_service.PaymentService.is_configured", return_value=False):
            result = HealthEngineService._check_payments()
        self.assertEqual(result["status"], CheckStatus.UNKNOWN)

    def test_payments_warning_above_failure_count(self):
        with patch("app.services.health_engine_service.PaymentService.is_configured", return_value=True), patch(
            "app.services.health_engine_service.MonitoringEventService.count_recent_failures", return_value=3
        ):
            result = HealthEngineService._check_payments()
        self.assertEqual(result["status"], CheckStatus.WARNING)

    def test_email_healthy_below_failure_count(self):
        with patch(
            "app.services.health_engine_service.MonitoringEventService.count_recent_failures", return_value=1
        ):
            result = HealthEngineService._check_email()
        self.assertEqual(result["status"], CheckStatus.HEALTHY)

    def test_backups_unknown_when_no_status_file(self):
        with patch(
            "app.services.health_engine_service.HealthService.get_backup_status",
            return_value={"status": "unknown", "stale": None},
        ), patch(
            "app.services.health_engine_service.HealthService.verify_latest_backup_restorable",
            return_value={"status": "unknown"},
        ):
            result = HealthEngineService._check_backups()
        self.assertEqual(result["status"], CheckStatus.UNKNOWN)

    def test_backups_critical_when_last_run_failed(self):
        with patch(
            "app.services.health_engine_service.HealthService.get_backup_status",
            return_value={"status": "unhealthy", "stale": None},
        ), patch(
            "app.services.health_engine_service.HealthService.verify_latest_backup_restorable",
            return_value={"status": "healthy"},
        ):
            result = HealthEngineService._check_backups()
        self.assertEqual(result["status"], CheckStatus.CRITICAL)

    def test_backups_warning_when_stale(self):
        with patch(
            "app.services.health_engine_service.HealthService.get_backup_status",
            return_value={"status": "healthy", "stale": True},
        ), patch(
            "app.services.health_engine_service.HealthService.verify_latest_backup_restorable",
            return_value={"status": "healthy"},
        ):
            result = HealthEngineService._check_backups()
        self.assertEqual(result["status"], CheckStatus.WARNING)

    def test_backups_critical_when_restore_verification_fails(self):
        with patch(
            "app.services.health_engine_service.HealthService.get_backup_status",
            return_value={"status": "healthy", "stale": False},
        ), patch(
            "app.services.health_engine_service.HealthService.verify_latest_backup_restorable",
            return_value={"status": "unhealthy"},
        ):
            result = HealthEngineService._check_backups()
        self.assertEqual(result["status"], CheckStatus.CRITICAL)

    def test_backups_healthy_when_current_and_verified(self):
        with patch(
            "app.services.health_engine_service.HealthService.get_backup_status",
            return_value={"status": "healthy", "stale": False},
        ), patch(
            "app.services.health_engine_service.HealthService.verify_latest_backup_restorable",
            return_value={"status": "healthy"},
        ):
            result = HealthEngineService._check_backups()
        self.assertEqual(result["status"], CheckStatus.HEALTHY)

    def test_frontend_unknown_when_url_not_configured(self):
        original = settings.FRONTEND_URL
        settings.FRONTEND_URL = ""
        try:
            result = HealthEngineService._check_frontend()
        finally:
            settings.FRONTEND_URL = original
        self.assertEqual(result["status"], CheckStatus.UNKNOWN)

    def test_frontend_healthy_when_reachable(self):
        fake_response = MagicMock(status_code=200)
        with patch("app.services.health_engine_service.requests.get", return_value=fake_response):
            result = HealthEngineService._check_frontend()
        self.assertEqual(result["status"], CheckStatus.HEALTHY)

    def test_frontend_warning_when_unreachable(self):
        with patch("app.services.health_engine_service.requests.get", side_effect=RuntimeError("timeout")):
            result = HealthEngineService._check_frontend()
        self.assertEqual(result["status"], CheckStatus.WARNING)

    def test_growth_intelligence_healthy_when_mission_control_succeeds(self):
        with patch("app.services.health_engine_service.MissionControlService.get_summary", return_value={}):
            result = HealthEngineService._check_growth_intelligence()
        self.assertEqual(result["status"], CheckStatus.HEALTHY)

    def test_growth_intelligence_critical_when_mission_control_raises(self):
        with patch(
            "app.services.health_engine_service.MissionControlService.get_summary",
            side_effect=RuntimeError("db down"),
        ):
            result = HealthEngineService._check_growth_intelligence()
        self.assertEqual(result["status"], CheckStatus.CRITICAL)


class HealthEngineEvaluateIntegrationTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = _make_isolated_db()

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_evaluate_returns_full_shape(self):
        report = HealthEngineService.evaluate(use_cache=False)

        self.assertIn("score", report)
        self.assertIn("status", report)
        self.assertIn("generated_at", report)
        self.assertEqual(set(report["checks"].keys()), set(HealthEngineService.WEIGHTS.keys()))
        for entry in report["checks"].values():
            self.assertIn(entry["status"], (CheckStatus.HEALTHY, CheckStatus.WARNING, CheckStatus.CRITICAL, CheckStatus.UNKNOWN))

    def test_evaluate_is_cached_within_ttl(self):
        first = HealthEngineService.evaluate(use_cache=True)
        second = HealthEngineService.evaluate(use_cache=True)
        self.assertEqual(first["generated_at"], second["generated_at"])

    def test_evaluate_bypasses_cache_when_requested(self):
        first = HealthEngineService.evaluate(use_cache=False)
        second = HealthEngineService.evaluate(use_cache=False)
        # Not asserting inequality of timestamps (could tie at second
        # resolution) — just that no exception occurs recomputing twice.
        self.assertIsInstance(first["score"], int)
        self.assertIsInstance(second["score"], int)

    def test_elevated_ai_pipeline_failures_lower_score_and_status(self):
        for _ in range(8):
            _insert_job("failed")
        for _ in range(2):
            _insert_job("completed")

        report = HealthEngineService.evaluate(use_cache=False)

        self.assertEqual(report["checks"]["ai_pipeline"]["status"], CheckStatus.CRITICAL)
        self.assertEqual(report["status"], "critical")


class AlertEngineServiceTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = _make_isolated_db()

    def tearDown(self):
        self._tmp_dir.cleanup()

    def _report(self, check_id: str, status: str) -> dict:
        return {
            "score": 50,
            "status": "critical",
            "generated_at": datetime.utcnow().isoformat(),
            "checks": {check_id: {"status": status, "message": "test failure", "evidence": {"foo": "bar"}}},
        }

    def test_raises_alert_with_all_mandated_fields(self):
        AlertEngineService.evaluate_and_raise(self._report("disk", CheckStatus.CRITICAL))

        alerts = AlertEngineService.get_open_alerts()

        self.assertEqual(len(alerts), 1)
        alert = alerts[0]
        for field in ("severity", "root_cause", "evidence", "suggested_fix", "time"):
            self.assertIn(field, alert)
        self.assertEqual(alert["severity"], "critical")
        self.assertTrue(alert["root_cause"])
        self.assertTrue(alert["suggested_fix"])

    def test_dedup_does_not_create_duplicate_open_alerts(self):
        AlertEngineService.evaluate_and_raise(self._report("disk", CheckStatus.CRITICAL))
        AlertEngineService.evaluate_and_raise(self._report("disk", CheckStatus.CRITICAL))
        AlertEngineService.evaluate_and_raise(self._report("disk", CheckStatus.CRITICAL))

        alerts = AlertEngineService.get_open_alerts()

        self.assertEqual(len(alerts), 1)

    def test_recovery_auto_resolves_open_alert(self):
        AlertEngineService.evaluate_and_raise(self._report("disk", CheckStatus.CRITICAL))
        self.assertEqual(len(AlertEngineService.get_open_alerts()), 1)

        AlertEngineService.evaluate_and_raise(self._report("disk", CheckStatus.HEALTHY))

        self.assertEqual(len(AlertEngineService.get_open_alerts()), 0)
        resolved = AlertEngineService.list_alerts(resolved=True)
        self.assertEqual(len(resolved), 1)
        self.assertIsNotNone(resolved[0]["resolved_at"])

    def test_re_breaking_after_recovery_opens_a_new_alert(self):
        AlertEngineService.evaluate_and_raise(self._report("disk", CheckStatus.CRITICAL))
        AlertEngineService.evaluate_and_raise(self._report("disk", CheckStatus.HEALTHY))
        AlertEngineService.evaluate_and_raise(self._report("disk", CheckStatus.WARNING))

        open_alerts = AlertEngineService.get_open_alerts()
        self.assertEqual(len(open_alerts), 1)
        self.assertEqual(open_alerts[0]["severity"], "warning")

    def test_list_alerts_never_raises_on_broken_db(self):
        DatabaseService.DB_PATH = Path("Z:/nonexistent/does-not-exist.db")
        self.assertEqual(AlertEngineService.list_alerts(), [])


class HealthHistoryServiceTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = _make_isolated_db()

    def tearDown(self):
        self._tmp_dir.cleanup()

    def _snapshot(self, score: int, status: str, created_at: str) -> None:
        connection = DatabaseService.get_connection()
        connection.execute(
            "INSERT INTO health_snapshots (created_at, score, status, checks_json) VALUES (?, ?, ?, '{}')",
            (created_at, score, status),
        )
        connection.commit()
        connection.close()

    def test_record_snapshot_persists_row(self):
        HealthHistoryService.record_snapshot(
            {"generated_at": datetime.utcnow().isoformat(), "score": 88, "status": "degraded", "checks": {"disk": {"status": "warning"}}}
        )

        history = HealthHistoryService.get_history("today")
        self.assertEqual(len(history["snapshots"]), 1)
        self.assertEqual(history["snapshots"][0]["score"], 88)

    def test_today_range_excludes_yesterday(self):
        now = datetime.utcnow()
        self._snapshot(90, "healthy", now.isoformat())
        self._snapshot(50, "critical", (now - timedelta(days=1)).isoformat())

        history = HealthHistoryService.get_history("today")

        self.assertEqual(len(history["snapshots"]), 1)
        self.assertEqual(history["snapshots"][0]["score"], 90)

    def test_yesterday_range_excludes_today(self):
        now = datetime.utcnow()
        self._snapshot(90, "healthy", now.isoformat())
        self._snapshot(50, "critical", (now - timedelta(days=1)).isoformat())

        history = HealthHistoryService.get_history("yesterday")

        self.assertEqual(len(history["snapshots"]), 1)
        self.assertEqual(history["snapshots"][0]["score"], 50)

    def test_7d_and_30d_ranges_include_older_snapshots(self):
        now = datetime.utcnow()
        self._snapshot(70, "degraded", (now - timedelta(days=5)).isoformat())
        self._snapshot(60, "degraded", (now - timedelta(days=20)).isoformat())

        history_7d = HealthHistoryService.get_history("7d")
        history_30d = HealthHistoryService.get_history("30d")

        self.assertEqual(len(history_7d["snapshots"]), 1)
        self.assertEqual(len(history_30d["snapshots"]), 2)

    def test_invalid_range_falls_back_to_today(self):
        history = HealthHistoryService.get_history("nonsense")
        self.assertEqual(history["range"], "today")

    def test_trend_empty_state(self):
        history = HealthHistoryService.get_history("today")
        self.assertEqual(history["trend"]["direction"], "unknown")
        self.assertIsNone(history["trend"]["avg_score"])

    def test_trend_direction_improving(self):
        now = datetime.utcnow()
        self._snapshot(60, "degraded", (now - timedelta(hours=2)).isoformat())
        self._snapshot(90, "healthy", now.isoformat())

        history = HealthHistoryService.get_history("today")

        self.assertEqual(history["trend"]["direction"], "improving")
        self.assertEqual(history["trend"]["current_score"], 90)
        self.assertEqual(history["trend"]["min_score"], 60)
        self.assertEqual(history["trend"]["max_score"], 90)

    def test_trend_direction_declining(self):
        now = datetime.utcnow()
        self._snapshot(90, "healthy", (now - timedelta(hours=2)).isoformat())
        self._snapshot(60, "degraded", now.isoformat())

        history = HealthHistoryService.get_history("today")

        self.assertEqual(history["trend"]["direction"], "declining")


class HealthSchedulerServiceTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = _make_isolated_db()

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_run_once_persists_snapshot_and_alerts(self):
        for _ in range(9):
            _insert_job("failed")
        _insert_job("completed")

        report = HealthSchedulerService.run_once()

        self.assertIn("score", report)

        history = HealthHistoryService.get_history("today")
        self.assertEqual(len(history["snapshots"]), 1)

        open_alerts = AlertEngineService.get_open_alerts()
        self.assertTrue(any(a["check_id"] == "ai_pipeline" for a in open_alerts))

    def test_run_once_never_raises_on_internal_failure(self):
        with patch(
            "app.services.health_scheduler_service.HealthEngineService.evaluate",
            side_effect=RuntimeError("boom"),
        ):
            result = HealthSchedulerService.run_once()

        self.assertEqual(result, {})


class AdminHealthEndpointTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = _make_isolated_db()
        self.app = FastAPI()
        self.app.include_router(admin_health_router_module.router)
        self.client = TestClient(self.app)

    def tearDown(self):
        self._tmp_dir.cleanup()
        self.app.dependency_overrides.clear()

    def test_non_admin_rejected_on_summary(self):
        self.app.dependency_overrides[get_current_user] = lambda: {"id": 1, "is_admin": 0}

        response = self.client.get("/admin/health/summary")

        self.assertEqual(response.status_code, 403)

    def test_admin_gets_summary_with_score_status_checks_alerts(self):
        self.app.dependency_overrides[get_current_user] = lambda: {"id": 1, "is_admin": 1}

        response = self.client.get("/admin/health/summary")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("score", body)
        self.assertIn("status", body)
        self.assertIn("checks", body)
        self.assertIn("open_alerts", body)

    def test_history_endpoint_accepts_valid_ranges(self):
        self.app.dependency_overrides[get_current_user] = lambda: {"id": 1, "is_admin": 1}

        for range_key in ("today", "yesterday", "7d", "30d"):
            response = self.client.get(f"/admin/health/history?range={range_key}")
            self.assertEqual(response.status_code, 200, range_key)
            self.assertEqual(response.json()["range"], range_key)

    def test_history_endpoint_rejects_invalid_range(self):
        self.app.dependency_overrides[get_current_user] = lambda: {"id": 1, "is_admin": 1}

        response = self.client.get("/admin/health/history?range=nonsense")

        self.assertEqual(response.status_code, 422)

    def test_alerts_endpoint_requires_admin(self):
        self.app.dependency_overrides[get_current_user] = lambda: {"id": 1, "is_admin": 0}

        response = self.client.get("/admin/health/alerts")

        self.assertEqual(response.status_code, 403)

    def test_alerts_endpoint_returns_list(self):
        self.app.dependency_overrides[get_current_user] = lambda: {"id": 1, "is_admin": 1}

        response = self.client.get("/admin/health/alerts")

        self.assertEqual(response.status_code, 200)
        self.assertIn("alerts", response.json())


class OpsProductionHealthEndpointTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = _make_isolated_db()
        self._original_key = settings.OPS_API_KEY
        settings.OPS_API_KEY = _TEST_OPS_KEY
        self.app = FastAPI()
        self.app.include_router(ops_router_module.router)
        self.client = TestClient(self.app)

    def tearDown(self):
        self._tmp_dir.cleanup()
        settings.OPS_API_KEY = self._original_key
        self.app.dependency_overrides.clear()

    def test_rejects_missing_key(self):
        response = self.client.get("/api/v1/ops/production-health")
        self.assertEqual(response.status_code, 401)

    def test_accepts_correct_key_and_returns_shape(self):
        response = self.client.get(
            "/api/v1/ops/production-health",
            headers={"Authorization": f"Bearer {_TEST_OPS_KEY}"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(
            set(body.keys()),
            {"status", "score", "production_status", "generated_at", "checks"},
        )
        self.assertEqual(body["status"], "ok")

    def test_failure_degrades_to_unavailable_without_breaking_other_endpoints(self):
        self.app.dependency_overrides[verify_ops_api_key] = lambda: None

        with patch.object(OpsService, "_compute_production_health", side_effect=RuntimeError("boom")):
            response = self.client.get("/api/v1/ops/production-health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "unavailable"})

    def test_capabilities_and_summary_contracts_are_unchanged(self):
        # VED-P1-002 must not touch the CR-037/CR-038 contracts already
        # covered by test_ops.py — this is a guard against accidental
        # drift, not a duplicate of those tests.
        self.app.dependency_overrides[verify_ops_api_key] = lambda: None

        capabilities = self.client.get("/api/v1/ops/capabilities").json()
        self.assertEqual(
            capabilities["features"],
            ["health", "system", "jobs", "storage", "users", "queue", "summary"],
        )

        summary = self.client.get("/api/v1/ops/summary").json()
        self.assertEqual(set(summary.keys()), {"health", "jobs", "storage", "users", "queue"})


if __name__ == "__main__":
    unittest.main()
