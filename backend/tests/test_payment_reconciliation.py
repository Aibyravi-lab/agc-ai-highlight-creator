"""
REVENUE-004: webhook + reconciliation safety-net coverage.

Protects against the failure mode where Razorpay captures a payment but
the browser dies before /payments/verify completes. All entitlement
assertions here exercise the real PaymentService.process_verified_payment
and its razorpay_payment_id UNIQUE constraint (never mocked) — only the
Razorpay SDK client itself is mocked where a live network call would
otherwise be required (webhook signature verification uses the real
HMAC-SHA256 code path throughout).
"""

import hashlib
import hmac
import json
import tempfile
import threading
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config.config import settings
from app.routers import payments as payments_router
from app.services.database_service import DatabaseService
from app.services.payment_service import (
    DuplicatePaymentError,
    PaymentService,
)
from app.services.reconciliation_scheduler_service import (
    ReconciliationSchedulerService,
)
from app.services.subscription_service import SubscriptionService

WEBHOOK_SECRET = "test_webhook_secret"


def _make_isolated_db():
    tmp_dir = tempfile.TemporaryDirectory()
    DatabaseService.DB_DIR = Path(tmp_dir.name)
    DatabaseService.DB_PATH = Path(tmp_dir.name) / "test_agc.db"
    DatabaseService.initialize()
    return tmp_dir


def _create_user(email: str) -> int:
    connection = DatabaseService.get_connection()
    cursor = connection.cursor()
    now = datetime.utcnow().isoformat()

    cursor.execute(
        """
        INSERT INTO users (name, email, password_hash, created_at)
        VALUES (?, ?, ?, ?)
        """,
        ("Test User", email, "hash", now)
    )

    user_id = cursor.lastrowid

    connection.commit()
    connection.close()

    SubscriptionService.create_default_subscription(user_id)

    return user_id


