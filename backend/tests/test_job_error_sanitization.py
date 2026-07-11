"""AGC-083 Phase 2: user-facing job errors must be sanitized.

Production evidence showed raw FFmpeg build banners and subprocess
stderr persisted verbatim into jobs.error (e.g. "Output file does not
contain any stream", "Error opening output file -"). That detail must
never reach the client, even though it's useful internally.
"""

from app.routers.pipeline import _sanitize_job


RAW_FFMPEG_ERROR = (
    "Audio extraction failed: ffmpeg version 6.0 Copyright (c) 2000-2023 "
    "the FFmpeg developers\nOutput file does not contain any stream\n"
    "Error opening output file -.\nInvalid argument\n"
    "  at /var/app/backend/app/services/whisper_service.py line 81"
)


def test_sanitize_job_strips_raw_error_for_failed_job():
    job = {
        "job_id": "4532e073-99a6-4af8-8273-7d42fba88ea1",
        "status": "failed",
        "message": "Failed",
        "error": RAW_FFMPEG_ERROR,
    }

    sanitized = _sanitize_job(job)

    assert sanitized["error"] == {
        "code": "INTERNAL_ERROR",
        "message": "Unexpected server error.",
    }
    assert "ffmpeg" not in str(sanitized["error"]).lower()
    assert "whisper_service.py" not in str(sanitized["error"])


def test_sanitize_job_leaves_non_failed_jobs_untouched():
    job = {
        "job_id": "abc",
        "status": "completed",
        "message": "Completed",
        "error": None,
    }

    sanitized = _sanitize_job(job)

    assert sanitized == job


def test_sanitize_job_leaves_processing_jobs_untouched():
    job = {
        "job_id": "abc",
        "status": "processing",
        "message": "Detecting Highlights",
        "error": None,
    }

    sanitized = _sanitize_job(job)

    assert sanitized == job
