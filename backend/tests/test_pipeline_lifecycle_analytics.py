"""VED-ANALYTICS-005: backend-authoritative "Upload Started", "Upload
Completed", "Pipeline Started", "Pipeline Completed", and "pipeline_failed"
analytics.

VED-ANALYTICS-004's forensic audit found these events were tab-dependent
(fired from frontend/hooks/usePipeline.ts), the same flaw VED-ANALYTICS-002
fixed for "Highlights Generated". This moves emission to:
  - backend/app/routers/upload.py (Upload Started / Upload Completed)
  - JobService.start_processing() (Pipeline Started — new CAS-guarded
    pending->processing transition)
  - JobService.complete_job() (Pipeline Completed, alongside the existing
    Highlights Generated dispatch)
  - JobService.fail_job() (pipeline_failed — now CAS-guarded the same way
    complete_job() is)

Covers:
  A) UploadRouterAnalyticsTests — Upload Started/Completed via the real
     upload endpoint.
  B) StartProcessingAnalyticsTests — Pipeline Started exactly-once.
  C) CompleteJobPipelineAnalyticsTests — Pipeline Completed exactly-once,
     alongside Highlights Generated.
  D) FailJobAnalyticsTests — pipeline_failed exactly-once, CAS guard
     against clobbering a completed job.
  E) AnalyticsServiceTests — payload shape, dual-naming, safe properties,
     config safety, network-failure containment for all five new capture
     methods.
"""

import io
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config.config import settings
from app.dependencies import get_current_user
from app.routers import upload as upload_router_module
from app.services.analytics_service import AnalyticsService
from app.services.database_service import DatabaseService
from app.services.job_service import JobService


def _make_isolated_db():
    tmp_dir = tempfile.TemporaryDirectory()
    DatabaseService.DB_DIR = Path(tmp_dir.name)
    DatabaseService.DB_PATH = Path(tmp_dir.name) / "test_agc.db"
    DatabaseService.initialize()
    return tmp_dir


def _insert_job(job_id, user_id, status, progress=0, message="Job Created"):
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


FAKE_RESULT = {
    "stats": {"highlights_found": 2, "processing_time": 12.5},
    "all_highlights": [],
}


# ---------------------------------------------------------------------------
# A) Upload router — Upload Started / Upload Completed
# ---------------------------------------------------------------------------

_VALID_MP4_HEADER = bytes([0, 0, 0, 0x18]) + b"ftyp" + b"isom"
_FAKE_VIDEO_BYTES = _VALID_MP4_HEADER + b"\x00" * 32


def _fake_upload_file(filename="clip.mp4", content=_FAKE_VIDEO_BYTES):
    return {"file": (filename, io.BytesIO(content), "video/mp4")}


def _metadata(duration_seconds: float = 60) -> dict:
    return {
        "filename": "clip.mp4",
        "duration_seconds": duration_seconds,
        "resolution": "1920x1080",
        "fps": 30.0,
        "codec": "h264",
        "file_size_mb": 1.0,
    }


@pytest.fixture
def upload_client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_FOLDER", str(tmp_path))
    monkeypatch.setattr(settings, "MAX_VIDEO_DURATION_MINUTES", 10)
    monkeypatch.setattr(upload_router_module, "MAX_FILE_SIZE_BYTES", 10 * 1024 * 1024)
    monkeypatch.setattr(
        upload_router_module.RateLimitService,
        "is_rate_limited",
        lambda *args, **kwargs: False,
    )

    app = FastAPI()
    app.include_router(upload_router_module.router)
    app.dependency_overrides[get_current_user] = lambda: {
        "id": 1,
        "credits_remaining": 5,
    }

    with TestClient(app) as test_client:
        yield test_client


def test_upload_started_emitted_on_successful_upload(upload_client):
    with patch.object(
        upload_router_module, "get_video_metadata", return_value=_metadata()
    ), patch.object(
        upload_router_module.AnalyticsService, "capture_upload_started"
    ) as mock_started:

        response = upload_client.post("/upload/", files=_fake_upload_file())

    assert response.status_code == 200
    mock_started.assert_called_once_with(user_id=1)


