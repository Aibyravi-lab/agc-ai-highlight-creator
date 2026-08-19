"""VED-ANALYTICS-002: reliable, exactly-once "Highlights Generated" analytics.

Production audit showed PostHog undercounting "Highlights Generated" against
real completed jobs, traced to the old client-side-only track() call in
frontend/hooks/usePipeline.ts depending on the originating browser tab
staying open until the pipeline finished. The fix moves emission to
JobService.complete_job() — the single authoritative place jobs.status
becomes "completed" (called from both BackgroundJobService's normal/retry
path and JobService.reconcile_interrupted_jobs's startup-recovery path) —
guarded by a compare-and-swap UPDATE (WHERE status != 'completed') so a job
can only ever trigger the event once, no matter how many times complete_job()
is called for it.

Covers:
  A) CompleteJobAnalyticsTests — direct complete_job() exactly-once behavior.
  B) ReconciliationAnalyticsTests — the startup-recovery path never
     double-fires for a job already completed normally.
  C) FailedJobAnalyticsTests — fail_job() never emits the event.
"""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from app.services.analytics_service import AnalyticsService
from app.services.database_service import DatabaseService
from app.services.job_service import JobService


def _make_isolated_db():
    tmp_dir = tempfile.TemporaryDirectory()
    DatabaseService.DB_DIR = Path(tmp_dir.name)
    DatabaseService.DB_PATH = Path(tmp_dir.name) / "test_agc.db"
    DatabaseService.initialize()
    return tmp_dir


