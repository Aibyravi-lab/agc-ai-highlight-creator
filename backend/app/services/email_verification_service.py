import hashlib
import secrets
from datetime import datetime, timedelta

from app.config.config import settings
from app.services.auth_service import AuthService
from app.services.database_service import DatabaseService
from app.services.email_service import EmailService


class EmailVerificationService:
    """
    AGC-070: email verification tokens. Reuses the exact token pattern
    already proven by PasswordResetService (secrets.token_urlsafe(32),
    sha256 hash stored at rest, expiry, atomic single-use consumption) but
    against its own email_verifications table, so the hardened password
    reset flow is never touched.
    """

    @staticmethod
    def _hash_token(
        token: str
    ) -> str:

        return hashlib.sha256(
            token.encode("utf-8")
        ).hexdigest()

    @classmethod
    def send_verification_email(
        cls,
        user_id: int,
        email: str
    ) -> None:

        token = secrets.token_urlsafe(32)

        token_hash = cls._hash_token(token)

        now = datetime.utcnow()

        expires_at = now + timedelta(
            minutes=settings.EMAIL_VERIFICATION_TOKEN_EXPIRY_MINUTES
        )

        connection = DatabaseService.get_connection()

        cursor = connection.cursor()

        # Invalidate previous unused tokens for this user before issuing a new one.
        cursor.execute(
            """
            UPDATE email_verifications
            SET used = 1
            WHERE user_id = ? AND used = 0
            """,
            (user_id,)
        )

        cursor.execute(
            """
            INSERT INTO email_verifications (
                user_id, token_hash, created_at, expires_at, used
            )
            VALUES (?, ?, ?, ?, 0)
            """,
            (
                user_id,
                token_hash,
                now.isoformat(),
                expires_at.isoformat()
            )
        )

        connection.commit()

        connection.close()

        verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"

        EmailService.send_verification_email(
            email,
            verify_url
        )

    @classmethod
    def verify(
        cls,
        token: str
    ) -> bool:

        token_hash = cls._hash_token(token)

        now_iso = datetime.utcnow().isoformat()

        connection = DatabaseService.get_connection()

        cursor = connection.cursor()

        # Atomic consumption: only one caller can flip used 0 -> 1 for a
        # given token, so a concurrent replay attempt sees rowcount == 0
        # and is rejected. Same approach as PasswordResetService.reset_password.
        cursor.execute(
            """
            UPDATE email_verifications
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
            FROM email_verifications
            WHERE token_hash = ?
            """,
            (token_hash,)
        )

        user_id = cursor.fetchone()[0]

        cursor.execute(
            """
            UPDATE users
            SET email_verified = 1
            WHERE id = ?
            """,
            (user_id,)
        )

        connection.commit()

        connection.close()

        return True

    @classmethod
    def resend(
        cls,
        email: str
    ) -> None:
        """
        Runs entirely inside a background task, mirroring
        PasswordResetService.request_reset: the router always returns the
        same generic response before this executes, so nothing here —
        including how long it takes — can be observed by the caller.
        """

        user = AuthService.get_user_by_email(email)

        if not user:

            return

        if user["email_verified"]:

            return

        cls.send_verification_email(
            user["id"],
            user["email"]
        )