def test_upload_started_not_emitted_when_rejected_before_acceptance(upload_client):
    """Upload Started represents an *accepted* upload — validation
    failures (bad extension here) happen before every gate passes, so it
    must not fire."""

    with patch.object(
        upload_router_module.AnalyticsService, "capture_upload_started"
    ) as mock_started:

        response = upload_client.post(
            "/upload/", files=_fake_upload_file(filename="notes.txt")
        )

    assert response.status_code == 400
    mock_started.assert_not_called()


def test_upload_completed_emitted_only_after_successful_completion(upload_client):
    with patch.object(
        upload_router_module, "get_video_metadata", return_value=_metadata()
    ), patch.object(
        upload_router_module.AnalyticsService, "capture_upload_completed"
    ) as mock_completed:

        response = upload_client.post("/upload/", files=_fake_upload_file())

    assert response.status_code == 200
    mock_completed.assert_called_once_with(user_id=1)


def test_upload_completed_not_emitted_when_duration_check_fails(upload_client, tmp_path):
    """Upload Started already fired by this point (file written), but
    Upload Completed must not fire for a rejected (too-long) upload."""

    over_limit_seconds = (settings.MAX_VIDEO_DURATION_MINUTES + 1) * 60

    with patch.object(
        upload_router_module,
        "get_video_metadata",
        return_value=_metadata(over_limit_seconds),
    ), patch.object(
        upload_router_module.AnalyticsService, "capture_upload_started"
    ), patch.object(
        upload_router_module.AnalyticsService, "capture_upload_completed"
    ) as mock_completed:

        response = upload_client.post("/upload/", files=_fake_upload_file())

    assert response.status_code == 400
    mock_completed.assert_not_called()


def test_analytics_failure_does_not_fail_the_upload(upload_client):
    with patch.object(
        upload_router_module, "get_video_metadata", return_value=_metadata()
    ), patch.object(
        upload_router_module.AnalyticsService,
        "capture_upload_started",
        side_effect=RuntimeError("PostHog unreachable"),
    ), patch.object(
        upload_router_module.AnalyticsService,
        "capture_upload_completed",
        side_effect=RuntimeError("PostHog unreachable"),
    ):

        response = upload_client.post("/upload/", files=_fake_upload_file())

    assert response.status_code == 200
    assert response.json()["success"] is True


# ---------------------------------------------------------------------------
# B) JobService.start_processing() — Pipeline Started exactly-once
# ---------------------------------------------------------------------------

class StartProcessingAnalyticsTests(unittest.TestCase):

    def setUp(self):
        self._db_tmp_dir = _make_isolated_db()
        self.addCleanup(self._db_tmp_dir.cleanup)

        self._capture_patch = patch(
            "app.services.job_service.AnalyticsService.capture_pipeline_started"
        )
        self.mock_capture = self._capture_patch.start()
        self.addCleanup(self._capture_patch.stop)

    def test_emits_exactly_once_on_pending_to_processing_transition(self):
        _insert_job("job-1", user_id=42, status="pending")

        JobService.start_processing(job_id="job-1")

        self.mock_capture.assert_called_once_with(user_id=42, job_id="job-1")

        job = JobService.get_job("job-1")
        self.assertEqual(job["status"], "processing")
        self.assertEqual(job["message"], "Pipeline Started")

    def test_duplicate_call_does_not_duplicate_analytics(self):
        _insert_job("job-2", user_id=7, status="pending")

        JobService.start_processing(job_id="job-2")
        JobService.start_processing(job_id="job-2")

        self.mock_capture.assert_called_once_with(user_id=7, job_id="job-2")

    def test_not_emitted_when_job_already_processing(self):
        _insert_job("job-3", user_id=9, status="processing")

        JobService.start_processing(job_id="job-3")

        self.mock_capture.assert_not_called()

    def test_unattributed_job_does_not_emit(self):
        _insert_job("job-4", user_id=None, status="pending")

        JobService.start_processing(job_id="job-4")

        self.mock_capture.assert_not_called()

    def test_analytics_failure_does_not_raise(self):
        self.mock_capture.side_effect = RuntimeError("PostHog unreachable")
        _insert_job("job-5", user_id=5, status="pending")

        # Must not raise.
        JobService.start_processing(job_id="job-5")

        job = JobService.get_job("job-5")
        self.assertEqual(job["status"], "processing")


