"""VED-GROWTH-005: every /upload exit path must emit a single structured
"upload_result" log carrying user_id + request_id + failure_stage + HTTP
status + a safe reason_code, so production access logs (which today only
show "POST /upload -> 400/200") can be joined back to a specific user and
cause. Observability-only — no upload business logic is exercised here that
wasn't already covered by the existing upload test files; these tests only
assert on the structured logging side effect of `_log_upload_result`.
"""

import io
import uuid
from unittest.mock import patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.config.config import settings
from app.dependencies import get_current_user
from app.routers import upload as upload_router_module


_VALID_MP4_HEADER = bytes([0, 0, 0, 0x18]) + b"ftyp" + b"isom"
_FAKE_VIDEO_BYTES = _VALID_MP4_HEADER + b"\x00" * 32

_TEST_USER_ID = 42

_SAFE_REASON_CODES = {
    "maintenance_mode",
    "insufficient_disk_space",
    "missing_filename",
    "invalid_extension",
    "file_too_large",
    "invalid_mime_type",
    "rate_limited",
    "file_write_failed",
    "invalid_video_metadata",
    "video_too_long",
    "cache_write_failed",
    "internal_error",
}

# Never allowed to appear anywhere in a structured log call, regardless of
# stage — guards against email/JWT/cookie/credential leakage into logs.
_FORBIDDEN_SUBSTRINGS = (
    "authorization", "bearer ", "jwt", "@", "password", "cookie",
)


def _fake_upload_file(filename="clip.mp4", content=_FAKE_VIDEO_BYTES):
    return {"file": (filename, io.BytesIO(content), "video/mp4")}


def _metadata(duration_seconds: float = 10) -> dict:
    return {
        "filename": "clip.mp4",
        "duration_seconds": duration_seconds,
        "resolution": "1920x1080",
        "fps": 30.0,
        "codec": "h264",
        "file_size_mb": 1.0,
    }


def _assert_structured_log(
    mock_log,
    response,
    *,
    stage,
    status_code,
    outcome,
    reason_code=None,
):
    mock_log.assert_called_once()
    kwargs = mock_log.call_args.kwargs

    assert kwargs["user_id"] == _TEST_USER_ID
    assert kwargs["request_id"] == response.headers["x-request-id"]
    assert kwargs["stage"] == stage
    assert kwargs["status_code"] == status_code
    assert kwargs["outcome"] == outcome

    if reason_code is not None:
        assert kwargs["reason_code"] == reason_code
        assert kwargs["reason_code"] in _SAFE_REASON_CODES
    else:
        assert kwargs.get("reason_code") is None

    call_text = " ".join(
        str(value)
        for value in (mock_log.call_args.args + tuple(kwargs.values()))
        if value
    ).lower()

    for forbidden in _FORBIDDEN_SUBSTRINGS:
        assert forbidden not in call_text


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_FOLDER", str(tmp_path))
    monkeypatch.setattr(
        upload_router_module.RateLimitService,
        "is_rate_limited",
        lambda *args, **kwargs: False,
    )
    monkeypatch.setattr(
        upload_router_module,
        "get_video_metadata",
        lambda *_args, **_kwargs: _metadata(),
    )
    monkeypatch.setattr(
        upload_router_module.MaintenanceService,
        "is_maintenance_mode",
        lambda: False,
    )
    monkeypatch.setattr(
        upload_router_module.DiskSpaceService,
        "has_sufficient_space",
        lambda: True,
    )
    monkeypatch.setattr(
        upload_router_module.AnalyticsService,
        "capture_upload_started",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        upload_router_module.AnalyticsService,
        "capture_upload_completed",
        lambda **kwargs: None,
    )

    app = FastAPI()

    # Mirrors main.py's request_id_middleware exactly, so these tests
    # exercise the same request_id plumbing production requests go through.
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    app.include_router(upload_router_module.router)
    app.dependency_overrides[get_current_user] = lambda: {
        "id": _TEST_USER_ID,
        "credits_remaining": 5,
    }

    with TestClient(app) as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# Success
# ---------------------------------------------------------------------------

def test_successful_upload_logs_success_stage(client):
    with patch.object(upload_router_module, "_log_upload_result") as mock_log:
        response = client.post("/upload/", files=_fake_upload_file())

    assert response.status_code == 200
    assert response.json()["success"] is True

    _assert_structured_log(
        mock_log, response,
        stage="success", status_code=200, outcome="success",
    )


# ---------------------------------------------------------------------------
# Invalid extension
# ---------------------------------------------------------------------------

def test_invalid_extension_logs_stage(client):
    with patch.object(upload_router_module, "_log_upload_result") as mock_log:
        response = client.post(
            "/upload/", files=_fake_upload_file(filename="notes.txt")
        )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_EXTENSION"

    _assert_structured_log(
        mock_log, response,
        stage="invalid_extension", status_code=400, outcome="failure",
        reason_code="invalid_extension",
    )


# ---------------------------------------------------------------------------
# Oversized file
# ---------------------------------------------------------------------------

def test_oversized_file_logs_stage(client, monkeypatch):
    monkeypatch.setattr(upload_router_module, "MAX_FILE_SIZE_BYTES", 10)

    with patch.object(upload_router_module, "_log_upload_result") as mock_log:
        response = client.post("/upload/", files=_fake_upload_file())

    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "UPLOAD_TOO_LARGE"

    _assert_structured_log(
        mock_log, response,
        stage="file_size", status_code=413, outcome="failure",
        reason_code="file_too_large",
    )


# ---------------------------------------------------------------------------
# Invalid MIME / magic bytes
# ---------------------------------------------------------------------------

