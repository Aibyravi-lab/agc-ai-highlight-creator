import hashlib
import os
import platform
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from app.config.config import settings

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DISK_WARNING_FREE_PERCENT = 15.0
_SUBPROCESS_TIMEOUT_SECONDS = 3
_BACKUP_TIMESTAMP_FORMAT = "%Y-%m-%d_%H%M%S"
_CHECKSUM_READ_CHUNK_BYTES = 1024 * 1024
_RESTORE_TEST_METHOD = "tmp_extraction+sqlite_pragma_integrity_check"


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

    # ── VED-P1-002: Production Monitoring diagnostics ───────────────────
    # Additive to the AGC-073 diagnostics above. Same contract: read-only,
    # never raises, never returns a filesystem path, stack trace, or
    # environment value. Severity/threshold judgement (warning vs.
    # critical) belongs to HealthEngineService, not here — these methods
    # only report raw, safely-collected values.

    @classmethod
    def check_sqlite_integrity(cls) -> dict:
        """Runs PRAGMA integrity_check on a fresh connection. Read-only —
        never writes to the database."""

        from app.services.database_service import DatabaseService

        try:
            connection = DatabaseService.get_connection()
            try:
                cursor = connection.cursor()
                cursor.execute("PRAGMA integrity_check")
                row = cursor.fetchone()
                ok = bool(row) and row[0] == "ok"
                return {"status": "healthy" if ok else "unhealthy", "result": row[0] if row else "unknown"}
            finally:
                connection.close()
        except Exception:
            return {"status": "unhealthy", "result": "unknown"}

    @classmethod
    def get_memory_usage(cls) -> dict:
        """Cross-platform best-effort read: /proc/meminfo on Linux (the
        production target), GlobalMemoryStatusEx via ctypes (stdlib, no new
        dependency) on Windows dev machines. Anything else reports
        "unknown" rather than guessing.
        """

        try:
            system = platform.system()

            if system == "Linux":
                fields: dict = {}
                with open("/proc/meminfo", "r", encoding="utf-8") as handle:
                    for line in handle:
                        key, _, rest = line.partition(":")
                        value = rest.strip().split(" ")[0]
                        if value.isdigit():
                            fields[key] = int(value)

                total_kb = fields.get("MemTotal")
                available_kb = fields.get("MemAvailable")

                if not total_kb or available_kb is None:
                    return cls._unknown_memory()

                used_kb = total_kb - available_kb
                percent_used = (used_kb / total_kb) * 100

                return {
                    "total_mb": round(total_kb / 1024, 2),
                    "used_mb": round(used_kb / 1024, 2),
                    "percent_used": round(percent_used, 2),
                    "status": "ok",
                }

            if system == "Windows":
                import ctypes

                class _MemoryStatusEx(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                    ]

                stat = _MemoryStatusEx()
                stat.dwLength = ctypes.sizeof(_MemoryStatusEx)
                if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                    return cls._unknown_memory()

                total_mb = stat.ullTotalPhys / (1024 ** 2)
                avail_mb = stat.ullAvailPhys / (1024 ** 2)

                return {
                    "total_mb": round(total_mb, 2),
                    "used_mb": round(total_mb - avail_mb, 2),
                    "percent_used": round(float(stat.dwMemoryLoad), 2),
                    "status": "ok",
                }

            return cls._unknown_memory()
        except Exception:
            return cls._unknown_memory()

    @classmethod
    def _unknown_memory(cls) -> dict:

        return {"total_mb": None, "used_mb": None, "percent_used": None, "status": "unknown"}

    @classmethod
    def get_cpu_usage(cls) -> dict:
        """1-minute load average normalized by core count. os.getloadavg()
        is POSIX-only (the production VPS target); Windows dev machines
        report "unknown" rather than a fabricated number.
        """

        cpu_count = os.cpu_count() or 1

        try:
            load_1m, _, _ = os.getloadavg()
            return {
                "load_average_1m": round(load_1m, 2),
                "cpu_count": cpu_count,
                "load_ratio": round(load_1m / cpu_count, 2),
                "status": "ok",
            }
        except (AttributeError, OSError):
            return {
                "load_average_1m": None,
                "cpu_count": cpu_count,
                "load_ratio": None,
                "status": "unknown",
            }

    @classmethod
    def get_backup_status(cls) -> dict:
        """Reads the status sentinel scripts/backup.sh writes on every run
        (BACKUP_ROOT/last_backup_status: "SUCCESS <ts>: <dest>" or
        "FAILED <ts>: <reason>"). Read-only — this app never triggers a
        backup itself.
        """

        try:
            status_path = Path(settings.BACKUP_ROOT) / "last_backup_status"

            if not status_path.exists():
                return {"status": "unknown", "last_result": None, "last_backup_at": None, "stale": None}

            content = status_path.read_text(encoding="utf-8", errors="ignore").strip()
            parts = content.split(" ", 2)
            result = parts[0] if parts else "UNKNOWN"
            timestamp_token = parts[1].rstrip(":") if len(parts) > 1 else None

            backup_at_iso: Optional[str] = None
            stale: Optional[bool] = None

            if timestamp_token:
                try:
                    backup_at = datetime.strptime(timestamp_token, _BACKUP_TIMESTAMP_FORMAT)
                    backup_at_iso = backup_at.isoformat()
                    stale = (datetime.utcnow() - backup_at) > timedelta(hours=settings.BACKUP_STALE_HOURS)
                except ValueError:
                    pass

            status = "healthy" if result == "SUCCESS" else "unhealthy" if result == "FAILED" else "unknown"

            return {
                "status": status,
                "last_result": result,
                "last_backup_at": backup_at_iso,
                "stale": stale,
            }
        except Exception:
            return {"status": "unknown", "last_result": None, "last_backup_at": None, "stale": None}

    @classmethod
    def verify_backup_archive_integrity(cls) -> dict:
        """Archive-integrity check ONLY: re-runs restore.sh's own checksum
        pre-flight (SHA256 of every archive against checksums.sha256 in the
        most recent backup directory) with zero extraction and zero writes
        to any live file. Never invokes restore.sh.

        This is NOT a restore test — it proves the archive bytes are intact,
        not that they actually extract into a usable database/config. It
        does not know whether the backup can really be restored; see
        get_restore_test_status() for that evidence, which comes from
        scripts/restore_test.sh actually extracting a backup and running
        PRAGMA integrity_check against the restored copy.
        """

        try:
            root = Path(settings.BACKUP_ROOT)

            if not root.exists():
                return {"status": "unknown", "verified": None, "backup_dir": None}

            candidates = sorted(
                (entry for entry in root.iterdir() if entry.is_dir() and entry.name[:4].isdigit()),
                reverse=True,
            )

            if not candidates:
                return {"status": "unknown", "verified": None, "backup_dir": None}

            latest = candidates[0]
            checksum_file = latest / "checksums.sha256"

            if not checksum_file.exists():
                return {"status": "unhealthy", "verified": False, "backup_dir": latest.name}

            verified = cls._verify_checksums(latest, checksum_file)

            return {
                "status": "healthy" if verified else "unhealthy",
                "verified": verified,
                "backup_dir": latest.name,
            }
        except Exception:
            return {"status": "unknown", "verified": None, "backup_dir": None}

    @classmethod
    def get_restore_test_status(cls) -> dict:
        """Reads the restore-test sentinel scripts/restore_test.sh writes
        after each run (BACKUP_ROOT/last_restore_test_status:
        "SUCCESS <ts>: <backup_dir>" or "FAILED <ts>: <backup_dir_or_unknown>
        - <reason>"). Read-only — this app never runs a restore test itself;
        scripts/restore_test.sh is invoked out-of-band (cron/manual), the
        same pattern as scripts/backup.sh and last_backup_status.

        scripts/restore_test.sh actually extracts the latest backup's
        archives into a throwaway /tmp directory and runs
        PRAGMA integrity_check against the extracted SQLite copy — unlike
        verify_backup_archive_integrity(), this is real evidence the backup
        is restorable, not just that its checksums match. Until this
        sentinel exists, restore capability is UNVERIFIED: status is
        "unknown", never "healthy" — callers must not report a backup as
        restore-verified on the strength of this method returning "unknown".
        """

        try:
            status_path = Path(settings.BACKUP_ROOT) / "last_restore_test_status"

            if not status_path.exists():
                return {
                    "status": "unknown",
                    "verified": None,
                    "tested_at": None,
                    "backup_dir": None,
                    "method": None,
                }

            content = status_path.read_text(encoding="utf-8", errors="ignore").strip()
            parts = content.split(" ", 2)
            result = parts[0] if parts else "UNKNOWN"
            timestamp_token = parts[1].rstrip(":") if len(parts) > 1 else None
            detail = parts[2].strip() if len(parts) > 2 else ""

            tested_at_iso: Optional[str] = None
            if timestamp_token:
                try:
                    tested_at = datetime.strptime(timestamp_token, _BACKUP_TIMESTAMP_FORMAT)
                    tested_at_iso = tested_at.isoformat()
                except ValueError:
                    pass

            if result == "SUCCESS":
                status, verified = "healthy", True
                backup_dir = detail or None
            elif result == "FAILED":
                status, verified = "unhealthy", False
                backup_dir_token = detail.split(" - ", 1)[0].strip()
                backup_dir = backup_dir_token if backup_dir_token and backup_dir_token != "unknown" else None
            else:
                status, verified = "unknown", None
                backup_dir = None

            return {
                "status": status,
                "verified": verified,
                "tested_at": tested_at_iso,
                "backup_dir": backup_dir,
                "method": _RESTORE_TEST_METHOD if verified is not None else None,
            }
        except Exception:
            return {
                "status": "unknown",
                "verified": None,
                "tested_at": None,
                "backup_dir": None,
                "method": None,
            }

    @classmethod
    def _verify_checksums(cls, backup_dir: Path, checksum_file: Path) -> bool:

        lines = checksum_file.read_text(encoding="utf-8", errors="ignore").splitlines()

        for line in lines:
            line = line.strip()
            if not line:
                continue

            parts = line.split(maxsplit=1)
            if len(parts) != 2:
                continue

            expected_hash, filename = parts
            archive_path = backup_dir / filename.lstrip("*")

            if not archive_path.exists():
                return False

            hasher = hashlib.sha256()
            with open(archive_path, "rb") as handle:
                for chunk in iter(lambda: handle.read(_CHECKSUM_READ_CHUNK_BYTES), b""):
                    hasher.update(chunk)

            if hasher.hexdigest() != expected_hash:
                return False

        return True
