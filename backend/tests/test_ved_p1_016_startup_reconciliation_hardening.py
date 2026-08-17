"""VED-P1-016: real startup-boundary self-recovery test.

test_startup_cleanup.py proves app.main calls JobService.reconcile_
interrupted_jobs() before CleanupService.cleanup(), but mocks reconcile_
interrupted_jobs itself away. test_ved_p1_011_completion_recovery.py and
test_ved_p1_012_recovery_registration.py prove reconcile_interrupted_jobs
and _register_recovered_artifacts are individually correct, but call them
directly rather than through the real app.main import/startup boundary.

Nothing currently proves the REAL recovery path -- load_valid_result_
artifact, _commit_recovered_job, _register_recovered_artifacts (Project +
History registration) -- actually runs to completion when app.main is
imported fresh, the same way it does on a real server restart. This file
closes that gap by fresh-importing app.main with only external/non-
essential side effects mocked (FFmpeg validation, file logging, the health
scheduler thread, cleanup sweep) and letting every recovery-relevant call
run for real against an isolated SQLite DB and job-storage folder.
"""

import importlib
import json
import sys
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
    results_dir = JobStorageService.subfolder(job_id, "results")
    result_path = results_dir / "result.json"

    with open(result_path, "w", encoding="utf-8") as file:
        json.dump(content, file)


def _recovered_result_payload(job_id):
    # Mirrors the actual shape ResultExportService.save_result writes to
    # disk: "highlights" (not "all_highlights"), no project_id/
    # history_saved/video. Paths are scoped to job_id so multi-job tests
    # don't collide on clip/thumbnail ownership.
    return {
        "title": "Epic Plays",
        "description": "desc",
        "hashtags": ["#gaming"],
        "highlights": [
            {
                "timestamp": 12.0,
                "clip_path": f"clips/{job_id}.mp4",
                "thumbnail_path": f"thumbnails/{job_id}.jpg",
            }
        ],
        "stats": {"highlights_found": 1},
        "final_reel": f"reels/{job_id}_final.mp4",
        "vertical_reel": f"reels/{job_id}_final_vertical.mp4",
        "thumbnail": f"thumbnails/{job_id}.jpg",
        "result_json": "results/result.json",
    }


class _RealStartupReconciliationTestCase(unittest.TestCase):
    """Fresh-imports app.main with only external/non-essential startup
    side effects mocked, so real JobService.reconcile_interrupted_jobs()
    (and everything it calls) executes through the actual startup
    boundary. Do NOT mock DatabaseService.initialize, JobService.
    reconcile_interrupted_jobs, JobService.load_valid_result_artifact,
    JobService._commit_recovered_job, ProjectService.create_project, or
    HistoryService.add_history -- those are exactly what this file
    verifies.
    """

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

        external_side_effect_patches = [
            "app.services.ffmpeg_service.FFmpegService.validate",
            "app.services.logger_service.LoggerService.initialize",
            "app.services.logger_service.LoggerService.info",
            "app.services.health_scheduler_service.HealthSchedulerService.start",
            "app.services.cleanup_service.CleanupService.cleanup",
        ]

        for target in external_side_effect_patches:
            patcher = patch(target)
            patcher.start()
            self.addCleanup(patcher.stop)

        self.addCleanup(sys.modules.pop, "app.main", None)

    def _import_fresh_main(self):
        sys.modules.pop("app.main", None)
        return importlib.import_module("app.main")


class RealStartupRecoveryTests(_RealStartupReconciliationTestCase):

    def test_real_startup_recovers_valid_interrupted_job_via_main_import(self):
        job_id = "startup-recovery-valid"
        payload = _recovered_result_payload(job_id)

        _write_result_json(job_id, payload)
        _insert_job(
            job_id, user_id=101, status="processing",
            progress=100, message="Completed"
        )

        main_module = self._import_fresh_main()

        job = JobService.get_job(job_id)
        self.assertEqual(job["status"], "completed")
        self.assertEqual(job["progress"], 100)
        self.assertEqual(job["result"], payload)

        self.mock_refund.assert_not_called()

        projects = ProjectService.get_projects(user_id=101)
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0]["job_id"], job_id)

        history = HistoryService.get_history(user_id=101)
        self.assertEqual(len(history), 1)

        self.assertTrue(hasattr(main_module, "app"))
        self.assertEqual(main_module._reconciled_jobs, 0)

    def test_real_startup_fails_and_refunds_job_with_no_result_artifact(self):
        job_id = "startup-recovery-invalid"

        _insert_job(
            job_id, user_id=102, status="processing",
            progress=50, message="Processing"
        )

        main_module = self._import_fresh_main()

        job = JobService.get_job(job_id)
        self.assertEqual(job["status"], "failed")

        self.mock_refund.assert_called_once_with(102)

        self.assertEqual(len(ProjectService.get_projects(user_id=102)), 0)
        self.assertEqual(len(HistoryService.get_history(user_id=102)), 0)

        self.assertEqual(main_module._reconciled_jobs, 1)
        self.assertTrue(hasattr(main_module, "app"))

    def test_real_startup_reconciliation_return_value_matches_failed_count(self):
        job_a = "startup-recovery-multi-valid"
        job_b = "startup-recovery-multi-invalid"
        payload_a = _recovered_result_payload(job_a)

        _write_result_json(job_a, payload_a)
        _insert_job(job_a, user_id=103, status="processing")
        _insert_job(job_b, user_id=104, status="processing")

        main_module = self._import_fresh_main()

        job_a_row = JobService.get_job(job_a)
        job_b_row = JobService.get_job(job_b)

        self.assertEqual(job_a_row["status"], "completed")
        self.assertEqual(job_b_row["status"], "failed")

        self.mock_refund.assert_called_once_with(104)

        self.assertEqual(len(ProjectService.get_projects(user_id=103)), 1)
        self.assertEqual(len(HistoryService.get_history(user_id=103)), 1)
        self.assertEqual(len(ProjectService.get_projects(user_id=104)), 0)
        self.assertEqual(len(HistoryService.get_history(user_id=104)), 0)

        self.assertEqual(main_module._reconciled_jobs, 1)


if __name__ == "__main__":
    unittest.main()
