"""AGC-067.1: maximum source video duration validation at upload time.

Prevents legitimate, low-bitrate, long-duration uploads from later
hanging the AGC-067 FFMPEG_LONG_TIMEOUT_SECONDS during frame/audio
extraction, by rejecting oversized-duration videos before the pipeline
ever starts.

Duration is read via the existing get_video_metadata() (ffprobe) path,
already timeout-protected by AGC-067 — no direct FFmpeg call is added
here, and no AGC-067 timeout values are touched.
"""

import io
from unittest.mock import patch, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config.config import settings
from app.dependencies import get_current_user
from app.routers import upload as upload_router_module


# A minimal valid MP4 header: ISO base media box with an "ftyp" atom.
# Satisfies MimeValidationService.detect() -> "video/mp4" without
# needing a real, ffprobe-parseable video file.
_VALID_MP4_HEADER = bytes([0, 0, 0, 0x18]) + b"ftyp" + b"isom"
_FAKE_VIDEO_BYTES = _VALID_MP4_HEADER + b"\x00" * 32


def _fake_upload_file(filename="clip.mp4", content=_FAKE_VIDEO_BYTES):
    return {"file": (filename, io.BytesIO(content), "video/mp4")}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_FOLDER", str(tmp_path))
    monkeypatch.setattr(settings, "MAX_VIDEO_DURATION_MINUTES", 10)
    monkeypatch.setattr(upload_router_module, "MAX_FILE_SIZE_BYTES", 10 * 1024 * 1024)
    # AGC-069: this fixture builds a standalone app that never calls
    # DatabaseService.initialize(), so the real rate limiter isn't
    # exercised here (that's covered by test_rate_limiting.py).
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


def _metadata(duration_seconds: float) -> dict:
    return {
        "filename": "clip.mp4",
        "duration_seconds": duration_seconds,
        "resolution": "1920x1080",
        "fps": 30.0,
        "codec": "h264",
        "file_size_mb": 1.0,
    }


# ---------------------------------------------------------------------------
# Duration within limit
# ---------------------------------------------------------------------------

def test_upload_within_duration_limit_succeeds(client, tmp_path):
    with patch.object(
        upload_router_module, "get_video_metadata", return_value=_metadata(300)
    ):
        response = client.post("/upload/", files=_fake_upload_file())

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True

    saved_files = list(tmp_path.iterdir())
    assert len(saved_files) == 1


# ---------------------------------------------------------------------------
# Duration exceeding limit
# ---------------------------------------------------------------------------

def test_upload_exceeding_duration_limit_returns_400(client, tmp_path):
    over_limit_seconds = (settings.MAX_VIDEO_DURATION_MINUTES + 1) * 60

    with patch.object(
        upload_router_module,
        "get_video_metadata",
        return_value=_metadata(over_limit_seconds),
    ):
        response = client.post("/upload/", files=_fake_upload_file())

    assert response.status_code == 400
    body = response.json()
    assert body["detail"]["code"] == "VIDEO_TOO_LONG"
    assert body["detail"]["message"] == (
        "Video exceeds the maximum allowed duration."
    )

    # No ffprobe internals or filesystem paths leaked to the client.
    assert "ffprobe" not in str(body).lower()
    assert str(tmp_path) not in str(body)

    # The rejected upload must not be left behind on disk.
    assert list(tmp_path.iterdir()) == []


# ---------------------------------------------------------------------------
# Boundary: exactly at the limit is accepted
# ---------------------------------------------------------------------------

def test_upload_at_exact_duration_limit_is_accepted(client, tmp_path):
    exact_limit_seconds = settings.MAX_VIDEO_DURATION_MINUTES * 60

    with patch.object(
        upload_router_module,
        "get_video_metadata",
        return_value=_metadata(exact_limit_seconds),
    ):
        response = client.post("/upload/", files=_fake_upload_file())

    assert response.status_code == 200
    assert response.json()["success"] is True


# ---------------------------------------------------------------------------
# ffprobe / metadata failure handled gracefully
# ---------------------------------------------------------------------------

def test_upload_ffprobe_failure_returns_400_without_leaking_internals(
    client, tmp_path
):
    internal_detail = (
        f"ffprobe exited with garbage at {tmp_path}/secret_internal_path.mp4"
    )

    with patch.object(
        upload_router_module,
        "get_video_metadata",
        side_effect=Exception(internal_detail),
    ):
        response = client.post("/upload/", files=_fake_upload_file())

    assert response.status_code == 400
    body = response.json()
    assert body["detail"]["code"] == "INVALID_VIDEO_METADATA"
    assert body["detail"]["message"] == (
        "Unable to process the uploaded video file."
    )

    # The raw exception text (which could contain paths/ffprobe output)
    # must never reach the client.
    assert internal_detail not in str(body)
    assert "secret_internal_path" not in str(body)

    assert list(tmp_path.iterdir()) == []


# ---------------------------------------------------------------------------
# Existing upload validation is unaffected
# ---------------------------------------------------------------------------

def test_invalid_extension_still_rejected_before_duration_check(client):
    mock_metadata = MagicMock()

    with patch.object(upload_router_module, "get_video_metadata", mock_metadata):
        response = client.post(
            "/upload/",
            files=_fake_upload_file(filename="notes.txt"),
        )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_EXTENSION"
    mock_metadata.assert_not_called()


def test_oversized_file_still_rejected_before_duration_check(client, monkeypatch):
    monkeypatch.setattr(upload_router_module, "MAX_FILE_SIZE_BYTES", 10)
    mock_metadata = MagicMock()

    with patch.object(upload_router_module, "get_video_metadata", mock_metadata):
        response = client.post("/upload/", files=_fake_upload_file())

    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "UPLOAD_TOO_LARGE"
    mock_metadata.assert_not_called()


def test_invalid_mime_type_still_rejected_before_duration_check(client):
    mock_metadata = MagicMock()

    with patch.object(upload_router_module, "get_video_metadata", mock_metadata):
        response = client.post(
            "/upload/",
            files=_fake_upload_file(content=b"not a real video header at all!!"),
        )

    assert response.status_code == 415
    assert response.json()["detail"]["code"] == "INVALID_MIME_TYPE"
    mock_metadata.assert_not_called()


# ---------------------------------------------------------------------------
# Config default
# ---------------------------------------------------------------------------

def test_max_video_duration_minutes_default_is_thirty():
    import os

    if "MAX_VIDEO_DURATION_MINUTES" in os.environ:
        pytest.skip("MAX_VIDEO_DURATION_MINUTES overridden in environment")

    assert settings.MAX_VIDEO_DURATION_MINUTES == 30
