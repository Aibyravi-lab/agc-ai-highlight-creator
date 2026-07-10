import tempfile
import threading
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from app.services.database_service import DatabaseService
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


def _force_subscription_state(
    user_id: int,
    plan: str,
    status: str,
    expires_at: str | None,
) -> None:
    # Bypasses SubscriptionService writers to plant a specific row shape
    # (in particular a past expires_at) that upgrade_to_pro would never
    # produce on its own, so tests can exercise the expiry check directly.
    connection = DatabaseService.get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE subscriptions
        SET plan = ?, status = ?, expires_at = ?
        WHERE user_id = ?
        """,
        (plan, status, expires_at, user_id)
    )

    connection.commit()
    connection.close()


def _payments_count(user_id: int) -> int:
    connection = DatabaseService.get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM payments WHERE user_id = ?",
        (user_id,)
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


class SubscriptionExpiryTests(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = _make_isolated_db()
        self.user_id = _create_user("expiry@test.com")

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_active_pro_remains_pro(self):
        future = (
            datetime.utcnow() + timedelta(days=10)
        ).isoformat()

        _force_subscription_state(
            self.user_id, SubscriptionPlan.PRO, SubscriptionStatus.ACTIVE, future
        )

        subscription = SubscriptionService.get_by_user_id(self.user_id)

        self.assertEqual(subscription["plan"], SubscriptionPlan.PRO)
        self.assertEqual(subscription["status"], SubscriptionStatus.ACTIVE)
        self.assertTrue(SubscriptionService.is_pro_active(self.user_id))

    def test_expired_pro_becomes_free(self):
        past = (
            datetime.utcnow() - timedelta(days=1)
        ).isoformat()

        _force_subscription_state(
            self.user_id, SubscriptionPlan.PRO, SubscriptionStatus.ACTIVE, past
        )

        subscription = SubscriptionService.get_by_user_id(self.user_id)

        self.assertEqual(subscription["plan"], SubscriptionPlan.FREE)
        self.assertEqual(subscription["status"], SubscriptionStatus.EXPIRED)

    def test_expired_pro_loses_unlimited_access(self):
        past = (
            datetime.utcnow() - timedelta(days=1)
        ).isoformat()

        _force_subscription_state(
            self.user_id, SubscriptionPlan.PRO, SubscriptionStatus.ACTIVE, past
        )

        self.assertFalse(SubscriptionService.is_pro_active(self.user_id))

    def test_historical_payments_remain_intact_after_expiry(self):
        past = (
            datetime.utcnow() - timedelta(days=1)
        ).isoformat()

        connection = DatabaseService.get_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO payments (
                user_id, razorpay_order_id, razorpay_payment_id,
                plan, status, created_at, processed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self.user_id, "order_hist", "pay_hist", "pro",
                "PROCESSED", past, past
            )
        )
        connection.commit()
        connection.close()

        _force_subscription_state(
            self.user_id, SubscriptionPlan.PRO, SubscriptionStatus.ACTIVE, past
        )

        SubscriptionService.get_by_user_id(self.user_id)

        self.assertEqual(_payments_count(self.user_id), 1)

    def test_downgrade_does_not_grant_free_credits(self):
        past = (
            datetime.utcnow() - timedelta(days=1)
        ).isoformat()

        _force_subscription_state(
            self.user_id, SubscriptionPlan.PRO, SubscriptionStatus.ACTIVE, past
        )

        credits_before = _credits_remaining(self.user_id)

        SubscriptionService.get_by_user_id(self.user_id)

        self.assertEqual(_credits_remaining(self.user_id), credits_before)

    def test_downgrade_happens_only_once(self):
        past = (
            datetime.utcnow() - timedelta(days=1)
        ).isoformat()

        _force_subscription_state(
            self.user_id, SubscriptionPlan.PRO, SubscriptionStatus.ACTIVE, past
        )

        first = SubscriptionService.get_by_user_id(self.user_id)
        updated_at_after_first = first["updated_at"]

        second = SubscriptionService.get_by_user_id(self.user_id)

        self.assertEqual(second["plan"], SubscriptionPlan.FREE)
        self.assertEqual(second["status"], SubscriptionStatus.EXPIRED)
        # Second call finds plan already FREE, so the conditional UPDATE's
        # WHERE clause (plan = PRO) no longer matches — updated_at is left
        # untouched, proving the downgrade only fires once.
        self.assertEqual(second["updated_at"], updated_at_after_first)

    def test_free_users_unaffected(self):
        subscription_before = SubscriptionService.get_by_user_id(self.user_id)
        self.assertEqual(subscription_before["plan"], SubscriptionPlan.FREE)
        self.assertEqual(subscription_before["status"], SubscriptionStatus.ACTIVE)

        subscription_after = SubscriptionService.get_by_user_id(self.user_id)

        self.assertEqual(subscription_after["plan"], SubscriptionPlan.FREE)
        self.assertEqual(subscription_after["status"], SubscriptionStatus.ACTIVE)
        self.assertIsNone(subscription_after["expires_at"])

    def test_expiry_exactly_equal_to_current_time_is_expired(self):
        now = datetime.utcnow().isoformat()

        _force_subscription_state(
            self.user_id, SubscriptionPlan.PRO, SubscriptionStatus.ACTIVE, now
        )

        subscription = SubscriptionService.get_by_user_id(self.user_id)

        self.assertEqual(subscription["plan"], SubscriptionPlan.FREE)
        self.assertEqual(subscription["status"], SubscriptionStatus.EXPIRED)

    def test_concurrent_requests_produce_consistent_state(self):
        past = (
            datetime.utcnow() - timedelta(days=1)
        ).isoformat()

        _force_subscription_state(
            self.user_id, SubscriptionPlan.PRO, SubscriptionStatus.ACTIVE, past
        )

        results = []
        results_lock = threading.Lock()

        def attempt():
            subscription = SubscriptionService.get_by_user_id(self.user_id)
            with results_lock:
                results.append(subscription["plan"])

        threads = [threading.Thread(target=attempt) for _ in range(10)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        self.assertTrue(
            all(plan == SubscriptionPlan.FREE for plan in results)
        )

        final = SubscriptionService.get_by_user_id(self.user_id)
        self.assertEqual(final["plan"], SubscriptionPlan.FREE)
        self.assertEqual(final["status"], SubscriptionStatus.EXPIRED)

    def test_upgrade_to_pro_sets_thirty_day_expiry(self):
        subscription = SubscriptionService.upgrade_to_pro(self.user_id)

        self.assertEqual(subscription["plan"], SubscriptionPlan.PRO)
        self.assertIsNotNone(subscription["expires_at"])

        expires_at = datetime.fromisoformat(subscription["expires_at"])
        started_at = datetime.fromisoformat(subscription["started_at"])
        delta = expires_at - started_at

        self.assertEqual(delta.days, SubscriptionService.PRO_SUBSCRIPTION_DURATION_DAYS)


if __name__ == "__main__":
    unittest.main()
