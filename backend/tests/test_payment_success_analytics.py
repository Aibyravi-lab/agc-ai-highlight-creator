"""VED-ANALYTICS-003: reliable, exactly-once "Payment Success" analytics.

PostHog was missing "Payment Success" against real processed payments because
the only emission was frontend/app/pricing/page.tsx's track("Payment
Success"), fired after the browser-side subscription refresh succeeded — an
extra step past the actual money-moving event that could fail or never run
(closed tab, network drop) even though Razorpay had already captured the
payment. The fix moves emission to PaymentService.process_verified_payment(),
the single place a *new* payments row is created — guarded by the existing
razorpay_payment_id UNIQUE constraint (see PaymentService's own class
docstring on WEBHOOK_EVENT_PAYMENT_CAPTURED) so the event can only ever fire
once per real-world payment, no matter how many times /payments/verify, the
webhook, or reconciliation attempt to process it.

Covers:
  A) PaymentSuccessAnalyticsTests — direct process_verified_payment()
     exactly-once behavior (first call, duplicate retry, mismatched
     duplicate, concurrent race).
  B) AnalyticsServiceTests — AnalyticsService.capture_payment_success itself:
     config safety, payload shape, network failure containment.
"""

import tempfile
import threading
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from app.services.analytics_service import AnalyticsService
from app.services.database_service import DatabaseService
from app.services.payment_service import DuplicatePaymentError, PaymentService
from app.services.subscription_service import SubscriptionService


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


# ---------------------------------------------------------------------------
# A) process_verified_payment() exactly-once analytics behavior
# ---------------------------------------------------------------------------

class PaymentSuccessAnalyticsTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = _make_isolated_db()
        self.addCleanup(self._tmp_dir.cleanup)

        self.user_id = _create_user("analytics-payment@test.com")

        self._capture_patch = patch(
            "app.services.payment_service.AnalyticsService.capture_payment_success"
        )
        self.mock_capture = self._capture_patch.start()
        self.addCleanup(self._capture_patch.stop)

    def test_first_successful_payment_emits_exactly_once(self):
        PaymentService.process_verified_payment(
            self.user_id, "order_1", "pay_1", "pro"
        )

        self.mock_capture.assert_called_once_with(
            user_id=self.user_id, plan="pro", payment_id="pay_1"
        )

    def test_duplicate_verify_request_does_not_emit_a_second_event(self):
        # Same (user, order, plan) as the first call — e.g. the browser
        # retrying /payments/verify for a payment the webhook already
        # processed. Must succeed idempotently without a second event.
        PaymentService.process_verified_payment(
            self.user_id, "order_1", "pay_2", "pro"
        )
        PaymentService.process_verified_payment(
            self.user_id, "order_1", "pay_2", "pro"
        )

        self.mock_capture.assert_called_once_with(
            user_id=self.user_id, plan="pro", payment_id="pay_2"
        )

    def test_webhook_then_browser_race_does_not_duplicate(self):
        # Simulates the webhook and the browser-driven /payments/verify path
        # both resolving the same real payment.
        PaymentService.process_verified_payment(
            self.user_id, "order_1", "pay_3", "pro"
        )
        PaymentService.process_verified_payment(
            self.user_id, "order_1", "pay_3", "pro"
        )

        self.assertEqual(self.mock_capture.call_count, 1)

    def test_mismatched_duplicate_does_not_emit(self):
        other_user_id = _create_user("analytics-other@test.com")

        PaymentService.process_verified_payment(
            self.user_id, "order_1", "pay_mismatch", "pro"
        )
        self.mock_capture.reset_mock()

        with self.assertRaises(DuplicatePaymentError):
            PaymentService.process_verified_payment(
                other_user_id, "order_2", "pay_mismatch", "pro"
            )

        self.mock_capture.assert_not_called()

    def test_concurrent_duplicate_processing_emits_exactly_once(self):
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

            with results_lock:
                results.append(outcome)

        threads = [threading.Thread(target=attempt) for _ in range(10)]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(results.count("success"), 10)
        self.mock_capture.assert_called_once_with(
            user_id=self.user_id, plan="pro", payment_id="pay_4"
        )

    def test_analytics_failure_does_not_fail_payment_processing(self):
        self.mock_capture.side_effect = RuntimeError("PostHog unreachable")

        # Must not raise — the payment is already committed by this point.
        subscription = PaymentService.process_verified_payment(
            self.user_id, "order_5", "pay_5", "pro"
        )

        self.assertEqual(subscription["plan"], "PRO")
        self.assertTrue(SubscriptionService.is_pro_active(self.user_id))


