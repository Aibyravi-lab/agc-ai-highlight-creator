import json
from datetime import datetime, timedelta, timezone

from app.services.database_service import DatabaseService
from app.services.logger_service import LoggerService


class HealthHistoryService:
    """VED-P1-002: persists HealthEngineService snapshots and serves the
    Today / Yesterday / 7 Days / 30 Days / Trend views for /admin/health.
    """

    RANGE_DAYS = {"today": 1, "yesterday": 1, "7d": 7, "30d": 30}

    @classmethod
    def record_snapshot(cls, report: dict) -> None:

        try:
            connection = DatabaseService.get_connection()
            try:
                connection.execute(
                    "INSERT INTO health_snapshots (created_at, score, status, checks_json) VALUES (?, ?, ?, ?)",
                    (
                        report.get("generated_at") or datetime.utcnow().isoformat(),
                        report.get("score", 0),
                        report.get("status", "unknown"),
                        json.dumps(report.get("checks", {})),
                    ),
                )
                connection.commit()
            finally:
                connection.close()
        except Exception as exc:
            LoggerService.error(f"HealthHistoryService.record_snapshot failed: {exc}")

    @classmethod
    def get_history(cls, range_key: str) -> dict:

        if range_key not in cls.RANGE_DAYS:
            range_key = "today"

        start, end = cls._bounds(range_key)

        rows = []
        try:
            connection = DatabaseService.get_connection()
            try:
                cursor = connection.cursor()
                cursor.execute(
                    """
                    SELECT created_at, score, status FROM health_snapshots
                    WHERE created_at >= ? AND created_at < ?
                    ORDER BY created_at ASC
                    """,
                    (start.isoformat(), end.isoformat()),
                )
                rows = cursor.fetchall()
            finally:
                connection.close()
        except Exception as exc:
            LoggerService.error(f"HealthHistoryService.get_history failed: {exc}")

        snapshots = [{"created_at": row[0], "score": row[1], "status": row[2]} for row in rows]

        return {
            "range": range_key,
            "snapshots": snapshots,
            "trend": cls._trend(snapshots),
        }

    @classmethod
    def _bounds(cls, range_key: str) -> tuple:

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        if range_key == "today":
            return today_start, today_start + timedelta(days=1)
        if range_key == "yesterday":
            return today_start - timedelta(days=1), today_start

        days = cls.RANGE_DAYS[range_key]
        return today_start - timedelta(days=days - 1), today_start + timedelta(days=1)

    @classmethod
    def _trend(cls, snapshots: list) -> dict:

        if not snapshots:
            return {
                "avg_score": None,
                "min_score": None,
                "max_score": None,
                "current_score": None,
                "direction": "unknown",
            }

        scores = [s["score"] for s in snapshots]
        delta = scores[-1] - scores[0]
        direction = "improving" if delta > 0 else "declining" if delta < 0 else "stable"

        return {
            "avg_score": round(sum(scores) / len(scores), 1),
            "min_score": min(scores),
            "max_score": max(scores),
            "current_score": scores[-1],
            "direction": direction,
        }
