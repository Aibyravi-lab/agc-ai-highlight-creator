import threading
from datetime import datetime, timedelta, timezone

import requests

from app.config.config import settings
from app.services.health_service import HealthService
from app.services.logger_service import LoggerService
from app.services.mission_control_service import MissionControlService
from app.services.monitoring_event_service import MonitoringEventService
from app.services.observability_service import ObservabilityService
from app.services.ops_service import OpsService
from app.services.payment_service import PaymentService


class CheckStatus:
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class HealthEngineService:
    """VED-P1-002: Production Monitoring health engine.

    Reuses every existing health signal (ObservabilityService, HealthService,
    OpsService, MissionControlService, PaymentService) and adds only the
    checks that had no home yet (SQLite integrity, memory, CPU, payment/
    email failure rate via MonitoringEventService, backups). Every check
    runs through _safe() in isolation — one failing check degrades only its
    own entry to "unknown", the same fail-isolation contract already used by
    HealthService._safe / ObservabilityService / OpsService.

    evaluate() is a pure read: it computes and returns a report but never
    writes to the database. Persistence (health_snapshots) and alerting
    (monitoring_alerts) are separate, explicit steps driven by
    HealthSchedulerService — see that module for why.
    """

    # Weight of each check in the 0-100 Production Health Score.
    # growth_intelligence is reported (visible in `checks`) but carries 0
    # weight: Mission Control cannot compute successfully if backend/
    # database are already down, so weighting it too would double-count
    # the same underlying signal.
    WEIGHTS: dict = {
        "backend": 15,
        "frontend": 5,
        "database": 15,
        "sqlite_integrity": 10,
        "disk": 10,
        "memory": 5,
        "cpu": 5,
        "queue": 5,
        "ai_pipeline": 10,
        "payments": 5,
        "email": 5,
        "backups": 10,
        "growth_intelligence": 0,
    }

    _STATUS_MULTIPLIER = {
        CheckStatus.HEALTHY: 1.0,
        CheckStatus.WARNING: 0.5,
        CheckStatus.CRITICAL: 0.0,
    }

    _cache: dict = {}
    _lock = threading.Lock()

    @classmethod
    def evaluate(cls, use_cache: bool = True) -> dict:

        if use_cache:
            cached = cls._get_cached()
            if cached is not None:
                return cached

        checks = {
            "backend": cls._safe(cls._check_backend),
            "frontend": cls._safe(cls._check_frontend),
            "database": cls._safe(cls._check_database),
            "sqlite_integrity": cls._safe(cls._check_sqlite_integrity),
            "disk": cls._safe(cls._check_disk),
            "memory": cls._safe(cls._check_memory),
            "cpu": cls._safe(cls._check_cpu),
            "queue": cls._safe(cls._check_queue),
            "ai_pipeline": cls._safe(cls._check_ai_pipeline),
            "payments": cls._safe(cls._check_payments),
            "email": cls._safe(cls._check_email),
            "backups": cls._safe(cls._check_backups),
            "growth_intelligence": cls._safe(cls._check_growth_intelligence),
        }

        score = cls._score(checks)
        status = cls._overall_status(score, checks)

        report = {
            "score": score,
            "status": status,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "checks": checks,
        }

        with cls._lock:
            cls._cache["report"] = (datetime.utcnow(), report)

        return report

    @classmethod
    def _get_cached(cls) -> dict | None:

        ttl = timedelta(seconds=settings.HEALTH_ENGINE_CACHE_TTL_SECONDS)

        with cls._lock:
            entry = cls._cache.get("report")
            if entry is None:
                return None
            stored_at, value = entry
            if datetime.utcnow() - stored_at <= ttl:
                return value
            return None

    @classmethod
    def clear_cache(cls) -> None:
        # Test-only convenience, mirrors OpsService._cache.clear() usage in
        # test_ops.py.

        with cls._lock:
            cls._cache.clear()

    @classmethod
    def _safe(cls, fn) -> dict:

        try:
            return fn()
        except Exception as exc:
            LoggerService.error(f"HealthEngineService check failed: {exc}")
            return {"status": CheckStatus.UNKNOWN, "message": "Check failed to run.", "evidence": {}}

    # ── Individual checks ────────────────────────────────────────────────

    @classmethod
    def _check_backend(cls) -> dict:

        health = ObservabilityService.check_health()
        healthy = health.get("status") == "ok"

        return {
            "status": CheckStatus.HEALTHY if healthy else CheckStatus.CRITICAL,
            "message": f"Backend reporting '{health.get('status')}'.",
            "evidence": {
                "uptime_seconds": health.get("uptime_seconds"),
                "environment": health.get("environment"),
                "ffmpeg": health.get("ffmpeg"),
            },
        }

    @classmethod
    def _check_frontend(cls) -> dict:

        url = settings.FRONTEND_URL

        if not url:
            return {"status": CheckStatus.UNKNOWN, "message": "FRONTEND_URL not configured.", "evidence": {}}

        try:
            response = requests.get(
                url,
                timeout=settings.FRONTEND_HEALTH_CHECK_TIMEOUT_SECONDS,
            )
            reachable = response.status_code < 500

            return {
                "status": CheckStatus.HEALTHY if reachable else CheckStatus.WARNING,
                "message": f"Frontend responded HTTP {response.status_code}.",
                "evidence": {"status_code": response.status_code},
            }
        except Exception:
            return {
                "status": CheckStatus.WARNING,
                "message": "Frontend did not respond within timeout.",
                "evidence": {},
            }

    @classmethod
    def _check_database(cls) -> dict:

        health = ObservabilityService.check_health()
        healthy = health.get("database") == "ok"

        return {
            "status": CheckStatus.HEALTHY if healthy else CheckStatus.CRITICAL,
            "message": "Database reachable." if healthy else "Database connection failed.",
            "evidence": {},
        }

    @classmethod
    def _check_sqlite_integrity(cls) -> dict:

        result = HealthService.check_sqlite_integrity()
        healthy = result.get("status") == "healthy"

        return {
            "status": CheckStatus.HEALTHY if healthy else CheckStatus.CRITICAL,
            "message": f"PRAGMA integrity_check: {result.get('result')}.",
            "evidence": result,
        }

    @classmethod
    def _check_disk(cls) -> dict:

        disk = HealthService.get_disk_usage()
        percent_free = disk.get("percent_free")

        if percent_free is None:
            return {"status": CheckStatus.UNKNOWN, "message": "Disk usage unavailable.", "evidence": disk}

        percent_used = round(100 - percent_free, 2)

        if percent_used >= settings.HEALTH_DISK_CRITICAL_PERCENT_USED:
            status = CheckStatus.CRITICAL
        elif percent_used >= settings.HEALTH_DISK_WARNING_PERCENT_USED:
            status = CheckStatus.WARNING
        else:
            status = CheckStatus.HEALTHY

        return {"status": status, "message": f"Disk {percent_used}% used.", "evidence": disk}

    @classmethod
    def _check_memory(cls) -> dict:

        memory = HealthService.get_memory_usage()
        percent_used = memory.get("percent_used")

        if memory.get("status") != "ok" or percent_used is None:
            return {
                "status": CheckStatus.UNKNOWN,
                "message": "Memory usage unavailable on this platform.",
                "evidence": memory,
            }

        if percent_used >= settings.HEALTH_MEMORY_CRITICAL_PERCENT_USED:
            status = CheckStatus.CRITICAL
        elif percent_used >= settings.HEALTH_MEMORY_WARNING_PERCENT_USED:
            status = CheckStatus.WARNING
        else:
            status = CheckStatus.HEALTHY

        return {"status": status, "message": f"Memory {percent_used}% used.", "evidence": memory}

    @classmethod
    def _check_cpu(cls) -> dict:

        cpu = HealthService.get_cpu_usage()
        ratio = cpu.get("load_ratio")

        if cpu.get("status") != "ok" or ratio is None:
            return {
                "status": CheckStatus.UNKNOWN,
                "message": "CPU load average unavailable on this platform.",
                "evidence": cpu,
            }

        if ratio >= settings.HEALTH_CPU_CRITICAL_LOAD_RATIO:
            status = CheckStatus.CRITICAL
        elif ratio >= settings.HEALTH_CPU_WARNING_LOAD_RATIO:
            status = CheckStatus.WARNING
        else:
            status = CheckStatus.HEALTHY

        return {"status": status, "message": f"Load ratio {ratio} of available cores.", "evidence": cpu}

    @classmethod
    def _check_queue(cls) -> dict:

        queue = OpsService.get_queue()

        if queue.get("status") != "ok":
            return {"status": CheckStatus.UNKNOWN, "message": "Queue depth unavailable.", "evidence": queue}

        depth = queue.get("queue_depth", 0)
        max_concurrent = queue.get("max_concurrent_jobs") or 1
        threshold = max_concurrent * settings.HEALTH_QUEUE_WARNING_MULTIPLIER

        status = CheckStatus.WARNING if depth > threshold else CheckStatus.HEALTHY

        return {
            "status": status,
            "message": f"Queue depth {depth} (warning threshold {round(threshold)}).",
            "evidence": queue,
        }

    @classmethod
    def _check_ai_pipeline(cls) -> dict:

        jobs = OpsService.get_jobs()

        if jobs.get("status") != "ok":
            return {"status": CheckStatus.UNKNOWN, "message": "Job stats unavailable.", "evidence": jobs}

        total = jobs.get("total_jobs", 0)
        failed = jobs.get("failed_jobs", 0)

        if total == 0:
            return {"status": CheckStatus.HEALTHY, "message": "No jobs processed yet.", "evidence": jobs}

        rate = failed / total

        if rate >= settings.HEALTH_AI_PIPELINE_FAILURE_RATE_CRITICAL:
            status = CheckStatus.CRITICAL
        elif rate >= settings.HEALTH_AI_PIPELINE_FAILURE_RATE_WARNING:
            status = CheckStatus.WARNING
        else:
            status = CheckStatus.HEALTHY

        return {
            "status": status,
            "message": f"AI pipeline failure rate {round(rate * 100, 1)}% ({failed}/{total}).",
            "evidence": jobs,
        }

    @classmethod
    def _check_payments(cls) -> dict:

        if not PaymentService.is_configured():
            return {"status": CheckStatus.UNKNOWN, "message": "Payment gateway not configured.", "evidence": {}}

        count = MonitoringEventService.count_recent_failures(
            MonitoringEventService.PAYMENT, settings.MONITORING_EVENT_WINDOW_MINUTES
        )
        status = (
            CheckStatus.WARNING
            if count >= settings.HEALTH_PAYMENT_FAILURE_WARNING_COUNT
            else CheckStatus.HEALTHY
        )

        return {
            "status": status,
            "message": f"{count} payment failure(s) in the last {settings.MONITORING_EVENT_WINDOW_MINUTES}m.",
            "evidence": {"failure_count": count, "window_minutes": settings.MONITORING_EVENT_WINDOW_MINUTES},
        }

    @classmethod
    def _check_email(cls) -> dict:

        count = MonitoringEventService.count_recent_failures(
            MonitoringEventService.EMAIL, settings.MONITORING_EVENT_WINDOW_MINUTES
        )
        status = (
            CheckStatus.WARNING
            if count >= settings.HEALTH_EMAIL_FAILURE_WARNING_COUNT
            else CheckStatus.HEALTHY
        )

        return {
            "status": status,
            "message": f"{count} email failure(s) in the last {settings.MONITORING_EVENT_WINDOW_MINUTES}m.",
            "evidence": {"failure_count": count, "window_minutes": settings.MONITORING_EVENT_WINDOW_MINUTES},
        }

    @classmethod
    def _check_backups(cls) -> dict:
        """VED-BACKUP-FIX: three separate signals, never conflated —
        (1) backup freshness/status, (2) archive-integrity (checksums,
        zero extraction), (3) restore_test (an actual non-destructive
        extraction + PRAGMA integrity_check, run out-of-band by
        scripts/restore_test.sh). A fresh, checksum-clean backup whose
        restore has never actually been test-extracted is WARNING, not
        HEALTHY — the message must never claim "restore-verified" unless
        restore_test.status == "healthy".
        """

        backup = HealthService.get_backup_status()
        archive_integrity = HealthService.verify_backup_archive_integrity()
        restore_test = HealthService.get_restore_test_status()

        if backup.get("status") == "unknown":
            status = CheckStatus.CRITICAL
            message = "No backup status recorded — backups may not be running."
        elif backup.get("status") == "unhealthy":
            status = CheckStatus.CRITICAL
            message = "Last backup run failed."
        elif backup.get("stale"):
            status = CheckStatus.CRITICAL
            message = f"Last successful backup is older than {settings.BACKUP_STALE_HOURS}h."
        elif archive_integrity.get("status") != "healthy":
            status = CheckStatus.CRITICAL
            message = "Latest backup failed archive-integrity verification (checksum mismatch or corrupt archive)."
        elif restore_test.get("status") == "unhealthy":
            status = CheckStatus.CRITICAL
            message = "Latest restore-test failed — backup may not actually be restorable."
        elif restore_test.get("status") == "unknown":
            status = CheckStatus.WARNING
            message = "Backups current and archive-integrity verified, but an actual restore-test has never been performed."
        else:
            status = CheckStatus.HEALTHY
            message = "Backups current, archive-integrity verified, and restore-test passed."

        return {
            "status": status,
            "message": message,
            "evidence": {
                "backup": backup,
                "archive_integrity": archive_integrity,
                "restore_test": restore_test,
            },
        }

    @classmethod
    def _check_growth_intelligence(cls) -> dict:

        try:
            MissionControlService.get_summary()
            return {
                "status": CheckStatus.HEALTHY,
                "message": "Mission Control summary computed successfully.",
                "evidence": {},
            }
        except Exception:
            return {
                "status": CheckStatus.CRITICAL,
                "message": "Mission Control summary failed to compute.",
                "evidence": {},
            }

    # ── Scoring ───────────────────────────────────────────────────────────

    @classmethod
    def _score(cls, checks: dict) -> int:

        numerator = 0.0
        denominator = 0.0

        for key, weight in cls.WEIGHTS.items():
            if weight <= 0:
                continue

            entry = checks.get(key, {})
            status = entry.get("status", CheckStatus.UNKNOWN)

            if status == CheckStatus.UNKNOWN:
                continue

            multiplier = cls._STATUS_MULTIPLIER.get(status, 0.0)
            numerator += weight * multiplier
            denominator += weight

        if denominator == 0:
            return 100

        return round(100 * numerator / denominator)

    @classmethod
    def _overall_status(cls, score: int, checks: dict) -> str:

        has_critical = any(entry.get("status") == CheckStatus.CRITICAL for entry in checks.values())
        has_warning = any(entry.get("status") == CheckStatus.WARNING for entry in checks.values())

        if has_critical or score < 70:
            return "critical"
        if has_warning or score < 90:
            return "degraded"
        return "healthy"
