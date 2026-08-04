"""VED-OPS-001: internal Operations API (/api/v1/ops/*).

Covers:
  - verify_ops_api_key rejects missing/malformed/wrong keys and accepts the
    correct one (dependency unit tests + end-to-end through the router)
  - response schema (exact key sets) for every endpoint, incl. the CR-037
    capabilities shape and the CR-038 "no api_version field" rule
  - endpoint behavior against seeded fixture data
  - no PII ever appears in /users or /summary
  - failure isolation: one failing section in /summary doesn't break others
  - a loose performance smoke check
"""

import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.config.config import settings
from app.dependencies import verify_ops_api_key
from app.routers import ops as ops_router_module
from app.services.database_service import DatabaseService
from app.services.ops_service import OpsService

_TEST_OPS_KEY = "test-ops-key-0123456789abcdef"


def _make_isolated_db():
    tmp_dir = tempfile.TemporaryDirectory()
    DatabaseService.DB_DIR = Path(tmp_dir.name)
    DatabaseService.DB_PATH = Path(tmp_dir.name) / "test_agc.db"
    DatabaseService.initialize()
    OpsService._cache.clear()
    return tmp_dir


def _create_user(
    email: str,
    is_admin: bool = False,
    is_internal: bool = False,
    email_verified: bool = False,
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

    if is_admin or is_internal or email_verified:
        connection = DatabaseService.get_connection()
        cursor = connection.cursor()
        if is_admin:
            cursor.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (user_id,))
        if is_internal:
            cursor.execute("UPDATE users SET is_internal = 1 WHERE id = ?", (user_id,))
        if email_verified:
            cursor.execute("UPDATE users SET email_verified = 1 WHERE id = ?", (user_id,))
        connection.commit()
        connection.close()

    return user_id


