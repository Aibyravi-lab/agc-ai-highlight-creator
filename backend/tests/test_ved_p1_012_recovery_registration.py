"""VED-P1-012: recovery integrity gap left by VED-P1-011.

A job recovered by JobService.reconcile_interrupted_jobs (see
test_ved_p1_011_completion_recovery.py) is marked "completed" purely from
its on-disk result.json. That snapshot predates HistoryService.add_history
and ProjectService.create_project in the normal pipeline (see
pipeline_service.py's post-export registration step), so pre-fix, a
recovered job was completed but permanently invisible in the user's
History/Projects lists, and its individual highlight clips (stored under
"highlights" rather than the normal path's "all_highlights") were not
authorized by JobService.user_owns_file.

Covers:
  A) RecoveryRegistrationTests — _register_recovered_artifacts's
     idempotency and failure isolation, called directly and via a full
     reconcile_interrupted_jobs pass.
  B) RecoveredResultAuthorizationTests — _collect_result_paths/
     user_owns_file accepting the recovered "highlights" shape without
     broadening authorization to other jobs' paths.
  C) ReconciliationOrderingTests — registration only runs after a
     successful _commit_recovered_job.
"""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from app.config.config import settings
from app.services.database_service import DatabaseService
from app.services.job_service import JobService
from app.services.job_storage_service import JobStorageService
from app.services.history_service import HistoryService
from app.services.project_service import ProjectService


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


def _write_result_json(job_id, content):
    import json

    results_dir = JobStorageService.subfolder(job_id, "results")
    result_path = results_dir / "result.json"

    with open(result_path, "w", encoding="utf-8") as file:
        json.dump(content, file)


# Mirrors the actual shape ResultExportService.save_result writes to disk:
# "highlights" (not "all_highlights"), no project_id/history_saved/video.
RECOVERED_RESULT_PAYLOAD = {
    "title": "Epic Plays",
    "description": "desc",
    "hashtags": ["#gaming"],
    "highlights": [
        {
            "timestamp": 12.0,
            "clip_path": "clips/a.mp4",
            "thumbnail_path": "thumbnails/a_clip.jpg",
        }
    ],
    "stats": {"highlights_found": 1},
    "final_reel": "reels/final.mp4",
    "vertical_reel": "reels/final_vertical.mp4",
    "thumbnail": "thumbnails/a.jpg",
    "result_json": "results/result.json",
}


class _IsolatedDbTestCase(unittest.TestCase):

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


# ---------------------------------------------------------------------------
# A) _register_recovered_artifacts idempotency and failure isolation
# ---------------------------------------------------------------------------

class RecoveryRegistrationTests(_IsolatedDbTestCase):

    def test_recovery_creates_one_project_and_one_history_row(self):
        _write_result_json("job-reg-1", RECOVERED_RESULT_PAYLOAD)
        _insert_job("job-reg-1", user_id=1, status="processing")

        JobService.reconcile_interrupted_jobs()

        projects = ProjectService.get_projects(user_id=1)
        history = HistoryService.get_history(user_id=1)

        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0]["job_id"], "job-reg-1")
        self.assertEqual(projects[0]["status"], "completed")

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["video_name"], "Recovered Job job-reg-1")

    def test_calling_registration_twice_does_not_duplicate(self):
        JobService._register_recovered_artifacts(
            job_id="job-reg-2", user_id=2, result=RECOVERED_RESULT_PAYLOAD
        )
        JobService._register_recovered_artifacts(
            job_id="job-reg-2", user_id=2, result=RECOVERED_RESULT_PAYLOAD
        )

        self.assertEqual(len(ProjectService.get_projects(user_id=2)), 1)
        self.assertEqual(len(HistoryService.get_history(user_id=2)), 1)

    def test_existing_project_is_not_duplicated_history_still_registered(self):
        ProjectService.create_project(
            user_id=3,
            job_id="job-reg-3",
            original_video_name="Recovered Job job-reg-3",
            thumbnail_path=None,
            horizontal_reel_path=None,
        )

        JobService._register_recovered_artifacts(
            job_id="job-reg-3", user_id=3, result=RECOVERED_RESULT_PAYLOAD
        )

        self.assertEqual(len(ProjectService.get_projects(user_id=3)), 1)
        self.assertEqual(len(HistoryService.get_history(user_id=3)), 1)

    def test_existing_history_is_not_duplicated_project_still_registered(self):
        HistoryService.add_history(
            video_name="Recovered Job job-reg-4",
            reel_path="reels/final.mp4",
            highlights_count=1,
            user_id=4,
        )

        JobService._register_recovered_artifacts(
            job_id="job-reg-4", user_id=4, result=RECOVERED_RESULT_PAYLOAD
        )

        self.assertEqual(len(HistoryService.get_history(user_id=4)), 1)
        self.assertEqual(len(ProjectService.get_projects(user_id=4)), 1)

    def test_project_creation_failure_does_not_raise_or_fail_job(self):
        _write_result_json("job-reg-5", RECOVERED_RESULT_PAYLOAD)
        _insert_job("job-reg-5", user_id=5, status="processing")

        with patch(
            "app.services.job_service.ProjectService.create_project",
            side_effect=Exception("disk full"),
        ), patch(
            "app.services.job_service.JobService.fail_job"
        ) as mock_fail_job, patch(
            "app.services.job_service.LoggerService"
        ):
            # Must not raise out of reconciliation.
            JobService.reconcile_interrupted_jobs()

        mock_fail_job.assert_not_called()
        self.mock_refund.assert_not_called()

        job = JobService.get_job("job-reg-5")
        self.assertEqual(job["status"], "completed")

    def test_history_creation_failure_does_not_raise_or_fail_job(self):
        _write_result_json("job-reg-6", RECOVERED_RESULT_PAYLOAD)
        _insert_job("job-reg-6", user_id=6, status="processing")

        with patch(
            "app.services.job_service.HistoryService.add_history",
            side_effect=Exception("disk full"),
        ), patch(
            "app.services.job_service.JobService.fail_job"
        ) as mock_fail_job, patch(
            "app.services.job_service.LoggerService"
        ):
            JobService.reconcile_interrupted_jobs()

        mock_fail_job.assert_not_called()
        self.mock_refund.assert_not_called()

        job = JobService.get_job("job-reg-6")
        self.assertEqual(job["status"], "completed")

        # The project insert runs before the history insert in the same
        # registration attempt, so it should have succeeded despite the
        # later history failure.
        self.assertEqual(len(ProjectService.get_projects(user_id=6)), 1)