# ---------------------------------------------------------------------------
# C) JobService.complete_job() — Pipeline Completed alongside Highlights
#    Generated
# ---------------------------------------------------------------------------

class CompleteJobPipelineAnalyticsTests(unittest.TestCase):

    def setUp(self):
        self._db_tmp_dir = _make_isolated_db()
        self.addCleanup(self._db_tmp_dir.cleanup)

        self._highlights_patch = patch(
            "app.services.job_service.AnalyticsService.capture_highlights_generated"
        )
        self.mock_highlights = self._highlights_patch.start()
        self.addCleanup(self._highlights_patch.stop)

        self._pipeline_patch = patch(
            "app.services.job_service.AnalyticsService.capture_pipeline_completed"
        )
        self.mock_pipeline = self._pipeline_patch.start()
        self.addCleanup(self._pipeline_patch.stop)

    def test_pipeline_completed_emits_exactly_once_with_processing_time(self):
        _insert_job("job-1", user_id=42, status="processing")

        JobService.complete_job(job_id="job-1", result=FAKE_RESULT)

        self.mock_pipeline.assert_called_once_with(
            user_id=42, job_id="job-1", processing_time_seconds=12.5
        )
        self.mock_highlights.assert_called_once_with(
            user_id=42, job_id="job-1", highlights_found=2
        )

    def test_retry_does_not_duplicate(self):
        _insert_job("job-2", user_id=13, status="processing")

        JobService.complete_job(job_id="job-2", result=FAKE_RESULT)
        JobService.complete_job(job_id="job-2", result=FAKE_RESULT)

        self.mock_pipeline.assert_called_once()

    def test_unattributed_job_does_not_emit(self):
        _insert_job("job-3", user_id=None, status="processing")

        JobService.complete_job(job_id="job-3", result=FAKE_RESULT)

        self.mock_pipeline.assert_not_called()

    def test_missing_processing_time_omits_property(self):
        _insert_job("job-4", user_id=8, status="processing")

        result_without_time = {"stats": {"highlights_found": 1}}

        JobService.complete_job(job_id="job-4", result=result_without_time)

        self.mock_pipeline.assert_called_once_with(
            user_id=8, job_id="job-4", processing_time_seconds=None
        )

    def test_pipeline_completed_failure_does_not_block_highlights_generated(self):
        """The two dispatches are isolated in separate try/except blocks —
        a failure in one must never suppress the other."""

        self.mock_pipeline.side_effect = RuntimeError("PostHog unreachable")
        _insert_job("job-5", user_id=3, status="processing")

        JobService.complete_job(job_id="job-5", result=FAKE_RESULT)

        self.mock_highlights.assert_called_once()

        job = JobService.get_job("job-5")
        self.assertEqual(job["status"], "completed")


# ---------------------------------------------------------------------------
# D) JobService.fail_job() — pipeline_failed exactly-once + CAS guard
# ---------------------------------------------------------------------------

class FailJobAnalyticsTests(unittest.TestCase):

    def setUp(self):
        self._db_tmp_dir = _make_isolated_db()
        self.addCleanup(self._db_tmp_dir.cleanup)

        self._capture_patch = patch(
            "app.services.job_service.AnalyticsService.capture_pipeline_failed"
        )
        self.mock_capture = self._capture_patch.start()
        self.addCleanup(self._capture_patch.stop)

    def test_emits_exactly_once(self):
        _insert_job("job-1", user_id=3, status="processing")

        JobService.fail_job(job_id="job-1", error="pipeline exploded")

        self.mock_capture.assert_called_once_with(user_id=3, job_id="job-1")

        job = JobService.get_job("job-1")
        self.assertEqual(job["status"], "failed")

    def test_duplicate_call_does_not_duplicate_analytics(self):
        _insert_job("job-2", user_id=4, status="processing")

        JobService.fail_job(job_id="job-2", error="first failure")
        JobService.fail_job(job_id="job-2", error="second failure")

        self.mock_capture.assert_called_once_with(user_id=4, job_id="job-2")

    def test_already_completed_job_is_never_clobbered_or_emitted(self):
        _insert_job(
            "job-3", user_id=6, status="completed", progress=100,
            message="Completed",
        )

        JobService.fail_job(job_id="job-3", error="late duplicate failure")

        self.mock_capture.assert_not_called()

        job = JobService.get_job("job-3")
        self.assertEqual(job["status"], "completed")

    def test_unattributed_job_does_not_emit(self):
        _insert_job("job-4", user_id=None, status="processing")

        JobService.fail_job(job_id="job-4", error="boom")

        self.mock_capture.assert_not_called()

    def test_no_raw_error_text_reaches_analytics_call(self):
        _insert_job("job-5", user_id=11, status="processing")

        JobService.fail_job(
            job_id="job-5", error="Traceback: secret internal path /srv/x"
        )

        self.mock_capture.assert_called_once_with(user_id=11, job_id="job-5")
        call_kwargs = self.mock_capture.call_args.kwargs
        self.assertNotIn("error", call_kwargs)

    def test_analytics_failure_does_not_raise(self):
        self.mock_capture.side_effect = RuntimeError("PostHog unreachable")
        _insert_job("job-6", user_id=1, status="processing")

        # Must not raise.
        JobService.fail_job(job_id="job-6", error="boom")

        job = JobService.get_job("job-6")
        self.assertEqual(job["status"], "failed")


