"""VED-SEC-001: uploaded video ownership must be enforced before
/pipeline/start is allowed to process a video_path.

Prior to this fix, VideoPathService.validate_upload_path only checked that
video_path resolved inside UPLOAD_FOLDER and existed on disk -- it never
checked that the authenticated caller was the user who uploaded it. Any
authenticated user who learned another user's video_path (e.g. via a
leaked/shared "location" value) could submit it to /pipeline/start under
their own account and have the victim's private video processed for them.

The fix: /upload/ now names every saved file "{uploader_user_id}_...", a
marker written only by the server from the authenticated uploader's own
id -- never from client input -- and VideoPathService.validate_upload_path
now requires that marker to match the calling user's id before the
existing traversal-hardened path is accepted.
"""

import io
from unittest.mock import patch, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config.config import settings
from app.dependencies import get_current_user
from app.routers import pipeline as pipeline_router
from app.routers import upload as upload_router_module
from app.services.video_path_service import VideoPathError, VideoPathService


_VALID_MP4_HEADER = bytes([0, 0, 0, 0x18]) + b"ftyp" + b"isom"
_FAKE_VIDEO_BYTES = _VALID_MP4_HEADER + b"\x00" * 32


def _fake_upload_file(filename="clip.mp4"):
    return {"file": (filename, io.BytesIO(_FAKE_VIDEO_BYTES), "video/mp4")}


@pytest.fixture
def current_user_holder():
    return {"user": {"id": 1, "credits_remaining": 5}}


@pytest.fixture
def client(tmp_path, monkeypatch, current_user_holder):
    monkeypatch.setattr(settings, "UPLOAD_FOLDER", str(tmp_path))
    monkeypatch.setattr(
        upload_router_module, "MAX_FILE_SIZE_BYTES", 10 * 1024 * 1024
    )
    monkeypatch.setattr(
        upload_router_module.RateLimitService,
        "is_rate_limited",
        lambda *args, **kwargs: False,
    )
    monkeypatch.setattr(
        upload_router_module,
        "get_video_metadata",
        lambda path: {
            "filename": "clip.mp4",
            "duration_seconds": 60.0,
            "resolution": "1920x1080",
            "fps": 30.0,
            "codec": "h264",
            "file_size_mb": 1.0,
        },
    )

    app = FastAPI()
    app.include_router(upload_router_module.router)
    app.dependency_overrides[get_current_user] = (
        lambda: current_user_holder["user"]
    )

    with TestClient(app) as test_client:
        yield test_client


def _upload_as(client, current_user_holder, user_id, filename="clip.mp4"):
    current_user_holder["user"] = {"id": user_id, "credits_remaining": 5}
    response = client.post("/upload/", files=_fake_upload_file(filename))
    assert response.status_code == 200
    return response.json()


# ---------------------------------------------------------------------------
# G: upload naming behavior
# ---------------------------------------------------------------------------


def test_uploaded_filename_carries_uploader_id_prefix(
    client, current_user_holder
):
    body = _upload_as(client, current_user_holder, user_id=42)

    assert body["filename"].startswith("42_")
    assert body["location"].endswith(body["filename"])


def test_two_users_uploading_get_distinctly_owned_filenames(
    client, current_user_holder, tmp_path
):
    body_a = _upload_as(client, current_user_holder, user_id=1)
    body_b = _upload_as(client, current_user_holder, user_id=2)

    assert body_a["filename"].startswith("1_")
    assert body_b["filename"].startswith("2_")
    assert body_a["filename"] != body_b["filename"]

    saved = {p.name for p in tmp_path.iterdir()}
    assert body_a["filename"] in saved
    assert body_b["filename"] in saved


# ---------------------------------------------------------------------------
# A/B: ownership enforcement at /pipeline/start
# ---------------------------------------------------------------------------


