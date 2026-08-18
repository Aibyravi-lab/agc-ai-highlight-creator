"""Usage-limit roadmap item: credit refund on pipeline failure.

Production verification already proved real deduction, real successful
generations, and zero-credit 403 enforcement end-to-end against the live
system. The one remaining gap -- credit refund after a genuine mid-pipeline
failure -- has no safe, deterministic external trigger in production (the
only refund_credit call sites are: an in-pipeline exception, an immediate
create_job/start_job crash, or a server-restart reconciliation of an
interrupted job; see BackgroundJobService.run_pipeline, pipeline.py's
/start error handler, and JobService.reconcile_interrupted_jobs). This file
closes that gap with focused tests against the real AuthService.
deduct_credit / refund_credit implementation and an isolated SQLite DB,
mocking only PipelineService.process_video -- the actual external failure
boundary -- never AuthService.refund_credit itself, so real
credits_remaining values are asserted before and after.
"""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from app.services.auth_service import AuthService
from app.services.background_job_service import BackgroundJobService
from app.services.database_service import DatabaseService
from app.services.job_service import JobService


def _make_isolated_db():
    tmp_dir = tempfile.TemporaryDirectory()
    DatabaseService.DB_DIR = Path(tmp_dir.name)
    DatabaseService.DB_PATH = Path(tmp_dir.name) / "test_agc.db"
    DatabaseService.initialize()
    return tmp_dir