# ---------------------------------------------------------------------------
# B) process_verified_payment() with a real (unpatched) AnalyticsService,
#    proving missing PostHog config never affects payment success
# ---------------------------------------------------------------------------

class PaymentSuccessMissingConfigTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = _make_isolated_db()
        self.addCleanup(self._tmp_dir.cleanup)

        self.user_id = _create_user("analytics-noconfig@test.com")

    def test_missing_posthog_config_payment_still_succeeds(self):
        from app.config.config import settings

        with patch.object(settings, "POSTHOG_API_KEY", ""), \
             patch.object(settings, "POSTHOG_HOST", ""), \
             patch("app.services.analytics_service.requests.post") as mock_post:

            subscription = PaymentService.process_verified_payment(
                self.user_id, "order_6", "pay_6", "pro"
            )

        self.assertEqual(subscription["plan"], "PRO")
        self.assertTrue(SubscriptionService.is_pro_active(self.user_id))
        mock_post.assert_not_called()


# ---------------------------------------------------------------------------
# C) AnalyticsService.capture_payment_success — config, payload, failures
# ---------------------------------------------------------------------------

class AnalyticsServiceTests(unittest.TestCase):

    def setUp(self):
        from app.config.config import settings
        self.settings = settings

    def test_missing_api_key_is_a_safe_noop(self):
        with patch.object(self.settings, "POSTHOG_API_KEY", ""), \
             patch.object(self.settings, "POSTHOG_HOST", "https://app.posthog.com"), \
             patch("app.services.analytics_service.requests.post") as mock_post:

            AnalyticsService.capture_payment_success(
                user_id=1, plan="pro", payment_id="pay_x"
            )

            mock_post.assert_not_called()

    def test_missing_host_is_a_safe_noop(self):
        with patch.object(self.settings, "POSTHOG_API_KEY", "phc_test"), \
             patch.object(self.settings, "POSTHOG_HOST", ""), \
             patch("app.services.analytics_service.requests.post") as mock_post:

            AnalyticsService.capture_payment_success(
                user_id=1, plan="pro", payment_id="pay_x"
            )

            mock_post.assert_not_called()

    def test_capture_sends_correct_event_name_and_safe_properties(self):
        with patch.object(self.settings, "POSTHOG_API_KEY", "phc_test"), \
             patch.object(self.settings, "POSTHOG_HOST", "https://app.posthog.com"), \
             patch("app.services.analytics_service.requests.post") as mock_post:

            AnalyticsService._send_payment_success(
                user_id=99, plan="pro", payment_id="pay_secret_123"
            )

            mock_post.assert_called_once()
            url, kwargs = mock_post.call_args[0], mock_post.call_args[1]
            self.assertEqual(url[0], "https://app.posthog.com/capture/")

            payload = kwargs["json"]
            self.assertEqual(payload["api_key"], "phc_test")
            self.assertEqual(payload["event"], "Payment Success")
            self.assertEqual(payload["distinct_id"], "99")
            self.assertEqual(payload["properties"]["plan"], "pro")
            self.assertEqual(kwargs["timeout"], AnalyticsService.CAPTURE_TIMEOUT_SECONDS)

            # No payment_id, order_id, signature, or email anywhere in the
            # outgoing payload — only a safe, deterministic plan string.
            self.assertNotIn("payment_id", payload["properties"])
            self.assertNotIn("order_id", payload["properties"])
            self.assertNotIn("signature", str(payload).lower())
            self.assertNotIn("email", str(payload).lower())

    def test_network_failure_is_caught_and_does_not_raise(self):
        with patch.object(self.settings, "POSTHOG_API_KEY", "phc_test"), \
             patch.object(self.settings, "POSTHOG_HOST", "https://app.posthog.com"), \
             patch(
                 "app.services.analytics_service.requests.post",
                 side_effect=ConnectionError("network unreachable")
             ):

            # Must not raise.
            AnalyticsService._send_payment_success(
                user_id=1, plan="pro", payment_id="pay_w"
            )


if __name__ == "__main__":
    unittest.main()