def _insert_job(
    user_id,
    status: str,
    created_at: str = None,
    started_at: str = None,
    completed_at: str = None,
) -> None:
    connection = DatabaseService.get_connection()
    cursor = connection.cursor()
    now = created_at or datetime.utcnow().isoformat()
    cursor.execute(
        """
        INSERT INTO jobs (job_id, user_id, status, progress, created_at, started_at, completed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (f"job-{status}-{uuid4().hex}", user_id, status, 0, now, started_at, completed_at),
    )
    connection.commit()
    connection.close()


class VerifyOpsApiKeyDependencyTests(unittest.TestCase):

    def setUp(self):
        self._original_key = settings.OPS_API_KEY
        settings.OPS_API_KEY = _TEST_OPS_KEY

    def tearDown(self):
        settings.OPS_API_KEY = self._original_key

    def test_rejects_missing_header(self):
        with self.assertRaises(HTTPException) as ctx:
            verify_ops_api_key(authorization=None)
        self.assertEqual(ctx.exception.status_code, 401)

    def test_rejects_non_bearer_scheme(self):
        with self.assertRaises(HTTPException) as ctx:
            verify_ops_api_key(authorization=_TEST_OPS_KEY)
        self.assertEqual(ctx.exception.status_code, 401)

    def test_rejects_wrong_key_same_length(self):
        wrong_key = "x" * len(_TEST_OPS_KEY)
        with self.assertRaises(HTTPException) as ctx:
            verify_ops_api_key(authorization=f"Bearer {wrong_key}")
        self.assertEqual(ctx.exception.status_code, 401)

    def test_rejects_when_no_key_configured(self):
        settings.OPS_API_KEY = ""
        with self.assertRaises(HTTPException) as ctx:
            verify_ops_api_key(authorization=f"Bearer {_TEST_OPS_KEY}")
        self.assertEqual(ctx.exception.status_code, 401)

    def test_accepts_correct_key(self):
        self.assertIsNone(verify_ops_api_key(authorization=f"Bearer {_TEST_OPS_KEY}"))


class OpsEndpointAuthTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = _make_isolated_db()
        self._original_key = settings.OPS_API_KEY
        settings.OPS_API_KEY = _TEST_OPS_KEY
        self.app = FastAPI()
        self.app.include_router(ops_router_module.router)
        self.client = TestClient(self.app)

    def tearDown(self):
        self._tmp_dir.cleanup()
        settings.OPS_API_KEY = self._original_key

    def test_missing_key_rejected_end_to_end(self):
        # No dependency override: falls through to the real
        # verify_ops_api_key, which requires a bearer key.
        response = self.client.get("/api/v1/ops/summary")
        self.assertEqual(response.status_code, 401)

    def test_wrong_key_rejected_end_to_end(self):
        response = self.client.get(
            "/api/v1/ops/summary",
            headers={"Authorization": "Bearer wrong-key"},
        )
        self.assertEqual(response.status_code, 401)

    def test_correct_key_accepted_end_to_end(self):
        response = self.client.get(
            "/api/v1/ops/summary",
            headers={"Authorization": f"Bearer {_TEST_OPS_KEY}"},
        )
        self.assertEqual(response.status_code, 200)

    def test_customer_jwt_auth_does_not_grant_ops_access(self):
        # CR-040: completely independent from customer authentication.
        # A request with no ops key (even if it carried a valid customer
        # JWT elsewhere) must still be rejected here — this router never
        # consults get_current_user/require_admin at all.
        response = self.client.get(
            "/api/v1/ops/summary",
            headers={"Authorization": "Bearer some-customer-jwt-token"},
        )
        self.assertEqual(response.status_code, 401)


class OpsEndpointSchemaAndBehaviorTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = _make_isolated_db()
        self.app = FastAPI()
        self.app.include_router(ops_router_module.router)
        self.app.dependency_overrides[verify_ops_api_key] = lambda: None
        self.client = TestClient(self.app)

    def tearDown(self):
        self._tmp_dir.cleanup()
        self.app.dependency_overrides.clear()

    def test_capabilities_matches_cr037_shape(self):
        response = self.client.get("/api/v1/ops/capabilities")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(set(body.keys()), {"contract_version", "version", "features"})
        self.assertEqual(body["contract_version"], "v1")
        self.assertEqual(
            body["features"],
            ["health", "system", "jobs", "storage", "users", "queue", "summary"],
        )

    def test_no_api_version_field_in_any_payload(self):
        # CR-038: the URI version is the contract now.
        for path in (
            "/api/v1/ops/capabilities",
            "/api/v1/ops/health",
            "/api/v1/ops/system",
            "/api/v1/ops/jobs",
            "/api/v1/ops/storage",
            "/api/v1/ops/users",
            "/api/v1/ops/queue",
            "/api/v1/ops/summary",
        ):
            response = self.client.get(path)
            self.assertNotIn("api_version", str(response.json()))

    def test_health_schema(self):
        response = self.client.get("/api/v1/ops/health")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("status", body)
        self.assertIn("database", body)
        self.assertIn("ffmpeg", body)

    def test_system_schema(self):
        response = self.client.get("/api/v1/ops/system")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(
            set(body.keys()),
            {"status", "environment", "uptime_seconds", "python_version", "ffmpeg", "build", "disk"},
        )

    def test_jobs_counts_and_average_duration(self):
        user_id = _create_user("jobs@test.com")
        _insert_job(user_id, "pending")
        _insert_job(user_id, "processing")
        _insert_job(
            user_id,
            "completed",
            started_at="2026-01-01T10:00:00",
            completed_at="2026-01-01T10:01:00",
        )
        _insert_job(user_id, "failed")

        response = self.client.get("/api/v1/ops/jobs")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(
            set(body.keys()),
            {
                "status", "total_jobs", "pending_jobs", "processing_jobs",
                "completed_jobs", "failed_jobs", "average_processing_time_seconds",
            },
        )
        self.assertEqual(body["total_jobs"], 4)
        self.assertEqual(body["pending_jobs"], 1)
        self.assertEqual(body["processing_jobs"], 1)
        self.assertEqual(body["completed_jobs"], 1)
        self.assertEqual(body["failed_jobs"], 1)
        self.assertEqual(body["average_processing_time_seconds"], 60.0)

    def test_storage_schema_no_filesystem_walk_fields(self):
        response = self.client.get("/api/v1/ops/storage")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(set(body.keys()), {"status", "disk", "jobs_in_flight"})

    def test_users_counts_and_no_pii(self):
        _create_user("verified@test.com", email_verified=True)
        _create_user("admin@test.com", is_admin=True)
        _create_user("internal@test.com", is_internal=True)
        _create_user("plain@test.com")

        response = self.client.get("/api/v1/ops/users")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(
            set(body.keys()),
            {"status", "total_users", "verified_users", "admin_users", "internal_users"},
        )
        self.assertEqual(body["total_users"], 4)
        self.assertEqual(body["verified_users"], 1)
        self.assertEqual(body["admin_users"], 1)
        self.assertEqual(body["internal_users"], 1)

        serialized = str(body).lower()
        for forbidden in (
            "verified@test.com", "admin@test.com", "internal@test.com",
            "plain@test.com", "password", "hash",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_queue_depth(self):
        user_id = _create_user("queue@test.com")
        _insert_job(user_id, "pending")
        _insert_job(user_id, "processing")
        _insert_job(user_id, "completed")

        response = self.client.get("/api/v1/ops/queue")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(set(body.keys()), {"status", "queue_depth", "max_concurrent_jobs"})
        self.assertEqual(body["queue_depth"], 2)

    def test_summary_contains_all_sections(self):
        response = self.client.get("/api/v1/ops/summary")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(set(body.keys()), {"health", "jobs", "storage", "users", "queue"})

    def test_summary_no_pii(self):
        _create_user("secret-summary@test.com")

        response = self.client.get("/api/v1/ops/summary")

        serialized = str(response.json()).lower()
        for forbidden in ("secret-summary@test.com", "password"):
            self.assertNotIn(forbidden, serialized)


class OpsFailureIsolationTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = _make_isolated_db()
        self.app = FastAPI()
        self.app.include_router(ops_router_module.router)
        self.app.dependency_overrides[verify_ops_api_key] = lambda: None
        self.client = TestClient(self.app)

    def tearDown(self):
        self._tmp_dir.cleanup()
        self.app.dependency_overrides.clear()

    def test_one_failing_section_does_not_break_summary(self):
        with patch.object(
            OpsService,
            "_compute_users",
            side_effect=RuntimeError("simulated users query failure"),
        ):
            response = self.client.get("/api/v1/ops/summary")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["users"], {"status": "unavailable"})
        self.assertIn("total_jobs", body["jobs"])
        self.assertIn("status", body["health"])
        self.assertIn("queue_depth", body["queue"])

    def test_endpoint_level_failure_returns_200_with_unavailable_status(self):
        with patch.object(
            OpsService,
            "_compute_jobs",
            side_effect=RuntimeError("simulated jobs query failure"),
        ):
            response = self.client.get("/api/v1/ops/jobs")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "unavailable"})


class OpsPerformanceSmokeTests(unittest.TestCase):
    """Loose wall-clock smoke check against a small fixture DB — not a true
    p95 SLA measurement. Real p95 validation needs a load-test tool (locust/
    k6); see known limitations."""

    def setUp(self):
        self._tmp_dir = _make_isolated_db()
        self.app = FastAPI()
        self.app.include_router(ops_router_module.router)
        self.app.dependency_overrides[verify_ops_api_key] = lambda: None
        self.client = TestClient(self.app)

        user_id = _create_user("perf@test.com")
        for i in range(50):
            _insert_job(user_id, "completed" if i % 2 == 0 else "failed")

    def tearDown(self):
        self._tmp_dir.cleanup()
        self.app.dependency_overrides.clear()

    def test_summary_responds_quickly_against_small_dataset(self):
        start = time.perf_counter()
        response = self.client.get("/api/v1/ops/summary")
        elapsed_ms = (time.perf_counter() - start) * 1000

        self.assertEqual(response.status_code, 200)
        self.assertLess(elapsed_ms, 500)

    def test_cached_second_call_is_not_slower(self):
        first_start = time.perf_counter()
        self.client.get("/api/v1/ops/jobs")
        first_elapsed = time.perf_counter() - first_start

        second_start = time.perf_counter()
        self.client.get("/api/v1/ops/jobs")
        second_elapsed = time.perf_counter() - second_start

        # Cached call should never be meaningfully slower than the cold one.
        self.assertLessEqual(second_elapsed, first_elapsed + 0.1)


if __name__ == "__main__":
    unittest.main()
