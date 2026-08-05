import threading

from app.config.config import settings
from app.services.alert_engine_service import AlertEngineService
from app.services.health_engine_service import HealthEngineService
from app.services.health_history_service import HealthHistoryService
from app.services.logger_service import LoggerService


class HealthSchedulerService:
    """VED-P1-002: drives automatic health evaluation without adding a
    scheduler dependency (no APScheduler, no external cron) — a single
    daemon thread on an interruptible sleep, the same raw-threading
    approach BackgroundJobService already uses for pipeline workers. Every
    HEALTH_SNAPSHOT_INTERVAL_MINUTES it runs HealthEngineService, persists
    a snapshot via HealthHistoryService, and raises/resolves alerts via
    AlertEngineService.
    """

    _thread: threading.Thread | None = None
    _stop_event = threading.Event()

    @classmethod
    def start(cls) -> None:

        if cls._thread is not None and cls._thread.is_alive():
            return

        cls._stop_event.clear()
        cls._thread = threading.Thread(
            target=cls._run,
            name="health-monitoring-scheduler",
            daemon=True,
        )
        cls._thread.start()

        LoggerService.info("HealthSchedulerService started")

    @classmethod
    def stop(cls) -> None:

        cls._stop_event.set()

        if cls._thread is not None:
            cls._thread.join(timeout=5)

        LoggerService.info("HealthSchedulerService stopped")

    @classmethod
    def _run(cls) -> None:

        interval_seconds = max(60, settings.HEALTH_SNAPSHOT_INTERVAL_MINUTES * 60)

        while not cls._stop_event.is_set():
            cls.run_once()
            cls._stop_event.wait(interval_seconds)

    @classmethod
    def run_once(cls) -> dict:
        # Public so tests (or a future manual "evaluate now" admin action)
        # can trigger exactly one evaluation cycle without spinning up the
        # background thread.

        try:
            report = HealthEngineService.evaluate(use_cache=False)
            HealthHistoryService.record_snapshot(report)
            AlertEngineService.evaluate_and_raise(report)
            return report
        except Exception as exc:
            LoggerService.error(f"HealthSchedulerService.run_once failed: {exc}")
            return {}