def _create_user(email: str, credits: int) -> int:
    connection = DatabaseService.get_connection()
    cursor = connection.cursor()
    now = datetime.utcnow().isoformat()

    cursor.execute(
        """
        INSERT INTO users (name, email, password_hash, created_at, credits_remaining)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("Test User", email, "hash", now, credits),
    )

    user_id = cursor.lastrowid
    connection.commit()
    connection.close()
    return user_id


def _credits(user_id: int) -> int:
    connection = DatabaseService.get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT credits_remaining FROM users WHERE id = ?", (user_id,)
    )
    value = cursor.fetchone()[0]
    connection.close()
    return value


class _IsolatedDbTestCase(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = _make_isolated_db()
        self.addCleanup(self._tmp_dir.cleanup)

        # Filesystem side effects unrelated to credit/refund logic, patched
        # the same way test_ved_p1_016_startup_reconciliation_hardening.py
        # patches them -- the real job-status/credit code still runs
        # against real DB rows, nothing here touches disk.
        for target in (
            "app.services.background_job_service.CleanupService.cleanup_temp_file",
            "app.services.background_job_service.CleanupService.cleanup",
            "app.services.background_job_service.LoggerService.info",
            "app.services.background_job_service.LoggerService.error",
        ):
            patcher = patch(target)
            patcher.start()
            self.addCleanup(patcher.stop)


class CreditDeductedBeforeJobStartTests(_IsolatedDbTestCase):
    """A: a credit is deducted before a pipeline job starts."""

    def test_start_video_processing_deducts_credit_before_job_creation(self):
        from app.routers import pipeline as pipeline_router

        user_id = _create_user("deduct-before-start@example.com", credits=3)
        current_user = {"id": user_id, "credits_remaining": 3}

        credits_at_create_job_call = {}

        def _record_credits_and_create(*, user_id):
            credits_at_create_job_call["value"] = _credits(user_id)
            return "job-recorded"

        with patch.object(
            pipeline_router.MaintenanceService,
            "is_maintenance_mode",
            return_value=False,
        ), patch.object(
            pipeline_router.VideoPathService,
            "validate_upload_path",
            side_effect=lambda path: path,
        ), patch.object(
            pipeline_router.BackgroundJobService,
            "is_accepting_jobs",
            return_value=True,
        ), patch.object(
            pipeline_router.RateLimitService,
            "is_rate_limited",
            return_value=False,
        ), patch.object(
            pipeline_router.JobService,
            "get_running_job_count",
            return_value=0,
        ), patch.object(
            pipeline_router.SubscriptionService,
            "is_pro_active",
            return_value=False,
        ), patch.object(
            pipeline_router.JobService,
            "create_job",
            side_effect=_record_credits_and_create,
        ), patch.object(
            pipeline_router.BackgroundJobService, "start_job"
        ) as mock_start_job:

            result = pipeline_router.start_video_processing(
                "video.mp4", current_user
            )

        self.assertTrue(result["success"])
        # The credit was already gone by the time create_job ran.
        self.assertEqual(credits_at_create_job_call["value"], 2)
        self.assertEqual(_credits(user_id), 2)
        mock_start_job.assert_called_once()


class PipelineFailureRefundTests(_IsolatedDbTestCase):
    """B, C, D, E: refund-on-failure, no-refund-on-success, no refund for
    PRO users, and no double refund via reconciliation.
    """

    def _job_with_deducted_credit(self, credits_before, is_pro=False):
        user_id = _create_user(
            f"refund-{credits_before}-{is_pro}@example.com",
            credits=credits_before,
        )
        if not is_pro:
            AuthService.deduct_credit(user_id)
        job_id = JobService.create_job(user_id=user_id)
        return user_id, job_id

    def test_pipeline_failure_refunds_exactly_one_credit(self):
        user_id, job_id = self._job_with_deducted_credit(credits_before=3)
        self.assertEqual(_credits(user_id), 2)

        with patch(
            "app.services.background_job_service.PipelineService.process_video",
            side_effect=RuntimeError("induced pipeline failure"),
        ), patch(
            "app.services.background_job_service.SubscriptionService.is_pro_active",
            return_value=False,
        ), patch(
            "app.services.background_job_service.AuthService.refund_credit",
            wraps=AuthService.refund_credit,
        ) as refund_spy:

            BackgroundJobService.run_pipeline(
                job_id=job_id, video_path="video.mp4", user_id=user_id
            )

        refund_spy.assert_called_once_with(user_id=user_id)
        self.assertEqual(_credits(user_id), 3)
        self.assertEqual(JobService.get_job(job_id)["status"], "failed")

    def test_successful_pipeline_does_not_refund(self):
        user_id, job_id = self._job_with_deducted_credit(credits_before=3)
        self.assertEqual(_credits(user_id), 2)

        fake_result = {"final_reel": "reels/x.mp4", "highlights": []}

        with patch(
            "app.services.background_job_service.PipelineService.process_video",
            return_value=fake_result,
        ), patch(
            "app.services.background_job_service.AuthService.refund_credit",
            wraps=AuthService.refund_credit,
        ) as refund_spy:

            BackgroundJobService.run_pipeline(
                job_id=job_id, video_path="video.mp4", user_id=user_id
            )

        refund_spy.assert_not_called()
        self.assertEqual(_credits(user_id), 2)
        self.assertEqual(JobService.get_job(job_id)["status"], "completed")

    def test_pro_user_failure_does_not_receive_free_credit_refund(self):
        user_id, job_id = self._job_with_deducted_credit(
            credits_before=0, is_pro=True
        )
        self.assertEqual(_credits(user_id), 0)

        with patch(
            "app.services.background_job_service.PipelineService.process_video",
            side_effect=RuntimeError("induced pipeline failure"),
        ), patch(
            "app.services.background_job_service.SubscriptionService.is_pro_active",
            return_value=True,
        ), patch(
            "app.services.background_job_service.AuthService.refund_credit",
            wraps=AuthService.refund_credit,
        ) as refund_spy:

            BackgroundJobService.run_pipeline(
                job_id=job_id, video_path="video.mp4", user_id=user_id
            )

        refund_spy.assert_not_called()
        self.assertEqual(_credits(user_id), 0)
        self.assertEqual(JobService.get_job(job_id)["status"], "failed")

    def test_reconciliation_does_not_double_refund_an_already_failed_job(self):
        user_id, job_id = self._job_with_deducted_credit(credits_before=3)

        with patch(
            "app.services.background_job_service.PipelineService.process_video",
            side_effect=RuntimeError("induced pipeline failure"),
        ), patch(
            "app.services.background_job_service.SubscriptionService.is_pro_active",
            return_value=False,
        ), patch(
            "app.services.background_job_service.AuthService.refund_credit",
            wraps=AuthService.refund_credit,
        ) as refund_spy:

            BackgroundJobService.run_pipeline(
                job_id=job_id, video_path="video.mp4", user_id=user_id
            )

        self.assertEqual(_credits(user_id), 3)
        refund_spy.assert_called_once()

        # Server-restart reconciliation only ever targets jobs still in
        # 'pending'/'processing' -- this job is already 'failed', so a
        # reconciliation pass run afterward must be a complete no-op and
        # must never touch this user's credits a second time.
        with patch(
            "app.services.job_service.AuthService.refund_credit",
            wraps=AuthService.refund_credit,
        ) as reconcile_refund_spy:

            reconciled = JobService.reconcile_interrupted_jobs()

        self.assertEqual(reconciled, 0)
        reconcile_refund_spy.assert_not_called()
        self.assertEqual(_credits(user_id), 3)


if __name__ == "__main__":
    unittest.main()
