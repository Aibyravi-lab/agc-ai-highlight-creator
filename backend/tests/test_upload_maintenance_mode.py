"""AGC-084: maintenance mode enforcement on POST /upload/.

The maintenance check must be the first thing the endpoint does — a
maintenance-ON request must never touch disk space checks, rate-limit
budget, or the filesystem, and normal upload behavior must be completely
unaffected when maintenance is OFF.
"""

import io
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config.config import settings
from app.dependencies import get_current_user
from app.routers import upload as upload_router_module

_VALID_MP4_HEADER = bytes([0, 0, 0, 0x18]) + b"ftyp" + b"isom"
_FAKE_VIDEO_BYTES = _VALID_MP4_HEADER + b"\x00" * 32


def _fake_upload_file(filename="clip.mp4", content=_FAKE_VIDEO_BYTES):
    return {"file": (filename, io.BytesIO(content), "video/mp4")}


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
        lambda *_args, **_kwargs: {
            "filename": "clip.mp4",
            "duration_seconds": 10,
            "resolution": "1920x1080",
            "fps": 30.0,
            "codec": "h264",
            "file_size_mb": 1.0,
        },
    )

    app = FastAPI()
    app.include_router(upload_router_module.router)
    app.dependency_overrides[get_current_user] = lambda: {
        "id": 1,
        "credits_remaining": 5,
    }

    with TestClient(app) as test_client:
        yield test_client


def test_upload_blocked_with_503_when_maintenance_on(client, tmp_path):
    with patch.object(
        upload_router_module.MaintenanceService,
        "is_maintenance_mode",
        return_value=True,
    ):
        response = client.post("/upload/", files=_fake_upload_file())

    assert response.status_code == 503
    body = response.json()
    assert body["detail"]["code"] == "MAINTENANCE_MODE"
    assert body["detail"]["message"] == upload_router_module.MaintenanceService.MESSAGE
    assert response.headers.get("retry-after") == "300"

    # Nothing was written to disk — the check short-circuits before any
    # disk-space check, filename handling, or file save.
    assert list(tmp_path.iterdir()) == []


def test_upload_succeeds_normally_when_maintenance_off(client, tmp_path):
    with patch.object(
        upload_router_module.MaintenanceService,
        "is_maintenance_mode",
        return_value=False,
    ):
        response = client.post("/upload/", files=_fake_upload_file())

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert len(list(tmp_path.iterdir())) == 1
