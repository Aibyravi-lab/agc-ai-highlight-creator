import platform
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from app.config.config import settings

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DISK_WARNING_FREE_PERCENT = 15.0
_SUBPROCESS_TIMEOUT_SECONDS = 3


class HealthService:
    """AGC-073: richer, read-only health diagnostics consumed by
    ObservabilityService.check_health(). Every method fails safely —
    never raises, never returns a filesystem path, stack trace, or
    environment value.
    """

    @classmethod
    def check_directory_writable(cls, folder: str) -> str:

        try:
            path = Path(folder)
            path.mkdir(parents=True, exist_ok=True)

            with tempfile.NamedTemporaryFile(dir=path):
                pass

            return "healthy"
        except Exception:
            return "unhealthy"

    @classmethod
    def get_disk_usage(cls) -> dict:

        try:
            usage = shutil.disk_usage(".")
            percent_free = (usage.free / usage.total) * 100

            return {
                "total_gb": round(usage.total / (1024 ** 3), 2),
                "used_gb": round(usage.used / (1024 ** 3), 2),
                "free_gb": round(usage.free / (1024 ** 3), 2),
                "percent_free": round(percent_free, 2),
                "status": (
                    "healthy"
                    if percent_free >= _DISK_WARNING_FREE_PERCENT
                    else "warning"
                ),
            }
        except Exception:
            return {
                "total_gb": None,
                "used_gb": None,
                "free_gb": None,
                "percent_free": None,
                "status": "unhealthy",
            }

    @classmethod
    def get_ffmpeg_info(cls) -> dict:

        ffmpeg_path = shutil.which("ffmpeg")

        if not ffmpeg_path:
            return {"status": "unhealthy", "version": "unknown"}

        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=_SUBPROCESS_TIMEOUT_SECONDS,
            )
            first_line = result.stdout.splitlines()[0] if result.stdout else ""
            stripped = first_line.replace("ffmpeg version", "").strip()
            version = stripped.split(" ")[0] if stripped else "unknown"
            return {"status": "healthy", "version": version}
        except Exception:
            return {"status": "healthy", "version": "unknown"}

    @classmethod
    def get_python_version(cls) -> str:

        try:
            return platform.python_version()
        except Exception:
            return "unknown"

    @classmethod
    def get_app_version(cls) -> dict:

        return {
            "git_commit": cls._run_git(["git", "rev-parse", "--short", "HEAD"]),
            "git_tag": cls._run_git(["git", "describe", "--tags"]),
        }

    @classmethod
    def _run_git(cls, command: list) -> str:

        try:
            result = subprocess.run(
                command,
                cwd=_REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=_SUBPROCESS_TIMEOUT_SECONDS,
            )
            output = result.stdout.strip()
            return output if (result.returncode == 0 and output) else "unknown"
        except Exception:
            return "unknown"

    @classmethod
    def _safe(cls, func, fallback):
        """Runs a single check in isolation: a failure here must only
        blank out that one check's own field, never the rest of the
        /health payload.
        """

        try:
            return func()
        except Exception:
            return fallback

    @classmethod
    def get_extended_report(cls) -> dict:
        """Assembles the AGC-073 additive fields merged into the
        existing /health payload by ObservabilityService.check_health().
        Each check is run independently via _safe() so one failing
        check can never abort or blank out the others.
        """

        uploads_status = cls._safe(
            lambda: cls.check_directory_writable(settings.UPLOAD_FOLDER),
            "unhealthy",
        )
        highlights_status = cls._safe(
            lambda: cls.check_directory_writable(settings.HIGHLIGHT_FOLDER),
            "unhealthy",
        )
        disk = cls._safe(
            cls.get_disk_usage,
            {
                "total_gb": None,
                "used_gb": None,
                "free_gb": None,
                "percent_free": None,
                "status": "unhealthy",
            },
        )
        ffmpeg = cls._safe(
            cls.get_ffmpeg_info,
            {"status": "unhealthy", "version": "unknown"},
        )
        build = cls._safe(
            cls.get_app_version,
            {"git_commit": "unknown", "git_tag": "unknown"},
        )
        python_version = cls._safe(cls.get_python_version, "unknown")

        return {
            "build": build,
            "python_version": python_version,
            "ffmpeg_version": ffmpeg.get("version", "unknown"),
            "disk": disk,
            "checks": {
                "uploads": uploads_status,
                "highlights": highlights_status,
                "ffmpeg": ffmpeg.get("status", "unhealthy"),
                "disk": disk.get("status", "unhealthy"),
            },
        }