def test_invalid_mime_logs_stage(client):
    with patch.object(upload_router_module, "_log_upload_result") as mock_log:
        response = client.post(
            "/upload/",
            files=_fake_upload_file(content=b"not a real video header at all!!"),
        )

    assert response.status_code == 415
    assert response.json()["detail"]["code"] == "INVALID_MIME_TYPE"

    _assert_structured_log(
        mock_log, response,
        stage="mime_validation", status_code=415, outcome="failure",
        reason_code="invalid_mime_type",
    )


# ---------------------------------------------------------------------------
# Video too long
# ---------------------------------------------------------------------------

def test_video_too_long_logs_stage(client, monkeypatch):
    monkeypatch.setattr(settings, "MAX_VIDEO_DURATION_MINUTES", 10)
    over_limit_seconds = (settings.MAX_VIDEO_DURATION_MINUTES + 1) * 60

    monkeypatch.setattr(
        upload_router_module,
        "get_video_metadata",
        lambda *_a, **_k: _metadata(duration_seconds=over_limit_seconds),
    )

    with patch.object(upload_router_module, "_log_upload_result") as mock_log:
        response = client.post("/upload/", files=_fake_upload_file())

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "VIDEO_TOO_LONG"

    _assert_structured_log(
        mock_log, response,
        stage="video_duration", status_code=400, outcome="failure",
        reason_code="video_too_long",
    )


# ---------------------------------------------------------------------------
# Metadata inspection failure
# ---------------------------------------------------------------------------

def test_metadata_inspection_failure_logs_stage(client):
    internal_detail = "ffprobe exited with garbage at /secret/internal/path.mp4"

    with patch.object(
        upload_router_module,
        "get_video_metadata",
        side_effect=Exception(internal_detail),
    ), patch.object(upload_router_module, "_log_upload_result") as mock_log:
        response = client.post("/upload/", files=_fake_upload_file())

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_VIDEO_METADATA"

    # Internal exception detail (paths, ffprobe output) must never reach
    # the HTTP response, only the server-side log.
    assert "secret" not in str(response.json()).lower()

    _assert_structured_log(
        mock_log, response,
        stage="metadata_inspection", status_code=400, outcome="failure",
        reason_code="invalid_video_metadata",
    )


# ---------------------------------------------------------------------------
# File write failure
# ---------------------------------------------------------------------------

def test_file_write_failure_logs_stage(client):
    with patch.object(
        upload_router_module.shutil,
        "copyfileobj",
        side_effect=OSError("disk full"),
    ), patch.object(upload_router_module, "_log_upload_result") as mock_log:
        response = client.post("/upload/", files=_fake_upload_file())

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "INTERNAL_ERROR"

    _assert_structured_log(
        mock_log, response,
        stage="file_write", status_code=500, outcome="failure",
        reason_code="file_write_failed",
    )


# ---------------------------------------------------------------------------
# Unexpected exception (not one of the explicitly handled stages)
# ---------------------------------------------------------------------------

def test_unexpected_exception_logs_stage(client):
    # Metadata missing "duration_seconds" triggers a raw, unhandled
    # KeyError past the metadata_inspection try/except — exactly the class
    # of bug the catch-all is meant to make visible instead of a silent,
    # untracked 500.
    with patch.object(
        upload_router_module,
        "get_video_metadata",
        lambda *_a, **_k: {"filename": "clip.mp4"},
    ), patch.object(upload_router_module, "_log_upload_result") as mock_log:
        response = client.post("/upload/", files=_fake_upload_file())

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "INTERNAL_ERROR"

    _assert_structured_log(
        mock_log, response,
        stage="unexpected_error", status_code=500, outcome="failure",
        reason_code="internal_error",
    )


# ---------------------------------------------------------------------------
# Rate limit
# ---------------------------------------------------------------------------

def test_rate_limited_logs_stage(client):
    with patch.object(
        upload_router_module.RateLimitService,
        "is_rate_limited",
        lambda *args, **kwargs: True,
    ), patch.object(upload_router_module, "_log_upload_result") as mock_log:
        response = client.post("/upload/", files=_fake_upload_file())

    assert response.status_code == 429
    assert response.json()["detail"]["code"] == "RATE_LIMITED"

    _assert_structured_log(
        mock_log, response,
        stage="rate_limit", status_code=429, outcome="failure",
        reason_code="rate_limited",
    )


# ---------------------------------------------------------------------------
# Maintenance mode
# ---------------------------------------------------------------------------

def test_maintenance_mode_logs_stage(client):
    with patch.object(
        upload_router_module.MaintenanceService,
        "is_maintenance_mode",
        lambda: True,
    ), patch.object(upload_router_module, "_log_upload_result") as mock_log:
        response = client.post("/upload/", files=_fake_upload_file())

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "MAINTENANCE_MODE"

    _assert_structured_log(
        mock_log, response,
        stage="maintenance_mode", status_code=503, outcome="failure",
        reason_code="maintenance_mode",
    )


# ---------------------------------------------------------------------------
# Response header
# ---------------------------------------------------------------------------

def test_request_id_returned_on_every_response(client):
    with patch.object(upload_router_module, "_log_upload_result"):
        success_response = client.post("/upload/", files=_fake_upload_file())

        with patch.object(
            upload_router_module.MaintenanceService,
            "is_maintenance_mode",
            lambda: True,
        ):
            failure_response = client.post("/upload/", files=_fake_upload_file())

    assert "x-request-id" in success_response.headers
    assert "x-request-id" in failure_response.headers
    assert success_response.headers["x-request-id"] != (
        failure_response.headers["x-request-id"]
    )