# ---------------------------------------------------------------------------
# B) Recovered-shape ("highlights") result authorization
# ---------------------------------------------------------------------------

class RecoveredResultAuthorizationTests(_IsolatedDbTestCase):

    def test_recovered_shape_authorizes_own_clip_and_thumbnail(self):
        _insert_job("job-auth-1", user_id=10, status="processing")
        JobService.complete_job(
            job_id="job-auth-1", result=RECOVERED_RESULT_PAYLOAD
        )

        self.assertTrue(
            JobService.user_owns_file(10, "clips/a.mp4")
        )
        self.assertTrue(
            JobService.user_owns_file(10, "thumbnails/a_clip.jpg")
        )

    def test_normal_shape_all_highlights_still_authorized(self):
        normal_result = dict(RECOVERED_RESULT_PAYLOAD)
        del normal_result["highlights"]
        normal_result["all_highlights"] = [
            {"clip_path": "clips/b.mp4", "thumbnail_path": "thumbnails/b_clip.jpg"}
        ]

        _insert_job("job-auth-2", user_id=11, status="processing")
        JobService.complete_job(job_id="job-auth-2", result=normal_result)

        self.assertTrue(
            JobService.user_owns_file(11, "clips/b.mp4")
        )

    def test_another_jobs_highlight_paths_are_not_authorized(self):
        _insert_job("job-auth-3", user_id=12, status="processing")
        JobService.complete_job(
            job_id="job-auth-3", result=RECOVERED_RESULT_PAYLOAD
        )

        other_result = dict(RECOVERED_RESULT_PAYLOAD)
        other_result["highlights"] = [
            {"clip_path": "clips/other-user.mp4", "thumbnail_path": "thumbnails/other-user.jpg"}
        ]
        _insert_job("job-auth-4", user_id=13, status="processing")
        JobService.complete_job(job_id="job-auth-4", result=other_result)

        self.assertFalse(
            JobService.user_owns_file(12, "clips/other-user.mp4")
        )


# ---------------------------------------------------------------------------
# C) Registration only runs after a successful _commit_recovered_job
# ---------------------------------------------------------------------------

class ReconciliationOrderingTests(_IsolatedDbTestCase):

    def test_registration_not_called_when_commit_recovered_job_fails(self):
        _write_result_json("job-order-1", RECOVERED_RESULT_PAYLOAD)
        _insert_job("job-order-1", user_id=20, status="processing")

        with patch(
            "app.services.job_service.JobService._commit_recovered_job",
            return_value=False,
        ), patch(
            "app.services.job_service.JobService._register_recovered_artifacts"
        ) as mock_register:
            JobService.reconcile_interrupted_jobs()

        mock_register.assert_not_called()

    def test_registration_called_when_commit_recovered_job_succeeds(self):
        _write_result_json("job-order-2", RECOVERED_RESULT_PAYLOAD)
        _insert_job("job-order-2", user_id=21, status="processing")

        with patch(
            "app.services.job_service.JobService._commit_recovered_job",
            return_value=True,
        ), patch(
            "app.services.job_service.JobService._register_recovered_artifacts"
        ) as mock_register:
            JobService.reconcile_interrupted_jobs()

        mock_register.assert_called_once_with(
            job_id="job-order-2", user_id=21, result=RECOVERED_RESULT_PAYLOAD
        )


if __name__ == "__main__":
    unittest.main()
