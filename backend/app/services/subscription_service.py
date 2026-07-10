from datetime import datetime, timedelta
from typing import Optional

from app.services.database_service import DatabaseService


class SubscriptionPlan:
    FREE = "FREE"
    PRO = "PRO"


class SubscriptionStatus:
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class SubscriptionService:

    # Razorpay's PRO plan (PaymentService.PLAN_PRICING) bills monthly, so a
    # successful upgrade grants 30 days of PRO access before it lapses.
    PRO_SUBSCRIPTION_DURATION_DAYS = 30

    @staticmethod
    def _row_factory(cursor, row):
        return {
            col[0]: row[idx]
            for idx, col in enumerate(cursor.description)
        }

    @classmethod
    def create_default_subscription(
        cls,
        user_id: int
    ) -> dict:

        now = datetime.utcnow().isoformat()

        connection = DatabaseService.get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT OR IGNORE INTO subscriptions (
                user_id, plan, status, started_at, expires_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                SubscriptionPlan.FREE,
                SubscriptionStatus.ACTIVE,
                now,
                None,
                now,
                now,
            )
        )

        connection.commit()

        connection.close()

        return cls.get_by_user_id(user_id)

    @classmethod
    def get_by_user_id(
        cls,
        user_id: int
    ) -> Optional[dict]:
        # Single read path for subscription state (used by is_pro_active and
        # GET /subscription/me), so expiry enforcement lives here: a PRO row
        # whose expires_at has passed is downgraded to FREE/EXPIRED before
        # being returned. The UPDATE's WHERE clause (plan = PRO AND
        # expires_at <= now) makes the downgrade idempotent and safe under
        # concurrent requests — once one request flips the row to FREE, the
        # same UPDATE is a no-op for every other in-flight request.

        now = datetime.utcnow().isoformat()

        connection = DatabaseService.get_connection()

        connection.row_factory = cls._row_factory

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE subscriptions
            SET plan = ?,
                status = ?,
                updated_at = ?
            WHERE user_id = ?
              AND plan = ?
              AND expires_at IS NOT NULL
              AND expires_at <= ?
            """,
            (
                SubscriptionPlan.FREE,
                SubscriptionStatus.EXPIRED,
                now,
                user_id,
                SubscriptionPlan.PRO,
                now,
            )
        )

        cursor.execute(
            """
            SELECT
                id,
                user_id,
                plan,
                status,
                started_at,
                expires_at,
                created_at,
                updated_at
            FROM subscriptions
            WHERE user_id = ?
            """,
            (user_id,)
        )

        subscription = cursor.fetchone()

        connection.commit()

        connection.close()

        return subscription

    @classmethod
    def _compute_pro_expiry(cls, now: datetime) -> str:

        return (
            now + timedelta(days=cls.PRO_SUBSCRIPTION_DURATION_DAYS)
        ).isoformat()

    @classmethod
    def upgrade_to_pro(
        cls,
        user_id: int
    ) -> dict:

        now = datetime.utcnow()
        now_iso = now.isoformat()
        expires_at = cls._compute_pro_expiry(now)

        connection = DatabaseService.get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE subscriptions
            SET plan = ?,
                status = ?,
                started_at = ?,
                expires_at = ?,
                updated_at = ?
            WHERE user_id = ?
            """,
            (
                SubscriptionPlan.PRO,
                SubscriptionStatus.ACTIVE,
                now_iso,
                expires_at,
                now_iso,
                user_id,
            )
        )

        connection.commit()

        upgraded = cursor.rowcount > 0

        connection.close()

        if not upgraded:
            # No pre-existing row (predates the subscriptions table and
            # somehow missed the backfill) — create the PRO row directly.
            connection = DatabaseService.get_connection()

            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO subscriptions (
                    user_id, plan, status, started_at, expires_at, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    SubscriptionPlan.PRO,
                    SubscriptionStatus.ACTIVE,
                    now_iso,
                    expires_at,
                    now_iso,
                    now_iso,
                )
            )

            connection.commit()

            connection.close()

        return cls.get_by_user_id(user_id)

    @classmethod
    def upgrade_to_pro_in_transaction(
        cls,
        connection,
        user_id: int
    ) -> None:
        # Same as upgrade_to_pro, but runs on a caller-owned connection so
        # it commits atomically with the caller's other writes.

        now = datetime.utcnow()
        now_iso = now.isoformat()
        expires_at = cls._compute_pro_expiry(now)

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE subscriptions
            SET plan = ?,
                status = ?,
                started_at = ?,
                expires_at = ?,
                updated_at = ?
            WHERE user_id = ?
            """,
            (
                SubscriptionPlan.PRO,
                SubscriptionStatus.ACTIVE,
                now_iso,
                expires_at,
                now_iso,
                user_id,
            )
        )

        if cursor.rowcount == 0:
            # No pre-existing row (predates the subscriptions table and
            # somehow missed the backfill) — create the PRO row directly.
            cursor.execute(
                """
                INSERT INTO subscriptions (
                    user_id, plan, status, started_at, expires_at, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    SubscriptionPlan.PRO,
                    SubscriptionStatus.ACTIVE,
                    now_iso,
                    expires_at,
                    now_iso,
                    now_iso,
                )
            )

    @classmethod
    def is_pro_active(
        cls,
        user_id: int
    ) -> bool:

        subscription = cls.get_by_user_id(user_id)

        return (
            subscription is not None
            and subscription["plan"] == SubscriptionPlan.PRO
            and subscription["status"] == SubscriptionStatus.ACTIVE
        )
