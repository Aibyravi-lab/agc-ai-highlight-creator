from pathlib import Path

from app.config.config import settings


class VideoPathError(ValueError):
    """Raised when a pipeline video_path is not a valid application upload."""


class VideoPathService:
    """Validates video_path values accepted from clients before they are
    ever handed to ffmpeg/ffprobe as an ``-i`` input (AGC-066).

    ffmpeg resolves its input using its own protocol handlers
    (http://, https://, file:, rtmp://, concat:, UNC paths, ...) — this
    is independent of how the OS/pathlib treats the same string. The
    only production-safe fix is an allowlist: a video_path is valid
    only if it resolves to a real file strictly inside the server's own
    upload storage folder. Everything else (remote URLs, localhost,
    private/link-local IPs, cloud metadata endpoints, traversal,
    absolute paths elsewhere on disk) is rejected by construction,
    without needing to enumerate each blocked case.
    """

    @classmethod
    def validate_upload_path(cls, video_path: str) -> str:

        if not video_path or not video_path.strip():
            raise VideoPathError("video_path is required")

        upload_root = Path(settings.UPLOAD_FOLDER).resolve()

        try:
            resolved = Path(video_path).resolve(strict=False)
        except (OSError, RuntimeError, TypeError, ValueError):
            raise VideoPathError("video_path is invalid")

        if resolved == upload_root or upload_root not in resolved.parents:
            raise VideoPathError(
                "video_path must reference an uploaded file"
            )

        if not resolved.is_file():
            raise VideoPathError("Uploaded video file was not found")

        return str(resolved)
