"""VED-085: Mission Control founder dashboard.

Covers three layers:
  - require_admin rejects non-admin users and allows admins (dependency unit test)
  - GET /admin/mission-control/summary is gated end-to-end through the router
  - MissionControlService aggregate queries and deterministic blocker rules
    produce correct results against fixture data in an isolated DB
"""

import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.dependencies import get_current_user, require_admin
from app.routers import mission_control as mission_control_router_module
from app.services.database_service import DatabaseService
from app.services.mission_control_service import MissionControlService
from app.services.subscription_service import (
    SubscriptionPlan,
    SubscriptionStatus,
    SubscriptionService,
)


def _make_isolated_db():
    tmp_dir = tempfile.TemporaryDirectory()
    DatabaseService.DB_DIR = Path(tmp_dir.name)
    DatabaseService.DB_PATH = Path(tmp_dir.name) / "test_agc.db"
    DatabaseService.initialize()
    return tmp_dir


def _create_user(
    email: str,
    is_admin: bool = False,
    credits_remaining=None,
    is_internal: bool = False,
) -> int:
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

    SubscriptionService.create_default_subscription(user_id)

    if is_admin or is_internal or credits_remaining is not None:
        connection = DatabaseService.get_connection()
        cursor = connection.cursor()
        if is_admin:
            cursor.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (user_id,))
        if is_internal:
            cursor.execute("UPDATE users SET is_internal = 1 WHERE id = ?", (user_id,))
        if credits_remaining is not None:
            cursor.execute(
                "UPDATE users SET credits_remaining = ? WHERE id = ?",
                (credits_remaining, user_id),
            )
        connection.commit()
        connection.close()

    return user_id


def _insert_job(user_id: int, status: str, created_at: str = None) -> None:
    connection = DatabaseService.get_connection()
    cursor = connection.cursor()
    now = created_at or datetime.utcnow().isoformat()
    cursor.execute(
        """
        INSERT INTO jobs (job_id, user_id, status, progress, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (f"job-{user_id}-{status}-{uuid4().hex}", user_id, status, 0, now),
    )
    connection.commit()
    connection.close()


def _insert_feedback(user_id: int) -> None:
    connection = DatabaseService.get_connection()
    cursor = connection.cursor()
    now = datetime.utcnow().isoformat()
    cursor.execute(
        """
        INSERT INTO feedback (user_id, project_id, rating, thumbs, comment, created_at)
        VALUES (?, NULL, 5, 'up', 'great', ?)
        """,
        (user_id, now),
    )
    connection.commit()
    connection.close()


def _insert_feedback_with_rating(
    user_id: int, rating: int, improvement_area: str = None, project_id: int = None
) -> None:
    connection = DatabaseService.get_connection()
    cursor = connection.cursor()
    now = datetime.utcnow().isoformat()
    cursor.execute(
        """
        INSERT INTO feedback (user_id, project_id, rating, improvement_area, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, project_id, rating, improvement_area, now),
    )
    connection.commit()
    connection.close()


def _insert_payment(user_id: int) -> None:
    connection = DatabaseService.get_connection()
    cursor = connection.cursor()
    now = datetime.utcnow().isoformat()
    cursor.execute(
        """
        INSERT INTO payments (
            user_id, razorpay_order_id, razorpay_payment_id,
            plan, status, created_at, processed_at
        )
        VALUES (?, ?, ?, 'pro', 'PROCESSED', ?, ?)
        """,
        (user_id, f"order-{user_id}", f"pay-{user_id}", now, now),
    )
    connection.commit()
    connection.close()


class RequireAdminDependencyTests(unittest.TestCase):

    def test_rejects_non_admin_user(self):
        with self.assertRaises(HTTPException) as ctx:
            require_admin(current_user={"id": 1, "is_admin": 0})

        self.assertEqual(ctx.exception.status_code, 403)

    def test_rejects_missing_is_admin_field(self):
        with self.assertRaises(HTTPException) as ctx:
            require_admin(current_user={"id": 1})

        self.assertEqual(ctx.exception.status_code, 403)

    def test_allows_admin_user(self):
        user = {"id": 1, "is_admin": 1}
        self.assertEqual(require_admin(current_user=user), user)


class MissionControlEndpointTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = _make_isolated_db()
        self.app = FastAPI()
        self.app.include_router(mission_control_router_module.router)
        self.client = TestClient(self.app)

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_non_admin_gets_403(self):
        self.app.dependency_overrides[get_current_user] = lambda: {
            "id": 1,
            "is_admin": 0,
        }

        response = self.client.get("/admin/mission-control/summary")

        self.assertEqual(response.status_code, 403)

    def test_admin_gets_200_with_expected_sections(self):
        self.app.dependency_overrides[get_current_user] = lambda: {
            "id": 1,
            "is_admin": 1,
        }

        response = self.client.get("/admin/mission-control/summary")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(
            set(body.keys()),
            {
                "production_health",
                "live_metrics",
                "distribution",
                "capability_registry",
                "blockers",
                "release",
                "weekly_activity",
                "social_integrations",
                "feedback_summary",
                "segmentation",
            },
        )

    def test_unauthenticated_request_is_rejected(self):
        # No dependency override: falls through to the real get_current_user,
        # which requires a bearer token.
        response = self.client.get("/admin/mission-control/summary")

        self.assertEqual(response.status_code, 401)


class MissionControlServiceMetricsTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = _make_isolated_db()

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_live_metrics_counts(self):
        u1 = _create_user("u1@test.com")
        u2 = _create_user("u2@test.com")
        _create_user("u3@test.com")

        connection = DatabaseService.get_connection()
        cursor = connection.cursor()
        cursor.execute("UPDATE users SET email_verified = 1 WHERE id = ?", (u1,))
        connection.commit()
        connection.close()

        # u1's two jobs land on distinct calendar dates so it still counts
        # as a repeat user under the GROW-007 distinct-date definition.
        _insert_job(u1, "completed", created_at="2026-01-01T10:00:00")
        _insert_job(u1, "completed", created_at="2026-01-02T10:00:00")
        _insert_job(u2, "failed")

        _insert_feedback(u1)
        _insert_payment(u1)

        SubscriptionService.upgrade_to_pro(u2)

        metrics = MissionControlService._get_live_metrics()

        self.assertEqual(metrics["total_users"], 3)
        self.assertEqual(metrics["verified_users"], 1)
        self.assertEqual(metrics["users_with_jobs"], 2)
        self.assertEqual(metrics["users_with_completed_jobs"], 1)
        self.assertEqual(metrics["repeat_users"], 1)
        self.assertEqual(metrics["total_jobs"], 3)
        self.assertEqual(metrics["completed_jobs"], 2)
        self.assertEqual(metrics["failed_jobs"], 1)
        self.assertEqual(metrics["active_pro_users"], 1)
        self.assertEqual(metrics["processed_payments"], 1)
        self.assertEqual(metrics["distinct_feedback_users"], 1)

    def test_expired_pro_is_not_counted_active(self):
        user_id = _create_user("expired@test.com")
        past = (datetime.utcnow() - timedelta(days=1)).isoformat()

        connection = DatabaseService.get_connection()
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE subscriptions SET plan = ?, status = ?, expires_at = ? WHERE user_id = ?",
            (SubscriptionPlan.PRO, SubscriptionStatus.ACTIVE, past, user_id),
        )
        connection.commit()
        connection.close()

        metrics = MissionControlService._get_live_metrics()

        self.assertEqual(metrics["active_pro_users"], 0)

    def test_distribution_credit_and_job_buckets(self):
        u1 = _create_user("a@test.com", credits_remaining=0)
        u2 = _create_user("b@test.com", credits_remaining=1)
        u3 = _create_user("c@test.com", credits_remaining=3)

        for _ in range(6):
            _insert_job(u3, "completed")
        _insert_job(u2, "completed")
        _insert_job(u2, "completed")
        _insert_job(u1, "completed")

        distribution = MissionControlService._get_distribution()

        self.assertEqual(distribution["credit_breakdown"]["exhausted"], 1)
        self.assertEqual(distribution["credit_breakdown"]["low"], 1)
        self.assertEqual(distribution["credit_breakdown"]["healthy"], 1)

        self.assertEqual(distribution["jobs_per_user"]["1"], 1)
        self.assertEqual(distribution["jobs_per_user"]["2-3"], 1)
        self.assertEqual(distribution["jobs_per_user"]["4-5"], 0)
        self.assertEqual(distribution["jobs_per_user"]["6+"], 1)


class MissionControlFeedbackSummaryTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = _make_isolated_db()

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_feedback_summary_defaults_on_empty_db(self):
        summary = MissionControlService._get_feedback_summary()

        self.assertEqual(summary["total_responses"], 0)
        self.assertIsNone(summary["positive_rate"])
        self.assertEqual(
            summary["rating_distribution"],
            {"great": 0, "good": 0, "okay": 0, "bad": 0},
        )
        self.assertIsNone(summary["top_improvement_area"])

    def test_feedback_summary_aggregates_ratings_positive_rate_and_top_area(self):
        u1 = _create_user("fb1@test.com")
        u2 = _create_user("fb2@test.com")
        u3 = _create_user("fb3@test.com")
        u4 = _create_user("fb4@test.com")

        _insert_feedback_with_rating(u1, rating=4, improvement_area="clip_timing")
        _insert_feedback_with_rating(u2, rating=4, improvement_area="clip_timing")
        _insert_feedback_with_rating(u3, rating=3, improvement_area="captions")
        _insert_feedback_with_rating(u4, rating=1)

        summary = MissionControlService._get_feedback_summary()

        self.assertEqual(summary["total_responses"], 4)
        self.assertEqual(
            summary["rating_distribution"],
            {"great": 2, "good": 1, "okay": 0, "bad": 1},
        )
        # 3 of 4 ratings are Good/Great -> 75.0%
        self.assertEqual(summary["positive_rate"], 75.0)
        self.assertEqual(summary["top_improvement_area"], "clip_timing")

    def test_no_sensitive_or_per_user_data_in_feedback_summary(self):
        summary = MissionControlService.get_summary()

        serialized = str(summary["feedback_summary"]).lower()
        for forbidden in ("comment", "user_id", "email"):
            self.assertNotIn(forbidden, serialized)

    def test_legacy_out_of_range_rating_does_not_corrupt_positive_rate(self):
        # A pre-GROW-005 row could have rating=5 (the old 1-5 scale's top
        # value), which isn't one of the four approved labels. It must be
        # excluded from BOTH the numerator and denominator together, not
        # just left out of the numerator while still inflating total_rated.
        u1 = _create_user("legacy1@test.com")
        u2 = _create_user("legacy2@test.com")

        _insert_feedback_with_rating(u1, rating=4)  # great, approved scale
        _insert_feedback_with_rating(u2, rating=5)  # legacy, out of range

        summary = MissionControlService._get_feedback_summary()

        self.assertEqual(summary["total_responses"], 2)
        # Only the rating=4 row counts toward the distribution/positive_rate.
        self.assertEqual(
            summary["rating_distribution"],
            {"great": 1, "good": 0, "okay": 0, "bad": 0},
        )
        self.assertEqual(summary["positive_rate"], 100.0)

    def test_top_improvement_area_tie_break_is_deterministic(self):
        u1 = _create_user("tie1@test.com")
        u2 = _create_user("tie2@test.com")

        _insert_feedback_with_rating(u1, rating=2, improvement_area="processing_speed")
        _insert_feedback_with_rating(u2, rating=2, improvement_area="captions")

        summary = MissionControlService._get_feedback_summary()

        # Tied 1-1 on count; alphabetical tiebreaker picks "captions".
        self.assertEqual(summary["top_improvement_area"], "captions")


class MissionControlBlockerTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = _make_isolated_db()

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_zero_feedback_and_zero_payments_blockers_fire_on_empty_db(self):
        summary = MissionControlService.get_summary()

        blocker_ids = {b["id"] for b in summary["blockers"]}
        self.assertIn("zero_feedback_users", blocker_ids)
        self.assertIn("no_processed_payments", blocker_ids)

    def test_zero_feedback_blocker_absent_once_feedback_exists(self):
        user_id = _create_user("hasfeedback@test.com")
        _insert_feedback_with_rating(user_id, rating=4)

        summary = MissionControlService.get_summary()

        blocker_ids = {b["id"] for b in summary["blockers"]}
        self.assertNotIn("zero_feedback_users", blocker_ids)

    def test_elevated_failed_job_rate_blocker(self):
        user_id = _create_user("failrate@test.com")

        _insert_job(user_id, "completed")
        for _ in range(4):
            _insert_job(user_id, "failed")

        summary = MissionControlService.get_summary()

        blocker_ids = {b["id"] for b in summary["blockers"]}
        self.assertIn("elevated_failed_job_rate", blocker_ids)

    def test_low_failed_job_rate_does_not_trigger_blocker(self):
        user_id = _create_user("healthyrate@test.com")

        for _ in range(9):
            _insert_job(user_id, "completed")
        _insert_job(user_id, "failed")

        summary = MissionControlService.get_summary()

        blocker_ids = {b["id"] for b in summary["blockers"]}
        self.assertNotIn("elevated_failed_job_rate", blocker_ids)

    def test_users_exhausting_credits_blocker(self):
        _create_user("exhausted@test.com", credits_remaining=0)

        summary = MissionControlService.get_summary()

        blocker_ids = {b["id"] for b in summary["blockers"]}
        self.assertIn("users_exhausting_credits", blocker_ids)

    def test_no_sensitive_fields_in_summary(self):
        _create_user("secret@test.com")
        summary = MissionControlService.get_summary()

        serialized = str(summary).lower()
        for forbidden in ("password", "token", "secret", "api_key", "razorpay_key"):
            self.assertNotIn(forbidden, serialized)


class MissionControlWeeklyActivityTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = _make_isolated_db()

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_returns_seven_zero_filled_days_in_chronological_order(self):
        activity = MissionControlService._get_weekly_activity()

        self.assertEqual(len(activity), 7)

        today = datetime.utcnow().date()
        expected_dates = [
            (today - timedelta(days=offset)).isoformat() for offset in range(6, -1, -1)
        ]
        self.assertEqual([day["date"] for day in activity], expected_dates)

        for day in activity:
            self.assertEqual(day["total"], 0)
            self.assertEqual(day["completed"], 0)
            self.assertEqual(day["failed"], 0)

    def test_buckets_jobs_by_utc_calendar_day_with_status_breakdown(self):
        user_id = _create_user("activity@test.com")
        today = datetime.utcnow().date()
        two_days_ago = (datetime.utcnow() - timedelta(days=2)).isoformat()
        eight_days_ago = (datetime.utcnow() - timedelta(days=8)).isoformat()

        _insert_job(user_id, "completed", created_at=today.isoformat() + "T10:00:00")
        _insert_job(user_id, "failed", created_at=today.isoformat() + "T11:00:00")
        _insert_job(user_id, "completed", created_at=two_days_ago)
        # Outside the 7-day window — must not be counted anywhere.
        _insert_job(user_id, "completed", created_at=eight_days_ago)

        activity = MissionControlService._get_weekly_activity()
        by_date = {day["date"]: day for day in activity}

        self.assertEqual(by_date[today.isoformat()]["total"], 2)
        self.assertEqual(by_date[today.isoformat()]["completed"], 1)
        self.assertEqual(by_date[today.isoformat()]["failed"], 1)

        two_days_ago_key = (today - timedelta(days=2)).isoformat()
        self.assertEqual(by_date[two_days_ago_key]["total"], 1)
        self.assertEqual(by_date[two_days_ago_key]["completed"], 1)

        total_across_window = sum(day["total"] for day in activity)
        self.assertEqual(total_across_window, 3)

    def test_future_dated_jobs_are_excluded_from_the_window(self):
        # VED-086 CTO audit: a job whose created_at is ahead of the server's
        # own "now" (clock skew, bad test fixture, corrupted data) must not
        # be counted in any of the 7 buckets — including today's.
        user_id = _create_user("future@test.com")
        three_days_ahead = (datetime.utcnow() + timedelta(days=3)).isoformat()

        _insert_job(user_id, "completed", created_at=three_days_ahead)

        activity = MissionControlService._get_weekly_activity()

        self.assertEqual(len(activity), 7)
        total_across_window = sum(day["total"] for day in activity)
        self.assertEqual(total_across_window, 0)


class MissionControlSocialIntegrationsTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = _make_isolated_db()

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_returns_expected_platforms_all_not_connected(self):
        summary = MissionControlService.get_summary()
        integrations = summary["social_integrations"]

        self.assertEqual(
            {i["platform"] for i in integrations},
            {"Instagram", "YouTube", "LinkedIn", "X"},
        )
        for integration in integrations:
            self.assertEqual(integration["status"], "not_connected")
            self.assertEqual(set(integration.keys()), {"platform", "status"})


