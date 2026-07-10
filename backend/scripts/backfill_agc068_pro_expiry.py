"""
AGC-068 follow-up: one-time backfill for existing PRO subscriptions that
predate expiry enforcement and were left with expires_at = NULL.

Sets expires_at = started_at + PRO_SUBSCRIPTION_DURATION_DAYS for every
row matching plan='PRO' AND expires_at IS NULL. started_at is the
timestamp SubscriptionService already refreshes on every upgrade_to_pro /
upgrade_to_pro_in_transaction call, so it reflects each user's actual
most recent PRO activation — the same quantity newly-created PRO rows
already use to compute their expiry.

Idempotent: rerunning is a no-op once every matching row has been updated,
because the WHERE clause requires expires_at IS NULL.

Usage (run once, from backend/):
    python scripts/backfill_agc068_pro_expiry.py            # dry run (default)
    python scripts/backfill_agc068_pro_expiry.py --apply     # apply the update
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.database_service import DatabaseService  # noqa: E402
from app.services.subscription_service import (  # noqa: E402
    SubscriptionPlan,
    SubscriptionService,
)


def main() -> None:
    apply = "--apply" in sys.argv[1:]

    connection = DatabaseService.get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT user_id, started_at
        FROM subscriptions
        WHERE plan = ?
          AND expires_at IS NULL
        """,
        (SubscriptionPlan.PRO,)
    )

    rows = cursor.fetchall()

    if not rows:
        print("No PRO subscriptions with expires_at IS NULL found. Nothing to do.")
        connection.close()
        return

    print(f"Found {len(rows)} PRO subscription(s) with expires_at IS NULL:")

    updates = []
    for user_id, started_at in rows:
        started = datetime.fromisoformat(started_at)
        expires_at = SubscriptionService._compute_pro_expiry(started)
        updates.append((expires_at, user_id))
        print(f"  user_id={user_id} started_at={started_at} -> expires_at={expires_at}")

    if not apply:
        print("\nDry run only — no rows changed. Re-run with --apply to commit.")
        connection.close()
        return

    cursor.executemany(
        """
        UPDATE subscriptions
        SET expires_at = ?
        WHERE user_id = ?
          AND plan = 'PRO'
          AND expires_at IS NULL
        """,
        updates
    )

    connection.commit()
    print(f"\nUpdated {cursor.rowcount if cursor.rowcount >= 0 else len(updates)} row(s).")
    connection.close()


if __name__ == "__main__":
    main()
