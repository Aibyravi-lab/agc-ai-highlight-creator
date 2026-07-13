import bcrypt
from datetime import datetime, timedelta
from typing import Optional

from jose import jwt, JWTError

from app.config.config import settings
from app.services.database_service import DatabaseService
from app.services.subscription_service import SubscriptionService


class AuthService:

    @staticmethod
    def normalize_email(
        email: str
    ) -> str:

        return email.strip().lower()

    @staticmethod
    def validate_password_strength(
        password: str
    ) -> Optional[str]:

        if len(password) < 8:

            return "Password must be at least 8 characters"

        return None

    @staticmethod
    def hash_password(
        password: str
    ) -> str:

        salt = bcrypt.gensalt()

        hashed = bcrypt.hashpw(
            password.encode("utf-8"),
            salt
        )

        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(
        plain_password: str,
        hashed_password: str
    ) -> bool:

        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )

    @staticmethod
    def create_access_token(
        data: dict,
        expires_delta: Optional[timedelta] = None
    ) -> str:

        to_encode = data.copy()

        expire = datetime.utcnow() + (
            expires_delta
            if expires_delta
            else timedelta(
                hours=settings.JWT_EXPIRY_HOURS
            )
        )

        to_encode["exp"] = expire

        return jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )

    @staticmethod
    def decode_access_token(
        token: str
    ) -> Optional[dict]:

        try:

            return jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )

        except JWTError:

            return None

    @classmethod
    def create_user(
        cls,
        name: str,
        email: str,
        password: str
    ) -> dict:

        email = cls.normalize_email(email)

        password_hash = cls.hash_password(password)

        created_at = datetime.utcnow().isoformat()

        connection = DatabaseService.get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO users (
                name,
                email,
                password_hash,
                created_at,
                email_verified
            )
            VALUES (?, ?, ?, ?, 0)
            """,
            (name, email, password_hash, created_at)
        )

        connection.commit()

        user_id = cursor.lastrowid

        connection.close()

        SubscriptionService.create_default_subscription(user_id)

        return {
            "id": user_id,
            "name": name,
            "email": email,
            "created_at": created_at,
            "credits_remaining": settings.FREE_CREDITS,
            "email_verified": False,
            "is_admin": False,
        }

    @classmethod
    def get_user_by_email(
        cls,
        email: str
    ) -> Optional[dict]:

        email = cls.normalize_email(email)

        connection = DatabaseService.get_connection()

        connection.row_factory = (
            lambda cursor, row: {
                col[0]: row[idx]
                for idx, col in enumerate(
                    cursor.description
                )
            }
        )

        cursor = connection.cursor()

        # Compares case-insensitively so pre-existing rows stored with
        # mixed-case emails (before this normalization was added) keep
        # matching a lowercased lookup.
        cursor.execute(
            """
            SELECT
                id,
                name,
                email,
                password_hash,
                created_at,
                last_login,
                credits_remaining,
                email_verified,
                is_admin
            FROM users
            WHERE LOWER(email) = ?
            """,
            (email,)
        )

        user = cursor.fetchone()

        connection.close()

        return user

    @classmethod
    def get_user_by_id(
        cls,
        user_id: int
    ) -> Optional[dict]:

        connection = DatabaseService.get_connection()

        connection.row_factory = (
            lambda cursor, row: {
                col[0]: row[idx]
                for idx, col in enumerate(
                    cursor.description
                )
            }
        )

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                name,
                email,
                created_at,
                last_login,
                credits_remaining,
                email_verified,
                is_admin
            FROM users
            WHERE id = ?
            """,
            (user_id,)
        )

        user = cursor.fetchone()

        connection.close()

        return user

    @classmethod
    def update_last_login(
        cls,
        user_id: int
    ) -> None:

        last_login = datetime.utcnow().isoformat()

        connection = DatabaseService.get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE users
            SET last_login = ?
            WHERE id = ?
            """,
            (last_login, user_id)
        )

        connection.commit()

        connection.close()

    @classmethod
    def deduct_credit(
        cls,
        user_id: int
    ) -> bool:

        connection = DatabaseService.get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE users
            SET credits_remaining = credits_remaining - 1
            WHERE id = ?
              AND credits_remaining > 0
            """,
            (user_id,)
        )

        connection.commit()

        deducted = cursor.rowcount > 0

        connection.close()

        return deducted

    @classmethod
    def refund_credit(
        cls,
        user_id: int
    ) -> None:

        connection = DatabaseService.get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE users
            SET credits_remaining = credits_remaining + 1
            WHERE id = ?
            """,
            (user_id,)
        )

        connection.commit()

        connection.close()
