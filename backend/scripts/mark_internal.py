"""
GROW-005.2: marks or unmarks a user account as internal/test activity so
Mission Control growth analytics (user funnel, feedback summary, credit/job
distribution) exclude it. Every job, project, and feedback row already
attributed to this user's account is excluded automatically as a result —
there is nothing else to reclassify.

This does NOT touch is_admin (Mission Control dashboard access), payment/
subscription entitlements, or authentication. It only affects which rows
count toward external growth metrics.

Same posture as scripts/grant_admin.py: no HTTP endpoint exists to toggle
this — privileged data classification happens over SSH/local shell access,
not through the public API surface. Exact email match only; no bulk or
domain-based classification.

Usage (run from backend/):
    python scripts/mark_internal.py founder@example.com            # dry run (default)
    python scripts/mark_internal.py founder@example.com --apply    # mark internal
    python scripts/mark_internal.py founder@example.com --revoke --apply
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.auth_service import AuthService  # noqa: E402
from app.services.database_service import DatabaseService  # noqa: E402


def main() -> None:
    args = sys.argv[1:]
    apply = "--apply" in args
    revoke = "--revoke" in args
    emails = [a for a in args if not a.startswith("--")]

    if len(emails) != 1:
        print("Usage: python scripts/mark_internal.py <email> [--apply] [--revoke]")
        sys.exit(1)

    email = emails[0]
    user = AuthService.get_user_by_email(email)

    if not user:
        print(f"No user found for email: {email}")
        sys.exit(1)

    target_value = 0 if revoke else 1
    action = "Unmark" if revoke else "Mark"

    print(
        f"{action} internal/test for user_id={user['id']} email={user['email']} "
        f"(currently is_internal={user['is_internal']})"
    )

    if not apply:
        print("\nDry run only — no rows changed. Re-run with --apply to commit.")
        return

    connection = DatabaseService.get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "UPDATE users SET is_internal = ? WHERE id = ?",
        (target_value, user["id"]),
    )

    affected = cursor.rowcount
    connection.commit()
    connection.close()

    print(f"Done. user_id={user['id']} is_internal={target_value} (rows affected: {affected})")


if __name__ == "__main__":
    main()
