import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from app.config.config import settings
from app.services.auth_service import AuthService
from app.services.database_service import DatabaseService
from app.services.email_service import EmailService
from app.services.logger_service import LoggerService


class PasswordResetService:

    @staticmethod
    def _hash_token(
        token: str
    ) -> str:

        return hashlib.sha256(
            token.encode("utf-8")
        ).hexdigest()

    @classmethod
    def _is_throttled(
        cls,
        user_id: int
    ) -> bool:

        now = datetime.utcnow()

        connection = DatabaseService.get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT created_at
            FROM password_resets
            WHERE user_id = ?
              AND created_at > ?
            ORDER BY created_at DESC
            """,
            (
                user_id,
                (now - timedelta(hours=1)).isoformat()
            )
        )

        recent = cursor.fetchall()

        connection.close()

        if len(recent) >= settings.PASSWORD_RESET_MAX_PER_HOUR:

            return True

        if recent:

            last_created = datetime.fromisoformat(recent[0][0])

            if (now - last_created) < timedelta(
                seconds=settings.PASSWORD_RESET_COOLDOWN_SECONDS
            ):

                return True

        return False

    @classmethod
    def request_reset(
        cls,
        email: str
    ) -> None:
        """
        Runs entirely inside a background task: the router always returns
        the same generic response before this executes, so nothing here —
        including how long it takes — can be observed by the caller. Every
        branch (unknown email, throttled, issued) must return the same way:
        silently.
        """

        user = AuthService.get_user_by_email(email)

        if not user:

            return

        if cls._is_throttled(user["id"]):

            LoggerService.info(
                f"Password reset throttled for user_id={user['id']}"
            )

            return

        token = secrets.token_urlsafe(32)

        token_hash = cls._hash_token(token)

        now = datetime.utcnow()

        expires_at = now + timedelta(
            minutes=settings.PASSWORD_RESET_TOKEN_EXPIRY_MINUTES
        )

        connection = DatabaseService.get_connection()

        cursor = connection.cursor()

        # Invalidate previous unused tokens for this user before issuing a new one.
        cursor.execute(
            """
            UPDATE password_resets
            SET used = 1
            WHERE user_id = ? AND used = 0
            """,
            (user["id"],)
        )

        cursor.execute(
            """
            INSERT INTO password_resets (
                user_id, token_hash, created_at, expires_at, used
            )
            VALUES (?, ?, ?, ?, 0)
            """,
            (
                user["id"],
                token_hash,
                now.isoformat(),
                expires_at.isoformat()
            )
        )

        connection.commit()

        connection.close()

        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"

        EmailService.send_password_reset_email(
            user["email"],
            reset_url
        )

    @classmethod
    def reset_password(
        cls,
        token: str,
        new_password: str
    ) -> bool:

        token_hash = cls._hash_token(token)

        now_iso = datetime.utcnow().isoformat()

        connection = DatabaseService.get_connection()

        cursor = connection.cursor()

        # Atomic consumption: only one caller can flip used 0 -> 1 for a
        # given token. SQLite serializes writers, so a concurrent replay
        # attempt sees rowcount == 0 and is rejected.
        cursor.execute(
            """
            UPDATE password_resets
            SET used = 1
            WHERE token_hash = ? AND used = 0 AND expires_at > ?
            """,
            (token_hash, now_iso)
        )

        connection.commit()

        if cursor.rowcount != 1:

            connection.close()

            return False

        cursor.execute(
            """
            SELECT user_id
            FROM password_resets
            WHERE token_hash = ?
            """,
            (token_hash,)
        )

        user_id = cursor.fetchone()[0]

        password_hash = AuthService.hash_password(new_password)

        cursor.execute(
            """
            UPDATE users
            SET password_hash = ?
            WHERE id = ?
            """,
            (password_hash, user_id)
        )

        # Invalidate all remaining tokens for this user after a successful reset.
        cursor.execute(
            """
            UPDATE password_resets
            SET used = 1
            WHERE user_id = ? AND used = 0
            """,
            (user_id,)
        )

        connection.commit()

        connection.close()

        return True
