import threading
from datetime import datetime, timedelta
from typing import Callable

from app.config.config import settings
from app.services.database_service import DatabaseService
from app.services.health_service import HealthService
from app.services.logger_service import LoggerService
from app.services.observability_service import ObservabilityService

# VED-OPS-001: caps the average-processing-time sample so this query stays
# bounded as the jobs table grows, unlike ObservabilityService.get_metrics()'s
# equivalent (unbounded) query — that existing method is left untouched.
_JOBS_AVG_DURATION_SAMPLE_LIMIT = 200


class OpsService:
    """Read-only, aggregate-only metrics for the internal Operations API
    (/api/v1/ops/*) consumed by Founder Pulse.

    Every public method fails in isolation: an exception degrades only that
    section's own payload (status: "unavailable") and is logged by message
    only — never the caller, the Authorization header, or a stack trace.
    """

    _cache: dict = {}
    _lock = threading.Lock()

    CAPABILITIES = [
        "health",
        "system",
        "jobs",
        "storage",
        "users",
        "queue",
        "summary",
    ]

    @classmethod
    def _cached(cls, key: str, compute: Callable[[], dict]) -> dict:

        ttl = timedelta(seconds=settings.OPS_CACHE_TTL_SECONDS)

        with cls._lock:
            entry = cls._cache.get(key)
            if entry is not None:
                stored_at, value = entry
                if datetime.utcnow() - stored_at <= ttl:
                    return value

        value = compute()

        with cls._lock:
            cls._cache[key] = (datetime.utcnow(), value)

        return value

    @classmethod
    def get_capabilities(cls) -> dict:

        return {
            "contract_version": "v1",
            "version": settings.APP_VERSION,
            "features": list(cls.CAPABILITIES),
        }

    @classmethod
    def get_health(cls) -> dict:

        try:
            return ObservabilityService.check_health()
        except Exception as exc:
            LoggerService.error(f"ops.health failed: {exc}")
            return {"status": "unavailable"}

    @classmethod
    def get_system(cls) -> dict:

        try:
            return cls._cached("system", cls._compute_system)
        except Exception as exc:
            LoggerService.error(f"ops.system failed: {exc}")
            return {"status": "unavailable"}

    @classmethod
    def _compute_system(cls) -> dict:

        health = ObservabilityService.check_health()

        return {
            "status": "ok",
            "environment": settings.ENVIRONMENT,
            "uptime_seconds": health.get("uptime_seconds"),
            "python_version": HealthService.get_python_version(),
            "ffmpeg": HealthService.get_ffmpeg_info(),
            "build": HealthService.get_app_version(),
            "disk": HealthService.get_disk_usage(),
        }

    @classmethod
    def get_jobs(cls) -> dict:

        try:
            return cls._cached("jobs", cls._compute_jobs)
        except Exception as exc:
            LoggerService.error(f"ops.jobs failed: {exc}")
            return {"status": "unavailable"}

    @classmethod
    def _compute_jobs(cls) -> dict:
        # CR-041 audit: MissionControlService._get_live_metrics also
        # totals/completes/fails jobs, but reuse is unsuitable here on both
        # performance and scope grounds — it runs as one step inside a
        # single monolithic method that issues ~10 queries over one
        # connection and writes (expires stale PRO subscriptions) as a side
        # effect, so calling into it would trade this endpoint's single
        # 5-aggregate SELECT for a much heavier multi-query, DB-mutating
        # call. It also never computes pending/processing counts, which
        # this endpoint requires. Kept separate.

        connection = DatabaseService.get_connection()

        try:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending,
                    SUM(CASE WHEN status = 'processing' THEN 1 ELSE 0 END) AS processing,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed
                FROM jobs
                """
            )
            total, pending, processing, completed, failed = cursor.fetchone()

            cursor.execute(
                """
                SELECT started_at, completed_at
                FROM jobs
                WHERE status = 'completed'
                  AND started_at IS NOT NULL
                  AND completed_at IS NOT NULL
                ORDER BY completed_at DESC
                LIMIT ?
                """,
                (_JOBS_AVG_DURATION_SAMPLE_LIMIT,),
            )
            recent_completed = cursor.fetchall()
        finally:
            connection.close()

        return {
            "status": "ok",
            "total_jobs": total or 0,
            "pending_jobs": pending or 0,
            "processing_jobs": processing or 0,
            "completed_jobs": completed or 0,
            "failed_jobs": failed or 0,
            "average_processing_time_seconds": ObservabilityService.average_job_duration_seconds(
                recent_completed
            ),
        }

    @classmethod
    def get_storage(cls) -> dict:

        try:
            jobs = cls._cached("jobs", cls._compute_jobs)

            return {
                "status": "ok",
                "disk": HealthService.get_disk_usage(),
                "jobs_in_flight": (
                    jobs.get("pending_jobs", 0) + jobs.get("processing_jobs", 0)
                ),
            }
        except Exception as exc:
            LoggerService.error(f"ops.storage failed: {exc}")
            return {"status": "unavailable"}

    @classmethod
    def get_users(cls) -> dict:

        try:
            return cls._cached("users", cls._compute_users)
        except Exception as exc:
            LoggerService.error(f"ops.users failed: {exc}")
            return {"status": "unavailable"}

    @classmethod
    def _compute_users(cls) -> dict:
        # VED-OPS-001: single-table, zero-join, no-PII aggregate. Never
        # selects name/email/password_hash.
        #
        # CR-041 audit: MissionControlService._get_live_metrics also counts
        # total/verified/internal users, but its counts answer a different
        # question (growth traction: users WHERE is_internal = 0) than this
        # endpoint's (infra capacity: every user row that exists, internal
        # accounts included). Reusing it would silently exclude internal/
        # test accounts from this endpoint's totals — a semantics mismatch,
        # not just a query difference. Kept separate.

        connection = DatabaseService.get_connection()

        try:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN email_verified = 1 THEN 1 ELSE 0 END) AS verified,
                    SUM(CASE WHEN is_admin = 1 THEN 1 ELSE 0 END) AS admins,
                    SUM(CASE WHEN is_internal = 1 THEN 1 ELSE 0 END) AS internal
                FROM users
                """
            )
            total, verified, admins, internal = cursor.fetchone()
        finally:
            connection.close()

        return {
            "status": "ok",
            "total_users": total or 0,
            "verified_users": verified or 0,
            "admin_users": admins or 0,
            "internal_users": internal or 0,
        }

    @classmethod
    def get_queue(cls) -> dict:

        try:
            return cls._cached("queue", cls._compute_queue)
        except Exception as exc:
            LoggerService.error(f"ops.queue failed: {exc}")
            return {"status": "unavailable"}

    @classmethod
    def _compute_queue(cls) -> dict:

        connection = DatabaseService.get_connection()

        try:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM jobs
                WHERE status IN ('pending', 'processing')
                """
            )
            depth = cursor.fetchone()[0]
        finally:
            connection.close()

        return {
            "status": "ok",
            "queue_depth": depth or 0,
            "max_concurrent_jobs": settings.MAX_CONCURRENT_JOBS,
        }

    @classmethod
    def get_production_health(cls) -> dict:
        # VED-P1-002: read-only Production Health Score for Founder Pulse,
        # reusing the same ops-key auth and cached-section pattern as every
        # other method on this class. Deliberately its own endpoint rather
        # than a new key on get_summary()/CAPABILITIES — both have existing
        # tests asserting an exact key/feature set (test_ops.py), and this
        # class's own contract (CR-038) requires additive-only evolution.

        try:
            return cls._cached("production_health", cls._compute_production_health)
        except Exception as exc:
            LoggerService.error(f"ops.production_health failed: {exc}")
            return {"status": "unavailable"}

    @classmethod
    def _compute_production_health(cls) -> dict:

        from app.services.health_engine_service import HealthEngineService

        report = HealthEngineService.evaluate()

        return {
            "status": "ok",
            "score": report["score"],
            "production_status": report["status"],
            "generated_at": report["generated_at"],
            "checks": {
                check_id: {"status": entry.get("status"), "message": entry.get("message")}
                for check_id, entry in report.get("checks", {}).items()
            },
        }

    @classmethod
    def get_summary(cls) -> dict:
        # Each section getter below already fails in isolation and never
        # raises, so one failing section (status: "unavailable") can never
        # take down the rest of the summary.

        return {
            "health": cls.get_health(),
            "jobs": cls.get_jobs(),
            "storage": cls.get_storage(),
            "users": cls.get_users(),
            "queue": cls.get_queue(),
        }
