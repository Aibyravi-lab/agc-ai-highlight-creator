import tempfile
import threading
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from app.routers import payments as payments_router
from app.services.database_service import DatabaseService
from app.services.payment_service import (
    DuplicatePaymentError,
    PaymentProcessingError,
    PaymentService,
)
from app.services.subscription_service import (
    SubscriptionPlan,
    SubscriptionStatus,
    SubscriptionService,
)


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


def _credits_remaining(user_id: int) -> int:
    connection = DatabaseService.get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT credits_remaining FROM users WHERE id = ?",
        (user_id,)
    )

    credits = cursor.fetchone()[0]

    connection.close()

    return credits


class ProcessVerifiedPaymentTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = _make_isolated_db()
        self.user_id = _create_user("replay@test.com")

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_first_verification_succeeds_and_activates_subscription(self):
        subscription = PaymentService.process_verified_payment(
            self.user_id, "order_1", "pay_1", "pro"
        )

        self.assertEqual(subscription["plan"], SubscriptionPlan.PRO)
        self.assertEqual(subscription["status"], SubscriptionStatus.ACTIVE)
        self.assertEqual(_payments_count("pay_1"), 1)

    def test_duplicate_payment_id_is_rejected(self):
        PaymentService.process_verified_payment(
            self.user_id, "order_1", "pay_2", "pro"
        )

        with self.assertRaises(DuplicatePaymentError):
            PaymentService.process_verified_payment(
                self.user_id, "order_1", "pay_2", "pro"
            )

        self.assertEqual(_payments_count("pay_2"), 1)

    def test_subscription_and_credits_not_duplicated_on_replay(self):
        credits_before = _credits_remaining(self.user_id)

        PaymentService.process_verified_payment(
            self.user_id, "order_1", "pay_3", "pro"
        )

        with self.assertRaises(DuplicatePaymentError):
            PaymentService.process_verified_payment(
                self.user_id, "order_1", "pay_3", "pro"
            )

        connection = DatabaseService.get_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM subscriptions WHERE user_id = ?",
            (self.user_id,)
        )
        subscription_rows = cursor.fetchone()[0]
        connection.close()

        self.assertEqual(subscription_rows, 1)
        self.assertEqual(_credits_remaining(self.user_id), credits_before)

    def test_concurrent_verification_only_one_request_succeeds(self):
        results = []
        results_lock = threading.Lock()

        def attempt():
            try:
                PaymentService.process_verified_payment(
                    self.user_id, "order_4", "pay_4", "pro"
                )
                outcome = "success"
            except DuplicatePaymentError:
                outcome = "duplicate"
            except Exception as exc:  # pragma: no cover - failure diagnostics
                outcome = f"error:{exc}"

            with results_lock:
                results.append(outcome)

        threads = [threading.Thread(target=attempt) for _ in range(10)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        self.assertEqual(results.count("success"), 1)
        self.assertEqual(results.count("duplicate"), 9)
        self.assertEqual(_payments_count("pay_4"), 1)

    def test_rollback_on_subscription_activation_failure(self):
        with patch.object(
            SubscriptionService,
            "upgrade_to_pro_in_transaction",
            side_effect=RuntimeError("boom")
        ):
            with self.assertRaises(PaymentProcessingError):
                PaymentService.process_verified_payment(
                    self.user_id, "order_5", "pay_5", "pro"
                )

        self.assertEqual(_payments_count("pay_5"), 0)

        subscription = SubscriptionService.get_by_user_id(self.user_id)
        self.assertEqual(subscription["plan"], SubscriptionPlan.FREE)


class VerifyPaymentRouterTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = _make_isolated_db()
        self.user_id = _create_user("router@test.com")

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_verify_endpoint_rejects_replayed_payment_with_409(self):
        body = payments_router.VerifyPaymentRequest(
            razorpay_order_id="order_x",
            razorpay_payment_id="pay_x",
            razorpay_signature="sig_x",
        )
        current_user = {"id": self.user_id}

        with patch.object(
            payments_router.PaymentService,
            "verify_payment",
            return_value=None
        ):
            first_response = payments_router.verify_payment(body, current_user)

            self.assertTrue(first_response["success"])
            self.assertEqual(first_response["plan"], SubscriptionPlan.PRO)

            with self.assertRaises(HTTPException) as ctx:
                payments_router.verify_payment(body, current_user)

        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(_payments_count("pay_x"), 1)


if __name__ == "__main__":
    unittest.main()