class MissionControlSegmentationTests(unittest.TestCase):
    """GROW-005.2: internal/test users must never inflate growth analytics,
    while still counting toward operational job/failure totals."""

    def setUp(self):
        self._tmp_dir = _make_isolated_db()

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_internal_user_excluded_external_user_included_in_live_metrics(self):
        external_user = _create_user("real-creator@test.com")
        internal_user = _create_user("founder-test@test.com", is_internal=True)

        connection = DatabaseService.get_connection()
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE users SET email_verified = 1 WHERE id IN (?, ?)",
            (external_user, internal_user),
        )
        connection.commit()
        connection.close()

        metrics = MissionControlService._get_live_metrics()

        self.assertEqual(metrics["total_users"], 1)
        self.assertEqual(metrics["internal_users"], 1)
        self.assertEqual(metrics["verified_users"], 1)

    def test_internal_jobs_excluded_from_growth_job_counts(self):
        external_user = _create_user("real-creator@test.com")
        internal_user = _create_user("founder-test@test.com", is_internal=True)

        _insert_job(external_user, "completed")
        _insert_job(external_user, "failed")
        _insert_job(internal_user, "completed")
        _insert_job(internal_user, "failed")

        metrics = MissionControlService._get_live_metrics()

        # Growth-facing counts only reflect the external user's jobs.
        self.assertEqual(metrics["external_total_jobs"], 2)
        self.assertEqual(metrics["external_completed_jobs"], 1)
        self.assertEqual(metrics["external_failed_jobs"], 1)
        self.assertEqual(metrics["internal_jobs"], 2)
        self.assertEqual(metrics["users_with_jobs"], 1)
        self.assertEqual(metrics["users_with_completed_jobs"], 1)

    def test_internal_jobs_still_counted_in_operational_totals(self):
        # A test job still consumed real server capacity, so total_jobs/
        # completed_jobs/failed_jobs (used for infra health and the
        # elevated_failed_job_rate blocker) must remain unfiltered.
        external_user = _create_user("real-creator@test.com")
        internal_user = _create_user("founder-test@test.com", is_internal=True)

        _insert_job(external_user, "completed")
        _insert_job(internal_user, "failed")

        metrics = MissionControlService._get_live_metrics()

        self.assertEqual(metrics["total_jobs"], 2)
        self.assertEqual(metrics["completed_jobs"], 1)
        self.assertEqual(metrics["failed_jobs"], 1)

    def test_null_owner_job_is_not_external(self):
        # CTO audit: a job with no resolvable owner has no deterministic
        # proof of external ownership and must NOT be counted as external
        # growth traction.
        _insert_job(None, "completed")

        metrics = MissionControlService._get_live_metrics()

        self.assertEqual(metrics["external_total_jobs"], 0)

    def test_null_owner_job_is_not_internal(self):
        _insert_job(None, "completed")

        metrics = MissionControlService._get_live_metrics()

        self.assertEqual(metrics["internal_jobs"], 0)

    def test_null_owner_job_is_counted_operationally(self):
        # Still real server workload — must count toward the unfiltered
        # operational totals even though it's excluded from both growth
        # buckets.
        _insert_job(None, "completed")

        metrics = MissionControlService._get_live_metrics()

        self.assertEqual(metrics["total_jobs"], 1)
        self.assertEqual(metrics["completed_jobs"], 1)
        self.assertEqual(metrics["unattributed_jobs"], 1)

    def test_null_owner_completed_job_does_not_inflate_external_completed_jobs(self):
        external_user = _create_user("ext@test.com")
        _insert_job(external_user, "completed")
        _insert_job(None, "completed")

        metrics = MissionControlService._get_live_metrics()

        self.assertEqual(metrics["external_completed_jobs"], 1)
        self.assertEqual(metrics["completed_jobs"], 2)

    def test_null_owner_failed_job_does_not_inflate_external_failed_jobs(self):
        external_user = _create_user("ext@test.com")
        _insert_job(external_user, "failed")
        _insert_job(None, "failed")

        metrics = MissionControlService._get_live_metrics()

        self.assertEqual(metrics["external_failed_jobs"], 1)
        self.assertEqual(metrics["failed_jobs"], 2)

    def test_segmentation_job_arithmetic_is_deterministic(self):
        external_user = _create_user("ext@test.com")
        internal_user = _create_user("int@test.com", is_internal=True)
        _insert_job(external_user, "completed")
        _insert_job(internal_user, "completed")
        _insert_job(internal_user, "failed")
        _insert_job(None, "completed")
        _insert_job(None, "failed")

        metrics = MissionControlService._get_live_metrics()

        self.assertEqual(
            metrics["external_total_jobs"]
            + metrics["internal_jobs"]
            + metrics["unattributed_jobs"],
            metrics["total_jobs"],
        )
        self.assertEqual(metrics["external_total_jobs"], 1)
        self.assertEqual(metrics["internal_jobs"], 2)
        self.assertEqual(metrics["unattributed_jobs"], 2)
        self.assertEqual(metrics["total_jobs"], 5)

    def test_distribution_excludes_internal_users_and_jobs(self):
        external_user = _create_user("ext@test.com", credits_remaining=0)
        internal_user = _create_user("int@test.com", credits_remaining=0, is_internal=True)

        _insert_job(external_user, "completed")
        for _ in range(5):
            _insert_job(internal_user, "completed")

        distribution = MissionControlService._get_distribution()

        self.assertEqual(distribution["credit_breakdown"]["exhausted"], 1)
        self.assertEqual(distribution["jobs_per_user"]["1"], 1)
        self.assertEqual(distribution["jobs_per_user"]["4-5"], 0)

    def test_internal_feedback_excluded_from_external_feedback_summary(self):
        external_user = _create_user("ext@test.com")
        internal_user = _create_user("int@test.com", is_internal=True)

        _insert_feedback_with_rating(external_user, rating=4)
        _insert_feedback_with_rating(internal_user, rating=1)

        summary = MissionControlService._get_feedback_summary()
        metrics = MissionControlService._get_live_metrics()

        self.assertEqual(summary["total_responses"], 1)
        self.assertEqual(
            summary["rating_distribution"],
            {"great": 1, "good": 0, "okay": 0, "bad": 0},
        )
        self.assertEqual(summary["positive_rate"], 100.0)
        self.assertEqual(metrics["distinct_feedback_users"], 1)

    def test_internal_only_feedback_does_not_clear_zero_feedback_blocker(self):
        internal_user = _create_user("int@test.com", is_internal=True)
        _insert_feedback_with_rating(internal_user, rating=4)

        summary = MissionControlService.get_summary()

        blocker_ids = {b["id"] for b in summary["blockers"]}
        self.assertIn("zero_feedback_users", blocker_ids)

    def test_external_feedback_clears_zero_feedback_blocker(self):
        external_user = _create_user("ext@test.com")
        _insert_feedback_with_rating(external_user, rating=4)

        summary = MissionControlService.get_summary()

        blocker_ids = {b["id"] for b in summary["blockers"]}
        self.assertNotIn("zero_feedback_users", blocker_ids)

    def test_internal_pro_subscription_excluded_from_active_pro_users_but_entitlement_unchanged(self):
        internal_user = _create_user("int@test.com", is_internal=True)
        SubscriptionService.upgrade_to_pro(internal_user)

        metrics = MissionControlService._get_live_metrics()
        self.assertEqual(metrics["active_pro_users"], 0)

        # Payment/subscription entitlement itself is untouched by segmentation.
        subscription = SubscriptionService.get_by_user_id(internal_user)
        self.assertEqual(subscription["plan"], SubscriptionPlan.PRO)
        self.assertEqual(subscription["status"], SubscriptionStatus.ACTIVE)

    def test_internal_payment_excluded_from_processed_payments(self):
        internal_user = _create_user("int@test.com", is_internal=True)
        _insert_payment(internal_user)

        metrics = MissionControlService._get_live_metrics()
        self.assertEqual(metrics["processed_payments"], 0)

    def test_segmentation_payload_counts_and_no_pii(self):
        external_user = _create_user("ext@test.com")
        internal_user = _create_user("int@test.com", is_internal=True)
        _insert_job(external_user, "completed")
        _insert_job(internal_user, "completed")
        _insert_job(None, "completed")

        summary = MissionControlService.get_summary()
        segmentation = summary["segmentation"]

        self.assertEqual(segmentation["external_users"], 1)
        self.assertEqual(segmentation["internal_users"], 1)
        self.assertEqual(segmentation["external_jobs"], 1)
        self.assertEqual(segmentation["internal_jobs"], 1)
        self.assertEqual(segmentation["unattributed_jobs"], 1)
        self.assertEqual(
            segmentation["external_jobs"] + segmentation["internal_jobs"] + segmentation["unattributed_jobs"],
            summary["live_metrics"]["total_jobs"],
        )

        serialized = str(summary).lower()
        for forbidden in ("ext@test.com", "int@test.com"):
            self.assertNotIn(forbidden, serialized)

    def test_empty_external_dataset_is_safe(self):
        # Only internal/unattributed users/jobs/feedback exist — external
        # metrics must be zero, not None/NaN/Infinity, and the summary call
        # must not raise.
        internal_user = _create_user("int@test.com", is_internal=True)
        _insert_job(internal_user, "failed")
        _insert_job(None, "completed")
        _insert_feedback_with_rating(internal_user, rating=1)

        summary = MissionControlService.get_summary()
        metrics = summary["live_metrics"]

        self.assertEqual(metrics["total_users"], 0)
        self.assertEqual(metrics["external_total_jobs"], 0)
        self.assertEqual(metrics["external_completed_jobs"], 0)
        self.assertEqual(metrics["external_failed_jobs"], 0)
        self.assertEqual(metrics["unattributed_jobs"], 1)
        self.assertEqual(metrics["users_with_jobs"], 0)
        self.assertEqual(summary["feedback_summary"]["total_responses"], 0)
        self.assertIsNone(summary["feedback_summary"]["positive_rate"])
        self.assertEqual(summary["distribution"]["credit_breakdown"]["exhausted"], 0)
        self.assertEqual(summary["distribution"]["credit_breakdown"]["low"], 0)
        self.assertEqual(summary["distribution"]["credit_breakdown"]["healthy"], 0)


