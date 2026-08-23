"""VED-MEDIA-001: cleanup_old_jobs() must never delete a job folder that a
projects row still references, no matter how old the job is.

Root cause: CleanupService.cleanup_old_jobs() (VED-P1-010/017) only ever
asked "how old is this job?" via JobService.get_job_retention_reference_times
-- it never asked "does anything still point at this job's media?". A
completed job's storage/jobs/<job_id> folder is exactly what projects.
job_id, thumbnail_path, horizontal_reel_path, and vertical_reel_path
reference for as long as that project row exists -- once TEMP_CLEANUP_HOURS
passed, the next job completion's CleanupService.cleanup() call
(BackgroundJobService.run_pipeline's finally block, or the startup sweep in
app.main) deleted that folder out from under the project, leaving the DB
saying "completed" while every download link 404s.

The fix makes cleanup_old_jobs() skip any job_id present in either
ProjectService.get_referenced_job_ids() or HistoryService.
get_referenced_job_ids() before applying any age check.

History has no job_id column (VED-P1-012), but pipeline_service.py's
completion path writes HistoryService.add_history(reel_path=...) and
ProjectService.create_project(...) from the *same* final_reel value, in
the same try block, history first. If project registration then raises
(the except at pipeline_service.py's post-export step), the already
-committed History row is left as the only persistent reference to that
job's media -- so HistoryService.get_referenced_job_ids() derives job_id
by resolving reel_path against JOBS_FOLDER, the same way ReelService
constructs it, rather than assuming a matching Projects row exists.

Covers:
  A) The regression itself -- an old completed job backing a project
     row must survive cleanup, reproducing the exact production bug.
  B) Cleanup must still delete a job of the same age with no project
     row (selectivity -- protection is per-job_id, not global).
  C) A project's own job_id is protected even when other, unrelated old
     job folders around it are correctly swept.
  D) A job referenced ONLY by History (no Projects row -- the
     Project-Registration-failed-after-History-committed window) must
     also survive cleanup.
  E) A job with neither a Projects nor a History reference is still
     swept -- History protection is per-job_id, not a second blanket
     exemption.
"""

import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from app.config.config import settings
from app.services.cleanup_service import CleanupService
from app.services.database_service import DatabaseService
from app.services.history_service import HistoryService
from app.services.job_storage_service import JobStorageService
from app.services.project_service import ProjectService


def _make_isolated_db():
    tmp_dir = tempfile.TemporaryDirectory()
    DatabaseService.DB_DIR = Path(tmp_dir.name)
    DatabaseService.DB_PATH = Path(tmp_dir.name) / "test_agc.db"
    DatabaseService.initialize()
    return tmp_dir


def _insert_job(job_id, user_id, status, created_at=None, completed_at=None):
    connection = DatabaseService.get_connection()
    cursor = connection.cursor()
    created_at = created_at or datetime.utcnow().isoformat()
    cursor.execute(
        """
        INSERT INTO jobs
            (job_id, user_id, status, progress, message,
             created_at, completed_at)
        VALUES (?, ?, ?, 100, 'Completed', ?, ?)
        """,
        (job_id, user_id, status, created_at, completed_at),
    )
    connection.commit()
    connection.close()


def _write_artifact(job_id, subfolder, filename, content=b"data"):
    folder = JobStorageService.subfolder(job_id, subfolder)
    path = folder / filename
    with open(path, "wb") as file:
        file.write(content)
    return f"{subfolder}/{filename}"


def _age_job_folder(job_id, hours):
    import os

    job_dir = JobStorageService.job_dir(job_id)
    old_time = (datetime.now() - timedelta(hours=hours)).timestamp()

    for root, dirs, files in os.walk(job_dir):
        for name in files:
            os.utime(os.path.join(root, name), (old_time, old_time))
        os.utime(root, (old_time, old_time))

    os.utime(job_dir, (old_time, old_time))


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


