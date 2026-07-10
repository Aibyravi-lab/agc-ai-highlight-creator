from datetime import datetime
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

        connection = DatabaseService.get_connection()

        connection.row_factory = cls._row_factory

        cursor = connection.cursor()

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

        connection.close()

        return subscription

    @classmethod
    def upgrade_to_pro(
        cls,
        user_id: int
    ) -> dict:

        now = datetime.utcnow().isoformat()

        connection = DatabaseService.get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE subscriptions
            SET plan = ?,
                status = ?,
                started_at = ?,
                expires_at = NULL,
                updated_at = ?
            WHERE user_id = ?
            """,
            (
                SubscriptionPlan.PRO,
                SubscriptionStatus.ACTIVE,
                now,
                now,
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
    def upgrade_to_pro_in_transaction(
        cls,
        connection,
        user_id: int
    ) -> None:
        # Same as upgrade_to_pro, but runs on a caller-owned connection so
        # it commits atomically with the caller's other writes.

        now = datetime.utcnow().isoformat()

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE subscriptions
            SET plan = ?,
                status = ?,
                started_at = ?,
                expires_at = NULL,
                updated_at = ?
            WHERE user_id = ?
            """,
            (
                SubscriptionPlan.PRO,
                SubscriptionStatus.ACTIVE,
                now,
                now,
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
                    now,
                    None,
                    now,
                    now,
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
