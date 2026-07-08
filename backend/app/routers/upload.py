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
from app.services.logger_service import LoggerService
from app.services.mime_validation_service import MimeValidationService
from app.services.upload_cache_service import UploadCacheService


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

    # ── 8. Cache and return ───────────────────────────────────
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
