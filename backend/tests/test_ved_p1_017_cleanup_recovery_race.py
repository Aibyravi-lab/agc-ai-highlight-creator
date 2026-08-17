"""VED-P1-017: startup recovery vs. cleanup race.

app.main runs, in order: JobService.reconcile_interrupted_jobs() (VED-P1-011/
012) then CleanupService.cleanup() (VED-P1-010's cleanup_old_jobs). A job
recovered from result.json alone has a JOBS_FOLDER/<job_id> directory whose
files were last written *before* whatever crash/restart interrupted it --
if the server was down longer than TEMP_CLEANUP_HOURS, that folder's mtime
is already past cleanup_old_jobs's deletion cutoff the moment reconciliation
finishes registering its Project/History rows. Pre-fix, cleanup_old_jobs
measures staleness purely by filesystem mtime and has no idea the job was
just recovered, so it deletes the clip/thumbnail/reel files out from under
the Project/History rows reconciliation just created in the same startup
pass -- the DB says "completed", but the artifacts are gone.

The fix makes cleanup_old_jobs prefer the job's DB-recorded lifecycle time
(completed_at, falling back to created_at) over filesystem mtime whenever a
jobs row exists for that folder -- completed_at is written at the moment
complete_job() runs, which for a recovered job is startup/recovery time, not
pre-crash time. Folders with no jobs row at all (genuinely orphaned) still
fall back to the pre-existing mtime check.

Covers:
  A) The primary regression -- a recovered job's artifacts must survive
     reconcile_interrupted_jobs() -> cleanup_old_jobs() in the same pass.
  B) Negative/retention cases -- cleanup must still remove a truly orphaned
     folder with no DB row, and must still (eventually) remove a genuinely
     stale terminal job once its own completed_at ages past the cutoff.
"""

import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from app.config.config import settings
from app.services.cleanup_service import CleanupService
from app.services.database_service import DatabaseService
from app.services.history_service import HistoryService
from app.services.job_service import JobService
from app.services.job_storage_service import JobStorageService
from app.services.project_service import ProjectService


def _make_isolated_db():
    tmp_dir = tempfile.TemporaryDirectory()
    DatabaseService.DB_DIR = Path(tmp_dir.name)
    DatabaseService.DB_PATH = Path(tmp_dir.name) / "test_agc.db"
    DatabaseService.initialize()
    return tmp_dir