def _start_pipeline(video_path, current_user):
    with patch.object(
        pipeline_router.MaintenanceService,
        "is_maintenance_mode",
        return_value=False,
    ), patch.object(
        pipeline_router.BackgroundJobService,
        "is_accepting_jobs",
        return_value=True,
    ), patch.object(
        pipeline_router.RateLimitService,
        "is_rate_limited",
        return_value=False,
    ), patch.object(
        pipeline_router.JobService,
        "get_running_job_count",
        return_value=0,
    ), patch.object(
        pipeline_router.SubscriptionService,
        "is_pro_active",
        return_value=False,
    ), patch.object(
        pipeline_router.AuthService, "deduct_credit"
    ) as mock_deduct_credit, patch.object(
        pipeline_router.JobService, "create_job"
    ) as mock_create_job, patch.object(
        pipeline_router.BackgroundJobService, "start_job"
    ) as mock_start_job:

        result = {}
        try:
            result["value"] = pipeline_router.start_video_processing(
                video_path, current_user
            )
        except Exception as exc:  # noqa: BLE001 - captured for assertions
            result["error"] = exc

        return result, mock_deduct_credit, mock_create_job, mock_start_job


def test_owner_can_start_pipeline_on_own_upload(client, current_user_holder):
    body = _upload_as(client, current_user_holder, user_id=1)

    result, mock_deduct_credit, mock_create_job, mock_start_job = (
        _start_pipeline(body["location"], {"id": 1, "credits_remaining": 5})
    )

    assert "value" in result, result.get("error")
    assert result["value"]["success"] is True
    mock_deduct_credit.assert_called_once()
    mock_create_job.assert_called_once()
    mock_start_job.assert_called_once()


def test_other_user_cannot_start_pipeline_on_someone_elses_upload(
    client, current_user_holder
):
    victim_upload = _upload_as(client, current_user_holder, user_id=1)

    attacker = {"id": 2, "credits_remaining": 5}
    result, mock_deduct_credit, mock_create_job, mock_start_job = (
        _start_pipeline(victim_upload["location"], attacker)
    )

    from fastapi import HTTPException

    assert isinstance(result.get("error"), HTTPException)
    assert result["error"].status_code == 400
    assert (
        result["error"].detail["code"]
        == pipeline_router.PipelineError.INVALID_VIDEO_PATH
    )

    # E: rejection happens before credit deduction.
    mock_deduct_credit.assert_not_called()
    # F: rejection creates no job and starts no worker.
    mock_create_job.assert_not_called()
    mock_start_job.assert_not_called()


def test_rejection_matches_generic_invalid_path_response_shape(
    client, current_user_holder
):
    # H: no cross-user leakage -- a real file owned by someone else must
    # be indistinguishable from a path that was never uploaded at all.
    victim_upload = _upload_as(client, current_user_holder, user_id=1)
    attacker = {"id": 2, "credits_remaining": 5}

    owned_by_other, *_ = _start_pipeline(
        victim_upload["location"], attacker
    )
    # Also not the attacker's own file (owned by user 1, like the real
    # victim upload above) and also nonexistent -- must hit the same
    # ownership rejection, not a distinct "not found" message.
    nonexistent, *_ = _start_pipeline(
        victim_upload["location"].replace(
            victim_upload["filename"], "1_never_existed.mp4"
        ),
        attacker,
    )

    assert owned_by_other["error"].detail == nonexistent["error"].detail
    assert owned_by_other["error"].status_code == (
        nonexistent["error"].status_code
    )


# ---------------------------------------------------------------------------
# C/D: existing traversal / missing-file protections untouched
# ---------------------------------------------------------------------------


def test_traversal_path_still_rejected(tmp_path):
    with patch.object(settings, "UPLOAD_FOLDER", str(tmp_path)):
        with pytest.raises(VideoPathError):
            VideoPathService.validate_upload_path(
                str(tmp_path / ".." / "etc" / "passwd"), user_id=1
            )


def test_missing_file_still_rejected(tmp_path):
    with patch.object(settings, "UPLOAD_FOLDER", str(tmp_path)):
        with pytest.raises(VideoPathError):
            VideoPathService.validate_upload_path(
                str(tmp_path / "1_does_not_exist.mp4"), user_id=1
            )
