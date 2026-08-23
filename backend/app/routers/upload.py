import os
import re
import shutil
import unicodedata
import uuid
from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    Depends,
    Request
)

from app.config.config import settings
from app.dependencies import get_current_user
from app.services.analytics_service import AnalyticsService
from app.services.disk_space_service import DiskSpaceService
from app.services.file_safety_service import FileSafetyService
from app.services.logger_service import LoggerService
from app.services.maintenance_service import MaintenanceService
from app.services.mime_validation_service import MimeValidationService
from app.services.rate_limit_service import RateLimitService
from app.services.upload_cache_service import UploadCacheService
from app.services.video_service import get_video_metadata


router = APIRouter(
    prefix="/upload",
    tags=["Video Upload"]
)


MAX_FILE_SIZE_BYTES = (
    settings.MAX_UPLOAD_SIZE_MB
    * 1024
    * 1024
)

ALLOWED_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".mkv",
    ".avi",
    ".webm",
}

# Reserved Windows filenames that must not be used on disk
_RESERVED_NAMES: frozenset = frozenset({
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5",
    "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5",
    "LPT6", "LPT7", "LPT8", "LPT9",
})

_UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


class UploadError:
    INVALID_FILENAME = "INVALID_FILENAME"
    INVALID_EXTENSION = "INVALID_EXTENSION"
    INVALID_MIME_TYPE = "INVALID_MIME_TYPE"
    UPLOAD_TOO_LARGE = "UPLOAD_TOO_LARGE"
    DUPLICATE_UPLOAD = "DUPLICATE_UPLOAD"
    VIDEO_TOO_LONG = "VIDEO_TOO_LONG"
    INVALID_VIDEO_METADATA = "INVALID_VIDEO_METADATA"
    RATE_LIMITED = "RATE_LIMITED"
    INSUFFICIENT_DISK_SPACE = "INSUFFICIENT_DISK_SPACE"
    MAINTENANCE_MODE = "MAINTENANCE_MODE"


def _sanitize_stem(raw_stem: str) -> str:

    # Normalize unicode to closest ASCII equivalent
    stem = unicodedata.normalize("NFKD", raw_stem)
    stem = stem.encode("ascii", "ignore").decode("ascii")

    # Replace unsafe filesystem chars and whitespace
    stem = _UNSAFE_CHARS.sub("_", stem)
    stem = stem.replace(" ", "_")

    # Strip leading/trailing dots, underscores, and spaces
    stem = stem.strip("._")

    # Reject Windows reserved names
    if stem.upper() in _RESERVED_NAMES:
        stem = f"upload_{stem}"

    return stem or "upload"


# VED-GROWTH-005: single canonical "upload_result" structured log emitted at
# every /upload exit path (success or failure), so production access logs
# (which only show "POST /upload -> 400/200") can be joined back to a
# user_id + request_id + failure_stage + safe reason_code. `detail` is
# free-text, server-log-only context (e.g. a sanitized exception message) —
# never derived from raw request bodies/headers, so it can't carry secrets.
def _log_upload_result(
    *,
    request_id: Optional[str],
    user_id: Optional[int],
    stage: str,
    status_code: int,
    outcome: str,
    reason_code: Optional[str] = None,
    detail: Optional[str] = None,
) -> None:

    message = f"upload_result stage={stage} status={status_code}"

    if detail:
        message = f"{message} detail={detail}"

    log_fn = LoggerService.info if outcome == "success" else LoggerService.error

    log_fn(
        message,
        request_id=request_id,
        user_id=user_id,
        event="upload_result",
        stage=stage,
        status_code=status_code,
        outcome=outcome,
        reason_code=reason_code,
    )


