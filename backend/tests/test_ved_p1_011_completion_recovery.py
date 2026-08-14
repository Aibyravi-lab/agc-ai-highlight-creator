"""VED-P1-011: completion-window false-failure recovery.

Closes two failure modes identified in the VED-P1-011 audit:

  1. A crash/restart between JobService.update_job(progress=100,
     message="Completed") and JobService.complete_job()'s commit leaves
     jobs.status="processing" even though the pipeline fully finished and
     result.json already exists. Pre-fix, startup reconciliation blindly
     marked every pending/processing job "failed" and refunded its
     credit, discarding the fact the job actually succeeded.

  2. complete_job() itself can raise (SQLite contention, disk I/O) after
     a valid result already exists. Pre-fix, that exception fell into
     BackgroundJobService.run_pipeline's generic pipeline-failure
     handler, false-failing and refunding a job that had actually
     succeeded.

Covers:
  A) JobServiceResultArtifactTests — load_valid_result_artifact's
     validation rules directly.
  B) ReconciliationRecoveryTests — reconcile_interrupted_jobs's per-job
     classification (recover / fail / idempotency) against a real,
     isolated SQLite DB and job-storage folder.
  C) CompleteJobRetryBehaviorTests — BackgroundJobService.run_pipeline's
     retry-then-recover-or-fail boundary around complete_job().
"""

import json
import sqlite3
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from app.config.config import settings
from app.services.database_service import DatabaseService
from app.services.job_service import JobService
from app.services.job_storage_service import JobStorageService


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