def _insert_job(job_id, user_id, status, progress=50, message="Processing"):
    connection = DatabaseService.get_connection()
    cursor = connection.cursor()
    now = datetime.utcnow().isoformat()
    cursor.execute(
        """
        INSERT INTO jobs (job_id, user_id, status, progress, message, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (job_id, user_id, status, progress, message, now),
    )
    connection.commit()
    connection.close()


FAKE_RESULT = {"stats": {"highlights_found": 1}, "all_highlights": []}


# ---------------------------------------------------------------------------
# A) complete_job() exactly-once behavior
# ---------------------------------------------------------------------------

class CompleteJobAnalyticsTests(unittest.TestCase):

    def setUp(self):
        self._db_tmp_dir = _make_isolated_db()
        self.addCleanup(self._db_tmp_dir.cleanup)

        self._capture_patch = patch(
            "app.services.job_service.AnalyticsService.capture_highlights_generated"
        )
        self.mock_capture = self._capture_patch.start()
        self.addCleanup(self._capture_patch.stop)

    def test_successful_completion_emits_exactly_once(self):
        _insert_job("job-1", user_id=42, status="processing")

        JobService.complete_job(job_id="job-1", result=FAKE_RESULT)

        self.mock_capture.assert_called_once_with(
            user_id=42, job_id="job-1", highlights_found=1
        )

        job = JobService.get_job("job-1")
        self.assertEqual(job["status"], "completed")

    def test_repeated_reads_after_completion_do_not_duplicate(self):
        """Simulates frontend polling: reading the job many times after
        completion must never itself trigger analytics — emission is tied
        only to the UPDATE inside complete_job(), not to reads."""
        _insert_job("job-2", user_id=7, status="processing")

        JobService.complete_job(job_id="job-2", result=FAKE_RESULT)

        for _ in range(10):
            JobService.get_job("job-2")

        self.mock_capture.assert_called_once_with(
            user_id=7, job_id="job-2", highlights_found=1
        )

    def test_retry_does_not_duplicate(self):
        """Mirrors BackgroundJobService._finish_job's retry-on-transient-
        failure pattern: complete_job() called twice in a row for the same
        job_id must only fire analytics once."""
        _insert_job("job-3", user_id=13, status="processing")

        JobService.complete_job(job_id="job-3", result=FAKE_RESULT)
        JobService.complete_job(job_id="job-3", result=FAKE_RESULT)

        self.mock_capture.assert_called_once_with(
            user_id=13, job_id="job-3", highlights_found=1
        )

    def test_analytics_failure_does_not_fail_the_job(self):
        self.mock_capture.side_effect = RuntimeError("PostHog unreachable")

        _insert_job("job-4", user_id=5, status="processing")

        # Must not raise.
        JobService.complete_job(job_id="job-4", result=FAKE_RESULT)

        job = JobService.get_job("job-4")
        self.assertEqual(job["status"], "completed")
        self.assertEqual(job["result"], FAKE_RESULT)

    def test_unattributed_job_does_not_emit(self):
        _insert_job("job-5", user_id=None, status="processing")

        JobService.complete_job(job_id="job-5", result=FAKE_RESULT)

        self.mock_capture.assert_not_called()

        job = JobService.get_job("job-5")
        self.assertEqual(job["status"], "completed")

    def test_already_completed_job_is_a_no_op(self):
        """A job that somehow reaches complete_job() while already
        'completed' (defensive case) must neither re-emit analytics nor
        re-write the row."""
        _insert_job(
            "job-6", user_id=9, status="completed",
            progress=100, message="Completed",
        )

        JobService.complete_job(job_id="job-6", result=FAKE_RESULT)

        self.mock_capture.assert_not_called()


# ---------------------------------------------------------------------------
# B) reconcile_interrupted_jobs (startup recovery) analytics behavior
# ---------------------------------------------------------------------------

class ReconciliationAnalyticsTests(unittest.TestCase):

    def setUp(self):
        self._db_tmp_dir = _make_isolated_db()
        self.addCleanup(self._db_tmp_dir.cleanup)

        self._jobs_tmp_dir = tempfile.TemporaryDirectory()
        from app.config.config import settings
        self._settings_patch = patch.object(
            settings, "JOBS_FOLDER", self._jobs_tmp_dir.name
        )
        self._settings_patch.start()
        self.addCleanup(self._settings_patch.stop)
        self.addCleanup(self._jobs_tmp_dir.cleanup)

        self._is_pro_patch = patch(
            "app.services.job_service.SubscriptionService.is_pro_active",
            return_value=False,
        )
        self._is_pro_patch.start()
        self.addCleanup(self._is_pro_patch.stop)

        self._refund_patch = patch(
            "app.services.job_service.AuthService.refund_credit"
        )
        self._refund_patch.start()
        self.addCleanup(self._refund_patch.stop)

        self._capture_patch = patch(
            "app.services.job_service.AnalyticsService.capture_highlights_generated"
        )
        self.mock_capture = self._capture_patch.start()
        self.addCleanup(self._capture_patch.stop)

    def test_recovered_job_emits_once(self):
        from app.services.job_storage_service import JobStorageService
        import json

        valid_result = {
            "title": "Epic Plays",
            "description": "desc",
            "hashtags": ["#gaming"],
            "highlights": [{"timestamp": 12.0, "clip_path": "clips/a.mp4"}],
            "stats": {"highlights_found": 1},
            "final_reel": "reels/final.mp4",
            "vertical_reel": "reels/final_vertical.mp4",
            "thumbnail": "thumbnails/a.jpg",
            "result_json": "results/result.json",
        }
        results_dir = JobStorageService.subfolder("job-recovered", "results")
        with open(results_dir / "result.json", "w", encoding="utf-8") as file:
            json.dump(valid_result, file)

        _insert_job("job-recovered", user_id=21, status="processing")

        JobService.reconcile_interrupted_jobs()

        self.mock_capture.assert_called_once_with(
            user_id=21, job_id="job-recovered", highlights_found=1
        )

    def test_already_completed_job_is_never_revisited_by_reconciliation(self):
        """A job that completed normally (and already fired analytics via
        the normal path) must be excluded from the interrupted-job scan on
        a later restart, so reconciliation can never double-fire it."""
        _insert_job(
            "job-already-done", user_id=8, status="completed",
            progress=100, message="Completed",
        )

        reconciled_failed = JobService.reconcile_interrupted_jobs()

        self.assertEqual(reconciled_failed, 0)
        self.mock_capture.assert_not_called()

    def test_unrecoverable_interrupted_job_does_not_emit(self):
        _insert_job("job-unrecoverable", user_id=11, status="processing")

        with patch("app.services.job_service.LoggerService"):
            JobService.reconcile_interrupted_jobs()

        self.mock_capture.assert_not_called()


# ---------------------------------------------------------------------------
# C) fail_job() never emits "Highlights Generated"
# ---------------------------------------------------------------------------

class FailedJobAnalyticsTests(unittest.TestCase):

    def setUp(self):
        self._db_tmp_dir = _make_isolated_db()
        self.addCleanup(self._db_tmp_dir.cleanup)

        self._capture_patch = patch(
            "app.services.job_service.AnalyticsService.capture_highlights_generated"
        )
        self.mock_capture = self._capture_patch.start()
        self.addCleanup(self._capture_patch.stop)

    def test_failed_job_does_not_emit(self):
        _insert_job("job-fail", user_id=3, status="processing")

        JobService.fail_job(job_id="job-fail", error="pipeline exploded")

        self.mock_capture.assert_not_called()

        job = JobService.get_job("job-fail")
        self.assertEqual(job["status"], "failed")


# ---------------------------------------------------------------------------
# D) AnalyticsService itself — config safety, payload shape, network failure
# ---------------------------------------------------------------------------

class AnalyticsServiceTests(unittest.TestCase):

    def setUp(self):
        from app.config.config import settings
        self.settings = settings

    def test_missing_api_key_is_a_safe_noop(self):
        with patch.object(self.settings, "POSTHOG_API_KEY", ""), \
             patch.object(self.settings, "POSTHOG_HOST", "https://app.posthog.com"), \
             patch("app.services.analytics_service.requests.post") as mock_post:

            # Must not raise, and must not submit any work to the executor.
            AnalyticsService.capture_highlights_generated(
                user_id=1, job_id="job-x", highlights_found=3
            )

            mock_post.assert_not_called()

    def test_missing_host_is_a_safe_noop(self):
        with patch.object(self.settings, "POSTHOG_API_KEY", "phc_test"), \
             patch.object(self.settings, "POSTHOG_HOST", ""), \
             patch("app.services.analytics_service.requests.post") as mock_post:

            AnalyticsService.capture_highlights_generated(
                user_id=1, job_id="job-x", highlights_found=3
            )

            mock_post.assert_not_called()

    def test_capture_sends_correct_event_properties(self):
        with patch.object(self.settings, "POSTHOG_API_KEY", "phc_test"), \
             patch.object(self.settings, "POSTHOG_HOST", "https://app.posthog.com"), \
             patch("app.services.analytics_service.requests.post") as mock_post:

            AnalyticsService._send_highlights_generated(
                user_id=99, job_id="job-y", highlights_found=4
            )

            mock_post.assert_called_once()
            url, kwargs = mock_post.call_args[0], mock_post.call_args[1]
            self.assertEqual(url[0], "https://app.posthog.com/capture/")
            payload = kwargs["json"]
            self.assertEqual(payload["api_key"], "phc_test")
            self.assertEqual(payload["event"], "Highlights Generated")
            self.assertEqual(payload["distinct_id"], "99")
            self.assertEqual(payload["properties"]["job_id"], "job-y")
            self.assertEqual(payload["properties"]["highlights_found"], 4)
            self.assertEqual(kwargs["timeout"], AnalyticsService.CAPTURE_TIMEOUT_SECONDS)

    def test_capture_omits_highlights_found_when_unavailable(self):
        with patch.object(self.settings, "POSTHOG_API_KEY", "phc_test"), \
             patch.object(self.settings, "POSTHOG_HOST", "https://app.posthog.com"), \
             patch("app.services.analytics_service.requests.post") as mock_post:

            AnalyticsService._send_highlights_generated(
                user_id=99, job_id="job-z", highlights_found=None
            )

            payload = mock_post.call_args[1]["json"]
            self.assertNotIn("highlights_found", payload["properties"])

    def test_network_failure_is_caught_and_does_not_raise(self):
        with patch.object(self.settings, "POSTHOG_API_KEY", "phc_test"), \
             patch.object(self.settings, "POSTHOG_HOST", "https://app.posthog.com"), \
             patch(
                 "app.services.analytics_service.requests.post",
                 side_effect=ConnectionError("network unreachable")
             ):

            # Must not raise.
            AnalyticsService._send_highlights_generated(
                user_id=1, job_id="job-w", highlights_found=1
            )


if __name__ == "__main__":
    unittest.main()
