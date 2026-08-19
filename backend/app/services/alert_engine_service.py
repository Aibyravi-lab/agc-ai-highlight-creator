import json
from datetime import datetime

from app.services.database_service import DatabaseService
from app.services.health_engine_service import CheckStatus
from app.services.logger_service import LoggerService


class AlertEngineService:
    """VED-P1-002: turns a HealthEngineService.evaluate() report into
    persisted, in-app-only alerts. No external services — no email, SMS, or
    Slack. Alerts live entirely in `monitoring_alerts` and are read back by
    the /admin/health API.

    Every alert carries the four fields the sprint mandates — Severity,
    Root Cause, Evidence, Suggested Fix — plus Time (created_at).

    Dedup rule: at most one *open* (resolved_at IS NULL) alert per check_id
    at a time, so a still-broken check does not spam new rows on every
    evaluation cycle. A check recovering to healthy auto-resolves its open
    alert.
    """

    SEVERITY_BY_STATUS = {
        CheckStatus.CRITICAL: "critical",
        CheckStatus.WARNING: "warning",
    }

    ROOT_CAUSES = {
        "backend": "Backend /health endpoint reporting a non-'ok' status.",
        "frontend": "Frontend did not respond to a reachability check within the configured timeout.",
        "database": "SQLite connection attempt failed.",
        "sqlite_integrity": "PRAGMA integrity_check reported corruption.",
        "disk": "Disk usage crossed the configured warning/critical threshold.",
        "memory": "System memory usage crossed the configured warning/critical threshold.",
        "cpu": "1-minute load average crossed the configured warning/critical threshold.",
        "queue": "Job queue depth crossed the configured warning threshold.",
        "ai_pipeline": "AI pipeline job failure rate crossed the configured warning/critical threshold.",
        "payments": "Payment failure count crossed the configured warning threshold in the rolling window.",
        "email": "Email send failure count crossed the configured warning threshold in the rolling window.",
        "backups": "Backup missing, failed, stale, archive-integrity check failed, or restore-test failed/never performed.",
        "growth_intelligence": "Mission Control summary computation failed.",
        # Deliberately no "self_recovery_backend"/"self_recovery_frontend"
        # entries here (VED-P1-018): those alerts are raised by record_alert()
        # with an already-specific, dynamic message (which unit, which
        # attempt), so _open_or_keep's entry["message"] fallback is what
        # should populate root_cause — a static string here would silently
        # overwrite it. See SUGGESTED_FIXES below for their static fix text.
    }

    SUGGESTED_FIXES = {
        "backend": "Check backend logs (logs/agc.log) and /health for which sub-check is failing; restart the backend service if needed.",
        "frontend": "Verify the frontend deployment is running and FRONTEND_URL is reachable from the backend host.",
        "database": "Verify data/agc.db is not locked, disk has free space, and file permissions are correct.",
        "sqlite_integrity": "Stop writes immediately and restore from the most recent verified backup via scripts/restore.sh.",
        "disk": "Free disk space (storage/frames, storage/thumbnails, storage/jobs are regenerable) or expand the volume.",
        "memory": "Investigate memory usage, restart the backend if leaking, or reduce MAX_CONCURRENT_JOBS.",
        "cpu": "Reduce MAX_CONCURRENT_JOBS or scale up the server.",
        "queue": "Increase MAX_CONCURRENT_JOBS or investigate why jobs are not draining.",
        "ai_pipeline": "Check logs/agc.log for Whisper/OpenCV/FFmpeg errors in recent failed jobs.",
        "payments": "Check the Razorpay dashboard and RAZORPAY_KEY_ID/RAZORPAY_KEY_SECRET configuration.",
        "email": "Check RESEND_API_KEY configuration and the Resend delivery dashboard.",
        "backups": "Run scripts/backup.sh manually and check the VPS cron schedule (investigate the failure in BACKUP_ROOT/logs); if the restore-test has never run or failed, run scripts/restore_test.sh and check BACKUP_ROOT/last_restore_test_status.",
        "growth_intelligence": "Check backend logs for the MissionControlService exception; likely a downstream database or query failure.",
        "self_recovery_backend": "Check backend logs and journalctl -u agc-backend.service; the watchdog has exhausted its automatic recovery attempts for this hour — manual intervention is required.",
        "self_recovery_frontend": "Check journalctl -u agc-frontend.service; the watchdog has exhausted its automatic recovery attempts for this hour — manual intervention is required.",
    }

    @classmethod
    def evaluate_and_raise(cls, report: dict) -> list:
        """Opens/keeps-open alerts for every check at warning/critical, and
        auto-resolves open alerts for checks that have recovered. Returns
        the list of currently-open alerts. Never raises — a persistence
        failure here must not break the caller's evaluation cycle.
        """

        try:
            connection = DatabaseService.get_connection()
            try:
                cursor = connection.cursor()
                now = datetime.utcnow().isoformat()

                for check_id, entry in report.get("checks", {}).items():
                    status = entry.get("status")

                    if status in (CheckStatus.WARNING, CheckStatus.CRITICAL):
                        cls._open_or_keep(cursor, check_id, status, entry, now)
                    else:
                        cls._resolve_open(cursor, check_id, now)

                connection.commit()
            finally:
                connection.close()
        except Exception as exc:
            LoggerService.error(f"AlertEngineService.evaluate_and_raise failed: {exc}")

        return cls.get_open_alerts()

    @classmethod
    def record_alert(cls, check_id: str, message: str, evidence: dict | None = None) -> None:
        """VED-P1-018: standalone entry point for producers other than
        HealthEngineService's evaluate_and_raise cycle — currently only the
        external self-recovery watchdog (scripts/self_recovery_watchdog.sh),
        which calls this via backend/scripts/record_recovery_alert.py after
        an automatic restart attempt fails to bring a service back. Reuses
        the same dedup-by-open-check_id rule as _open_or_keep. Never raises.
        """

        try:
            connection = DatabaseService.get_connection()
            try:
                cursor = connection.cursor()
                now = datetime.utcnow().isoformat()
                entry = {"message": message, "evidence": evidence or {}}
                cls._open_or_keep(cursor, check_id, CheckStatus.CRITICAL, entry, now)
                connection.commit()
            finally:
                connection.close()
        except Exception as exc:
            LoggerService.error(f"AlertEngineService.record_alert failed: {exc}")

    @classmethod
    def resolve_alert(cls, check_id: str) -> None:
        """VED-P1-018: counterpart to record_alert — called by the external
        watchdog once a service it previously flagged has recovered. Never
        raises.
        """

        try:
            connection = DatabaseService.get_connection()
            try:
                cursor = connection.cursor()
                now = datetime.utcnow().isoformat()
                cls._resolve_open(cursor, check_id, now)
                connection.commit()
            finally:
                connection.close()
        except Exception as exc:
            LoggerService.error(f"AlertEngineService.resolve_alert failed: {exc}")

    @classmethod
    def _open_or_keep(cls, cursor, check_id: str, status: str, entry: dict, now: str) -> None:

        cursor.execute(
            "SELECT id FROM monitoring_alerts WHERE check_id = ? AND resolved_at IS NULL",
            (check_id,),
        )

        if cursor.fetchone():
            return

        severity = cls.SEVERITY_BY_STATUS.get(status, "warning")
        root_cause = cls.ROOT_CAUSES.get(check_id, entry.get("message", "Unknown check failure."))
        suggested_fix = cls.SUGGESTED_FIXES.get(check_id, "Investigate the failing check's evidence.")
        evidence = json.dumps({"message": entry.get("message"), "evidence": entry.get("evidence", {})})

        cursor.execute(
            """
            INSERT INTO monitoring_alerts
                (check_id, severity, root_cause, evidence, suggested_fix, created_at, resolved_at)
            VALUES (?, ?, ?, ?, ?, ?, NULL)
            """,
            (check_id, severity, root_cause, evidence, suggested_fix, now),
        )

    @classmethod
    def _resolve_open(cls, cursor, check_id: str, now: str) -> None:

        cursor.execute(
            "UPDATE monitoring_alerts SET resolved_at = ? WHERE check_id = ? AND resolved_at IS NULL",
            (now, check_id),
        )

    @classmethod
    def get_open_alerts(cls) -> list:

        return cls._list_alerts(resolved=False)

    @classmethod
    def list_alerts(cls, resolved: bool | None = None, limit: int = 100) -> list:

        return cls._list_alerts(resolved=resolved, limit=limit)

    @classmethod
    def _list_alerts(cls, resolved: bool | None = None, limit: int = 100) -> list:

        try:
            connection = DatabaseService.get_connection()
            try:
                cursor = connection.cursor()

                base_query = (
                    "SELECT id, check_id, severity, root_cause, evidence, suggested_fix, "
                    "created_at, resolved_at FROM monitoring_alerts"
                )

                if resolved is True:
                    cursor.execute(f"{base_query} WHERE resolved_at IS NOT NULL ORDER BY created_at DESC LIMIT ?", (limit,))
                elif resolved is False:
                    cursor.execute(f"{base_query} WHERE resolved_at IS NULL ORDER BY created_at DESC LIMIT ?", (limit,))
                else:
                    cursor.execute(f"{base_query} ORDER BY created_at DESC LIMIT ?", (limit,))

                rows = cursor.fetchall()
            finally:
                connection.close()

            return [cls._row_to_alert(row) for row in rows]
        except Exception as exc:
            LoggerService.error(f"AlertEngineService list_alerts failed: {exc}")
            return []

    @classmethod
    def _row_to_alert(cls, row) -> dict:

        (alert_id, check_id, severity, root_cause, evidence_json, suggested_fix, created_at, resolved_at) = row

        try:
            evidence = json.loads(evidence_json)
        except (TypeError, ValueError):
            evidence = {}

        return {
            "id": alert_id,
            "check_id": check_id,
            "severity": severity,
            "root_cause": root_cause,
            "evidence": evidence,
            "suggested_fix": suggested_fix,
            "time": created_at,
            "resolved_at": resolved_at,
        }