# ---------------------------------------------------------------------------
# E) AnalyticsService — payload shape, dual-naming, safe properties, config
# ---------------------------------------------------------------------------

class AnalyticsServiceTests(unittest.TestCase):

    def setUp(self):
        self.settings = settings

    def test_missing_api_key_is_a_safe_noop_for_all_new_events(self):
        with patch.object(self.settings, "POSTHOG_API_KEY", ""), \
             patch.object(self.settings, "POSTHOG_HOST", "https://app.posthog.com"), \
             patch("app.services.analytics_service.requests.post") as mock_post:

            AnalyticsService.capture_upload_started(user_id=1)
            AnalyticsService.capture_upload_completed(user_id=1)
            AnalyticsService.capture_pipeline_started(user_id=1, job_id="job-x")
            AnalyticsService.capture_pipeline_completed(user_id=1, job_id="job-x")
            AnalyticsService.capture_pipeline_failed(user_id=1, job_id="job-x")

            mock_post.assert_not_called()

    def test_missing_host_is_a_safe_noop_for_all_new_events(self):
        with patch.object(self.settings, "POSTHOG_API_KEY", "phc_test"), \
             patch.object(self.settings, "POSTHOG_HOST", ""), \
             patch("app.services.analytics_service.requests.post") as mock_post:

            AnalyticsService.capture_upload_started(user_id=1)
            AnalyticsService.capture_upload_completed(user_id=1)
            AnalyticsService.capture_pipeline_started(user_id=1, job_id="job-x")
            AnalyticsService.capture_pipeline_completed(user_id=1, job_id="job-x")
            AnalyticsService.capture_pipeline_failed(user_id=1, job_id="job-x")

            mock_post.assert_not_called()

    def test_upload_started_sends_dual_event_names(self):
        with patch.object(self.settings, "POSTHOG_API_KEY", "phc_test"), \
             patch.object(self.settings, "POSTHOG_HOST", "https://app.posthog.com"), \
             patch("app.services.analytics_service.requests.post") as mock_post:

            AnalyticsService._send_upload_started(99)

            self.assertEqual(mock_post.call_count, 2)
            events = {c.kwargs["json"]["event"] for c in mock_post.call_args_list}
            self.assertEqual(events, {"upload_started", "Upload Started"})
            for call in mock_post.call_args_list:
                self.assertEqual(call.kwargs["json"]["distinct_id"], "99")
                self.assertEqual(call.kwargs["timeout"], AnalyticsService.CAPTURE_TIMEOUT_SECONDS)

    def test_upload_completed_carries_first_upload_set_property(self):
        with patch.object(self.settings, "POSTHOG_API_KEY", "phc_test"), \
             patch.object(self.settings, "POSTHOG_HOST", "https://app.posthog.com"), \
             patch("app.services.analytics_service.requests.post") as mock_post:

            AnalyticsService._send_upload_completed(99)

            self.assertEqual(mock_post.call_count, 2)
            pascal_call = next(
                c for c in mock_post.call_args_list
                if c.kwargs["json"]["event"] == "Upload Completed"
            )
            self.assertEqual(
                pascal_call.kwargs["json"]["properties"]["$set"],
                {"first_upload_completed": True},
            )

    def test_pipeline_started_sends_dual_event_names_with_job_id(self):
        with patch.object(self.settings, "POSTHOG_API_KEY", "phc_test"), \
             patch.object(self.settings, "POSTHOG_HOST", "https://app.posthog.com"), \
             patch("app.services.analytics_service.requests.post") as mock_post:

            AnalyticsService._send_pipeline_started(99, "job-y")

            self.assertEqual(mock_post.call_count, 2)
            events = {c.kwargs["json"]["event"] for c in mock_post.call_args_list}
            self.assertEqual(events, {"pipeline_started", "Pipeline Started"})
            for call in mock_post.call_args_list:
                self.assertEqual(call.kwargs["json"]["properties"]["job_id"], "job-y")

    def test_pipeline_completed_processing_time_only_on_pascal_event(self):
        with patch.object(self.settings, "POSTHOG_API_KEY", "phc_test"), \
             patch.object(self.settings, "POSTHOG_HOST", "https://app.posthog.com"), \
             patch("app.services.analytics_service.requests.post") as mock_post:

            AnalyticsService._send_pipeline_completed(99, "job-z", 42.5)

            self.assertEqual(mock_post.call_count, 2)
            snake_call = next(
                c for c in mock_post.call_args_list
                if c.kwargs["json"]["event"] == "pipeline_completed"
            )
            pascal_call = next(
                c for c in mock_post.call_args_list
                if c.kwargs["json"]["event"] == "Pipeline Completed"
            )
            self.assertNotIn(
                "processing_time_seconds", snake_call.kwargs["json"]["properties"]
            )
            self.assertEqual(
                pascal_call.kwargs["json"]["properties"]["processing_time_seconds"],
                42.5,
            )

    def test_pipeline_failed_sends_single_event_with_safe_status_only(self):
        with patch.object(self.settings, "POSTHOG_API_KEY", "phc_test"), \
             patch.object(self.settings, "POSTHOG_HOST", "https://app.posthog.com"), \
             patch("app.services.analytics_service.requests.post") as mock_post:

            AnalyticsService._send_pipeline_failed(99, "job-w")

            mock_post.assert_called_once()
            payload = mock_post.call_args.kwargs["json"]
            self.assertEqual(payload["event"], "pipeline_failed")
            self.assertEqual(payload["properties"]["status"], "failed")
            self.assertEqual(payload["properties"]["job_id"], "job-w")

            # No raw error/exception text anywhere in the payload — only a
            # fixed, safe "failed" status string.
            self.assertNotIn("error", str(payload).lower())
            self.assertNotIn("traceback", str(payload).lower())

    def test_no_pii_in_any_new_event_payload(self):
        with patch.object(self.settings, "POSTHOG_API_KEY", "phc_test"), \
             patch.object(self.settings, "POSTHOG_HOST", "https://app.posthog.com"), \
             patch("app.services.analytics_service.requests.post") as mock_post:

            AnalyticsService._send_upload_started(1)
            AnalyticsService._send_upload_completed(1)
            AnalyticsService._send_pipeline_started(1, "job-a")
            AnalyticsService._send_pipeline_completed(1, "job-a", 1.0)
            AnalyticsService._send_pipeline_failed(1, "job-a")

            for call in mock_post.call_args_list:
                payload_str = str(call.kwargs["json"]).lower()
                self.assertNotIn("email", payload_str)
                self.assertNotIn("password", payload_str)
                self.assertNotIn("token", payload_str)
                self.assertNotIn("razorpay", payload_str)

    def test_network_failure_is_caught_and_does_not_raise(self):
        with patch.object(self.settings, "POSTHOG_API_KEY", "phc_test"), \
             patch.object(self.settings, "POSTHOG_HOST", "https://app.posthog.com"), \
             patch(
                 "app.services.analytics_service.requests.post",
                 side_effect=ConnectionError("network unreachable"),
             ):

            # Must not raise for any of the five new events.
            AnalyticsService._send_upload_started(1)
            AnalyticsService._send_upload_completed(1)
            AnalyticsService._send_pipeline_started(1, "job-b")
            AnalyticsService._send_pipeline_completed(1, "job-b", None)
            AnalyticsService._send_pipeline_failed(1, "job-b")


if __name__ == "__main__":
    unittest.main()
