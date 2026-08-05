from datetime import datetime, timedelta

from app.services.database_service import DatabaseService
from app.services.logger_service import LoggerService


class MonitoringEventService:
    """VED-P1-002: additive failure-event log for signals that have no
    persisted table of their own — payment and email failures never write
    a DB row today (PaymentService only inserts into `payments` on
    success; EmailService never persists anything). This service is the
    single place new failure events are recorded, so HealthEngineService
    has something to read for the "Payment failures" / "Email failures"
    health checks the sprint requires.

    record_failure() must never raise and never change the caller's
    control flow — callers invoke it from an existing `except` block
    purely for observability, exactly like the LoggerService.error() call
    already sitting next to it.
    """

    PAYMENT = "payment"
    EMAIL = "email"

    @classmethod
    def record_failure(cls, category: str, detail: str) -> None:

        try:
            connection = DatabaseService.get_connection()
            try:
                connection.execute(
                    "INSERT INTO monitoring_events (category, detail, created_at) VALUES (?, ?, ?)",
                    (category, detail, datetime.utcnow().isoformat()),
                )
                connection.commit()
            finally:
                connection.close()
        except Exception as exc:
            LoggerService.error(f"MonitoringEventService.record_failure failed: {exc}")

    @classmethod
    def count_recent_failures(cls, category: str, window_minutes: int) -> int:

        try:
            cutoff = (datetime.utcnow() - timedelta(minutes=window_minutes)).isoformat()

            connection = DatabaseService.get_connection()
            try:
                cursor = connection.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM monitoring_events WHERE category = ? AND created_at >= ?",
                    (category, cutoff),
                )
                row = cursor.fetchone()
                return row[0] if row else 0
            finally:
                connection.close()
        except Exception as exc:
            LoggerService.error(f"MonitoringEventService.count_recent_failures failed: {exc}")
            return 0