def _insert_pending_order(
    razorpay_order_id: str,
    user_id: int,
    plan: str = "pro",
    status: str = "PENDING",
    created_at: str | None = None,
) -> None:
    now = created_at or datetime.utcnow().isoformat()

    connection = DatabaseService.get_connection()
    connection.execute(
        """
        INSERT INTO pending_orders (
            razorpay_order_id, user_id, plan, status, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (razorpay_order_id, user_id, plan, status, now, now)
    )
    connection.commit()
    connection.close()


def _pending_order_status(razorpay_order_id: str) -> str | None:
    connection = DatabaseService.get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT status FROM pending_orders WHERE razorpay_order_id = ?",
        (razorpay_order_id,)
    )
    row = cursor.fetchone()
    connection.close()
    return row[0] if row else None


def _payments_count(razorpay_payment_id: str) -> int:
    connection = DatabaseService.get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM payments WHERE razorpay_payment_id = ?",
        (razorpay_payment_id,)
    )
    count = cursor.fetchone()[0]
    connection.close()
    return count


def _captured_payload(order_id: str, payment_id: str) -> dict:
    return {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "order_id": order_id,
                    "status": "captured",
                }
            }
        }
    }


def _failed_payload(order_id: str, payment_id: str) -> dict:
    return {
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "order_id": order_id,
                    "status": "failed",
                }
            }
        }
    }


def _sign(body_bytes: bytes, secret: str) -> str:
    return hmac.new(
        secret.encode("utf-8"), body_bytes, hashlib.sha256
    ).hexdigest()


def _webhook_client() -> TestClient:
    app = FastAPI()
    app.include_router(payments_router.router)
    return TestClient(app)


class WebhookRouteTests(unittest.TestCase):
    """Full route coverage — real HMAC signature verification, no mocks."""

    def setUp(self):
        self._tmp_dir = _make_isolated_db()
        self.user_id = _create_user("webhook@test.com")
        self.client = _webhook_client()

    def tearDown(self):
        self._tmp_dir.cleanup()

    def _post(self, body_dict, headers_override=None):
        body_bytes = json.dumps(body_dict).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if headers_override is not None:
            headers.update(headers_override)
        return self.client.post(
            "/payments/webhook", content=body_bytes, headers=headers
        )

    def test_valid_signature_captured_event_grants_pro(self):
        _insert_pending_order("order_w1", self.user_id)
        body_bytes = json.dumps(
            _captured_payload("order_w1", "pay_w1")
        ).encode("utf-8")

        with patch.object(settings, "RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET):
            response = self.client.post(
                "/payments/webhook",
                content=body_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-Razorpay-Signature": _sign(body_bytes, WEBHOOK_SECRET),
                }
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(_payments_count("pay_w1"), 1)
        self.assertTrue(SubscriptionService.is_pro_active(self.user_id))
        self.assertEqual(_pending_order_status("order_w1"), "RESOLVED")

    def test_invalid_signature_rejected(self):
        _insert_pending_order("order_w2", self.user_id)
        body_bytes = json.dumps(
            _captured_payload("order_w2", "pay_w2")
        ).encode("utf-8")

        with patch.object(settings, "RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET):
            response = self.client.post(
                "/payments/webhook",
                content=body_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-Razorpay-Signature": _sign(body_bytes, "wrong_secret"),
                }
            )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(_payments_count("pay_w2"), 0)
        self.assertFalse(SubscriptionService.is_pro_active(self.user_id))

    def test_missing_signature_rejected(self):
        _insert_pending_order("order_w3", self.user_id)

        with patch.object(settings, "RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET):
            response = self._post(_captured_payload("order_w3", "pay_w3"))

        self.assertEqual(response.status_code, 401)
        self.assertEqual(_payments_count("pay_w3"), 0)

    def test_webhook_not_configured_returns_503(self):
        with patch.object(settings, "RAZORPAY_WEBHOOK_SECRET", ""):
            response = self._post(_captured_payload("order_w4", "pay_w4"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(_payments_count("pay_w4"), 0)


class WebhookEventHandlingTests(unittest.TestCase):
    """PaymentService.handle_webhook_event — event-type semantics."""

    def setUp(self):
        self._tmp_dir = _make_isolated_db()
        self.user_id = _create_user("events@test.com")

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_duplicate_captured_event_is_idempotent(self):
        _insert_pending_order("order_e1", self.user_id)
        payload = _captured_payload("order_e1", "pay_e1")

        PaymentService.handle_webhook_event(payload, "evt_e1")
        PaymentService.handle_webhook_event(payload, "evt_e1_retry")

        self.assertEqual(_payments_count("pay_e1"), 1)
        self.assertTrue(SubscriptionService.is_pro_active(self.user_id))

    def test_unknown_event_is_ignored_without_crash(self):
        _insert_pending_order("order_e2", self.user_id)

        PaymentService.handle_webhook_event(
            {"event": "payment.authorized", "payload": {}}, "evt_e2"
        )

        self.assertEqual(_payments_count("pay_e2"), 0)
        self.assertFalse(SubscriptionService.is_pro_active(self.user_id))
        self.assertEqual(_pending_order_status("order_e2"), "PENDING")

    def test_unmatched_order_is_logged_not_crashed(self):
        PaymentService.handle_webhook_event(
            _captured_payload("order_unknown", "pay_e3"), "evt_e3"
        )

        self.assertEqual(_payments_count("pay_e3"), 0)

    def test_malformed_payload_does_not_crash(self):
        PaymentService.handle_webhook_event(
            {"event": "payment.captured", "payload": {}}, "evt_e4"
        )

    def test_failed_event_never_revokes_existing_entitlement(self):
        _insert_pending_order("order_e5", self.user_id)
        PaymentService.handle_webhook_event(
            _captured_payload("order_e5", "pay_e5"), "evt_e5"
        )
        self.assertTrue(SubscriptionService.is_pro_active(self.user_id))

        PaymentService.handle_webhook_event(
            _failed_payload("order_e5", "pay_e5"), "evt_e5_failed"
        )

        self.assertTrue(SubscriptionService.is_pro_active(self.user_id))
        self.assertEqual(_payments_count("pay_e5"), 1)

    def test_out_of_order_failed_before_captured_still_grants_on_capture(self):
        _insert_pending_order("order_e6", self.user_id)

        PaymentService.handle_webhook_event(
            _failed_payload("order_e6", "pay_e6"), "evt_e6_failed"
        )
        self.assertFalse(SubscriptionService.is_pro_active(self.user_id))

        PaymentService.handle_webhook_event(
            _captured_payload("order_e6", "pay_e6"), "evt_e6_captured"
        )

        self.assertTrue(SubscriptionService.is_pro_active(self.user_id))
        self.assertEqual(_payments_count("pay_e6"), 1)


class RecordPendingOrderTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = _make_isolated_db()
        self.user_id = _create_user("pending@test.com")

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_record_pending_order_persists_mapping(self):
        PaymentService._record_pending_order(self.user_id, "order_p1", "pro")

        connection = DatabaseService.get_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT user_id, plan, status FROM pending_orders "
            "WHERE razorpay_order_id = ?",
            ("order_p1",)
        )
        row = cursor.fetchone()
        connection.close()

        self.assertEqual(row, (self.user_id, "pro", "PENDING"))

    def test_record_pending_order_failure_is_non_fatal(self):
        with patch.object(
            DatabaseService, "get_connection", side_effect=RuntimeError("db down")
        ):
            PaymentService._record_pending_order(self.user_id, "order_p2", "pro")


class ReconciliationSchedulerTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = _make_isolated_db()
        self.user_id = _create_user("reconcile@test.com")
        self._configured_patch = patch.object(
            PaymentService, "is_configured", return_value=True
        )
        self._configured_patch.start()

    def tearDown(self):
        self._configured_patch.stop()
        self._tmp_dir.cleanup()

    @staticmethod
    def _old_timestamp(minutes: int = 0, hours: int = 0) -> str:
        return (
            datetime.utcnow() - timedelta(minutes=minutes, hours=hours)
        ).isoformat()

    def test_captured_payment_discovered_and_entitled(self):
        _insert_pending_order(
            "order_r1", self.user_id, created_at=self._old_timestamp(minutes=30)
        )

        mock_client = MagicMock()
        mock_client.order.payments.return_value = {
            "items": [{"id": "pay_r1", "status": "captured"}]
        }

        with patch.object(PaymentService, "get_client", return_value=mock_client):
            report = ReconciliationSchedulerService.run_once()

        self.assertEqual(report["resolved"], 1)
        self.assertEqual(_payments_count("pay_r1"), 1)
        self.assertTrue(SubscriptionService.is_pro_active(self.user_id))
        self.assertEqual(_pending_order_status("order_r1"), "RESOLVED")

    def test_already_processed_payment_handled_without_double_entitlement(self):
        # pending_orders row deliberately left PENDING to simulate the edge
        # case where a payments row exists via a path other than this
        # order's own process_verified_payment resolution.
        _insert_pending_order(
            "order_r2", self.user_id, created_at=self._old_timestamp(minutes=30)
        )
        now = datetime.utcnow().isoformat()
        connection = DatabaseService.get_connection()
        connection.execute(
            """
            INSERT INTO payments (
                user_id, razorpay_order_id, razorpay_payment_id, plan,
                status, created_at, processed_at
            )
            VALUES (?, ?, ?, 'pro', 'PROCESSED', ?, ?)
            """,
            (self.user_id, "order_r2", "pay_r2", now, now)
        )
        connection.commit()
        connection.close()

        mock_client = MagicMock()
        mock_client.order.payments.return_value = {
            "items": [{"id": "pay_r2", "status": "captured"}]
        }

        with patch.object(PaymentService, "get_client", return_value=mock_client):
            report = ReconciliationSchedulerService.run_once()

        self.assertEqual(report["resolved"], 1)
        self.assertEqual(_payments_count("pay_r2"), 1)

    def test_razorpay_api_failure_does_not_crash_sweep(self):
        _insert_pending_order(
            "order_r3", self.user_id, created_at=self._old_timestamp(minutes=30)
        )

        mock_client = MagicMock()
        mock_client.order.payments.side_effect = RuntimeError("network error")

        with patch.object(PaymentService, "get_client", return_value=mock_client):
            report = ReconciliationSchedulerService.run_once()

        self.assertEqual(report["checked"], 1)
        self.assertEqual(report["resolved"], 0)
        self.assertEqual(_pending_order_status("order_r3"), "PENDING")

    def test_missing_unmatched_payment_stays_pending(self):
        _insert_pending_order(
            "order_r4", self.user_id, created_at=self._old_timestamp(minutes=30)
        )

        mock_client = MagicMock()
        mock_client.order.payments.return_value = {"items": []}

        with patch.object(PaymentService, "get_client", return_value=mock_client):
            report = ReconciliationSchedulerService.run_once()

        self.assertEqual(report["resolved"], 0)
        self.assertEqual(report["abandoned"], 0)
        self.assertEqual(_pending_order_status("order_r4"), "PENDING")

    def test_old_unresolved_order_marked_abandoned(self):
        _insert_pending_order(
            "order_r5", self.user_id, created_at=self._old_timestamp(hours=25)
        )

        mock_client = MagicMock()
        mock_client.order.payments.return_value = {"items": []}

        with patch.object(PaymentService, "get_client", return_value=mock_client):
            report = ReconciliationSchedulerService.run_once()

        self.assertEqual(report["abandoned"], 1)
        self.assertEqual(_pending_order_status("order_r5"), "ABANDONED")
        self.assertFalse(SubscriptionService.is_pro_active(self.user_id))

    def test_orders_within_grace_period_are_skipped(self):
        _insert_pending_order(
            "order_r6", self.user_id, created_at=datetime.utcnow().isoformat()
        )

        mock_client = MagicMock()

        with patch.object(PaymentService, "get_client", return_value=mock_client):
            report = ReconciliationSchedulerService.run_once()

        self.assertEqual(report["checked"], 0)
        mock_client.order.payments.assert_not_called()

    def test_not_configured_skips_sweep(self):
        _insert_pending_order(
            "order_r7", self.user_id, created_at=self._old_timestamp(minutes=30)
        )

        with patch.object(PaymentService, "is_configured", return_value=False):
            report = ReconciliationSchedulerService.run_once()

        self.assertEqual(report, {"skipped": "not_configured"})
        self.assertEqual(_pending_order_status("order_r7"), "PENDING")


class ConcurrencyTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = _make_isolated_db()
        self.user_id = _create_user("concurrent@test.com")

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_browser_verification_and_webhook_race(self):
        _insert_pending_order("order_c1", self.user_id)
        payload = _captured_payload("order_c1", "pay_c1")
        results = []
        results_lock = threading.Lock()

        def browser_verify():
            try:
                PaymentService.process_verified_payment(
                    self.user_id, "order_c1", "pay_c1", "pro"
                )
                outcome = "success"
            except DuplicatePaymentError:
                outcome = "duplicate"
            with results_lock:
                results.append(outcome)

        def webhook_deliver():
            PaymentService.handle_webhook_event(payload, "evt_c1")

        threads = [
            threading.Thread(target=browser_verify),
            threading.Thread(target=webhook_deliver),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(_payments_count("pay_c1"), 1)
        self.assertTrue(SubscriptionService.is_pro_active(self.user_id))

    def test_duplicate_webhook_deliveries_race(self):
        _insert_pending_order("order_c2", self.user_id)
        payload = _captured_payload("order_c2", "pay_c2")

        threads = [
            threading.Thread(
                target=PaymentService.handle_webhook_event,
                args=(payload, f"evt_c2_{i}")
            )
            for i in range(5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(_payments_count("pay_c2"), 1)
        self.assertTrue(SubscriptionService.is_pro_active(self.user_id))

    def test_reconciliation_and_webhook_race(self):
        _insert_pending_order(
            "order_c3",
            self.user_id,
            created_at=(datetime.utcnow() - timedelta(minutes=30)).isoformat()
        )
        payload = _captured_payload("order_c3", "pay_c3")

        mock_client = MagicMock()
        mock_client.order.payments.return_value = {
            "items": [{"id": "pay_c3", "status": "captured"}]
        }

        def run_reconciliation():
            with patch.object(PaymentService, "get_client", return_value=mock_client), \
                 patch.object(PaymentService, "is_configured", return_value=True):
                ReconciliationSchedulerService.run_once()

        def deliver_webhook():
            PaymentService.handle_webhook_event(payload, "evt_c3")

        threads = [
            threading.Thread(target=run_reconciliation),
            threading.Thread(target=deliver_webhook),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(_payments_count("pay_c3"), 1)
        self.assertTrue(SubscriptionService.is_pro_active(self.user_id))


if __name__ == "__main__":
    unittest.main()