VALID_RESULT_PAYLOAD = {
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


def _write_result_json(job_id, content):
    results_dir = JobStorageService.subfolder(job_id, "results")
    result_path = results_dir / "result.json"

    if isinstance(content, str):
        result_path.write_text(content, encoding="utf-8")
    else:
        with open(result_path, "w", encoding="utf-8") as file:
            json.dump(content, file)


# ---------------------------------------------------------------------------
# A) JobService.load_valid_result_artifact validation rules
# ---------------------------------------------------------------------------

class JobServiceResultArtifactTests(unittest.TestCase):

    def setUp(self):
        self._tmp_jobs_dir = tempfile.TemporaryDirectory()
        self._settings_patch = patch.object(
            settings, "JOBS_FOLDER", self._tmp_jobs_dir.name
        )
        self._settings_patch.start()
        self.addCleanup(self._settings_patch.stop)
        self.addCleanup(self._tmp_jobs_dir.cleanup)

    def test_missing_file_returns_none(self):
        self.assertIsNone(
            JobService.load_valid_result_artifact("no-such-job")
        )

    def test_valid_result_returns_parsed_payload(self):
        _write_result_json("job-valid", VALID_RESULT_PAYLOAD)

        result = JobService.load_valid_result_artifact("job-valid")

        self.assertEqual(result, VALID_RESULT_PAYLOAD)

    def test_malformed_json_returns_none(self):
        _write_result_json("job-malformed", "{not valid json")

        with patch("app.services.job_service.LoggerService"):
            self.assertIsNone(
                JobService.load_valid_result_artifact("job-malformed")
            )

    def test_non_object_json_returns_none(self):
        _write_result_json("job-list", [1, 2, 3])

        with patch("app.services.job_service.LoggerService"):
            self.assertIsNone(
                JobService.load_valid_result_artifact("job-list")
            )

    def test_missing_required_fields_returns_none(self):
        _write_result_json("job-incomplete", {"title": "x"})

        with patch("app.services.job_service.LoggerService"):
            self.assertIsNone(
                JobService.load_valid_result_artifact("job-incomplete")
            )

    def test_empty_highlights_returns_none(self):
        payload = dict(VALID_RESULT_PAYLOAD, highlights=[])
        _write_result_json("job-empty-highlights", payload)

        with patch("app.services.job_service.LoggerService"):
            self.assertIsNone(
                JobService.load_valid_result_artifact("job-empty-highlights")
            )

    def test_missing_final_reel_returns_none(self):
        payload = dict(VALID_RESULT_PAYLOAD, final_reel="")
        _write_result_json("job-no-reel", payload)

        with patch("app.services.job_service.LoggerService"):
            self.assertIsNone(
                JobService.load_valid_result_artifact("job-no-reel")
            )


# ---------------------------------------------------------------------------
# B) reconcile_interrupted_jobs per-job classification
# ---------------------------------------------------------------------------

class ReconciliationRecoveryTests(unittest.TestCase):

    def setUp(self):
        self._db_tmp_dir = _make_isolated_db()
        self.addCleanup(self._db_tmp_dir.cleanup)

        self._jobs_tmp_dir = tempfile.TemporaryDirectory()
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
        self.mock_refund = self._refund_patch.start()
        self.addCleanup(self._refund_patch.stop)

    def test_valid_result_recovers_job_as_completed_without_refund(self):
        _write_result_json("job-a", VALID_RESULT_PAYLOAD)
        _insert_job(
            "job-a", user_id=1, status="processing",
            progress=95, message="Adding Captions"
        )

        reconciled_failed = JobService.reconcile_interrupted_jobs()

        job = JobService.get_job("job-a")
        self.assertEqual(job["status"], "completed")
        self.assertEqual(job["progress"], 100)
        self.assertEqual(job["message"], "Completed")
        self.assertEqual(job["result"], VALID_RESULT_PAYLOAD)
        self.assertIsNotNone(job["completed_at"])
        self.mock_refund.assert_not_called()
        self.assertEqual(reconciled_failed, 0)

    def test_no_result_preserves_existing_fail_and_refund_behavior(self):
        _insert_job("job-b", user_id=2, status="processing")

        reconciled_failed = JobService.reconcile_interrupted_jobs()

        job = JobService.get_job("job-b")
        self.assertEqual(job["status"], "failed")
        self.assertEqual(job["message"], "Failed")
        self.assertEqual(job["error"], "Interrupted by server restart")
        self.mock_refund.assert_called_once_with(2)
        self.assertEqual(reconciled_failed, 1)

    def test_invalid_result_is_not_treated_as_recovery(self):
        _write_result_json("job-c", "{corrupt")
        _insert_job("job-c", user_id=3, status="processing")

        with patch("app.services.job_service.LoggerService"):
            reconciled_failed = JobService.reconcile_interrupted_jobs()

        job = JobService.get_job("job-c")
        self.assertEqual(job["status"], "failed")
        self.mock_refund.assert_called_once_with(3)
        self.assertEqual(reconciled_failed, 1)

    def test_reconciliation_is_idempotent_across_repeated_runs(self):
        _write_result_json("job-recoverable", VALID_RESULT_PAYLOAD)
        _insert_job("job-recoverable", user_id=4, status="processing")
        _insert_job("job-unrecoverable", user_id=5, status="processing")

        JobService.reconcile_interrupted_jobs()
        first_refund_call_count = self.mock_refund.call_count

        # Second pass must find nothing left in pending/processing — both
        # jobs already reached a terminal status on the first pass.
        second_reconciled = JobService.reconcile_interrupted_jobs()

        self.assertEqual(second_reconciled, 0)
        self.assertEqual(self.mock_refund.call_count, first_refund_call_count)

        recovered = JobService.get_job("job-recoverable")
        failed = JobService.get_job("job-unrecoverable")
        self.assertEqual(recovered["status"], "completed")
        self.assertEqual(failed["status"], "failed")

    def test_completed_and_failed_jobs_are_left_untouched(self):
        _insert_job(
            "job-already-done", user_id=6, status="completed",
            progress=100, message="Completed"
        )
        _insert_job(
            "job-already-failed", user_id=7, status="failed",
            progress=0, message="Failed"
        )

        reconciled_failed = JobService.reconcile_interrupted_jobs()

        self.assertEqual(reconciled_failed, 0)
        self.mock_refund.assert_not_called()
        self.assertEqual(
            JobService.get_job("job-already-done")["status"], "completed"
        )
        self.assertEqual(
            JobService.get_job("job-already-failed")["status"], "failed"
        )


# ---------------------------------------------------------------------------
# C) BackgroundJobService.run_pipeline's complete_job retry/recovery
#    boundary. JobService is mocked wholesale (matching the existing
#    VED-P1-009 BackgroundJobServiceCreditBehaviorTests pattern) so these
#    tests pin call behavior and ordering; real persistence is covered by
#    ReconciliationRecoveryTests and JobServiceResultArtifactTests above.
# ---------------------------------------------------------------------------

class CompleteJobRetryBehaviorTests(unittest.TestCase):

    def _run(self, complete_job_side_effect, load_valid_result_return_value=None):
        from app.services.background_job_service import BackgroundJobService

        fake_result = {"highlights_found": 1, "all_highlights": []}

        with patch(
            "app.services.background_job_service.PipelineService.process_video",
            return_value=fake_result,
        ), patch(
            "app.services.background_job_service.JobService"
        ) as mock_job_service, patch(
            "app.services.background_job_service.SubscriptionService.is_pro_active",
            return_value=False,
        ), patch(
            "app.services.background_job_service.AuthService"
        ) as mock_auth_service, patch(
            "app.services.background_job_service.CleanupService"
        ), patch(
            "app.services.background_job_service.LoggerService"
        ) as mock_logger, patch(
            "app.services.background_job_service.time.sleep"
        ) as mock_sleep:

            mock_job_service.complete_job.side_effect = complete_job_side_effect
            mock_job_service.load_valid_result_artifact.return_value = (
                load_valid_result_return_value
            )

            BackgroundJobService.run_pipeline(
                job_id="job-1", video_path="video.mp4", user_id=7
            )

        return mock_job_service, mock_auth_service, mock_logger, mock_sleep, fake_result

    def test_retry_succeeds_after_transient_failure(self):
        mock_job_service, mock_auth_service, _mock_logger, mock_sleep, fake_result = self._run(
            complete_job_side_effect=[
                sqlite3.OperationalError("database is locked"),
                None,
            ]
        )

        self.assertEqual(mock_job_service.complete_job.call_count, 2)
        for call in mock_job_service.complete_job.call_args_list:
            self.assertEqual(call.kwargs["job_id"], "job-1")
            self.assertEqual(call.kwargs["result"], fake_result)

        mock_job_service.fail_job.assert_not_called()
        mock_auth_service.refund_credit.assert_not_called()
        mock_sleep.assert_called_once()

    def test_persistent_failure_with_valid_result_stays_recoverable(self):
        mock_job_service, mock_auth_service, mock_logger, _mock_sleep, _fake_result = self._run(
            complete_job_side_effect=sqlite3.OperationalError("database is locked"),
            load_valid_result_return_value={"highlights": [{"a": 1}]},
        )

        self.assertEqual(mock_job_service.complete_job.call_count, 2)
        mock_job_service.fail_job.assert_not_called()
        mock_auth_service.refund_credit.assert_not_called()
        mock_job_service.load_valid_result_artifact.assert_called_once_with("job-1")

        logged_events = " ".join(
            call.args[0] for call in mock_logger.error.call_args_list
        )
        self.assertIn("event=complete_job_commit_failed", logged_events)
        self.assertIn("outcome=left_recoverable", logged_events)

    def test_persistent_failure_without_valid_result_fails_and_refunds(self):
        mock_job_service, mock_auth_service, _mock_logger, _mock_sleep, _fake_result = self._run(
            complete_job_side_effect=sqlite3.OperationalError("database is locked"),
            load_valid_result_return_value=None,
        )

        self.assertEqual(mock_job_service.complete_job.call_count, 2)
        mock_job_service.fail_job.assert_called_once()
        self.assertEqual(
            mock_job_service.fail_job.call_args.kwargs["job_id"], "job-1"
        )
        self.assertIn(
            "Job completion failed",
            mock_job_service.fail_job.call_args.kwargs["error"],
        )
        mock_auth_service.refund_credit.assert_called_once_with(user_id=7)

    def test_happy_path_completes_on_first_attempt_no_sleep(self):
        mock_job_service, mock_auth_service, _mock_logger, mock_sleep, fake_result = self._run(
            complete_job_side_effect=None
        )

        mock_job_service.complete_job.assert_called_once_with(
            job_id="job-1", result=fake_result
        )
        mock_job_service.fail_job.assert_not_called()
        mock_auth_service.refund_credit.assert_not_called()
        mock_sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
