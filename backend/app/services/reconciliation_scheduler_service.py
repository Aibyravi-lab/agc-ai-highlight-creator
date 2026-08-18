import threading
from datetime import datetime, timedelta

from app.config.config import settings
from app.services.logger_service import LoggerService
from app.services.payment_service import (
    DuplicatePaymentError,
    PaymentService,
)


class ReconciliationSchedulerService:
    """REVENUE-004: safety net for the webhook path, using the exact same
    daemon-thread-on-interruptible-sleep pattern as HealthSchedulerService
    (no APScheduler, no external cron, no new process). Every
    RECONCILIATION_INTERVAL_MINUTES it looks for pending_orders that are
    old enough that a normal checkout would already have verified, asks
    Razorpay directly whether any of them were actually captured, and
    converges any it finds into PaymentService.process_verified_payment —
    the same single source of truth the browser and webhook paths use.
    """

    _thread: threading.Thread | None = None
    _stop_event = threading.Event()

    # Orders younger than this are still very likely to complete via the
    # normal browser /payments/verify round trip or the webhook — checking
    # them this early would just be wasted Razorpay API calls.
    GRACE_PERIOD_MINUTES = 10

    # Matches Razorpay's own webhook retry window (webhooks are retried
    # with backoff for up to 24h before Razorpay gives up). An order still
    # unresolved after this long is treated as abandoned rather than
    # polled forever.
    ABANDON_AFTER_HOURS = 24

    @classmethod
    def start(cls) -> None:

        if cls._thread is not None and cls._thread.is_alive():
            return

        cls._stop_event.clear()
        cls._thread = threading.Thread(
            target=cls._run,
            name="payment-reconciliation-scheduler",
            daemon=True,
        )
        cls._thread.start()

        LoggerService.info("ReconciliationSchedulerService started")

    @classmethod
    def stop(cls) -> None:

        cls._stop_event.set()

        if cls._thread is not None:
            cls._thread.join(timeout=5)

        LoggerService.info("ReconciliationSchedulerService stopped")

    @classmethod
    def _run(cls) -> None:

        interval_seconds = max(
            60, settings.RECONCILIATION_INTERVAL_MINUTES * 60
        )

        while not cls._stop_event.is_set():
            cls.run_once()
            cls._stop_event.wait(interval_seconds)

    @classmethod
    def run_once(cls) -> dict:
        # Public so tests (or a future manual "reconcile now" admin action)
        # can trigger exactly one sweep without spinning up the background
        # thread. Never raises — a bad sweep must not take down the
        # scheduler thread or, if called inline, the caller.

        try:
            return cls._reconcile()
        except Exception as exc:
            LoggerService.error(
                f"ReconciliationSchedulerService.run_once failed: {exc}"
            )
            return {}

    @classmethod
    def _reconcile(cls) -> dict:

        if not PaymentService.is_configured():
            return {"skipped": "not_configured"}

        now = datetime.utcnow()
        grace_cutoff = (
            now - timedelta(minutes=cls.GRACE_PERIOD_MINUTES)
        ).isoformat()

        pending_orders = PaymentService.list_pending_orders_older_than(
            grace_cutoff
        )

        checked = 0
        resolved = 0
        abandoned = 0

        for order in pending_orders:
            checked += 1

            try:
                outcome = cls._check_order(order, now)
            except Exception as exc:
                # A single Razorpay API/network failure must not stop the
                # rest of the sweep — every other pending order still gets
                # its chance this cycle, and this one is retried next cycle.
                LoggerService.error(
                    f"Reconciliation check failed for "
                    f"order_id={order['razorpay_order_id']}: {exc}"
                )
                continue

            if outcome == "resolved":
                resolved += 1
            elif outcome == "abandoned":
                abandoned += 1

        report = {
            "checked": checked,
            "resolved": resolved,
            "abandoned": abandoned,
        }

        if checked:
            LoggerService.info(f"Reconciliation sweep: {report}")

        return report

    @classmethod
    def _check_order(cls, order: dict, now: datetime) -> str:

        razorpay_order_id = order["razorpay_order_id"]

        client = PaymentService.get_client()
        payments = client.order.payments(razorpay_order_id)

        captured = next(
            (
                item for item in payments.get("items", [])
                if item.get("status") == "captured"
            ),
            None
        )

        if captured is not None:
            try:
                PaymentService.process_verified_payment(
                    order["user_id"],
                    razorpay_order_id,
                    captured["id"],
                    order["plan"],
                )
                LoggerService.info(
                    f"Reconciliation recovered missed payment "
                    f"order_id={razorpay_order_id} "
                    f"payment_id={captured['id']}",
                    user_id=order["user_id"]
                )
            except DuplicatePaymentError:
                # Resolved by the webhook or browser verify between our
                # SELECT and this call — already correctly entitled.
                pass

            return "resolved"

        created_at = datetime.fromisoformat(order["created_at"])

        if now - created_at > timedelta(hours=cls.ABANDON_AFTER_HOURS):
            PaymentService.mark_order_abandoned(razorpay_order_id)
            return "abandoned"

        return "pending"
