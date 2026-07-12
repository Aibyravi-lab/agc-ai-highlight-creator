import os
import re
import shutil
import unicodedata
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    Depends
)

from app.config.config import settings
from app.dependencies import get_current_user
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


@router.post("/")
async def upload_video(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):

    # ── Maintenance check ─────────────────────────────────────
    # AGC-084: checked first, ahead of every other validation, so a
    # maintenance window rejects new uploads without touching disk,
    # rate-limit budget, or the filesystem.
    if MaintenanceService.is_maintenance_mode():

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
    user_id = current_user["id"]

    # ── 5b. Rate limit ────────────────────────────────────────
    if RateLimitService.is_rate_limited(
        key=f"user:{user_id}",
        endpoint="upload",
        max_attempts=settings.UPLOAD_RATE_LIMIT_MAX_PER_HOUR,
        window_seconds=3600
    ):

        raise HTTPException(
            status_code=429,
            detail={
                "code": UploadError.RATE_LIMITED,
                "message": "Too many requests. Please try again later."
            }
        )

    # ── 6. Sanitize filename ──────────────────────────────────
    raw_stem = Path(bare_name).stem
    safe_stem = _sanitize_stem(raw_stem)

    unique_filename = (
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

        LoggerService.error(
            f"Upload failed for user {user_id}: {error}"
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

        LoggerService.error(
            f"Video metadata inspection failed for user "
            f"{user_id}: {error}"
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

    UploadCacheService.store(
        user_id=user_id,
        filename=bare_name,
        size=file_size,
        upload_info=upload_info
    )

    return upload_info