@router.post("/")
async def upload_video(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):

    request_id = getattr(request.state, "request_id", None)
    user_id = current_user["id"]

    try:

        # ── Maintenance check ─────────────────────────────────────
        # AGC-084: checked first, ahead of every other validation, so a
        # maintenance window rejects new uploads without touching disk,
        # rate-limit budget, or the filesystem.
        if MaintenanceService.is_maintenance_mode():

            _log_upload_result(
                request_id=request_id,
                user_id=user_id,
                stage="maintenance_mode",
                status_code=503,
                outcome="failure",
                reason_code="maintenance_mode",
            )

            raise HTTPException(
                status_code=503,
                detail={
                    "code": UploadError.MAINTENANCE_MODE,
                    "message": MaintenanceService.MESSAGE
                },
                headers={
                    "Retry-After": str(MaintenanceService.RETRY_AFTER_SECONDS)
                }
            )

        # ── 0. Disk space check ───────────────────────────────────
        if not DiskSpaceService.has_sufficient_space():

            _log_upload_result(
                request_id=request_id,
                user_id=user_id,
                stage="disk_space",
                status_code=507,
                outcome="failure",
                reason_code="insufficient_disk_space",
            )

            raise HTTPException(
                status_code=507,
                detail={
                    "code": UploadError.INSUFFICIENT_DISK_SPACE,
                    "message": (
                        "Server storage is nearly full. "
                        "Please try again later."
                    )
                }
            )

        # ── 1. Filename presence ──────────────────────────────────
        if not file.filename:

            _log_upload_result(
                request_id=request_id,
                user_id=user_id,
                stage="missing_filename",
                status_code=400,
                outcome="failure",
                reason_code="missing_filename",
            )

            raise HTTPException(
                status_code=400,
                detail={
                    "code": UploadError.INVALID_FILENAME,
                    "message": "Filename is missing."
                }
            )

        # Strip any path component — prevent traversal before anything else
        bare_name = Path(file.filename).name

        if not bare_name:

            _log_upload_result(
                request_id=request_id,
                user_id=user_id,
                stage="missing_filename",
                status_code=400,
                outcome="failure",
                reason_code="missing_filename",
            )

            raise HTTPException(
                status_code=400,
                detail={
                    "code": UploadError.INVALID_FILENAME,
                    "message": "Filename is invalid."
                }
            )

        # ── 2. Extension validation ───────────────────────────────
        extension = Path(bare_name).suffix.lower()

        if extension not in ALLOWED_EXTENSIONS:

            _log_upload_result(
                request_id=request_id,
                user_id=user_id,
                stage="invalid_extension",
                status_code=400,
                outcome="failure",
                reason_code="invalid_extension",
            )

            raise HTTPException(
                status_code=400,
                detail={
                    "code": UploadError.INVALID_EXTENSION,
                    "message": (
                        "Only MP4, MOV, MKV, AVI, and WebM "
                        "files are allowed."
                    )
                }
            )

        # ── 3. File size validation ───────────────────────────────
        file.file.seek(0, os.SEEK_END)
        file_size = file.file.tell()
        file.file.seek(0)

        if file_size > MAX_FILE_SIZE_BYTES:

            _log_upload_result(
                request_id=request_id,
                user_id=user_id,
                stage="file_size",
                status_code=413,
                outcome="failure",
                reason_code="file_too_large",
            )

            raise HTTPException(
                status_code=413,
                detail={
                    "code": UploadError.UPLOAD_TOO_LARGE,
                    "message": (
                        f"File exceeds the maximum upload "
                        f"size of {settings.MAX_UPLOAD_SIZE_MB} MB."
                    )
                }
            )

        # ── 4. MIME type validation (magic bytes) ─────────────────
        header = file.file.read(MimeValidationService.HEADER_SIZE)
        file.file.seek(0)

        allowed, detected_mime = MimeValidationService.is_allowed(header)

        if not allowed:

            _log_upload_result(
                request_id=request_id,
                user_id=user_id,
                stage="mime_validation",
                status_code=415,
                outcome="failure",
                reason_code="invalid_mime_type",
            )

            raise HTTPException(
                status_code=415,
                detail={
                    "code": UploadError.INVALID_MIME_TYPE,
                    "message": (
                        f"File type not supported. "
                        f"Detected: {detected_mime or 'unknown'}. "
                        f"Allowed: video/mp4, video/quicktime, "
                        f"video/x-msvideo, video/webm, video/x-matroska."
                    )
                }
            )

        # ── 5. Duplicate upload check ─────────────────────────────
        # AGC-049: reuse disabled. Returning a cached upload_info let
        # two jobs share one physical file, and CleanupService deletes
        # a job's file unconditionally when that job finishes — so the
        # first job to finish could delete the file still in use by the
        # second. Every upload must always write its own new file.

        # ── 5b. Rate limit ────────────────────────────────────────
        if RateLimitService.is_rate_limited(
            key=f"user:{user_id}",
            endpoint="upload",
            max_attempts=settings.UPLOAD_RATE_LIMIT_MAX_PER_HOUR,
            window_seconds=3600
        ):

            _log_upload_result(
                request_id=request_id,
                user_id=user_id,
                stage="rate_limit",
                status_code=429,
                outcome="failure",
                reason_code="rate_limited",
            )

            raise HTTPException(
                status_code=429,
                detail={
                    "code": UploadError.RATE_LIMITED,
                    "message": "Too many requests. Please try again later."
                }
            )

        # VED-ANALYTICS-005: authoritative "Upload Started" — every prior gate
        # (maintenance, disk space, filename, extension, size, MIME, rate
        # limit) has passed, so the backend is now committing to this upload.
        # Wrapped so a PostHog failure can never fail the upload itself.
        try:

            AnalyticsService.capture_upload_started(
                user_id=user_id
            )

        except Exception as analytics_error:

            LoggerService.error(
                "event=analytics_dispatch_failed "
                f"analytics_event=upload_started error={analytics_error}",
                user_id=user_id
            )

        # ── 6. Sanitize filename ──────────────────────────────────
        raw_stem = Path(bare_name).stem
        safe_stem = _sanitize_stem(raw_stem)

        # VED-SEC-001: the leading "{user_id}_" segment is the durable
        # ownership marker VideoPathService.validate_upload_path checks
        # before a /pipeline/start request may process this file — it is
        # always derived from the authenticated uploader's own ID, never
        # from client input, so it cannot be forged by another user. Stays
        # a flat filename (no per-user subdirectory) so CleanupService's
        # existing flat-iteration cleanup of UPLOAD_FOLDER needs no changes.
        unique_filename = (
            f"{user_id}_"
            f"{uuid.uuid4().hex[:8]}"
            f"_{safe_stem}"
            f"{extension}"
        )

        # ── 7. Save file ──────────────────────────────────────────
        upload_dir = settings.UPLOAD_FOLDER
        os.makedirs(upload_dir, exist_ok=True)

        file_path = os.path.join(upload_dir, unique_filename)

        try:

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

        except Exception as error:

            _log_upload_result(
                request_id=request_id,
                user_id=user_id,
                stage="file_write",
                status_code=500,
                outcome="failure",
                reason_code="file_write_failed",
                detail=str(error),
            )

            raise HTTPException(
                status_code=500,
                detail={
                    "code": "INTERNAL_ERROR",
                    "message": "Unexpected server error."
                }
            )

        # ── 8. Video duration validation ──────────────────────────
        # Reuses the ffprobe path already hardened by AGC-067
        # (FFMPEG_QUICK_TIMEOUT_SECONDS) — no direct FFmpeg call here.
        try:

            metadata = get_video_metadata(file_path)

        except Exception as error:

            FileSafetyService.safe_delete_file(file_path)

            _log_upload_result(
                request_id=request_id,
                user_id=user_id,
                stage="metadata_inspection",
                status_code=400,
                outcome="failure",
                reason_code="invalid_video_metadata",
                detail=str(error),
            )

            raise HTTPException(
                status_code=400,
                detail={
                    "code": UploadError.INVALID_VIDEO_METADATA,
                    "message": "Unable to process the uploaded video file."
                }
            )

        max_duration_seconds = (
            settings.MAX_VIDEO_DURATION_MINUTES
            * 60
        )

        if metadata["duration_seconds"] > max_duration_seconds:

            FileSafetyService.safe_delete_file(file_path)

            _log_upload_result(
                request_id=request_id,
                user_id=user_id,
                stage="video_duration",
                status_code=400,
                outcome="failure",
                reason_code="video_too_long",
            )

            raise HTTPException(
                status_code=400,
                detail={
                    "code": UploadError.VIDEO_TOO_LONG,
                    "message": (
                        "Video exceeds the maximum allowed duration."
                    )
                }
            )

        # ── 9. Cache and return ───────────────────────────────────
        upload_info = {

            "success": True,

            "message":
            "Video uploaded successfully 🎮",

            "filename":
            unique_filename,

            "original_filename":
            file.filename,

            "size_mb":
            round(file_size / 1024 / 1024, 2),

            "location":
            file_path,

            "mime_type":
            detected_mime,

        }

        try:

            UploadCacheService.store(
                user_id=user_id,
                filename=bare_name,
                size=file_size,
                upload_info=upload_info
            )

        except Exception as error:

            _log_upload_result(
                request_id=request_id,
                user_id=user_id,
                stage="upload_cache",
                status_code=500,
                outcome="failure",
                reason_code="cache_write_failed",
                detail=str(error),
            )

            raise HTTPException(
                status_code=500,
                detail={
                    "code": "INTERNAL_ERROR",
                    "message": "Unexpected server error."
                }
            )

        # VED-ANALYTICS-005: authoritative "Upload Completed" — file is
        # written to disk, duration-validated, and cached. Fires only on this
        # success path; any exception above (save failure, invalid metadata,
        # video too long) returns before reaching here, so it is never
        # double-counted against a failed upload.
        try:

            AnalyticsService.capture_upload_completed(
                user_id=user_id
            )

        except Exception as analytics_error:

            LoggerService.error(
                "event=analytics_dispatch_failed "
                f"analytics_event=upload_completed error={analytics_error}",
                user_id=user_id
            )

        _log_upload_result(
            request_id=request_id,
            user_id=user_id,
            stage="success",
            status_code=200,
            outcome="success",
        )

        return upload_info

    except HTTPException:

        raise

    except Exception as error:

        _log_upload_result(
            request_id=request_id,
            user_id=user_id,
            stage="unexpected_error",
            status_code=500,
            outcome="failure",
            reason_code="internal_error",
            detail=str(error),
        )

        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": "Unexpected server error."
            }
        )