class ProjectReferencedJobSurvivesCleanupTests(_IsolatedJobsEnvTestCase):

    def test_old_completed_job_referenced_by_project_is_not_deleted(self):
        """Reproduces the production bug: job 98891b68 completed, a
        projects row was created pointing at its media, TEMP_CLEANUP_HOURS
        passed, and cleanup ran again on a later job's completion."""

        job_id = "media-001-referenced-old-1"

        reel_path = _write_artifact(job_id, "reels", "final_highlight_reel.mp4")
        thumb_path = _write_artifact(job_id, "thumbnails", "thumbnail_14.jpg")

        _insert_job(
            job_id,
            user_id=103,
            status="completed",
            created_at=(datetime.utcnow() - timedelta(hours=96)).isoformat(),
            completed_at=(datetime.utcnow() - timedelta(hours=72)).isoformat(),
        )
        _age_job_folder(job_id, hours=72)

        ProjectService.create_project(
            user_id=103,
            job_id=job_id,
            original_video_name="gameplay.mp4",
            thumbnail_path=thumb_path,
            horizontal_reel_path=reel_path,
        )

        CleanupService.cleanup_old_jobs()

        job_dir = JobStorageService.job_dir(job_id)
        self.assertTrue(job_dir.exists())
        self.assertTrue((job_dir / reel_path).exists())
        self.assertTrue((job_dir / thumb_path).exists())

    def test_unreferenced_job_of_same_age_is_still_deleted(self):
        """Selectivity: protection is per-job_id via the projects table,
        not a blanket exemption for every completed job."""

        job_id = "media-001-unreferenced-old-1"

        _write_artifact(job_id, "clips", "a.mp4")

        _insert_job(
            job_id,
            user_id=104,
            status="completed",
            created_at=(datetime.utcnow() - timedelta(hours=96)).isoformat(),
            completed_at=(datetime.utcnow() - timedelta(hours=72)).isoformat(),
        )
        _age_job_folder(job_id, hours=72)

        CleanupService.cleanup_old_jobs()

        job_dir = JobStorageService.job_dir(job_id)
        self.assertFalse(job_dir.exists())

    def test_referenced_job_protected_while_sibling_unreferenced_job_is_swept(self):

        referenced_job_id = "media-001-sibling-referenced-1"
        unreferenced_job_id = "media-001-sibling-unreferenced-1"

        reel_path = _write_artifact(referenced_job_id, "reels", "final.mp4")
        _write_artifact(unreferenced_job_id, "clips", "a.mp4")

        for job_id in (referenced_job_id, unreferenced_job_id):
            _insert_job(
                job_id,
                user_id=105,
                status="completed",
                created_at=(datetime.utcnow() - timedelta(hours=96)).isoformat(),
                completed_at=(datetime.utcnow() - timedelta(hours=72)).isoformat(),
            )
            _age_job_folder(job_id, hours=72)

        ProjectService.create_project(
            user_id=105,
            job_id=referenced_job_id,
            original_video_name="gameplay.mp4",
            thumbnail_path=None,
            horizontal_reel_path=reel_path,
        )

        CleanupService.cleanup_old_jobs()

        self.assertTrue(
            JobStorageService.job_dir(referenced_job_id).exists()
        )
        self.assertFalse(
            JobStorageService.job_dir(unreferenced_job_id).exists()
        )


