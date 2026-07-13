"""
VED-085: grants or revokes Mission Control admin access for a user.

There is deliberately no HTTP endpoint to toggle is_admin (same posture as
scripts/maintenance.sh: privileged state changes happen over SSH/local
shell access, not through the public API surface).

Usage (run from backend/):
    python scripts/grant_admin.py founder@example.com            # dry run (default)
    python scripts/grant_admin.py founder@example.com --apply    # grant admin
    python scripts/grant_admin.py founder@example.com --revoke --apply
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
        print("Usage: python scripts/grant_admin.py <email> [--apply] [--revoke]")
        sys.exit(1)

    email = emails[0]
    user = AuthService.get_user_by_email(email)

    if not user:
        print(f"No user found for email: {email}")
        sys.exit(1)

    target_value = 0 if revoke else 1
    action = "Revoke" if revoke else "Grant"

    print(
        f"{action} admin access for user_id={user['id']} email={user['email']} "
        f"(currently is_admin={user['is_admin']})"
    )

    if not apply:
        print("\nDry run only — no rows changed. Re-run with --apply to commit.")
        return

    connection = DatabaseService.get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "UPDATE users SET is_admin = ? WHERE id = ?",
        (target_value, user["id"]),
    )

    connection.commit()
    connection.close()

    print(f"Done. user_id={user['id']} is_admin={target_value}")


if __name__ == "__main__":
    main()
