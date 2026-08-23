"""VED-MEDIA-002: "Media unavailable" UX for projects/history whose
persisted media no longer exists on disk (see VED-MEDIA-001).

Covers:
  1. Project with all media present -> both *_available flags true.
  2. Project with missing thumbnail but existing reel -> thumbnail
     unavailable, reel still usable.
  3. Project with missing reel -> horizontal_reel_available false.
  4. Project with all media missing -> both flags false.
  5. History with existing reel -> reel_available true.
  6. History with missing reel -> reel_available false.
  7. Existing authorization (per-user scoping) still enforced.
  8. Missing/garbage paths never cause a 500 -- FileSafetyService.
     is_available() and the /projects, /history/ endpoints all degrade
     to False/empty, never raise.
  9. Path traversal cannot be introduced -- is_available() reuses the
     same _is_safe_target boundary safe_delete_file already uses, so a
     path outside the approved storage roots (even one that genuinely
     exists on disk) is reported unavailable, not leaked as available.
  10. VED-MEDIA-001's cleanup_old_jobs reference-aware behavior is
      unaffected -- covered by test_ved_media_001_cleanup_reference_aware.py
      still passing unchanged (run as part of the full suite, not
      duplicated here).
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config.config import settings
from app.dependencies import get_current_user
from app.routers import history as history_router_module
from app.routers import projects as projects_router_module
from app.services.database_service import DatabaseService
from app.services.file_safety_service import FileSafetyService
from app.services.history_service import HistoryService
from app.services.job_storage_service import JobStorageService
from app.services.project_service import ProjectService


def _make_isolated_db():
    tmp_dir = tempfile.TemporaryDirectory()
    DatabaseService.DB_DIR = Path(tmp_dir.name)
    DatabaseService.DB_PATH = Path(tmp_dir.name) / "test_agc.db"
    DatabaseService.initialize()
    return tmp_dir


def _write_artifact(job_id, subfolder, filename, content=b"data"):
    folder = JobStorageService.subfolder(job_id, subfolder)
    path = folder / filename
    with open(path, "wb") as file:
        file.write(content)
    return str(path)


class _IsolatedStorageTestCase(unittest.TestCase):

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


# ---------------------------------------------------------------------------
# FileSafetyService.is_available -- the shared, security-critical primitive
# ---------------------------------------------------------------------------

class IsAvailableTests(_IsolatedStorageTestCase):

    def test_none_path_is_unavailable(self):
        self.assertFalse(FileSafetyService.is_available(None))

    def test_empty_string_path_is_unavailable(self):
        self.assertFalse(FileSafetyService.is_available(""))
        self.assertFalse(FileSafetyService.is_available("   "))

    def test_existing_file_inside_allowed_root_is_available(self):
        path = _write_artifact("job-a", "reels", "final.mp4")
        self.assertTrue(FileSafetyService.is_available(path))

    def test_missing_file_inside_allowed_root_is_unavailable(self):
        missing_path = str(
            Path(self._jobs_tmp_dir.name) / "job-a" / "reels" / "gone.mp4"
        )
        self.assertFalse(FileSafetyService.is_available(missing_path))

    def test_directory_is_not_reported_available(self):
        folder = JobStorageService.subfolder("job-a", "reels")
        self.assertFalse(FileSafetyService.is_available(str(folder)))

    def test_existing_file_outside_allowed_roots_is_unavailable(self):
        """Path traversal / boundary protection: a file that genuinely
        exists on disk, but outside every approved storage root, must
        never be reported available."""

        with tempfile.TemporaryDirectory() as outside_dir:
            outside_file = Path(outside_dir) / "secret.txt"
            outside_file.write_bytes(b"not application storage")

            self.assertFalse(
                FileSafetyService.is_available(str(outside_file))
            )

    def test_traversal_string_resolving_outside_roots_is_unavailable(self):
        job_dir = JobStorageService.subfolder("job-a", "reels")
        traversal_path = str(
            Path(job_dir) / ".." / ".." / ".." / "outside.mp4"
        )
        self.assertFalse(FileSafetyService.is_available(traversal_path))

    def test_malformed_path_never_raises(self):
        # Embedded NUL is invalid on both POSIX and Windows path APIs.
        self.assertFalse(FileSafetyService.is_available("bad\x00path"))


# ---------------------------------------------------------------------------
# ProjectService -- attaches thumbnail_available / horizontal_reel_available
# ---------------------------------------------------------------------------

class ProjectServiceAvailabilityTests(_IsolatedStorageTestCase):

    def test_all_media_present_reports_both_available(self):
        thumb = _write_artifact("job-1", "thumbnails", "t.jpg")
        reel = _write_artifact("job-1", "reels", "final.mp4")

        project_id = ProjectService.create_project(
            user_id=1,
            job_id="job-1",
            original_video_name="a.mp4",
            thumbnail_path=thumb,
            horizontal_reel_path=reel,
        )

        projects = ProjectService.get_projects(user_id=1)
        self.assertEqual(len(projects), 1)
        self.assertTrue(projects[0]["thumbnail_available"])
        self.assertTrue(projects[0]["horizontal_reel_available"])

        single = ProjectService.get_project(user_id=1, project_id=project_id)
        self.assertTrue(single["thumbnail_available"])
        self.assertTrue(single["horizontal_reel_available"])

    def test_missing_thumbnail_with_existing_reel(self):
        reel = _write_artifact("job-2", "reels", "final.mp4")
        missing_thumb = str(
            Path(self._jobs_tmp_dir.name) / "job-2" / "thumbnails" / "gone.jpg"
        )

        ProjectService.create_project(
            user_id=2,
            job_id="job-2",
            original_video_name="b.mp4",
            thumbnail_path=missing_thumb,
            horizontal_reel_path=reel,
        )

        project = ProjectService.get_projects(user_id=2)[0]
        self.assertFalse(project["thumbnail_available"])
        self.assertTrue(project["horizontal_reel_available"])

    def test_missing_reel_is_reported_unavailable(self):
        thumb = _write_artifact("job-3", "thumbnails", "t.jpg")
        missing_reel = str(
            Path(self._jobs_tmp_dir.name) / "job-3" / "reels" / "gone.mp4"
        )

        ProjectService.create_project(
            user_id=3,
            job_id="job-3",
            original_video_name="c.mp4",
            thumbnail_path=thumb,
            horizontal_reel_path=missing_reel,
        )

        project = ProjectService.get_projects(user_id=3)[0]
        self.assertTrue(project["thumbnail_available"])
        self.assertFalse(project["horizontal_reel_available"])

    def test_all_media_missing(self):
        missing_thumb = str(
            Path(self._jobs_tmp_dir.name) / "job-4" / "thumbnails" / "gone.jpg"
        )
        missing_reel = str(
            Path(self._jobs_tmp_dir.name) / "job-4" / "reels" / "gone.mp4"
        )

        ProjectService.create_project(
            user_id=4,
            job_id="job-4",
            original_video_name="d.mp4",
            thumbnail_path=missing_thumb,
            horizontal_reel_path=missing_reel,
        )

        project = ProjectService.get_projects(user_id=4)[0]
        self.assertFalse(project["thumbnail_available"])
        self.assertFalse(project["horizontal_reel_available"])

    def test_null_paths_report_unavailable_not_a_crash(self):
        ProjectService.create_project(
            user_id=5,
            job_id=None,
            original_video_name="e.mp4",
            thumbnail_path=None,
            horizontal_reel_path=None,
        )

        project = ProjectService.get_projects(user_id=5)[0]
        self.assertFalse(project["thumbnail_available"])
        self.assertFalse(project["horizontal_reel_available"])

    def test_get_projects_does_not_mutate_persisted_paths(self):
        reel = _write_artifact("job-6", "reels", "final.mp4")

        ProjectService.create_project(
            user_id=6,
            job_id="job-6",
            original_video_name="f.mp4",
            thumbnail_path=None,
            horizontal_reel_path=reel,
        )

        project = ProjectService.get_projects(user_id=6)[0]
        self.assertEqual(project["horizontal_reel_path"], reel)
        self.assertIsNone(project["thumbnail_path"])


# ---------------------------------------------------------------------------
# HistoryService -- attaches reel_available
# ---------------------------------------------------------------------------

class HistoryServiceAvailabilityTests(_IsolatedStorageTestCase):

    def test_existing_reel_reports_available(self):
        reel = _write_artifact("job-h1", "reels", "final.mp4")

        HistoryService.add_history(
            video_name="g.mp4",
            reel_path=reel,
            highlights_count=3,
            user_id=7,
        )

        item = HistoryService.get_history(user_id=7)[0]
        self.assertTrue(item["reel_available"])

    def test_missing_reel_reports_unavailable(self):
        missing_reel = str(
            Path(self._jobs_tmp_dir.name) / "job-h2" / "reels" / "gone.mp4"
        )

        HistoryService.add_history(
            video_name="h.mp4",
            reel_path=missing_reel,
            highlights_count=1,
            user_id=8,
        )

        item = HistoryService.get_history(user_id=8)[0]
        self.assertFalse(item["reel_available"])
        # Preserved metadata, per VED-MEDIA-002 UX requirements.
        self.assertEqual(item["video_name"], "h.mp4")
        self.assertEqual(item["highlights_count"], 1)


# ---------------------------------------------------------------------------
# Router-level: authorization, response shape, no 500s
# ---------------------------------------------------------------------------

class ProjectsRouterAvailabilityTests(_IsolatedStorageTestCase):

    def setUp(self):
        super().setUp()
        self.app = FastAPI()
        self.app.include_router(projects_router_module.router)
        self.client = TestClient(self.app)

    def _as_user(self, user_id: int):
        self.app.dependency_overrides[get_current_user] = lambda: {"id": user_id}

    def test_unauthenticated_request_is_rejected(self):
        response = self.client.get("/projects")
        self.assertEqual(response.status_code, 401)

    def test_response_includes_availability_flags_and_no_500(self):
        missing_reel = str(
            Path(self._jobs_tmp_dir.name) / "job-r1" / "reels" / "gone.mp4"
        )
        ProjectService.create_project(
            user_id=10,
            job_id="job-r1",
            original_video_name="i.mp4",
            thumbnail_path=None,
            horizontal_reel_path=missing_reel,
        )

        self._as_user(10)
        response = self.client.get("/projects")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["data"]), 1)
        self.assertIn("thumbnail_available", body["data"][0])
        self.assertIn("horizontal_reel_available", body["data"][0])
        self.assertFalse(body["data"][0]["horizontal_reel_available"])

    def test_user_only_sees_own_projects_availability(self):
        """Existing per-user authorization is untouched by this change --
        a project owned by user 11 must never be visible to user 12."""

        reel = _write_artifact("job-r2", "reels", "final.mp4")
        ProjectService.create_project(
            user_id=11,
            job_id="job-r2",
            original_video_name="j.mp4",
            thumbnail_path=None,
            horizontal_reel_path=reel,
        )

        self._as_user(12)
        response = self.client.get("/projects")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"], [])


class HistoryRouterAvailabilityTests(_IsolatedStorageTestCase):

    def setUp(self):
        super().setUp()
        self.app = FastAPI()
        self.app.include_router(history_router_module.router)
        self.client = TestClient(self.app)

    def _as_user(self, user_id: int):
        self.app.dependency_overrides[get_current_user] = lambda: {"id": user_id}

    def test_unauthenticated_request_is_rejected(self):
        response = self.client.get("/history/")
        self.assertEqual(response.status_code, 401)

    def test_response_includes_reel_available_and_no_500(self):
        missing_reel = str(
            Path(self._jobs_tmp_dir.name) / "job-h3" / "reels" / "gone.mp4"
        )
        HistoryService.add_history(
            video_name="k.mp4",
            reel_path=missing_reel,
            highlights_count=2,
            user_id=13,
        )

        self._as_user(13)
        response = self.client.get("/history/")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["data"]), 1)
        self.assertIn("reel_available", body["data"][0])
        self.assertFalse(body["data"][0]["reel_available"])

    def test_user_only_sees_own_history(self):
        reel = _write_artifact("job-h4", "reels", "final.mp4")
        HistoryService.add_history(
            video_name="l.mp4",
            reel_path=reel,
            highlights_count=1,
            user_id=14,
        )

        self._as_user(15)
        response = self.client.get("/history/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"], [])


if __name__ == "__main__":
    unittest.main()
