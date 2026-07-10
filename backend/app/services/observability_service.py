import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.config.config import settings
from app.services.database_service import DatabaseService
from app.services.health_service import HealthService

_start_time = time.time()


class ObservabilityService:

    @classmethod
    def check_health(cls) -> dict:

        db_ok = cls._check_database()
        ffmpeg_ok = cls._check_ffmpeg()
        uptime_seconds = int(time.time() - _start_time)
        overall = "ok" if (db_ok and ffmpeg_ok) else "degraded"

        # AGC-073: additive diagnostics merged into the existing
        # contract. Never overrides the fields above, so existing
        # consumers (deploy validation scripts, docs) keep working.
        extended = cls._get_extended_report_safe()
        extended["checks"]["database"] = "healthy" if db_ok else "unhealthy"

        return {
            "status": overall,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "database": "ok" if db_ok else "error",
            "ffmpeg": "ok" if ffmpeg_ok else "error",
            "uptime_seconds": uptime_seconds,
            **extended,
        }

    @classmethod
    def _get_extended_report_safe(cls) -> dict:

        try:
            return HealthService.get_extended_report()
        except Exception:
            return {
                "build": {"git_commit": "unknown", "git_tag": "unknown"},
                "python_version": "unknown",
                "ffmpeg_version": "unknown",
                "disk": {
                    "total_gb": None,
                    "used_gb": None,
                    "free_gb": None,
                    "percent_free": None,
                    "status": "unhealthy",
                },
                "checks": {
                    "uploads": "unhealthy",
                    "highlights": "unhealthy",
                    "ffmpeg": "unhealthy",
                    "disk": "unhealthy",
                },
            }

    @classmethod
    def check_ready(cls) -> dict:

        checks = {
            "database": cls._check_database(),
            "storage": cls._check_storage_folders(),
            "outputs": cls._check_output_folders(),
            "ffmpeg": cls._check_ffmpeg(),
        }
        ready = all(checks.values())

        return {
            "ready": ready,
            "checks": {
                k: "ok" if v else "error"
                for k, v in checks.items()
            },
        }

    @classmethod
    def get_metrics(cls) -> dict:

        try:
            connection = DatabaseService.get_connection()
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(
                        CASE WHEN status = 'completed'
                        THEN 1 ELSE 0 END
                    ) AS completed,
                    SUM(
                        CASE WHEN status = 'failed'
                        THEN 1 ELSE 0 END
                    ) AS failed,
                    SUM(
                        CASE WHEN status IN ('pending', 'processing')
                        THEN 1 ELSE 0 END
                    ) AS active
                FROM jobs
                """
            )

            job_row = cursor.fetchone()

            cursor.execute(
                "SELECT COUNT(*) FROM users"
            )
            user_count = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT started_at, completed_at
                FROM jobs
                WHERE status = 'completed'
                  AND started_at IS NOT NULL
                  AND completed_at IS NOT NULL
                """
            )
            completed_rows = cursor.fetchall()
            connection.close()

            avg_time = cls._compute_avg_processing_time(
                completed_rows
            )

            return {
                "total_jobs": job_row[0] or 0,
                "completed_jobs": job_row[1] or 0,
                "failed_jobs": job_row[2] or 0,
                "active_jobs": job_row[3] or 0,
                "total_users": user_count or 0,
                "average_processing_time_seconds": avg_time,
            }

        except Exception:
            return {
                "total_jobs": 0,
                "completed_jobs": 0,
                "failed_jobs": 0,
                "active_jobs": 0,
                "total_users": 0,
                "average_processing_time_seconds": None,
            }

    @classmethod
    def _check_database(cls) -> bool:

        try:
            connection = DatabaseService.get_connection()
            connection.execute("SELECT 1")
            connection.close()
            return True
        except Exception:
            return False

    @classmethod
    def _check_ffmpeg(cls) -> bool:

        return (
            shutil.which("ffmpeg") is not None
            and shutil.which("ffprobe") is not None
        )

    @classmethod
    def _check_storage_folders(cls) -> bool:

        folders = [
            settings.UPLOAD_FOLDER,
            settings.JOBS_FOLDER,
        ]
        return all(Path(f).exists() for f in folders)

    @classmethod
    def _check_output_folders(cls) -> bool:

        return Path(settings.JOBS_FOLDER).exists()

    @classmethod
    def _compute_avg_processing_time(
        cls,
        rows: list
    ) -> Optional[float]:

        durations = []

        for started_at, completed_at in rows:
            try:
                started = datetime.fromisoformat(started_at)
                completed = datetime.fromisoformat(completed_at)
                durations.append(
                    (completed - started).total_seconds()
                )
            except Exception:
                pass

        if not durations:
            return None

        return round(sum(durations) / len(durations), 2)