class HistoryOnlyReferenceSurvivesCleanupTests(_IsolatedJobsEnvTestCase):

    def test_job_referenced_only_by_history_is_not_deleted(self):
        """Reproduces the Project-Registration-failed-after-History
        -committed window: a History row exists with reel_path pointing
        into the job folder, but no Projects row was ever created for
        this job_id."""

        job_id = "media-001-history-only-old-1"

        reel_path = _write_artifact(job_id, "reels", "final_highlight_reel.mp4")

        _insert_job(
            job_id,
            user_id=106,
            status="completed",
            created_at=(datetime.utcnow() - timedelta(hours=96)).isoformat(),
            completed_at=(datetime.utcnow() - timedelta(hours=72)).isoformat(),
        )
        _age_job_folder(job_id, hours=72)

        job_dir = JobStorageService.job_dir(job_id)

        HistoryService.add_history(
            video_name="gameplay.mp4",
            reel_path=str(job_dir / reel_path),
            highlights_count=3,
            user_id=106,
        )

        self.assertEqual(ProjectService.get_referenced_job_ids(), set())

        CleanupService.cleanup_old_jobs()

        self.assertTrue(job_dir.exists())
        self.assertTrue((job_dir / reel_path).exists())

    def test_job_with_no_project_and_no_history_reference_is_still_deleted(self):
        """History protection must stay per-job_id -- a job with neither
        reference is still swept once stale."""

        job_id = "media-001-no-reference-old-1"

        _write_artifact(job_id, "clips", "a.mp4")

        _insert_job(
            job_id,
            user_id=107,
            status="completed",
            created_at=(datetime.utcnow() - timedelta(hours=96)).isoformat(),
            completed_at=(datetime.utcnow() - timedelta(hours=72)).isoformat(),
        )
        _age_job_folder(job_id, hours=72)

        # A History row for a DIFFERENT job exists in the same table, to
        # prove get_referenced_job_ids() isn't accidentally matching on
        # user_id or returning every job wholesale.
        other_job_id = "media-001-no-reference-sibling-1"
        other_reel_path = _write_artifact(other_job_id, "reels", "final.mp4")
        HistoryService.add_history(
            video_name="other.mp4",
            reel_path=str(JobStorageService.job_dir(other_job_id) / other_reel_path),
            highlights_count=1,
            user_id=107,
        )

        CleanupService.cleanup_old_jobs()

        self.assertFalse(JobStorageService.job_dir(job_id).exists())
        self.assertTrue(JobStorageService.job_dir(other_job_id).exists())


class HistoryGetReferencedJobIdsTests(_IsolatedJobsEnvTestCase):

    def test_derives_job_id_from_reel_path_under_jobs_folder(self):

        job_id = "media-001-history-derive-1"
        reel_path = _write_artifact(job_id, "reels", "final.mp4")
        job_dir = JobStorageService.job_dir(job_id)

        HistoryService.add_history(
            video_name="a.mp4",
            reel_path=str(job_dir / reel_path),
            highlights_count=1,
            user_id=1,
        )

        self.assertEqual(
            HistoryService.get_referenced_job_ids(),
            {job_id},
        )

    def test_ignores_null_and_unrelated_reel_paths(self):

        connection = DatabaseService.get_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO history (user_id, video_name, date, reel_path, highlights_count)
            VALUES (?, ?, ?, ?, ?)
            """,
            (1, "legacy.mp4", "2020-01-01", None, 0),
        )
        connection.commit()
        connection.close()

        HistoryService.add_history(
            video_name="unrelated.mp4",
            reel_path="/completely/unrelated/path.mp4",
            highlights_count=0,
            user_id=1,
        )

        self.assertEqual(HistoryService.get_referenced_job_ids(), set())


class GetReferencedJobIdsTests(_IsolatedJobsEnvTestCase):

    def test_returns_distinct_non_null_job_ids(self):

        ProjectService.create_project(
            user_id=1,
            job_id="job-a",
            original_video_name="a.mp4",
            thumbnail_path=None,
            horizontal_reel_path=None,
        )
        ProjectService.create_project(
            user_id=1,
            job_id="job-a",
            original_video_name="a-again.mp4",
            thumbnail_path=None,
            horizontal_reel_path=None,
        )
        ProjectService.create_project(
            user_id=2,
            job_id="job-b",
            original_video_name="b.mp4",
            thumbnail_path=None,
            horizontal_reel_path=None,
        )
        ProjectService.create_project(
            user_id=3,
            job_id=None,
            original_video_name="legacy-no-job.mp4",
            thumbnail_path=None,
            horizontal_reel_path=None,
        )

        referenced = ProjectService.get_referenced_job_ids()

        self.assertEqual(referenced, {"job-a", "job-b"})


if __name__ == "__main__":
    unittest.main()