class MissionControlRepeatUserTests(unittest.TestCase):
    """GROW-007: repeat_users must reflect jobs on >= 2 distinct calendar
    dates, not raw job count — same-session retries/reruns are not
    retention."""

    def setUp(self):
        self._tmp_dir = _make_isolated_db()

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_same_calendar_date_jobs_do_not_create_a_repeat_user(self):
        user_id = _create_user("sameday@test.com")
        _insert_job(user_id, "completed", created_at="2026-03-01T09:00:00")
        _insert_job(user_id, "completed", created_at="2026-03-01T18:00:00")
        _insert_job(user_id, "completed", created_at="2026-03-01T23:59:59")

        metrics = MissionControlService._get_live_metrics()

        self.assertEqual(metrics["repeat_users"], 0)

    def test_distinct_calendar_date_jobs_create_a_repeat_user(self):
        user_id = _create_user("twodays@test.com")
        _insert_job(user_id, "completed", created_at="2026-03-01T23:59:59")
        _insert_job(user_id, "completed", created_at="2026-03-02T00:00:01")

        metrics = MissionControlService._get_live_metrics()

        self.assertEqual(metrics["repeat_users"], 1)

    def test_internal_user_with_multi_date_jobs_excluded_from_repeat_users(self):
        internal_user = _create_user("internal-multi@test.com", is_internal=True)
        _insert_job(internal_user, "completed", created_at="2026-03-01T10:00:00")
        _insert_job(internal_user, "completed", created_at="2026-03-02T10:00:00")

        metrics = MissionControlService._get_live_metrics()

        self.assertEqual(metrics["repeat_users"], 0)

    def test_null_owner_jobs_do_not_create_a_repeat_user(self):
        _insert_job(None, "completed", created_at="2026-03-01T10:00:00")
        _insert_job(None, "completed", created_at="2026-03-02T10:00:00")

        metrics = MissionControlService._get_live_metrics()

        self.assertEqual(metrics["repeat_users"], 0)

    def test_repeat_users_is_zero_on_empty_dataset(self):
        metrics = MissionControlService._get_live_metrics()

        self.assertEqual(metrics["repeat_users"], 0)


if __name__ == "__main__":
    unittest.main()
