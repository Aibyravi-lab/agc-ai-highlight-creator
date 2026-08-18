import tempfile
import threading
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from app.routers import payments as payments_router
from app.services.database_service import DatabaseService
from app.services.monitoring_event_service import MonitoringEventService
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

    def test_duplicate_payment_id_same_details_is_idempotent(self):
        # Same user/order/plan as the first call — e.g. the webhook already
        # processed this payment and the browser is now retrying /verify
        # for the same real payment. Must succeed, not raise.
        first = PaymentService.process_verified_payment(
            self.user_id, "order_1", "pay_2", "pro"
        )

        second = PaymentService.process_verified_payment(
            self.user_id, "order_1", "pay_2", "pro"
        )

        self.assertEqual(second["plan"], SubscriptionPlan.PRO)
        self.assertEqual(second["status"], SubscriptionStatus.ACTIVE)
        self.assertEqual(second, first)
        self.assertEqual(_payments_count("pay_2"), 1)

    def test_subscription_and_credits_not_duplicated_on_replay(self):
        credits_before = _credits_remaining(self.user_id)

        first = PaymentService.process_verified_payment(
            self.user_id, "order_1", "pay_3", "pro"
        )

        second = PaymentService.process_verified_payment(
            self.user_id, "order_1", "pay_3", "pro"
        )

        self.assertEqual(second, first)

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

    def test_replay_does_not_reset_subscription_expiry(self):
        # The idempotent path must not call upgrade_to_pro_in_transaction
        # again — an already-active subscription's expiry must not move.
        first = PaymentService.process_verified_payment(
            self.user_id, "order_1", "pay_expiry", "pro"
        )

        second = PaymentService.process_verified_payment(
            self.user_id, "order_1", "pay_expiry", "pro"
        )

        self.assertEqual(second["expires_at"], first["expires_at"])
        self.assertEqual(second["started_at"], first["started_at"])

    def test_mismatched_duplicate_different_user_is_rejected(self):
        other_user_id = _create_user("other@test.com")

        PaymentService.process_verified_payment(
            self.user_id, "order_1", "pay_mismatch_user", "pro"
        )

        with self.assertRaises(DuplicatePaymentError):
            PaymentService.process_verified_payment(
                other_user_id, "order_1", "pay_mismatch_user", "pro"
            )

        self.assertEqual(_payments_count("pay_mismatch_user"), 1)
        self.assertFalse(SubscriptionService.is_pro_active(other_user_id))

    def test_mismatched_duplicate_different_order_is_rejected(self):
        PaymentService.process_verified_payment(
            self.user_id, "order_1", "pay_mismatch_order", "pro"
        )

        with self.assertRaises(DuplicatePaymentError):
            PaymentService.process_verified_payment(
                self.user_id, "order_2", "pay_mismatch_order", "pro"
            )

        self.assertEqual(_payments_count("pay_mismatch_order"), 1)

    def test_concurrent_identical_verification_all_succeed_idempotently(self):
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

        # Every caller supplied the exact same (user, order, plan) for this
        # payment_id, so every caller must succeed idempotently — only the
        # winner of the INSERT race does real work; everyone else resolves
        # against that same row.
        self.assertEqual(results.count("success"), 10)
        self.assertEqual(results.count("duplicate"), 0)
        self.assertEqual(_payments_count("pay_4"), 1)

    def test_concurrent_mismatched_verification_only_one_user_succeeds(self):
        # Six different (user, order) pairs race for the same payment_id —
        # simulates one legitimate caller plus five attempts to attach an
        # already-captured payment_id to a different user/order. Whichever
        # one wins the underlying INSERT race is non-deterministic, but the
        # invariant that must hold regardless of who wins is: exactly one
        # payments row, exactly one caller sees success, and PRO entitlement
        # is granted to that one winner's user_id only — never to more than
        # one identity for the same real-world payment.
        candidates = [
            (self.user_id, "order_legit")
        ] + [
            (_create_user(f"concurrent-other-{i}@test.com"), f"order_attack_{i}")
            for i in range(5)
        ]
        results = {}
        results_lock = threading.Lock()

        def attempt(user_id, order_id):
            try:
                PaymentService.process_verified_payment(
                    user_id, order_id, "pay_race_mismatch", "pro"
                )
                outcome = "success"
            except DuplicatePaymentError:
                outcome = "duplicate"

            with results_lock:
                results[user_id] = outcome

        threads = [
            threading.Thread(target=attempt, args=(user_id, order_id))
            for user_id, order_id in candidates
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        self.assertEqual(_payments_count("pay_race_mismatch"), 1)

        winners = [uid for uid, outcome in results.items() if outcome == "success"]
        losers = [uid for uid, outcome in results.items() if outcome == "duplicate"]

        self.assertEqual(len(winners), 1)
        self.assertEqual(len(losers), 5)
        self.assertTrue(SubscriptionService.is_pro_active(winners[0]))
        for user_id in losers:
            self.assertFalse(SubscriptionService.is_pro_active(user_id))

    def test_non_duplicate_integrity_error_raises_processing_error(self):
        # A FOREIGN KEY violation on user_id is a real sqlite3.IntegrityError
        # that has nothing to do with the razorpay_payment_id UNIQUE
        # constraint. The re-read after the exception correctly finds no
        # row for this payment_id, and that must surface as a clean
        # PaymentProcessingError instead of crashing inside
        # _resolve_existing_payment(None, ...).
        nonexistent_user_id = 999999

        with patch.object(
            MonitoringEventService, "record_failure"
        ) as mock_record_failure:
            with self.assertRaises(PaymentProcessingError):
                PaymentService.process_verified_payment(
                    nonexistent_user_id, "order_fk", "pay_fk", "pro"
                )

        self.assertEqual(_payments_count("pay_fk"), 0)
        mock_record_failure.assert_called_with(
            MonitoringEventService.PAYMENT, "processing_failed"
        )

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

    def test_verify_endpoint_idempotent_retry_returns_200(self):
        # Simulates the browser retrying /payments/verify (or double-firing
        # the request) for a payment the webhook, or an earlier call, has
        # already fully processed — must succeed with 200, not 409.
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
            second_response = payments_router.verify_payment(body, current_user)

        self.assertTrue(first_response["success"])
        self.assertEqual(first_response["plan"], SubscriptionPlan.PRO)
        self.assertTrue(second_response["success"])
        self.assertEqual(second_response["plan"], SubscriptionPlan.PRO)
        self.assertEqual(second_response["status"], SubscriptionStatus.ACTIVE)
        self.assertEqual(_payments_count("pay_x"), 1)

    def test_verify_endpoint_rejects_mismatched_duplicate_with_409(self):
        # Same razorpay_payment_id but a different order_id than the one it
        # was originally processed under — must stay rejected.
        first_body = payments_router.VerifyPaymentRequest(
            razorpay_order_id="order_y1",
            razorpay_payment_id="pay_y",
            razorpay_signature="sig_y",
        )
        second_body = payments_router.VerifyPaymentRequest(
            razorpay_order_id="order_y2",
            razorpay_payment_id="pay_y",
            razorpay_signature="sig_y",
        )
        current_user = {"id": self.user_id}

        with patch.object(
            payments_router.PaymentService,
            "verify_payment",
            return_value=None
        ):
            payments_router.verify_payment(first_body, current_user)

            with self.assertRaises(HTTPException) as ctx:
                payments_router.verify_payment(second_body, current_user)

        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(_payments_count("pay_y"), 1)


if __name__ == "__main__":
    unittest.main()
