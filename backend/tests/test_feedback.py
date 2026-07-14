"""GROW-005: In-app user feedback loop.

Covers:
  - unauthenticated requests are rejected
  - valid feedback is accepted and persisted with the new fields
  - rating / improvement_area validation restricts values to the approved set
  - a JSON boolean is not silently coerced into a valid integer rating
  - oversized comments are rejected and valid comments are trimmed
  - feedback is scoped to the authenticated user (ownership of feedback rows)
  - a supplied project_id must exist and belong to the submitting user
  - duplicate feedback for the same project is rejected (409)
"""

import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.dependencies import get_current_user
from app.routers import feedback as feedback_router_module
from app.services.database_service import DatabaseService
from app.services.project_service import ProjectService


def _make_isolated_db():
    tmp_dir = tempfile.TemporaryDirectory()
    DatabaseService.DB_DIR = Path(tmp_dir.name)
    DatabaseService.DB_PATH = Path(tmp_dir.name) / "test_agc.db"
    DatabaseService.initialize()
    return tmp_dir


def _create_project(user_id: int) -> int:
    return ProjectService.create_project(
        user_id=user_id,
        job_id=f"job-{user_id}",
        original_video_name="clip.mp4",
        thumbnail_path=None,
        horizontal_reel_path=None,
    )


class FeedbackEndpointTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = _make_isolated_db()
        self.app = FastAPI()
        self.app.include_router(feedback_router_module.router)
        self.client = TestClient(self.app)

    def tearDown(self):
        self._tmp_dir.cleanup()

    def _as_user(self, user_id: int):
        self.app.dependency_overrides[get_current_user] = lambda: {"id": user_id}

    def test_unauthenticated_post_is_rejected(self):
        response = self.client.post("/feedback", json={"rating": 4})
        self.assertEqual(response.status_code, 401)

    def test_valid_feedback_without_a_project_is_accepted(self):
        self._as_user(1)

        response = self.client.post(
            "/feedback",
            json={"rating": 4, "improvement_area": "clip_timing", "comment": "Loved it"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["rating"], 4)
        self.assertEqual(body["data"]["improvement_area"], "clip_timing")
        self.assertEqual(body["data"]["comment"], "Loved it")
        self.assertEqual(body["data"]["user_id"], 1)

    def test_valid_feedback_for_an_owned_project_is_accepted(self):
        self._as_user(1)
        project_id = _create_project(1)

        response = self.client.post(
            "/feedback", json={"project_id": project_id, "rating": 3}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["project_id"], project_id)

    def test_rating_outside_approved_range_is_rejected(self):
        self._as_user(1)

        response = self.client.post("/feedback", json={"rating": 5})

        self.assertEqual(response.status_code, 422)

    def test_boolean_rating_is_not_coerced_into_a_valid_integer(self):
        self._as_user(1)

        response = self.client.post("/feedback", json={"rating": True})

        self.assertEqual(response.status_code, 422)

    def test_invalid_improvement_area_is_rejected(self):
        self._as_user(1)

        response = self.client.post(
            "/feedback", json={"rating": 3, "improvement_area": "not_a_real_option"}
        )

        self.assertEqual(response.status_code, 422)

    def test_oversized_comment_is_rejected(self):
        self._as_user(1)

        response = self.client.post(
            "/feedback", json={"rating": 3, "comment": "x" * 501}
        )

        self.assertEqual(response.status_code, 422)

    def test_comment_is_trimmed_and_blank_comment_becomes_null(self):
        self._as_user(1)

        response = self.client.post(
            "/feedback", json={"rating": 3, "comment": "   "}
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["data"]["comment"])

        response = self.client.post(
            "/feedback", json={"rating": 3, "comment": "  nice  "}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["comment"], "nice")

    def test_feedback_belongs_to_authenticated_user(self):
        self._as_user(1)
        self.client.post("/feedback", json={"rating": 4})

        self._as_user(2)
        self.client.post("/feedback", json={"rating": 2})

        self._as_user(1)
        response = self.client.get("/feedback")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["count"], 1)
        self.assertTrue(all(item["user_id"] == 1 for item in body["data"]))

    def test_nonexistent_project_id_is_rejected(self):
        self._as_user(1)

        response = self.client.post(
            "/feedback", json={"project_id": 999999, "rating": 3}
        )

        self.assertEqual(response.status_code, 404)

    def test_project_id_owned_by_another_user_is_rejected(self):
        other_users_project = _create_project(2)

        self._as_user(1)
        response = self.client.post(
            "/feedback", json={"project_id": other_users_project, "rating": 3}
        )

        self.assertEqual(response.status_code, 404)

    def test_duplicate_feedback_for_same_project_is_rejected(self):
        self._as_user(1)
        project_id = _create_project(1)

        first = self.client.post(
            "/feedback", json={"project_id": project_id, "rating": 3}
        )
        self.assertEqual(first.status_code, 200)

        second = self.client.post(
            "/feedback", json={"project_id": project_id, "rating": 1}
        )
        self.assertEqual(second.status_code, 409)

    def test_multiple_submissions_without_a_project_id_are_allowed(self):
        self._as_user(1)

        first = self.client.post("/feedback", json={"rating": 4})
        second = self.client.post("/feedback", json={"rating": 3})

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)

    def test_delete_of_unowned_feedback_returns_404(self):
        self._as_user(1)
        created = self.client.post("/feedback", json={"rating": 4}).json()["data"]["id"]

        self._as_user(2)
        response = self.client.delete(f"/feedback/{created}")

        self.assertEqual(response.status_code, 404)


class FeedbackMigrationSafetyTests(unittest.TestCase):
    """Verifies idx_feedback_user_project doesn't crash app startup when
    historical duplicate (user_id, project_id) rows already exist."""

    def setUp(self):
        self._tmp_dir = _make_isolated_db()

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_initialize_survives_preexisting_duplicate_rows(self):
        connection = DatabaseService.get_connection()
        cursor = connection.cursor()

        # Simulate a pre-GROW-005 production DB that already has duplicate
        # (user_id, project_id) feedback rows the new unique index can't
        # accommodate.
        cursor.execute("DROP INDEX IF EXISTS idx_feedback_user_project")
        cursor.execute(
            "INSERT INTO feedback (user_id, project_id, rating, created_at) "
            "VALUES (1, 7, 4, '2026-01-01T00:00:00')"
        )
        cursor.execute(
            "INSERT INTO feedback (user_id, project_id, rating, created_at) "
            "VALUES (1, 7, 2, '2026-01-02T00:00:00')"
        )
        connection.commit()
        connection.close()

        # Must not raise, and must not delete the pre-existing rows.
        DatabaseService.initialize()

        connection = DatabaseService.get_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM feedback WHERE user_id = 1 AND project_id = 7")
        count = cursor.fetchone()[0]
        connection.close()

        self.assertEqual(count, 2)


if __name__ == "__main__":
    unittest.main()