def _insert_job(
    job_id,
    user_id,
    status,
    created_at=None,
    completed_at=None,
    progress=50,
    message="Processing",
):
    connection = DatabaseService.get_connection()
    cursor = connection.cursor()
    created_at = created_at or datetime.utcnow().isoformat()
    cursor.execute(
        """
        INSERT INTO jobs
            (job_id, user_id, status, progress, message,
             created_at, completed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (job_id, user_id, status, progress, message, created_at, completed_at),
    )
    connection.commit()
    connection.close()


def _write_result_json(job_id, content):
    import json

    results_dir = JobStorageService.subfolder(job_id, "results")
    result_path = results_dir / "result.json"

    with open(result_path, "w", encoding="utf-8") as file:
        json.dump(content, file)


def _write_artifact(job_id, subfolder, filename, content=b"data"):
    folder = JobStorageService.subfolder(job_id, subfolder)
    path = folder / filename
    with open(path, "wb") as file:
        file.write(content)
    return f"{subfolder}/{filename}"


def _age_job_folder(job_id, hours):
    """Backdate every file's mtime under the job folder, simulating a
    job whose artifacts were written well before a later server
    restart/outage -- the exact condition that exposes the race.
    """
    job_dir = JobStorageService.job_dir(job_id)
    old_time = (datetime.now() - timedelta(hours=hours)).timestamp()

    for root, dirs, files in os.walk(job_dir):
        for name in files:
            os.utime(os.path.join(root, name), (old_time, old_time))
        os.utime(root, (old_time, old_time))

    os.utime(job_dir, (old_time, old_time))


RECOVERED_RESULT_PAYLOAD_TEMPLATE = {
    "title": "Epic Plays",
    "description": "desc",
    "hashtags": ["#gaming"],
    "stats": {"highlights_found": 1},
}


class _IsolatedJobsEnvTestCase(unittest.TestCase):

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

        self._temp_cleanup_hours_patch = patch.object(
            settings, "TEMP_CLEANUP_HOURS", 24
        )
        self._temp_cleanup_hours_patch.start()
        self.addCleanup(self._temp_cleanup_hours_patch.stop)

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
# A) Primary regression: recovered job's artifacts must survive cleanup
# ---------------------------------------------------------------------------

class RecoveredJobSurvivesCleanupTests(_IsolatedJobsEnvTestCase):

    def test_recovered_job_artifacts_survive_immediate_startup_cleanup(self):
        job_id = "race-recovered-1"

        clip_path = _write_artifact(job_id, "clips", "a.mp4")
        thumb_path = _write_artifact(job_id, "thumbnails", "a.jpg")
        reel_path = _write_artifact(job_id, "reels", "final.mp4")
        vertical_path = _write_artifact(job_id, "reels", "final_vertical.mp4")

        payload = dict(RECOVERED_RESULT_PAYLOAD_TEMPLATE)
        payload.update(
            {
                "highlights": [
                    {
                        "timestamp": 12.0,
                        "clip_path": clip_path,
                        "thumbnail_path": thumb_path,
                    }
                ],
                "final_reel": reel_path,
                "vertical_reel": vertical_path,
                "thumbnail": thumb_path,
                "result_json": "results/result.json",
            }
        )
        _write_result_json(job_id, payload)

        # Job was left "processing" in the DB by a crash long before this
        # restart -- its on-disk artifacts (written pre-crash) are older
        # than TEMP_CLEANUP_HOURS, but the DB has no completed_at yet
        # because complete_job() never got to run before the crash.
        _insert_job(
            job_id,
            user_id=201,
            status="processing",
            created_at=(datetime.utcnow() - timedelta(hours=72)).isoformat(),
        )
        _age_job_folder(job_id, hours=72)

        recovered_count = JobService.reconcile_interrupted_jobs()
        self.assertEqual(recovered_count, 0)

        job = JobService.get_job(job_id)
        self.assertEqual(job["status"], "completed")
        self.mock_refund.assert_not_called()

        # Real cleanup, not mocked -- this is exactly what app.main runs
        # immediately after reconciliation.
        CleanupService.cleanup_old_jobs()

        job_dir = JobStorageService.job_dir(job_id)
        self.assertTrue(job_dir.exists())
        self.assertTrue((job_dir / clip_path).exists())
        self.assertTrue((job_dir / thumb_path).exists())
        self.assertTrue((job_dir / reel_path).exists())
        self.assertTrue((job_dir / vertical_path).exists())

        self.assertEqual(len(ProjectService.get_projects(user_id=201)), 1)
        self.assertEqual(len(HistoryService.get_history(user_id=201)), 1)


# ---------------------------------------------------------------------------
# B) Negative / retention: cleanup must still do its job
# ---------------------------------------------------------------------------

class CleanupRetentionStillWorksTests(_IsolatedJobsEnvTestCase):

    def test_orphaned_folder_with_no_db_row_is_still_deleted(self):
        job_id = "race-orphan-1"

        _write_artifact(job_id, "clips", "a.mp4")
        _age_job_folder(job_id, hours=72)

        # No jobs row at all for this job_id.
        CleanupService.cleanup_old_jobs()

        job_dir = JobStorageService.job_dir(job_id)
        self.assertFalse(job_dir.exists())

    def test_genuinely_stale_completed_job_is_still_deleted(self):
        job_id = "race-stale-completed-1"

        _write_artifact(job_id, "clips", "a.mp4")
        _age_job_folder(job_id, hours=72)

        _insert_job(
            job_id,
            user_id=202,
            status="completed",
            created_at=(datetime.utcnow() - timedelta(hours=96)).isoformat(),
            completed_at=(datetime.utcnow() - timedelta(hours=72)).isoformat(),
        )

        CleanupService.cleanup_old_jobs()

        job_dir = JobStorageService.job_dir(job_id)
        self.assertFalse(job_dir.exists())

    def test_genuinely_stale_failed_job_is_still_deleted(self):
        job_id = "race-stale-failed-1"

        _write_artifact(job_id, "clips", "a.mp4")
        _age_job_folder(job_id, hours=72)

        _insert_job(
            job_id,
            user_id=203,
            status="failed",
            created_at=(datetime.utcnow() - timedelta(hours=96)).isoformat(),
            completed_at=(datetime.utcnow() - timedelta(hours=72)).isoformat(),
        )

        CleanupService.cleanup_old_jobs()

        job_dir = JobStorageService.job_dir(job_id)
        self.assertFalse(job_dir.exists())

    def test_recently_completed_job_with_old_folder_mtime_is_kept(self):
        # A job that completed normally (no crash) very recently, but whose
        # early-pipeline subfolders happen to have an old mtime (e.g. frame
        # extraction started long before a slow render finished) must not
        # be swept just because some subfolder is old -- completed_at is
        # what governs once a DB row exists.
        job_id = "race-fresh-completed-1"

        _write_artifact(job_id, "clips", "a.mp4")
        _age_job_folder(job_id, hours=72)

        _insert_job(
            job_id,
            user_id=204,
            status="completed",
            created_at=(datetime.utcnow() - timedelta(hours=72)).isoformat(),
            completed_at=datetime.utcnow().isoformat(),
        )

        CleanupService.cleanup_old_jobs()

        job_dir = JobStorageService.job_dir(job_id)
        self.assertTrue(job_dir.exists())

    def test_long_abandoned_processing_job_with_no_completed_at_is_deleted(self):
        # A job stuck "processing" with no completed_at (never finished,
        # never recovered) and created long ago should still eventually be
        # swept -- falls back to created_at, preserving prior behavior for
        # abandoned jobs instead of retaining them forever.
        job_id = "race-abandoned-processing-1"

        _write_artifact(job_id, "clips", "a.mp4")
        _age_job_folder(job_id, hours=72)

        _insert_job(
            job_id,
            user_id=205,
            status="processing",
            created_at=(datetime.utcnow() - timedelta(hours=72)).isoformat(),
        )

        CleanupService.cleanup_old_jobs()

        job_dir = JobStorageService.job_dir(job_id)
        self.assertFalse(job_dir.exists())

    def test_recently_created_processing_job_is_kept(self):
        job_id = "race-active-processing-1"

        _write_artifact(job_id, "clips", "a.mp4")
        _age_job_folder(job_id, hours=72)

        _insert_job(
            job_id,
            user_id=206,
            status="processing",
            created_at=datetime.utcnow().isoformat(),
        )

        CleanupService.cleanup_old_jobs()

        job_dir = JobStorageService.job_dir(job_id)
        self.assertTrue(job_dir.exists())


if __name__ == "__main__":
    unittest.main()
